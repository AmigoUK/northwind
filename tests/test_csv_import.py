"""Tests for data/csv_import.py — parse_csv() and import_rows()."""
import csv
import os
import textwrap

from data.csv_import import parse_csv, import_rows, check_headers


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


# ── New tests for v2.11 ───────────────────────────────────────────────────────


# 1. check_headers — full match
def test_check_headers_full_match(tmp_path, test_db):
    headers = [
        "CustomerID", "CompanyName", "ContactName", "ContactTitle",
        "Address", "City", "Region", "PostalCode", "Country", "Phone", "Fax",
    ]
    all_ok, auto_mapping = check_headers("Customers", headers)
    assert all_ok is True
    assert auto_mapping["CustomerID"] == "CustomerID"
    assert auto_mapping["CompanyName"] == "CompanyName"
    assert auto_mapping["Fax"] == "Fax"


# 2. check_headers — partial match (missing required)
def test_check_headers_partial_match(tmp_path, test_db):
    # Only ContactName → missing CustomerID and CompanyName (both required)
    headers = ["ContactName", "City"]
    all_ok, auto_mapping = check_headers("Customers", headers)
    assert all_ok is False
    # ContactName and City should still be in auto_mapping
    assert "ContactName" in auto_mapping
    assert "City" in auto_mapping
    # CustomerID is not mapped
    assert "CustomerID" not in auto_mapping


# 3. parse_csv with col_mapping_override
def test_parse_csv_col_mapping_override(tmp_path, test_db):
    path = _write_csv(tmp_path, "cust_custom.csv", """
        cust_id,company,extra_col
        XCUST,Custom Corp,ignored
    """)
    override = {"cust_id": "CustomerID", "company": "CompanyName"}
    rows, errors = parse_csv(path, "Customers", col_mapping_override=override)
    assert len(rows) == 1
    assert rows[0]["CustomerID"] == "XCUST"
    assert rows[0]["CompanyName"] == "Custom Corp"
    # extra_col not in override → not present in row
    assert "extra_col" not in rows[0]


# 4. fetch_all_with_lines returns ProductID, Quantity, UnitPrice, Discount
def test_orders_export_has_line_items(tmp_path, test_db):
    from data.orders import fetch_all_with_lines
    rows = fetch_all_with_lines()
    # There are seeded orders with line items; find one that has a ProductID
    rows_with_items = [r for r in rows if r["ProductID"] is not None]
    assert len(rows_with_items) > 0
    row = rows_with_items[0]
    assert "ProductID" in row
    assert "Quantity" in row
    assert "UnitPrice" in row
    assert "Discount" in row


# 5. fetch_all_with_lines includes shipping fields
def test_orders_export_has_shipping_fields(tmp_path, test_db):
    from data.orders import fetch_all_with_lines
    rows = fetch_all_with_lines()
    assert len(rows) > 0
    row = rows[0]
    for field in ("ShipName", "ShipAddress", "ShipCity", "ShipCountry"):
        assert field in row


# 6. Orders import — blank OrderID creates new order with OrderDetails
def test_orders_import_new_order(tmp_path, test_db):
    from db import get_connection
    rows = [
        {
            "OrderID": None,
            "CustomerID": "ALFKI",
            "OrderDate": "2026-01-01",
            "ProductID": "1",
            "Quantity": "5",
            "UnitPrice": "18.00",
            "Discount": "0",
        }
    ]
    result = import_rows("Orders", rows)
    assert result["inserted"] == 1
    assert result["errors"] == []
    # Verify OrderDetails were created
    conn = get_connection()
    new_order_id = conn.execute(
        "SELECT OrderID FROM Orders WHERE OrderDate='2026-01-01' ORDER BY OrderID DESC"
    ).fetchone()
    assert new_order_id is not None
    details = conn.execute(
        "SELECT * FROM OrderDetails WHERE OrderID=?", (new_order_id[0],)
    ).fetchall()
    assert len(details) == 1
    assert details[0]["ProductID"] == 1
    conn.close()


# 7. Orders import — existing OrderID updates header + replaces OrderDetails
def test_orders_import_update_existing(tmp_path, test_db):
    from db import get_connection
    # Order 10248 exists in seed with Freight=32.38
    rows = [
        {
            "OrderID": "10248",
            "CustomerID": "ALFKI",
            "Freight": "99.99",
            "OrderDate": "1996-07-04",
            "ProductID": "1",
            "Quantity": "3",
            "UnitPrice": "18.00",
            "Discount": "0",
        }
    ]
    result = import_rows("Orders", rows)
    assert result["updated"] == 1
    conn = get_connection()
    order = conn.execute("SELECT Freight FROM Orders WHERE OrderID=10248").fetchone()
    assert abs(order["Freight"] - 99.99) < 0.01
    details = conn.execute(
        "SELECT * FROM OrderDetails WHERE OrderID=10248"
    ).fetchall()
    # Old details replaced with the single new line
    assert len(details) == 1
    assert details[0]["ProductID"] == 1
    conn.close()


# 8. Orders import — header-only (no ProductID) → 0 OrderDetails rows
def test_orders_import_header_only(tmp_path, test_db):
    from db import get_connection
    rows = [
        {
            "OrderID": None,
            "CustomerID": "ANATR",
            "OrderDate": "2026-02-01",
            "ProductID": None,
            "Quantity": None,
            "UnitPrice": None,
            "Discount": None,
        }
    ]
    result = import_rows("Orders", rows)
    assert result["inserted"] == 1
    conn = get_connection()
    new_oid = conn.execute(
        "SELECT OrderID FROM Orders WHERE OrderDate='2026-02-01'"
    ).fetchone()
    assert new_oid is not None
    details = conn.execute(
        "SELECT COUNT(*) FROM OrderDetails WHERE OrderID=?", (new_oid[0],)
    ).fetchone()
    assert details[0] == 0
    conn.close()


# 9. Orders import — 3-line-item order → 3 OrderDetails rows
def test_orders_import_multi_items(tmp_path, test_db):
    from db import get_connection
    rows = [
        {"OrderID": None, "CustomerID": "AROUT", "OrderDate": "2026-03-01",
         "ProductID": "1", "Quantity": "2", "UnitPrice": "18.00", "Discount": "0"},
        {"OrderID": None, "CustomerID": "AROUT", "OrderDate": "2026-03-01",
         "ProductID": "2", "Quantity": "4", "UnitPrice": "19.00", "Discount": "0"},
        {"OrderID": None, "CustomerID": "AROUT", "OrderDate": "2026-03-01",
         "ProductID": "3", "Quantity": "6", "UnitPrice": "10.00", "Discount": "0"},
    ]
    result = import_rows("Orders", rows)
    assert result["inserted"] == 1
    conn = get_connection()
    new_oid = conn.execute(
        "SELECT OrderID FROM Orders WHERE OrderDate='2026-03-01'"
    ).fetchone()
    assert new_oid is not None
    details = conn.execute(
        "SELECT COUNT(*) FROM OrderDetails WHERE OrderID=?", (new_oid[0],)
    ).fetchone()
    assert details[0] == 3
    conn.close()


# 10. Orders full round-trip: export to CSV → import back → verify
def test_orders_full_roundtrip(tmp_path, test_db):
    from data.orders import fetch_all_with_lines
    from screens.export_helpers import write_csv
    from db import get_connection

    _EXPORT_HEADERS = [
        "OrderID", "CustomerID", "CustomerName", "EmployeeID", "EmployeeName",
        "OrderDate", "RequiredDate", "ShippedDate", "ShipVia", "ShipperName",
        "Freight", "ShipName", "ShipAddress", "ShipCity", "ShipRegion",
        "ShipPostalCode", "ShipCountry",
        "ProductID", "ProductName", "Quantity", "UnitPrice", "Discount",
    ]

    # Export order 10248 rows
    all_rows = fetch_all_with_lines()
    order_rows = [r for r in all_rows if r["OrderID"] == 10248]
    assert len(order_rows) > 0

    csv_path = str(tmp_path / "orders_rt.csv")
    data_rows = [[r.get(col) for col in _EXPORT_HEADERS] for r in order_rows]
    write_csv(csv_path, _EXPORT_HEADERS, data_rows)

    # Modify the order in DB so we can confirm the import updates it
    conn = get_connection()
    conn.execute("UPDATE Orders SET Freight=0 WHERE OrderID=10248")
    conn.commit()
    conn.close()

    # Import back
    rows, errors = parse_csv(csv_path, "Orders")
    assert not (errors and not rows), f"parse errors: {errors}"
    result = import_rows("Orders", rows)
    assert result["updated"] == 1

    # Verify freight was restored
    conn = get_connection()
    order = conn.execute("SELECT Freight FROM Orders WHERE OrderID=10248").fetchone()
    assert order["Freight"] > 0
    conn.close()


# 11. Customers fetch_all_full has all 11 columns
def test_customers_full_export_has_all_cols(tmp_path, test_db):
    from data.customers import fetch_all_full
    rows = fetch_all_full()
    assert len(rows) > 0
    expected_cols = {
        "CustomerID", "CompanyName", "ContactName", "ContactTitle",
        "Address", "City", "Region", "PostalCode", "Country", "Phone", "Fax",
    }
    actual_cols = set(rows[0].keys())
    assert expected_cols == actual_cols


# 13. Products with numeric FK IDs that don't exist are imported with NULL FKs
def test_import_products_nonexistent_fk_ids_become_null(tmp_path, test_db):
    """FK constraints are enforced (PRAGMA foreign_keys=ON).  Numeric SupplierID/
    CategoryID values that don't exist in the DB must be nullified so the INSERT
    doesn't fail — products must be inserted, not silently skipped."""
    # Use IDs that are NOT in the seeded DB (9999)
    rows = [{"ProductName": "Ghost Widget", "SupplierID": "9999", "CategoryID": "9999",
             "UnitPrice": "5.00", "UnitsInStock": "10", "Discontinued": "0"}]
    result = import_rows("Products", rows)
    assert result["inserted"] == 1, f"Expected 1 inserted, got: {result}"
    assert result["skipped"] == 0

    import data.products as pdata
    from db import get_connection
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM Products WHERE ProductName='Ghost Widget'"
    ).fetchone()
    conn.close()
    assert row is not None, "Product was not inserted"
    assert row["SupplierID"] is None, "SupplierID should be nullified when FK not found"
    assert row["CategoryID"] is None, "CategoryID should be nullified when FK not found"


# 12. Products fetch_all_full has both FK IDs and display names
def test_products_full_export_has_both_ids_and_names(tmp_path, test_db):
    from data.products import fetch_all_full
    rows = fetch_all_full()
    assert len(rows) > 0
    row = rows[0]
    assert "SupplierID" in row
    assert "SupplierName" in row
    assert "CategoryID" in row
    assert "CategoryName" in row
    # Values should be present (seeded products have supplier + category)
    assert row["SupplierID"] is not None
    assert row["CategoryID"] is not None
