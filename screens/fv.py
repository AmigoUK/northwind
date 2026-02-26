from __future__ import annotations
"""screens/fv.py — FV (Faktura VAT) panel, detail, and creation flow."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static
from textual import on

import data.fv as fvdata
import data.customers as cdata
import data.wz as wzdata
from data.settings import get_currency_symbol
from screens.modals import ConfirmDeleteModal, PickerModal


class FVNewModal(ModalScreen):
    """Multi-step modal to create a new FV invoice."""

    def __init__(self) -> None:
        super().__init__()
        self._customer_id = None
        self._customer_name = ""
        self._selected_wz_ids: set[int] = set()

    def compose(self) -> ComposeResult:
        with Vertical(classes="order-detail-dialog"):
            yield Label("New FV — Faktura VAT", classes="modal-title")
            yield Label("Customer *:")
            with Horizontal():
                yield Label("(none)", id="lbl-customer")
                yield Button("Pick Customer", id="btn-pick-cust")
            yield Label("Available WZ (issued, not invoiced):", classes="section-label")
            yield DataTable(id="wz-tbl", cursor_type="row", zebra_stripes=True)
            yield Static("", id="wz-hint")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("FV Date (YYYY-MM-DD) *:")
                    yield Input(id="f-fvdate", placeholder="2026-01-01")
                with Vertical(classes="form-field"):
                    yield Label("Due Date (YYYY-MM-DD):")
                    yield Input(id="f-duedate", placeholder="2026-01-31")
                with Vertical(classes="form-field"):
                    yield Label("Payment Method:")
                    yield Select(
                        [("cash", "cash"), ("bank", "bank"), ("(none)", "(none)")],
                        id="f-payment", value="bank",
                    )
            yield Label("Notes:")
            yield Input(id="f-notes", placeholder="Optional notes")
            with Horizontal(classes="modal-buttons"):
                yield Button("Create Invoice", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("Space=toggle WZ selection  ESC=close", classes="modal-hint")

    def on_mount(self) -> None:
        from datetime import date
        self.query_one("#f-fvdate", Input).value = str(date.today())
        tbl = self.query_one("#wz-tbl", DataTable)
        for label, width in [
            ("Sel", 4), ("WZ_ID", 6), ("Number", 16), ("Date", 12), ("Total", 12),
        ]:
            tbl.add_column(label, width=width)

    def _refresh_wz_table(self) -> None:
        tbl = self.query_one("#wz-tbl", DataTable)
        tbl.clear()
        if not self._customer_id:
            self.query_one("#wz-hint", Static).update("Pick a customer to see available WZ.")
            return
        sym = get_currency_symbol()
        rows = wzdata.fetch_issued_for_customer(self._customer_id)
        for row in rows:
            sel = "[X]" if row[0] in self._selected_wz_ids else "[ ]"
            tbl.add_row(
                sel, str(row[0]), row[1], row[2], f"{sym}{float(row[3]):.2f}",
                key=str(row[0]),
            )
        if not rows:
            self.query_one("#wz-hint", Static).update("No issued WZ documents for this customer.")
        else:
            count = len(self._selected_wz_ids)
            self.query_one("#wz-hint", Static).update(
                f"{len(rows)} available · {count} selected (press Space to toggle)"
            )

    @on(Button.Pressed, "#btn-pick-cust")
    def on_pick_customer(self) -> None:
        rows = cdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._customer_id = pk
                self._selected_wz_ids.clear()
                cust = cdata.get_by_pk(pk)
                if cust:
                    self._customer_name = cust["CompanyName"]
                    self.query_one("#lbl-customer", Label).update(cust["CompanyName"])
                self._refresh_wz_table()
        self.app.push_screen(
            PickerModal("Select Customer",
                        [("ID", 6), ("Company", 26), ("Contact", 18), ("City", 12)], rows),
            callback=after,
        )

    @on(DataTable.RowSelected, "#wz-tbl")
    def on_wz_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key:
            wz_id = int(event.row_key.value)
            if wz_id in self._selected_wz_ids:
                self._selected_wz_ids.discard(wz_id)
            else:
                self._selected_wz_ids.add(wz_id)
            self._refresh_wz_table()

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        from datetime import datetime
        if not self._customer_id:
            self.notify("Customer is required.", severity="error")
            return
        if not self._selected_wz_ids:
            self.notify("Select at least one WZ document.", severity="error")
            return
        fv_date = self.query_one("#f-fvdate", Input).value.strip()
        due_date = self.query_one("#f-duedate", Input).value.strip()
        try:
            datetime.strptime(fv_date, "%Y-%m-%d")
        except ValueError:
            self.notify("FV Date must be YYYY-MM-DD.", severity="error")
            return
        if due_date:
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError:
                self.notify("Due Date must be YYYY-MM-DD.", severity="error")
                return
        payment = self.query_one("#f-payment", Select).value
        if payment == "(none)":
            payment = ""
        notes = self.query_one("#f-notes", Input).value.strip()
        try:
            fv_id = fvdata.create(
                self._customer_id, list(self._selected_wz_ids),
                fv_date, due_date, payment, notes,
            )
            self.notify(f"Invoice created (FV #{fv_id}).", severity="information")
            self.dismiss(fv_id)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class FVDetailModal(ModalScreen):
    """Full FV detail with linked WZ and line items."""

    def __init__(self, fv_id: int) -> None:
        super().__init__()
        self.fv_id = fv_id
        self._changed = False

    def compose(self) -> ComposeResult:
        with Vertical(classes="order-detail-dialog"):
            yield Label("", id="fv-title", classes="modal-title")
            yield Static("", id="fv-header")
            yield Label("Linked WZ Documents:", classes="section-label")
            yield DataTable(id="wz-tbl", cursor_type="row", zebra_stripes=True)
            yield Label("Line Items (from all WZ):", classes="section-label")
            yield DataTable(id="lines-tbl", cursor_type="row", zebra_stripes=True)
            yield Static("", id="fv-total")
            with Horizontal(classes="modal-buttons"):
                yield Button("Mark Paid", id="btn-paid",   variant="primary")
                yield Button("Delete",    id="btn-delete", variant="error")
                yield Button("Close",     id="btn-close")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        wz_tbl = self.query_one("#wz-tbl", DataTable)
        for label, width in [("WZ_ID", 6), ("Number", 16), ("Date", 12), ("Total", 12)]:
            wz_tbl.add_column(label, width=width)
        lines_tbl = self.query_one("#lines-tbl", DataTable)
        for label, width in [
            ("ProdID", 6), ("Product Name", 28), ("Qty", 6), ("Price", 12), ("Line Total", 12),
        ]:
            lines_tbl.add_column(label, width=width)
        self._load()

    def _load(self) -> None:
        sym = get_currency_symbol()
        hdr = fvdata.get_by_pk(self.fv_id)
        if not hdr:
            self.dismiss(self._changed)
            return
        self.query_one("#fv-title", Label).update(f"FV #{self.fv_id} — {hdr.get('FV_Number', '')}")
        info = [
            f"[b]Number:[/b]   {hdr.get('FV_Number', '')}",
            f"[b]Customer:[/b] {hdr.get('CustomerID', '')} — {hdr.get('CompanyName') or ''}",
            f"[b]Date:[/b]     {hdr.get('FV_Date', '')}   "
            f"[b]Due:[/b] {hdr.get('DueDate') or '—'}",
            f"[b]Payment:[/b]  {hdr.get('PaymentMethod') or '—'}   "
            f"[b]Status:[/b] {hdr.get('Status', '')}",
            f"[b]Total Net:[/b] {sym}{hdr.get('TotalNet', 0):.2f}",
        ]
        if hdr.get("Notes"):
            info.append(f"[b]Notes:[/b] {hdr['Notes']}")
        self.query_one("#fv-header", Static).update("\n".join(info))

        wz_tbl = self.query_one("#wz-tbl", DataTable)
        wz_tbl.clear()
        for wz in fvdata.fetch_linked_wz(self.fv_id):
            wz_tbl.add_row(
                str(wz["WZ_ID"]), wz["WZ_Number"], wz["WZ_Date"],
                f"{sym}{wz['Total']:.2f}",
            )

        lines_tbl = self.query_one("#lines-tbl", DataTable)
        lines_tbl.clear()
        total = 0.0
        for it in fvdata.fetch_line_items(self.fv_id):
            lt = it["LineTotal"]
            total += lt
            lines_tbl.add_row(
                str(it["ProductID"]), it["ProductName"], str(it["Quantity"]),
                f"{sym}{it['UnitPrice']:.2f}", f"{sym}{lt:.2f}",
            )
        self.query_one("#fv-total", Static).update(f"[b]Total:[/b] {sym}{total:.2f}")

        status = hdr.get("Status", "issued")
        try:
            self.query_one("#btn-paid", Button).disabled = (status == "paid")
        except Exception:
            pass

    @on(Button.Pressed, "#btn-paid")
    def on_mark_paid(self) -> None:
        try:
            fvdata.mark_paid(self.fv_id)
            self._changed = True
            self._load()
            self.notify("Invoice marked as paid.", severity="information")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        def after(confirmed):
            if confirmed:
                try:
                    fvdata.delete(self.fv_id)
                    self.dismiss(True)
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"FV #{self.fv_id}"), callback=after)

    @on(Button.Pressed, "#btn-close")
    def on_close(self) -> None:
        self.dismiss(self._changed)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(self._changed)


class FVPanel(Widget):
    BINDINGS = [
        ("n", "new_record",   "New FV"),
        ("f", "focus_search", "Search"),
    ]

    _selected_pk = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Input(placeholder="Search invoices...", id="search-box")
            yield DataTable(id="tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("+ New Invoice", id="btn-new",    variant="success")
                yield Button("Open",          id="btn-open")
                yield Button("Delete",        id="btn-delete", variant="error")
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        for label, width in [
            ("ID", 6), ("Number", 16), ("Date", 12), ("Customer", 22),
            ("Status", 8), ("Payment", 8), ("Total", 12),
        ]:
            tbl.add_column(label, width=width)
        self.refresh_data()

    def refresh_data(self, term: str = "") -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        rows = fvdata.search(term) if term else fvdata.fetch_all()
        sym = get_currency_symbol()
        for row in rows:
            display = list(row)
            if display[6] is not None:
                display[6] = f"{sym}{float(display[6]):.2f}"
            tbl.add_row(*[str(c) if c is not None else "" for c in display],
                        key=str(row[0]))
        try:
            self.query_one("#count-label", Label).update(f"{len(rows)} records")
        except Exception:
            pass

    @on(Input.Changed, "#search-box")
    def on_search(self, event: Input.Changed) -> None:
        self.refresh_data(event.value)

    @on(DataTable.RowHighlighted, "#tbl")
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._selected_pk = event.row_key.value

    @on(DataTable.RowSelected, "#tbl")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key:
            self._open_detail(int(event.row_key.value))

    def _open_detail(self, fv_id: int) -> None:
        def after(changed):
            if changed:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(FVDetailModal(fv_id), callback=after)

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-open")
    def on_btn_open(self) -> None:
        if self._selected_pk:
            self._open_detail(int(self._selected_pk))
        else:
            self.notify("Select an invoice first.", severity="warning")

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        if not self._selected_pk:
            self.notify("Select an invoice first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    fvdata.delete(int(self._selected_pk))
                    self._selected_pk = None
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify("Invoice deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"FV #{self._selected_pk}"), callback=after)

    def action_new_record(self) -> None:
        def after_form(fv_id):
            if fv_id:
                def after_detail(changed):
                    self.refresh_data(self.query_one("#search-box", Input).value)
                self.app.push_screen(FVDetailModal(fv_id), callback=after_detail)
        self.app.push_screen(FVNewModal(), callback=after_form)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()
