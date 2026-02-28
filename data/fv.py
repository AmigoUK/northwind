from __future__ import annotations
"""data/fv.py — FV (Faktura VAT) data access."""
from db import get_connection, next_doc_number


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT f.FV_ID, f.FV_Number, f.FV_Date, c.CompanyName AS Customer,
                  f.Status, f.PaymentMethod, f.TotalNet
           FROM FV f
           LEFT JOIN Customers c ON f.CustomerID = c.CustomerID
           ORDER BY f.FV_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        """SELECT f.FV_ID, f.FV_Number, f.FV_Date, c.CompanyName AS Customer,
                  f.Status, f.PaymentMethod, f.TotalNet
           FROM FV f
           LEFT JOIN Customers c ON f.CustomerID = c.CustomerID
           WHERE f.FV_Number LIKE ? OR c.CompanyName LIKE ?
           ORDER BY f.FV_ID DESC""",
        (like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT f.*, c.CompanyName
           FROM FV f
           LEFT JOIN Customers c ON f.CustomerID = c.CustomerID
           WHERE f.FV_ID = ?""",
        (pk,),
    ).fetchone()
    if not row:
        conn.close()
        return None
    d = dict(row)
    total = d.get("TotalNet") or 0.0
    paid  = d.get("PaidAmount") or 0.0
    d["Outstanding"] = total - paid
    # FK correction summary
    fk_row = conn.execute(
        "SELECT COUNT(*) AS cnt, COALESCE(SUM(TotalCorrection), 0) AS total_corr "
        "FROM FK WHERE FV_ID = ?",
        (pk,),
    ).fetchone()
    conn.close()
    d["FK_Count"] = fk_row["cnt"] if fk_row else 0
    d["FK_TotalCorrection"] = fk_row["total_corr"] if fk_row else 0.0
    return d


def fetch_linked_wz(fv_id) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT w.WZ_ID, w.WZ_Number, w.WZ_Date,
                  COALESCE(SUM(wi.UnitPrice * wi.Quantity), 0.0) AS Total
           FROM FV_WZ fw
           JOIN WZ w ON fw.WZ_ID = w.WZ_ID
           LEFT JOIN WZ_Items wi ON w.WZ_ID = wi.WZ_ID
           WHERE fw.FV_ID = ?
           GROUP BY w.WZ_ID
           ORDER BY w.WZ_Date""",
        (fv_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_line_items(fv_id) -> list:
    """Aggregate line items from all linked WZ docs."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.ProductID, p.ProductName,
                  SUM(wi.Quantity) AS Quantity, wi.UnitPrice,
                  SUM(wi.UnitPrice * wi.Quantity) AS LineTotal
           FROM FV_WZ fw
           JOIN WZ_Items wi ON fw.WZ_ID = wi.WZ_ID
           JOIN Products p ON wi.ProductID = p.ProductID
           WHERE fw.FV_ID = ?
           GROUP BY p.ProductID, wi.UnitPrice
           ORDER BY p.ProductName""",
        (fv_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create(customer_id: str, wz_ids: list[int], fv_date: str,
           payment_term_days: int = 30, payment_method: str = "",
           notes: str = "") -> int:
    """Create FV from list of WZ IDs. No payment doc is auto-created. Returns FV_ID."""
    from datetime import date, timedelta
    conn = get_connection()
    # Compute total from WZ items
    placeholders = ",".join("?" * len(wz_ids))
    total = conn.execute(
        f"SELECT COALESCE(SUM(UnitPrice * Quantity), 0) FROM WZ_Items WHERE WZ_ID IN ({placeholders})",
        wz_ids,
    ).fetchone()[0]
    fv_date_obj = date.fromisoformat(fv_date)
    due_date = str(fv_date_obj + timedelta(days=payment_term_days))
    number = next_doc_number("FV", conn)
    cur = conn.execute(
        "INSERT INTO FV (FV_Number, CustomerID, FV_Date, DueDate, PaymentMethod, "
        "Status, TotalNet, Notes, PaymentTermDays, PaidAmount) "
        "VALUES (?,?,?,?,?,'issued',?,?,?,0)",
        (number, customer_id, fv_date, due_date,
         payment_method or None, total, notes or None, payment_term_days),
    )
    fv_id = cur.lastrowid
    for wz_id in wz_ids:
        conn.execute("INSERT INTO FV_WZ (FV_ID, WZ_ID) VALUES (?,?)", (fv_id, wz_id))
        conn.execute("UPDATE WZ SET Status='invoiced' WHERE WZ_ID=?", (wz_id,))
    conn.commit()
    conn.close()
    return fv_id


def record_payment(fv_id: int, amount: float, method: str,
                   description: str = "") -> int:
    """Record a payment against an FV. Creates KP or BankEntry. Returns payment doc ID."""
    from data.kassa import create_kp
    from data.bank import create_bank_entry
    conn = get_connection()
    row = conn.execute(
        "SELECT CustomerID, FV_Number, TotalNet, COALESCE(PaidAmount, 0) "
        "FROM FV WHERE FV_ID=?",
        (fv_id,),
    ).fetchone()
    if not row:
        conn.close()
        raise ValueError(f"FV #{fv_id} not found.")
    customer_id, fv_number, total_net, paid_so_far = row
    new_paid = paid_so_far + amount
    if new_paid >= total_net:
        new_status = "paid"
    elif new_paid > 0:
        new_status = "partial"
    else:
        new_status = "issued"
    conn.execute(
        "UPDATE FV SET PaidAmount=?, Status=? WHERE FV_ID=?",
        (new_paid, new_status, fv_id),
    )
    conn.commit()
    conn.close()
    desc = description or f"Payment for {fv_number}"
    if method == "cash":
        return create_kp(customer_id=customer_id, fv_id=fv_id,
                         amount=amount, description=desc)
    else:
        return create_bank_entry(
            direction="in", customer_id=customer_id, fv_id=fv_id,
            amount=amount, description=desc,
        )


def mark_paid(fv_id: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE FV SET Status='paid' WHERE FV_ID=?", (fv_id,))
    conn.commit()
    conn.close()


def cancel(fv_id: int, reason: str, user_id: int) -> None:
    """Cancel an unpaid FV: mark as cancelled, revert linked WZ to 'issued'."""
    from datetime import datetime
    conn = get_connection()
    fv = conn.execute(
        "SELECT Status, COALESCE(PaidAmount, 0) FROM FV WHERE FV_ID=?", (fv_id,)
    ).fetchone()
    if not fv:
        conn.close()
        raise ValueError(f"FV #{fv_id} not found.")
    status, paid = fv[0], fv[1]
    if status == "cancelled":
        conn.close()
        raise ValueError("FV is already cancelled.")
    if status not in ("issued", "partial", "paid"):
        conn.close()
        raise ValueError(f"Cannot cancel FV with status '{status}'.")
    if paid > 0:
        conn.close()
        raise ValueError("FV has payments. Issue a Faktura Korygujaca (FK) instead.")
    # Revert linked WZ from 'invoiced' to 'issued'
    conn.execute(
        "UPDATE WZ SET Status='issued' WHERE WZ_ID IN "
        "(SELECT WZ_ID FROM FV_WZ WHERE FV_ID=?) AND Status='invoiced'",
        (fv_id,),
    )
    conn.execute(
        "UPDATE FV SET Status='cancelled', CancelledAt=?, CancelledBy=?, CancelReason=? "
        "WHERE FV_ID=?",
        (datetime.now().isoformat(), user_id, reason, fv_id),
    )
    conn.commit()
    conn.close()


def delete(pk) -> None:
    from data.delete_guards import can_delete_fv, before_delete_fv
    ok, reasons = can_delete_fv(pk)
    if not ok:
        raise ValueError("Cannot delete: " + "; ".join(reasons))
    before_delete_fv(pk)  # restore WZ docs to 'issued'
    conn = get_connection()
    conn.execute("DELETE FROM FV WHERE FV_ID=?", (pk,))
    conn.commit()
    conn.close()
