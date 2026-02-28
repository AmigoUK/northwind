"""data/fk.py — FK (Faktura Korygujaca / Credit Note) data access and business logic."""
from __future__ import annotations

from db import get_connection, next_doc_number
from data.products import apply_stock_delta


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT fk.FK_ID, fk.FK_Number, fk.FK_Date, c.CompanyName AS Customer,
                  fk.FK_Type, f.FV_Number AS OrigFV, fk.TotalCorrection, fk.Status
           FROM FK fk
           LEFT JOIN Customers c ON fk.CustomerID = c.CustomerID
           LEFT JOIN FV f ON fk.FV_ID = f.FV_ID
           ORDER BY fk.FK_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        """SELECT fk.FK_ID, fk.FK_Number, fk.FK_Date, c.CompanyName AS Customer,
                  fk.FK_Type, f.FV_Number AS OrigFV, fk.TotalCorrection, fk.Status
           FROM FK fk
           LEFT JOIN Customers c ON fk.CustomerID = c.CustomerID
           LEFT JOIN FV f ON fk.FV_ID = f.FV_ID
           WHERE fk.FK_Number LIKE ? OR f.FV_Number LIKE ? OR c.CompanyName LIKE ?
           ORDER BY fk.FK_ID DESC""",
        (like, like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT fk.*, c.CompanyName, f.FV_Number
           FROM FK fk
           LEFT JOIN Customers c ON fk.CustomerID = c.CustomerID
           LEFT JOIN FV f ON fk.FV_ID = f.FV_ID
           WHERE fk.FK_ID = ?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_items(fk_id) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT fi.ProductID, p.ProductName,
                  fi.OrigQuantity, fi.CorrQuantity,
                  fi.OrigUnitPrice, fi.CorrUnitPrice,
                  fi.LineCorrection
           FROM FK_Items fi
           JOIN Products p ON fi.ProductID = p.ProductID
           WHERE fi.FK_ID = ?
           ORDER BY p.ProductName""",
        (fk_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_for_fv(fv_id) -> list:
    """All FK linked to a specific FV."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT FK_ID, FK_Number, FK_Date, FK_Type, TotalCorrection
           FROM FK WHERE FV_ID=? ORDER BY FK_ID""",
        (fv_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_full_reversal(fv_id: int, reason: str, fk_date: str,
                         user_id: int, reverse_stock: bool = False,
                         notes: str = "") -> int:
    """Full reversal FK: all lines set to CorrQuantity=0.
    TotalCorrection = -TotalNet. Adjusts FV.TotalNet."""
    from datetime import datetime
    conn = get_connection()
    fv = conn.execute(
        "SELECT CustomerID, TotalNet, COALESCE(PaidAmount, 0) FROM FV WHERE FV_ID=?",
        (fv_id,),
    ).fetchone()
    if not fv:
        conn.close()
        raise ValueError(f"FV #{fv_id} not found.")
    customer_id, total_net, paid = fv
    total_net = total_net or 0.0

    number = next_doc_number("FK", conn)
    total_correction = -total_net

    cur = conn.execute(
        "INSERT INTO FK (FK_Number, FV_ID, CustomerID, FK_Date, FK_Type, Reason, "
        "Status, TotalCorrection, Notes, CreatedBy, CreatedAt) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (number, fv_id, customer_id, fk_date, "full_reversal", reason,
         "issued", total_correction, notes or None, user_id,
         datetime.now().isoformat()),
    )
    fk_id = cur.lastrowid

    # Get all line items from linked WZ docs
    items = conn.execute(
        """SELECT p.ProductID, SUM(wi.Quantity) AS Qty, wi.UnitPrice
           FROM FV_WZ fw
           JOIN WZ_Items wi ON fw.WZ_ID = wi.WZ_ID
           JOIN Products p ON wi.ProductID = p.ProductID
           WHERE fw.FV_ID = ?
           GROUP BY p.ProductID, wi.UnitPrice""",
        (fv_id,),
    ).fetchall()
    for it in items:
        line_corr = -(it["Qty"] * it["UnitPrice"])
        conn.execute(
            "INSERT INTO FK_Items (FK_ID, ProductID, OrigQuantity, CorrQuantity, "
            "OrigUnitPrice, CorrUnitPrice, LineCorrection) VALUES (?,?,?,?,?,?,?)",
            (fk_id, it["ProductID"], it["Qty"], 0, it["UnitPrice"], it["UnitPrice"],
             line_corr),
        )
        if reverse_stock:
            apply_stock_delta(it["ProductID"], it["Qty"], conn)

    # Adjust FV.TotalNet and recalculate status
    conn.execute(
        "UPDATE FV SET TotalNet = TotalNet + ? WHERE FV_ID=?",
        (total_correction, fv_id),
    )
    # Revert WZ from 'invoiced' to 'issued'
    conn.execute(
        "UPDATE WZ SET Status='issued' WHERE WZ_ID IN "
        "(SELECT WZ_ID FROM FV_WZ WHERE FV_ID=?) AND Status='invoiced'",
        (fv_id,),
    )
    _recalc_fv_status(fv_id, conn)
    conn.commit()
    conn.close()
    return fk_id


def create_partial_correction(fv_id: int, reason: str, fk_date: str,
                              user_id: int, corrections: list[dict],
                              reverse_stock: bool = False,
                              notes: str = "") -> int:
    """Partial correction FK.
    corrections = [{product_id, new_quantity, new_unit_price}, ...]
    """
    from datetime import datetime
    conn = get_connection()
    fv = conn.execute(
        "SELECT CustomerID FROM FV WHERE FV_ID=?", (fv_id,)
    ).fetchone()
    if not fv:
        conn.close()
        raise ValueError(f"FV #{fv_id} not found.")
    customer_id = fv[0]

    number = next_doc_number("FK", conn)

    # Get original items to compare
    orig_items = {}
    items = conn.execute(
        """SELECT p.ProductID, SUM(wi.Quantity) AS Qty, wi.UnitPrice
           FROM FV_WZ fw
           JOIN WZ_Items wi ON fw.WZ_ID = wi.WZ_ID
           JOIN Products p ON wi.ProductID = p.ProductID
           WHERE fw.FV_ID = ?
           GROUP BY p.ProductID, wi.UnitPrice""",
        (fv_id,),
    ).fetchall()
    for it in items:
        orig_items[it["ProductID"]] = {"qty": it["Qty"], "price": it["UnitPrice"]}

    total_correction = 0.0
    fk_items = []
    for corr in corrections:
        pid = corr["product_id"]
        orig = orig_items.get(pid)
        if not orig:
            continue
        new_qty = corr.get("new_quantity", orig["qty"])
        new_price = corr.get("new_unit_price", orig["price"])
        line_corr = (new_qty * new_price) - (orig["qty"] * orig["price"])
        total_correction += line_corr
        fk_items.append((pid, orig["qty"], new_qty, orig["price"], new_price, line_corr))

    cur = conn.execute(
        "INSERT INTO FK (FK_Number, FV_ID, CustomerID, FK_Date, FK_Type, Reason, "
        "Status, TotalCorrection, Notes, CreatedBy, CreatedAt) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (number, fv_id, customer_id, fk_date, "partial_correction", reason,
         "issued", total_correction, notes or None, user_id,
         datetime.now().isoformat()),
    )
    fk_id = cur.lastrowid

    for pid, orig_qty, new_qty, orig_price, new_price, line_corr in fk_items:
        conn.execute(
            "INSERT INTO FK_Items (FK_ID, ProductID, OrigQuantity, CorrQuantity, "
            "OrigUnitPrice, CorrUnitPrice, LineCorrection) VALUES (?,?,?,?,?,?,?)",
            (fk_id, pid, orig_qty, new_qty, orig_price, new_price, line_corr),
        )
        if reverse_stock and new_qty < orig_qty:
            delta = orig_qty - new_qty
            apply_stock_delta(pid, delta, conn)

    # Adjust FV.TotalNet
    conn.execute(
        "UPDATE FV SET TotalNet = TotalNet + ? WHERE FV_ID=?",
        (total_correction, fv_id),
    )
    _recalc_fv_status(fv_id, conn)
    conn.commit()
    conn.close()
    return fk_id


def create_cancellation(fv_id: int, reason: str, fk_date: str,
                        user_id: int, reverse_stock: bool = False,
                        notes: str = "") -> int:
    """Full cancellation FK: same as full_reversal + marks FV as cancelled."""
    fk_id = create_full_reversal(fv_id, reason, fk_date, user_id,
                                 reverse_stock, notes)
    # Update FK type to 'cancellation' and cancel the FV
    conn = get_connection()
    conn.execute(
        "UPDATE FK SET FK_Type='cancellation' WHERE FK_ID=?", (fk_id,)
    )
    conn.execute(
        "UPDATE FV SET Status='cancelled' WHERE FV_ID=?", (fv_id,)
    )
    conn.commit()
    conn.close()
    return fk_id


def _recalc_fv_status(fv_id: int, conn) -> None:
    """Recalculate FV.Status based on current PaidAmount vs TotalNet."""
    row = conn.execute(
        "SELECT TotalNet, COALESCE(PaidAmount, 0) FROM FV WHERE FV_ID=?",
        (fv_id,),
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
    conn.execute("UPDATE FV SET Status=? WHERE FV_ID=?", (status, fv_id))
