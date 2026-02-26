from __future__ import annotations
"""screens/wz.py — WZ (Wydanie Zewnętrzne) panel, detail, and form modals."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static
from textual import on

import data.wz as wzdata
import data.customers as cdata
import data.products as pdata
from data.settings import get_currency_symbol, get_backorder_allowed
from screens.modals import ConfirmActionModal, ConfirmDeleteModal, PickerModal


class WZItemFormModal(ModalScreen):
    """Add a line item to a WZ document."""

    def __init__(self, wz_id: int) -> None:
        super().__init__()
        self.wz_id = wz_id
        self._product_id = None
        self._product_name = ""

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(f"Add Item to WZ #{self.wz_id}", classes="modal-title")
            yield Label("Product:")
            with Horizontal():
                yield Label("(none)", id="lbl-product")
                yield Button("Pick Product", id="btn-pick-prod")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Unit Price:")
                    yield Input(id="f-price", placeholder="0.00")
                with Vertical(classes="form-field"):
                    yield Label("Quantity:")
                    yield Input(id="f-qty", value="1", placeholder="1")
            with Horizontal(classes="modal-buttons"):
                yield Button("Add", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    @on(Button.Pressed, "#btn-pick-prod")
    def on_pick_product(self) -> None:
        rows = pdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._product_id = int(pk)
                prod = pdata.get_by_pk(int(pk))
                if prod:
                    self._product_name = prod["ProductName"]
                    self.query_one("#lbl-product", Label).update(prod["ProductName"])
                    self.query_one("#f-price", Input).value = str(prod.get("UnitPrice", 0.0))
        self.app.push_screen(
            PickerModal(
                "Select Product",
                [("ID", 4), ("Product Name", 28), ("Category", 16), ("Price", 8), ("Stock", 6)],
                rows,
            ),
            callback=after,
        )

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        if not self._product_id:
            self.notify("Select a product first.", severity="error")
            return
        try:
            price = float(self.query_one("#f-price", Input).value.strip() or "0")
            qty   = int(self.query_one("#f-qty",   Input).value.strip() or "1")
        except ValueError:
            self.notify("Price and Quantity must be numbers.", severity="error")
            return
        if qty < 1:
            self.notify("Quantity must be at least 1.", severity="error")
            return
        available = pdata.get_stock(self._product_id)
        if qty > available:
            if get_backorder_allowed():
                self.notify(
                    f"Stock: {available} available. Backorder active — saving {qty}.",
                    severity="warning",
                )
            elif available == 0:
                self.notify("No stock available. Cannot add item.", severity="error")
                return
            else:
                self.notify(
                    f"Only {available} in stock. Quantity clamped to {available}.",
                    severity="warning",
                )
                qty = available
        try:
            wzdata.add_item(self.wz_id, self._product_id, qty, price)
            self.notify(f"'{self._product_name}' added.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class WZFormModal(ModalScreen):
    """Create a new standalone WZ document (draft)."""

    def __init__(self) -> None:
        super().__init__()
        self._customer_id = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("New WZ — Wydanie Zewnętrzne", classes="modal-title")
            yield Label("Customer *:")
            with Horizontal():
                yield Label("(none)", id="lbl-customer")
                yield Button("Pick Customer", id="btn-pick-cust")
            yield Label("WZ Date (YYYY-MM-DD):")
            yield Input(id="f-date", placeholder="2026-01-01")
            yield Label("Notes:")
            yield Input(id="f-notes", placeholder="Optional notes")
            with Horizontal(classes="modal-buttons"):
                yield Button("Create Draft", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        from datetime import date
        self.query_one("#f-date", Input).value = str(date.today())

    @on(Button.Pressed, "#btn-pick-cust")
    def on_pick_customer(self) -> None:
        rows = cdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._customer_id = pk
                cust = cdata.get_by_pk(pk)
                if cust:
                    self.query_one("#lbl-customer", Label).update(cust["CompanyName"])
        self.app.push_screen(
            PickerModal("Select Customer",
                        [("ID", 6), ("Company", 26), ("Contact", 18), ("City", 12)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        from datetime import datetime
        if not self._customer_id:
            self.notify("Customer is required.", severity="error")
            return
        wz_date = self.query_one("#f-date", Input).value.strip()
        if not wz_date:
            self.notify("WZ Date is required.", severity="error")
            return
        try:
            datetime.strptime(wz_date, "%Y-%m-%d")
        except ValueError:
            self.notify("Date must be YYYY-MM-DD.", severity="error")
            return
        notes = self.query_one("#f-notes", Input).value.strip()
        try:
            wz_id = wzdata.create_draft(self._customer_id, wz_date, notes=notes)
            self.notify(f"WZ draft created (ID #{wz_id}).", severity="information")
            self.dismiss(wz_id)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class WZDetailModal(ModalScreen):
    """Full WZ detail with line items."""

    def __init__(self, wz_id: int) -> None:
        super().__init__()
        self.wz_id = wz_id
        self._changed = False
        self._selected_product_id = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="order-detail-dialog"):
            yield Label("", id="wz-title", classes="modal-title")
            yield Static("", id="wz-header")
            yield Label("Line Items:", classes="section-label")
            yield DataTable(id="items-tbl", cursor_type="row", zebra_stripes=True)
            yield Static("", id="wz-total")
            with Horizontal(classes="modal-buttons"):
                yield Button("Issue WZ",   id="btn-issue",  variant="primary")
                yield Button("+ Item",     id="btn-add",    variant="success")
                yield Button("- Item",     id="btn-remove", variant="warning")
                yield Button("Delete",     id="btn-delete", variant="error")
                yield Button("PDF",        id="btn-pdf",    variant="default")
                yield Button("Close",      id="btn-close")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        from data.settings import get_setting
        self._show_prices = get_setting("doc_wz_show_prices", "true").lower() == "true"
        tbl = self.query_one("#items-tbl", DataTable)
        tbl.add_column("ProdID", width=6)
        tbl.add_column("Product Name", width=36)
        tbl.add_column("Qty", width=6)
        if self._show_prices:
            tbl.add_column("Unit Price", width=12)
            tbl.add_column("Line Total", width=12)
        self._load()

    def _load(self) -> None:
        sym = get_currency_symbol()
        hdr = wzdata.get_by_pk(self.wz_id)
        if not hdr:
            self.dismiss(self._changed)
            return
        self.query_one("#wz-title", Label).update(f"WZ #{self.wz_id} — {hdr.get('WZ_Number', '')}")
        lines_info = [
            f"[b]Number:[/b]   {hdr.get('WZ_Number', '')}",
            f"[b]Customer:[/b] {hdr.get('CustomerID', '')} — {hdr.get('CompanyName') or ''}",
            f"[b]Date:[/b]     {hdr.get('WZ_Date', '')}   [b]Status:[/b] {hdr.get('Status', '')}",
        ]
        if hdr.get("OrderID"):
            lines_info.append(f"[b]Source SO:[/b] Order #{hdr['OrderID']}")
        if hdr.get("Notes"):
            lines_info.append(f"[b]Notes:[/b]    {hdr['Notes']}")
        self.query_one("#wz-header", Static).update("\n".join(lines_info))

        tbl = self.query_one("#items-tbl", DataTable)
        tbl.clear()
        items = wzdata.fetch_items(self.wz_id)
        total = 0.0
        for it in items:
            lt = it["LineTotal"]
            total += lt
            if self._show_prices:
                row_data = (
                    str(it["ProductID"]),
                    it["ProductName"],
                    str(it["Quantity"]),
                    f"{sym}{it['UnitPrice']:.2f}",
                    f"{sym}{lt:.2f}",
                )
            else:
                row_data = (
                    str(it["ProductID"]),
                    it["ProductName"],
                    str(it["Quantity"]),
                )
            tbl.add_row(*row_data, key=str(it["ProductID"]))
        total_widget = self.query_one("#wz-total", Static)
        if self._show_prices:
            total_widget.update(f"[b]Total:[/b] {sym}{total:.2f}")
        else:
            total_widget.update("")

        # Adjust buttons based on status
        status = hdr.get("Status", "draft")
        try:
            self.query_one("#btn-issue", Button).disabled = (status != "draft")
            self.query_one("#btn-add",   Button).disabled = (status != "draft")
            self.query_one("#btn-remove",Button).disabled = (status != "draft")
            self.query_one("#btn-delete",Button).disabled = (status == "issued")
        except Exception:
            pass

    @on(DataTable.RowHighlighted, "#items-tbl")
    def on_item_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._selected_product_id = event.row_key.value

    @on(Button.Pressed, "#btn-issue")
    def on_issue(self) -> None:
        def after(confirmed):
            if confirmed:
                try:
                    wzdata.issue(self.wz_id)
                    self._changed = True
                    self._load()
                    self.notify("WZ issued — stock updated.", severity="information")
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
        self.app.push_screen(
            ConfirmActionModal(
                f"Issue WZ #{self.wz_id}?",
                "Stock will be reduced for each line item.",
                confirm_label="Issue",
            ),
            callback=after,
        )

    @on(Button.Pressed, "#btn-add")
    def on_add_item(self) -> None:
        def after(saved):
            if saved:
                self._changed = True
                self._load()
        self.app.push_screen(WZItemFormModal(self.wz_id), callback=after)

    @on(Button.Pressed, "#btn-remove")
    def on_remove_item(self) -> None:
        if not self._selected_product_id:
            self.notify("Select a line item first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    wzdata.remove_item(self.wz_id, int(self._selected_product_id))
                    self._selected_product_id = None
                    self._changed = True
                    self._load()
                    self.notify("Item removed.", severity="information")
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal("this line item"), callback=after)

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        def after(confirmed):
            if confirmed:
                try:
                    wzdata.delete(self.wz_id)
                    self.dismiss(True)
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"WZ #{self.wz_id}"), callback=after)

    @on(Button.Pressed, "#btn-pdf")
    def on_pdf(self) -> None:
        try:
            import pdf_export
            path = pdf_export.export_wz(self.wz_id)
            self.notify(f"PDF saved → {path}", severity="information")
        except Exception as e:
            self.notify(f"PDF error: {e}", severity="error")

    @on(Button.Pressed, "#btn-close")
    def on_close(self) -> None:
        self.dismiss(self._changed)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(self._changed)


class WZPanel(Widget):
    BINDINGS = [
        ("n", "new_record",   "New WZ"),
        ("f", "focus_search", "Search"),
    ]

    _selected_pk = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Input(placeholder="Search WZ documents...", id="search-box")
            yield DataTable(id="tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("+ New",  id="btn-new",    variant="success")
                yield Button("Open",   id="btn-open")
                yield Button("Delete", id="btn-delete", variant="error")
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        for label, width in [
            ("ID", 6), ("Number", 16), ("Date", 12), ("Customer", 24),
            ("Status", 10), ("Total", 12),
        ]:
            tbl.add_column(label, width=width)
        self.refresh_data()

    def refresh_data(self, term: str = "") -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        rows = wzdata.search(term) if term else wzdata.fetch_all()
        sym = get_currency_symbol()
        for row in rows:
            display = list(row)
            if display[5] is not None:
                display[5] = f"{sym}{float(display[5]):.2f}"
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

    def _open_detail(self, wz_id: int) -> None:
        def after(changed):
            if changed:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(WZDetailModal(wz_id), callback=after)

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-open")
    def on_btn_open(self) -> None:
        if self._selected_pk:
            self._open_detail(int(self._selected_pk))
        else:
            self.notify("Select a WZ document first.", severity="warning")

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        if not self._selected_pk:
            self.notify("Select a WZ document first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    wzdata.delete(int(self._selected_pk))
                    self._selected_pk = None
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify("WZ deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"WZ #{self._selected_pk}"), callback=after)

    def action_new_record(self) -> None:
        def after_form(wz_id):
            if wz_id:
                def after_detail(changed):
                    self.refresh_data(self.query_one("#search-box", Input).value)
                self.app.push_screen(WZDetailModal(wz_id), callback=after_detail)
        self.app.push_screen(WZFormModal(), callback=after_form)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()
