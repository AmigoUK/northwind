"""data/dashboard.py — KPI queries and recent-orders snapshot for the Dashboard panel."""
from db import get_connection
from data.settings import get_currency_symbol
from datetime import date as _date


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


def kpis_extended() -> dict:
    """Extended KPIs including trend arrows and pending orders."""
    conn = get_connection()
    today = str(_date.today())
    # current month prefix e.g. "1996-07"
    cur_month = today[:7]
    # previous month: simple string subtraction not reliable, use SQL
    pending = conn.execute(
        "SELECT COUNT(*) FROM Orders WHERE ShippedDate IS NULL"
    ).fetchone()[0]

    avg_fulfil = conn.execute(
        """SELECT ROUND(AVG(julianday(ShippedDate) - julianday(OrderDate)), 1)
           FROM Orders
           WHERE ShippedDate IS NOT NULL AND OrderDate IS NOT NULL
             AND julianday(ShippedDate) - julianday(OrderDate) BETWEEN 0 AND 365"""
    ).fetchone()[0] or 0.0

    rev_this = conn.execute(
        """SELECT COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0)
           FROM Orders o JOIN OrderDetails od ON o.OrderID = od.OrderID
           WHERE strftime('%Y-%m', o.OrderDate) = ?""",
        (cur_month,),
    ).fetchone()[0] or 0.0

    # last month via date arithmetic in Python
    from datetime import datetime
    dt = datetime.strptime(cur_month + "-01", "%Y-%m-%d")
    if dt.month == 1:
        last_month = f"{dt.year - 1}-12"
    else:
        last_month = f"{dt.year}-{dt.month - 1:02d}"

    rev_last = conn.execute(
        """SELECT COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0.0)
           FROM Orders o JOIN OrderDetails od ON o.OrderID = od.OrderID
           WHERE strftime('%Y-%m', o.OrderDate) = ?""",
        (last_month,),
    ).fetchone()[0] or 0.0

    conn.close()

    if rev_last > 0:
        delta_pct = ((rev_this - rev_last) / rev_last) * 100
    else:
        delta_pct = 0.0
    trend_arrow = "↑" if rev_this >= rev_last else "↓"

    return {
        "pending_orders":     pending,
        "avg_fulfil_days":    avg_fulfil,
        "revenue_this_month": rev_this,
        "revenue_last_month": rev_last,
        "trend_arrow":        trend_arrow,
        "delta_pct":          delta_pct,
    }


def kpis_for_period(date_from: str, date_to: str) -> dict:
    """Revenue, orders, customers, AOV for a specific date range (used by Charts KPI bar)."""
    conn = get_connection()
    orders = conn.execute(
        "SELECT COUNT(DISTINCT OrderID) FROM Orders "
        "WHERE OrderDate BETWEEN ? AND ?", (date_from, date_to)
    ).fetchone()[0] or 0
    revenue = conn.execute(
        """SELECT COALESCE(SUM(od.UnitPrice * od.Quantity * (1.0 - od.Discount)), 0)
           FROM Orders o JOIN OrderDetails od ON o.OrderID = od.OrderID
           WHERE o.OrderDate BETWEEN ? AND ?""", (date_from, date_to)
    ).fetchone()[0] or 0.0
    customers = conn.execute(
        "SELECT COUNT(DISTINCT CustomerID) FROM Orders "
        "WHERE OrderDate BETWEEN ? AND ?", (date_from, date_to)
    ).fetchone()[0] or 0
    conn.close()
    aov = revenue / orders if orders else 0.0
    return {"revenue": revenue, "orders": orders, "customers": customers, "aov": aov}


def finance_kpis() -> dict:
    """Returns cash_balance, bank_balance, ar_due_30d."""
    from datetime import date, timedelta
    conn = get_connection()
    cr_total  = conn.execute("SELECT COALESCE(SUM(Amount),0) FROM CR").fetchone()[0]
    cp_total  = conn.execute("SELECT COALESCE(SUM(Amount),0) FROM CP").fetchone()[0]
    bank_in   = conn.execute(
        "SELECT COALESCE(SUM(Amount),0) FROM BankEntry WHERE Direction='in'"
    ).fetchone()[0]
    bank_out  = conn.execute(
        "SELECT COALESCE(SUM(Amount),0) FROM BankEntry WHERE Direction='out'"
    ).fetchone()[0]
    cutoff = str(_date.today() + timedelta(days=30))
    ar_due = conn.execute(
        """SELECT COALESCE(SUM(f.TotalNet - COALESCE(f.PaidAmount, 0)), 0)
           FROM INV f
           WHERE f.Status != 'paid'
             AND f.TotalNet > COALESCE(f.PaidAmount, 0)
             AND f.DueDate IS NOT NULL
             AND f.DueDate <= ?""",
        (cutoff,),
    ).fetchone()[0]
    conn.close()
    return {
        "cash_balance": cr_total - cp_total,
        "bank_balance":  bank_in - bank_out,
        "ar_due_30d":    ar_due,
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
