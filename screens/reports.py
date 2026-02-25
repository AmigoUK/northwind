"""screens/reports.py — Reports panel with Select widget and DataTable results."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static
from textual import on

import data.reports as rdata


_REPORT_OPTIONS = [
    ("Sales by Customer",          "customer"),
    ("Sales by Product",           "product"),
    ("Sales by Employee",          "employee"),
    ("Top 10 Products by Revenue", "top10"),
    ("Low Stock Alert",            "lowstock"),
    ("Orders by Date Range",       "daterange"),
]


class ReportsPanel(Widget):
    BINDINGS = [
        ("r", "run_report", "Run Report"),
        ("x", "export_csv", "Export CSV"),
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
            with Horizontal(id="date-range-row", classes="date-range-hidden"):
                yield Input(placeholder="From date (YYYY-MM-DD)", id="date-from")
                yield Input(placeholder="To date (YYYY-MM-DD)",   id="date-to")
                yield Button("Run", id="btn-run-date", variant="primary")
            yield DataTable(id="report-tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        self._run_report("customer")

    @on(Select.Changed, "#report-type")
    def on_report_changed(self, event: Select.Changed) -> None:
        if event.value and event.value is not Select.BLANK:
            date_row = self.query_one("#date-range-row")
            if event.value == "daterange":
                date_row.remove_class("date-range-hidden")
                date_row.add_class("date-range-visible")
            else:
                date_row.remove_class("date-range-visible")
                date_row.add_class("date-range-hidden")
                self._run_report(str(event.value))

    @on(Button.Pressed, "#btn-run-date")
    def on_run_date(self) -> None:
        from datetime import datetime
        date_from = self.query_one("#date-from", Input).value.strip()
        date_to   = self.query_one("#date-to",   Input).value.strip()
        if not date_from or not date_to:
            self.notify("Both From and To dates are required.", severity="error")
            return
        for label, val in [("From Date", date_from), ("To Date", date_to)]:
            try:
                datetime.strptime(val, "%Y-%m-%d")
            except ValueError:
                self.notify(f"{label} must be YYYY-MM-DD.", severity="error")
                return
        if date_from > date_to:
            self.notify("From date must be before To date.", severity="error")
            return
        self._run_report("daterange", date_from=date_from, date_to=date_to)

    def _run_report(self, report_type: str, **kwargs) -> None:
        tbl = self.query_one("#report-tbl", DataTable)
        tbl.clear(columns=True)
        try:
            if report_type == "customer":
                headers, rows = rdata.sales_by_customer()
            elif report_type == "product":
                headers, rows = rdata.sales_by_product()
            elif report_type == "employee":
                headers, rows = rdata.sales_by_employee()
            elif report_type == "top10":
                headers, rows = rdata.top_10()
            elif report_type == "lowstock":
                headers, rows = rdata.low_stock_alert()
                if not rows:
                    self.notify("No low-stock products found.", severity="information")
                    return
            elif report_type == "daterange":
                headers, rows = rdata.orders_by_date_range(
                    kwargs.get("date_from", ""), kwargs.get("date_to", "")
                )
                if not rows:
                    self.notify("No orders found in that date range.", severity="information")
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
        import csv, os
        from datetime import datetime
        if not self._last_rows:
            self.notify("Run a report first, then press X to export.", severity="warning")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_type = str(self.query_one("#report-type", Select).value)
        path = os.path.expanduser(f"~/Downloads/northwind_report_{report_type}_{ts}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(self._last_headers)
            for row in self._last_rows:
                writer.writerow([str(c) if c is not None else "" for c in row])
        self.notify(f"Exported {len(self._last_rows)} rows → {path}", severity="information")

    def action_run_report(self) -> None:
        report_type = self.query_one("#report-type", Select).value
        if report_type and report_type is not Select.BLANK:
            if str(report_type) == "daterange":
                self.on_run_date()
            else:
                self._run_report(str(report_type))
