from __future__ import annotations
"""screens/cash.py — Cash register panel (CR receipts + CP payments)."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static, TabbedContent, TabPane
from textual import on

import data.cash as cashdata
import data.customers as cdata
import data.suppliers as sdata
from data.settings import get_currency_symbol
from screens.modals import ConfirmDeleteModal, PickerModal


class CRFormModal(ModalScreen):
    """Create a manual CR cash receipt."""

    def __init__(self) -> None:
        super().__init__()
        self._customer_id = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("New CR — Cash Receipt", classes="modal-title")
            yield Label("Customer (optional):")
            with Horizontal():
                yield Label("(none)", id="lbl-cust")
                yield Button("Pick Customer ▼", id="btn-pick-cust")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Amount *:")
                    yield Input(id="f-amount", placeholder="0.00")
                with Vertical(classes="form-field"):
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
                cust = cdata.get_by_pk(pk)
                if cust:
                    self.query_one("#lbl-cust", Label).update(cust["CompanyName"])
        self.app.push_screen(
            PickerModal("Select Customer",
                        [("ID", 6), ("Company", 26), ("Contact", 18), ("City", 12)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
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
            cashdata.create_cr(self._customer_id, None, amount, desc)
            self.notify("CR created.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class CPFormModal(ModalScreen):
    """Create a manual CP cash payment."""

    def __init__(self) -> None:
        super().__init__()
        self._supplier_id = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("New CP — Cash Payment", classes="modal-title")
            yield Label("Supplier (optional):")
            with Horizontal():
                yield Label("(none)", id="lbl-sup")
                yield Button("Pick Supplier ▼", id="btn-pick-sup")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Amount *:")
                    yield Input(id="f-amount", placeholder="0.00")
                with Vertical(classes="form-field"):
                    yield Label("Description:")
                    yield Input(id="f-desc", placeholder="Description")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    @on(Button.Pressed, "#btn-pick-sup")
    def on_pick_sup(self) -> None:
        rows = sdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._supplier_id = int(pk)
                sup = sdata.get_by_pk(int(pk))
                if sup:
                    self.query_one("#lbl-sup", Label).update(sup["CompanyName"])
        self.app.push_screen(
            PickerModal("Select Supplier",
                        [("ID", 4), ("Company", 26), ("City", 14), ("Country", 12)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
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
            cashdata.create_cp(self._supplier_id, None, amount, desc)
            self.notify("CP created.", severity="information")
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


class CashPanel(Widget):
    """Cash register panel with CR and CP tabs and running balance."""

    BINDINGS = [
        ("n", "new_record",   "New Entry"),
        ("f", "focus_search", "Search"),
    ]

    _cr_selected: str | None = None
    _cp_selected: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Static("", id="cash-balance")
            with Horizontal(classes="toolbar"):
                yield Button("→ Bank Acct", id="btn-transfer-bank", variant="warning")
            with TabbedContent(id="cash-tabs"):
                with TabPane("CR — Receipts", id="tab-cr"):
                    with Vertical():
                        yield DataTable(id="cr-tbl", cursor_type="row", zebra_stripes=True)
                        with Horizontal(classes="toolbar"):
                            yield Button("+ New CR", id="btn-new-cr", variant="success")
                            yield Button("PDF",      id="btn-pdf-cr")
                            yield Button("Delete",   id="btn-del-cr", variant="error")
                            yield Label("", id="cr-count", classes="count-label")
                with TabPane("CP — Payments", id="tab-cp"):
                    with Vertical():
                        yield DataTable(id="cp-tbl", cursor_type="row", zebra_stripes=True)
                        with Horizontal(classes="toolbar"):
                            yield Button("+ New CP", id="btn-new-cp", variant="success")
                            yield Button("PDF",      id="btn-pdf-cp")
                            yield Button("Delete",   id="btn-del-cp", variant="error")
                            yield Label("", id="cp-count", classes="count-label")

    def on_mount(self) -> None:
        cr_tbl = self.query_one("#cr-tbl", DataTable)
        for label, width in [
            ("ID", 6), ("Number", 16), ("Date", 12), ("Customer", 22),
            ("Amount", 12), ("Description", 20),
        ]:
            cr_tbl.add_column(label, width=width)

        cp_tbl = self.query_one("#cp-tbl", DataTable)
        for label, width in [
            ("ID", 6), ("Number", 16), ("Date", 12), ("Supplier", 22),
            ("Amount", 12), ("Description", 20),
        ]:
            cp_tbl.add_column(label, width=width)

        self._refresh_all()

    def _refresh_all(self) -> None:
        self._refresh_cr()
        self._refresh_cp()
        self._refresh_balance()

    def _refresh_balance(self) -> None:
        sym = get_currency_symbol()
        cr_total = cashdata.cash_balance_cr()
        cp_total = cashdata.cash_balance_cp()
        balance = cr_total - cp_total
        self.query_one("#cash-balance", Static).update(
            f"[b]Cash Balance:[/b]  In: {sym}{cr_total:.2f}  "
            f"Out: {sym}{cp_total:.2f}  "
            f"Net: [bold]{sym}{balance:.2f}[/bold]"
        )

    def _refresh_cr(self) -> None:
        tbl = self.query_one("#cr-tbl", DataTable)
        tbl.clear()
        sym = get_currency_symbol()
        rows = cashdata.fetch_all_cr()
        for row in rows:
            display = list(row)
            if display[4] is not None:
                display[4] = f"{sym}{float(display[4]):.2f}"
            tbl.add_row(*[str(c) if c is not None else "" for c in display], key=str(row[0]))
        try:
            self.query_one("#cr-count", Label).update(f"{len(rows)} records")
        except Exception:
            pass

    def _refresh_cp(self) -> None:
        tbl = self.query_one("#cp-tbl", DataTable)
        tbl.clear()
        sym = get_currency_symbol()
        rows = cashdata.fetch_all_cp()
        for row in rows:
            display = list(row)
            if display[4] is not None:
                display[4] = f"{sym}{float(display[4]):.2f}"
            tbl.add_row(*[str(c) if c is not None else "" for c in display], key=str(row[0]))
        try:
            self.query_one("#cp-count", Label).update(f"{len(rows)} records")
        except Exception:
            pass

    @on(DataTable.RowHighlighted, "#cr-tbl")
    def on_cr_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._cr_selected = event.row_key.value

    @on(DataTable.RowHighlighted, "#cp-tbl")
    def on_cp_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._cp_selected = event.row_key.value

    @on(Button.Pressed, "#btn-transfer-bank")
    def on_transfer_to_bank(self) -> None:
        def after(result):
            if result:
                amount, desc = result
                try:
                    cashdata.transfer_to_bank(amount, desc)
                    self._refresh_all()
                    self.notify(f"Transferred to bank: {amount:.2f}", severity="information")
                except Exception as e:
                    self.notify(f"Transfer failed: {e}", severity="error")
        self.app.push_screen(TransferModal("Transfer Cash → Bank Account"), callback=after)

    @on(Button.Pressed, "#btn-pdf-cr")
    def on_pdf_cr(self) -> None:
        if not self._cr_selected:
            self.notify("Select a CR entry first.", severity="warning")
            return
        try:
            import pdf_export
            path = pdf_export.export_cr(int(self._cr_selected))
            self.notify(f"PDF saved → {path}", severity="information")
        except Exception as e:
            self.notify(f"PDF error: {e}", severity="error")

    @on(Button.Pressed, "#btn-pdf-cp")
    def on_pdf_cp(self) -> None:
        if not self._cp_selected:
            self.notify("Select a CP entry first.", severity="warning")
            return
        try:
            import pdf_export
            path = pdf_export.export_cp(int(self._cp_selected))
            self.notify(f"PDF saved → {path}", severity="information")
        except Exception as e:
            self.notify(f"PDF error: {e}", severity="error")

    @on(Button.Pressed, "#btn-new-cr")
    def on_new_cr(self) -> None:
        def after(saved):
            if saved:
                self._refresh_all()
        self.app.push_screen(CRFormModal(), callback=after)

    @on(Button.Pressed, "#btn-new-cp")
    def on_new_cp(self) -> None:
        def after(saved):
            if saved:
                self._refresh_all()
        self.app.push_screen(CPFormModal(), callback=after)

    @on(Button.Pressed, "#btn-del-cr")
    def on_delete_cr(self) -> None:
        if not self._cr_selected:
            self.notify("Select a CR entry first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    cashdata.delete_cr(int(self._cr_selected))
                    self._cr_selected = None
                    self._refresh_all()
                    self.notify("CR deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"CR #{self._cr_selected}"), callback=after)

    @on(Button.Pressed, "#btn-del-cp")
    def on_delete_cp(self) -> None:
        if not self._cp_selected:
            self.notify("Select a CP entry first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    cashdata.delete_cp(int(self._cp_selected))
                    self._cp_selected = None
                    self._refresh_all()
                    self.notify("CP deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"CP #{self._cp_selected}"), callback=after)

    def action_new_record(self) -> None:
        try:
            active = self.query_one(TabbedContent).active
        except Exception:
            active = "tab-cr"
        if active == "tab-cp":
            def after(saved):
                if saved:
                    self._refresh_all()
            self.app.push_screen(CPFormModal(), callback=after)
        else:
            def after(saved):
                if saved:
                    self._refresh_all()
            self.app.push_screen(CRFormModal(), callback=after)

    def refresh_data(self) -> None:
        self._refresh_all()

    def action_focus_search(self) -> None:
        pass
