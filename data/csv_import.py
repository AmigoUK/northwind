"""data/csv_import.py — CSV import for master data tables."""
from __future__ import annotations

import csv
import os
import sqlite3
from collections import defaultdict

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
            "OrderID", "CustomerID", "EmployeeID",
            "OrderDate", "RequiredDate", "ShippedDate",
            "ShipVia", "Freight", "ShipName", "ShipAddress",
            "ShipCity", "ShipRegion", "ShipPostalCode", "ShipCountry",
            # line-item columns (denormalized import)
            "ProductID", "Quantity", "UnitPrice", "Discount",
        ],
        "pk": "OrderID",
    },
}

# Alias mappings: normalised header → canonical column name (or None = display-only, skip on import)
_ALIASES: dict[str, dict[str, str | None]] = {
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
        # display-only aliases → None (skip on import)
        "suppliername": None,
        "categoryname": None,
    },
    "Categories": {
        "id": "CategoryID",
        "categoryname": "CategoryName",
    },
    "Orders": {
        "id": "OrderID",
        "customer": "CustomerID",
        "employee": "EmployeeID",
        "orderdate": "OrderDate",
        "shipped": "ShippedDate",
        "qty": "Quantity",
        # display-only aliases → None (skip on import)
        "customername": None,
        "employeename": None,
        "shippername": None,
        "productname": None,
    },
}

# Map normalised header → canonical column name for each table
_HEADER_MAPS: dict[str, dict[str, str]] = {}
for _tbl, _cfg in TABLE_CONFIGS.items():
    _map = {col.lower().replace(" ", ""): col for col in _cfg["columns"]}
    # Merge aliases (don't overwrite existing canonical names; skip display-only None aliases)
    for alias, canon in _ALIASES.get(_tbl, {}).items():
        if canon is not None:
            _map.setdefault(alias, canon)
    _HEADER_MAPS[_tbl] = _map


def check_headers(
    table: str,
    csv_headers: list[str],
) -> tuple[bool, dict[str, str]]:
    """
    Returns (all_required_matched, auto_mapping).
    auto_mapping: {raw_csv_col → canonical_db_col} for every recognised header.
    all_required_matched: True if every required column has a match.
    """
    cfg = TABLE_CONFIGS[table]
    header_map = _HEADER_MAPS[table]
    auto_mapping: dict[str, str] = {}
    for raw in csv_headers:
        normalised = raw.strip().lower().replace(" ", "")
        if normalised in header_map:
            auto_mapping[raw] = header_map[normalised]
    mapped = set(auto_mapping.values())
    all_ok = all(r in mapped for r in cfg["required"])
    return all_ok, auto_mapping


def parse_csv(
    path: str,
    table: str,
    col_mapping_override: dict[str, str] | None = None,
) -> tuple[list[dict], list[str]]:
    """Read CSV, validate headers against TABLE_CONFIGS.

    If col_mapping_override is provided, it is used directly instead of auto-detection.
    Columns mapped to None or "" in the override are skipped.

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

        if col_mapping_override is not None:
            # Use the provided override mapping; skip columns mapped to None/""
            col_mapping: dict[str, str] = {
                raw: canon
                for raw, canon in col_mapping_override.items()
                if canon
            }
        else:
            # Build mapping: csv_header → canonical column
            col_mapping = {}
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
            if "CategoryID" in row:
                if not _is_numeric(row["CategoryID"]):
                    result = conn.execute(
                        "SELECT CategoryID FROM Categories WHERE CategoryName = ?",
                        (row["CategoryID"],),
                    ).fetchone()
                    row["CategoryID"] = result[0] if result else None
                elif row["CategoryID"] is not None:
                    # Validate the numeric ID exists (FK constraints are enforced)
                    result = conn.execute(
                        "SELECT 1 FROM Categories WHERE CategoryID = ?",
                        (int(row["CategoryID"]),),
                    ).fetchone()
                    if not result:
                        row["CategoryID"] = None

            if "SupplierID" in row:
                if not _is_numeric(row["SupplierID"]):
                    result = conn.execute(
                        "SELECT SupplierID FROM Suppliers WHERE CompanyName = ?",
                        (row["SupplierID"],),
                    ).fetchone()
                    row["SupplierID"] = result[0] if result else None
                elif row["SupplierID"] is not None:
                    # Validate the numeric ID exists (FK constraints are enforced)
                    result = conn.execute(
                        "SELECT 1 FROM Suppliers WHERE SupplierID = ?",
                        (int(row["SupplierID"]),),
                    ).fetchone()
                    if not result:
                        row["SupplierID"] = None

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

            if "EmployeeID" in row:
                if not _is_numeric(row["EmployeeID"]):
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
                elif row["EmployeeID"] is not None:
                    # Validate the numeric ID exists (FK constraint is enforced)
                    result = conn.execute(
                        "SELECT 1 FROM Employees WHERE EmployeeID = ?",
                        (int(row["EmployeeID"]),),
                    ).fetchone()
                    if not result:
                        row["EmployeeID"] = None

            if "ShipVia" in row and row["ShipVia"] is not None:
                try:
                    ship_via = int(row["ShipVia"])
                    result = conn.execute(
                        "SELECT 1 FROM Shippers WHERE ShipperID = ?", (ship_via,)
                    ).fetchone()
                    row["ShipVia"] = ship_via if result else None
                except (ValueError, TypeError):
                    row["ShipVia"] = None
    finally:
        conn.close()

    # Products only: normalise Discontinued string → int so that the
    # `1 if data.get("Discontinued") else 0` check in products.insert() works.
    if table == "Products" and "Discontinued" in row:
        val = row["Discontinued"]
        row["Discontinued"] = 1 if str(val or "0") == "1" else 0


def import_rows_orders(rows: list[dict]) -> dict:
    """Import denormalized order rows (one row per line item).

    Groups rows by OrderID:
    - OrderID present + exists in DB → UPDATE Orders header, DELETE + re-INSERT OrderDetails
    - OrderID absent/not in DB → INSERT INTO Orders + INSERT OrderDetails
    - Rows where ProductID is None → header-only (zero line items)
    - Multiple rows with blank OrderID → all grouped into ONE new order

    Returns {"inserted": N, "updated": N, "skipped": N, "errors": [...]}.
    """
    inserted = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    # Group rows by OrderID (None key = new orders to create)
    groups: dict = defaultdict(list)
    for row in rows:
        order_id = row.get("OrderID")
        try:
            order_id = int(order_id) if order_id is not None else None
        except (ValueError, TypeError):
            order_id = None
        groups[order_id].append(row)

    conn = get_connection()
    try:
        for order_id, order_rows in groups.items():
            try:
                # Use the first row for header data
                header_row = dict(order_rows[0])

                # Resolve FK names for header fields
                _resolve_fk_names("Orders", header_row)

                # Collect line items (rows where ProductID is present)
                line_items = []
                for r in order_rows:
                    pid = r.get("ProductID")
                    if pid is not None:
                        try:
                            pid = int(pid)
                        except (ValueError, TypeError):
                            pid = None
                    if pid is not None:
                        # Validate product exists (FK constraint is enforced)
                        if not conn.execute(
                            "SELECT 1 FROM Products WHERE ProductID = ?", (pid,)
                        ).fetchone():
                            pid = None
                    if pid is not None:
                        qty = r.get("Quantity")
                        price = r.get("UnitPrice")
                        discount = r.get("Discount")
                        try:
                            qty = int(qty) if qty is not None else 1
                        except (ValueError, TypeError):
                            qty = 1
                        try:
                            price = float(price) if price is not None else 0.0
                        except (ValueError, TypeError):
                            price = 0.0
                        try:
                            discount = float(discount) if discount is not None else 0.0
                        except (ValueError, TypeError):
                            discount = 0.0
                        line_items.append((pid, qty, price, discount))

                if order_id is not None:
                    # Check if order exists in DB
                    exists = conn.execute(
                        "SELECT 1 FROM Orders WHERE OrderID=?", (order_id,)
                    ).fetchone()
                    if exists:
                        # UPDATE header
                        conn.execute(
                            """UPDATE Orders SET CustomerID=?, EmployeeID=?, OrderDate=?,
                               RequiredDate=?, ShippedDate=?, ShipVia=?, Freight=?,
                               ShipName=?, ShipAddress=?, ShipCity=?, ShipRegion=?,
                               ShipPostalCode=?, ShipCountry=?
                               WHERE OrderID=?""",
                            (
                                header_row.get("CustomerID"),
                                header_row.get("EmployeeID") or None,
                                header_row.get("OrderDate") or None,
                                header_row.get("RequiredDate") or None,
                                header_row.get("ShippedDate") or None,
                                header_row.get("ShipVia") or None,
                                header_row.get("Freight", 0.0) or 0.0,
                                header_row.get("ShipName") or None,
                                header_row.get("ShipAddress") or None,
                                header_row.get("ShipCity") or None,
                                header_row.get("ShipRegion") or None,
                                header_row.get("ShipPostalCode") or None,
                                header_row.get("ShipCountry") or None,
                                order_id,
                            ),
                        )
                        # DELETE and re-INSERT OrderDetails
                        conn.execute(
                            "DELETE FROM OrderDetails WHERE OrderID=?", (order_id,)
                        )
                        for pid, qty, price, disc in line_items:
                            conn.execute(
                                "INSERT INTO OrderDetails (OrderID, ProductID, UnitPrice, Quantity, Discount) "
                                "VALUES (?,?,?,?,?)",
                                (order_id, pid, price, qty, disc),
                            )
                        conn.commit()
                        updated += 1
                        continue
                    # OrderID not in DB → treat as INSERT with provided ID
                    conn.execute(
                        """INSERT INTO Orders
                           (OrderID, CustomerID, EmployeeID, OrderDate, RequiredDate, ShippedDate,
                            ShipVia, Freight, ShipName, ShipAddress, ShipCity, ShipRegion,
                            ShipPostalCode, ShipCountry)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            order_id,
                            header_row.get("CustomerID"),
                            header_row.get("EmployeeID") or None,
                            header_row.get("OrderDate") or None,
                            header_row.get("RequiredDate") or None,
                            header_row.get("ShippedDate") or None,
                            header_row.get("ShipVia") or None,
                            header_row.get("Freight", 0.0) or 0.0,
                            header_row.get("ShipName") or None,
                            header_row.get("ShipAddress") or None,
                            header_row.get("ShipCity") or None,
                            header_row.get("ShipRegion") or None,
                            header_row.get("ShipPostalCode") or None,
                            header_row.get("ShipCountry") or None,
                        ),
                    )
                else:
                    # INSERT new order (auto-generate OrderID)
                    cur = conn.execute(
                        """INSERT INTO Orders
                           (CustomerID, EmployeeID, OrderDate, RequiredDate, ShippedDate,
                            ShipVia, Freight, ShipName, ShipAddress, ShipCity, ShipRegion,
                            ShipPostalCode, ShipCountry)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            header_row.get("CustomerID"),
                            header_row.get("EmployeeID") or None,
                            header_row.get("OrderDate") or None,
                            header_row.get("RequiredDate") or None,
                            header_row.get("ShippedDate") or None,
                            header_row.get("ShipVia") or None,
                            header_row.get("Freight", 0.0) or 0.0,
                            header_row.get("ShipName") or None,
                            header_row.get("ShipAddress") or None,
                            header_row.get("ShipCity") or None,
                            header_row.get("ShipRegion") or None,
                            header_row.get("ShipPostalCode") or None,
                            header_row.get("ShipCountry") or None,
                        ),
                    )
                    order_id = cur.lastrowid

                for pid, qty, price, disc in line_items:
                    conn.execute(
                        "INSERT INTO OrderDetails (OrderID, ProductID, UnitPrice, Quantity, Discount) "
                        "VALUES (?,?,?,?,?)",
                        (order_id, pid, price, qty, disc),
                    )
                conn.commit()
                inserted += 1

            except sqlite3.IntegrityError as exc:
                conn.rollback()
                skipped += 1
                errors.append(f"Order {order_id}: integrity error — {exc}")
            except Exception as exc:
                conn.rollback()
                errors.append(f"Order {order_id}: {exc}")
    finally:
        conn.close()

    return {"inserted": inserted, "updated": updated, "skipped": skipped, "errors": errors}


def import_rows(table: str, rows: list[dict]) -> dict:
    """Insert rows using existing data layer functions.

    Returns {"inserted": N, "updated": N, "skipped": N, "errors": [(row_num, msg)]}.
    """
    if table == "Orders":
        return import_rows_orders(rows)

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
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
        except Exception as exc:
            row_errors.append((i, str(exc)))

    return {"inserted": inserted, "updated": 0, "skipped": skipped, "errors": row_errors}
