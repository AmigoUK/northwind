"""data/csv_import.py — CSV import for master data tables."""
from __future__ import annotations

import csv
import os
import sqlite3

from data import customers as cust_data
from data import suppliers as supp_data
from data import products as prod_data
from data import categories as cat_data

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
}

# Map normalised header → canonical column name for each table
_HEADER_MAPS: dict[str, dict[str, str]] = {}
for _tbl, _cfg in TABLE_CONFIGS.items():
    _HEADER_MAPS[_tbl] = {col.lower().replace(" ", ""): col for col in _cfg["columns"]}


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


def import_rows(table: str, rows: list[dict]) -> dict:
    """Insert rows using existing data layer functions.

    Returns {"inserted": N, "skipped": N, "errors": [(row_num, msg)]}.
    """
    inserted = 0
    skipped = 0
    row_errors: list[tuple[int, str]] = []

    for i, row in enumerate(rows, start=1):
        try:
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
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
        except Exception as exc:
            row_errors.append((i, str(exc)))

    return {"inserted": inserted, "skipped": skipped, "errors": row_errors}
