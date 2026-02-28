"""data/cn.py — CN (Credit Note) data access and business logic."""
from __future__ import annotations

from db import get_connection, next_doc_number
from data.products import apply_stock_delta


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT fk.CN_ID, fk.CN_Number, fk.CN_Date, c.CompanyName AS Customer,
                  fk.CN_Type, f.INV_Number AS OrigINV, fk.TotalCorrection, fk.Status
           FROM CN fk
           LEFT JOIN Customers c ON fk.CustomerID = c.CustomerID
           LEFT JOIN INV f ON fk.INV_ID = f.INV_ID
           ORDER BY fk.CN_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        """SELECT fk.CN_ID, fk.CN_Number, fk.CN_Date, c.CompanyName AS Customer,
                  fk.CN_Type, f.INV_Number AS OrigINV, fk.TotalCorrection, fk.Status
           FROM CN fk
           LEFT JOIN Customers c ON fk.CustomerID = c.CustomerID
           LEFT JOIN INV f ON fk.INV_ID = f.INV_ID
           WHERE fk.CN_Number LIKE ? OR f.INV_Number LIKE ? OR c.CompanyName LIKE ?
           ORDER BY fk.CN_ID DESC""",
        (like, like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT fk.*, c.CompanyName, f.INV_Number
           FROM CN fk
           LEFT JOIN Customers c ON fk.CustomerID = c.CustomerID
           LEFT JOIN INV f ON fk.INV_ID = f.INV_ID
           WHERE fk.CN_ID = ?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_items(cn_id) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT fi.ProductID, p.ProductName,
                  fi.OrigQuantity, fi.CorrQuantity,
                  fi.OrigUnitPrice, fi.CorrUnitPrice,
                  fi.LineCorrection
           FROM CN_Items fi
           JOIN Products p ON fi.ProductID = p.ProductID
           WHERE fi.CN_ID = ?
           ORDER BY p.ProductName""",
        (cn_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_for_inv(inv_id) -> list:
    """All CN linked to a specific INV."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT CN_ID, CN_Number, CN_Date, CN_Type, TotalCorrection
           FROM CN WHERE INV_ID=? ORDER BY CN_ID""",
        (inv_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_full_reversal(inv_id: int, reason: str, cn_date: str,
                         user_id: int, reverse_stock: bool = False,
                         notes: str = "") -> int:
    """Full reversal CN: all lines set to CorrQuantity=0.
    TotalCorrection = -TotalNet. Adjusts INV.TotalNet."""
    from datetime import datetime
    conn = get_connection()
    inv = conn.execute(
        "SELECT CustomerID, TotalNet, COALESCE(PaidAmount, 0) FROM INV WHERE INV_ID=?",
        (inv_id,),
    ).fetchone()
    if not inv:
        conn.close()
        raise ValueError(f"INV #{inv_id} not found.")
    customer_id, total_net, paid = inv
    total_net = total_net or 0.0

    number = next_doc_number("CN", conn)
    total_correction = -total_net

    cur = conn.execute(
        "INSERT INTO CN (CN_Number, INV_ID, CustomerID, CN_Date, CN_Type, Reason, "
        "Status, TotalCorrection, Notes, CreatedBy, CreatedAt) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (number, inv_id, customer_id, cn_date, "full_reversal", reason,
         "issued", total_correction, notes or None, user_id,
         datetime.now().isoformat()),
    )
    cn_id = cur.lastrowid

    # Get all line items from linked DN docs
    items = conn.execute(
        """SELECT p.ProductID, SUM(wi.Quantity) AS Qty, wi.UnitPrice
           FROM INV_DN fw
           JOIN DN_Items wi ON fw.DN_ID = wi.DN_ID
           JOIN Products p ON wi.ProductID = p.ProductID
           WHERE fw.INV_ID = ?
           GROUP BY p.ProductID, wi.UnitPrice""",
        (inv_id,),
    ).fetchall()
    for it in items:
        line_corr = -(it["Qty"] * it["UnitPrice"])
        conn.execute(
            "INSERT INTO CN_Items (CN_ID, ProductID, OrigQuantity, CorrQuantity, "
            "OrigUnitPrice, CorrUnitPrice, LineCorrection) VALUES (?,?,?,?,?,?,?)",
            (cn_id, it["ProductID"], it["Qty"], 0, it["UnitPrice"], it["UnitPrice"],
             line_corr),
        )
        if reverse_stock:
            apply_stock_delta(it["ProductID"], it["Qty"], conn)

    # Adjust INV.TotalNet and recalculate status
    conn.execute(
        "UPDATE INV SET TotalNet = TotalNet + ? WHERE INV_ID=?",
        (total_correction, inv_id),
    )
    # Revert DN from 'invoiced' to 'issued'
    conn.execute(
        "UPDATE DN SET Status='issued' WHERE DN_ID IN "
        "(SELECT DN_ID FROM INV_DN WHERE INV_ID=?) AND Status='invoiced'",
        (inv_id,),
    )
    _recalc_inv_status(inv_id, conn)
    conn.commit()
    conn.close()
    return cn_id


def create_partial_correction(inv_id: int, reason: str, cn_date: str,
                              user_id: int, corrections: list[dict],
                              reverse_stock: bool = False,
                              notes: str = "") -> int:
    """Partial correction CN.
    corrections = [{product_id, new_quantity, new_unit_price}, ...]
    """
    from datetime import datetime
    conn = get_connection()
    inv = conn.execute(
        "SELECT CustomerID FROM INV WHERE INV_ID=?", (inv_id,)
    ).fetchone()
    if not inv:
        conn.close()
        raise ValueError(f"INV #{inv_id} not found.")
    customer_id = inv[0]

    number = next_doc_number("CN", conn)

    # Get original items to compare
    orig_items = {}
    items = conn.execute(
        """SELECT p.ProductID, SUM(wi.Quantity) AS Qty, wi.UnitPrice
           FROM INV_DN fw
           JOIN DN_Items wi ON fw.DN_ID = wi.DN_ID
           JOIN Products p ON wi.ProductID = p.ProductID
           WHERE fw.INV_ID = ?
           GROUP BY p.ProductID, wi.UnitPrice""",
        (inv_id,),
    ).fetchall()
    for it in items:
        orig_items[it["ProductID"]] = {"qty": it["Qty"], "price": it["UnitPrice"]}

    total_correction = 0.0
    cn_items = []
    for corr in corrections:
        pid = corr["product_id"]
        orig = orig_items.get(pid)
        if not orig:
            continue
        new_qty = corr.get("new_quantity", orig["qty"])
        new_price = corr.get("new_unit_price", orig["price"])
        line_corr = (new_qty * new_price) - (orig["qty"] * orig["price"])
        total_correction += line_corr
        cn_items.append((pid, orig["qty"], new_qty, orig["price"], new_price, line_corr))

    cur = conn.execute(
        "INSERT INTO CN (CN_Number, INV_ID, CustomerID, CN_Date, CN_Type, Reason, "
        "Status, TotalCorrection, Notes, CreatedBy, CreatedAt) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (number, inv_id, customer_id, cn_date, "partial_correction", reason,
         "issued", total_correction, notes or None, user_id,
         datetime.now().isoformat()),
    )
    cn_id = cur.lastrowid

    for pid, orig_qty, new_qty, orig_price, new_price, line_corr in cn_items:
        conn.execute(
            "INSERT INTO CN_Items (CN_ID, ProductID, OrigQuantity, CorrQuantity, "
            "OrigUnitPrice, CorrUnitPrice, LineCorrection) VALUES (?,?,?,?,?,?,?)",
            (cn_id, pid, orig_qty, new_qty, orig_price, new_price, line_corr),
        )
        if reverse_stock and new_qty < orig_qty:
            delta = orig_qty - new_qty
            apply_stock_delta(pid, delta, conn)

    # Adjust INV.TotalNet
    conn.execute(
        "UPDATE INV SET TotalNet = TotalNet + ? WHERE INV_ID=?",
        (total_correction, inv_id),
    )
    _recalc_inv_status(inv_id, conn)
    conn.commit()
    conn.close()
    return cn_id


def create_cancellation(inv_id: int, reason: str, cn_date: str,
                        user_id: int, reverse_stock: bool = False,
                        notes: str = "") -> int:
    """Full cancellation CN: same as full_reversal + marks INV as cancelled."""
    cn_id = create_full_reversal(inv_id, reason, cn_date, user_id,
                                 reverse_stock, notes)
    # Update CN type to 'cancellation' and cancel the INV
    conn = get_connection()
    conn.execute(
        "UPDATE CN SET CN_Type='cancellation' WHERE CN_ID=?", (cn_id,)
    )
    conn.execute(
        "UPDATE INV SET Status='cancelled' WHERE INV_ID=?", (inv_id,)
    )
    conn.commit()
    conn.close()
    return cn_id


def _recalc_inv_status(inv_id: int, conn) -> None:
    """Recalculate INV.Status based on current PaidAmount vs TotalNet."""
    row = conn.execute(
        "SELECT TotalNet, COALESCE(PaidAmount, 0) FROM INV WHERE INV_ID=?",
        (inv_id,),
    ).fetchone()
    if not row:
        return
    total, paid = row[0] or 0, row[1]
    if total <= 0:
        # Fully reversed — check for overpayment
        status = "paid" if paid > 0 else "cancelled"
    elif paid >= total:
        status = "paid"
    elif paid > 0:
        status = "partial"
    else:
        status = "issued"
    conn.execute("UPDATE INV SET Status=? WHERE INV_ID=?", (status, inv_id))
