from __future__ import annotations
"""data/kassa.py — KP (Kasa Przyjmie) and KW (Kasa Wypłaci) data access."""
from db import get_connection, next_doc_number


# ── KP (Cash in) ──────────────────────────────────────────────────────────────

def fetch_all_kp() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT k.KP_ID, k.KP_Number, k.KP_Date,
                  c.CompanyName AS Customer, k.Amount, k.Description
           FROM KP k
           LEFT JOIN Customers c ON k.CustomerID = c.CustomerID
           ORDER BY k.KP_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_kp_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT k.*, c.CompanyName
           FROM KP k
           LEFT JOIN Customers c ON k.CustomerID = c.CustomerID
           WHERE k.KP_ID=?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_kp(customer_id: str | None, fv_id: int | None,
              amount: float, description: str = "") -> int:
    """Create a KP cash receipt. Returns KP_ID."""
    from datetime import date
    conn = get_connection()
    number = next_doc_number("KP", conn)
    cur = conn.execute(
        "INSERT INTO KP (KP_Number, KP_Date, CustomerID, FV_ID, Amount, Description) "
        "VALUES (?,?,?,?,?,?)",
        (number, str(date.today()), customer_id or None, fv_id or None,
         amount, description or None),
    )
    kp_id = cur.lastrowid
    conn.commit()
    conn.close()
    return kp_id


def cash_balance_kp() -> float:
    conn = get_connection()
    val = conn.execute("SELECT COALESCE(SUM(Amount), 0) FROM KP").fetchone()[0]
    conn.close()
    return val


def delete_kp(pk) -> None:
    from data.delete_guards import before_delete_kp
    before_delete_kp(pk)  # decrement FV.PaidAmount if linked
    conn = get_connection()
    conn.execute("DELETE FROM KP WHERE KP_ID=?", (pk,))
    conn.commit()
    conn.close()


# ── KW (Cash out) ─────────────────────────────────────────────────────────────

def fetch_all_kw() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT k.KW_ID, k.KW_Number, k.KW_Date,
                  s.CompanyName AS Supplier, k.Amount, k.Description
           FROM KW k
           LEFT JOIN Suppliers s ON k.SupplierID = s.SupplierID
           ORDER BY k.KW_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_kw_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT k.*, s.CompanyName
           FROM KW k
           LEFT JOIN Suppliers s ON k.SupplierID = s.SupplierID
           WHERE k.KW_ID=?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_kw(supplier_id: int | None, pz_id: int | None,
              amount: float, description: str = "") -> int:
    """Create a KW cash payment. Returns KW_ID."""
    from datetime import date
    conn = get_connection()
    number = next_doc_number("KW", conn)
    cur = conn.execute(
        "INSERT INTO KW (KW_Number, KW_Date, SupplierID, PZ_ID, Amount, Description) "
        "VALUES (?,?,?,?,?,?)",
        (number, str(date.today()), supplier_id or None, pz_id or None,
         amount, description or None),
    )
    kw_id = cur.lastrowid
    conn.commit()
    conn.close()
    return kw_id


def cash_balance_kw() -> float:
    conn = get_connection()
    val = conn.execute("SELECT COALESCE(SUM(Amount), 0) FROM KW").fetchone()[0]
    conn.close()
    return val


def delete_kw(pk) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM KW WHERE KW_ID=?", (pk,))
    conn.commit()
    conn.close()  # KW has no side-effects to reverse


# ── Transfers ─────────────────────────────────────────────────────────────────

def transfer_to_bank(amount: float, description: str = "") -> tuple[int, int]:
    """Create KW (cash out) + BankEntry (in) atomically. Returns (kw_id, entry_id)."""
    from datetime import date
    conn = get_connection()
    today = str(date.today())
    desc = description or "Deposit to bank"

    kw_number   = next_doc_number("KW",   conn)
    bank_number = next_doc_number("Bank", conn)

    kw_desc   = f"{desc} → {bank_number}"
    bank_desc = f"{desc} ← {kw_number}"

    cur = conn.execute(
        "INSERT INTO KW (KW_Number, KW_Date, SupplierID, PZ_ID, Amount, Description) "
        "VALUES (?,?,?,?,?,?)",
        (kw_number, today, None, None, amount, kw_desc),
    )
    kw_id = cur.lastrowid

    cur = conn.execute(
        "INSERT INTO BankEntry (Entry_Number, Entry_Date, Direction, CustomerID, "
        "SupplierID, FV_ID, PZ_ID, Amount, Description) VALUES (?,?,?,?,?,?,?,?,?)",
        (bank_number, today, "in", None, None, None, None, amount, bank_desc),
    )
    entry_id = cur.lastrowid

    conn.commit()
    conn.close()
    return kw_id, entry_id
