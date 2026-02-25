"""screens/regions.py — Regions and Territories panel using TabbedContent."""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static, TabbedContent, TabPane
from textual import on

import data.regions as rdata
from screens.modals import ConfirmDeleteModal, PickerModal


class RegionFormModal(ModalScreen):
    def __init__(self, pk=None) -> None:
        super().__init__()
        self.pk = pk

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(
                "Add Region" if not self.pk else f"Edit Region #{self.pk}",
                classes="modal-title",
            )
            yield Label("Region Description *:")
            yield Input(id="f-desc", placeholder="Description")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        if self.pk:
            row = rdata.get_by_pk(self.pk)
            if row:
                self.query_one("#f-desc", Input).value = row.get("RegionDescription") or ""

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        desc = self.query_one("#f-desc", Input).value.strip()
        if not desc:
            self.notify("Description is required.", severity="error")
            return
        try:
            if self.pk is None:
                rdata.insert({"RegionDescription": desc})
                self.notify(f"Region '{desc}' added.", severity="information")
            else:
                rdata.update(self.pk, {"RegionDescription": desc})
                self.notify("Region updated.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class RegionDetailModal(ModalScreen):
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
        from db import get_connection
        conn = get_connection()
        row = conn.execute("SELECT * FROM Region WHERE RegionID=?", (self.pk,)).fetchone()
        territories = conn.execute(
            "SELECT TerritoryDescription FROM Territories WHERE RegionID=? ORDER BY TerritoryID",
            (self.pk,),
        ).fetchall()
        conn.close()
        if not row:
            self.dismiss(self._changed)
            return
        self.query_one("#detail-title", Label).update(f"Region #{self.pk}: {row['RegionDescription']}")
        terr_str = ", ".join(t["TerritoryDescription"] for t in territories) or "(none)"
        lines = [
            f"[b]ID:[/b]          {row['RegionID']}",
            f"[b]Description:[/b] {row.get('RegionDescription') or ''}",
            f"[b]Territories:[/b] {terr_str}",
        ]
        self.query_one("#detail-content", Static).update("\n".join(lines))

    @on(Button.Pressed, "#btn-edit")
    def on_edit(self) -> None:
        def after(saved):
            if saved:
                self._changed = True
                self._load()
        self.app.push_screen(RegionFormModal(pk=self.pk), callback=after)

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        row = rdata.get_by_pk(self.pk)
        name = row.get("RegionDescription", str(self.pk)) if row else str(self.pk)

        def after_confirm(confirmed):
            if confirmed:
                try:
                    rdata.delete(self.pk)
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


class TerritoryFormModal(ModalScreen):
    def __init__(self, pk=None, region_id=None) -> None:
        super().__init__()
        self.pk = pk
        self._region_id = region_id

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(
                "Add Territory" if not self.pk else f"Edit Territory '{self.pk}'",
                classes="modal-title",
            )
            if not self.pk:
                yield Label("Territory ID:")
                yield Input(id="f-id", placeholder="e.g. 01581")
            yield Label("Territory Description *:")
            yield Input(id="f-desc", placeholder="Description")
            yield Label("Region:")
            with Horizontal():
                yield Label("(none)", id="lbl-region")
                yield Button("Pick Region", id="btn-pick-region")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        if self._region_id:
            row = rdata.get_by_pk(self._region_id)
            if row:
                self.query_one("#lbl-region", Label).update(row["RegionDescription"])
        if self.pk:
            row = rdata.get_territory_by_pk(self.pk)
            if row:
                self.query_one("#f-desc", Input).value = row.get("TerritoryDescription") or ""
                self._region_id = row.get("RegionID")
                if row.get("RegionDescription"):
                    self.query_one("#lbl-region", Label).update(row["RegionDescription"])

    @on(Button.Pressed, "#btn-pick-region")
    def on_pick_region(self) -> None:
        rows = rdata.fetch_for_picker()
        def after(pk):
            if pk:
                self._region_id = int(pk)
                row = rdata.get_by_pk(int(pk))
                if row:
                    self.query_one("#lbl-region", Label).update(row["RegionDescription"])
        self.app.push_screen(
            PickerModal("Select Region", [("ID", 4), ("Description", 30)], rows),
            callback=after,
        )

    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        desc = self.query_one("#f-desc", Input).value.strip()
        if not desc:
            self.notify("Description is required.", severity="error")
            return
        if not self._region_id:
            self.notify("Region is required.", severity="error")
            return
        try:
            if self.pk is None:
                tid = self.query_one("#f-id", Input).value.strip()
                if not tid:
                    self.notify("Territory ID is required.", severity="error")
                    return
                rdata.insert_territory({
                    "TerritoryID":          tid,
                    "TerritoryDescription": desc,
                    "RegionID":             self._region_id,
                })
                self.notify(f"Territory '{desc}' added.", severity="information")
            else:
                rdata.update_territory(self.pk, {
                    "TerritoryDescription": desc,
                    "RegionID":             self._region_id,
                })
                self.notify("Territory updated.", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class TerritoryDetailModal(ModalScreen):
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
        row = rdata.get_territory_by_pk(self.pk)
        if not row:
            self.dismiss(self._changed)
            return
        self.query_one("#detail-title", Label).update(f"Territory: {row['TerritoryDescription']}")
        lines = [
            f"[b]Territory ID:[/b]  {row['TerritoryID']}",
            f"[b]Description:[/b]   {row.get('TerritoryDescription') or ''}",
            f"[b]Region:[/b]        #{row.get('RegionID', '')} {row.get('RegionDescription') or ''}",
        ]
        self.query_one("#detail-content", Static).update("\n".join(lines))

    @on(Button.Pressed, "#btn-edit")
    def on_edit(self) -> None:
        def after(saved):
            if saved:
                self._changed = True
                self._load()
        self.app.push_screen(TerritoryFormModal(pk=self.pk), callback=after)

    @on(Button.Pressed, "#btn-delete")
    def on_delete(self) -> None:
        row = rdata.get_territory_by_pk(self.pk)
        name = row.get("TerritoryDescription", self.pk) if row else self.pk

        def after_confirm(confirmed):
            if confirmed:
                try:
                    rdata.delete_territory(self.pk)
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


class RegionsPanel(Widget):
    BINDINGS = [
        ("n", "new_record",   "New"),
        ("f", "focus_search", "Search"),
        ("x", "export_csv",   "Export CSV"),
    ]

    _selected_region_pk  = None
    _selected_terr_pk    = None

    def compose(self) -> ComposeResult:
        with TabbedContent(id="regions-tabs"):
            with TabPane("Regions", id="tab-regions"):
                with Vertical(classes="panel-container"):
                    yield Input(placeholder="Search regions...", id="regions-search")
                    yield DataTable(id="regions-tbl", cursor_type="row", zebra_stripes=True)
                    with Horizontal(classes="toolbar"):
                        yield Button("+ New",  id="btn-region-new",    variant="success")
                        yield Button("Open",   id="btn-region-open")
                        yield Button("Delete", id="btn-region-delete",  variant="error")
                        yield Label("", id="regions-count-label", classes="count-label")
            with TabPane("Territories", id="tab-territories"):
                with Vertical(classes="panel-container"):
                    yield Input(placeholder="Search territories...", id="territories-search")
                    yield DataTable(id="territories-tbl", cursor_type="row", zebra_stripes=True)
                    with Horizontal(classes="toolbar"):
                        yield Button("+ New",  id="btn-terr-new",    variant="success")
                        yield Button("Open",   id="btn-terr-open")
                        yield Button("Delete", id="btn-terr-delete",  variant="error")
                        yield Label("", id="terr-count-label", classes="count-label")

    def on_mount(self) -> None:
        reg_tbl = self.query_one("#regions-tbl", DataTable)
        for label, width in [("ID", 4), ("Region Description", 35)]:
            reg_tbl.add_column(label, width=width)

        terr_tbl = self.query_one("#territories-tbl", DataTable)
        for label, width in [("Territory ID", 12), ("Description", 25), ("Region", 18)]:
            terr_tbl.add_column(label, width=width)

        self.refresh_regions()
        self.refresh_territories()

    def refresh_regions(self, term: str = "") -> None:
        tbl = self.query_one("#regions-tbl", DataTable)
        tbl.clear()
        rows = rdata.search(term) if term else rdata.fetch_all()
        for row in rows:
            tbl.add_row(*[str(c) if c is not None else "" for c in row], key=str(row[0]))
        try:
            self.query_one("#regions-count-label", Label).update(f"{len(rows)} records")
        except Exception:
            pass

    def refresh_territories(self, term: str = "") -> None:
        tbl = self.query_one("#territories-tbl", DataTable)
        tbl.clear()
        rows = rdata.search_territories(term) if term else rdata.fetch_territories()
        for row in rows:
            tbl.add_row(*[str(c) if c is not None else "" for c in row], key=str(row[0]))
        try:
            self.query_one("#terr-count-label", Label).update(f"{len(rows)} records")
        except Exception:
            pass

    @on(Input.Changed, "#regions-search")
    def on_regions_search(self, event: Input.Changed) -> None:
        self.refresh_regions(event.value)

    @on(Input.Changed, "#territories-search")
    def on_territories_search(self, event: Input.Changed) -> None:
        self.refresh_territories(event.value)

    @on(DataTable.RowHighlighted, "#regions-tbl")
    def on_region_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._selected_region_pk = event.row_key.value

    @on(DataTable.RowSelected, "#regions-tbl")
    def on_region_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key:
            self._open_region(event.row_key.value)

    @on(DataTable.RowHighlighted, "#territories-tbl")
    def on_terr_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._selected_terr_pk = event.row_key.value

    @on(DataTable.RowSelected, "#territories-tbl")
    def on_terr_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key:
            self._open_territory(event.row_key.value)

    def _open_region(self, pk) -> None:
        def after(changed):
            if changed:
                self.refresh_regions()
        self.app.push_screen(RegionDetailModal(pk=int(pk)), callback=after)

    def _open_territory(self, pk) -> None:
        def after(changed):
            if changed:
                self.refresh_territories()
        self.app.push_screen(TerritoryDetailModal(pk=pk), callback=after)

    # Region buttons
    @on(Button.Pressed, "#btn-region-new")
    def on_btn_region_new(self) -> None:
        def after(saved):
            if saved:
                self.refresh_regions()
        self.app.push_screen(RegionFormModal(pk=None), callback=after)

    @on(Button.Pressed, "#btn-region-open")
    def on_btn_region_open(self) -> None:
        if self._selected_region_pk:
            self._open_region(self._selected_region_pk)
        else:
            self.notify("Select a region first.", severity="warning")

    @on(Button.Pressed, "#btn-region-delete")
    def on_btn_region_delete(self) -> None:
        if not self._selected_region_pk:
            self.notify("Select a region first.", severity="warning")
            return
        row = rdata.get_by_pk(int(self._selected_region_pk))
        name = row.get("RegionDescription", str(self._selected_region_pk)) if row else str(self._selected_region_pk)

        def after_confirm(confirmed):
            if confirmed:
                try:
                    rdata.delete(int(self._selected_region_pk))
                    self._selected_region_pk = None
                    self.refresh_regions()
                    self.notify("Region deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")

        self.app.push_screen(ConfirmDeleteModal(name), callback=after_confirm)

    # Territory buttons
    @on(Button.Pressed, "#btn-terr-new")
    def on_btn_terr_new(self) -> None:
        def after(saved):
            if saved:
                self.refresh_territories()
        self.app.push_screen(TerritoryFormModal(pk=None), callback=after)

    @on(Button.Pressed, "#btn-terr-open")
    def on_btn_terr_open(self) -> None:
        if self._selected_terr_pk:
            self._open_territory(self._selected_terr_pk)
        else:
            self.notify("Select a territory first.", severity="warning")

    @on(Button.Pressed, "#btn-terr-delete")
    def on_btn_terr_delete(self) -> None:
        if not self._selected_terr_pk:
            self.notify("Select a territory first.", severity="warning")
            return
        row = rdata.get_territory_by_pk(self._selected_terr_pk)
        name = row.get("TerritoryDescription", self._selected_terr_pk) if row else self._selected_terr_pk

        def after_confirm(confirmed):
            if confirmed:
                try:
                    rdata.delete_territory(self._selected_terr_pk)
                    self._selected_terr_pk = None
                    self.refresh_territories()
                    self.notify("Territory deleted.", severity="information")
                except Exception as e:
                    self.notify(f"Cannot delete: {e}", severity="error")

        self.app.push_screen(ConfirmDeleteModal(name), callback=after_confirm)

    def action_export_csv(self) -> None:
        import csv, os
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            tabs = self.query_one(TabbedContent)
            if tabs.active == "tab-territories":
                term = self.query_one("#territories-search", Input).value
                rows = rdata.search_territories(term) if term else rdata.fetch_territories()
                headers = ["Territory ID", "Description", "Region"]
                name = "territories"
            else:
                term = self.query_one("#regions-search", Input).value
                rows = rdata.search(term) if term else rdata.fetch_all()
                headers = ["ID", "Region Description"]
                name = "regions"
        except Exception:
            rows = rdata.fetch_all()
            headers = ["ID", "Region Description"]
            name = "regions"
        path = os.path.expanduser(f"~/Downloads/northwind_{name}_{ts}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([str(c) if c is not None else "" for c in row])
        self.notify(f"Exported {len(rows)} rows → {path}", severity="information")

    def action_new_record(self) -> None:
        # Dispatch to whichever tab is active
        try:
            tabs = self.query_one(TabbedContent)
            if tabs.active == "tab-territories":
                self.on_btn_terr_new()
            else:
                self.on_btn_region_new()
        except Exception:
            self.on_btn_region_new()

    def action_focus_search(self) -> None:
        try:
            tabs = self.query_one(TabbedContent)
            if tabs.active == "tab-territories":
                self.query_one("#territories-search", Input).focus()
            else:
                self.query_one("#regions-search", Input).focus()
        except Exception:
            pass
