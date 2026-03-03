from __future__ import annotations
"""data/gr.py — GR (Goods Receipt) data access."""
from db import get_connection, next_doc_number
from data.products import apply_stock_delta


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.GR_ID, p.GR_Number, p.GR_Date, s.CompanyName AS Supplier,
                  p.Status,
                  COALESCE(SUM(pi.UnitCost * pi.Quantity), 0.0) AS TotalCost
           FROM GR p
           LEFT JOIN Suppliers s ON p.SupplierID = s.SupplierID
           LEFT JOIN GR_Items pi ON p.GR_ID = pi.GR_ID
           GROUP BY p.GR_ID
           ORDER BY p.GR_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.GR_ID, p.GR_Number, p.GR_Date, s.CompanyName AS Supplier,
                  p.Status,
                  COALESCE(SUM(pi.UnitCost * pi.Quantity), 0.0) AS TotalCost
           FROM GR p
           LEFT JOIN Suppliers s ON p.SupplierID = s.SupplierID
           LEFT JOIN GR_Items pi ON p.GR_ID = pi.GR_ID
           WHERE p.GR_Number LIKE ? OR s.CompanyName LIKE ?
           GROUP BY p.GR_ID
           ORDER BY p.GR_ID DESC""",
        (like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT p.*, s.CompanyName
           FROM GR p
           LEFT JOIN Suppliers s ON p.SupplierID = s.SupplierID
           WHERE p.GR_ID = ?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_items(gr_id) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT pi.ProductID, pr.ProductName, pi.Quantity, pi.UnitCost,
                  pi.UnitCost * pi.Quantity AS LineTotal
           FROM GR_Items pi
           JOIN Products pr ON pi.ProductID = pr.ProductID
           WHERE pi.GR_ID = ?
           ORDER BY pr.ProductName""",
        (gr_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_draft(supplier_id: int, gr_date: str, supplier_doc_ref: str = "",
                 payment_method: str = "", notes: str = "",
                 year_override: int | None = None) -> int:
    """Create GR document in 'draft' status. Returns GR_ID."""
    conn = get_connection()
    number = next_doc_number("GR", conn, year_override=year_override)
    cur = conn.execute(
        "INSERT INTO GR (GR_Number, SupplierID, SupplierDocRef, GR_Date, Status, PaymentMethod, Notes) "
        "VALUES (?,?,?,?,'draft',?,?)",
        (number, supplier_id, supplier_doc_ref or None, gr_date,
         payment_method or None, notes or None),
    )
    gr_id = cur.lastrowid
    conn.commit()
    conn.close()
    return gr_id


def add_item(gr_id: int, product_id: int, quantity: int, unit_cost: float) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO GR_Items (GR_ID, ProductID, Quantity, UnitCost) VALUES (?,?,?,?)",
        (gr_id, product_id, quantity, unit_cost),
    )
    conn.commit()
    conn.close()


def remove_item(gr_id: int, product_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "DELETE FROM GR_Items WHERE GR_ID=? AND ProductID=?", (gr_id, product_id)
    )
    conn.commit()
    conn.close()


def receive(gr_id: int, date_override: str | None = None) -> None:
    """Set GR status to 'received', increment stock, auto-generate payment doc."""
    from data.cash import create_cp
    from data.bank import create_bank_entry
    conn = get_connection()
    gr = conn.execute(
        "SELECT Status, SupplierID, PaymentMethod, GR_Number FROM GR WHERE GR_ID=?",
        (gr_id,),
    ).fetchone()
    if not gr:
        conn.close()
        raise ValueError(f"GR #{gr_id} not found.")
    if gr[0] != "draft":
        conn.close()
        raise ValueError(f"GR #{gr_id} is already {gr[0]}.")
    items = conn.execute(
        "SELECT ProductID, Quantity, UnitCost FROM GR_Items WHERE GR_ID=?", (gr_id,)
    ).fetchall()
    if not items:
        conn.close()
        raise ValueError("Cannot receive a GR with no items.")
    total = sum(r[1] * r[2] for r in items)
    for row in items:
        apply_stock_delta(row[0], row[1], conn)
    conn.execute(
        "UPDATE GR SET Status='received' WHERE GR_ID=?", (gr_id,)
    )
    conn.commit()
    supplier_id = gr[1]
    payment_method = gr[2]
    gr_number = gr[3]
    conn.close()
    # Auto-generate payment document
    desc = f"Payment for {gr_number}"
    if payment_method == "cash":
        from data.cash import get_cash_balance
        if get_cash_balance() < total:
            payment_method = "bank"  # insufficient cash — fall back to bank
    if payment_method == "cash":
        create_cp(supplier_id=supplier_id, gr_id=gr_id, amount=total,
                  description=desc, date_override=date_override)
    elif payment_method == "bank":
        create_bank_entry(
            direction="out", supplier_id=supplier_id, gr_id=gr_id,
            amount=total, description=desc, date_override=date_override,
        )


def cancel(gr_id: int, reason: str, user_id: int) -> None:
    """Cancel a received GR: reverse stock, mark as cancelled."""
    from datetime import datetime
    conn = get_connection()
    gr = conn.execute("SELECT Status FROM GR WHERE GR_ID=?", (gr_id,)).fetchone()
    if not gr:
        conn.close()
        raise ValueError(f"GR #{gr_id} not found.")
    status = gr[0]
    if status == "draft":
        conn.close()
        raise ValueError("Delete the draft instead of cancelling.")
    if status == "cancelled":
        conn.close()
        raise ValueError("GR is already cancelled.")
    if status != "received":
        conn.close()
        raise ValueError(f"Cannot cancel GR with status '{status}'.")
    # Reverse stock
    items = conn.execute(
        "SELECT ProductID, Quantity FROM GR_Items WHERE GR_ID=?", (gr_id,)
    ).fetchall()
    for it in items:
        apply_stock_delta(it["ProductID"], -it["Quantity"], conn)
    conn.execute(
        "UPDATE GR SET Status='cancelled', CancelledAt=?, CancelledBy=?, CancelReason=? "
        "WHERE GR_ID=?",
        (datetime.now().isoformat(), user_id, reason, gr_id),
    )
    conn.commit()
    conn.close()


def delete(pk) -> None:
    from data.delete_guards import can_delete_gr
    ok, reasons = can_delete_gr(pk)
    if not ok:
        raise ValueError("Cannot delete: " + "; ".join(reasons))
    conn = get_connection()
    conn.execute("DELETE FROM GR WHERE GR_ID=?", (pk,))
    conn.commit()
    conn.close()
