from __future__ import annotations
"""screens/kassa.py — Cash register panel (KP receipts + KW payments)."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static, TabbedContent, TabPane
from textual import on

import data.kassa as kassadata
import data.customers as cdata
import data.suppliers as sdata
from data.settings import get_currency_symbol
from screens.modals import ConfirmDeleteModal, PickerModal


class KPFormModal(ModalScreen):
    """Create a manual KP cash receipt."""

    def __init__(self) -> None:
        super().__init__()
        self._customer_id = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("New KP — Kasa Przyjmie", classes="modal-title")
            yield Label("Customer (optional):")
            with Horizontal():
                yield Label("(none)", id="lbl-cust")
                yield Button("Pick Customer", id="btn-pick-cust")
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
            kassadata.create_kp(self._customer_id, None, amount, desc)
            self.notify("KP created.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class KWFormModal(ModalScreen):
    """Create a manual KW cash payment."""

    def __init__(self) -> None:
        super().__init__()
        self._supplier_id = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("New KW — Kasa Wypłaci", classes="modal-title")
            yield Label("Supplier (optional):")
            with Horizontal():
                yield Label("(none)", id="lbl-sup")
                yield Button("Pick Supplier", id="btn-pick-sup")
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
            kassadata.create_kw(self._supplier_id, None, amount, desc)
            self.notify("KW created.", severity="information")
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


class KassaPanel(Widget):
    """Cash register panel with KP and KW tabs and running balance."""

    BINDINGS = [
        ("n", "new_record",   "New Entry"),
        ("f", "focus_search", "Search"),
    ]

    _kp_selected: str | None = None
    _kw_selected: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Static("", id="kassa-balance")
            with Horizontal(classes="toolbar"):
                yield Button("→ Bank", id="btn-transfer-bank", variant="warning")
            with TabbedContent(id="kassa-tabs"):
                with TabPane("KP — Receipts", id="tab-kp"):
                    with Vertical():
                        yield DataTable(id="kp-tbl", cursor_type="row", zebra_stripes=True)
                        with Horizontal(classes="toolbar"):
                            yield Button("+ New KP", id="btn-new-kp", variant="success")
                            yield Button("Delete",   id="btn-del-kp", variant="error")
                            yield Label("", id="kp-count", classes="count-label")
                with TabPane("KW — Payments", id="tab-kw"):
                    with Vertical():
                        yield DataTable(id="kw-tbl", cursor_type="row", zebra_stripes=True)
                        with Horizontal(classes="toolbar"):
                            yield Button("+ New KW", id="btn-new-kw", variant="success")
                            yield Button("Delete",   id="btn-del-kw", variant="error")
                            yield Label("", id="kw-count", classes="count-label")

    def on_mount(self) -> None:
        kp_tbl = self.query_one("#kp-tbl", DataTable)
        for label, width in [
            ("ID", 6), ("Number", 16), ("Date", 12), ("Customer", 22),
            ("Amount", 12), ("Description", 20),
        ]:
            kp_tbl.add_column(label, width=width)

        kw_tbl = self.query_one("#kw-tbl", DataTable)
        for label, width in [
            ("ID", 6), ("Number", 16), ("Date", 12), ("Supplier", 22),
            ("Amount", 12), ("Description", 20),
        ]:
            kw_tbl.add_column(label, width=width)

        self._refresh_all()

    def _refresh_all(self) -> None:
        self._refresh_kp()
        self._refresh_kw()
        self._refresh_balance()

    def _refresh_balance(self) -> None:
        sym = get_currency_symbol()
        kp_total = kassadata.cash_balance_kp()
        kw_total = kassadata.cash_balance_kw()
        balance = kp_total - kw_total
        self.query_one("#kassa-balance", Static).update(
            f"[b]Cash Balance:[/b]  In: {sym}{kp_total:.2f}  "
            f"Out: {sym}{kw_total:.2f}  "
            f"Net: [bold]{sym}{balance:.2f}[/bold]"
        )

    def _refresh_kp(self) -> None:
        tbl = self.query_one("#kp-tbl", DataTable)
        tbl.clear()
        sym = get_currency_symbol()
        rows = kassadata.fetch_all_kp()
        for row in rows:
            display = list(row)
            if display[4] is not None:
                display[4] = f"{sym}{float(display[4]):.2f}"
            tbl.add_row(*[str(c) if c is not None else "" for c in display], key=str(row[0]))
        try:
            self.query_one("#kp-count", Label).update(f"{len(rows)} records")
        except Exception:
            pass

    def _refresh_kw(self) -> None:
        tbl = self.query_one("#kw-tbl", DataTable)
        tbl.clear()
        sym = get_currency_symbol()
        rows = kassadata.fetch_all_kw()
        for row in rows:
            display = list(row)
            if display[4] is not None:
                display[4] = f"{sym}{float(display[4]):.2f}"
            tbl.add_row(*[str(c) if c is not None else "" for c in display], key=str(row[0]))
        try:
            self.query_one("#kw-count", Label).update(f"{len(rows)} records")
        except Exception:
            pass

    @on(DataTable.RowHighlighted, "#kp-tbl")
    def on_kp_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._kp_selected = event.row_key.value

    @on(DataTable.RowHighlighted, "#kw-tbl")
    def on_kw_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._kw_selected = event.row_key.value

    @on(Button.Pressed, "#btn-transfer-bank")
    def on_transfer_to_bank(self) -> None:
        def after(result):
            if result:
                amount, desc = result
                try:
                    kassadata.transfer_to_bank(amount, desc)
                    self._refresh_all()
                    self.notify(f"Transferred to bank: {amount:.2f}", severity="information")
                except Exception as e:
                    self.notify(f"Transfer failed: {e}", severity="error")
        self.app.push_screen(TransferModal("Transfer Cash → Bank"), callback=after)

    @on(Button.Pressed, "#btn-new-kp")
    def on_new_kp(self) -> None:
        def after(saved):
            if saved:
                self._refresh_all()
        self.app.push_screen(KPFormModal(), callback=after)

    @on(Button.Pressed, "#btn-new-kw")
    def on_new_kw(self) -> None:
        def after(saved):
            if saved:
                self._refresh_all()
        self.app.push_screen(KWFormModal(), callback=after)

    @on(Button.Pressed, "#btn-del-kp")
    def on_delete_kp(self) -> None:
        if not self._kp_selected:
            self.notify("Select a KP entry first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    kassadata.delete_kp(int(self._kp_selected))
                    self._kp_selected = None
                    self._refresh_all()
                    self.notify("KP deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"KP #{self._kp_selected}"), callback=after)

    @on(Button.Pressed, "#btn-del-kw")
    def on_delete_kw(self) -> None:
        if not self._kw_selected:
            self.notify("Select a KW entry first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    kassadata.delete_kw(int(self._kw_selected))
                    self._kw_selected = None
                    self._refresh_all()
                    self.notify("KW deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"KW #{self._kw_selected}"), callback=after)

    def action_new_record(self) -> None:
        try:
            active = self.query_one(TabbedContent).active
        except Exception:
            active = "tab-kp"
        if active == "tab-kw":
            def after(saved):
                if saved:
                    self._refresh_all()
            self.app.push_screen(KWFormModal(), callback=after)
        else:
            def after(saved):
                if saved:
                    self._refresh_all()
            self.app.push_screen(KPFormModal(), callback=after)

    def refresh_data(self) -> None:
        self._refresh_all()

    def action_focus_search(self) -> None:
        pass
