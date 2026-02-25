"""screens/shippers.py — Shippers panel, detail modal, and form modal."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static
from textual import on

import data.shippers as sdata
from screens.modals import ConfirmDeleteModal


class ShipperFormModal(ModalScreen):
    def __init__(self, pk=None) -> None:
        super().__init__()
        self.pk = pk

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(
                "Add Shipper" if not self.pk else f"Edit Shipper #{self.pk}",
                classes="modal-title",
            )
            yield Label("Company Name *:")
            yield Input(id="f-company", placeholder="Company Name")
            yield Label("Phone:")
            yield Input(id="f-phone",   placeholder="Phone")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        if self.pk:
            row = sdata.get_by_pk(self.pk)
            if row:
                self.query_one("#f-company", Input).value = row.get("CompanyName") or ""
                self.query_one("#f-phone",   Input).value = row.get("Phone")       or ""

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        company = self.query_one("#f-company", Input).value.strip()
        if not company:
            self.notify("Company Name is required.", severity="error")
            return
        data = {
            "CompanyName": company,
            "Phone":       self.query_one("#f-phone", Input).value.strip(),
        }
        try:
            if self.pk is None:
                sdata.insert(data)
                self.notify(f"Shipper '{company}' added.", severity="information")
            else:
                sdata.update(self.pk, data)
                self.notify("Shipper updated.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class ShipperDetailModal(ModalScreen):
    def __init__(self, pk) -> None:
        super().__init__()
        self.pk = pk
        self._changed = False

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("", id="detail-title", classes="modal-title")
            yield Static("", id="detail-content")
            with Horizontal(classes="modal-buttons"):
                yield Button("Edit",   id="btn-edit",   variant="primary")
                yield Button("Delete", id="btn-delete", variant="error")
                yield Button("Close",  id="btn-close")

    def on_mount(self) -> None:
        self._load()

    def _load(self) -> None:
        row = sdata.get_by_pk(self.pk)
        if not row:
            self.dismiss(self._changed)
            return
        self.query_one("#detail-title", Label).update(f"Shipper #{self.pk}: {row['CompanyName']}")
        lines = [
            f"[b]ID:[/b]           {row['ShipperID']}",
            f"[b]Company Name:[/b] {row.get('CompanyName') or ''}",
            f"[b]Phone:[/b]        {row.get('Phone') or ''}",
        ]
        self.query_one("#detail-content", Static).update("\n".join(lines))

    @on(Button.Pressed, "#btn-edit")
    def on_edit(self) -> None:
        def after(saved):
            if saved:
                self._changed = True
                self._load()
        self.app.push_screen(ShipperFormModal(pk=self.pk), callback=after)

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        row = sdata.get_by_pk(self.pk)
        name = row.get("CompanyName", str(self.pk)) if row else str(self.pk)

        def after_confirm(confirmed):
            if confirmed:
                try:
                    sdata.delete(self.pk)
                    self.dismiss(True)
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")

        self.app.push_screen(ConfirmDeleteModal(name), callback=after_confirm)

    @on(Button.Pressed, "#btn-close")
    def on_close(self) -> None:
        self.dismiss(self._changed)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(self._changed)


class ShippersPanel(Widget):
    BINDINGS = [
        ("n", "new_record",   "New Shipper"),
        ("f", "focus_search", "Search"),
        ("x", "export_csv",   "Export CSV"),
    ]

    _selected_pk = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Input(placeholder="Search shippers...", id="search-box")
            yield DataTable(id="tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("+ New",  id="btn-new",    variant="success")
                yield Button("Open",   id="btn-open")
                yield Button("Delete", id="btn-delete", variant="error")
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        for label, width in [("ID", 4), ("Company Name", 32), ("Phone", 22)]:
            tbl.add_column(label, width=width)
        self.refresh_data()

    def refresh_data(self, term: str = "") -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        rows = sdata.search(term) if term else sdata.fetch_all()
        for row in rows:
            tbl.add_row(*[str(c) if c is not None else "" for c in row],
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
            self._open_detail(event.row_key.value)

    def _open_detail(self, pk) -> None:
        def after(changed):
            if changed:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(ShipperDetailModal(pk=pk), callback=after)

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-open")
    def on_btn_open(self) -> None:
        if self._selected_pk:
            self._open_detail(self._selected_pk)
        else:
            self.notify("Select a shipper first.", severity="warning")

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        if not self._selected_pk:
            self.notify("Select a shipper first.", severity="warning")
            return
        row = sdata.get_by_pk(self._selected_pk)
        name = row.get("CompanyName", str(self._selected_pk)) if row else str(self._selected_pk)

        def after_confirm(confirmed):
            if confirmed:
                try:
                    sdata.delete(self._selected_pk)
                    self._selected_pk = None
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify("Shipper deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")

        self.app.push_screen(ConfirmDeleteModal(name), callback=after_confirm)

    def action_new_record(self) -> None:
        def after(saved):
            if saved:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(ShipperFormModal(pk=None), callback=after)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()

    def action_export_csv(self) -> None:
        import csv, os
        from datetime import datetime
        term = self.query_one("#search-box", Input).value
        rows = sdata.search(term) if term else sdata.fetch_all()
        headers = ["ID", "Company Name", "Phone"]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.expanduser(f"~/Downloads/northwind_shippers_{ts}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([str(c) if c is not None else "" for c in row])
        self.notify(f"Exported {len(rows)} rows → {path}", severity="information")
