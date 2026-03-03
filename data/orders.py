from __future__ import annotations
"""data/orders.py — SQL-only data access for Orders and OrderDetails."""
from db import get_connection


def fetch_all() -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT o.OrderID,
                  c.CompanyName AS Customer,
                  e.LastName || ', ' || e.FirstName AS Employee,
                  o.OrderDate, o.ShippedDate,
                  ROUND(COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0), 2) AS Total
           FROM Orders o
           LEFT JOIN Customers   c  ON o.CustomerID  = c.CustomerID
           LEFT JOIN Employees   e  ON o.EmployeeID  = e.EmployeeID
           LEFT JOIN OrderDetails od ON o.OrderID    = od.OrderID
           GROUP BY o.OrderID ORDER BY o.OrderID"""
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def fetch_all_with_lines() -> list[dict]:
    """Denormalized: one row per line item. Orders with no items get one row with NULL line-item columns."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT
               o.OrderID,
               o.CustomerID,       c.CompanyName              AS CustomerName,
               o.EmployeeID,       e.LastName||', '||e.FirstName AS EmployeeName,
               o.OrderDate,        o.RequiredDate,             o.ShippedDate,
               o.ShipVia,          s.CompanyName              AS ShipperName,
               o.Freight,
               o.ShipName, o.ShipAddress, o.ShipCity,
               o.ShipRegion, o.ShipPostalCode, o.ShipCountry,
               od.ProductID,       p.ProductName,
               od.Quantity,        od.UnitPrice,               od.Discount
           FROM Orders o
           LEFT JOIN Customers    c  ON o.CustomerID = c.CustomerID
           LEFT JOIN Employees    e  ON o.EmployeeID = e.EmployeeID
           LEFT JOIN Shippers     s  ON o.ShipVia    = s.ShipperID
           LEFT JOIN OrderDetails od ON o.OrderID    = od.OrderID
           LEFT JOIN Products     p  ON od.ProductID = p.ProductID
           ORDER BY o.OrderID, od.ProductID"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search(term: str) -> list:
    like = f"%{term}%"
    conn = get_connection()
    rows = conn.execute(
        """SELECT o.OrderID,
                  c.CompanyName AS Customer,
                  e.LastName || ', ' || e.FirstName AS Employee,
                  o.OrderDate, o.ShippedDate,
                  ROUND(COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0), 2) AS Total
           FROM Orders o
           LEFT JOIN Customers   c  ON o.CustomerID  = c.CustomerID
           LEFT JOIN Employees   e  ON o.EmployeeID  = e.EmployeeID
           LEFT JOIN OrderDetails od ON o.OrderID    = od.OrderID
           WHERE c.CustomerID LIKE ? OR c.CompanyName LIKE ? OR CAST(o.OrderID AS TEXT) LIKE ?
           GROUP BY o.OrderID ORDER BY o.OrderID""",
        (like, like, like),
    ).fetchall()
    conn.close()
    return [list(r) for r in rows]


def get_by_pk(pk) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT o.*,
                  c.CompanyName, c.ContactName,
                  e.LastName || ', ' || e.FirstName AS EmployeeName,
                  s.CompanyName AS ShipperName
           FROM Orders o
           LEFT JOIN Customers c ON o.CustomerID=c.CustomerID
           LEFT JOIN Employees e ON o.EmployeeID=e.EmployeeID
           LEFT JOIN Shippers  s ON o.ShipVia=s.ShipperID
           WHERE o.OrderID=?""",
        (pk,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_lines(order_id) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT od.ProductID, p.ProductName, od.Quantity, od.UnitPrice, od.Discount,
                  ROUND(od.UnitPrice * od.Quantity * (1.0 - od.Discount), 2) AS LineTotal
           FROM OrderDetails od
           JOIN Products p ON od.ProductID=p.ProductID
           WHERE od.OrderID=?
           ORDER BY od.ProductID""",
        (order_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def fetch_totals(order_id) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        """SELECT ROUND(COALESCE(SUM(od.UnitPrice*od.Quantity*(1.0-od.Discount)),0.0),2) AS subtotal,
                  o.Freight
           FROM Orders o
           LEFT JOIN OrderDetails od ON o.OrderID=od.OrderID
           WHERE o.OrderID=?
           GROUP BY o.OrderID""",
        (order_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_header(data: dict) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO Orders
           (CustomerID, EmployeeID, OrderDate, RequiredDate, ShipVia, Freight,
            ShipName, ShipAddress, ShipCity, ShipRegion, ShipPostalCode, ShipCountry)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            data.get("CustomerID"),
            data.get("EmployeeID") or None,
            data.get("OrderDate") or None,
            data.get("RequiredDate") or None,
            data.get("ShipVia") or None,
            data.get("Freight", 0.0),
            data.get("ShipName") or None,
            data.get("ShipAddress") or None,
            data.get("ShipCity") or None,
            data.get("ShipRegion") or None,
            data.get("ShipPostalCode") or None,
            data.get("ShipCountry") or None,
        ),
    )
    conn.commit()
    order_id = cur.lastrowid
    conn.close()
    return order_id


def update_header(pk, data: dict) -> None:
    conn = get_connection()
    conn.execute(
        """UPDATE Orders SET OrderDate=?, RequiredDate=?, ShipVia=?, Freight=?,
           ShipName=?, ShipAddress=?, ShipCity=?, ShipRegion=?, ShipPostalCode=?, ShipCountry=?
           WHERE OrderID=?""",
        (
            data.get("OrderDate") or None,
            data.get("RequiredDate") or None,
            data.get("ShipVia") or None,
            data.get("Freight", 0.0),
            data.get("ShipName") or None,
            data.get("ShipAddress") or None,
            data.get("ShipCity") or None,
            data.get("ShipRegion") or None,
            data.get("ShipPostalCode") or None,
            data.get("ShipCountry") or None,
            pk,
        ),
    )
    conn.commit()
    conn.close()


def add_line_item(order_id, product_id, unit_price: float, quantity: int, discount: float) -> None:
    conn = get_connection()
    existing = conn.execute(
        "SELECT 1 FROM OrderDetails WHERE OrderID=? AND ProductID=?",
        (order_id, product_id),
    ).fetchone()
    if existing:
        conn.close()
        raise ValueError(f"Product #{product_id} is already in this order.")
    conn.execute(
        "INSERT INTO OrderDetails (OrderID, ProductID, UnitPrice, Quantity, Discount) "
        "VALUES (?,?,?,?,?)",
        (order_id, product_id, unit_price, quantity, discount),
    )
    conn.commit()
    conn.close()


def remove_line_item(order_id, product_id) -> None:
    conn = get_connection()
    conn.execute(
        "DELETE FROM OrderDetails WHERE OrderID=? AND ProductID=?",
        (order_id, product_id),
    )
    conn.commit()
    conn.close()


def mark_shipped(order_id, shipped_date: str) -> None:
    from data.products import apply_stock_delta
    conn = get_connection()
    row = conn.execute(
        "SELECT ShippedDate FROM Orders WHERE OrderID=?", (order_id,)
    ).fetchone()
    already_shipped = row and row[0]
    # Check if a DN has already been issued for this order (stock already reduced)
    dn_issued = conn.execute(
        "SELECT 1 FROM DN WHERE OrderID=? AND Status IN ('issued','invoiced')",
        (order_id,),
    ).fetchone()
    conn.execute(
        "UPDATE Orders SET ShippedDate=? WHERE OrderID=?",
        (shipped_date, order_id),
    )
    if not already_shipped and not dn_issued:
        # Only reduce stock if neither shipped nor DN-issued before
        lines = conn.execute(
            "SELECT ProductID, Quantity FROM OrderDetails WHERE OrderID=?", (order_id,)
        ).fetchall()
        for line in lines:
            apply_stock_delta(line[0], -line[1], conn)
    conn.commit()
    conn.close()


def delete(pk) -> None:
    from data.delete_guards import can_delete_order
    ok, reasons = can_delete_order(pk)
    if not ok:
        raise ValueError("Cannot delete: " + "; ".join(reasons))
    conn = get_connection()
    conn.execute("DELETE FROM Orders WHERE OrderID=?", (pk,))
    conn.commit()
    conn.close()
