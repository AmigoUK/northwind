from __future__ import annotations
"""screens/stock_movements.py — PW/RW (internal stock movements) panel."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static, TabbedContent, TabPane
from textual import on

import data.pw_rw as pwrw
import data.products as pdata
from data.settings import get_backorder_allowed
from screens.modals import ConfirmDeleteModal, PickerModal


class MovementItemRow:
    """Temporary storage for a pending line item during form creation."""
    __slots__ = ("product_id", "product_name", "quantity")

    def __init__(self, product_id: int, product_name: str, quantity: int) -> None:
        self.product_id = product_id
        self.product_name = product_name
        self.quantity = quantity


class MovementFormModal(ModalScreen):
    """Create a new PW or RW movement document."""

    def __init__(self, doc_type: str) -> None:
        super().__init__()
        self.doc_type = doc_type  # "PW" or "RW"
        self._items: list[MovementItemRow] = []
        self._selected_idx: int | None = None

    def compose(self) -> ComposeResult:
        title = "PW — Przyjęcie Wewnętrzne" if self.doc_type == "PW" else "RW — Rozchód Wewnętrzny"
        with Vertical(classes="order-detail-dialog"):
            yield Label(f"New {title}", classes="modal-title")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Date (YYYY-MM-DD) *:")
                    yield Input(id="f-date", placeholder="2026-01-01")
                with Vertical(classes="form-field"):
                    yield Label("Reason:")
                    yield Input(id="f-reason", placeholder="Reason / description")
            yield Label("Items:", classes="section-label")
            yield DataTable(id="items-tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal():
                yield Button("+ Add Item", id="btn-add-item", variant="success")
                yield Button("- Remove",   id="btn-rem-item", variant="warning")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        from datetime import date
        self.query_one("#f-date", Input).value = str(date.today())
        tbl = self.query_one("#items-tbl", DataTable)
        for label, width in [("Product Name", 32), ("Quantity", 10)]:
            tbl.add_column(label, width=width)

    def _refresh_items_table(self) -> None:
        tbl = self.query_one("#items-tbl", DataTable)
        tbl.clear()
        for i, item in enumerate(self._items):
            tbl.add_row(item.product_name, str(item.quantity), key=str(i))

    @on(DataTable.RowHighlighted, "#items-tbl")
    def on_item_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            try:
                self._selected_idx = int(event.row_key.value)
            except (ValueError, TypeError):
                self._selected_idx = None

    @on(Button.Pressed, "#btn-add-item")
    def on_add_item(self) -> None:
        rows = pdata.fetch_for_picker()
        def after_product(pk):
            if not pk:
                return
            prod = pdata.get_by_pk(int(pk))
            if not prod:
                return

            class QtyModal(ModalScreen):
                def compose(inner_self) -> ComposeResult:
                    with Vertical(classes="confirm-dialog"):
                        yield Label(f"Quantity for {prod['ProductName']}:", classes="modal-title")
                        yield Input(id="f-qty", value="1", placeholder="1")
                        with Horizontal(classes="modal-buttons"):
                            yield Button("Add", id="btn-ok", variant="primary")
                            yield Button("Cancel", id="btn-cancel")

                @on(Button.Pressed, "#btn-ok")
                def on_ok(inner_self) -> None:
                    try:
                        qty = int(inner_self.query_one("#f-qty", Input).value.strip() or "1")
                    except ValueError:
                        inner_self.notify("Quantity must be a number.", severity="error")
                        return
                    if qty < 1:
                        inner_self.notify("Quantity must be at least 1.", severity="error")
                        return
                    inner_self.dismiss(qty)

                @on(Button.Pressed, "#btn-cancel")
                def on_cancel(inner_self) -> None:
                    inner_self.dismiss(None)

                def on_key(inner_self, event) -> None:
                    if event.key == "escape":
                        inner_self.dismiss(None)

            def after_qty(qty):
                if qty:
                    if self.doc_type == "RW":
                        available = pdata.get_stock(int(pk))
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
                    self._items.append(MovementItemRow(int(pk), prod["ProductName"], qty))
                    self._refresh_items_table()

            self.app.push_screen(QtyModal(), callback=after_qty)

        self.app.push_screen(
            PickerModal(
                "Select Product",
                [("ID", 4), ("Product Name", 28), ("Category", 16), ("Price", 8), ("Stock", 6)],
                rows,
            ),
            callback=after_product,
        )

    @on(Button.Pressed, "#btn-rem-item")
    def on_remove_item(self) -> None:
        if self._selected_idx is not None and 0 <= self._selected_idx < len(self._items):
            self._items.pop(self._selected_idx)
            self._selected_idx = None
            self._refresh_items_table()
        else:
            self.notify("Select an item first.", severity="warning")

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        from datetime import datetime
        doc_date = self.query_one("#f-date", Input).value.strip()
        try:
            datetime.strptime(doc_date, "%Y-%m-%d")
        except ValueError:
            self.notify("Date must be YYYY-MM-DD.", severity="error")
            return
        if not self._items:
            self.notify("Add at least one item.", severity="error")
            return
        reason = self.query_one("#f-reason", Input).value.strip()
        items_data = [{"product_id": it.product_id, "quantity": it.quantity}
                      for it in self._items]
        try:
            if self.doc_type == "PW":
                doc_id = pwrw.create_pw(doc_date, reason, items=items_data)
                self.notify(f"PW #{doc_id} created — stock increased.", severity="information")
            else:
                doc_id = pwrw.create_rw(doc_date, reason, items=items_data)
                self.notify(f"RW #{doc_id} created — stock decreased.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class MovementDetailModal(ModalScreen):
    """View a PW or RW document's details."""

    def __init__(self, doc_type: str, doc_id: int) -> None:
        super().__init__()
        self.doc_type = doc_type
        self.doc_id = doc_id

    def compose(self) -> ComposeResult:
        with Vertical(classes="order-detail-dialog"):
            yield Label("", id="doc-title", classes="modal-title")
            yield Static("", id="doc-header")
            yield Label("Items:", classes="section-label")
            yield DataTable(id="items-tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="modal-buttons"):
                yield Button("Delete", id="btn-delete", variant="error")
                yield Button("Close",  id="btn-close")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        tbl = self.query_one("#items-tbl", DataTable)
        for label, width in [("Product Name", 36), ("Quantity", 10)]:
            tbl.add_column(label, width=width)
        self._load()

    def _load(self) -> None:
        if self.doc_type == "PW":
            hdr = pwrw.get_pw_by_pk(self.doc_id)
            items = pwrw.fetch_pw_items(self.doc_id)
            num_field = "PW_Number"
            date_field = "PW_Date"
        else:
            hdr = pwrw.get_rw_by_pk(self.doc_id)
            items = pwrw.fetch_rw_items(self.doc_id)
            num_field = "RW_Number"
            date_field = "RW_Date"
        if not hdr:
            self.dismiss(False)
            return
        self.query_one("#doc-title", Label).update(
            f"{self.doc_type} #{self.doc_id} — {hdr.get(num_field, '')}"
        )
        info = [
            f"[b]Number:[/b] {hdr.get(num_field, '')}",
            f"[b]Date:[/b]   {hdr.get(date_field, '')}",
            f"[b]Reason:[/b] {hdr.get('Reason') or '—'}",
        ]
        self.query_one("#doc-header", Static).update("\n".join(info))
        tbl = self.query_one("#items-tbl", DataTable)
        tbl.clear()
        for it in items:
            tbl.add_row(it["ProductName"], str(it["Quantity"]))

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        def after(confirmed):
            if confirmed:
                try:
                    if self.doc_type == "PW":
                        pwrw.delete_pw(self.doc_id)
                    else:
                        pwrw.delete_rw(self.doc_id)
                    self.notify("Document deleted.", severity="information")
                    self.dismiss(True)
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(
            ConfirmDeleteModal(f"{self.doc_type} #{self.doc_id}"), callback=after
        )

    @on(Button.Pressed, "#btn-close")
    def on_close(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class StockMovementsPanel(Widget):
    """Panel with two tabs: PW (goods in) and RW (goods out)."""

    BINDINGS = [
        ("n", "new_record",   "New"),
        ("f", "focus_search", "Search"),
    ]

    _pw_selected: str | None = None
    _rw_selected: str | None = None

    def compose(self) -> ComposeResult:
        with TabbedContent(id="mov-tabs"):
            with TabPane("PW — Goods In", id="tab-pw"):
                with Vertical(classes="panel-container"):
                    yield DataTable(id="pw-tbl", cursor_type="row", zebra_stripes=True)
                    with Horizontal(classes="toolbar"):
                        yield Button("+ New PW", id="btn-new-pw", variant="success")
                        yield Button("Open",     id="btn-open-pw")
                        yield Button("Delete",   id="btn-del-pw", variant="error")
                        yield Label("", id="pw-count", classes="count-label")
            with TabPane("RW — Goods Out", id="tab-rw"):
                with Vertical(classes="panel-container"):
                    yield DataTable(id="rw-tbl", cursor_type="row", zebra_stripes=True)
                    with Horizontal(classes="toolbar"):
                        yield Button("+ New RW", id="btn-new-rw", variant="success")
                        yield Button("Open",     id="btn-open-rw")
                        yield Button("Delete",   id="btn-del-rw", variant="error")
                        yield Label("", id="rw-count", classes="count-label")

    def on_mount(self) -> None:
        pw_tbl = self.query_one("#pw-tbl", DataTable)
        for label, width in [("ID", 6), ("Number", 16), ("Date", 12), ("Reason", 26), ("Qty", 6)]:
            pw_tbl.add_column(label, width=width)

        rw_tbl = self.query_one("#rw-tbl", DataTable)
        for label, width in [("ID", 6), ("Number", 16), ("Date", 12), ("Reason", 26), ("Qty", 6)]:
            rw_tbl.add_column(label, width=width)

        self._refresh_pw()
        self._refresh_rw()

    def _refresh_pw(self) -> None:
        tbl = self.query_one("#pw-tbl", DataTable)
        tbl.clear()
        rows = pwrw.fetch_all_pw()
        for row in rows:
            tbl.add_row(*[str(c) if c is not None else "" for c in row], key=str(row[0]))
        try:
            self.query_one("#pw-count", Label).update(f"{len(rows)} records")
        except Exception:
            pass

    def _refresh_rw(self) -> None:
        tbl = self.query_one("#rw-tbl", DataTable)
        tbl.clear()
        rows = pwrw.fetch_all_rw()
        for row in rows:
            tbl.add_row(*[str(c) if c is not None else "" for c in row], key=str(row[0]))
        try:
            self.query_one("#rw-count", Label).update(f"{len(rows)} records")
        except Exception:
            pass

    @on(DataTable.RowHighlighted, "#pw-tbl")
    def on_pw_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._pw_selected = event.row_key.value

    @on(DataTable.RowHighlighted, "#rw-tbl")
    def on_rw_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._rw_selected = event.row_key.value

    @on(DataTable.RowSelected, "#pw-tbl")
    def on_pw_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key:
            self._open_detail("PW", int(event.row_key.value))

    @on(DataTable.RowSelected, "#rw-tbl")
    def on_rw_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key:
            self._open_detail("RW", int(event.row_key.value))

    def _open_detail(self, doc_type: str, doc_id: int) -> None:
        def after(changed):
            if changed:
                self._refresh_pw()
                self._refresh_rw()
        self.app.push_screen(MovementDetailModal(doc_type, doc_id), callback=after)

    @on(Button.Pressed, "#btn-new-pw")
    def on_new_pw(self) -> None:
        def after(saved):
            if saved:
                self._refresh_pw()
        self.app.push_screen(MovementFormModal("PW"), callback=after)

    @on(Button.Pressed, "#btn-new-rw")
    def on_new_rw(self) -> None:
        def after(saved):
            if saved:
                self._refresh_rw()
        self.app.push_screen(MovementFormModal("RW"), callback=after)

    @on(Button.Pressed, "#btn-open-pw")
    def on_open_pw(self) -> None:
        if self._pw_selected:
            self._open_detail("PW", int(self._pw_selected))
        else:
            self.notify("Select a PW document first.", severity="warning")

    @on(Button.Pressed, "#btn-open-rw")
    def on_open_rw(self) -> None:
        if self._rw_selected:
            self._open_detail("RW", int(self._rw_selected))
        else:
            self.notify("Select a RW document first.", severity="warning")

    @on(Button.Pressed, "#btn-del-pw")
    def on_delete_pw(self) -> None:
        if not self._pw_selected:
            self.notify("Select a PW document first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    pwrw.delete_pw(int(self._pw_selected))
                    self._pw_selected = None
                    self._refresh_pw()
                    self.notify("PW deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"PW #{self._pw_selected}"), callback=after)

    @on(Button.Pressed, "#btn-del-rw")
    def on_delete_rw(self) -> None:
        if not self._rw_selected:
            self.notify("Select a RW document first.", severity="warning")
            return
        def after(confirmed):
            if confirmed:
                try:
                    pwrw.delete_rw(int(self._rw_selected))
                    self._rw_selected = None
                    self._refresh_rw()
                    self.notify("RW deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")
        self.app.push_screen(ConfirmDeleteModal(f"RW #{self._rw_selected}"), callback=after)

    def action_new_record(self) -> None:
        # Determine active tab
        try:
            active = self.query_one(TabbedContent).active
            doc_type = "RW" if active == "tab-rw" else "PW"
        except Exception:
            doc_type = "PW"
        def after(saved):
            if saved:
                self._refresh_pw()
                self._refresh_rw()
        self.app.push_screen(MovementFormModal(doc_type), callback=after)

    def action_focus_search(self) -> None:
        pass  # No search box in this panel
