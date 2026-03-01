from __future__ import annotations
"""screens/bank.py — Bank entries panel."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Select, Static
from textual import on

import data.bank as bankdata
import data.customers as cdata
import data.suppliers as sdata
from data.settings import get_currency_symbol
from screens.modals import ConfirmDeleteModal, PickerModal


class BankEntryFormModal(ModalScreen):
    """Create a manual bank entry."""

    def __init__(self) -> None:
        super().__init__()
        self._customer_id = None
        self._supplier_id = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("New Bank Account Entry", classes="modal-title")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Direction *:")
                    yield Select(
                        [("in — money received", "in"), ("out — money sent", "out")],
                        id="f-dir", value="in",
                    )
                with Vertical(classes="form-field"):
                    yield Label("Amount *:")
                    yield Input(id="f-amount", placeholder="0.00")
            yield Label("Customer (optional):")
            with Horizontal():
                yield Label("(none)", id="lbl-cust")
                yield Button("Pick Customer ▼", id="btn-pick-cust")
            yield Label("Supplier (optional):")
            with Horizontal():
                yield Label("(none)", id="lbl-sup")
                yield Button("Pick Supplier ▼", id="btn-pick-sup")
            yield Label("Description:")
            yield Input(id="f-desc", placeholder="Description")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    @on(Button.Pressed, "#btn-pick-cust")
    def on_pick_cust(self) -> None:
        rows = cdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._customer_id = pk
                self._supplier_id = None
                cust = cdata.get_by_pk(pk)
                if cust:
                    self.query_one("#lbl-cust", Label).update(cust["CompanyName"])
                    self.query_one("#lbl-sup",  Label).update("(none)")
        self.app.push_screen(
            PickerModal("Select Customer",
                        [("ID", 6), ("Company", 26), ("Contact", 18), ("City", 12)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-pick-sup")
    def on_pick_sup(self) -> None:
        rows = sdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._supplier_id = int(pk)
                self._customer_id = None
                sup = sdata.get_by_pk(int(pk))
                if sup:
                    self.query_one("#lbl-sup",  Label).update(sup["CompanyName"])
                    self.query_one("#lbl-cust", Label).update("(none)")
        self.app.push_screen(
            PickerModal("Select Supplier",
                        [("ID", 4), ("Company", 26), ("City", 14), ("Country", 12)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        direction = self.query_one("#f-dir", Select).value
        try:
            amount = float(self.query_one("#f-amount", Input).value.strip() or "0")
        except ValueError:
            self.notify("Amount must be a number.", severity="error")
            return
        if amount <= 0:
            self.notify("Amount must be positive.", severity="error")
            return
        desc = self.query_one("#f-desc", Input).value.strip()
        try:
            bankdata.create_bank_entry(
                direction=direction, amount=amount, description=desc,
                customer_id=self._customer_id, supplier_id=self._supplier_id,
            )
            self.notify("Bank Account entry created.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class TransferModal(ModalScreen):
    """Generic transfer amount/description modal."""

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(self._title, classes="modal-title")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Amount *:")
                    yield Input(id="f-amount", placeholder="0.00")
                with Vertical(classes="form-field"):
                    yield Label("Description (optional):")
                    yield Input(id="f-desc", placeholder="")
            with Horizontal(classes="modal-buttons"):
                yield Button("Transfer", id="btn-confirm", variant="primary")
                yield Button("Cancel",   id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    @on(Button.Pressed, "#btn-confirm")
    def on_confirm(self) -> None:
        try:
            amount = float(self.query_one("#f-amount", Input).value.strip() or "0")
        except ValueError:
            self.notify("Amount must be a number.", severity="error")
            return
        if amount <= 0:
            self.notify("Amount must be positive.", severity="error")
            return
        desc = self.query_one("#f-desc", Input).value.strip()
        self.dismiss((amount, desc))

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class BankPanel(Widget):
    BINDINGS = [
        ("n", "new_record",   "New Entry"),
        ("f", "focus_search", "Search"),
    ]

    _selected_pk = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Static("", id="bank-balance")
            yield Input(placeholder="Search bank entries...", id="search-box")
            yield DataTable(id="tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("+ New Entry", id="btn-new",    variant="success")
                yield Button("→ Cash Reg",  id="btn-transfer-cash", variant="warning")
                yield Button("PDF",         id="btn-pdf")
                yield Button("Delete",      id="btn-delete", variant="error")
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        for label, width in [
            ("ID", 6), ("Number", 16), ("Date", 12), ("Dir", 4),
            ("Counterparty", 22), ("Amount", 12), ("Description", 20),
        ]:
            tbl.add_column(label, width=width)
        self.refresh_data()

    def refresh_data(self, term: str = "") -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        rows = bankdata.search(term) if term else bankdata.fetch_all()
        sym = get_currency_symbol()
        for row in rows:
            display = list(row)
            if display[5] is not None:
                display[5] = f"{sym}{float(display[5]):.2f}"
            tbl.add_row(*[str(c) if c is not None else "" for c in display], key=str(row[0]))
        try:
            self.query_one("#count-label", Label).update(f"{len(rows)} records")
        except Exception:
            pass
        # Update balance
        try:
            balance = bankdata.bank_balance()
            self.query_one("#bank-balance", Static).update(
                f"[b]Bank Account Balance:[/b] {sym}{balance:.2f}"
            )
        except Exception:
            pass

    @on(Input.Changed, "#search-box")
    def on_search(self, event: Input.Changed) -> None:
        self.refresh_data(event.value)

    @on(DataTable.RowHighlighted, "#tbl")
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._selected_pk = event.row_key.value

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-transfer-cash")
    def on_transfer_to_cash(self) -> None:
        def after(result):
            if result:
                amount, desc = result
                try:
                    bankdata.withdraw_to_cash(amount, desc)
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify(f"Withdrawn to Cash Register: {amount:.2f}", severity="information")
                except Exception as e:
                    self.notify(f"Transfer failed: {e}", severity="error")
        self.app.push_screen(TransferModal("Withdraw Bank Account → Cash Register"), callback=after)

    @on(Button.Pressed, "#btn-pdf")
    def on_btn_pdf(self) -> None:
        if not self._selected_pk:
            self.notify("Select a Bank Account entry first.", severity="warning")
            return
        from datetime import datetime
        from screens.modals import FileSelectModal
        entry_id = int(self._selected_pk)
        suggested = f"northwind_bank_{entry_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        def after(path):
            if path:
                try:
                    import pdf_export
                    pdf_export.export_bank_entry(entry_id, save_path=path)
                    self.notify(f"PDF saved → {path}", severity="information")
                except Exception as e:
                    self.notify(f"PDF error: {e}", severity="error")
        self.app.push_screen(FileSelectModal(title="Save Bank Entry PDF", mode="save",
            default_path="~/Downloads", suggested_name=suggested, file_filter=".pdf"), callback=after)

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        if not self._selected_pk:
            self.notify("Select a Bank Account entry first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    bankdata.delete(int(self._selected_pk))
                    self._selected_pk = None
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify("Bank Account entry deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"Bank Account Entry #{self._selected_pk}"), callback=after)

    def action_new_record(self) -> None:
        def after(saved):
            if saved:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(BankEntryFormModal(), callback=after)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()
