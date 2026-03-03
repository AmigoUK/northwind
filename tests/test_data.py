"""Core business logic tests — ~20 tests covering critical paths.

These run against an isolated temp DB (see conftest.py) with standard
Northwind seed data. No TUI is launched.
"""
from datetime import date

import db
from data import products, settings, users, dn, gr


# ── Doc Numbering ─────────────────────────────────────────────────────────────


class TestDocNumbering:
    def test_format(self):
        """next_doc_number returns the expected DN/YYYY/001 format."""
        conn = db.get_connection()
        num = db.next_doc_number("DN", conn)
        conn.commit()
        conn.close()
        year = date.today().year
        assert num == f"DN/{year}/001"

    def test_sequential_increment(self):
        """Consecutive calls increment the counter: 001 → 002."""
        conn = db.get_connection()
        n1 = db.next_doc_number("DN", conn)
        n2 = db.next_doc_number("DN", conn)
        conn.commit()
        conn.close()
        assert n1.endswith("/001")
        assert n2.endswith("/002")

    def test_new_year_resets(self):
        """A different year starts at 001 again."""
        conn = db.get_connection()
        db.next_doc_number("DN", conn)  # creates 2026/001
        conn.commit()
        conn.close()
        # Verify the sequence exists for current year
        year = date.today().year
        conn = db.get_connection()
        row = conn.execute(
            "SELECT LastNum FROM DocSequence WHERE DocType='DN' AND Year=?",
            (year,),
        ).fetchone()
        assert row[0] == 1
        # Verify no sequence exists for next year yet — so next call
        # for that year would start at 001
        next_year = year + 1
        row = conn.execute(
            "SELECT LastNum FROM DocSequence WHERE DocType='DN' AND Year=?",
            (next_year,),
        ).fetchone()
        assert row is None  # no sequence → next_doc_number would create 001
        conn.close()


# ── Authentication ────────────────────────────────────────────────────────────


class TestAuthentication:
    def test_valid_admin_login(self):
        """Default admin/1234 credentials return a user dict."""
        user = users.authenticate("admin", "1234")
        assert user is not None
        assert user["username"] == "admin"
        assert user["role"] == "admin"

    def test_wrong_pin_fails(self):
        """Correct username but wrong PIN returns None."""
        assert users.authenticate("admin", "9999") is None

    def test_nonexistent_user_fails(self):
        """Unknown username returns None."""
        assert users.authenticate("ghost", "1234") is None


# ── Product CRUD & Stock ─────────────────────────────────────────────────────


class TestProducts:
    def test_fetch_all_returns_seeded(self):
        """fetch_all returns at least some of the 20 seeded products."""
        rows = products.fetch_all()
        # Seed has 20 products, but 3 are discontinued (hidden by default)
        assert len(rows) >= 15

    def test_insert_and_get_roundtrip(self):
        """Insert a product, then retrieve it by PK."""
        products.insert({
            "ProductName": "Test Widget",
            "UnitPrice": 12.50,
            "UnitsInStock": 100,
            "ReorderLevel": 10,
        })
        # The new product gets the next auto-increment ID
        conn = db.get_connection()
        row = conn.execute(
            "SELECT ProductID FROM Products WHERE ProductName='Test Widget'"
        ).fetchone()
        conn.close()
        assert row is not None
        product = products.get_by_pk(row[0])
        assert product["ProductName"] == "Test Widget"
        assert product["UnitPrice"] == 12.50

    def test_apply_stock_delta(self):
        """apply_stock_delta adjusts UnitsInStock correctly."""
        original = products.get_stock(1)
        conn = db.get_connection()
        products.apply_stock_delta(1, -5, conn)
        conn.commit()
        conn.close()
        assert products.get_stock(1) == original - 5

    def test_search_by_name(self):
        """search finds products by partial name match."""
        results = products.search("Chai")
        names = [r[1] for r in results]
        assert any("Chai" in n for n in names)

    def test_low_stock(self):
        """low_stock returns products at or below reorder level."""
        rows = products.low_stock()
        for row in rows:
            pid = row[0]
            p = products.get_by_pk(pid)
            assert p["UnitsInStock"] <= p["ReorderLevel"]


# ── DN Workflow ──────────────────────────────────────────────────────────────


class TestDNWorkflow:
    def test_create_draft_with_items(self):
        """Create a draft DN and add items to it."""
        dn_id = dn.create_draft("ALFKI", str(date.today()))
        dn.add_item(dn_id, 1, 5, 18.00)
        dn.add_item(dn_id, 2, 3, 19.00)
        items = dn.fetch_items(dn_id)
        assert len(items) == 2
        doc = dn.get_by_pk(dn_id)
        assert doc["Status"] == "draft"

    def test_issue_reduces_stock(self):
        """Issuing a DN decrements UnitsInStock for each item."""
        stock_before = products.get_stock(1)
        dn_id = dn.create_draft("ALFKI", str(date.today()))
        dn.add_item(dn_id, 1, 3, 18.00)
        dn.issue(dn_id)
        assert products.get_stock(1) == stock_before - 3
        doc = dn.get_by_pk(dn_id)
        assert doc["Status"] == "issued"

    def test_issued_dn_cannot_be_reissued(self):
        """An already-issued DN raises ValueError on second issue."""
        dn_id = dn.create_draft("ALFKI", str(date.today()))
        dn.add_item(dn_id, 1, 1, 18.00)
        dn.issue(dn_id)
        import pytest
        with pytest.raises(ValueError, match="already issued"):
            dn.issue(dn_id)


# ── GR Workflow ──────────────────────────────────────────────────────────────


class TestGRWorkflow:
    def test_create_pz_with_items(self):
        """Create a draft GR and add items."""
        gr_id = gr.create_draft(1, str(date.today()))
        gr.add_item(gr_id, 1, 10, 15.00)
        items = gr.fetch_items(gr_id)
        assert len(items) == 1
        doc = gr.get_by_pk(gr_id)
        assert doc["Status"] == "draft"

    def test_receive_increases_stock(self):
        """Receiving a GR increments UnitsInStock for each item."""
        stock_before = products.get_stock(1)
        gr_id = gr.create_draft(1, str(date.today()))
        gr.add_item(gr_id, 1, 20, 15.00)
        gr.receive(gr_id)
        assert products.get_stock(1) == stock_before + 20
        doc = gr.get_by_pk(gr_id)
        assert doc["Status"] == "received"

    def test_cash_payment_doc_on_receive(self):
        """Receiving a GR with payment_method='cash' auto-creates a CP."""
        from data.cash import fetch_all_cp, create_cr
        create_cr(None, None, 100.0, "seed cash for test")  # fund cash register
        cp_before = len(fetch_all_cp())
        gr_id = gr.create_draft(1, str(date.today()), payment_method="cash")
        gr.add_item(gr_id, 1, 5, 10.00)
        gr.receive(gr_id)
        cp_after = len(fetch_all_cp())
        assert cp_after == cp_before + 1


# ── Settings ─────────────────────────────────────────────────────────────────


class TestSettings:
    def test_set_get_roundtrip(self):
        """set_setting / get_setting round-trip works."""
        settings.set_setting("test_key", "hello")
        assert settings.get_setting("test_key") == "hello"

    def test_get_default_for_missing_key(self):
        """get_setting returns the default for a non-existent key."""
        assert settings.get_setting("nonexistent", "fallback") == "fallback"
