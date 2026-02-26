"""screens/charts.py — ASCII charts panel using plotext (v2.0)."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label, Static, TabbedContent, TabPane
from textual import on

import data.reports as rdata
import data.dashboard as ddata
from data.settings import get_currency_symbol


def _render_sales_trend() -> str:
    """Line chart: monthly revenue for rolling 12 months."""
    try:
        import plotext as plt
        _, rows = rdata.monthly_revenue_trend(12)
        if not rows:
            return "No data available."
        labels = [r[0] for r in rows]
        values = [float(str(r[1]).lstrip("$£€¥").replace(",", "")) for r in rows]
        plt.clf()
        plt.plot_size(80, 20)
        plt.plot(values, label="Revenue")
        plt.xticks(range(1, len(labels) + 1), labels)
        plt.title("Monthly Revenue Trend")
        plt.xlabel("Month")
        plt.ylabel("Revenue")
        return plt.build()
    except Exception as e:
        return f"Chart error: {e}"


def _render_category_mix() -> str:
    """Horizontal bar chart: revenue % by product category."""
    try:
        import plotext as plt
        _, rows = rdata.category_revenue()
        if not rows:
            return "No data available."
        sym = get_currency_symbol()
        labels = [r[0] for r in rows]
        values = [float(str(r[2]).lstrip("$£€¥").replace(",", "")) for r in rows]
        total = sum(values) or 1.0
        pcts = [v / total * 100 for v in values]
        plt.clf()
        plt.plot_size(80, 20)
        plt.bar(labels, pcts, orientation="h")
        plt.title("Category Revenue Mix (%)")
        plt.xlabel("Revenue %")
        return plt.build()
    except Exception as e:
        return f"Chart error: {e}"


def _render_top_employees() -> str:
    """Bar chart: order count and revenue per employee."""
    try:
        import plotext as plt
        _, rows = rdata.sales_by_employee()
        if not rows:
            return "No data available."
        # rows: [EmployeeID, EmployeeName, Title, Orders, Revenue]
        names = [str(r[1]).split(",")[0].strip() for r in rows]
        orders = [int(r[3]) for r in rows]
        plt.clf()
        plt.plot_size(80, 20)
        plt.bar(names, orders)
        plt.title("Orders per Employee")
        plt.xlabel("Employee")
        plt.ylabel("Orders")
        return plt.build()
    except Exception as e:
        return f"Chart error: {e}"


class ChartsPanel(Widget):
    BINDINGS = [
        ("r", "refresh_charts", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Label("Charts", classes="panel-title")
            with TabbedContent(id="charts-tabs"):
                with TabPane("Sales Trend", id="tab-sales-trend"):
                    yield Static("", id="chart-sales-trend", classes="chart-static")
                with TabPane("Category Mix", id="tab-category-mix"):
                    yield Static("", id="chart-category-mix", classes="chart-static")
                with TabPane("Top Employees", id="tab-top-employees"):
                    yield Static("", id="chart-top-employees", classes="chart-static")

    def on_mount(self) -> None:
        self._refresh_all()

    @on(TabbedContent.TabActivated)
    def on_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self._refresh_all()

    def _refresh_all(self) -> None:
        try:
            self.query_one("#chart-sales-trend",    Static).update(_render_sales_trend())
        except Exception:
            pass
        try:
            self.query_one("#chart-category-mix",   Static).update(_render_category_mix())
        except Exception:
            pass
        try:
            self.query_one("#chart-top-employees",  Static).update(_render_top_employees())
        except Exception:
            pass

    def action_refresh_charts(self) -> None:
        self._refresh_all()
        self.notify("Charts refreshed.", severity="information")

    def action_new_record(self) -> None:
        pass

    def action_focus_search(self) -> None:
        pass
