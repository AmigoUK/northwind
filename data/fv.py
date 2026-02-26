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
    conn.close()
    return dict(row) if row else None


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
           due_date: str, payment_method: str, notes: str = "") -> int:
    """Create FV from list of WZ IDs. Auto-generates KP or BankEntry. Returns FV_ID."""
    from data.kassa import create_kp
    from data.bank import create_bank_entry
    conn = get_connection()
    # Compute total from WZ items
    placeholders = ",".join("?" * len(wz_ids))
    total = conn.execute(
        f"SELECT COALESCE(SUM(UnitPrice * Quantity), 0) FROM WZ_Items WHERE WZ_ID IN ({placeholders})",
        wz_ids,
    ).fetchone()[0]
    number = next_doc_number("FV", conn)
    cur = conn.execute(
        "INSERT INTO FV (FV_Number, CustomerID, FV_Date, DueDate, PaymentMethod, Status, TotalNet, Notes) "
        "VALUES (?,?,?,?,?,'issued',?,?)",
        (number, customer_id, fv_date, due_date or None,
         payment_method or None, total, notes or None),
    )
    fv_id = cur.lastrowid
    for wz_id in wz_ids:
        conn.execute("INSERT INTO FV_WZ (FV_ID, WZ_ID) VALUES (?,?)", (fv_id, wz_id))
        conn.execute("UPDATE WZ SET Status='invoiced' WHERE WZ_ID=?", (wz_id,))
    conn.commit()
    conn.close()
    # Auto-generate payment document
    desc = f"Payment for {number}"
    if payment_method == "cash":
        create_kp(customer_id=customer_id, fv_id=fv_id, amount=total, description=desc)
    elif payment_method == "bank":
        create_bank_entry(
            direction="in", customer_id=customer_id, fv_id=fv_id,
            amount=total, description=desc,
        )
    return fv_id


def mark_paid(fv_id: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE FV SET Status='paid' WHERE FV_ID=?", (fv_id,))
    conn.commit()
    conn.close()


def delete(pk) -> None:
    conn = get_connection()
    # Restore WZ docs to 'issued' status
    conn.execute(
        "UPDATE WZ SET Status='issued' WHERE WZ_ID IN (SELECT WZ_ID FROM FV_WZ WHERE FV_ID=?)",
        (pk,),
    )
    conn.execute("DELETE FROM FV WHERE FV_ID=?", (pk,))
    conn.commit()
    conn.close()
