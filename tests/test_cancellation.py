"""Tests for document cancellation — DN, INV, GR.

Covers: cancellation preconditions, cascade effects on related documents,
stock reversal, status transitions, and error cases.
"""
from datetime import date

import pytest

import db
from data import products, dn, inv, gr


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_dn_issued(customer_id="ALFKI", product_id=1, qty=5, price=18.0):
    dn_id = dn.create_draft(customer_id, str(date.today()))
    dn.add_item(dn_id, product_id, qty, price)
    dn.issue(dn_id)
    return dn_id


def _make_inv(customer_id="ALFKI", product_id=1, qty=5, price=18.0):
    dn_id = _make_dn_issued(customer_id, product_id, qty, price)
    inv_id = inv.create(customer_id, [dn_id], str(date.today()))
    return inv_id, dn_id


# ── DN Cancellation ─────────────────────────────────────────────────────────

class TestDNCancellation:
    def test_cancel_issued_dn(self):
        """Cancelling an issued DN sets status to 'cancelled'."""
        dn_id = _make_dn_issued()
        dn.cancel(dn_id, reason="Damaged goods", user_id=1)
        doc = dn.get_by_pk(dn_id)
        assert doc["Status"] == "cancelled"
        assert doc["CancelReason"] == "Damaged goods"
        assert doc["CancelledBy"] == 1
        assert doc["CancelledAt"] is not None

    def test_cancel_dn_reverses_stock(self):
        """Stock is restored when an issued DN is cancelled."""
        stock_before = products.get_stock(1)
        dn_id = _make_dn_issued(qty=7)
        assert products.get_stock(1) == stock_before - 7
        dn.cancel(dn_id, reason="Error", user_id=1)
        assert products.get_stock(1) == stock_before

    def test_cancel_draft_dn_raises(self):
        """Draft DN cannot be cancelled — it should be deleted instead."""
        dn_id = dn.create_draft("ALFKI", str(date.today()))
        with pytest.raises(ValueError, match="[Dd]raft"):
            dn.cancel(dn_id, reason="Oops", user_id=1)

    def test_cancel_invoiced_dn_raises(self):
        """An invoiced DN cannot be cancelled — cancel the INV first."""
        inv_id, dn_id = _make_inv()
        with pytest.raises(ValueError, match="[Ii]NV|invoice"):
            dn.cancel(dn_id, reason="Oops", user_id=1)

    def test_cancel_already_cancelled_raises(self):
        """Cannot cancel a DN that's already cancelled."""
        dn_id = _make_dn_issued()
        dn.cancel(dn_id, reason="First", user_id=1)
        with pytest.raises(ValueError, match="already cancelled"):
            dn.cancel(dn_id, reason="Second", user_id=1)


# ── INV Cancellation ─────────────────────────────────────────────────────────

class TestINVCancellation:
    def test_cancel_unpaid_inv(self):
        """Cancelling an unpaid INV sets status to 'cancelled'."""
        inv_id, dn_id = _make_inv()
        inv.cancel(inv_id, reason="Duplicate invoice", user_id=1)
        doc = inv.get_by_pk(inv_id)
        assert doc["Status"] == "cancelled"
        assert doc["CancelReason"] == "Duplicate invoice"

    def test_cancel_inv_reverts_dn_to_issued(self):
        """Linked DN documents revert from 'invoiced' to 'issued'."""
        inv_id, dn_id = _make_inv()
        dn_doc = dn.get_by_pk(dn_id)
        assert dn_doc["Status"] == "invoiced"
        inv.cancel(inv_id, reason="Error", user_id=1)
        dn_doc = dn.get_by_pk(dn_id)
        assert dn_doc["Status"] == "issued"

    def test_cancel_paid_inv_raises(self):
        """Cannot cancel an INV that has payments — use CN instead."""
        inv_id, _ = _make_inv()
        inv.record_payment(inv_id, 10.0, "cash")
        with pytest.raises(ValueError, match="[Pp]ayment|CN"):
            inv.cancel(inv_id, reason="Error", user_id=1)

    def test_cancel_already_cancelled_raises(self):
        inv_id, _ = _make_inv()
        inv.cancel(inv_id, reason="First", user_id=1)
        with pytest.raises(ValueError, match="already cancelled"):
            inv.cancel(inv_id, reason="Second", user_id=1)


# ── GR Cancellation ─────────────────────────────────────────────────────────

class TestGRCancellation:
    def test_cancel_received_gr(self):
        """Cancelling a received GR sets status to 'cancelled'."""
        gr_id = gr.create_draft(1, str(date.today()))
        gr.add_item(gr_id, 1, 10, 15.0)
        gr.receive(gr_id)
        gr.cancel(gr_id, reason="Wrong goods", user_id=1)
        doc = gr.get_by_pk(gr_id)
        assert doc["Status"] == "cancelled"
        assert doc["CancelReason"] == "Wrong goods"

    def test_cancel_gr_reverses_stock(self):
        """Stock is decremented when a received GR is cancelled."""
        stock_before = products.get_stock(1)
        gr_id = gr.create_draft(1, str(date.today()))
        gr.add_item(gr_id, 1, 15, 12.0)
        gr.receive(gr_id)
        assert products.get_stock(1) == stock_before + 15
        gr.cancel(gr_id, reason="Error", user_id=1)
        assert products.get_stock(1) == stock_before

    def test_cancel_draft_gr_raises(self):
        """Draft GR cannot be cancelled — delete it instead."""
        gr_id = gr.create_draft(1, str(date.today()))
        with pytest.raises(ValueError, match="[Dd]raft"):
            gr.cancel(gr_id, reason="Oops", user_id=1)

    def test_cancel_already_cancelled_raises(self):
        gr_id = gr.create_draft(1, str(date.today()))
        gr.add_item(gr_id, 1, 5, 10.0)
        gr.receive(gr_id)
        gr.cancel(gr_id, reason="First", user_id=1)
        with pytest.raises(ValueError, match="already cancelled"):
            gr.cancel(gr_id, reason="Second", user_id=1)
