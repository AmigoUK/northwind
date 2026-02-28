"""Tests for delete guard functions and side-effect handlers.

Covers: can_delete_* guard checks, before_delete_* side-effects,
cascade behaviour on master data, and edge cases.
"""
from datetime import date

import pytest

import db
from data import products, wz, fv, pz, kassa, bank, pw_rw, orders
from data.delete_guards import (
    can_delete_order,
    can_delete_wz,
    can_delete_fv,
    can_delete_pz,
    can_delete_pw,
    can_delete_product,
    can_delete_customer,
    can_delete_supplier,
    can_delete_category,
    can_delete_employee,
    can_delete_shipper,
    before_delete_kp,
    before_delete_bank_entry,
    before_delete_pw,
    before_delete_rw,
    _fmt_reasons,
)


# ── Helper ───────────────────────────────────────────────────────────────────

def _make_wz_issued(customer_id="ALFKI", product_id=1, qty=5, price=18.0):
    """Create and issue a WZ, returning the WZ_ID."""
    wz_id = wz.create_draft(customer_id, str(date.today()))
    wz.add_item(wz_id, product_id, qty, price)
    wz.issue(wz_id)
    return wz_id


def _make_fv(customer_id="ALFKI", product_id=1, qty=5, price=18.0):
    """Create WZ → issue → create FV, returning (fv_id, wz_id)."""
    wz_id = _make_wz_issued(customer_id, product_id, qty, price)
    fv_id = fv.create(customer_id, [wz_id], str(date.today()))
    return fv_id, wz_id


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
    def test_order_without_wz_can_be_deleted(self):
        """Seed order 10248 has no WZ → can_delete_order returns True."""
        ok, reasons = can_delete_order(10248)
        assert ok
        assert reasons == []

    def test_order_with_wz_blocked(self):
        """Create a WZ referencing an order → deletion blocked."""
        conn = db.get_connection()
        # Create a draft WZ linked to order 10249
        num = db.next_doc_number("WZ", conn)
        conn.execute(
            "INSERT INTO WZ (WZ_Number, OrderID, CustomerID, WZ_Date, Status) "
            "VALUES (?, ?, 'ALFKI', ?, 'draft')",
            (num, 10249, str(date.today())),
        )
        conn.commit()
        conn.close()
        ok, reasons = can_delete_order(10249)
        assert not ok
        assert any("WZ" in r for r in reasons)


class TestCanDeleteWZ:
    def test_draft_without_fv_can_be_deleted(self):
        wz_id = wz.create_draft("ALFKI", str(date.today()))
        ok, reasons = can_delete_wz(wz_id)
        assert ok

    def test_issued_wz_blocked(self):
        wz_id = _make_wz_issued()
        ok, reasons = can_delete_wz(wz_id)
        assert not ok
        assert any("issued" in r for r in reasons)

    def test_invoiced_wz_blocked(self):
        fv_id, wz_id = _make_fv()
        ok, reasons = can_delete_wz(wz_id)
        assert not ok
        assert any("invoiced" in r or "FV" in r for r in reasons)


class TestCanDeleteFV:
    def test_fv_without_payments_can_be_deleted(self):
        fv_id, _ = _make_fv()
        ok, reasons = can_delete_fv(fv_id)
        assert ok

    def test_fv_with_kp_blocked(self):
        fv_id, _ = _make_fv()
        kassa.create_kp(customer_id="ALFKI", fv_id=fv_id, amount=50.0)
        ok, reasons = can_delete_fv(fv_id)
        assert not ok
        assert any("KP" in r for r in reasons)

    def test_fv_with_bank_entry_blocked(self):
        fv_id, _ = _make_fv()
        bank.create_bank_entry(direction="in", customer_id="ALFKI",
                               fv_id=fv_id, amount=50.0)
        ok, reasons = can_delete_fv(fv_id)
        assert not ok
        assert any("Bank" in r for r in reasons)


class TestCanDeletePZ:
    def test_draft_pz_can_be_deleted(self):
        pz_id = pz.create_draft(1, str(date.today()))
        ok, reasons = can_delete_pz(pz_id)
        assert ok

    def test_received_pz_blocked(self):
        pz_id = pz.create_draft(1, str(date.today()))
        pz.add_item(pz_id, 1, 10, 15.0)
        pz.receive(pz_id)
        ok, reasons = can_delete_pz(pz_id)
        assert not ok
        assert any("received" in r for r in reasons)


class TestCanDeletePW:
    def test_pw_ok_when_stock_sufficient(self):
        pw_id = pw_rw.create_pw(str(date.today()), reason="test",
                                items=[{"product_id": 1, "quantity": 5}])
        ok, reasons = can_delete_pw(pw_id)
        assert ok

    def test_pw_blocked_when_stock_insufficient(self):
        """If stock was consumed after PW, reversal would go negative."""
        original_stock = products.get_stock(1)
        pw_id = pw_rw.create_pw(str(date.today()), reason="test",
                                items=[{"product_id": 1, "quantity": 10}])
        # Consume all stock via RW
        total = original_stock + 10
        pw_rw.create_rw(str(date.today()), reason="consume",
                        items=[{"product_id": 1, "quantity": total}])
        ok, reasons = can_delete_pw(pw_id)
        assert not ok
        assert any("negative" in r for r in reasons)


# ── Side-effects ─────────────────────────────────────────────────────────────

class TestBeforeDeleteKP:
    def test_decrement_fv_paid_amount(self):
        """Deleting a KP linked to an FV decrements PaidAmount and recalcs status."""
        fv_id, _ = _make_fv()
        # Record a payment via FV module (creates KP + updates FV)
        fv.record_payment(fv_id, 50.0, "cash")
        fv_doc = fv.get_by_pk(fv_id)
        assert fv_doc["PaidAmount"] == 50.0

        # Find the KP that was created
        conn = db.get_connection()
        kp_row = conn.execute(
            "SELECT KP_ID FROM KP WHERE FV_ID=?", (fv_id,)
        ).fetchone()
        conn.close()
        kp_id = kp_row["KP_ID"]

        # Delete KP → should decrement PaidAmount
        kassa.delete_kp(kp_id)
        fv_doc = fv.get_by_pk(fv_id)
        assert fv_doc["PaidAmount"] == 0.0
        assert fv_doc["Status"] == "issued"


class TestBeforeDeleteBankEntry:
    def test_decrement_fv_paid_amount(self):
        fv_id, _ = _make_fv()
        fv.record_payment(fv_id, 30.0, "bank")
        fv_doc = fv.get_by_pk(fv_id)
        assert fv_doc["PaidAmount"] == 30.0

        conn = db.get_connection()
        entry_row = conn.execute(
            "SELECT Entry_ID FROM BankEntry WHERE FV_ID=?", (fv_id,)
        ).fetchone()
        conn.close()

        bank.delete(entry_row["Entry_ID"])
        fv_doc = fv.get_by_pk(fv_id)
        assert fv_doc["PaidAmount"] == 0.0
        assert fv_doc["Status"] == "issued"


class TestBeforeDeletePW:
    def test_stock_reversed_on_pw_delete(self):
        stock_before = products.get_stock(1)
        pw_id = pw_rw.create_pw(str(date.today()), reason="test",
                                items=[{"product_id": 1, "quantity": 10}])
        assert products.get_stock(1) == stock_before + 10
        pw_rw.delete_pw(pw_id)
        assert products.get_stock(1) == stock_before


class TestBeforeDeleteRW:
    def test_stock_reversed_on_rw_delete(self):
        stock_before = products.get_stock(1)
        rw_id = pw_rw.create_rw(str(date.today()), reason="test",
                                items=[{"product_id": 1, "quantity": 5}])
        assert products.get_stock(1) == stock_before - 5
        pw_rw.delete_rw(rw_id)
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
