"""screens/reports.py — Reports panel with Select widget and DataTable results."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static
from textual import on

import data.reports as rdata


_REPORT_OPTIONS = [
    ("Sales by Customer",           "customer"),
    ("Sales by Product",            "product"),
    ("Sales by Employee",           "employee"),
    ("Top 10 Products by Revenue",  "top10"),
    ("Low Stock Alert",             "lowstock"),
    ("Orders by Date Range",        "daterange"),
    ("Monthly Revenue Trend",       "monthly_trend"),
    ("Order Fulfilment Time",       "fulfilment"),
    ("Category Revenue",            "category_rev"),
    ("Repeat Customers",            "repeat_cust"),
    ("Overdue Orders",              "overdue"),
    ("Cash & Bank Account Status",   "liquidity"),
    ("AR Aging",                    "ar_aging"),
    ("Incoming Payments (30 days)", "payment_forecast"),
]


class ReportsPanel(Widget):
    BINDINGS = [
        ("r", "run_report", "Run Report"),
    ]

    _last_headers: list = []
    _last_rows: list = []

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Label("Reports", classes="panel-title")
            yield Select(
                _REPORT_OPTIONS,
                id="report-type",
                allow_blank=False,
                value="customer",
            )
            with Horizontal(id="date-range-row", classes="date-range-visible"):
                yield Label("From:")
                yield Input(placeholder="YYYY-MM-DD", id="date-from")
                yield Label("To:")
                yield Input(placeholder="YYYY-MM-DD", id="date-to")
                yield Button("Apply", id="btn-run-date", variant="primary")
            yield DataTable(id="report-tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        self._run_report("customer")

    @on(Select.Changed, "#report-type")
    def on_report_changed(self, event: Select.Changed) -> None:
        if event.value and event.value is not Select.BLANK:
            dates = self._get_validated_dates()
            if dates is not None:
                self._run_report(str(event.value), *dates)

    def _get_validated_dates(self) -> tuple[str, str] | None:
        from datetime import datetime
        date_from = self.query_one("#date-from", Input).value.strip()
        date_to   = self.query_one("#date-to",   Input).value.strip()
        if not date_from and not date_to:
            return "0001-01-01", "9999-12-31"
        for label, val in [("From date", date_from), ("To date", date_to)]:
            if val:
                try:
                    datetime.strptime(val, "%Y-%m-%d")
                except ValueError:
                    self.notify(f"{label} must be YYYY-MM-DD.", severity="error")
                    return None
        df = date_from or "0001-01-01"
        dt = date_to   or "9999-12-31"
        if df > dt:
            self.notify("From date must be before To date.", severity="error")
            return None
        return df, dt

    @on(Button.Pressed, "#btn-run-date")
    def on_apply_dates(self, event: Button.Pressed) -> None:
        dates = self._get_validated_dates()
        if dates is None:
            return
        report_type = self.query_one("#report-type", Select).value
        if report_type and report_type is not Select.BLANK:
            self._run_report(str(report_type), *dates)

    @on(Input.Submitted)
    def on_date_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in ("date-from", "date-to"):
            dates = self._get_validated_dates()
            if dates is None:
                return
            report_type = self.query_one("#report-type", Select).value
            if report_type and report_type is not Select.BLANK:
                self._run_report(str(report_type), *dates)

    def _run_report(self, report_type: str,
                    date_from: str = "0001-01-01",
                    date_to:   str = "9999-12-31") -> None:
        tbl = self.query_one("#report-tbl", DataTable)
        tbl.clear(columns=True)
        try:
            if report_type == "customer":
                headers, rows = rdata.sales_by_customer(date_from, date_to)
            elif report_type == "product":
                headers, rows = rdata.sales_by_product(date_from, date_to)
            elif report_type == "employee":
                headers, rows = rdata.sales_by_employee(date_from, date_to)
            elif report_type == "top10":
                headers, rows = rdata.top_10(date_from, date_to)
            elif report_type == "lowstock":
                headers, rows = rdata.low_stock_alert()
                if not rows:
                    self.notify("No low-stock products found.", severity="information")
                    return
            elif report_type == "daterange":
                headers, rows = rdata.orders_by_date_range(date_from, date_to)
                if not rows:
                    self.notify("No orders found in that date range.", severity="information")
                    return
            elif report_type == "monthly_trend":
                headers, rows = rdata.monthly_revenue_trend(date_from, date_to)
            elif report_type == "fulfilment":
                headers, rows = rdata.order_fulfilment_time(date_from, date_to)
            elif report_type == "category_rev":
                headers, rows = rdata.category_revenue(date_from, date_to)
            elif report_type == "repeat_cust":
                headers, rows = rdata.repeat_customers(date_from, date_to)
            elif report_type == "overdue":
                headers, rows = rdata.overdue_orders()
                if not rows:
                    self.notify("No overdue orders found.", severity="information")
                    return
            elif report_type == "liquidity":
                headers, rows = rdata.liquidity_snapshot()
            elif report_type == "ar_aging":
                headers, rows = rdata.ar_aging()
                if not rows:
                    self.notify("No unpaid invoices found.", severity="information")
                    return
            elif report_type == "payment_forecast":
                headers, rows = rdata.payment_forecast()
                if not rows:
                    self.notify("No payments due in the next 30 days.", severity="information")
                    return
            else:
                return

            for label, width in headers:
                tbl.add_column(label, width=width)
            for i, row in enumerate(rows):
                tbl.add_row(*[str(c) if c is not None else "" for c in row], key=str(i))

            self._last_headers = [h for h, _ in headers]
            self._last_rows = list(rows)
            try:
                self.query_one("#count-label", Label).update(f"{len(rows)} records")
            except Exception:
                pass

        except Exception as e:
            self.notify(f"Error running report: {e}", severity="error")

    def action_export_csv(self) -> None:
        from screens.export_helpers import export_csv_with_selector
        if not self._last_rows:
            self.notify("Run a report first, then press X to export.", severity="warning")
            return
        report_type = str(self.query_one("#report-type", Select).value)
        export_csv_with_selector(self, f"report_{report_type}", self._last_headers, self._last_rows)

    def action_run_report(self) -> None:
        dates = self._get_validated_dates()
        if dates is None:
            return
        report_type = self.query_one("#report-type", Select).value
        if report_type and report_type is not Select.BLANK:
            self._run_report(str(report_type), *dates)
