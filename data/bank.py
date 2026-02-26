from __future__ import annotations
"""data/bank.py — BankEntry data access."""
from db import get_connection, next_doc_number


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT b.Entry_ID, b.Entry_Number, b.Entry_Date, b.Direction,
                  COALESCE(c.CompanyName, s.CompanyName, '') AS Counterparty,
                  b.Amount, b.Description
           FROM BankEntry b
           LEFT JOIN Customers c ON b.CustomerID = c.CustomerID
           LEFT JOIN Suppliers s ON b.SupplierID = s.SupplierID
           ORDER BY b.Entry_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        """SELECT b.Entry_ID, b.Entry_Number, b.Entry_Date, b.Direction,
                  COALESCE(c.CompanyName, s.CompanyName, '') AS Counterparty,
                  b.Amount, b.Description
           FROM BankEntry b
           LEFT JOIN Customers c ON b.CustomerID = c.CustomerID
           LEFT JOIN Suppliers s ON b.SupplierID = s.SupplierID
           WHERE b.Entry_Number LIKE ? OR b.Description LIKE ?
              OR c.CompanyName LIKE ? OR s.CompanyName LIKE ?
           ORDER BY b.Entry_ID DESC""",
        (like, like, like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT b.*,
                  c.CompanyName AS CustomerName, s.CompanyName AS SupplierName
           FROM BankEntry b
           LEFT JOIN Customers c ON b.CustomerID = c.CustomerID
           LEFT JOIN Suppliers s ON b.SupplierID = s.SupplierID
           WHERE b.Entry_ID=?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_bank_entry(direction: str, amount: float, description: str = "",
                      customer_id: str | None = None, supplier_id: int | None = None,
                      fv_id: int | None = None, pz_id: int | None = None) -> int:
    """Create a bank entry (in or out). Returns Entry_ID."""
    from datetime import date
    conn = get_connection()
    number = next_doc_number("Bank", conn)
    cur = conn.execute(
        "INSERT INTO BankEntry (Entry_Number, Entry_Date, Direction, CustomerID, "
        "SupplierID, FV_ID, PZ_ID, Amount, Description) VALUES (?,?,?,?,?,?,?,?,?)",
        (number, str(date.today()), direction, customer_id or None,
         supplier_id or None, fv_id or None, pz_id or None, amount, description or None),
    )
    entry_id = cur.lastrowid
    conn.commit()
    conn.close()
    return entry_id


def bank_balance() -> float:
    conn = get_connection()
    ins  = conn.execute(
        "SELECT COALESCE(SUM(Amount),0) FROM BankEntry WHERE Direction='in'"
    ).fetchone()[0]
    outs = conn.execute(
        "SELECT COALESCE(SUM(Amount),0) FROM BankEntry WHERE Direction='out'"
    ).fetchone()[0]
    conn.close()
    return ins - outs


def delete(pk) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM BankEntry WHERE Entry_ID=?", (pk,))
    conn.commit()
    conn.close()


# ── Transfers ─────────────────────────────────────────────────────────────────

def withdraw_to_kassa(amount: float, description: str = "") -> tuple[int, int]:
    """Create BankEntry (out) + KP (cash in) atomically. Returns (entry_id, kp_id)."""
    from datetime import date
    conn = get_connection()
    today = str(date.today())
    desc = description or "Cash withdrawal"

    bank_number = next_doc_number("Bank", conn)
    kp_number   = next_doc_number("KP",   conn)

    bank_desc = f"{desc} → {kp_number}"
    kp_desc   = f"{desc} ← {bank_number}"

    cur = conn.execute(
        "INSERT INTO BankEntry (Entry_Number, Entry_Date, Direction, CustomerID, "
        "SupplierID, FV_ID, PZ_ID, Amount, Description) VALUES (?,?,?,?,?,?,?,?,?)",
        (bank_number, today, "out", None, None, None, None, amount, bank_desc),
    )
    entry_id = cur.lastrowid

    cur = conn.execute(
        "INSERT INTO KP (KP_Number, KP_Date, CustomerID, FV_ID, Amount, Description) "
        "VALUES (?,?,?,?,?,?)",
        (kp_number, today, None, None, amount, kp_desc),
    )
    kp_id = cur.lastrowid

    conn.commit()
    conn.close()
    return entry_id, kp_id
