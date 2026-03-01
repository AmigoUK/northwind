"""Tests for data/csv_import.py — parse_csv() and import_rows()."""
import os
import textwrap

from data.csv_import import parse_csv, import_rows


def _write_csv(tmp_path, filename, content):
    """Write CSV content to a temp file and return its path."""
    path = str(tmp_path / filename)
    with open(path, "w") as f:
        f.write(textwrap.dedent(content).lstrip())
    return path


# ── parse_csv tests ──────────────────────────────────────────────────────────


def test_parse_customers_valid(tmp_path, test_db):
    path = _write_csv(tmp_path, "cust.csv", """
        CustomerID,CompanyName,City
        TEST1,Test Corp,London
        TEST2,Acme Inc,Berlin
    """)
    rows, errors = parse_csv(path, "Customers")
    assert len(rows) == 2
    assert rows[0]["CustomerID"] == "TEST1"
    assert rows[0]["CompanyName"] == "Test Corp"
    assert rows[0]["City"] == "London"
    # Optional column not in CSV → None
    assert rows[0].get("ContactName") is None


def test_parse_case_insensitive_headers(tmp_path, test_db):
    path = _write_csv(tmp_path, "cust.csv", """
        customerid, company name ,city
        TEST1,Test Corp,London
    """)
    rows, errors = parse_csv(path, "Customers")
    assert len(rows) == 1
    assert rows[0]["CustomerID"] == "TEST1"
    assert rows[0]["CompanyName"] == "Test Corp"


def test_parse_missing_required_column(tmp_path, test_db):
    path = _write_csv(tmp_path, "cust.csv", """
        City,ContactName
        London,John
    """)
    rows, errors = parse_csv(path, "Customers")
    assert len(rows) == 0
    assert any("Missing required" in e for e in errors)


def test_parse_extra_columns_warning(tmp_path, test_db):
    path = _write_csv(tmp_path, "cust.csv", """
        CustomerID,CompanyName,ExtraCol
        TEST1,Test Corp,ignored
    """)
    rows, errors = parse_csv(path, "Customers")
    assert len(rows) == 1
    assert any("Ignored" in e for e in errors)
    assert "ExtraCol" not in rows[0]


def test_parse_file_not_found(tmp_path, test_db):
    rows, errors = parse_csv("/nonexistent/path.csv", "Customers")
    assert len(rows) == 0
    assert any("not found" in e for e in errors)


def test_parse_empty_values_become_none(tmp_path, test_db):
    path = _write_csv(tmp_path, "cust.csv", """
        CustomerID,CompanyName,City,Region
        TEST1,Test Corp,,
    """)
    rows, errors = parse_csv(path, "Customers")
    assert rows[0]["City"] is None
    assert rows[0]["Region"] is None


def test_parse_categories(tmp_path, test_db):
    path = _write_csv(tmp_path, "cat.csv", """
        CategoryName,Description
        Widgets,Various widgets
    """)
    rows, errors = parse_csv(path, "Categories")
    assert len(rows) == 1
    assert rows[0]["CategoryName"] == "Widgets"


def test_parse_products(tmp_path, test_db):
    path = _write_csv(tmp_path, "prod.csv", """
        ProductName,UnitPrice,UnitsInStock
        Widget X,9.99,100
    """)
    rows, errors = parse_csv(path, "Products")
    assert len(rows) == 1
    assert rows[0]["ProductName"] == "Widget X"
    assert rows[0]["UnitPrice"] == "9.99"


def test_parse_suppliers(tmp_path, test_db):
    path = _write_csv(tmp_path, "supp.csv", """
        CompanyName,ContactName,City
        Acme Supply,John Doe,Chicago
    """)
    rows, errors = parse_csv(path, "Suppliers")
    assert len(rows) == 1
    assert rows[0]["CompanyName"] == "Acme Supply"


# ── import_rows tests ────────────────────────────────────────────────────────


def test_import_customers(tmp_path, test_db):
    path = _write_csv(tmp_path, "cust.csv", """
        CustomerID,CompanyName,City
        XIMPT,Import Corp,Paris
    """)
    rows, _ = parse_csv(path, "Customers")
    result = import_rows("Customers", rows)
    assert result["inserted"] == 1
    assert result["skipped"] == 0

    import data.customers as cdata
    rec = cdata.get_by_pk("XIMPT")
    assert rec is not None
    assert rec["CompanyName"] == "Import Corp"


def test_import_customers_duplicate_skipped(tmp_path, test_db):
    path = _write_csv(tmp_path, "cust.csv", """
        CustomerID,CompanyName
        XDUP1,First Import
    """)
    rows, _ = parse_csv(path, "Customers")
    r1 = import_rows("Customers", rows)
    assert r1["inserted"] == 1

    # Import same file again
    r2 = import_rows("Customers", rows)
    assert r2["inserted"] == 0
    assert r2["skipped"] == 1


def test_import_categories(tmp_path, test_db):
    path = _write_csv(tmp_path, "cat.csv", """
        CategoryName,Description
        Test Widgets,For testing
    """)
    rows, _ = parse_csv(path, "Categories")
    result = import_rows("Categories", rows)
    assert result["inserted"] == 1


def test_import_suppliers(tmp_path, test_db):
    path = _write_csv(tmp_path, "supp.csv", """
        CompanyName,City,Country
        Test Supplies Inc,Tokyo,Japan
    """)
    rows, _ = parse_csv(path, "Suppliers")
    result = import_rows("Suppliers", rows)
    assert result["inserted"] == 1


def test_import_products(tmp_path, test_db):
    path = _write_csv(tmp_path, "prod.csv", """
        ProductName,UnitPrice,UnitsInStock,Discontinued
        Test Widget,19.99,50,0
    """)
    rows, _ = parse_csv(path, "Products")
    result = import_rows("Products", rows)
    assert result["inserted"] == 1


def test_import_customer_missing_id(tmp_path, test_db):
    rows = [{"CompanyName": "No ID Corp"}]
    result = import_rows("Customers", rows)
    assert result["inserted"] == 0
    assert len(result["errors"]) == 1
    assert "CustomerID" in result["errors"][0][1]
