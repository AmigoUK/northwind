"""screens/charts.py — Pure-Unicode text charts panel (v2.1, no plotext)."""
from __future__ import annotations

import re

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Static, TabbedContent, TabPane
from textual import on

import data.reports as rdata
import data.dashboard as ddata
from data.settings import get_currency_symbol
from db import get_connection


# ── Rendering helpers (pure functions, no state) ──────────────────────────────

_SPARK = "▁▂▃▄▅▆▇█"
_FULL  = "█"
_EMPTY = "░"


def _sparkline(values: list[float]) -> str:
    lo, hi = min(values), max(values)
    rng = hi - lo or 1
    return "".join(_SPARK[round((v - lo) / rng * 7)] for v in values)


def _hbar(value: float, max_val: float, width: int) -> str:
    filled = round(value / max_val * width) if max_val else 0
    return _FULL * filled + _EMPTY * (width - filled)


def _parse_num(s: object) -> float:
    """Strip leading currency chars and commas → float."""
    return float(re.sub(r'^[^\d.]+', '', str(s)).replace(",", ""))


def _short_month(ym: str) -> str:
    """Convert '1996-07' → \"Jul'96\"."""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    try:
        y, m = ym.split("-")
        return f"{months[int(m) - 1]}'{y[2:]}"
    except Exception:
        return ym


# ── Chart builders ────────────────────────────────────────────────────────────

def _build_sales_trend(data_rows: list, w: int) -> str:
    """Return plain-text sparkline + data table for monthly revenue."""
    sym = get_currency_symbol()
    labels  = [_short_month(r[0]) for r in data_rows]
    revenues = [_parse_num(r[1]) for r in data_rows]
    orders   = [int(r[2]) if len(r) > 2 else 0 for r in data_rows]

    period_str = (
        f"{labels[0]} – {labels[-1]}" if len(labels) > 1 else labels[0]
    )
    sep_width = min(w - 2, 44)
    sep = "─" * sep_width

    spark = _sparkline(revenues) if len(revenues) > 1 else revenues[0] and "█" or "░"

    lines: list[str] = []
    lines.append(f"Revenue by Month  ({period_str})")
    lines.append("")
    lines.append(f"Trend  {spark}")
    lines.append("")
    lines.append(f" {'Month':<8}  {'Revenue':>12}  {'Orders':>6}  MoM")
    lines.append(sep)

    for i, (lbl, rev, ord_) in enumerate(zip(labels, revenues, orders)):
        if i == 0:
            mom = "  —"
        else:
            prev = revenues[i - 1]
            if prev:
                delta = (rev - prev) / prev * 100
                arrow = "↑" if delta >= 0 else "↓"
                mom = f"{arrow}{abs(delta):.1f}%"
            else:
                mom = "  —"
        lines.append(f" {lbl:<8}  {sym}{rev:>10,.0f}  {ord_:>6}  {mom}")

    lines.append(sep)

    if len(revenues) >= 2:
        prev, latest = revenues[-2], revenues[-1]
        arrow = "↑" if latest >= prev else "↓"
        delta = ((latest - prev) / prev * 100) if prev else 0.0
        lines.append(
            f"\nLatest: {sym}{latest:,.0f}   vs prev: {arrow}{abs(delta):.1f}%"
        )

    return "\n".join(lines)


def _build_category_mix(cat_rows: list, w: int) -> str:
    """Return plain-text horizontal bar chart for category revenue mix."""
    sym = get_currency_symbol()
    bar_width = max(20, min(40, w - 36))

    raw_labels  = [r[0] for r in cat_rows]
    raw_values  = [_parse_num(r[2]) for r in cat_rows]
    total = sum(raw_values) or 1.0
    pcts  = [v / total * 100 for v in raw_values]
    max_val = max(raw_values) if raw_values else 1.0

    lines: list[str] = ["Revenue Share by Category", ""]
    for lbl, val, pct in zip(raw_labels, raw_values, pcts):
        label = lbl[:12]
        bar   = _hbar(val, max_val, bar_width)
        sym_str = sym
        lines.append(f"{label:<12}  {bar}  {pct:5.1f}%  {sym_str}{val:>9,.0f}")

    return "\n".join(lines)


def _build_top_employees(names: list[str], counts: list[int], w: int) -> str:
    """Return plain-text horizontal bar chart for orders per employee."""
    bar_width = max(20, min(40, w - 20))
    max_count = max(counts) if counts else 1

    pairs = sorted(zip(names, counts), key=lambda x: x[1], reverse=True)

    lines: list[str] = ["Orders by Employee", ""]
    for name, count in pairs:
        label = name[:12]
        bar   = _hbar(count, max_count, bar_width)
        lines.append(f"{label:<12}  {bar}  {count:>3}")

    return "\n".join(lines)


# ── Widget ────────────────────────────────────────────────────────────────────

class ChartsPanel(Widget):
    BINDINGS = [
        ("r", "refresh_charts", "Refresh"),
    ]

    _date_from: str = "0001-01-01"
    _date_to:   str = "9999-12-31"

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Label("Charts", classes="panel-title")
            with Horizontal(classes="charts-kpi-bar"):
                yield Static("Rev: —",         id="kpi-revenue")
                yield Static("Orders: —",      id="kpi-orders")
                yield Static("AOV: —",         id="kpi-aov")
                yield Static("Customers: —",   id="kpi-customers")
                yield Static("Pending: —",     id="kpi-pending")
            with Horizontal(classes="charts-controls"):
                yield Select(
                    [("All Data", "all")],
                    id="period-select",
                    allow_blank=False,
                    value="all",
                )
                yield Label("  [R] Refresh")
            with Horizontal(classes="charts-date-row"):
                yield Label("From:")
                yield Input(placeholder="YYYY-MM-DD", id="chart-date-from")
                yield Label("To:")
                yield Input(placeholder="YYYY-MM-DD", id="chart-date-to")
                yield Button("Apply", id="btn-chart-apply", variant="primary")
            with TabbedContent(id="charts-tabs"):
                with TabPane("Sales Trend", id="tab-sales-trend"):
                    yield Static("Loading…", id="chart-sales-trend",
                                 classes="chart-static")
                with TabPane("Category Mix", id="tab-category-mix"):
                    yield Static("", id="chart-category-mix",
                                 classes="chart-static")
                with TabPane("Top Employees", id="tab-top-employees"):
                    yield Static("", id="chart-top-employees",
                                 classes="chart-static")
                with TabPane("Cash & Bank", id="tab-cash-bank"):
                    yield Static("Loading…", id="chart-cash-bank",
                                 classes="chart-static")

    def on_mount(self) -> None:
        self._populate_period_select()
        self._load_kpis()
        self._render_active_tab()

    # ── Period selector ───────────────────────────────────────────────────────

    def _populate_period_select(self) -> None:
        try:
            conn = get_connection()
            years = conn.execute(
                "SELECT DISTINCT strftime('%Y', OrderDate) y FROM Orders "
                "WHERE OrderDate IS NOT NULL ORDER BY y"
            ).fetchall()
            conn.close()
            opts: list[tuple[str, str]] = [("All Data", "all")]
            for row in years:
                y = row[0]
                opts.append((y, y))
            sel = self.query_one("#period-select", Select)
            sel.set_options(opts)
            if years:
                most_recent = years[-1][0]
                sel.value = most_recent
                self._date_from = f"{most_recent}-01-01"
                self._date_to   = f"{most_recent}-12-31"
            else:
                sel.value = "all"
        except Exception:
            pass

    @on(Select.Changed, "#period-select")
    def on_period_changed(self, event: Select.Changed) -> None:
        val = event.value
        if val is Select.BLANK:
            return
        if val == "all":
            self._date_from = "0001-01-01"
            self._date_to   = "9999-12-31"
            self.query_one("#chart-date-from", Input).value = ""
            self.query_one("#chart-date-to",   Input).value = ""
        else:
            self._date_from = f"{val}-01-01"
            self._date_to   = f"{val}-12-31"
            self.query_one("#chart-date-from", Input).value = self._date_from
            self.query_one("#chart-date-to",   Input).value = self._date_to
        self._render_active_tab()

    # ── Date filter ───────────────────────────────────────────────────────────

    def _apply_date_filter(self) -> None:
        from datetime import datetime
        date_from = self.query_one("#chart-date-from", Input).value.strip()
        date_to   = self.query_one("#chart-date-to",   Input).value.strip()

        if not date_from and not date_to:
            self._date_from = "0001-01-01"
            self._date_to   = "9999-12-31"
            self.query_one("#period-select", Select).value = "all"
            self._render_active_tab()
            return

        for label, val in [("From date", date_from), ("To date", date_to)]:
            if val:
                try:
                    datetime.strptime(val, "%Y-%m-%d")
                except ValueError:
                    self.notify(f"{label} must be YYYY-MM-DD.", severity="error")
                    return

        df = date_from or "0001-01-01"
        dt = date_to   or "9999-12-31"
        if df > dt:
            self.notify("From date must be before To date.", severity="error")
            return

        self._date_from = df
        self._date_to   = dt
        self._render_active_tab()
        self.notify(f"Filter: {df} → {dt}", severity="information")

    @on(Button.Pressed, "#btn-chart-apply")
    def on_apply_date(self, event: Button.Pressed) -> None:
        self._apply_date_filter()

    @on(Input.Submitted)
    def on_date_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in ("chart-date-from", "chart-date-to"):
            self._apply_date_filter()

    # ── KPI bar ───────────────────────────────────────────────────────────────

    def _load_kpis(self) -> None:
        try:
            kpis = ddata.kpis()
            ext  = ddata.kpis_extended()
            sym  = get_currency_symbol()
            aov  = kpis["revenue"] / kpis["orders"] if kpis["orders"] else 0.0
            self.query_one("#kpi-revenue",   Static).update(
                f"Rev: {sym}{kpis['revenue']:,.0f}")
            self.query_one("#kpi-orders",    Static).update(
                f"Orders: {kpis['orders']}")
            self.query_one("#kpi-aov",       Static).update(
                f"AOV: {sym}{aov:,.0f}")
            self.query_one("#kpi-customers", Static).update(
                f"Customers: {kpis['customers']}")
            self.query_one("#kpi-pending",   Static).update(
                f"Pending: {ext['pending_orders']}")
        except Exception:
            pass

    # ── Dynamic sizing ────────────────────────────────────────────────────────

    def _chart_size(self) -> tuple[int, int]:
        try:
            tabs = self.query_one("#charts-tabs")
            w = max(40, tabs.content_region.width - 2)
            return w, 0
        except Exception:
            return 80, 0

    # ── Tab routing ───────────────────────────────────────────────────────────

    def _active_tab_id(self) -> str:
        try:
            return str(self.query_one("#charts-tabs", TabbedContent).active)
        except Exception:
            return "tab-sales-trend"

    def _render_active_tab(self) -> None:
        tab = self._active_tab_id()
        if tab == "tab-sales-trend":
            self._render_sales_trend()
        elif tab == "tab-category-mix":
            self._render_category_mix()
        elif tab == "tab-top-employees":
            self._render_top_employees()
        elif tab == "tab-cash-bank":
            self._render_cash_bank()

    @on(TabbedContent.TabActivated)
    def on_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self._render_active_tab()

    def on_resize(self, event) -> None:
        self._render_active_tab()

    # ── Chart 1 — Sales Trend ─────────────────────────────────────────────────

    def _render_sales_trend(self) -> None:
        widget = self.query_one("#chart-sales-trend", Static)
        try:
            _, rows = rdata.monthly_revenue_trend(self._date_from, self._date_to)
            if not rows:
                widget.update("No data for the selected period.")
                return
            w, _ = self._chart_size()
            widget.update(_build_sales_trend(rows, w))
        except Exception as e:
            widget.update(f"Error: {e}")

    # ── Chart 2 — Category Mix ────────────────────────────────────────────────

    def _render_category_mix(self) -> None:
        widget = self.query_one("#chart-category-mix", Static)
        try:
            _, cat_rows = rdata.category_revenue()
            if not cat_rows:
                widget.update("No data available.")
                return
            w, _ = self._chart_size()
            widget.update(_build_category_mix(cat_rows, w))
        except Exception as e:
            widget.update(f"Error: {e}")

    # ── Chart 3 — Top Employees ───────────────────────────────────────────────

    def _render_top_employees(self) -> None:
        widget = self.query_one("#chart-top-employees", Static)
        try:
            names, counts = rdata.chart_employees(self._date_from, self._date_to)
            if not names:
                widget.update("No data for the selected period.")
                return
            w, _ = self._chart_size()
            widget.update(_build_top_employees(names, counts, w))
        except Exception as e:
            widget.update(f"Error: {e}")

    # ── Chart 4 — Cash & Bank ─────────────────────────────────────────────────

    def _render_cash_bank(self) -> None:
        widget = self.query_one("#chart-cash-bank", Static)
        try:
            trend = rdata.cash_bank_trend()
            sym = get_currency_symbol()
            lines: list[str] = []

            kassa_data = trend["kassa"]
            if kassa_data:
                vals = [v for _, v in kassa_data]
                spark = _sparkline(vals) if len(vals) > 1 else "█"
                lines.append("Kasa (Cash) Running Balance")
                lines.append(f"Trend  {spark}")
                lines.append(f"Latest: {sym}{vals[-1]:,.2f}")
                lines.append("")
                lines.append(f" {'Date':<12}  {'Balance':>12}")
                lines.append("─" * 28)
                for d, v in kassa_data[-10:]:
                    lines.append(f" {d:<12}  {sym}{v:>10,.2f}")
            else:
                lines.append("Kasa (Cash): No transactions recorded.")

            lines.append("")
            lines.append("")

            bank_data = trend["bank"]
            if bank_data:
                vals = [v for _, v in bank_data]
                spark = _sparkline(vals) if len(vals) > 1 else "█"
                lines.append("Bank Running Balance")
                lines.append(f"Trend  {spark}")
                lines.append(f"Latest: {sym}{vals[-1]:,.2f}")
                lines.append("")
                lines.append(f" {'Date':<12}  {'Balance':>12}")
                lines.append("─" * 28)
                for d, v in bank_data[-10:]:
                    lines.append(f" {d:<12}  {sym}{v:>10,.2f}")
            else:
                lines.append("Bank: No transactions recorded.")

            widget.update("\n".join(lines))
        except Exception as e:
            widget.update(f"Error: {e}")

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_refresh_charts(self) -> None:
        self._load_kpis()
        self._render_active_tab()
        self.notify("Charts refreshed.", severity="information")

    def action_new_record(self) -> None:
        pass

    def action_focus_search(self) -> None:
        pass
