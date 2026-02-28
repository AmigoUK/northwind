"""Tests for document cancellation — WZ, FV, PZ.

Covers: cancellation preconditions, cascade effects on related documents,
stock reversal, status transitions, and error cases.
"""
from datetime import date

import pytest

import db
from data import products, wz, fv, pz


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_wz_issued(customer_id="ALFKI", product_id=1, qty=5, price=18.0):
    wz_id = wz.create_draft(customer_id, str(date.today()))
    wz.add_item(wz_id, product_id, qty, price)
    wz.issue(wz_id)
    return wz_id


def _make_fv(customer_id="ALFKI", product_id=1, qty=5, price=18.0):
    wz_id = _make_wz_issued(customer_id, product_id, qty, price)
    fv_id = fv.create(customer_id, [wz_id], str(date.today()))
    return fv_id, wz_id


# ── WZ Cancellation ─────────────────────────────────────────────────────────

class TestWZCancellation:
    def test_cancel_issued_wz(self):
        """Cancelling an issued WZ sets status to 'cancelled'."""
        wz_id = _make_wz_issued()
        wz.cancel(wz_id, reason="Damaged goods", user_id=1)
        doc = wz.get_by_pk(wz_id)
        assert doc["Status"] == "cancelled"
        assert doc["CancelReason"] == "Damaged goods"
        assert doc["CancelledBy"] == 1
        assert doc["CancelledAt"] is not None

    def test_cancel_wz_reverses_stock(self):
        """Stock is restored when an issued WZ is cancelled."""
        stock_before = products.get_stock(1)
        wz_id = _make_wz_issued(qty=7)
        assert products.get_stock(1) == stock_before - 7
        wz.cancel(wz_id, reason="Error", user_id=1)
        assert products.get_stock(1) == stock_before

    def test_cancel_draft_wz_raises(self):
        """Draft WZ cannot be cancelled — it should be deleted instead."""
        wz_id = wz.create_draft("ALFKI", str(date.today()))
        with pytest.raises(ValueError, match="[Dd]raft"):
            wz.cancel(wz_id, reason="Oops", user_id=1)

    def test_cancel_invoiced_wz_raises(self):
        """An invoiced WZ cannot be cancelled — cancel the FV first."""
        fv_id, wz_id = _make_fv()
        with pytest.raises(ValueError, match="[Ff]V|invoice"):
            wz.cancel(wz_id, reason="Oops", user_id=1)

    def test_cancel_already_cancelled_raises(self):
        """Cannot cancel a WZ that's already cancelled."""
        wz_id = _make_wz_issued()
        wz.cancel(wz_id, reason="First", user_id=1)
        with pytest.raises(ValueError, match="already cancelled"):
            wz.cancel(wz_id, reason="Second", user_id=1)


# ── FV Cancellation ─────────────────────────────────────────────────────────

class TestFVCancellation:
    def test_cancel_unpaid_fv(self):
        """Cancelling an unpaid FV sets status to 'cancelled'."""
        fv_id, wz_id = _make_fv()
        fv.cancel(fv_id, reason="Duplicate invoice", user_id=1)
        doc = fv.get_by_pk(fv_id)
        assert doc["Status"] == "cancelled"
        assert doc["CancelReason"] == "Duplicate invoice"

    def test_cancel_fv_reverts_wz_to_issued(self):
        """Linked WZ documents revert from 'invoiced' to 'issued'."""
        fv_id, wz_id = _make_fv()
        wz_doc = wz.get_by_pk(wz_id)
        assert wz_doc["Status"] == "invoiced"
        fv.cancel(fv_id, reason="Error", user_id=1)
        wz_doc = wz.get_by_pk(wz_id)
        assert wz_doc["Status"] == "issued"

    def test_cancel_paid_fv_raises(self):
        """Cannot cancel an FV that has payments — use FK instead."""
        fv_id, _ = _make_fv()
        fv.record_payment(fv_id, 10.0, "cash")
        with pytest.raises(ValueError, match="[Pp]ayment|FK"):
            fv.cancel(fv_id, reason="Error", user_id=1)

    def test_cancel_already_cancelled_raises(self):
        fv_id, _ = _make_fv()
        fv.cancel(fv_id, reason="First", user_id=1)
        with pytest.raises(ValueError, match="already cancelled"):
            fv.cancel(fv_id, reason="Second", user_id=1)


# ── PZ Cancellation ─────────────────────────────────────────────────────────

class TestPZCancellation:
    def test_cancel_received_pz(self):
        """Cancelling a received PZ sets status to 'cancelled'."""
        pz_id = pz.create_draft(1, str(date.today()))
        pz.add_item(pz_id, 1, 10, 15.0)
        pz.receive(pz_id)
        pz.cancel(pz_id, reason="Wrong goods", user_id=1)
        doc = pz.get_by_pk(pz_id)
        assert doc["Status"] == "cancelled"
        assert doc["CancelReason"] == "Wrong goods"

    def test_cancel_pz_reverses_stock(self):
        """Stock is decremented when a received PZ is cancelled."""
        stock_before = products.get_stock(1)
        pz_id = pz.create_draft(1, str(date.today()))
        pz.add_item(pz_id, 1, 15, 12.0)
        pz.receive(pz_id)
        assert products.get_stock(1) == stock_before + 15
        pz.cancel(pz_id, reason="Error", user_id=1)
        assert products.get_stock(1) == stock_before

    def test_cancel_draft_pz_raises(self):
        """Draft PZ cannot be cancelled — delete it instead."""
        pz_id = pz.create_draft(1, str(date.today()))
        with pytest.raises(ValueError, match="[Dd]raft"):
            pz.cancel(pz_id, reason="Oops", user_id=1)

    def test_cancel_already_cancelled_raises(self):
        pz_id = pz.create_draft(1, str(date.today()))
        pz.add_item(pz_id, 1, 5, 10.0)
        pz.receive(pz_id)
        pz.cancel(pz_id, reason="First", user_id=1)
        with pytest.raises(ValueError, match="already cancelled"):
            pz.cancel(pz_id, reason="Second", user_id=1)
