"""Tests for data/demo.py — demo data insert, clean, and full DB lifecycle."""
import re

import pytest

from data.demo import (
    has_demo_data, has_master_data, demo_status,
    insert_demo_data, clean_demo_data,
)
from data.users import verify_admin_pin
from data.settings import get_setting
from db import get_connection, init_db


class TestHasDemoData:
    def test_false_on_fresh_db(self):
        assert has_demo_data() is False

    def test_true_after_insert(self):
        insert_demo_data()
        assert has_demo_data() is True

    def test_false_after_clean(self):
        insert_demo_data()
        clean_demo_data()
        assert has_demo_data() is False


class TestInsertDemoData:
    def test_creates_expected_dn_count(self):
        counts = insert_demo_data()
        assert counts["DN"] >= 1500

    def test_creates_expected_inv_count(self):
        counts = insert_demo_data()
        assert counts["INV"] >= 1500

    def test_creates_expected_gr_count(self):
        counts = insert_demo_data()
        assert counts["GR"] >= 500

    def test_creates_cn(self):
        counts = insert_demo_data()
        assert counts["CN"] >= 20

    def test_creates_si_and_so(self):
        counts = insert_demo_data()
        assert counts["SI"] >= 10
        assert counts["SO"] >= 10

    def test_creates_transfer(self):
        counts = insert_demo_data()
        assert counts["transfers"] >= 10

    def test_double_insert_raises(self):
        insert_demo_data()
        with pytest.raises(ValueError, match="already exists"):
            insert_demo_data()


class TestInsertDemoDataScale:
    """Verify count ranges, stock integrity, and determinism of large demo data."""

    def test_no_negative_stock(self):
        insert_demo_data()
        conn = get_connection()
        neg = conn.execute(
            "SELECT COUNT(*) FROM Products WHERE UnitsInStock < 0"
        ).fetchone()[0]
        conn.close()
        assert neg == 0, f"{neg} products have negative stock"

    def test_master_data_expanded(self):
        insert_demo_data()
        conn = get_connection()
        customers = conn.execute("SELECT COUNT(*) FROM Customers").fetchone()[0]
        suppliers = conn.execute("SELECT COUNT(*) FROM Suppliers").fetchone()[0]
        products = conn.execute("SELECT COUNT(*) FROM Products").fetchone()[0]
        conn.close()
        assert customers == 30
        assert suppliers == 15
        assert products == 50

    def test_deterministic_output(self):
        """Same seed produces same counts on two separate runs."""
        counts1 = insert_demo_data()
        clean_demo_data()
        counts2 = insert_demo_data()
        # Compare key doc counts (elapsed_seconds will differ)
        for key in ("DN", "INV", "GR", "CN", "SI", "SO"):
            assert counts1[key] == counts2[key], \
                f"{key}: {counts1[key]} != {counts2[key]}"

    def test_cr_and_cp_created(self):
        counts = insert_demo_data()
        assert counts["CR"] >= 100
        assert counts["CP"] >= 100

    def test_bank_entries_created(self):
        counts = insert_demo_data()
        assert counts["BankEntry"] >= 500

    def test_elapsed_seconds_returned(self):
        counts = insert_demo_data()
        assert "elapsed_seconds" in counts
        assert isinstance(counts["elapsed_seconds"], float)


class TestCleanDemoData:
    def test_removes_all_transactional_data(self):
        insert_demo_data()
        clean_demo_data()
        conn = get_connection()
        for table in ("DN", "INV", "GR", "SI", "SO", "CR", "CP",
                      "BankEntry", "CN"):
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert count == 0, f"{table} still has {count} rows"
        conn.close()

    def test_clears_doc_sequence(self):
        insert_demo_data()
        clean_demo_data()
        conn = get_connection()
        count = conn.execute("SELECT COUNT(*) FROM DocSequence").fetchone()[0]
        conn.close()
        assert count == 0

    def test_master_data_removed(self):
        insert_demo_data()
        clean_demo_data()
        conn = get_connection()
        categories = conn.execute("SELECT COUNT(*) FROM Categories").fetchone()[0]
        customers = conn.execute("SELECT COUNT(*) FROM Customers").fetchone()[0]
        products = conn.execute("SELECT COUNT(*) FROM Products").fetchone()[0]
        orders = conn.execute("SELECT COUNT(*) FROM Orders").fetchone()[0]
        conn.close()
        assert categories == 0
        assert customers == 0
        assert products == 0
        assert orders == 0

    def test_clean_on_empty_db_is_safe(self):
        deleted = clean_demo_data()
        # Only transactional tables should be 0; master tables had seed data
        # After clean, even master is gone
        assert isinstance(deleted, dict)


class TestCleanAfterLarge:
    """Verify clean_demo_data() still works after large insert."""

    def test_clean_removes_all_large_data(self):
        insert_demo_data()
        deleted = clean_demo_data()
        assert deleted["DN"] >= 1500
        assert deleted["INV"] >= 1500
        assert has_demo_data() is False
        assert has_master_data() is False

    def test_reinsert_after_clean(self):
        insert_demo_data()
        clean_demo_data()
        counts = insert_demo_data()
        assert has_demo_data() is True
        assert counts["DN"] >= 1500


class TestCleanPreservesUsersAndSettings:
    def test_users_preserved(self):
        conn = get_connection()
        before = conn.execute("SELECT COUNT(*) FROM AppUsers").fetchone()[0]
        conn.close()
        insert_demo_data()
        clean_demo_data()
        conn = get_connection()
        after = conn.execute("SELECT COUNT(*) FROM AppUsers").fetchone()[0]
        conn.close()
        assert after == before

    def test_custom_settings_preserved(self):
        from data.settings import set_setting
        set_setting("currency_symbol", "£")
        insert_demo_data()
        clean_demo_data()
        assert get_setting("currency_symbol") == "£"


class TestInsertSeedsMasterData:
    def test_insert_recreates_categories_after_clean(self):
        clean_demo_data()
        assert has_master_data() is False
        insert_demo_data()
        conn = get_connection()
        count = conn.execute("SELECT COUNT(*) FROM Categories").fetchone()[0]
        conn.close()
        assert count == 8

    def test_insert_recreates_products_after_clean(self):
        clean_demo_data()
        insert_demo_data()
        conn = get_connection()
        count = conn.execute("SELECT COUNT(*) FROM Products").fetchone()[0]
        conn.close()
        assert count == 50

    def test_insert_clears_production_mode(self):
        clean_demo_data()
        assert get_setting("production_mode") == "true"
        insert_demo_data()
        assert get_setting("production_mode") == "false"


class TestProductionMode:
    def test_clean_sets_production_mode(self):
        insert_demo_data()
        clean_demo_data()
        assert get_setting("production_mode") == "true"

    def test_init_db_skips_seeding_when_production_mode(self):
        insert_demo_data()
        clean_demo_data()
        assert has_master_data() is False
        # init_db should NOT re-seed because production_mode is true
        init_db()
        assert has_master_data() is False

    def test_full_insert_clean_insert_cycle(self):
        insert_demo_data()
        assert has_demo_data() is True
        clean_demo_data()
        assert has_demo_data() is False
        assert has_master_data() is False
        # Re-insert should work — clears production_mode and re-seeds
        counts = insert_demo_data()
        assert has_demo_data() is True
        assert has_master_data() is True
        assert counts["DN"] >= 1500


class TestVerifyAdminPin:
    def test_valid_admin_pin(self):
        assert verify_admin_pin("1234") is True

    def test_invalid_pin(self):
        assert verify_admin_pin("9999") is False

    def test_empty_pin(self):
        assert verify_admin_pin("") is False

    def test_non_admin_pin_rejected(self):
        from data.users import insert as user_insert
        user_insert({
            "username": "regular_user",
            "display_name": "Regular User",
            "pin": "5678",
            "role": "user",
        })
        assert verify_admin_pin("5678") is False


class TestDemoStatus:
    def test_master_data_loaded(self):
        assert demo_status() == "Master data loaded"

    def test_demo_data_present(self):
        insert_demo_data()
        assert demo_status() == "Demo data present"

    def test_clean_production_ready(self):
        clean_demo_data()
        assert demo_status() == "Clean (production-ready)"


class TestFullCycle:
    def test_insert_clean_insert(self):
        insert_demo_data()
        assert has_demo_data() is True
        assert has_master_data() is True
        clean_demo_data()
        assert has_demo_data() is False
        assert has_master_data() is False
        counts = insert_demo_data()
        assert has_demo_data() is True
        assert has_master_data() is True
        assert counts["DN"] >= 1500


class TestDataConsistency:
    """Verify referential integrity and data consistency after demo insert."""

    @pytest.fixture(autouse=True)
    def _with_demo(self):
        insert_demo_data()

    def test_all_data_modules_callable(self):
        """Every data module's fetch_all / search runs without SQL errors."""
        from data import (
            customers, suppliers, products, categories, shippers,
            orders, regions, employees, dn, inv, gr, cn, cash, bank,
            si_so,
        )
        for mod in (customers, suppliers, products, categories, shippers,
                    orders, regions, employees):
            mod.fetch_all()
            mod.search("")
        dn.fetch_all()
        inv.fetch_all()
        gr.fetch_all()
        cn.fetch_all()
        cash.fetch_all_cr()
        cash.fetch_all_cp()
        bank.fetch_all()
        si_so.fetch_all_si()
        si_so.fetch_all_so()

    def test_inv_has_linked_dns(self):
        """Every invoice has at least one linked DN via INV_DN."""
        from data import inv as invdata
        conn = get_connection()
        inv_ids = [r[0] for r in conn.execute(
            "SELECT INV_ID FROM INV LIMIT 50"
        ).fetchall()]
        conn.close()
        assert len(inv_ids) > 0
        for inv_id in inv_ids:
            linked = invdata.fetch_linked_dn(inv_id)
            assert len(linked) > 0, f"INV {inv_id} has no linked DNs"
            for dn in linked:
                assert "DN_ID" in dn
                assert "DN_Number" in dn
                assert "DN_Date" in dn
                assert "Total" in dn

    def test_fk_inv_customer(self):
        """Every INV references a valid CustomerID."""
        conn = get_connection()
        orphans = conn.execute(
            "SELECT i.INV_ID, i.CustomerID FROM INV i "
            "LEFT JOIN Customers c ON i.CustomerID = c.CustomerID "
            "WHERE c.CustomerID IS NULL"
        ).fetchall()
        conn.close()
        assert len(orphans) == 0, f"INVs with invalid CustomerID: {orphans[:5]}"

    def test_fk_dn_customer(self):
        """Every DN references a valid CustomerID."""
        conn = get_connection()
        orphans = conn.execute(
            "SELECT d.DN_ID, d.CustomerID FROM DN d "
            "LEFT JOIN Customers c ON d.CustomerID = c.CustomerID "
            "WHERE c.CustomerID IS NULL"
        ).fetchall()
        conn.close()
        assert len(orphans) == 0, f"DNs with invalid CustomerID: {orphans[:5]}"

    def test_fk_gr_supplier(self):
        """Every GR references a valid SupplierID."""
        conn = get_connection()
        orphans = conn.execute(
            "SELECT g.GR_ID, g.SupplierID FROM GR g "
            "LEFT JOIN Suppliers s ON g.SupplierID = s.SupplierID "
            "WHERE s.SupplierID IS NULL"
        ).fetchall()
        conn.close()
        assert len(orphans) == 0, f"GRs with invalid SupplierID: {orphans[:5]}"

    def test_fk_inv_dn_join(self):
        """Every INV_DN row references valid INV_ID and DN_ID."""
        conn = get_connection()
        bad_inv = conn.execute(
            "SELECT j.INV_ID FROM INV_DN j "
            "LEFT JOIN INV i ON j.INV_ID = i.INV_ID "
            "WHERE i.INV_ID IS NULL"
        ).fetchall()
        bad_dn = conn.execute(
            "SELECT j.DN_ID FROM INV_DN j "
            "LEFT JOIN DN d ON j.DN_ID = d.DN_ID "
            "WHERE d.DN_ID IS NULL"
        ).fetchall()
        conn.close()
        assert len(bad_inv) == 0, f"INV_DN orphan INV refs: {bad_inv[:5]}"
        assert len(bad_dn) == 0, f"INV_DN orphan DN refs: {bad_dn[:5]}"

    def test_no_orphan_line_items(self):
        """DN_Items and GR_Items all reference existing parent docs."""
        conn = get_connection()
        orphan_dn = conn.execute(
            "SELECT di.DN_ID FROM DN_Items di "
            "LEFT JOIN DN d ON di.DN_ID = d.DN_ID "
            "WHERE d.DN_ID IS NULL"
        ).fetchall()
        orphan_gr = conn.execute(
            "SELECT gi.GR_ID FROM GR_Items gi "
            "LEFT JOIN GR g ON gi.GR_ID = g.GR_ID "
            "WHERE g.GR_ID IS NULL"
        ).fetchall()
        conn.close()
        assert len(orphan_dn) == 0, f"Orphan DN_Items: {orphan_dn[:5]}"
        assert len(orphan_gr) == 0, f"Orphan GR_Items: {orphan_gr[:5]}"

    def test_line_items_reference_valid_products(self):
        """All line items reference existing ProductIDs."""
        conn = get_connection()
        bad_dn = conn.execute(
            "SELECT di.ProductID FROM DN_Items di "
            "LEFT JOIN Products p ON di.ProductID = p.ProductID "
            "WHERE p.ProductID IS NULL"
        ).fetchall()
        bad_gr = conn.execute(
            "SELECT gi.ProductID FROM GR_Items gi "
            "LEFT JOIN Products p ON gi.ProductID = p.ProductID "
            "WHERE p.ProductID IS NULL"
        ).fetchall()
        conn.close()
        assert len(bad_dn) == 0, f"DN_Items with invalid ProductID: {bad_dn[:5]}"
        assert len(bad_gr) == 0, f"GR_Items with invalid ProductID: {bad_gr[:5]}"

    def test_no_negative_totals_or_quantities(self):
        """No negative TotalNet on INV; no negative Quantity/Price on items."""
        conn = get_connection()
        neg_inv = conn.execute(
            "SELECT COUNT(*) FROM INV WHERE TotalNet < 0"
        ).fetchone()[0]
        neg_dn_qty = conn.execute(
            "SELECT COUNT(*) FROM DN_Items WHERE Quantity < 0"
        ).fetchone()[0]
        neg_dn_price = conn.execute(
            "SELECT COUNT(*) FROM DN_Items WHERE UnitPrice < 0"
        ).fetchone()[0]
        neg_gr_qty = conn.execute(
            "SELECT COUNT(*) FROM GR_Items WHERE Quantity < 0"
        ).fetchone()[0]
        neg_gr_cost = conn.execute(
            "SELECT COUNT(*) FROM GR_Items WHERE UnitCost < 0"
        ).fetchone()[0]
        conn.close()
        assert neg_inv == 0, f"{neg_inv} invoices with negative TotalNet"
        assert neg_dn_qty == 0, f"{neg_dn_qty} DN items with negative Quantity"
        assert neg_dn_price == 0, f"{neg_dn_price} DN items with negative UnitPrice"
        assert neg_gr_qty == 0, f"{neg_gr_qty} GR items with negative Quantity"
        assert neg_gr_cost == 0, f"{neg_gr_cost} GR items with negative UnitCost"

    def test_doc_number_patterns(self):
        """Document numbers follow expected ABBR/YYYY/NNN patterns."""
        conn = get_connection()
        patterns = {
            "DN": (r"^DN/\d{4}/\d+$", "DN_Number", "DN"),
            "INV": (r"^INV/\d{4}/\d+$", "INV_Number", "INV"),
            "GR": (r"^GR/\d{4}/\d+$", "GR_Number", "GR"),
            "CN": (r"^CN/\d{4}/\d+$", "CN_Number", "CN"),
        }
        for doc_type, (pattern, col, table) in patterns.items():
            rows = conn.execute(f"SELECT {col} FROM {table}").fetchall()
            assert len(rows) > 0, f"No {doc_type} documents found"
            bad = [r[0] for r in rows if not re.match(pattern, r[0])]
            assert len(bad) == 0, (
                f"{doc_type} docs with bad number format: {bad[:5]}"
            )
        conn.close()
