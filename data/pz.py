from __future__ import annotations
"""data/pz.py — PZ (Przyjęcie Zewnętrzne) data access."""
from db import get_connection, next_doc_number
from data.products import apply_stock_delta


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.PZ_ID, p.PZ_Number, p.PZ_Date, s.CompanyName AS Supplier,
                  p.Status,
                  COALESCE(SUM(pi.UnitCost * pi.Quantity), 0.0) AS TotalCost
           FROM PZ p
           LEFT JOIN Suppliers s ON p.SupplierID = s.SupplierID
           LEFT JOIN PZ_Items pi ON p.PZ_ID = pi.PZ_ID
           GROUP BY p.PZ_ID
           ORDER BY p.PZ_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.PZ_ID, p.PZ_Number, p.PZ_Date, s.CompanyName AS Supplier,
                  p.Status,
                  COALESCE(SUM(pi.UnitCost * pi.Quantity), 0.0) AS TotalCost
           FROM PZ p
           LEFT JOIN Suppliers s ON p.SupplierID = s.SupplierID
           LEFT JOIN PZ_Items pi ON p.PZ_ID = pi.PZ_ID
           WHERE p.PZ_Number LIKE ? OR s.CompanyName LIKE ?
           GROUP BY p.PZ_ID
           ORDER BY p.PZ_ID DESC""",
        (like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT p.*, s.CompanyName
           FROM PZ p
           LEFT JOIN Suppliers s ON p.SupplierID = s.SupplierID
           WHERE p.PZ_ID = ?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_items(pz_id) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT pi.ProductID, pr.ProductName, pi.Quantity, pi.UnitCost,
                  pi.UnitCost * pi.Quantity AS LineTotal
           FROM PZ_Items pi
           JOIN Products pr ON pi.ProductID = pr.ProductID
           WHERE pi.PZ_ID = ?
           ORDER BY pr.ProductName""",
        (pz_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_draft(supplier_id: int, pz_date: str, supplier_doc_ref: str = "",
                 payment_method: str = "", notes: str = "") -> int:
    """Create PZ document in 'draft' status. Returns PZ_ID."""
    conn = get_connection()
    number = next_doc_number("PZ", conn)
    cur = conn.execute(
        "INSERT INTO PZ (PZ_Number, SupplierID, SupplierDocRef, PZ_Date, Status, PaymentMethod, Notes) "
        "VALUES (?,?,?,?,'draft',?,?)",
        (number, supplier_id, supplier_doc_ref or None, pz_date,
         payment_method or None, notes or None),
    )
    pz_id = cur.lastrowid
    conn.commit()
    conn.close()
    return pz_id


def add_item(pz_id: int, product_id: int, quantity: int, unit_cost: float) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO PZ_Items (PZ_ID, ProductID, Quantity, UnitCost) VALUES (?,?,?,?)",
        (pz_id, product_id, quantity, unit_cost),
    )
    conn.commit()
    conn.close()


def remove_item(pz_id: int, product_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "DELETE FROM PZ_Items WHERE PZ_ID=? AND ProductID=?", (pz_id, product_id)
    )
    conn.commit()
    conn.close()


def receive(pz_id: int) -> None:
    """Set PZ status to 'received', increment stock, auto-generate payment doc."""
    from data.kassa import create_kw
    from data.bank import create_bank_entry
    conn = get_connection()
    pz = conn.execute(
        "SELECT Status, SupplierID, PaymentMethod, PZ_Number FROM PZ WHERE PZ_ID=?",
        (pz_id,),
    ).fetchone()
    if not pz:
        conn.close()
        raise ValueError(f"PZ #{pz_id} not found.")
    if pz[0] != "draft":
        conn.close()
        raise ValueError(f"PZ #{pz_id} is already {pz[0]}.")
    items = conn.execute(
        "SELECT ProductID, Quantity, UnitCost FROM PZ_Items WHERE PZ_ID=?", (pz_id,)
    ).fetchall()
    if not items:
        conn.close()
        raise ValueError("Cannot receive a PZ with no items.")
    total = sum(r[1] * r[2] for r in items)
    for row in items:
        apply_stock_delta(row[0], row[1], conn)
    conn.execute(
        "UPDATE PZ SET Status='received' WHERE PZ_ID=?", (pz_id,)
    )
    conn.commit()
    supplier_id = pz[1]
    payment_method = pz[2]
    pz_number = pz[3]
    conn.close()
    # Auto-generate payment document
    desc = f"Payment for {pz_number}"
    if payment_method == "cash":
        create_kw(supplier_id=supplier_id, pz_id=pz_id, amount=total, description=desc)
    elif payment_method == "bank":
        create_bank_entry(
            direction="out", supplier_id=supplier_id, pz_id=pz_id,
            amount=total, description=desc,
        )


def delete(pk) -> None:
    conn = get_connection()
    pz = conn.execute("SELECT Status FROM PZ WHERE PZ_ID=?", (pk,)).fetchone()
    if pz and pz[0] == "received":
        raise ValueError("Cannot delete a received PZ.")
    conn.execute("DELETE FROM PZ WHERE PZ_ID=?", (pk,))
    conn.commit()
    conn.close()
