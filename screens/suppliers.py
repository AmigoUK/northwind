"""screens/suppliers.py — Suppliers panel, detail modal, and form modal."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static
from textual import on

import data.suppliers as sdata
from screens.modals import ConfirmDeleteModal


class SupplierFormModal(ModalScreen):
    def __init__(self, pk=None) -> None:
        super().__init__()
        self.pk = pk

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(
                "Add Supplier" if not self.pk else f"Edit Supplier #{self.pk}",
                classes="modal-title",
            )
            yield Label("Company Name *:")
            yield Input(id="f-company", placeholder="Company Name")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Contact Name:")
                    yield Input(id="f-contact", placeholder="Contact Name")
                with Vertical(classes="form-field"):
                    yield Label("Contact Title:")
                    yield Input(id="f-ctitle", placeholder="Contact Title")
            yield Label("Address:")
            yield Input(id="f-address", placeholder="Address")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("City:")
                    yield Input(id="f-city", placeholder="City")
                with Vertical(classes="form-field"):
                    yield Label("Region:")
                    yield Input(id="f-region", placeholder="Region")
                with Vertical(classes="form-field"):
                    yield Label("Postal Code:")
                    yield Input(id="f-postal", placeholder="Postal Code")
            with Horizontal(classes="form-row"):
                with Vertical(classes="form-field"):
                    yield Label("Country:")
                    yield Input(id="f-country", placeholder="Country")
                with Vertical(classes="form-field"):
                    yield Label("Phone:")
                    yield Input(id="f-phone", placeholder="Phone")
                with Vertical(classes="form-field"):
                    yield Label("Fax:")
                    yield Input(id="f-fax", placeholder="Fax")
            yield Label("Home Page:")
            yield Input(id="f-homepage", placeholder="Home Page URL")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        if self.pk:
            row = sdata.get_by_pk(self.pk)
            if row:
                self.query_one("#f-company",  Input).value = row.get("CompanyName")  or ""
                self.query_one("#f-contact",  Input).value = row.get("ContactName")  or ""
                self.query_one("#f-ctitle",   Input).value = row.get("ContactTitle") or ""
                self.query_one("#f-address",  Input).value = row.get("Address")      or ""
                self.query_one("#f-city",     Input).value = row.get("City")         or ""
                self.query_one("#f-region",   Input).value = row.get("Region")       or ""
                self.query_one("#f-postal",   Input).value = row.get("PostalCode")   or ""
                self.query_one("#f-country",  Input).value = row.get("Country")      or ""
                self.query_one("#f-phone",    Input).value = row.get("Phone")        or ""
                self.query_one("#f-fax",      Input).value = row.get("Fax")          or ""
                self.query_one("#f-homepage", Input).value = row.get("HomePage")     or ""

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        company = self.query_one("#f-company", Input).value.strip()
        if not company:
            self.notify("Company Name is required.", severity="error")
            return
        data = {
            "CompanyName":  company,
            "ContactName":  self.query_one("#f-contact",  Input).value.strip(),
            "ContactTitle": self.query_one("#f-ctitle",   Input).value.strip(),
            "Address":      self.query_one("#f-address",  Input).value.strip(),
            "City":         self.query_one("#f-city",     Input).value.strip(),
            "Region":       self.query_one("#f-region",   Input).value.strip(),
            "PostalCode":   self.query_one("#f-postal",   Input).value.strip(),
            "Country":      self.query_one("#f-country",  Input).value.strip(),
            "Phone":        self.query_one("#f-phone",    Input).value.strip(),
            "Fax":          self.query_one("#f-fax",      Input).value.strip(),
            "HomePage":     self.query_one("#f-homepage", Input).value.strip(),
        }
        try:
            if self.pk is None:
                sdata.insert(data)
                self.notify(f"Supplier '{company}' added.", severity="information")
            else:
                sdata.update(self.pk, data)
                self.notify("Supplier updated.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class SupplierDetailModal(ModalScreen):
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
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        self._load()

    def _load(self) -> None:
        row = sdata.get_by_pk(self.pk)
        if not row:
            self.dismiss(self._changed)
            return
        self.query_one("#detail-title", Label).update(f"Supplier #{self.pk}: {row['CompanyName']}")
        lines = [
            f"[b]ID:[/b]            {row['SupplierID']}",
            f"[b]Company:[/b]       {row.get('CompanyName') or ''}",
            f"[b]Contact:[/b]       {row.get('ContactName') or ''}",
            f"[b]Title:[/b]         {row.get('ContactTitle') or ''}",
            f"[b]Address:[/b]       {row.get('Address') or ''}",
            f"[b]City:[/b]          {row.get('City') or ''}",
            f"[b]Region:[/b]        {row.get('Region') or ''}",
            f"[b]Postal Code:[/b]   {row.get('PostalCode') or ''}",
            f"[b]Country:[/b]       {row.get('Country') or ''}",
            f"[b]Phone:[/b]         {row.get('Phone') or ''}",
            f"[b]Fax:[/b]           {row.get('Fax') or ''}",
            f"[b]Home Page:[/b]     {row.get('HomePage') or ''}",
        ]
        self.query_one("#detail-content", Static).update("\n".join(lines))

    @on(Button.Pressed, "#btn-edit")
    def on_edit(self) -> None:
        def after(saved):
            if saved:
                self._changed = True
                self._load()
        self.app.push_screen(SupplierFormModal(pk=self.pk), callback=after)

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


class SuppliersPanel(Widget):
    BINDINGS = [
        ("n", "new_record",     "New Supplier"),
        ("f", "focus_search",   "Search"),
        ("+", "new_product",    "New Product"),
        ("x", "export_csv",     "Export CSV"),
    ]

    _selected_pk = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Input(placeholder="Search suppliers...", id="search-box")
            yield DataTable(id="tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("+ New",  id="btn-new",    variant="success")
                yield Button("Open",   id="btn-open")
                yield Button("Delete", id="btn-delete", variant="error")
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        for label, width in [
            ("ID", 4), ("Company", 25), ("Contact", 18),
            ("City", 14), ("Country", 10), ("Phone", 16),
        ]:
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
        self.app.push_screen(SupplierDetailModal(pk=pk), callback=after)

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-open")
    def on_btn_open(self) -> None:
        if self._selected_pk:
            self._open_detail(self._selected_pk)
        else:
            self.notify("Select a supplier first.", severity="warning")

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        if not self._selected_pk:
            self.notify("Select a supplier first.", severity="warning")
            return
        row = sdata.get_by_pk(self._selected_pk)
        name = row.get("CompanyName", str(self._selected_pk)) if row else str(self._selected_pk)

        def after_confirm(confirmed):
            if confirmed:
                try:
                    sdata.delete(self._selected_pk)
                    self._selected_pk = None
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify("Supplier deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")

        self.app.push_screen(ConfirmDeleteModal(name), callback=after_confirm)

    def action_new_record(self) -> None:
        def after(saved):
            if saved:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(SupplierFormModal(pk=None), callback=after)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()

    def action_export_csv(self) -> None:
        import csv, os
        from datetime import datetime
        term = self.query_one("#search-box", Input).value
        rows = sdata.search(term) if term else sdata.fetch_all()
        headers = ["ID", "Company", "Contact", "City", "Country", "Phone"]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.expanduser(f"~/Downloads/northwind_suppliers_{ts}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([str(c) if c is not None else "" for c in row])
        self.notify(f"Exported {len(rows)} rows → {path}", severity="information")

    def action_new_product(self) -> None:
        if not self._selected_pk:
            self.notify("Select a supplier first.", severity="warning")
            return
        from screens.products import ProductFormModal
        from textual.widgets import ContentSwitcher

        def after(saved):
            if saved:
                try:
                    self.app.query_one(ContentSwitcher).current = "products"
                    self.app.query_one("#products").refresh_data()
                except Exception:
                    pass

        self.app.push_screen(
            ProductFormModal(pk=None, supplier_id=int(self._selected_pk)), callback=after
        )
