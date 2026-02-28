from __future__ import annotations
"""data/si_so.py — SI (Stock Issue) and SO (Stock Out) data access."""
from db import get_connection, next_doc_number
from data.products import apply_stock_delta


# ── SI ────────────────────────────────────────────────────────────────────────

def fetch_all_si() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.SI_ID, p.SI_Number, p.SI_Date, p.Reason,
                  COALESCE(SUM(pi.Quantity), 0) AS TotalQty
           FROM SI p
           LEFT JOIN SI_Items pi ON p.SI_ID = pi.SI_ID
           GROUP BY p.SI_ID
           ORDER BY p.SI_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_si_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM SI WHERE SI_ID=?", (pk,)).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_si_items(si_id) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT pi.ProductID, p.ProductName, pi.Quantity
           FROM SI_Items pi
           JOIN Products p ON pi.ProductID = p.ProductID
           WHERE pi.SI_ID = ?
           ORDER BY p.ProductName""",
        (si_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_si(si_date: str, reason: str = "", notes: str = "",
              items: list[dict] | None = None) -> int:
    """Create SI and immediately apply stock increase. Returns SI_ID."""
    conn = get_connection()
    number = next_doc_number("SI", conn)
    cur = conn.execute(
        "INSERT INTO SI (SI_Number, SI_Date, Reason, Notes) VALUES (?,?,?,?)",
        (number, si_date, reason or None, notes or None),
    )
    si_id = cur.lastrowid
    for item in (items or []):
        conn.execute(
            "INSERT INTO SI_Items (SI_ID, ProductID, Quantity) VALUES (?,?,?)",
            (si_id, item["product_id"], item["quantity"]),
        )
        apply_stock_delta(item["product_id"], item["quantity"], conn)
    conn.commit()
    conn.close()
    return si_id


def delete_si(pk) -> None:
    from data.delete_guards import can_delete_si, before_delete_si
    ok, reasons = can_delete_si(pk)
    if not ok:
        raise ValueError("Cannot delete: " + "; ".join(reasons))
    before_delete_si(pk)  # reverse stock increases
    conn = get_connection()
    conn.execute("DELETE FROM SI WHERE SI_ID=?", (pk,))
    conn.commit()
    conn.close()


# ── SO ────────────────────────────────────────────────────────────────────────

def fetch_all_so() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT r.SO_ID, r.SO_Number, r.SO_Date, r.Reason,
                  COALESCE(SUM(ri.Quantity), 0) AS TotalQty
           FROM SO r
           LEFT JOIN SO_Items ri ON r.SO_ID = ri.SO_ID
           GROUP BY r.SO_ID
           ORDER BY r.SO_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_so_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM SO WHERE SO_ID=?", (pk,)).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_so_items(so_id) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT ri.ProductID, p.ProductName, ri.Quantity
           FROM SO_Items ri
           JOIN Products p ON ri.ProductID = p.ProductID
           WHERE ri.SO_ID = ?
           ORDER BY p.ProductName""",
        (so_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_so(so_date: str, reason: str = "", notes: str = "",
              items: list[dict] | None = None) -> int:
    """Create SO and immediately apply stock decrease. Returns SO_ID."""
    conn = get_connection()
    number = next_doc_number("SO", conn)
    cur = conn.execute(
        "INSERT INTO SO (SO_Number, SO_Date, Reason, Notes) VALUES (?,?,?,?)",
        (number, so_date, reason or None, notes or None),
    )
    so_id = cur.lastrowid
    for item in (items or []):
        conn.execute(
            "INSERT INTO SO_Items (SO_ID, ProductID, Quantity) VALUES (?,?,?)",
            (so_id, item["product_id"], item["quantity"]),
        )
        apply_stock_delta(item["product_id"], -item["quantity"], conn)
    conn.commit()
    conn.close()
    return so_id


def delete_so(pk) -> None:
    from data.delete_guards import before_delete_so
    before_delete_so(pk)  # reverse stock decreases
    conn = get_connection()
    conn.execute("DELETE FROM SO WHERE SO_ID=?", (pk,))
    conn.commit()
    conn.close()


# ── Audit trail (no stock delta) ──────────────────────────────────────────────

def record_stock_audit(doc_type: str, product_id: int, quantity: int,
                       reason: str = "Stock correction") -> int:
    """Insert SI or SO header + item for audit trail. Does NOT adjust UnitsInStock."""
    from datetime import date
    conn = get_connection()
    today = str(date.today())
    if doc_type == "SI":
        number = next_doc_number("SI", conn)
        cur = conn.execute(
            "INSERT INTO SI (SI_Number, SI_Date, Reason) VALUES (?,?,?)",
            (number, today, reason),
        )
        doc_id = cur.lastrowid
        conn.execute(
            "INSERT INTO SI_Items (SI_ID, ProductID, Quantity) VALUES (?,?,?)",
            (doc_id, product_id, quantity),
        )
    else:  # SO
        number = next_doc_number("SO", conn)
        cur = conn.execute(
            "INSERT INTO SO (SO_Number, SO_Date, Reason) VALUES (?,?,?)",
            (number, today, reason),
        )
        doc_id = cur.lastrowid
        conn.execute(
            "INSERT INTO SO_Items (SO_ID, ProductID, Quantity) VALUES (?,?,?)",
            (doc_id, product_id, quantity),
        )
    conn.commit()
    conn.close()
    return doc_id
