from __future__ import annotations
"""data/pw_rw.py — PW (Przyjęcie Wewnętrzne) and RW (Rozchód Wewnętrzny) data access."""
from db import get_connection, next_doc_number
from data.products import apply_stock_delta


# ── PW ────────────────────────────────────────────────────────────────────────

def fetch_all_pw() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.PW_ID, p.PW_Number, p.PW_Date, p.Reason,
                  COALESCE(SUM(pi.Quantity), 0) AS TotalQty
           FROM PW p
           LEFT JOIN PW_Items pi ON p.PW_ID = pi.PW_ID
           GROUP BY p.PW_ID
           ORDER BY p.PW_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_pw_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM PW WHERE PW_ID=?", (pk,)).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_pw_items(pw_id) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT pi.ProductID, p.ProductName, pi.Quantity
           FROM PW_Items pi
           JOIN Products p ON pi.ProductID = p.ProductID
           WHERE pi.PW_ID = ?
           ORDER BY p.ProductName""",
        (pw_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_pw(pw_date: str, reason: str = "", notes: str = "",
              items: list[dict] | None = None) -> int:
    """Create PW and immediately apply stock increase. Returns PW_ID."""
    conn = get_connection()
    number = next_doc_number("PW", conn)
    cur = conn.execute(
        "INSERT INTO PW (PW_Number, PW_Date, Reason, Notes) VALUES (?,?,?,?)",
        (number, pw_date, reason or None, notes or None),
    )
    pw_id = cur.lastrowid
    for item in (items or []):
        conn.execute(
            "INSERT INTO PW_Items (PW_ID, ProductID, Quantity) VALUES (?,?,?)",
            (pw_id, item["product_id"], item["quantity"]),
        )
        apply_stock_delta(item["product_id"], item["quantity"], conn)
    conn.commit()
    conn.close()
    return pw_id


def delete_pw(pk) -> None:
    from data.delete_guards import can_delete_pw, before_delete_pw
    ok, reasons = can_delete_pw(pk)
    if not ok:
        raise ValueError("Cannot delete: " + "; ".join(reasons))
    before_delete_pw(pk)  # reverse stock increases
    conn = get_connection()
    conn.execute("DELETE FROM PW WHERE PW_ID=?", (pk,))
    conn.commit()
    conn.close()


# ── RW ────────────────────────────────────────────────────────────────────────

def fetch_all_rw() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT r.RW_ID, r.RW_Number, r.RW_Date, r.Reason,
                  COALESCE(SUM(ri.Quantity), 0) AS TotalQty
           FROM RW r
           LEFT JOIN RW_Items ri ON r.RW_ID = ri.RW_ID
           GROUP BY r.RW_ID
           ORDER BY r.RW_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_rw_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM RW WHERE RW_ID=?", (pk,)).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_rw_items(rw_id) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT ri.ProductID, p.ProductName, ri.Quantity
           FROM RW_Items ri
           JOIN Products p ON ri.ProductID = p.ProductID
           WHERE ri.RW_ID = ?
           ORDER BY p.ProductName""",
        (rw_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_rw(rw_date: str, reason: str = "", notes: str = "",
              items: list[dict] | None = None) -> int:
    """Create RW and immediately apply stock decrease. Returns RW_ID."""
    conn = get_connection()
    number = next_doc_number("RW", conn)
    cur = conn.execute(
        "INSERT INTO RW (RW_Number, RW_Date, Reason, Notes) VALUES (?,?,?,?)",
        (number, rw_date, reason or None, notes or None),
    )
    rw_id = cur.lastrowid
    for item in (items or []):
        conn.execute(
            "INSERT INTO RW_Items (RW_ID, ProductID, Quantity) VALUES (?,?,?)",
            (rw_id, item["product_id"], item["quantity"]),
        )
        apply_stock_delta(item["product_id"], -item["quantity"], conn)
    conn.commit()
    conn.close()
    return rw_id


def delete_rw(pk) -> None:
    from data.delete_guards import before_delete_rw
    before_delete_rw(pk)  # reverse stock decreases
    conn = get_connection()
    conn.execute("DELETE FROM RW WHERE RW_ID=?", (pk,))
    conn.commit()
    conn.close()


# ── Audit trail (no stock delta) ──────────────────────────────────────────────

def record_stock_audit(doc_type: str, product_id: int, quantity: int,
                       reason: str = "Stock correction") -> int:
    """Insert PW or RW header + item for audit trail. Does NOT adjust UnitsInStock."""
    from datetime import date
    conn = get_connection()
    today = str(date.today())
    if doc_type == "PW":
        number = next_doc_number("PW", conn)
        cur = conn.execute(
            "INSERT INTO PW (PW_Number, PW_Date, Reason) VALUES (?,?,?)",
            (number, today, reason),
        )
        doc_id = cur.lastrowid
        conn.execute(
            "INSERT INTO PW_Items (PW_ID, ProductID, Quantity) VALUES (?,?,?)",
            (doc_id, product_id, quantity),
        )
    else:  # RW
        number = next_doc_number("RW", conn)
        cur = conn.execute(
            "INSERT INTO RW (RW_Number, RW_Date, Reason) VALUES (?,?,?)",
            (number, today, reason),
        )
        doc_id = cur.lastrowid
        conn.execute(
            "INSERT INTO RW_Items (RW_ID, ProductID, Quantity) VALUES (?,?,?)",
            (doc_id, product_id, quantity),
        )
    conn.commit()
    conn.close()
    return doc_id
