"""data/csv_import.py — CSV import for master data tables."""
from __future__ import annotations

import csv
import os
import sqlite3

from data import customers as cust_data
from data import suppliers as supp_data
from data import products as prod_data
from data import categories as cat_data
from db import get_connection

TABLE_CONFIGS = {
    "Customers": {
        "required": ["CustomerID", "CompanyName"],
        "columns": [
            "CustomerID", "CompanyName", "ContactName", "ContactTitle",
            "Address", "City", "Region", "PostalCode", "Country", "Phone", "Fax",
        ],
        "pk": "CustomerID",
    },
    "Suppliers": {
        "required": ["CompanyName"],
        "columns": [
            "CompanyName", "ContactName", "ContactTitle", "Address",
            "City", "Region", "PostalCode", "Country", "Phone", "Fax", "HomePage",
        ],
        "pk": "SupplierID",
    },
    "Products": {
        "required": ["ProductName"],
        "columns": [
            "ProductName", "SupplierID", "CategoryID", "QuantityPerUnit",
            "UnitPrice", "UnitsInStock", "UnitsOnOrder", "ReorderLevel", "Discontinued",
        ],
        "pk": "ProductID",
    },
    "Categories": {
        "required": ["CategoryName"],
        "columns": ["CategoryName", "Description"],
        "pk": "CategoryID",
    },
    "Orders": {
        "required": [],          # all schema columns are nullable
        "columns": [
            "CustomerID", "EmployeeID", "OrderDate", "RequiredDate", "ShippedDate",
            "ShipVia", "Freight", "ShipName", "ShipAddress",
            "ShipCity", "ShipRegion", "ShipPostalCode", "ShipCountry",
        ],
        "pk": "OrderID",
    },
}

# Alias mappings: export display header → canonical column name
_ALIASES: dict[str, dict[str, str]] = {
    "Customers": {
        "id": "CustomerID",
        "company": "CompanyName",
        "contact": "ContactName",
    },
    "Suppliers": {
        "id": "SupplierID",
        "company": "CompanyName",
        "contact": "ContactName",
    },
    "Products": {
        "id": "ProductID",
        "productname": "ProductName",
        "category": "CategoryID",
        "supplier": "SupplierID",
        "price": "UnitPrice",
        "instock": "UnitsInStock",
    },
    "Categories": {
        "id": "CategoryID",
        "categoryname": "CategoryName",
    },
    "Orders": {
        "id": "OrderID",
        # Export cols: "Customer" → CustomerID (value is CompanyName)
        #              "Employee" → EmployeeID (value is "Last, First")
        #              "Order Date" → OrderDate
        #              "Shipped"    → ShippedDate
        #              "Total"      → no mapping (computed aggregate, ignored)
        "customer": "CustomerID",
        "employee": "EmployeeID",
        "orderdate": "OrderDate",
        "shipped": "ShippedDate",
    },
}

# Map normalised header → canonical column name for each table
_HEADER_MAPS: dict[str, dict[str, str]] = {}
for _tbl, _cfg in TABLE_CONFIGS.items():
    _map = {col.lower().replace(" ", ""): col for col in _cfg["columns"]}
    # Merge aliases (don't overwrite existing canonical names)
    for alias, canon in _ALIASES.get(_tbl, {}).items():
        _map.setdefault(alias, canon)
    _HEADER_MAPS[_tbl] = _map


def parse_csv(path: str, table: str) -> tuple[list[dict], list[str]]:
    """Read CSV, validate headers against TABLE_CONFIGS.

    Returns (rows as list of dicts, list of validation errors).
    Missing required columns → error (file rejected).
    Extra/unrecognised columns → warning only.
    """
    cfg = TABLE_CONFIGS[table]
    header_map = _HEADER_MAPS[table]
    errors: list[str] = []

    expanded = os.path.expanduser(path)
    if not os.path.isfile(expanded):
        return [], [f"File not found: {path}"]

    with open(expanded, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return [], ["CSV file is empty or has no header row."]

        # Build mapping: csv_header → canonical column
        col_mapping: dict[str, str] = {}
        unrecognised: list[str] = []
        for raw_header in reader.fieldnames:
            normalised = raw_header.strip().lower().replace(" ", "")
            if normalised in header_map:
                col_mapping[raw_header] = header_map[normalised]
            else:
                unrecognised.append(raw_header.strip())

        if unrecognised:
            errors.append(f"Ignored columns: {', '.join(unrecognised)}")

        # Check required columns are present
        mapped_cols = set(col_mapping.values())
        missing = [r for r in cfg["required"] if r not in mapped_cols]
        if missing:
            return [], [f"Missing required columns: {', '.join(missing)}"]

        rows: list[dict] = []
        for i, raw_row in enumerate(reader, start=2):  # row 2 = first data row
            row: dict = {}
            for csv_col, canon_col in col_mapping.items():
                val = raw_row.get(csv_col, "")
                row[canon_col] = val.strip() if val and val.strip() else None
            rows.append(row)

    return rows, errors


def _resolve_fk_names(table: str, row: dict) -> None:
    """Resolve display-name strings to proper FK values in-place.

    Products
    --------
    Export writes CategoryName / CompanyName into Category / Supplier columns.
    These are looked up and replaced with the integer FK IDs.  Unresolvable
    names fall back to None (both columns are nullable).
    Also normalises Discontinued "0"/"1" strings to integers.

    Orders
    ------
    Export writes CompanyName into Customer, and "Last, First" into Employee.
    Customer  → CustomerID (text PK)  via Customers.CompanyName lookup;
                also accepts a value that already IS a valid CustomerID code.
    Employee  → EmployeeID (int)      via Employees.LastName/FirstName lookup.
    Unresolvable names fall back to None (all Orders FK columns are nullable).
    """
    if table not in ("Products", "Orders"):
        return

    def _is_numeric(val) -> bool:
        if val is None:
            return True
        try:
            int(val)
            return True
        except (ValueError, TypeError):
            return False

    conn = get_connection()
    try:
        if table == "Products":
            if "CategoryID" in row and not _is_numeric(row["CategoryID"]):
                result = conn.execute(
                    "SELECT CategoryID FROM Categories WHERE CategoryName = ?",
                    (row["CategoryID"],),
                ).fetchone()
                row["CategoryID"] = result[0] if result else None

            if "SupplierID" in row and not _is_numeric(row["SupplierID"]):
                result = conn.execute(
                    "SELECT SupplierID FROM Suppliers WHERE CompanyName = ?",
                    (row["SupplierID"],),
                ).fetchone()
                row["SupplierID"] = result[0] if result else None

        elif table == "Orders":
            if "CustomerID" in row and row["CustomerID"]:
                val = row["CustomerID"]
                # Try to resolve as CompanyName (typical from export)
                result = conn.execute(
                    "SELECT CustomerID FROM Customers WHERE CompanyName = ?", (val,)
                ).fetchone()
                if result:
                    row["CustomerID"] = result[0]
                else:
                    # Accept as-is only if it's already a valid CustomerID code
                    exists = conn.execute(
                        "SELECT 1 FROM Customers WHERE CustomerID = ?", (val,)
                    ).fetchone()
                    row["CustomerID"] = val if exists else None

            if "EmployeeID" in row and not _is_numeric(row["EmployeeID"]):
                val = str(row["EmployeeID"])
                if "," in val:
                    last, first = (p.strip() for p in val.split(",", 1))
                    result = conn.execute(
                        "SELECT EmployeeID FROM Employees WHERE LastName=? AND FirstName=?",
                        (last, first),
                    ).fetchone()
                else:
                    result = conn.execute(
                        "SELECT EmployeeID FROM Employees WHERE LastName=?", (val,)
                    ).fetchone()
                row["EmployeeID"] = result[0] if result else None
    finally:
        conn.close()

    # Products only: normalise Discontinued string → int so that the
    # `1 if data.get("Discontinued") else 0` check in products.insert() works.
    if table == "Products" and "Discontinued" in row:
        val = row["Discontinued"]
        row["Discontinued"] = 1 if str(val or "0") == "1" else 0


def import_rows(table: str, rows: list[dict]) -> dict:
    """Insert rows using existing data layer functions.

    Returns {"inserted": N, "skipped": N, "errors": [(row_num, msg)]}.
    """
    inserted = 0
    skipped = 0
    row_errors: list[tuple[int, str]] = []

    for i, row in enumerate(rows, start=1):
        try:
            _resolve_fk_names(table, row)
            if table == "Customers":
                cid = row.get("CustomerID")
                if not cid:
                    row_errors.append((i, "Missing CustomerID"))
                    continue
                cust_data.insert(cid, row)
            elif table == "Suppliers":
                supp_data.insert(row)
            elif table == "Products":
                prod_data.insert(row)
            elif table == "Categories":
                cat_data.insert(row)
            elif table == "Orders":
                from data import orders as ord_data
                ord_data.insert_header(row)
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
        except Exception as exc:
            row_errors.append((i, str(exc)))

    return {"inserted": inserted, "skipped": skipped, "errors": row_errors}
