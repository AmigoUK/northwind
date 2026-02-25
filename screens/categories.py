"""screens/categories.py — Categories panel, detail modal, and form modal."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static
from textual import on

import data.categories as cdata
from screens.modals import ConfirmDeleteModal


class CategoryFormModal(ModalScreen):
    def __init__(self, pk=None) -> None:
        super().__init__()
        self.pk = pk

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(
                "Add Category" if not self.pk else f"Edit Category #{self.pk}",
                classes="modal-title",
            )
            yield Label("Category Name *:")
            yield Input(id="f-name", placeholder="Category Name")
            yield Label("Description:")
            yield Input(id="f-desc", placeholder="Description")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")

    def on_mount(self) -> None:
        if self.pk:
            row = cdata.get_by_pk(self.pk)
            if row:
                self.query_one("#f-name", Input).value = row.get("CategoryName") or ""
                self.query_one("#f-desc", Input).value = row.get("Description")  or ""

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        name = self.query_one("#f-name", Input).value.strip()
        if not name:
            self.notify("Category Name is required.", severity="error")
            return
        data = {
            "CategoryName": name,
            "Description":  self.query_one("#f-desc", Input).value.strip(),
        }
        try:
            if self.pk is None:
                cdata.insert(data)
                self.notify(f"Category '{name}' added.", severity="information")
            else:
                cdata.update(self.pk, data)
                self.notify("Category updated.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class CategoryDetailModal(ModalScreen):
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
        row = cdata.get_by_pk(self.pk)
        if not row:
            self.dismiss(self._changed)
            return
        self.query_one("#detail-title", Label).update(f"Category #{self.pk}: {row['CategoryName']}")
        lines = [
            f"[b]ID:[/b]          {row['CategoryID']}",
            f"[b]Name:[/b]        {row.get('CategoryName') or ''}",
            f"[b]Description:[/b] {row.get('Description') or ''}",
        ]
        self.query_one("#detail-content", Static).update("\n".join(lines))

    @on(Button.Pressed, "#btn-edit")
    def on_edit(self) -> None:
        def after(saved):
            if saved:
                self._changed = True
                self._load()
        self.app.push_screen(CategoryFormModal(pk=self.pk), callback=after)

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        row = cdata.get_by_pk(self.pk)
        name = row.get("CategoryName", str(self.pk)) if row else str(self.pk)

        def after_confirm(confirmed):
            if confirmed:
                try:
                    cdata.delete(self.pk)
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


class CategoriesPanel(Widget):
    BINDINGS = [
        ("n", "new_record",     "New Category"),
        ("f", "focus_search",   "Search"),
        ("+", "new_product",    "New Product"),
        ("x", "export_csv",     "Export CSV"),
    ]

    _selected_pk = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Input(placeholder="Search categories...", id="search-box")
            yield DataTable(id="tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="toolbar"):
                yield Button("+ New",  id="btn-new",    variant="success")
                yield Button("Open",   id="btn-open")
                yield Button("Delete", id="btn-delete", variant="error")
                yield Label("", id="count-label", classes="count-label")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        for label, width in [("ID", 4), ("Category Name", 22), ("Description", 45)]:
            tbl.add_column(label, width=width)
        self.refresh_data()

    def refresh_data(self, term: str = "") -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        rows = cdata.search(term) if term else cdata.fetch_all()
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
        self.app.push_screen(CategoryDetailModal(pk=pk), callback=after)

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_record()

    @on(Button.Pressed, "#btn-open")
    def on_btn_open(self) -> None:
        if self._selected_pk:
            self._open_detail(self._selected_pk)
        else:
            self.notify("Select a category first.", severity="warning")

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        if not self._selected_pk:
            self.notify("Select a category first.", severity="warning")
            return
        row = cdata.get_by_pk(self._selected_pk)
        name = row.get("CategoryName", str(self._selected_pk)) if row else str(self._selected_pk)

        def after_confirm(confirmed):
            if confirmed:
                try:
                    cdata.delete(self._selected_pk)
                    self._selected_pk = None
                    self.refresh_data(self.query_one("#search-box", Input).value)
                    self.notify("Category deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")

        self.app.push_screen(ConfirmDeleteModal(name), callback=after_confirm)

    def action_new_record(self) -> None:
        def after(saved):
            if saved:
                self.refresh_data(self.query_one("#search-box", Input).value)
        self.app.push_screen(CategoryFormModal(pk=None), callback=after)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()

    def action_export_csv(self) -> None:
        import csv, os
        from datetime import datetime
        term = self.query_one("#search-box", Input).value
        rows = cdata.search(term) if term else cdata.fetch_all()
        headers = ["ID", "Category Name", "Description"]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.expanduser(f"~/Downloads/northwind_categories_{ts}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([str(c) if c is not None else "" for c in row])
        self.notify(f"Exported {len(rows)} rows → {path}", severity="information")

    def action_new_product(self) -> None:
        if not self._selected_pk:
            self.notify("Select a category first.", severity="warning")
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
            ProductFormModal(pk=None, category_id=int(self._selected_pk)), callback=after
        )
