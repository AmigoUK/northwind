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
        "SELECT DN_ID, DN_Number FROM DN WHERE OrderID=?", (pk,)
    ).fetchall()
    for r in rows:
        reasons.append(f"DN {r['DN_Number']} exists for this order")
    conn.close()
    return (len(reasons) == 0, _fmt_reasons(reasons))


def can_delete_dn(pk) -> tuple[bool, list[str]]:
    conn = get_connection()
    reasons = []
    dn = conn.execute("SELECT Status FROM DN WHERE DN_ID=?", (pk,)).fetchone()
    if not dn:
        conn.close()
        return (True, [])
    status = dn[0]
    if status in ("issued", "invoiced", "cancelled"):
        reasons.append(f"Cannot delete a DN with status '{status}'")
    # Check INV_DN junction
    inv_rows = conn.execute(
        "SELECT f.INV_Number FROM INV_DN fw JOIN INV f ON fw.INV_ID=f.INV_ID WHERE fw.DN_ID=?",
        (pk,),
    ).fetchall()
    for r in inv_rows:
        reasons.append(f"INV {r['INV_Number']} references this DN")
    conn.close()
    return (len(reasons) == 0, _fmt_reasons(reasons))


def can_delete_inv(pk) -> tuple[bool, list[str]]:
    conn = get_connection()
    reasons = []
    # Check CR references
    cr_rows = conn.execute(
        "SELECT CR_Number, Amount FROM CR WHERE INV_ID=?", (pk,)
    ).fetchall()
    for r in cr_rows:
        reasons.append(f"CR {r['CR_Number']} (${r['Amount']:.2f}) references this invoice")
    # Check BankEntry references
    be_rows = conn.execute(
        "SELECT Entry_Number, Amount FROM BankEntry WHERE INV_ID=?", (pk,)
    ).fetchall()
    for r in be_rows:
        reasons.append(f"Bank {r['Entry_Number']} (${r['Amount']:.2f}) references this invoice")
    conn.close()
    return (len(reasons) == 0, _fmt_reasons(reasons))


def can_delete_gr(pk) -> tuple[bool, list[str]]:
    conn = get_connection()
    reasons = []
    gr = conn.execute("SELECT Status FROM GR WHERE GR_ID=?", (pk,)).fetchone()
    if not gr:
        conn.close()
        return (True, [])
    if gr[0] in ("received", "cancelled"):
        reasons.append(f"Cannot delete a GR with status '{gr[0]}'")
    # Check CP references
    cp_rows = conn.execute(
        "SELECT CP_Number FROM CP WHERE GR_ID=?", (pk,)
    ).fetchall()
    for r in cp_rows:
        reasons.append(f"CP {r['CP_Number']} references this GR")
    # Check BankEntry references
    be_rows = conn.execute(
        "SELECT Entry_Number FROM BankEntry WHERE GR_ID=?", (pk,)
    ).fetchall()
    for r in be_rows:
        reasons.append(f"Bank {r['Entry_Number']} references this GR")
    conn.close()
    return (len(reasons) == 0, _fmt_reasons(reasons))


def can_delete_si(pk) -> tuple[bool, list[str]]:
    """Block SI deletion if reversing stock would make any product negative."""
    conn = get_connection()
    reasons = []
    items = conn.execute(
        "SELECT pi.ProductID, pi.Quantity, p.ProductName, p.UnitsInStock "
        "FROM SI_Items pi JOIN Products p ON pi.ProductID=p.ProductID "
        "WHERE pi.SI_ID=?",
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

def before_delete_inv(pk) -> None:
    """Restore linked DN docs to 'issued' status (existing logic, now centralized)."""
    conn = get_connection()
    conn.execute(
        "UPDATE DN SET Status='issued' WHERE DN_ID IN "
        "(SELECT DN_ID FROM INV_DN WHERE INV_ID=?)",
        (pk,),
    )
    conn.commit()
    conn.close()


def before_delete_cr(pk) -> None:
    """Decrement INV.PaidAmount and recalculate INV.Status when CR is deleted."""
    conn = get_connection()
    cr = conn.execute("SELECT INV_ID, Amount FROM CR WHERE CR_ID=?", (pk,)).fetchone()
    if cr and cr["INV_ID"]:
        inv_id = cr["INV_ID"]
        amount = cr["Amount"]
        conn.execute(
            "UPDATE INV SET PaidAmount = MAX(PaidAmount - ?, 0) WHERE INV_ID=?",
            (amount, inv_id),
        )
        _recalc_inv_status(inv_id, conn)
    conn.commit()
    conn.close()


def before_delete_bank_entry(pk) -> None:
    """Decrement INV.PaidAmount when a BankEntry linked to an INV is deleted."""
    conn = get_connection()
    entry = conn.execute(
        "SELECT INV_ID, Amount, Direction FROM BankEntry WHERE Entry_ID=?", (pk,)
    ).fetchone()
    if entry and entry["INV_ID"] and entry["Direction"] == "in":
        inv_id = entry["INV_ID"]
        amount = entry["Amount"]
        conn.execute(
            "UPDATE INV SET PaidAmount = MAX(PaidAmount - ?, 0) WHERE INV_ID=?",
            (amount, inv_id),
        )
        _recalc_inv_status(inv_id, conn)
    conn.commit()
    conn.close()


def before_delete_si(pk) -> None:
    """Reverse stock increases when SI is deleted."""
    from data.products import apply_stock_delta
    conn = get_connection()
    items = conn.execute(
        "SELECT ProductID, Quantity FROM SI_Items WHERE SI_ID=?", (pk,)
    ).fetchall()
    for it in items:
        apply_stock_delta(it["ProductID"], -it["Quantity"], conn)
    conn.commit()
    conn.close()


def before_delete_so(pk) -> None:
    """Reverse stock decreases when SO is deleted."""
    from data.products import apply_stock_delta
    conn = get_connection()
    items = conn.execute(
        "SELECT ProductID, Quantity FROM SO_Items WHERE SO_ID=?", (pk,)
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
        ("DN_Items", "ProductID", "DN item(s)"),
        ("GR_Items", "ProductID", "GR item(s)"),
        ("SI_Items", "ProductID", "SI item(s)"),
        ("SO_Items", "ProductID", "SO item(s)"),
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
        ("DN", "CustomerID", "DN document(s)"),
        ("INV", "CustomerID", "invoice(s)"),
        ("CR", "CustomerID", "CR receipt(s)"),
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
        ("GR", "SupplierID", "GR document(s)"),
        ("CP", "SupplierID", "CP payment(s)"),
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

def _recalc_inv_status(inv_id: int, conn) -> None:
    """Recalculate INV.Status based on current PaidAmount vs TotalNet."""
    row = conn.execute(
        "SELECT TotalNet, COALESCE(PaidAmount, 0) FROM INV WHERE INV_ID=?",
        (inv_id,),
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
    conn.execute("UPDATE INV SET Status=? WHERE INV_ID=?", (status, inv_id))
