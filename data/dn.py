from __future__ import annotations
"""data/dn.py — DN (Delivery Note) data access."""
from db import get_connection, next_doc_number
from data.products import apply_stock_delta


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT w.DN_ID, w.DN_Number, w.DN_Date, c.CompanyName AS Customer,
                  w.Status,
                  COALESCE(SUM(wi.UnitPrice * wi.Quantity), 0.0) AS Total
           FROM DN w
           LEFT JOIN Customers c ON w.CustomerID = c.CustomerID
           LEFT JOIN DN_Items wi ON w.DN_ID = wi.DN_ID
           GROUP BY w.DN_ID
           ORDER BY w.DN_ID DESC"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        """SELECT w.DN_ID, w.DN_Number, w.DN_Date, c.CompanyName AS Customer,
                  w.Status,
                  COALESCE(SUM(wi.UnitPrice * wi.Quantity), 0.0) AS Total
           FROM DN w
           LEFT JOIN Customers c ON w.CustomerID = c.CustomerID
           LEFT JOIN DN_Items wi ON w.DN_ID = wi.DN_ID
           WHERE w.DN_Number LIKE ? OR c.CompanyName LIKE ?
           GROUP BY w.DN_ID
           ORDER BY w.DN_ID DESC""",
        (like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT w.*, c.CompanyName
           FROM DN w
           LEFT JOIN Customers c ON w.CustomerID = c.CustomerID
           WHERE w.DN_ID = ?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_items(dn_id) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT wi.ProductID, p.ProductName, wi.Quantity, wi.UnitPrice,
                  wi.UnitPrice * wi.Quantity AS LineTotal
           FROM DN_Items wi
           JOIN Products p ON wi.ProductID = p.ProductID
           WHERE wi.DN_ID = ?
           ORDER BY p.ProductName""",
        (dn_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_issued_for_customer(customer_id: str) -> list:
    """Return DN docs with status 'issued' for a given customer (for INV creation)."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT w.DN_ID, w.DN_Number, w.DN_Date,
                  COALESCE(SUM(wi.UnitPrice * wi.Quantity), 0.0) AS Total
           FROM DN w
           LEFT JOIN DN_Items wi ON w.DN_ID = wi.DN_ID
           WHERE w.CustomerID = ? AND w.Status = 'issued'
           GROUP BY w.DN_ID
           ORDER BY w.DN_Date""",
        (customer_id,),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def create_draft(customer_id: str, dn_date: str, order_id=None, notes: str = "") -> int:
    """Create a DN document in 'draft' status. Returns DN_ID."""
    conn = get_connection()
    number = next_doc_number("DN", conn)
    cur = conn.execute(
        "INSERT INTO DN (DN_Number, OrderID, CustomerID, DN_Date, Status, Notes) "
        "VALUES (?,?,?,?,'draft',?)",
        (number, order_id or None, customer_id, dn_date, notes or None),
    )
    dn_id = cur.lastrowid
    conn.commit()
    conn.close()
    return dn_id


def add_item(dn_id: int, product_id: int, quantity: int, unit_price: float) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO DN_Items (DN_ID, ProductID, Quantity, UnitPrice) VALUES (?,?,?,?)",
        (dn_id, product_id, quantity, unit_price),
    )
    conn.commit()
    conn.close()


def remove_item(dn_id: int, product_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "DELETE FROM DN_Items WHERE DN_ID=? AND ProductID=?", (dn_id, product_id)
    )
    conn.commit()
    conn.close()


def issue(dn_id: int) -> None:
    """Set DN status to 'issued' and decrement stock for each item."""
    from data.settings import get_backorder_allowed
    conn = get_connection()
    dn = conn.execute("SELECT Status FROM DN WHERE DN_ID=?", (dn_id,)).fetchone()
    if not dn:
        conn.close()
        raise ValueError(f"DN #{dn_id} not found.")
    if dn[0] != "draft":
        conn.close()
        raise ValueError(f"DN #{dn_id} is already {dn[0]}.")
    items = conn.execute(
        "SELECT ProductID, Quantity FROM DN_Items WHERE DN_ID=?", (dn_id,)
    ).fetchall()
    if not items:
        conn.close()
        raise ValueError("Cannot issue a DN with no items.")
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
    conn.execute("UPDATE DN SET Status='issued' WHERE DN_ID=?", (dn_id,))
    conn.commit()
    conn.close()


def fetch_for_order(order_id: int) -> list:
    """Return all DN docs linked to a given order."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DN_ID, DN_Number, Status FROM DN WHERE OrderID=?", (order_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_from_order(order_id: int, dn_date: str) -> int:
    """Create and immediately issue a DN from an existing order's line items.
    If backorders are disabled, quantities are clamped to available stock.
    Raises ValueError if all lines would be clamped to zero.
    """
    from data.settings import get_backorder_allowed
    conn = get_connection()
    # Guard: prevent issuing a second DN for the same order
    existing = conn.execute(
        "SELECT DN_ID, DN_Number FROM DN WHERE OrderID=?", (order_id,)
    ).fetchone()
    if existing:
        conn.close()
        raise ValueError(
            f"DN {existing[1]} already exists for Order #{order_id}."
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
    number = next_doc_number("DN", conn)
    cur = conn.execute(
        "INSERT INTO DN (DN_Number, OrderID, CustomerID, DN_Date, Status) "
        "VALUES (?,?,?,?,'draft')",
        (number, order_id, customer_id, dn_date),
    )
    dn_id = cur.lastrowid
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
                "INSERT INTO DN_Items (DN_ID, ProductID, Quantity, UnitPrice) VALUES (?,?,?,?)",
                (dn_id, product_id, qty, unit_price),
            )
            apply_stock_delta(product_id, -qty, conn)
            items_added += 1
    if items_added == 0:
        conn.execute("DELETE FROM DN WHERE DN_ID=?", (dn_id,))
        conn.commit()
        conn.close()
        raise ValueError("All line items have zero stock. Cannot create DN.")
    conn.execute("UPDATE DN SET Status='issued' WHERE DN_ID=?", (dn_id,))
    conn.commit()
    conn.close()
    return dn_id


def cancel(dn_id: int, reason: str, user_id: int) -> None:
    """Cancel an issued DN: reverse stock, mark as cancelled."""
    from datetime import datetime
    conn = get_connection()
    dn = conn.execute("SELECT Status FROM DN WHERE DN_ID=?", (dn_id,)).fetchone()
    if not dn:
        conn.close()
        raise ValueError(f"DN #{dn_id} not found.")
    status = dn[0]
    if status == "draft":
        conn.close()
        raise ValueError("Delete the draft instead of cancelling.")
    if status == "invoiced":
        conn.close()
        raise ValueError("Cancel or issue CN on the INV first.")
    if status == "cancelled":
        conn.close()
        raise ValueError("DN is already cancelled.")
    if status != "issued":
        conn.close()
        raise ValueError(f"Cannot cancel DN with status '{status}'.")
    # Reverse stock
    items = conn.execute(
        "SELECT ProductID, Quantity FROM DN_Items WHERE DN_ID=?", (dn_id,)
    ).fetchall()
    for it in items:
        apply_stock_delta(it["ProductID"], it["Quantity"], conn)
    conn.execute(
        "UPDATE DN SET Status='cancelled', CancelledAt=?, CancelledBy=?, CancelReason=? "
        "WHERE DN_ID=?",
        (datetime.now().isoformat(), user_id, reason, dn_id),
    )
    conn.commit()
    conn.close()


def delete(pk) -> None:
    from data.delete_guards import can_delete_dn
    ok, reasons = can_delete_dn(pk)
    if not ok:
        raise ValueError("Cannot delete: " + "; ".join(reasons))
    conn = get_connection()
    conn.execute("DELETE FROM DN WHERE DN_ID=?", (pk,))
    conn.commit()
    conn.close()
