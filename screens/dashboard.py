"""screens/dashboard.py — Dashboard panel with KPI cards and recent orders."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import DataTable, Label, Static

import data.dashboard as ddata
from data.settings import get_currency_symbol


class DashboardPanel(Widget):
    BINDINGS = [
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Label("Northwind Dashboard", classes="panel-title")
            with Horizontal(id="kpi-row"):
                with Vertical(classes="kpi-card"):
                    yield Static("", id="kpi-customers-val", classes="kpi-value")
                    yield Label("Customers", classes="kpi-title")
                with Vertical(classes="kpi-card"):
                    yield Static("", id="kpi-orders-val", classes="kpi-value")
                    yield Label("Orders", classes="kpi-title")
                with Vertical(classes="kpi-card"):
                    yield Static("", id="kpi-lowstock-val", classes="kpi-value")
                    yield Label("Low Stock", classes="kpi-title")
                with Vertical(classes="kpi-card"):
                    yield Static("", id="kpi-revenue-val", classes="kpi-value")
                    yield Label("Total Revenue", classes="kpi-title")
                with Vertical(classes="kpi-card"):
                    yield Static("", id="kpi-pending-val", classes="kpi-value")
                    yield Label("Pending Orders", classes="kpi-title")
                with Vertical(classes="kpi-card"):
                    yield Static("", id="kpi-fulfil-val", classes="kpi-value")
                    yield Label("Avg Fulfil Days", classes="kpi-title")
                with Vertical(classes="kpi-card"):
                    yield Static("", id="kpi-this-month-val", classes="kpi-value")
                    yield Label("This Month", classes="kpi-title")
            yield Label("Recent Orders (last 10)", id="dashboard-recent-label")
            yield DataTable(id="recent-tbl", cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        tbl = self.query_one("#recent-tbl", DataTable)
        for label, width in [
            ("ID", 7), ("Customer", 28), ("Order Date", 12),
            ("Shipped", 12), ("Total", 12),
        ]:
            tbl.add_column(label, width=width)
        self._load()

    def _load(self) -> None:
        try:
            kpis = ddata.kpis()
            symbol = get_currency_symbol()
            self.query_one("#kpi-customers-val", Static).update(str(kpis["customers"]))
            self.query_one("#kpi-orders-val",    Static).update(str(kpis["orders"]))
            self.query_one("#kpi-lowstock-val",  Static).update(str(kpis["low_stock"]))
            self.query_one("#kpi-revenue-val",   Static).update(f"{symbol}{kpis['revenue']:,.0f}")
        except Exception as e:
            self.notify(f"KPI error: {e}", severity="error")

        try:
            ext = ddata.kpis_extended()
            symbol = get_currency_symbol()
            self.query_one("#kpi-pending-val",    Static).update(str(ext["pending_orders"]))
            self.query_one("#kpi-fulfil-val",     Static).update(f"{ext['avg_fulfil_days']}d")
            trend = ext["trend_arrow"]
            delta = ext["delta_pct"]
            this_rev = ext["revenue_this_month"]
            self.query_one("#kpi-this-month-val", Static).update(
                f"{symbol}{this_rev:,.0f} {trend}{abs(delta):.0f}%"
            )
        except Exception:
            pass

        try:
            tbl = self.query_one("#recent-tbl", DataTable)
            tbl.clear()
            for row in ddata.recent_orders(10):
                tbl.add_row(*[str(c) for c in row], key=str(row[0]))
        except Exception as e:
            self.notify(f"Recent orders error: {e}", severity="error")

    def action_refresh(self) -> None:
        self._load()
        self.notify("Dashboard refreshed.", severity="information")
