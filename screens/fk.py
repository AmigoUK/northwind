from __future__ import annotations
"""screens/fk.py — FK (Faktura Korygujaca / Credit Note) panel, detail, and creation flow."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Checkbox, DataTable, Input, Label, Select, Static
from textual import on

import data.fk as fkdata
import data.fv as fvdata
import data.customers as cdata
from data.settings import get_currency_symbol
from screens.modals import PickerModal


class FKNewModal(ModalScreen):
    """Creation wizard for a new FK (Credit Note).
    Can be opened standalone (pick FV) or pre-populated from FVDetailModal.
    """

    def __init__(self, fv_id: int | None = None) -> None:
        super().__init__()
        self._fv_id = fv_id
        self._fv_data = None
        self._fk_type = "full_reversal"
        self._corrections: list[dict] = []

    def compose(self) -> ComposeResult:
        with Vertical(classes="order-detail-dialog"):
            yield Label("New FK — Faktura Korygujaca", classes="modal-title")
            yield Label("Original Invoice:")
            with Horizontal():
                yield Label("(none)", id="lbl-fv")
                yield Button("Pick FV", id="btn-pick-fv")
            yield Static("", id="fv-info")
            yield Label("FK Type:")
            yield Select(
                [
                    ("Full Reversal", "full_reversal"),
                    ("Partial Correction", "partial_correction"),
                    ("Cancellation (FV + FK)", "cancellation"),
                ],
                id="f-type", value="full_reversal",
            )
            yield Label("Line Items (for partial correction):", classes="section-label")
            yield DataTable(id="items-tbl", cursor_type="row", zebra_stripes=True)
            yield Static("", id="correction-preview")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("FK Date (YYYY-MM-DD) *:")
                    yield Input(id="f-date", placeholder="2026-01-01")
                with Vertical(classes="form-field"):
                    yield Label("Reason (required) *:")
                    yield Input(id="f-reason", placeholder="Reason for correction")
            yield Label("Notes:")
            yield Input(id="f-notes", placeholder="Optional notes")
            yield Checkbox("Return goods to stock", id="f-reverse-stock", value=False)
            with Horizontal(classes="modal-buttons"):
                yield Button("Create FK", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        from datetime import date
        self.query_one("#f-date", Input).value = str(date.today())
        tbl = self.query_one("#items-tbl", DataTable)
        for label, width in [
            ("ProdID", 6), ("Product", 26), ("Orig Qty", 8),
            ("New Qty", 8), ("Orig Price", 10), ("New Price", 10),
        ]:
            tbl.add_column(label, width=width)
        if self._fv_id:
            self._load_fv(self._fv_id)

    def _load_fv(self, fv_id: int) -> None:
        self._fv_id = fv_id
        self._fv_data = fvdata.get_by_pk(fv_id)
        if not self._fv_data:
            self.notify("FV not found.", severity="error")
            return
        fv = self._fv_data
        self.query_one("#lbl-fv", Label).update(
            f"FV #{fv['FV_ID']} — {fv.get('FV_Number', '')}"
        )
        sym = get_currency_symbol()
        self.query_one("#fv-info", Static).update(
            f"Customer: {fv.get('CompanyName', '')} | "
            f"Total: {sym}{fv.get('TotalNet', 0):.2f} | "
            f"Paid: {sym}{fv.get('PaidAmount', 0):.2f} | "
            f"Status: {fv.get('Status', '')}"
        )
        self._load_items()

    def _load_items(self) -> None:
        """Load original FV line items into corrections list and table."""
        if not self._fv_id:
            return
        items = fvdata.fetch_line_items(self._fv_id)
        self._corrections = []
        for it in items:
            self._corrections.append({
                "product_id": it["ProductID"],
                "product_name": it["ProductName"],
                "orig_quantity": it["Quantity"],
                "new_quantity": it["Quantity"],
                "orig_unit_price": it["UnitPrice"],
                "new_unit_price": it["UnitPrice"],
            })
        self._refresh_items_table()

    def _refresh_items_table(self) -> None:
        tbl = self.query_one("#items-tbl", DataTable)
        tbl.clear()
        sym = get_currency_symbol()
        total_correction = 0.0
        is_partial = self._fk_type == "partial_correction"
        for corr in self._corrections:
            orig_total = corr["orig_quantity"] * corr["orig_unit_price"]
            if is_partial:
                new_total = corr["new_quantity"] * corr["new_unit_price"]
            else:
                new_total = 0  # full reversal: all go to 0
            line_corr = new_total - orig_total
            total_correction += line_corr
            new_qty_display = str(corr["new_quantity"]) if is_partial else "0"
            new_price_display = f"{sym}{corr['new_unit_price']:.2f}" if is_partial else "—"
            tbl.add_row(
                str(corr["product_id"]),
                corr["product_name"],
                str(corr["orig_quantity"]),
                new_qty_display,
                f"{sym}{corr['orig_unit_price']:.2f}",
                new_price_display,
                key=str(corr["product_id"]),
            )
        self.query_one("#correction-preview", Static).update(
            f"[b]Total Correction:[/b] {sym}{total_correction:.2f}"
        )
        # Show/hide items table based on type
        tbl.display = is_partial

    @on(Select.Changed, "#f-type")
    def on_type_changed(self, event: Select.Changed) -> None:
        val = event.value
        self._fk_type = str(val) if val != Select.BLANK else "full_reversal"
        self._refresh_items_table()

    @on(DataTable.RowSelected, "#items-tbl")
    def on_item_selected(self, event: DataTable.RowSelected) -> None:
        """For partial correction: allow editing quantity/price."""
        if self._fk_type != "partial_correction":
            return
        if not event.row_key:
            return
        pid = int(event.row_key.value)
        corr = next((c for c in self._corrections if c["product_id"] == pid), None)
        if not corr:
            return
        # Open inline edit modal
        def after(result):
            if result:
                corr["new_quantity"] = result["new_quantity"]
                corr["new_unit_price"] = result["new_unit_price"]
                self._refresh_items_table()
        self.app.push_screen(
            FKItemEditModal(corr["product_name"], corr["orig_quantity"],
                           corr["orig_unit_price"], corr["new_quantity"],
                           corr["new_unit_price"]),
            callback=after,
        )

    @on(Button.Pressed, "#btn-pick-fv")
    def on_pick_fv(self) -> None:
        rows = fvdata.fetch_all()
        def after(pk):
            if pk:
                self._load_fv(int(pk))
        self.app.push_screen(
            PickerModal(
                "Select Invoice (FV)",
                [("ID", 6), ("Number", 16), ("Date", 12), ("Customer", 22),
                 ("Status", 8), ("Payment", 8), ("Total", 12)],
                rows,
            ),
            callback=after,
        )

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        from datetime import datetime
        if not self._fv_id:
            self.notify("Select an invoice first.", severity="error")
            return
        reason = self.query_one("#f-reason", Input).value.strip()
        if not reason:
            self.notify("Reason is required.", severity="error")
            return
        fk_date = self.query_one("#f-date", Input).value.strip()
        try:
            datetime.strptime(fk_date, "%Y-%m-%d")
        except ValueError:
            self.notify("Date must be YYYY-MM-DD.", severity="error")
            return
        notes = self.query_one("#f-notes", Input).value.strip()
        reverse_stock = self.query_one("#f-reverse-stock", Checkbox).value
        user_id = getattr(self.app, "_current_user", {}).get("user_id", 0)

        try:
            if self._fk_type == "full_reversal":
                fk_id = fkdata.create_full_reversal(
                    self._fv_id, reason, fk_date, user_id, reverse_stock, notes,
                )
            elif self._fk_type == "partial_correction":
                corrections = [
                    {
                        "product_id": c["product_id"],
                        "new_quantity": c["new_quantity"],
                        "new_unit_price": c["new_unit_price"],
                    }
                    for c in self._corrections
                    if (c["new_quantity"] != c["orig_quantity"]
                        or c["new_unit_price"] != c["orig_unit_price"])
                ]
                if not corrections:
                    self.notify("No corrections made. Adjust quantities or prices.", severity="error")
                    return
                fk_id = fkdata.create_partial_correction(
                    self._fv_id, reason, fk_date, user_id, corrections,
                    reverse_stock, notes,
                )
            else:  # cancellation
                fk_id = fkdata.create_cancellation(
                    self._fv_id, reason, fk_date, user_id, reverse_stock, notes,
                )
            self.notify(f"FK #{fk_id} created.", severity="information")
            self.dismiss(fk_id)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class FKItemEditModal(ModalScreen):
    """Edit quantity and price for a single FK correction line."""

    def __init__(self, product_name: str, orig_qty: int, orig_price: float,
                 current_qty: int, current_price: float) -> None:
        super().__init__()
        self._product_name = product_name
        self._orig_qty = orig_qty
        self._orig_price = orig_price
        self._current_qty = current_qty
        self._current_price = current_price

    def compose(self) -> ComposeResult:
        with Vertical(classes="confirm-dialog"):
            yield Label(f"Edit: {self._product_name}", classes="modal-title")
            yield Label(f"Original: qty={self._orig_qty}, price={self._orig_price:.2f}")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("New Quantity:")
                    yield Input(id="f-qty", value=str(self._current_qty))
                with Vertical(classes="form-field"):
                    yield Label("New Unit Price:")
                    yield Input(id="f-price", value=f"{self._current_price:.2f}")
            with Horizontal(classes="modal-buttons"):
                yield Button("OK", id="btn-ok", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    @on(Button.Pressed, "#btn-ok")
    def on_ok(self) -> None:
        try:
            qty = int(self.query_one("#f-qty", Input).value.strip())
            price = float(self.query_one("#f-price", Input).value.strip())
        except ValueError:
            self.notify("Enter valid numbers.", severity="error")
            return
        if qty < 0:
            self.notify("Quantity cannot be negative.", severity="error")
            return
        self.dismiss({"new_quantity": qty, "new_unit_price": price})

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class FKDetailModal(ModalScreen):
    """Read-only FK detail view."""

    def __init__(self, fk_id: int) -> None:
        super().__init__()
        self.fk_id = fk_id

    def compose(self) -> ComposeResult:
        with Vertical(classes="order-detail-dialog"):
            yield Label("", id="fk-title", classes="modal-title")
            yield Static("", id="fk-header")
            yield Label("Correction Items:", classes="section-label")
            yield DataTable(id="items-tbl", cursor_type="row", zebra_stripes=True)
            yield Static("", id="fk-total")
            with Horizontal(classes="modal-buttons"):
                yield Button("PDF", id="btn-pdf", variant="default")
                yield Button("Close", id="btn-close")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        tbl = self.query_one("#items-tbl", DataTable)
        for label, width in [
            ("ProdID", 6), ("Product", 22), ("Orig Qty", 8), ("Corr Qty", 8),
            ("Orig Price", 10), ("Corr Price", 10), ("Correction", 12),
        ]:
            tbl.add_column(label, width=width)
        self._load()

    def _load(self) -> None:
        sym = get_currency_symbol()
        hdr = fkdata.get_by_pk(self.fk_id)
        if not hdr:
            self.dismiss(False)
            return
        self.query_one("#fk-title", Label).update(
            f"FK #{self.fk_id} — {hdr.get('FK_Number', '')}"
        )
        info = [
            f"[b]Number:[/b]    {hdr.get('FK_Number', '')}",
            f"[b]Orig FV:[/b]   {hdr.get('FV_Number', '')} (FV_ID #{hdr.get('FV_ID', '')})",
            f"[b]Customer:[/b]  {hdr.get('CompanyName', '')}",
            f"[b]Date:[/b]      {hdr.get('FK_Date', '')}   [b]Type:[/b] {hdr.get('FK_Type', '')}",
            f"[b]Status:[/b]    {hdr.get('Status', '')}",
            f"[b]Reason:[/b]    {hdr.get('Reason', '')}",
        ]
        if hdr.get("Notes"):
            info.append(f"[b]Notes:[/b]     {hdr['Notes']}")
        self.query_one("#fk-header", Static).update("\n".join(info))

        tbl = self.query_one("#items-tbl", DataTable)
        tbl.clear()
        items = fkdata.fetch_items(self.fk_id)
        total = 0.0
        for it in items:
            lc = it["LineCorrection"]
            total += lc
            tbl.add_row(
                str(it["ProductID"]), it["ProductName"],
                str(it["OrigQuantity"]), str(it["CorrQuantity"]),
                f"{sym}{it['OrigUnitPrice']:.2f}", f"{sym}{it['CorrUnitPrice']:.2f}",
                f"{sym}{lc:.2f}",
            )
        self.query_one("#fk-total", Static).update(
            f"[b]Total Correction:[/b] {sym}{total:.2f}"
        )

    @on(Button.Pressed, "#btn-pdf")
    def on_pdf(self) -> None:
        try:
            import pdf_export
            path = pdf_export.export_fk(self.fk_id)
            self.notify(f"PDF saved → {path}", severity="information")
        except Exception as e:
            self.notify(f"PDF error: {e}", severity="error")

    @on(Button.Pressed, "#btn-close")
    def on_close(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class FKPanel(Widget):
    """FK (Credit Notes) list panel."""
    BINDINGS = [
        ("n", "new_record",   "New FK"),
        ("f", "focus_search", "Search"),
    ]

    _selected_pk = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Input(placeholder="Search credit notes...", id="search-box")
            yield DataTable(id="tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("+ New FK", id="btn-new", variant="success")
                yield Button("Open",     id="btn-open")
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        for label, width in [
            ("ID", 6), ("Number", 16), ("Date", 12), ("Customer", 22),
            ("Type", 18), ("Orig FV", 16), ("Correction", 12), ("Status", 8),
        ]:
            tbl.add_column(label, width=width)
        self.refresh_data()

    def refresh_data(self, term: str = "") -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        rows = fkdata.search(term) if term else fkdata.fetch_all()
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

    def _open_detail(self, fk_id: int) -> None:
        self.app.push_screen(FKDetailModal(fk_id))

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-open")
    def on_btn_open(self) -> None:
        if self._selected_pk:
            self._open_detail(int(self._selected_pk))
        else:
            self.notify("Select a credit note first.", severity="warning")

    def action_new_record(self) -> None:
        def after(fk_id):
            if fk_id:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(FKNewModal(), callback=after)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()
