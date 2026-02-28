"""Tests for FK (Faktura Korygujaca / Credit Note) business logic.

Covers: full reversal, partial correction, cancellation,
payment/stock/pricing effects, and edge cases.
"""
from datetime import date

import pytest

import db
from data import products, wz, fv, fk


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_fv_with_items(customer_id="ALFKI", items=None):
    """Create WZ → issue → FV. Returns (fv_id, wz_id).
    items = [(product_id, qty, price), ...]
    """
    if items is None:
        items = [(1, 10, 18.0)]
    wz_id = wz.create_draft(customer_id, str(date.today()))
    for pid, qty, price in items:
        wz.add_item(wz_id, pid, qty, price)
    wz.issue(wz_id)
    fv_id = fv.create(customer_id, [wz_id], str(date.today()))
    return fv_id, wz_id


# ── Full Reversal ────────────────────────────────────────────────────────────

class TestFullReversal:
    def test_creates_fk_with_correct_total(self):
        """Full reversal: TotalCorrection == -TotalNet."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        fv_doc = fv.get_by_pk(fv_id)
        original_total = fv_doc["TotalNet"]

        fk_id = fk.create_full_reversal(
            fv_id, reason="Customer return", fk_date=str(date.today()),
            user_id=1,
        )
        fk_doc = fk.get_by_pk(fk_id)
        assert fk_doc is not None
        assert fk_doc["FK_Type"] == "full_reversal"
        assert fk_doc["TotalCorrection"] == -original_total
        assert fk_doc["Reason"] == "Customer return"

    def test_items_corrected_to_zero(self):
        """All FK_Items have CorrQuantity=0."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        fk_id = fk.create_full_reversal(
            fv_id, reason="Error", fk_date=str(date.today()), user_id=1,
        )
        items = fk.fetch_items(fk_id)
        assert len(items) >= 1
        for item in items:
            assert item["CorrQuantity"] == 0

    def test_adjusts_fv_total_net(self):
        """FV.TotalNet is adjusted downward by TotalCorrection."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        fk.create_full_reversal(
            fv_id, reason="Return", fk_date=str(date.today()), user_id=1,
        )
        fv_doc = fv.get_by_pk(fv_id)
        assert fv_doc["TotalNet"] == 0.0

    def test_reverts_wz_to_issued(self):
        """Linked WZ goes from 'invoiced' back to 'issued'."""
        fv_id, wz_id = _make_fv_with_items()
        assert wz.get_by_pk(wz_id)["Status"] == "invoiced"
        fk.create_full_reversal(
            fv_id, reason="Return", fk_date=str(date.today()), user_id=1,
        )
        assert wz.get_by_pk(wz_id)["Status"] == "issued"

    def test_stock_restored_when_reverse_stock_true(self):
        """With reverse_stock=True, stock is restored for all items."""
        stock_before = products.get_stock(1)
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        stock_after_wz = products.get_stock(1)
        assert stock_after_wz == stock_before - 10

        fk.create_full_reversal(
            fv_id, reason="Return", fk_date=str(date.today()),
            user_id=1, reverse_stock=True,
        )
        assert products.get_stock(1) == stock_before

    def test_stock_not_changed_when_reverse_stock_false(self):
        """Without reverse_stock, stock is unchanged."""
        stock_before = products.get_stock(1)
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        stock_after_wz = products.get_stock(1)

        fk.create_full_reversal(
            fv_id, reason="Return", fk_date=str(date.today()),
            user_id=1, reverse_stock=False,
        )
        assert products.get_stock(1) == stock_after_wz

    def test_fv_status_recalculated(self):
        """After full reversal with no payments, FV goes to 'cancelled'."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        fk.create_full_reversal(
            fv_id, reason="Return", fk_date=str(date.today()), user_id=1,
        )
        fv_doc = fv.get_by_pk(fv_id)
        # TotalNet == 0, PaidAmount == 0 → cancelled
        assert fv_doc["Status"] == "cancelled"

    def test_overpayment_flagged(self):
        """If FV was already paid, status becomes 'paid' (overpayment scenario)."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        fv.record_payment(fv_id, 180.0, "cash")
        fv_doc = fv.get_by_pk(fv_id)
        assert fv_doc["Status"] == "paid"

        fk.create_full_reversal(
            fv_id, reason="Return", fk_date=str(date.today()), user_id=1,
        )
        fv_doc = fv.get_by_pk(fv_id)
        # TotalNet == 0, PaidAmount == 180 → paid (overpayment)
        assert fv_doc["Status"] == "paid"


# ── Partial Correction ───────────────────────────────────────────────────────

class TestPartialCorrection:
    def test_quantity_correction(self):
        """Partial correction reducing quantity."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        corrections = [{"product_id": 1, "new_quantity": 7, "new_unit_price": 18.0}]
        fk_id = fk.create_partial_correction(
            fv_id, reason="Qty adjustment", fk_date=str(date.today()),
            user_id=1, corrections=corrections,
        )
        fk_doc = fk.get_by_pk(fk_id)
        assert fk_doc["FK_Type"] == "partial_correction"
        # Correction = (7 * 18) - (10 * 18) = -54.0
        assert fk_doc["TotalCorrection"] == pytest.approx(-54.0)

    def test_price_correction(self):
        """Partial correction changing unit price."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        corrections = [{"product_id": 1, "new_quantity": 10, "new_unit_price": 15.0}]
        fk_id = fk.create_partial_correction(
            fv_id, reason="Price adjustment", fk_date=str(date.today()),
            user_id=1, corrections=corrections,
        )
        fk_doc = fk.get_by_pk(fk_id)
        # Correction = (10 * 15) - (10 * 18) = -30.0
        assert fk_doc["TotalCorrection"] == pytest.approx(-30.0)

    def test_fv_total_adjusted(self):
        """FV.TotalNet is adjusted by the correction amount."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        original_total = fv.get_by_pk(fv_id)["TotalNet"]
        corrections = [{"product_id": 1, "new_quantity": 8, "new_unit_price": 18.0}]
        fk.create_partial_correction(
            fv_id, reason="Qty adj", fk_date=str(date.today()),
            user_id=1, corrections=corrections,
        )
        new_total = fv.get_by_pk(fv_id)["TotalNet"]
        # Should be 180 + (-36) = 144
        assert new_total == pytest.approx(144.0)

    def test_stock_restored_for_qty_decrease(self):
        """With reverse_stock=True and qty decreased, stock is restored."""
        stock_before = products.get_stock(1)
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        stock_after_wz = products.get_stock(1)

        corrections = [{"product_id": 1, "new_quantity": 6, "new_unit_price": 18.0}]
        fk.create_partial_correction(
            fv_id, reason="Return 4", fk_date=str(date.today()),
            user_id=1, corrections=corrections, reverse_stock=True,
        )
        # 4 units returned to stock
        assert products.get_stock(1) == stock_after_wz + 4

    def test_items_show_both_values(self):
        """FK_Items record both original and corrected values."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        corrections = [{"product_id": 1, "new_quantity": 7, "new_unit_price": 16.0}]
        fk_id = fk.create_partial_correction(
            fv_id, reason="Adj", fk_date=str(date.today()),
            user_id=1, corrections=corrections,
        )
        items = fk.fetch_items(fk_id)
        assert len(items) == 1
        it = items[0]
        assert it["OrigQuantity"] == 10
        assert it["CorrQuantity"] == 7
        assert it["OrigUnitPrice"] == 18.0
        assert it["CorrUnitPrice"] == 16.0

    def test_unknown_product_ignored(self):
        """Corrections for products not in the FV are silently ignored."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        corrections = [{"product_id": 9999, "new_quantity": 5, "new_unit_price": 10.0}]
        fk_id = fk.create_partial_correction(
            fv_id, reason="Bad product", fk_date=str(date.today()),
            user_id=1, corrections=corrections,
        )
        fk_doc = fk.get_by_pk(fk_id)
        assert fk_doc["TotalCorrection"] == 0.0


# ── Cancellation ─────────────────────────────────────────────────────────────

class TestCancellation:
    def test_creates_cancellation_type(self):
        """create_cancellation produces FK_Type='cancellation'."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        fk_id = fk.create_cancellation(
            fv_id, reason="Void invoice", fk_date=str(date.today()),
            user_id=1,
        )
        fk_doc = fk.get_by_pk(fk_id)
        assert fk_doc["FK_Type"] == "cancellation"

    def test_fv_marked_cancelled(self):
        """The original FV is marked as cancelled."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        fk.create_cancellation(
            fv_id, reason="Void", fk_date=str(date.today()), user_id=1,
        )
        fv_doc = fv.get_by_pk(fv_id)
        assert fv_doc["Status"] == "cancelled"

    def test_total_correction_is_full_negative(self):
        """TotalCorrection == -original TotalNet."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        fk_id = fk.create_cancellation(
            fv_id, reason="Void", fk_date=str(date.today()), user_id=1,
        )
        fk_doc = fk.get_by_pk(fk_id)
        assert fk_doc["TotalCorrection"] == pytest.approx(-180.0)


# ── FV integration ───────────────────────────────────────────────────────────

class TestFVIntegration:
    def test_fv_get_by_pk_includes_fk_summary(self):
        """get_by_pk returns FK_Count and FK_TotalCorrection."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        fv_doc = fv.get_by_pk(fv_id)
        assert fv_doc["FK_Count"] == 0
        assert fv_doc["FK_TotalCorrection"] == 0.0

        fk.create_full_reversal(
            fv_id, reason="Return", fk_date=str(date.today()), user_id=1,
        )
        fv_doc = fv.get_by_pk(fv_id)
        assert fv_doc["FK_Count"] == 1
        assert fv_doc["FK_TotalCorrection"] == pytest.approx(-180.0)

    def test_fetch_for_fv(self):
        """fetch_for_fv lists all FK linked to an FV."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        assert fk.fetch_for_fv(fv_id) == []
        fk.create_full_reversal(
            fv_id, reason="R1", fk_date=str(date.today()), user_id=1,
        )
        linked = fk.fetch_for_fv(fv_id)
        assert len(linked) == 1
        assert linked[0]["FK_Type"] == "full_reversal"

    def test_fk_number_sequential(self):
        """FK documents get sequential numbering."""
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        fk_id1 = fk.create_full_reversal(
            fv_id, reason="R1", fk_date=str(date.today()), user_id=1,
        )

        fv_id2, _ = _make_fv_with_items(items=[(2, 5, 19.0)])
        fk_id2 = fk.create_full_reversal(
            fv_id2, reason="R2", fk_date=str(date.today()), user_id=1,
        )
        doc1 = fk.get_by_pk(fk_id1)
        doc2 = fk.get_by_pk(fk_id2)
        assert doc1["FK_Number"].endswith("/001")
        assert doc2["FK_Number"].endswith("/002")

    def test_nonexistent_fv_raises(self):
        """Creating FK for a non-existent FV raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            fk.create_full_reversal(
                99999, reason="Bad", fk_date=str(date.today()), user_id=1,
            )


# ── Search and listing ───────────────────────────────────────────────────────

class TestFKListing:
    def test_fetch_all(self):
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        fk.create_full_reversal(
            fv_id, reason="R", fk_date=str(date.today()), user_id=1,
        )
        rows = fk.fetch_all()
        assert len(rows) >= 1

    def test_search_by_fk_number(self):
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        fk_id = fk.create_full_reversal(
            fv_id, reason="R", fk_date=str(date.today()), user_id=1,
        )
        fk_doc = fk.get_by_pk(fk_id)
        results = fk.search(fk_doc["FK_Number"])
        assert len(results) >= 1

    def test_search_by_customer(self):
        fv_id, _ = _make_fv_with_items(items=[(1, 10, 18.0)])
        fk.create_full_reversal(
            fv_id, reason="R", fk_date=str(date.today()), user_id=1,
        )
        results = fk.search("Alfreds")
        assert len(results) >= 1
