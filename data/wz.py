from __future__ import annotations
"""data/wz.py — WZ (Wydanie Zewnętrzne) data access."""
from db import get_connection, next_doc_number
from data.products import apply_stock_delta


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT w.WZ_ID, w.WZ_Number, w.WZ_Date, c.CompanyName AS Customer,
                  w.Status,
                  COALESCE(SUM(wi.UnitPrice * wi.Quantity), 0.0) AS Total
           FROM WZ w
           LEFT JOIN Customers c ON w.CustomerID = c.CustomerID
           LEFT JOIN WZ_Items wi ON w.WZ_ID = wi.WZ_ID
           GROUP BY w.WZ_ID
           ORDER BY w.WZ_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        """SELECT w.WZ_ID, w.WZ_Number, w.WZ_Date, c.CompanyName AS Customer,
                  w.Status,
                  COALESCE(SUM(wi.UnitPrice * wi.Quantity), 0.0) AS Total
           FROM WZ w
           LEFT JOIN Customers c ON w.CustomerID = c.CustomerID
           LEFT JOIN WZ_Items wi ON w.WZ_ID = wi.WZ_ID
           WHERE w.WZ_Number LIKE ? OR c.CompanyName LIKE ?
           GROUP BY w.WZ_ID
           ORDER BY w.WZ_ID DESC""",
        (like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT w.*, c.CompanyName
           FROM WZ w
           LEFT JOIN Customers c ON w.CustomerID = c.CustomerID
           WHERE w.WZ_ID = ?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_items(wz_id) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT wi.ProductID, p.ProductName, wi.Quantity, wi.UnitPrice,
                  wi.UnitPrice * wi.Quantity AS LineTotal
           FROM WZ_Items wi
           JOIN Products p ON wi.ProductID = p.ProductID
           WHERE wi.WZ_ID = ?
           ORDER BY p.ProductName""",
        (wz_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_issued_for_customer(customer_id: str) -> list:
    """Return WZ docs with status 'issued' for a given customer (for FV creation)."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT w.WZ_ID, w.WZ_Number, w.WZ_Date,
                  COALESCE(SUM(wi.UnitPrice * wi.Quantity), 0.0) AS Total
           FROM WZ w
           LEFT JOIN WZ_Items wi ON w.WZ_ID = wi.WZ_ID
           WHERE w.CustomerID = ? AND w.Status = 'issued'
           GROUP BY w.WZ_ID
           ORDER BY w.WZ_Date""",
        (customer_id,),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def create_draft(customer_id: str, wz_date: str, order_id=None, notes: str = "") -> int:
    """Create a WZ document in 'draft' status. Returns WZ_ID."""
    conn = get_connection()
    number = next_doc_number("WZ", conn)
    cur = conn.execute(
        "INSERT INTO WZ (WZ_Number, OrderID, CustomerID, WZ_Date, Status, Notes) "
        "VALUES (?,?,?,?,'draft',?)",
        (number, order_id or None, customer_id, wz_date, notes or None),
    )
    wz_id = cur.lastrowid
    conn.commit()
    conn.close()
    return wz_id


def add_item(wz_id: int, product_id: int, quantity: int, unit_price: float) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO WZ_Items (WZ_ID, ProductID, Quantity, UnitPrice) VALUES (?,?,?,?)",
        (wz_id, product_id, quantity, unit_price),
    )
    conn.commit()
    conn.close()


def remove_item(wz_id: int, product_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "DELETE FROM WZ_Items WHERE WZ_ID=? AND ProductID=?", (wz_id, product_id)
    )
    conn.commit()
    conn.close()


def issue(wz_id: int) -> None:
    """Set WZ status to 'issued' and decrement stock for each item."""
    from data.settings import get_backorder_allowed
    conn = get_connection()
    wz = conn.execute("SELECT Status FROM WZ WHERE WZ_ID=?", (wz_id,)).fetchone()
    if not wz:
        conn.close()
        raise ValueError(f"WZ #{wz_id} not found.")
    if wz[0] != "draft":
        conn.close()
        raise ValueError(f"WZ #{wz_id} is already {wz[0]}.")
    items = conn.execute(
        "SELECT ProductID, Quantity FROM WZ_Items WHERE WZ_ID=?", (wz_id,)
    ).fetchall()
    if not items:
        conn.close()
        raise ValueError("Cannot issue a WZ with no items.")
    if not get_backorder_allowed():
        for row in items:
            product_id, qty = row[0], row[1]
            avail_row = conn.execute(
                "SELECT UnitsInStock, ProductName FROM Products WHERE ProductID=?",
                (product_id,),
            ).fetchone()
            if avail_row is None:
                conn.close()
                raise ValueError(f"Product #{product_id} not found.")
            if qty > avail_row[0]:
                conn.close()
                raise ValueError(
                    f"Insufficient stock for '{avail_row[1]}': "
                    f"{avail_row[0]} available, {qty} requested."
                )
    for row in items:
        apply_stock_delta(row[0], -row[1], conn)
    conn.execute("UPDATE WZ SET Status='issued' WHERE WZ_ID=?", (wz_id,))
    conn.commit()
    conn.close()


def fetch_for_order(order_id: int) -> list:
    """Return all WZ docs linked to a given order."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT WZ_ID, WZ_Number, Status FROM WZ WHERE OrderID=?", (order_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_from_order(order_id: int, wz_date: str) -> int:
    """Create and immediately issue a WZ from an existing order's line items.
    If backorders are disabled, quantities are clamped to available stock.
    Raises ValueError if all lines would be clamped to zero.
    """
    from data.settings import get_backorder_allowed
    conn = get_connection()
    # Guard: prevent issuing a second WZ for the same order
    existing = conn.execute(
        "SELECT WZ_ID, WZ_Number FROM WZ WHERE OrderID=?", (order_id,)
    ).fetchone()
    if existing:
        conn.close()
        raise ValueError(
            f"WZ {existing[1]} already exists for Order #{order_id}."
        )
    order = conn.execute(
        "SELECT CustomerID FROM Orders WHERE OrderID=?", (order_id,)
    ).fetchone()
    if not order:
        conn.close()
        raise ValueError(f"Order #{order_id} not found.")
    customer_id = order[0]
    lines = conn.execute(
        "SELECT ProductID, UnitPrice, Quantity FROM OrderDetails WHERE OrderID=?",
        (order_id,),
    ).fetchall()
    if not lines:
        conn.close()
        raise ValueError("Order has no line items.")
    backorder = get_backorder_allowed()
    number = next_doc_number("WZ", conn)
    cur = conn.execute(
        "INSERT INTO WZ (WZ_Number, OrderID, CustomerID, WZ_Date, Status) "
        "VALUES (?,?,?,?,'draft')",
        (number, order_id, customer_id, wz_date),
    )
    wz_id = cur.lastrowid
    items_added = 0
    for row in lines:
        product_id, unit_price, qty = row[0], row[1], row[2]
        if not backorder:
            avail = conn.execute(
                "SELECT UnitsInStock FROM Products WHERE ProductID=?", (product_id,)
            ).fetchone()
            available = avail[0] if avail else 0
            qty = min(qty, available)
        if qty > 0:
            conn.execute(
                "INSERT INTO WZ_Items (WZ_ID, ProductID, Quantity, UnitPrice) VALUES (?,?,?,?)",
                (wz_id, product_id, qty, unit_price),
            )
            apply_stock_delta(product_id, -qty, conn)
            items_added += 1
    if items_added == 0:
        conn.execute("DELETE FROM WZ WHERE WZ_ID=?", (wz_id,))
        conn.commit()
        conn.close()
        raise ValueError("All line items have zero stock. Cannot create WZ.")
    conn.execute("UPDATE WZ SET Status='issued' WHERE WZ_ID=?", (wz_id,))
    conn.commit()
    conn.close()
    return wz_id


def delete(pk) -> None:
    conn = get_connection()
    wz = conn.execute("SELECT Status FROM WZ WHERE WZ_ID=?", (pk,)).fetchone()
    if wz and wz[0] == "issued":
        raise ValueError("Cannot delete an issued WZ. Reverse stock manually.")
    conn.execute("DELETE FROM WZ WHERE WZ_ID=?", (pk,))
    conn.commit()
    conn.close()
