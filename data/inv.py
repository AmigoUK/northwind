from __future__ import annotations
"""data/inv.py — INV (Invoice) data access."""
from db import get_connection, next_doc_number


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT f.INV_ID, f.INV_Number, f.INV_Date, c.CompanyName AS Customer,
                  f.Status, f.PaymentMethod, f.TotalNet
           FROM INV f
           LEFT JOIN Customers c ON f.CustomerID = c.CustomerID
           ORDER BY f.INV_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        """SELECT f.INV_ID, f.INV_Number, f.INV_Date, c.CompanyName AS Customer,
                  f.Status, f.PaymentMethod, f.TotalNet
           FROM INV f
           LEFT JOIN Customers c ON f.CustomerID = c.CustomerID
           WHERE f.INV_Number LIKE ? OR c.CompanyName LIKE ?
           ORDER BY f.INV_ID DESC""",
        (like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT f.*, c.CompanyName
           FROM INV f
           LEFT JOIN Customers c ON f.CustomerID = c.CustomerID
           WHERE f.INV_ID = ?""",
        (pk,),
    ).fetchone()
    if not row:
        conn.close()
        return None
    d = dict(row)
    total = d.get("TotalNet") or 0.0
    paid  = d.get("PaidAmount") or 0.0
    d["Outstanding"] = total - paid
    # CN correction summary
    fk_row = conn.execute(
        "SELECT COUNT(*) AS cnt, COALESCE(SUM(TotalCorrection), 0) AS total_corr "
        "FROM CN WHERE INV_ID = ?",
        (pk,),
    ).fetchone()
    conn.close()
    d["CN_Count"] = fk_row["cnt"] if fk_row else 0
    d["CN_TotalCorrection"] = fk_row["total_corr"] if fk_row else 0.0
    return d


def fetch_linked_dn(inv_id) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT w.DN_ID, w.DN_Number, w.DN_Date,
                  COALESCE(SUM(wi.UnitPrice * wi.Quantity), 0.0) AS Total
           FROM INV_DN fw
           JOIN DN w ON fw.DN_ID = w.DN_ID
           LEFT JOIN DN_Items wi ON w.DN_ID = wi.DN_ID
           WHERE fw.INV_ID = ?
           GROUP BY w.DN_ID
           ORDER BY w.DN_Date""",
        (inv_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_line_items(inv_id) -> list:
    """Aggregate line items from all linked DN docs."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.ProductID, p.ProductName,
                  SUM(wi.Quantity) AS Quantity, wi.UnitPrice,
                  SUM(wi.UnitPrice * wi.Quantity) AS LineTotal
           FROM INV_DN fw
           JOIN DN_Items wi ON fw.DN_ID = wi.DN_ID
           JOIN Products p ON wi.ProductID = p.ProductID
           WHERE fw.INV_ID = ?
           GROUP BY p.ProductID, wi.UnitPrice
           ORDER BY p.ProductName""",
        (inv_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create(customer_id: str, wz_ids: list[int], inv_date: str,
           payment_term_days: int = 30, payment_method: str = "",
           notes: str = "", year_override: int | None = None) -> int:
    """Create INV from list of DN IDs. No payment doc is auto-created. Returns INV_ID."""
    from datetime import date, timedelta
    conn = get_connection()
    # Compute total from DN items
    placeholders = ",".join("?" * len(wz_ids))
    total = conn.execute(
        f"SELECT COALESCE(SUM(UnitPrice * Quantity), 0) FROM DN_Items WHERE DN_ID IN ({placeholders})",
        wz_ids,
    ).fetchone()[0]
    inv_date_obj = date.fromisoformat(inv_date)
    due_date = str(inv_date_obj + timedelta(days=payment_term_days))
    number = next_doc_number("INV", conn, year_override=year_override)
    cur = conn.execute(
        "INSERT INTO INV (INV_Number, CustomerID, INV_Date, DueDate, PaymentMethod, "
        "Status, TotalNet, Notes, PaymentTermDays, PaidAmount) "
        "VALUES (?,?,?,?,?,'issued',?,?,?,0)",
        (number, customer_id, inv_date, due_date,
         payment_method or None, total, notes or None, payment_term_days),
    )
    inv_id = cur.lastrowid
    for wz_id in wz_ids:
        conn.execute("INSERT INTO INV_DN (INV_ID, DN_ID) VALUES (?,?)", (inv_id, wz_id))
        conn.execute("UPDATE DN SET Status='invoiced' WHERE DN_ID=?", (wz_id,))
    conn.commit()
    conn.close()
    return inv_id


def _recalc_inv_status(inv_id: int, conn) -> None:
    """Set INV.Status based on PaidAmount vs TotalNet.
    issued/partial → partial  (0 < PaidAmount < TotalNet)
    issued/partial → paid     (PaidAmount >= TotalNet)
    Called by record_payment() and allocate_payment_to_inv()."""
    row = conn.execute(
        "SELECT TotalNet, COALESCE(PaidAmount, 0) FROM INV WHERE INV_ID=?", (inv_id,)
    ).fetchone()
    if not row:
        return
    total, paid = row[0], row[1]
    if paid >= total:
        status = "paid"
    elif paid > 0:
        status = "partial"
    else:
        status = "issued"
    conn.execute("UPDATE INV SET Status=? WHERE INV_ID=?", (status, inv_id))


def record_payment(inv_id: int, amount: float, method: str,
                   description: str = "",
                   date_override: str | None = None) -> int:
    """Record a payment against an INV. Creates CR or BankEntry. Returns payment doc ID."""
    from data.cash import create_cr
    from data.bank import create_bank_entry
    conn = get_connection()
    row = conn.execute(
        "SELECT CustomerID, INV_Number, COALESCE(PaidAmount, 0) "
        "FROM INV WHERE INV_ID=?",
        (inv_id,),
    ).fetchone()
    if not row:
        conn.close()
        raise ValueError(f"INV #{inv_id} not found.")
    customer_id, inv_number, paid_so_far = row
    new_paid = paid_so_far + amount
    conn.execute(
        "UPDATE INV SET PaidAmount=? WHERE INV_ID=?",
        (new_paid, inv_id),
    )
    _recalc_inv_status(inv_id, conn)
    conn.commit()
    conn.close()
    desc = description or f"Payment for {inv_number}"
    if method == "cash":
        return create_cr(customer_id=customer_id, inv_id=inv_id,
                         amount=amount, description=desc,
                         date_override=date_override)
    else:
        return create_bank_entry(
            direction="in", customer_id=customer_id, inv_id=inv_id,
            amount=amount, description=desc, date_override=date_override,
        )


def mark_paid(inv_id: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE INV SET Status='paid' WHERE INV_ID=?", (inv_id,))
    conn.commit()
    conn.close()


def cancel(inv_id: int, reason: str, user_id: int) -> None:
    """Cancel an unpaid INV: mark as cancelled, revert linked DN to 'issued'."""
    from datetime import datetime
    conn = get_connection()
    inv = conn.execute(
        "SELECT Status, COALESCE(PaidAmount, 0) FROM INV WHERE INV_ID=?", (inv_id,)
    ).fetchone()
    if not inv:
        conn.close()
        raise ValueError(f"INV #{inv_id} not found.")
    status, paid = inv[0], inv[1]
    if status == "cancelled":
        conn.close()
        raise ValueError("INV is already cancelled.")
    if status not in ("issued", "partial", "paid"):
        conn.close()
        raise ValueError(f"Cannot cancel INV with status '{status}'.")
    if paid > 0:
        conn.close()
        raise ValueError("INV has payments. Issue a Credit Note (CN) instead.")
    # Revert linked DN from 'invoiced' to 'issued'
    conn.execute(
        "UPDATE DN SET Status='issued' WHERE DN_ID IN "
        "(SELECT DN_ID FROM INV_DN WHERE INV_ID=?) AND Status='invoiced'",
        (inv_id,),
    )
    conn.execute(
        "UPDATE INV SET Status='cancelled', CancelledAt=?, CancelledBy=?, CancelReason=? "
        "WHERE INV_ID=?",
        (datetime.now().isoformat(), user_id, reason, inv_id),
    )
    conn.commit()
    conn.close()


def delete(pk) -> None:
    from data.delete_guards import can_delete_inv, before_delete_inv
    ok, reasons = can_delete_inv(pk)
    if not ok:
        raise ValueError("Cannot delete: " + "; ".join(reasons))
    before_delete_inv(pk)  # restore DN docs to 'issued'
    conn = get_connection()
    conn.execute("DELETE FROM INV WHERE INV_ID=?", (pk,))
    conn.commit()
    conn.close()
