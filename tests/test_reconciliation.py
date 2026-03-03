"""Tests for data/reconciliation.py — AR/AP reconciliation logic."""
import pytest
from datetime import date, timedelta

import db
import data.inv as inv_data
import data.cash as cash_data
import data.bank as bank_data
import data.reconciliation as rdata


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_dn(conn, customer_id="ALFKI", product_id=1, qty=10, price=100.0,
             dn_date="2026-01-01"):
    """Insert a DN + DN_Items row and return DN_ID."""
    from db import next_doc_number
    number = next_doc_number("DN", conn)
    cur = conn.execute(
        "INSERT INTO DN (DN_Number, CustomerID, DN_Date, Status) VALUES (?,?,?,'issued')",
        (number, customer_id, dn_date),
    )
    dn_id = cur.lastrowid
    conn.execute(
        "INSERT INTO DN_Items (DN_ID, ProductID, Quantity, UnitPrice) VALUES (?,?,?,?)",
        (dn_id, product_id, qty, price),
    )
    conn.commit()
    return dn_id


def _make_inv(conn, customer_id="ALFKI", total=1000.0, inv_date="2026-01-10",
              due_date="2026-02-10", status="issued"):
    """Insert an INV row directly and return INV_ID."""
    from db import next_doc_number
    number = next_doc_number("INV", conn)
    cur = conn.execute(
        "INSERT INTO INV (INV_Number, CustomerID, INV_Date, DueDate, Status, TotalNet, PaidAmount) "
        "VALUES (?,?,?,?,?,?,0)",
        (number, customer_id, inv_date, due_date, status, total),
    )
    inv_id = cur.lastrowid
    conn.commit()
    return inv_id


def _make_cn(conn, inv_id, customer_id="ALFKI", correction=100.0, cn_date="2026-01-15"):
    """Insert a CN row and return CN_ID."""
    from db import next_doc_number
    number = next_doc_number("CN", conn)
    cur = conn.execute(
        "INSERT INTO CN (CN_Number, INV_ID, CustomerID, CN_Date, CN_Type, Reason, "
        "Status, TotalCorrection, CreatedAt) "
        "VALUES (?,?,?,?,'quantity','Test reason','issued',?,?)",
        (number, inv_id, customer_id, cn_date, -abs(correction), cn_date),
    )
    cn_id = cur.lastrowid
    conn.commit()
    return cn_id


def _make_gr(conn, supplier_id=1, product_id=1, qty=5, unit_cost=50.0,
             gr_date="2026-01-05", status="received"):
    """Insert a GR + GR_Items row and return GR_ID."""
    from db import next_doc_number
    number = next_doc_number("GR", conn)
    cur = conn.execute(
        "INSERT INTO GR (GR_Number, SupplierID, GR_Date, Status) VALUES (?,?,?,?)",
        (number, supplier_id, gr_date, status),
    )
    gr_id = cur.lastrowid
    conn.execute(
        "INSERT INTO GR_Items (GR_ID, ProductID, Quantity, UnitCost) VALUES (?,?,?,?)",
        (gr_id, product_id, qty, unit_cost),
    )
    conn.commit()
    return gr_id


# ── AR tests ──────────────────────────────────────────────────────────────────

def test_customer_statement_has_all_doc_types(test_db):
    """ALFKI statement contains rows with doc_type in {INV, CR, BankIN, CN}."""
    conn = db.get_connection()
    inv_id = _make_inv(conn, "ALFKI", 1500.0, "2026-01-10")
    _make_cn(conn, inv_id, "ALFKI", 100.0, "2026-01-12")
    conn.close()

    cash_data.create_cr("ALFKI", None, 500.0, "Payment", "2026-01-15")
    bank_data.create_bank_entry("in", 200.0, "Wire", customer_id="ALFKI",
                                date_override="2026-01-20")

    rows = rdata.fetch_customer_statement("ALFKI")
    doc_types = {r["doc_type"] for r in rows}
    assert "INV"    in doc_types
    assert "CR"     in doc_types
    assert "BankIN" in doc_types
    assert "CN"     in doc_types


def test_customer_statement_running_balance(test_db):
    """Final balance equals sum(debits) − sum(credits) across all rows."""
    conn = db.get_connection()
    _make_inv(conn, "ALFKI", 1000.0, "2026-01-10")
    conn.close()

    cash_data.create_cr("ALFKI", None, 300.0, "p1", "2026-01-15")
    cash_data.create_cr("ALFKI", None, 200.0, "p2", "2026-01-20")

    rows = rdata.fetch_customer_statement("ALFKI")
    total_debit  = sum(r["debit"]  for r in rows)
    total_credit = sum(r["credit"] for r in rows)
    expected_balance = total_debit - total_credit
    assert abs(rows[-1]["balance"] - expected_balance) < 0.001


def test_ar_aging_buckets(test_db):
    """An INV with a past DueDate appears in the correct overdue bucket."""
    # Create an INV due 45 days ago → should fall in 31-60 bucket
    due_45_ago = str(date.today() - timedelta(days=45))
    conn = db.get_connection()
    _make_inv(conn, "ALFKI", 750.0, "2025-11-01", due_date=due_45_ago, status="issued")
    conn.close()

    aging = rdata.fetch_ar_aging()
    alfki_row = next((r for r in aging if r["CustomerID"] == "ALFKI"), None)
    assert alfki_row is not None, "ALFKI should appear in aging"
    assert alfki_row["d31_60"] > 0, "750 should be in 31-60d bucket"
    assert alfki_row["total_outstanding"] > 0


def test_fetch_unallocated_cr_excludes_linked(test_db):
    """CR with INV_ID set does NOT appear; CR without INV_ID does."""
    conn = db.get_connection()
    inv_id = _make_inv(conn, "ALFKI", 500.0, "2026-01-10")
    conn.close()

    # Unallocated CR
    cr_unalloc = cash_data.create_cr("ALFKI", None, 100.0, "unalloc", "2026-01-15")
    # Allocated CR (linked to inv)
    cash_data.create_cr("ALFKI", inv_id, 400.0, "alloc", "2026-01-16")

    unalloc = rdata.fetch_unallocated_cr("ALFKI")
    ids = [r["CR_ID"] for r in unalloc]
    assert cr_unalloc in ids
    # The allocated one must not appear
    assert len([r for r in unalloc if r["CR_ID"] != cr_unalloc]) == 0


def test_allocate_cr_to_inv_sets_inv_id(test_db):
    """After allocation: CR.INV_ID is set to the target INV."""
    conn = db.get_connection()
    inv_id = _make_inv(conn, "ALFKI", 500.0, "2026-01-10")
    conn.close()

    cr_id = cash_data.create_cr("ALFKI", None, 200.0, "payment", "2026-01-15")
    rdata.allocate_payment_to_inv("cr", cr_id, inv_id)

    conn = db.get_connection()
    row = conn.execute("SELECT INV_ID FROM CR WHERE CR_ID=?", (cr_id,)).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == inv_id


def test_allocate_cr_to_inv_updates_paid_amount(test_db):
    """After allocation: INV.PaidAmount increases by the CR amount."""
    conn = db.get_connection()
    inv_id = _make_inv(conn, "ALFKI", 1000.0, "2026-01-10")
    conn.close()

    cr_id = cash_data.create_cr("ALFKI", None, 400.0, "payment", "2026-01-15")
    rdata.allocate_payment_to_inv("cr", cr_id, inv_id)

    conn = db.get_connection()
    row = conn.execute(
        "SELECT COALESCE(PaidAmount,0) FROM INV WHERE INV_ID=?", (inv_id,)
    ).fetchone()
    conn.close()
    assert abs(row[0] - 400.0) < 0.001


def test_allocate_cr_to_inv_recalcs_status_to_paid(test_db):
    """When CR amount equals TotalNet, INV.Status becomes 'paid'."""
    conn = db.get_connection()
    inv_id = _make_inv(conn, "ALFKI", 300.0, "2026-01-10")
    conn.close()

    cr_id = cash_data.create_cr("ALFKI", None, 300.0, "full payment", "2026-01-15")
    rdata.allocate_payment_to_inv("cr", cr_id, inv_id)

    conn = db.get_connection()
    row = conn.execute("SELECT Status FROM INV WHERE INV_ID=?", (inv_id,)).fetchone()
    conn.close()
    assert row[0] == "paid"


def test_allocate_already_allocated_raises(test_db):
    """ValueError is raised if CR.INV_ID is already set."""
    conn = db.get_connection()
    inv_id1 = _make_inv(conn, "ALFKI", 500.0, "2026-01-10")
    inv_id2 = _make_inv(conn, "ALFKI", 500.0, "2026-01-11")
    conn.close()

    cr_id = cash_data.create_cr("ALFKI", inv_id1, 200.0, "already linked", "2026-01-15")

    with pytest.raises(ValueError, match="already allocated"):
        rdata.allocate_payment_to_inv("cr", cr_id, inv_id2)


# ── AP tests ──────────────────────────────────────────────────────────────────

def test_supplier_statement_has_gr_cp_bankout(test_db):
    """Supplier #1 statement has GR, CP, and BankOUT doc types."""
    conn = db.get_connection()
    _make_gr(conn, supplier_id=1, product_id=1, qty=10, unit_cost=20.0,
             gr_date="2026-01-05", status="received")
    conn.close()

    cash_data.create_cr(None, None, 100.0, "seed cash for test", "2026-01-06")
    cash_data.create_cp(1, None, 50.0, "partial payment", "2026-01-10")
    bank_data.create_bank_entry("out", 100.0, "wire payment", supplier_id=1,
                                date_override="2026-01-15")

    rows = rdata.fetch_supplier_statement(1)
    doc_types = {r["doc_type"] for r in rows}
    assert "GR"      in doc_types
    assert "CP"      in doc_types
    assert "BankOUT" in doc_types


def test_allocate_cp_to_gr_sets_gr_id(test_db):
    """After allocation: CP.GR_ID is set to the target GR."""
    conn = db.get_connection()
    gr_id = _make_gr(conn, supplier_id=1, product_id=1, qty=5, unit_cost=40.0,
                     gr_date="2026-01-05", status="received")
    conn.close()

    cash_data.create_cr(None, None, 200.0, "seed cash for test", "2026-01-06")
    cp_id = cash_data.create_cp(1, None, 200.0, "payment", "2026-01-10")
    rdata.allocate_payment_to_gr("cp", cp_id, gr_id)

    conn = db.get_connection()
    row = conn.execute("SELECT GR_ID FROM CP WHERE CP_ID=?", (cp_id,)).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == gr_id


# ── All-unpaid view tests ──────────────────────────────────────────────────────

def test_fetch_all_unpaid_inv_all(test_db):
    """fetch_all_unpaid_inv() with no filter returns issued/partial INVs from all customers."""
    conn = db.get_connection()
    inv1 = _make_inv(conn, "ALFKI", 500.0, "2026-01-10", status="issued")
    inv2 = _make_inv(conn, "ANATR", 800.0, "2026-01-12", status="partial")
    conn.close()

    rows = rdata.fetch_all_unpaid_inv()
    ids = [r["inv_id"] for r in rows]
    assert inv1 in ids
    assert inv2 in ids


def test_fetch_all_unpaid_inv_filtered(test_db):
    """fetch_all_unpaid_inv(customer_id) returns only that customer's unpaid INVs."""
    conn = db.get_connection()
    inv_alfki = _make_inv(conn, "ALFKI", 500.0, "2026-01-10", status="issued")
    inv_anatr = _make_inv(conn, "ANATR", 800.0, "2026-01-12", status="issued")
    conn.close()

    rows = rdata.fetch_all_unpaid_inv("ALFKI")
    ids = [r["inv_id"] for r in rows]
    assert inv_alfki in ids
    assert inv_anatr not in ids


def test_fetch_all_unpaid_gr_all(test_db):
    """fetch_all_unpaid_gr() with no filter returns all received GRs without payment."""
    conn = db.get_connection()
    gr1 = _make_gr(conn, supplier_id=1, product_id=1, qty=5, unit_cost=50.0,
                   gr_date="2026-01-05", status="received")
    gr2 = _make_gr(conn, supplier_id=2, product_id=1, qty=3, unit_cost=30.0,
                   gr_date="2026-01-06", status="received")
    conn.close()

    rows = rdata.fetch_all_unpaid_gr()
    ids = [r["gr_id"] for r in rows]
    assert gr1 in ids
    assert gr2 in ids


def test_fetch_all_unpaid_gr_filtered(test_db):
    """fetch_all_unpaid_gr(supplier_id) returns only that supplier's unpaid GRs."""
    conn = db.get_connection()
    gr_s1 = _make_gr(conn, supplier_id=1, product_id=1, qty=5, unit_cost=50.0,
                     gr_date="2026-01-05", status="received")
    gr_s2 = _make_gr(conn, supplier_id=2, product_id=1, qty=3, unit_cost=30.0,
                     gr_date="2026-01-06", status="received")
    conn.close()

    rows = rdata.fetch_all_unpaid_gr(1)
    ids = [r["gr_id"] for r in rows]
    assert gr_s1 in ids
    assert gr_s2 not in ids
