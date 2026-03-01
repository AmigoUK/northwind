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
                      inv_id: int | None = None, gr_id: int | None = None,
                      date_override: str | None = None) -> int:
    """Create a bank entry (in or out). Returns Entry_ID."""
    from datetime import date
    entry_date = date_override or str(date.today())
    year_override = int(entry_date[:4]) if date_override else None
    conn = get_connection()
    number = next_doc_number("Bank", conn, year_override=year_override)
    cur = conn.execute(
        "INSERT INTO BankEntry (Entry_Number, Entry_Date, Direction, CustomerID, "
        "SupplierID, INV_ID, GR_ID, Amount, Description) VALUES (?,?,?,?,?,?,?,?,?)",
        (number, entry_date, direction, customer_id or None,
         supplier_id or None, inv_id or None, gr_id or None, amount, description or None),
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
    from data.delete_guards import before_delete_bank_entry
    before_delete_bank_entry(pk)  # decrement INV.PaidAmount if linked
    conn = get_connection()
    conn.execute("DELETE FROM BankEntry WHERE Entry_ID=?", (pk,))
    conn.commit()
    conn.close()


# ── Transfers ─────────────────────────────────────────────────────────────────

def withdraw_to_cash(amount: float, description: str = "",
                     date_override: str | None = None) -> tuple[int, int]:
    """Create BankEntry (out) + CR (cash in) atomically. Returns (entry_id, cr_id)."""
    from datetime import date
    conn = get_connection()
    today = date_override or str(date.today())
    year_override = int(today[:4]) if date_override else None
    desc = description or "Cash withdrawal"

    bank_number = next_doc_number("Bank", conn, year_override=year_override)
    cr_number   = next_doc_number("CR",   conn, year_override=year_override)

    bank_desc = f"{desc} → {cr_number}"
    cr_desc   = f"{desc} ← {bank_number}"

    cur = conn.execute(
        "INSERT INTO BankEntry (Entry_Number, Entry_Date, Direction, CustomerID, "
        "SupplierID, INV_ID, GR_ID, Amount, Description) VALUES (?,?,?,?,?,?,?,?,?)",
        (bank_number, today, "out", None, None, None, None, amount, bank_desc),
    )
    entry_id = cur.lastrowid

    cur = conn.execute(
        "INSERT INTO CR (CR_Number, CR_Date, CustomerID, INV_ID, Amount, Description) "
        "VALUES (?,?,?,?,?,?)",
        (cr_number, today, None, None, amount, cr_desc),
    )
    cr_id = cur.lastrowid

    conn.commit()
    conn.close()
    return entry_id, cr_id
