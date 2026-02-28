from __future__ import annotations
"""data/cash.py — CR (Cash Receipt) and CP (Cash Payment) data access."""
from db import get_connection, next_doc_number


# ── CR (Cash in) ──────────────────────────────────────────────────────────────

def fetch_all_cr() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT k.CR_ID, k.CR_Number, k.CR_Date,
                  c.CompanyName AS Customer, k.Amount, k.Description
           FROM CR k
           LEFT JOIN Customers c ON k.CustomerID = c.CustomerID
           ORDER BY k.CR_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_cr_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT k.*, c.CompanyName
           FROM CR k
           LEFT JOIN Customers c ON k.CustomerID = c.CustomerID
           WHERE k.CR_ID=?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_cr(customer_id: str | None, inv_id: int | None,
              amount: float, description: str = "") -> int:
    """Create a CR cash receipt. Returns CR_ID."""
    from datetime import date
    conn = get_connection()
    number = next_doc_number("CR", conn)
    cur = conn.execute(
        "INSERT INTO CR (CR_Number, CR_Date, CustomerID, INV_ID, Amount, Description) "
        "VALUES (?,?,?,?,?,?)",
        (number, str(date.today()), customer_id or None, inv_id or None,
         amount, description or None),
    )
    cr_id = cur.lastrowid
    conn.commit()
    conn.close()
    return cr_id


def cash_balance_cr() -> float:
    conn = get_connection()
    val = conn.execute("SELECT COALESCE(SUM(Amount), 0) FROM CR").fetchone()[0]
    conn.close()
    return val


def delete_cr(pk) -> None:
    from data.delete_guards import before_delete_cr
    before_delete_cr(pk)  # decrement INV.PaidAmount if linked
    conn = get_connection()
    conn.execute("DELETE FROM CR WHERE CR_ID=?", (pk,))
    conn.commit()
    conn.close()


# ── CP (Cash out) ─────────────────────────────────────────────────────────────

def fetch_all_cp() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT k.CP_ID, k.CP_Number, k.CP_Date,
                  s.CompanyName AS Supplier, k.Amount, k.Description
           FROM CP k
           LEFT JOIN Suppliers s ON k.SupplierID = s.SupplierID
           ORDER BY k.CP_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_cp_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT k.*, s.CompanyName
           FROM CP k
           LEFT JOIN Suppliers s ON k.SupplierID = s.SupplierID
           WHERE k.CP_ID=?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_cp(supplier_id: int | None, gr_id: int | None,
              amount: float, description: str = "") -> int:
    """Create a CP cash payment. Returns CP_ID."""
    from datetime import date
    conn = get_connection()
    number = next_doc_number("CP", conn)
    cur = conn.execute(
        "INSERT INTO CP (CP_Number, CP_Date, SupplierID, GR_ID, Amount, Description) "
        "VALUES (?,?,?,?,?,?)",
        (number, str(date.today()), supplier_id or None, gr_id or None,
         amount, description or None),
    )
    cp_id = cur.lastrowid
    conn.commit()
    conn.close()
    return cp_id


def cash_balance_cp() -> float:
    conn = get_connection()
    val = conn.execute("SELECT COALESCE(SUM(Amount), 0) FROM CP").fetchone()[0]
    conn.close()
    return val


def delete_cp(pk) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM CP WHERE CP_ID=?", (pk,))
    conn.commit()
    conn.close()  # CP has no side-effects to reverse


# ── Transfers ─────────────────────────────────────────────────────────────────

def transfer_to_bank(amount: float, description: str = "") -> tuple[int, int]:
    """Create CP (cash out) + BankEntry (in) atomically. Returns (cp_id, entry_id)."""
    from datetime import date
    conn = get_connection()
    today = str(date.today())
    desc = description or "Deposit to bank"

    cp_number   = next_doc_number("CP",   conn)
    bank_number = next_doc_number("Bank", conn)

    cp_desc   = f"{desc} → {bank_number}"
    bank_desc = f"{desc} ← {cp_number}"

    cur = conn.execute(
        "INSERT INTO CP (CP_Number, CP_Date, SupplierID, GR_ID, Amount, Description) "
        "VALUES (?,?,?,?,?,?)",
        (cp_number, today, None, None, amount, cp_desc),
    )
    cp_id = cur.lastrowid

    cur = conn.execute(
        "INSERT INTO BankEntry (Entry_Number, Entry_Date, Direction, CustomerID, "
        "SupplierID, INV_ID, GR_ID, Amount, Description) VALUES (?,?,?,?,?,?,?,?,?)",
        (bank_number, today, "in", None, None, None, None, amount, bank_desc),
    )
    entry_id = cur.lastrowid

    conn.commit()
    conn.close()
    return cp_id, entry_id
