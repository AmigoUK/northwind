"""Tests for CN (Credit Note) business logic.

Covers: full reversal, partial correction, cancellation,
payment/stock/pricing effects, and edge cases.
"""
from datetime import date

import pytest

import db
from data import products, dn, inv, cn


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_inv_with_items(customer_id="ALFKI", items=None):
    """Create DN → issue → INV. Returns (inv_id, dn_id).
    items = [(product_id, qty, price), ...]
    """
    if items is None:
        items = [(1, 10, 18.0)]
    dn_id = dn.create_draft(customer_id, str(date.today()))
    for pid, qty, price in items:
        dn.add_item(dn_id, pid, qty, price)
    dn.issue(dn_id)
    inv_id = inv.create(customer_id, [dn_id], str(date.today()))
    return inv_id, dn_id


# ── Full Reversal ────────────────────────────────────────────────────────────

class TestFullReversal:
    def test_creates_cn_with_correct_total(self):
        """Full reversal: TotalCorrection == -TotalNet."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        inv_doc = inv.get_by_pk(inv_id)
        original_total = inv_doc["TotalNet"]

        cn_id = cn.create_full_reversal(
            inv_id, reason="Customer return", cn_date=str(date.today()),
            user_id=1,
        )
        cn_doc = cn.get_by_pk(cn_id)
        assert cn_doc is not None
        assert cn_doc["CN_Type"] == "full_reversal"
        assert cn_doc["TotalCorrection"] == -original_total
        assert cn_doc["Reason"] == "Customer return"

    def test_items_corrected_to_zero(self):
        """All CN_Items have CorrQuantity=0."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        cn_id = cn.create_full_reversal(
            inv_id, reason="Error", cn_date=str(date.today()), user_id=1,
        )
        items = cn.fetch_items(cn_id)
        assert len(items) >= 1
        for item in items:
            assert item["CorrQuantity"] == 0

    def test_adjusts_inv_total_net(self):
        """INV.TotalNet is adjusted downward by TotalCorrection."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        cn.create_full_reversal(
            inv_id, reason="Return", cn_date=str(date.today()), user_id=1,
        )
        inv_doc = inv.get_by_pk(inv_id)
        assert inv_doc["TotalNet"] == 0.0

    def test_reverts_dn_to_issued(self):
        """Linked DN goes from 'invoiced' back to 'issued'."""
        inv_id, dn_id = _make_inv_with_items()
        assert dn.get_by_pk(dn_id)["Status"] == "invoiced"
        cn.create_full_reversal(
            inv_id, reason="Return", cn_date=str(date.today()), user_id=1,
        )
        assert dn.get_by_pk(dn_id)["Status"] == "issued"

    def test_stock_restored_when_reverse_stock_true(self):
        """With reverse_stock=True, stock is restored for all items."""
        stock_before = products.get_stock(1)
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        stock_after_dn = products.get_stock(1)
        assert stock_after_dn == stock_before - 10

        cn.create_full_reversal(
            inv_id, reason="Return", cn_date=str(date.today()),
            user_id=1, reverse_stock=True,
        )
        assert products.get_stock(1) == stock_before

    def test_stock_not_changed_when_reverse_stock_false(self):
        """Without reverse_stock, stock is unchanged."""
        stock_before = products.get_stock(1)
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        stock_after_dn = products.get_stock(1)

        cn.create_full_reversal(
            inv_id, reason="Return", cn_date=str(date.today()),
            user_id=1, reverse_stock=False,
        )
        assert products.get_stock(1) == stock_after_dn

    def test_inv_status_recalculated(self):
        """After full reversal with no payments, INV goes to 'cancelled'."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        cn.create_full_reversal(
            inv_id, reason="Return", cn_date=str(date.today()), user_id=1,
        )
        inv_doc = inv.get_by_pk(inv_id)
        # TotalNet == 0, PaidAmount == 0 → cancelled
        assert inv_doc["Status"] == "cancelled"

    def test_overpayment_flagged(self):
        """If INV was already paid, status becomes 'paid' (overpayment scenario)."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        inv.record_payment(inv_id, 180.0, "cash")
        inv_doc = inv.get_by_pk(inv_id)
        assert inv_doc["Status"] == "paid"

        cn.create_full_reversal(
            inv_id, reason="Return", cn_date=str(date.today()), user_id=1,
        )
        inv_doc = inv.get_by_pk(inv_id)
        # TotalNet == 0, PaidAmount == 180 → paid (overpayment)
        assert inv_doc["Status"] == "paid"


# ── Partial Correction ───────────────────────────────────────────────────────

class TestPartialCorrection:
    def test_quantity_correction(self):
        """Partial correction reducing quantity."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        corrections = [{"product_id": 1, "new_quantity": 7, "new_unit_price": 18.0}]
        cn_id = cn.create_partial_correction(
            inv_id, reason="Qty adjustment", cn_date=str(date.today()),
            user_id=1, corrections=corrections,
        )
        cn_doc = cn.get_by_pk(cn_id)
        assert cn_doc["CN_Type"] == "partial_correction"
        # Correction = (7 * 18) - (10 * 18) = -54.0
        assert cn_doc["TotalCorrection"] == pytest.approx(-54.0)

    def test_price_correction(self):
        """Partial correction changing unit price."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        corrections = [{"product_id": 1, "new_quantity": 10, "new_unit_price": 15.0}]
        cn_id = cn.create_partial_correction(
            inv_id, reason="Price adjustment", cn_date=str(date.today()),
            user_id=1, corrections=corrections,
        )
        cn_doc = cn.get_by_pk(cn_id)
        # Correction = (10 * 15) - (10 * 18) = -30.0
        assert cn_doc["TotalCorrection"] == pytest.approx(-30.0)

    def test_inv_total_adjusted(self):
        """INV.TotalNet is adjusted by the correction amount."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        original_total = inv.get_by_pk(inv_id)["TotalNet"]
        corrections = [{"product_id": 1, "new_quantity": 8, "new_unit_price": 18.0}]
        cn.create_partial_correction(
            inv_id, reason="Qty adj", cn_date=str(date.today()),
            user_id=1, corrections=corrections,
        )
        new_total = inv.get_by_pk(inv_id)["TotalNet"]
        # Should be 180 + (-36) = 144
        assert new_total == pytest.approx(144.0)

    def test_stock_restored_for_qty_decrease(self):
        """With reverse_stock=True and qty decreased, stock is restored."""
        stock_before = products.get_stock(1)
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        stock_after_dn = products.get_stock(1)

        corrections = [{"product_id": 1, "new_quantity": 6, "new_unit_price": 18.0}]
        cn.create_partial_correction(
            inv_id, reason="Return 4", cn_date=str(date.today()),
            user_id=1, corrections=corrections, reverse_stock=True,
        )
        # 4 units returned to stock
        assert products.get_stock(1) == stock_after_dn + 4

    def test_items_show_both_values(self):
        """CN_Items record both original and corrected values."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        corrections = [{"product_id": 1, "new_quantity": 7, "new_unit_price": 16.0}]
        cn_id = cn.create_partial_correction(
            inv_id, reason="Adj", cn_date=str(date.today()),
            user_id=1, corrections=corrections,
        )
        items = cn.fetch_items(cn_id)
        assert len(items) == 1
        it = items[0]
        assert it["OrigQuantity"] == 10
        assert it["CorrQuantity"] == 7
        assert it["OrigUnitPrice"] == 18.0
        assert it["CorrUnitPrice"] == 16.0

    def test_unknown_product_ignored(self):
        """Corrections for products not in the INV are silently ignored."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        corrections = [{"product_id": 9999, "new_quantity": 5, "new_unit_price": 10.0}]
        cn_id = cn.create_partial_correction(
            inv_id, reason="Bad product", cn_date=str(date.today()),
            user_id=1, corrections=corrections,
        )
        cn_doc = cn.get_by_pk(cn_id)
        assert cn_doc["TotalCorrection"] == 0.0


# ── Cancellation ─────────────────────────────────────────────────────────────

class TestCancellation:
    def test_creates_cancellation_type(self):
        """create_cancellation produces CN_Type='cancellation'."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        cn_id = cn.create_cancellation(
            inv_id, reason="Void invoice", cn_date=str(date.today()),
            user_id=1,
        )
        cn_doc = cn.get_by_pk(cn_id)
        assert cn_doc["CN_Type"] == "cancellation"

    def test_inv_marked_cancelled(self):
        """The original INV is marked as cancelled."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        cn.create_cancellation(
            inv_id, reason="Void", cn_date=str(date.today()), user_id=1,
        )
        inv_doc = inv.get_by_pk(inv_id)
        assert inv_doc["Status"] == "cancelled"

    def test_total_correction_is_full_negative(self):
        """TotalCorrection == -original TotalNet."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        cn_id = cn.create_cancellation(
            inv_id, reason="Void", cn_date=str(date.today()), user_id=1,
        )
        cn_doc = cn.get_by_pk(cn_id)
        assert cn_doc["TotalCorrection"] == pytest.approx(-180.0)


# ── INV integration ───────────────────────────────────────────────────────────

class TestINVIntegration:
    def test_inv_get_by_pk_includes_cn_summary(self):
        """get_by_pk returns CN_Count and CN_TotalCorrection."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        inv_doc = inv.get_by_pk(inv_id)
        assert inv_doc["CN_Count"] == 0
        assert inv_doc["CN_TotalCorrection"] == 0.0

        cn.create_full_reversal(
            inv_id, reason="Return", cn_date=str(date.today()), user_id=1,
        )
        inv_doc = inv.get_by_pk(inv_id)
        assert inv_doc["CN_Count"] == 1
        assert inv_doc["CN_TotalCorrection"] == pytest.approx(-180.0)

    def test_fetch_for_inv(self):
        """fetch_for_inv lists all CN linked to an INV."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        assert cn.fetch_for_inv(inv_id) == []
        cn.create_full_reversal(
            inv_id, reason="R1", cn_date=str(date.today()), user_id=1,
        )
        linked = cn.fetch_for_inv(inv_id)
        assert len(linked) == 1
        assert linked[0]["CN_Type"] == "full_reversal"

    def test_cn_number_sequential(self):
        """CN documents get sequential numbering."""
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        cn_id1 = cn.create_full_reversal(
            inv_id, reason="R1", cn_date=str(date.today()), user_id=1,
        )

        inv_id2, _ = _make_inv_with_items(items=[(2, 5, 19.0)])
        cn_id2 = cn.create_full_reversal(
            inv_id2, reason="R2", cn_date=str(date.today()), user_id=1,
        )
        doc1 = cn.get_by_pk(cn_id1)
        doc2 = cn.get_by_pk(cn_id2)
        assert doc1["CN_Number"].endswith("/001")
        assert doc2["CN_Number"].endswith("/002")

    def test_nonexistent_inv_raises(self):
        """Creating CN for a non-existent INV raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            cn.create_full_reversal(
                99999, reason="Bad", cn_date=str(date.today()), user_id=1,
            )


# ── Search and listing ───────────────────────────────────────────────────────

class TestCNListing:
    def test_fetch_all(self):
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        cn.create_full_reversal(
            inv_id, reason="R", cn_date=str(date.today()), user_id=1,
        )
        rows = cn.fetch_all()
        assert len(rows) >= 1

    def test_search_by_cn_number(self):
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        cn_id = cn.create_full_reversal(
            inv_id, reason="R", cn_date=str(date.today()), user_id=1,
        )
        cn_doc = cn.get_by_pk(cn_id)
        results = cn.search(cn_doc["CN_Number"])
        assert len(results) >= 1

    def test_search_by_customer(self):
        inv_id, _ = _make_inv_with_items(items=[(1, 10, 18.0)])
        cn.create_full_reversal(
            inv_id, reason="R", cn_date=str(date.today()), user_id=1,
        )
        results = cn.search("Alfreds")
        assert len(results) >= 1
