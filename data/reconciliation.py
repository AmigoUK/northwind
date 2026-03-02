from __future__ import annotations
"""data/reconciliation.py — AR/AP reconciliation queries and allocation logic."""
from db import get_connection


# ── AR — Accounts Receivable ──────────────────────────────────────────────────

def fetch_customer_statement(customer_id: str) -> list[dict]:
    """Unified chronological ledger for one customer.

    Each dict has: date, doc_type, doc_number, description, debit, credit,
    allocated (bool), doc_id, balance (running, added in Python).
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT date, doc_type, doc_number, description, debit, credit, allocated, doc_id
        FROM (
            SELECT INV_Date   AS date, 'INV'   AS doc_type, INV_Number AS doc_number,
                   COALESCE(Notes, '') AS description,
                   COALESCE(TotalNet, 0) AS debit, 0.0 AS credit,
                   1 AS allocated, INV_ID AS doc_id
            FROM INV
            WHERE CustomerID = ?
            UNION ALL
            SELECT CR_Date    AS date, 'CR'    AS doc_type, CR_Number  AS doc_number,
                   COALESCE(Description, '') AS description,
                   0.0 AS debit, COALESCE(Amount, 0) AS credit,
                   CASE WHEN INV_ID IS NOT NULL THEN 1 ELSE 0 END AS allocated,
                   CR_ID AS doc_id
            FROM CR
            WHERE CustomerID = ?
            UNION ALL
            SELECT Entry_Date AS date, 'BankIN' AS doc_type, Entry_Number AS doc_number,
                   COALESCE(Description, '') AS description,
                   0.0 AS debit, COALESCE(Amount, 0) AS credit,
                   CASE WHEN INV_ID IS NOT NULL THEN 1 ELSE 0 END AS allocated,
                   Entry_ID AS doc_id
            FROM BankEntry
            WHERE Direction = 'in' AND CustomerID = ?
            UNION ALL
            SELECT CN_Date    AS date, 'CN'    AS doc_type, CN_Number  AS doc_number,
                   COALESCE(Reason, '') AS description,
                   0.0 AS debit, ABS(COALESCE(TotalCorrection, 0)) AS credit,
                   1 AS allocated, CN_ID AS doc_id
            FROM CN
            WHERE CustomerID = ?
        )
        ORDER BY date ASC, doc_type ASC
        """,
        (customer_id, customer_id, customer_id, customer_id),
    ).fetchall()
    conn.close()

    result = []
    balance = 0.0
    for r in rows:
        balance += r[4] - r[5]   # debit increases owed, credit decreases
        result.append({
            "date":        r[0],
            "doc_type":    r[1],
            "doc_number":  r[2],
            "description": r[3],
            "debit":       r[4],
            "credit":      r[5],
            "allocated":   bool(r[6]),
            "doc_id":      r[7],
            "balance":     balance,
        })
    return result


def fetch_ar_aging() -> list[dict]:
    """Multi-customer aging. One row per customer with open/partial INVs.

    Columns: CustomerID, CompanyName, current_amt, d1_30, d31_60, d61_90,
             d90plus, total_outstanding.
    Only INVs with Status IN ('issued','partial') and DueDate IS NOT NULL.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT c.CustomerID, c.CompanyName,
               COALESCE(SUM(CASE
                   WHEN julianday('now') - julianday(i.DueDate) <= 0
                   THEN i.TotalNet - COALESCE(i.PaidAmount, 0) ELSE 0 END), 0) AS current_amt,
               COALESCE(SUM(CASE
                   WHEN julianday('now') - julianday(i.DueDate) BETWEEN 1  AND 30
                   THEN i.TotalNet - COALESCE(i.PaidAmount, 0) ELSE 0 END), 0) AS d1_30,
               COALESCE(SUM(CASE
                   WHEN julianday('now') - julianday(i.DueDate) BETWEEN 31 AND 60
                   THEN i.TotalNet - COALESCE(i.PaidAmount, 0) ELSE 0 END), 0) AS d31_60,
               COALESCE(SUM(CASE
                   WHEN julianday('now') - julianday(i.DueDate) BETWEEN 61 AND 90
                   THEN i.TotalNet - COALESCE(i.PaidAmount, 0) ELSE 0 END), 0) AS d61_90,
               COALESCE(SUM(CASE
                   WHEN julianday('now') - julianday(i.DueDate) > 90
                   THEN i.TotalNet - COALESCE(i.PaidAmount, 0) ELSE 0 END), 0) AS d90plus,
               COALESCE(SUM(i.TotalNet - COALESCE(i.PaidAmount, 0)), 0) AS total_outstanding
        FROM INV i
        JOIN Customers c ON i.CustomerID = c.CustomerID
        WHERE i.Status IN ('issued', 'partial') AND i.DueDate IS NOT NULL
        GROUP BY c.CustomerID, c.CompanyName
        ORDER BY total_outstanding DESC
        """,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_all_unpaid_inv(customer_id: str | None = None) -> list[dict]:
    """Return all unpaid/partial INVs across all customers, optionally filtered by customer_id."""
    conn = get_connection()
    sql = """
        SELECT i.INV_ID, i.INV_Number, i.INV_Date, i.DueDate,
               c.CompanyName AS CustomerName, i.CustomerID,
               i.TotalNet,
               COALESCE(i.PaidAmount, 0) AS PaidAmount,
               i.TotalNet - COALESCE(i.PaidAmount, 0) AS Outstanding,
               i.Status,
               CAST(
                   CASE WHEN i.DueDate IS NOT NULL
                        THEN MAX(0, julianday('now') - julianday(i.DueDate))
                        ELSE 0
                   END AS INTEGER
               ) AS DaysOverdue
        FROM INV i
        JOIN Customers c ON i.CustomerID = c.CustomerID
        WHERE i.Status IN ('issued', 'partial')
    """
    params: list = []
    if customer_id is not None:
        sql += " AND i.CustomerID = ?"
        params.append(customer_id)
    sql += " ORDER BY i.DueDate ASC, Outstanding DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    keys = ["inv_id", "inv_number", "date", "due_date", "customer_name", "customer_id",
            "total", "paid", "outstanding", "status", "days_overdue"]
    return [dict(zip(keys, r)) for r in rows]


def fetch_all_unpaid_gr(supplier_id: int | None = None) -> list[dict]:
    """Return received GRs with no allocated payment, optionally filtered by supplier_id."""
    conn = get_connection()
    sql = """
        SELECT g.GR_ID, g.GR_Number, g.GR_Date,
               s.CompanyName AS SupplierName, g.SupplierID,
               COALESCE(SUM(gi.Quantity * gi.UnitCost), 0) AS TotalCost
        FROM GR g
        JOIN Suppliers s ON g.SupplierID = s.SupplierID
        LEFT JOIN GR_Items gi ON g.GR_ID = gi.GR_ID
        WHERE g.Status = 'received'
          AND NOT EXISTS (
              SELECT 1 FROM CP WHERE CP.GR_ID = g.GR_ID
              UNION ALL
              SELECT 1 FROM BankEntry
              WHERE BankEntry.GR_ID = g.GR_ID AND BankEntry.Direction = 'out'
          )
    """
    params: list = []
    if supplier_id is not None:
        sql += " AND g.SupplierID = ?"
        params.append(supplier_id)
    sql += " GROUP BY g.GR_ID ORDER BY g.GR_Date ASC, TotalCost DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    keys = ["gr_id", "gr_number", "date", "supplier_name", "supplier_id", "total_cost"]
    return [dict(zip(keys, r)) for r in rows]


def fetch_unallocated_cr(customer_id: str | None = None) -> list[dict]:
    """CR entries with INV_ID IS NULL, optionally filtered by customer."""
    conn = get_connection()
    if customer_id is not None:
        rows = conn.execute(
            "SELECT CR_ID, CR_Number, CR_Date, CustomerID, Amount, Description "
            "FROM CR WHERE INV_ID IS NULL AND CustomerID = ? ORDER BY CR_Date",
            (customer_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT CR_ID, CR_Number, CR_Date, CustomerID, Amount, Description "
            "FROM CR WHERE INV_ID IS NULL ORDER BY CR_Date",
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_unallocated_bank_in(customer_id: str | None = None) -> list[dict]:
    """BankEntry Direction='in' with INV_ID IS NULL, optionally filtered by customer."""
    conn = get_connection()
    if customer_id is not None:
        rows = conn.execute(
            "SELECT Entry_ID, Entry_Number, Entry_Date, CustomerID, Amount, Description "
            "FROM BankEntry WHERE Direction='in' AND INV_ID IS NULL AND CustomerID = ? "
            "ORDER BY Entry_Date",
            (customer_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT Entry_ID, Entry_Number, Entry_Date, CustomerID, Amount, Description "
            "FROM BankEntry WHERE Direction='in' AND INV_ID IS NULL ORDER BY Entry_Date",
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── AP — Accounts Payable ─────────────────────────────────────────────────────

def fetch_supplier_statement(supplier_id: int) -> list[dict]:
    """Unified chronological ledger for one supplier.

    doc_types: 'GR' (debit), 'CP' (credit), 'BankOUT' (credit).
    Only GRs with Status='received' are included as payables.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT date, doc_type, doc_number, description, debit, credit, allocated, doc_id
        FROM (
            SELECT g.GR_Date   AS date, 'GR' AS doc_type, g.GR_Number AS doc_number,
                   COALESCE(g.Notes, '') AS description,
                   COALESCE(SUM(gi.Quantity * gi.UnitCost), 0) AS debit,
                   0.0 AS credit,
                   1 AS allocated, g.GR_ID AS doc_id
            FROM GR g
            LEFT JOIN GR_Items gi ON g.GR_ID = gi.GR_ID
            WHERE g.SupplierID = ? AND g.Status = 'received'
            GROUP BY g.GR_ID
            UNION ALL
            SELECT CP_Date    AS date, 'CP'     AS doc_type, CP_Number  AS doc_number,
                   COALESCE(Description, '') AS description,
                   0.0 AS debit, COALESCE(Amount, 0) AS credit,
                   CASE WHEN GR_ID IS NOT NULL THEN 1 ELSE 0 END AS allocated,
                   CP_ID AS doc_id
            FROM CP
            WHERE SupplierID = ?
            UNION ALL
            SELECT Entry_Date AS date, 'BankOUT' AS doc_type, Entry_Number AS doc_number,
                   COALESCE(Description, '') AS description,
                   0.0 AS debit, COALESCE(Amount, 0) AS credit,
                   CASE WHEN GR_ID IS NOT NULL THEN 1 ELSE 0 END AS allocated,
                   Entry_ID AS doc_id
            FROM BankEntry
            WHERE Direction = 'out' AND SupplierID = ?
        )
        ORDER BY date ASC, doc_type ASC
        """,
        (supplier_id, supplier_id, supplier_id),
    ).fetchall()
    conn.close()

    result = []
    balance = 0.0
    for r in rows:
        balance += r[4] - r[5]
        result.append({
            "date":        r[0],
            "doc_type":    r[1],
            "doc_number":  r[2],
            "description": r[3],
            "debit":       r[4],
            "credit":      r[5],
            "allocated":   bool(r[6]),
            "doc_id":      r[7],
            "balance":     balance,
        })
    return result


def fetch_unallocated_cp(supplier_id: int | None = None) -> list[dict]:
    """CP entries with GR_ID IS NULL, optionally filtered by supplier."""
    conn = get_connection()
    if supplier_id is not None:
        rows = conn.execute(
            "SELECT CP_ID, CP_Number, CP_Date, SupplierID, Amount, Description "
            "FROM CP WHERE GR_ID IS NULL AND SupplierID = ? ORDER BY CP_Date",
            (supplier_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT CP_ID, CP_Number, CP_Date, SupplierID, Amount, Description "
            "FROM CP WHERE GR_ID IS NULL ORDER BY CP_Date",
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_unallocated_bank_out(supplier_id: int | None = None) -> list[dict]:
    """BankEntry Direction='out' with GR_ID IS NULL, optionally filtered by supplier."""
    conn = get_connection()
    if supplier_id is not None:
        rows = conn.execute(
            "SELECT Entry_ID, Entry_Number, Entry_Date, SupplierID, Amount, Description "
            "FROM BankEntry WHERE Direction='out' AND GR_ID IS NULL AND SupplierID = ? "
            "ORDER BY Entry_Date",
            (supplier_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT Entry_ID, Entry_Number, Entry_Date, SupplierID, Amount, Description "
            "FROM BankEntry WHERE Direction='out' AND GR_ID IS NULL ORDER BY Entry_Date",
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Allocation ────────────────────────────────────────────────────────────────

def allocate_payment_to_inv(doc_type: str, doc_id: int, inv_id: int) -> None:
    """Link an existing unallocated CR or BankEntry-in to an invoice.

    doc_type: 'cr' | 'bank'
    1. Fetch payment amount
    2. Guard: raise ValueError if already allocated
    3. UPDATE CR.INV_ID or BankEntry.INV_ID
    4. UPDATE INV.PaidAmount += amount
    5. Recalculate INV.Status
    """
    from data.inv import _recalc_inv_status
    conn = get_connection()
    try:
        if doc_type == "cr":
            row = conn.execute(
                "SELECT Amount, INV_ID FROM CR WHERE CR_ID=?", (doc_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"CR #{doc_id} not found.")
            amount, existing_inv_id = row[0], row[1]
            if existing_inv_id is not None:
                raise ValueError(f"CR #{doc_id} is already allocated to INV #{existing_inv_id}.")
            conn.execute("UPDATE CR SET INV_ID=? WHERE CR_ID=?", (inv_id, doc_id))
        elif doc_type == "bank":
            row = conn.execute(
                "SELECT Amount, INV_ID FROM BankEntry WHERE Entry_ID=?", (doc_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"BankEntry #{doc_id} not found.")
            amount, existing_inv_id = row[0], row[1]
            if existing_inv_id is not None:
                raise ValueError(
                    f"BankEntry #{doc_id} is already allocated to INV #{existing_inv_id}."
                )
            conn.execute(
                "UPDATE BankEntry SET INV_ID=? WHERE Entry_ID=?", (inv_id, doc_id)
            )
        else:
            raise ValueError(f"Unknown doc_type '{doc_type}'. Use 'cr' or 'bank'.")

        conn.execute(
            "UPDATE INV SET PaidAmount = COALESCE(PaidAmount, 0) + ? WHERE INV_ID=?",
            (amount, inv_id),
        )
        _recalc_inv_status(inv_id, conn)
        conn.commit()
    finally:
        conn.close()


def allocate_payment_to_gr(doc_type: str, doc_id: int, gr_id: int) -> None:
    """Link an existing unallocated CP or BankEntry-out to a GR.

    doc_type: 'cp' | 'bank'
    GR has no payable-tracking field, so no side-effect on GR itself.
    """
    conn = get_connection()
    try:
        if doc_type == "cp":
            row = conn.execute(
                "SELECT GR_ID FROM CP WHERE CP_ID=?", (doc_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"CP #{doc_id} not found.")
            if row[0] is not None:
                raise ValueError(f"CP #{doc_id} is already allocated to GR #{row[0]}.")
            conn.execute("UPDATE CP SET GR_ID=? WHERE CP_ID=?", (gr_id, doc_id))
        elif doc_type == "bank":
            row = conn.execute(
                "SELECT GR_ID FROM BankEntry WHERE Entry_ID=?", (doc_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"BankEntry #{doc_id} not found.")
            if row[0] is not None:
                raise ValueError(
                    f"BankEntry #{doc_id} is already allocated to GR #{row[0]}."
                )
            conn.execute(
                "UPDATE BankEntry SET GR_ID=? WHERE Entry_ID=?", (gr_id, doc_id)
            )
        else:
            raise ValueError(f"Unknown doc_type '{doc_type}'. Use 'cp' or 'bank'.")

        conn.commit()
    finally:
        conn.close()
