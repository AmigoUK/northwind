"""data/delete_guards.py — Centralized delete guards and side-effect handlers.

Each can_delete_<type>(pk) returns (bool, list[str]) — True if deletion is allowed,
with a list of human-readable reasons if not.

before_delete_<type>(pk) performs side-effects that must happen before the actual
DELETE statement (e.g., reversing payments, restoring stock).
"""
from __future__ import annotations

from db import get_connection


def _fmt_reasons(reasons: list[str], limit: int = 5) -> list[str]:
    """Truncate long reason lists with '...and N more'."""
    if len(reasons) <= limit:
        return reasons
    extra = len(reasons) - limit
    return reasons[:limit] + [f"...and {extra} more"]


# ── Document guards ───────────────────────────────────────────────────────────

def can_delete_order(pk) -> tuple[bool, list[str]]:
    conn = get_connection()
    reasons = []
    rows = conn.execute(
        "SELECT WZ_ID, WZ_Number FROM WZ WHERE OrderID=?", (pk,)
    ).fetchall()
    for r in rows:
        reasons.append(f"WZ {r['WZ_Number']} exists for this order")
    conn.close()
    return (len(reasons) == 0, _fmt_reasons(reasons))


def can_delete_wz(pk) -> tuple[bool, list[str]]:
    conn = get_connection()
    reasons = []
    wz = conn.execute("SELECT Status FROM WZ WHERE WZ_ID=?", (pk,)).fetchone()
    if not wz:
        conn.close()
        return (True, [])
    status = wz[0]
    if status in ("issued", "invoiced", "cancelled"):
        reasons.append(f"Cannot delete a WZ with status '{status}'")
    # Check FV_WZ junction
    fv_rows = conn.execute(
        "SELECT f.FV_Number FROM FV_WZ fw JOIN FV f ON fw.FV_ID=f.FV_ID WHERE fw.WZ_ID=?",
        (pk,),
    ).fetchall()
    for r in fv_rows:
        reasons.append(f"FV {r['FV_Number']} references this WZ")
    conn.close()
    return (len(reasons) == 0, _fmt_reasons(reasons))


def can_delete_fv(pk) -> tuple[bool, list[str]]:
    conn = get_connection()
    reasons = []
    # Check KP references
    kp_rows = conn.execute(
        "SELECT KP_Number, Amount FROM KP WHERE FV_ID=?", (pk,)
    ).fetchall()
    for r in kp_rows:
        reasons.append(f"KP {r['KP_Number']} (${r['Amount']:.2f}) references this invoice")
    # Check BankEntry references
    be_rows = conn.execute(
        "SELECT Entry_Number, Amount FROM BankEntry WHERE FV_ID=?", (pk,)
    ).fetchall()
    for r in be_rows:
        reasons.append(f"Bank {r['Entry_Number']} (${r['Amount']:.2f}) references this invoice")
    conn.close()
    return (len(reasons) == 0, _fmt_reasons(reasons))


def can_delete_pz(pk) -> tuple[bool, list[str]]:
    conn = get_connection()
    reasons = []
    pz = conn.execute("SELECT Status FROM PZ WHERE PZ_ID=?", (pk,)).fetchone()
    if not pz:
        conn.close()
        return (True, [])
    if pz[0] in ("received", "cancelled"):
        reasons.append(f"Cannot delete a PZ with status '{pz[0]}'")
    # Check KW references
    kw_rows = conn.execute(
        "SELECT KW_Number FROM KW WHERE PZ_ID=?", (pk,)
    ).fetchall()
    for r in kw_rows:
        reasons.append(f"KW {r['KW_Number']} references this PZ")
    # Check BankEntry references
    be_rows = conn.execute(
        "SELECT Entry_Number FROM BankEntry WHERE PZ_ID=?", (pk,)
    ).fetchall()
    for r in be_rows:
        reasons.append(f"Bank {r['Entry_Number']} references this PZ")
    conn.close()
    return (len(reasons) == 0, _fmt_reasons(reasons))


def can_delete_pw(pk) -> tuple[bool, list[str]]:
    """Block PW deletion if reversing stock would make any product negative."""
    conn = get_connection()
    reasons = []
    items = conn.execute(
        "SELECT pi.ProductID, pi.Quantity, p.ProductName, p.UnitsInStock "
        "FROM PW_Items pi JOIN Products p ON pi.ProductID=p.ProductID "
        "WHERE pi.PW_ID=?",
        (pk,),
    ).fetchall()
    for it in items:
        if it["UnitsInStock"] - it["Quantity"] < 0:
            reasons.append(
                f"Reversing '{it['ProductName']}' would result in negative stock "
                f"({it['UnitsInStock']} - {it['Quantity']})"
            )
    conn.close()
    return (len(reasons) == 0, _fmt_reasons(reasons))


# ── Side-effect handlers (call BEFORE the actual DELETE) ─────────────────────

def before_delete_fv(pk) -> None:
    """Restore linked WZ docs to 'issued' status (existing logic, now centralized)."""
    conn = get_connection()
    conn.execute(
        "UPDATE WZ SET Status='issued' WHERE WZ_ID IN "
        "(SELECT WZ_ID FROM FV_WZ WHERE FV_ID=?)",
        (pk,),
    )
    conn.commit()
    conn.close()


def before_delete_kp(pk) -> None:
    """Decrement FV.PaidAmount and recalculate FV.Status when KP is deleted."""
    conn = get_connection()
    kp = conn.execute("SELECT FV_ID, Amount FROM KP WHERE KP_ID=?", (pk,)).fetchone()
    if kp and kp["FV_ID"]:
        fv_id = kp["FV_ID"]
        amount = kp["Amount"]
        conn.execute(
            "UPDATE FV SET PaidAmount = MAX(PaidAmount - ?, 0) WHERE FV_ID=?",
            (amount, fv_id),
        )
        _recalc_fv_status(fv_id, conn)
    conn.commit()
    conn.close()


def before_delete_bank_entry(pk) -> None:
    """Decrement FV.PaidAmount when a BankEntry linked to an FV is deleted."""
    conn = get_connection()
    entry = conn.execute(
        "SELECT FV_ID, Amount, Direction FROM BankEntry WHERE Entry_ID=?", (pk,)
    ).fetchone()
    if entry and entry["FV_ID"] and entry["Direction"] == "in":
        fv_id = entry["FV_ID"]
        amount = entry["Amount"]
        conn.execute(
            "UPDATE FV SET PaidAmount = MAX(PaidAmount - ?, 0) WHERE FV_ID=?",
            (amount, fv_id),
        )
        _recalc_fv_status(fv_id, conn)
    conn.commit()
    conn.close()


def before_delete_pw(pk) -> None:
    """Reverse stock increases when PW is deleted."""
    from data.products import apply_stock_delta
    conn = get_connection()
    items = conn.execute(
        "SELECT ProductID, Quantity FROM PW_Items WHERE PW_ID=?", (pk,)
    ).fetchall()
    for it in items:
        apply_stock_delta(it["ProductID"], -it["Quantity"], conn)
    conn.commit()
    conn.close()


def before_delete_rw(pk) -> None:
    """Reverse stock decreases when RW is deleted."""
    from data.products import apply_stock_delta
    conn = get_connection()
    items = conn.execute(
        "SELECT ProductID, Quantity FROM RW_Items WHERE RW_ID=?", (pk,)
    ).fetchall()
    for it in items:
        apply_stock_delta(it["ProductID"], it["Quantity"], conn)
    conn.commit()
    conn.close()


# ── Master data guards ────────────────────────────────────────────────────────

def can_delete_product(pk) -> tuple[bool, list[str]]:
    conn = get_connection()
    reasons = []
    tables = [
        ("OrderDetails", "ProductID", "order detail(s)"),
        ("WZ_Items", "ProductID", "WZ item(s)"),
        ("PZ_Items", "ProductID", "PZ item(s)"),
        ("PW_Items", "ProductID", "PW item(s)"),
        ("RW_Items", "ProductID", "RW item(s)"),
    ]
    for table, col, label in tables:
        cnt = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {col}=?", (pk,)
        ).fetchone()[0]
        if cnt:
            reasons.append(f"Referenced by {cnt} {label}")
    conn.close()
    return (len(reasons) == 0, _fmt_reasons(reasons))


def can_delete_customer(pk) -> tuple[bool, list[str]]:
    conn = get_connection()
    reasons = []
    tables = [
        ("Orders", "CustomerID", "order(s)"),
        ("WZ", "CustomerID", "WZ document(s)"),
        ("FV", "CustomerID", "invoice(s)"),
        ("KP", "CustomerID", "KP receipt(s)"),
        ("BankEntry", "CustomerID", "bank entry(ies)"),
    ]
    for table, col, label in tables:
        cnt = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {col}=?", (pk,)
        ).fetchone()[0]
        if cnt:
            reasons.append(f"Referenced by {cnt} {label}")
    conn.close()
    return (len(reasons) == 0, _fmt_reasons(reasons))


def can_delete_supplier(pk) -> tuple[bool, list[str]]:
    conn = get_connection()
    reasons = []
    tables = [
        ("Products", "SupplierID", "product(s)"),
        ("PZ", "SupplierID", "PZ document(s)"),
        ("KW", "SupplierID", "KW payment(s)"),
        ("BankEntry", "SupplierID", "bank entry(ies)"),
    ]
    for table, col, label in tables:
        cnt = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {col}=?", (pk,)
        ).fetchone()[0]
        if cnt:
            reasons.append(f"Referenced by {cnt} {label}")
    conn.close()
    return (len(reasons) == 0, _fmt_reasons(reasons))


def can_delete_category(pk) -> tuple[bool, list[str]]:
    conn = get_connection()
    cnt = conn.execute(
        "SELECT COUNT(*) FROM Products WHERE CategoryID=?", (pk,)
    ).fetchone()[0]
    conn.close()
    if cnt:
        return (False, [f"Referenced by {cnt} product(s)"])
    return (True, [])


def can_delete_employee(pk) -> tuple[bool, list[str]]:
    conn = get_connection()
    reasons = []
    order_cnt = conn.execute(
        "SELECT COUNT(*) FROM Orders WHERE EmployeeID=?", (pk,)
    ).fetchone()[0]
    if order_cnt:
        reasons.append(f"Referenced by {order_cnt} order(s)")
    report_cnt = conn.execute(
        "SELECT COUNT(*) FROM Employees WHERE ReportsTo=?", (pk,)
    ).fetchone()[0]
    if report_cnt:
        reasons.append(f"{report_cnt} employee(s) report to this person")
    conn.close()
    return (len(reasons) == 0, _fmt_reasons(reasons))


def can_delete_shipper(pk) -> tuple[bool, list[str]]:
    conn = get_connection()
    cnt = conn.execute(
        "SELECT COUNT(*) FROM Orders WHERE ShipVia=?", (pk,)
    ).fetchone()[0]
    conn.close()
    if cnt:
        return (False, [f"Referenced by {cnt} order(s)"])
    return (True, [])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _recalc_fv_status(fv_id: int, conn) -> None:
    """Recalculate FV.Status based on current PaidAmount vs TotalNet."""
    row = conn.execute(
        "SELECT TotalNet, COALESCE(PaidAmount, 0) FROM FV WHERE FV_ID=?",
        (fv_id,),
    ).fetchone()
    if not row:
        return
    total, paid = row[0] or 0, row[1]
    if paid >= total and total > 0:
        status = "paid"
    elif paid > 0:
        status = "partial"
    else:
        status = "issued"
    conn.execute("UPDATE FV SET Status=? WHERE FV_ID=?", (status, fv_id))
