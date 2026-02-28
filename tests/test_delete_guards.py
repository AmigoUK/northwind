"""Tests for delete guard functions and side-effect handlers.

Covers: can_delete_* guard checks, before_delete_* side-effects,
cascade behaviour on master data, and edge cases.
"""
from datetime import date

import pytest

import db
from data import products, dn, inv, gr, cash, bank, si_so, orders
from data.delete_guards import (
    can_delete_order,
    can_delete_dn,
    can_delete_inv,
    can_delete_gr,
    can_delete_si,
    can_delete_product,
    can_delete_customer,
    can_delete_supplier,
    can_delete_category,
    can_delete_employee,
    can_delete_shipper,
    before_delete_cr,
    before_delete_bank_entry,
    before_delete_si,
    before_delete_so,
    _fmt_reasons,
)


# ── Helper ───────────────────────────────────────────────────────────────────

def _make_dn_issued(customer_id="ALFKI", product_id=1, qty=5, price=18.0):
    """Create and issue a DN, returning the DN_ID."""
    dn_id = dn.create_draft(customer_id, str(date.today()))
    dn.add_item(dn_id, product_id, qty, price)
    dn.issue(dn_id)
    return dn_id


def _make_inv(customer_id="ALFKI", product_id=1, qty=5, price=18.0):
    """Create DN → issue → create INV, returning (inv_id, dn_id)."""
    dn_id = _make_dn_issued(customer_id, product_id, qty, price)
    inv_id = inv.create(customer_id, [dn_id], str(date.today()))
    return inv_id, dn_id


# ── _fmt_reasons ─────────────────────────────────────────────────────────────

class TestFmtReasons:
    def test_short_list_unchanged(self):
        r = _fmt_reasons(["a", "b", "c"], limit=5)
        assert r == ["a", "b", "c"]

    def test_long_list_truncated(self):
        r = _fmt_reasons(["a", "b", "c", "d", "e", "f", "g"], limit=3)
        assert len(r) == 4
        assert r[-1] == "...and 4 more"


# ── Document guards ──────────────────────────────────────────────────────────

class TestCanDeleteOrder:
    def test_order_without_dn_can_be_deleted(self):
        """Seed order 10248 has no DN → can_delete_order returns True."""
        ok, reasons = can_delete_order(10248)
        assert ok
        assert reasons == []

    def test_order_with_dn_blocked(self):
        """Create a DN referencing an order → deletion blocked."""
        conn = db.get_connection()
        # Create a draft DN linked to order 10249
        num = db.next_doc_number("DN", conn)
        conn.execute(
            "INSERT INTO DN (DN_Number, OrderID, CustomerID, DN_Date, Status) "
            "VALUES (?, ?, 'ALFKI', ?, 'draft')",
            (num, 10249, str(date.today())),
        )
        conn.commit()
        conn.close()
        ok, reasons = can_delete_order(10249)
        assert not ok
        assert any("DN" in r for r in reasons)


class TestCanDeleteDN:
    def test_draft_without_inv_can_be_deleted(self):
        dn_id = dn.create_draft("ALFKI", str(date.today()))
        ok, reasons = can_delete_dn(dn_id)
        assert ok

    def test_issued_dn_blocked(self):
        dn_id = _make_dn_issued()
        ok, reasons = can_delete_dn(dn_id)
        assert not ok
        assert any("issued" in r for r in reasons)

    def test_invoiced_dn_blocked(self):
        inv_id, dn_id = _make_inv()
        ok, reasons = can_delete_dn(dn_id)
        assert not ok
        assert any("invoiced" in r or "INV" in r for r in reasons)


class TestCanDeleteINV:
    def test_inv_without_payments_can_be_deleted(self):
        inv_id, _ = _make_inv()
        ok, reasons = can_delete_inv(inv_id)
        assert ok

    def test_inv_with_cr_blocked(self):
        inv_id, _ = _make_inv()
        cash.create_cr(customer_id="ALFKI", inv_id=inv_id, amount=50.0)
        ok, reasons = can_delete_inv(inv_id)
        assert not ok
        assert any("CR" in r for r in reasons)

    def test_inv_with_bank_entry_blocked(self):
        inv_id, _ = _make_inv()
        bank.create_bank_entry(direction="in", customer_id="ALFKI",
                               inv_id=inv_id, amount=50.0)
        ok, reasons = can_delete_inv(inv_id)
        assert not ok
        assert any("Bank" in r for r in reasons)


class TestCanDeleteGR:
    def test_draft_gr_can_be_deleted(self):
        gr_id = gr.create_draft(1, str(date.today()))
        ok, reasons = can_delete_gr(gr_id)
        assert ok

    def test_received_gr_blocked(self):
        gr_id = gr.create_draft(1, str(date.today()))
        gr.add_item(gr_id, 1, 10, 15.0)
        gr.receive(gr_id)
        ok, reasons = can_delete_gr(gr_id)
        assert not ok
        assert any("received" in r for r in reasons)


class TestCanDeleteSI:
    def test_si_ok_when_stock_sufficient(self):
        si_id = si_so.create_si(str(date.today()), reason="test",
                                items=[{"product_id": 1, "quantity": 5}])
        ok, reasons = can_delete_si(si_id)
        assert ok

    def test_si_blocked_when_stock_insufficient(self):
        """If stock was consumed after SI, reversal would go negative."""
        original_stock = products.get_stock(1)
        si_id = si_so.create_si(str(date.today()), reason="test",
                                items=[{"product_id": 1, "quantity": 10}])
        # Consume all stock via SO
        total = original_stock + 10
        si_so.create_so(str(date.today()), reason="consume",
                        items=[{"product_id": 1, "quantity": total}])
        ok, reasons = can_delete_si(si_id)
        assert not ok
        assert any("negative" in r for r in reasons)


# ── Side-effects ─────────────────────────────────────────────────────────────

class TestBeforeDeleteCR:
    def test_decrement_inv_paid_amount(self):
        """Deleting a CR linked to an INV decrements PaidAmount and recalcs status."""
        inv_id, _ = _make_inv()
        # Record a payment via INV module (creates CR + updates INV)
        inv.record_payment(inv_id, 50.0, "cash")
        inv_doc = inv.get_by_pk(inv_id)
        assert inv_doc["PaidAmount"] == 50.0

        # Find the CR that was created
        conn = db.get_connection()
        cr_row = conn.execute(
            "SELECT CR_ID FROM CR WHERE INV_ID=?", (inv_id,)
        ).fetchone()
        conn.close()
        cr_id = cr_row["CR_ID"]

        # Delete CR → should decrement PaidAmount
        cash.delete_cr(cr_id)
        inv_doc = inv.get_by_pk(inv_id)
        assert inv_doc["PaidAmount"] == 0.0
        assert inv_doc["Status"] == "issued"


class TestBeforeDeleteBankEntry:
    def test_decrement_inv_paid_amount(self):
        inv_id, _ = _make_inv()
        inv.record_payment(inv_id, 30.0, "bank")
        inv_doc = inv.get_by_pk(inv_id)
        assert inv_doc["PaidAmount"] == 30.0

        conn = db.get_connection()
        entry_row = conn.execute(
            "SELECT Entry_ID FROM BankEntry WHERE INV_ID=?", (inv_id,)
        ).fetchone()
        conn.close()

        bank.delete(entry_row["Entry_ID"])
        inv_doc = inv.get_by_pk(inv_id)
        assert inv_doc["PaidAmount"] == 0.0
        assert inv_doc["Status"] == "issued"


class TestBeforeDeleteSI:
    def test_stock_reversed_on_si_delete(self):
        stock_before = products.get_stock(1)
        si_id = si_so.create_si(str(date.today()), reason="test",
                                items=[{"product_id": 1, "quantity": 10}])
        assert products.get_stock(1) == stock_before + 10
        si_so.delete_si(si_id)
        assert products.get_stock(1) == stock_before


class TestBeforeDeleteSO:
    def test_stock_reversed_on_so_delete(self):
        stock_before = products.get_stock(1)
        so_id = si_so.create_so(str(date.today()), reason="test",
                                items=[{"product_id": 1, "quantity": 5}])
        assert products.get_stock(1) == stock_before - 5
        si_so.delete_so(so_id)
        assert products.get_stock(1) == stock_before


# ── Master data guards ───────────────────────────────────────────────────────

class TestMasterDataGuards:
    def test_product_with_order_details_blocked(self):
        """Product 1 is referenced by OrderDetails → can't delete."""
        ok, reasons = can_delete_product(1)
        assert not ok
        assert any("order detail" in r for r in reasons)

    def test_product_without_references_ok(self):
        """A fresh product with no references can be deleted."""
        products.insert({"ProductName": "Deletable", "UnitPrice": 1.0,
                         "UnitsInStock": 0, "ReorderLevel": 0})
        conn = db.get_connection()
        row = conn.execute(
            "SELECT ProductID FROM Products WHERE ProductName='Deletable'"
        ).fetchone()
        conn.close()
        ok, reasons = can_delete_product(row["ProductID"])
        assert ok

    def test_customer_with_orders_blocked(self):
        ok, reasons = can_delete_customer("ALFKI")
        assert not ok
        assert any("order" in r for r in reasons)

    def test_supplier_with_products_blocked(self):
        ok, reasons = can_delete_supplier(1)
        assert not ok
        assert any("product" in r for r in reasons)

    def test_category_with_products_blocked(self):
        ok, reasons = can_delete_category(1)
        assert not ok
        assert any("product" in r for r in reasons)

    def test_employee_with_orders_blocked(self):
        ok, reasons = can_delete_employee(5)
        assert not ok

    def test_employee_with_reports_blocked(self):
        """Employee 2 has direct reports."""
        ok, reasons = can_delete_employee(2)
        assert not ok
        assert any("report" in r for r in reasons)

    def test_shipper_with_orders_blocked(self):
        ok, reasons = can_delete_shipper(1)
        assert not ok
        assert any("order" in r for r in reasons)
