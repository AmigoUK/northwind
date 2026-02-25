"""screens/sql.py — Interactive SQL query panel.

Educational patterns:
- sqlite3.cursor.description to dynamically read column names from any query
- DML vs SELECT detection (cursor.description is None after INSERT/UPDATE/DELETE)
- time.time() for simple query timing
- CSV export of arbitrary result sets
"""
import csv
import time
from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, DataTable, Label, Static, TextArea
from textual import on

from db import get_connection


class SqlPanel(Widget):
    BINDINGS = [
        Binding("ctrl+r", "run_query",  "Run"),
        Binding("x",      "export_csv", "Export CSV"),
    ]

    def on_mount(self) -> None:
        self._history: list[str] = []
        self._result_rows: list[list] = []
        self._result_headers: list[str] = []

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Label("SQL Query", classes="panel-title")
            yield TextArea("SELECT * FROM Customers LIMIT 10;", id="sql-input")
            with Horizontal(classes="toolbar"):
                yield Button("Run (ctrl+r)", id="btn-run", variant="primary")
                yield Button("Clear", id="btn-clear")
                yield Label("", id="sql-status", classes="sql-status count-label")
            yield Static("", id="sql-error")
            yield DataTable(id="sql-results", cursor_type="row", zebra_stripes=True)

    @on(Button.Pressed, "#btn-run")
    def action_run_query(self) -> None:
        sql = self.query_one("#sql-input", TextArea).text.strip()
        if not sql:
            return

        # Add to history (memory only, last 10 unique queries)
        if not self._history or self._history[-1] != sql:
            self._history.append(sql)
            if len(self._history) > 10:
                self._history.pop(0)

        error_widget  = self.query_one("#sql-error",    Static)
        status_widget = self.query_one("#sql-status",   Label)
        tbl           = self.query_one("#sql-results",  DataTable)

        error_widget.update("")
        tbl.clear(columns=True)
        self._result_rows = []
        self._result_headers = []

        conn = get_connection()
        try:
            t0 = time.time()
            cursor = conn.execute(sql)
            elapsed = time.time() - t0

            if cursor.description:
                # SELECT query — populate DataTable
                headers = [d[0] for d in cursor.description]
                rows = cursor.fetchall()

                self._result_headers = headers
                self._result_rows = [list(r) for r in rows]

                for col in headers:
                    tbl.add_column(col)
                for row in rows:
                    tbl.add_row(*[str(c) if c is not None else "" for c in row])

                status_widget.update(f"{len(rows)} rows · {elapsed:.3f}s")
            else:
                # DML (INSERT / UPDATE / DELETE) — commit and report
                conn.commit()
                status_widget.update(f"{cursor.rowcount} rows affected · {elapsed:.3f}s")
                self.notify(f"{cursor.rowcount} rows affected", severity="information")

        except Exception as e:
            error_widget.update(f"Error: {e}")
            status_widget.update("")
        finally:
            conn.close()

    @on(Button.Pressed, "#btn-clear")
    def on_clear(self) -> None:
        self.query_one("#sql-input",   TextArea).load_text("")
        self.query_one("#sql-results", DataTable).clear(columns=True)
        self.query_one("#sql-error",   Static).update("")
        self.query_one("#sql-status",  Label).update("")
        self._result_rows = []
        self._result_headers = []

    def action_export_csv(self) -> None:
        if not self._result_headers:
            self.notify("No results to export.", severity="warning")
            return
        filename = f"sql_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self._result_headers)
            writer.writerows(self._result_rows)
        self.notify(f"Exported to {filename}", severity="information")
