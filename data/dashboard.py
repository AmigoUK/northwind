"""data/dashboard.py — KPI queries and recent-orders snapshot for the Dashboard panel."""
from db import get_connection
from data.settings import get_currency_symbol


def kpis() -> dict:
    """Return a dict with: customers, orders, low_stock, revenue."""
    conn = get_connection()
    customers = conn.execute("SELECT COUNT(*) FROM Customers").fetchone()[0]
    orders    = conn.execute("SELECT COUNT(*) FROM Orders").fetchone()[0]
    low_stock = conn.execute(
        "SELECT COUNT(*) FROM Products WHERE UnitsInStock <= ReorderLevel AND Discontinued = 0"
    ).fetchone()[0]
    revenue_row = conn.execute(
        "SELECT COALESCE(SUM(UnitPrice * Quantity * (1.0 - Discount)), 0.0) FROM OrderDetails"
    ).fetchone()
    revenue = revenue_row[0] if revenue_row else 0.0
    conn.close()
    return {
        "customers": customers,
        "orders":    orders,
        "low_stock": low_stock,
        "revenue":   revenue,
    }


def recent_orders(n: int = 10) -> list:
    """Return the last n orders as list of lists: [ID, Customer, OrderDate, ShippedDate, Total]."""
    sym = get_currency_symbol()
    conn = get_connection()
    rows = conn.execute(
        """SELECT o.OrderID,
                  COALESCE(c.CompanyName, o.CustomerID) AS Customer,
                  o.OrderDate,
                  COALESCE(o.ShippedDate, '(pending)') AS Shipped,
                  COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0) AS Total
           FROM Orders o
           LEFT JOIN Customers c ON o.CustomerID = c.CustomerID
           LEFT JOIN OrderDetails od ON o.OrderID = od.OrderID
           GROUP BY o.OrderID, c.CompanyName, o.CustomerID, o.OrderDate, o.ShippedDate
           ORDER BY o.OrderID DESC
           LIMIT ?""",
        (n,),
    ).fetchall()
    conn.close()
    return [
        [r["OrderID"], r["Customer"], r["OrderDate"] or "", r["Shipped"], f"{sym}{r['Total']:.2f}"]
        for r in rows
    ]
