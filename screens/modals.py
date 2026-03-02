"""screens/modals.py — Shared modal dialogs: ConfirmActionModal, ConfirmDeleteModal, CleanDatabaseModal, PickerModal, ImportCSVModal, FileSelectModal."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, DirectoryTree, Input, Label, Static
from textual import on


class ConfirmActionModal(ModalScreen[bool]):
    """Generic confirmation dialog with custom title and button label."""

    def __init__(self, title: str, message: str = "", confirm_label: str = "Confirm") -> None:
        super().__init__()
        self._title = title
        self._message = message
        self._confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        with Vertical(classes="confirm-dialog"):
            yield Label(self._title, classes="modal-title")
            if self._message:
                yield Label(self._message, classes="modal-subtitle")
            with Horizontal(classes="modal-buttons"):
                yield Button(self._confirm_label, id="btn-yes", variant="primary")
                yield Button("Cancel", id="btn-no")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#btn-no").focus()

    def on_key(self, event) -> None:
        if event.key == "y":
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            self.dismiss(False)

    @on(Button.Pressed, "#btn-yes")
    def on_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-no")
    def on_no(self) -> None:
        self.dismiss(False)


class ConfirmDeleteModal(ModalScreen[bool]):
    """Ask the user to confirm deletion. Returns True if confirmed."""

    def __init__(self, name: str, details: str = "") -> None:
        super().__init__()
        self._name = name
        self._details = details

    def compose(self) -> ComposeResult:
        with Vertical(classes="confirm-dialog"):
            yield Label(f"Delete '{self._name}'?", classes="modal-title")
            if self._details:
                yield Label(self._details, classes="modal-subtitle")
            yield Label("This action cannot be undone.", classes="modal-subtitle")
            with Horizontal(classes="modal-buttons"):
                yield Button("Delete", id="btn-yes", variant="error")
                yield Button("Cancel", id="btn-no", variant="primary")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#btn-no").focus()

    def on_key(self, event) -> None:
        if event.key == "y":
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            self.dismiss(False)

    @on(Button.Pressed, "#btn-yes")
    def on_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-no")
    def on_no(self) -> None:
        self.dismiss(False)


class QuitConfirmModal(ModalScreen[bool]):
    """Ask the user to confirm quitting the app. Returns True if confirmed."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="confirm-dialog"):
            yield Label("Quit Northwind Traders?", classes="modal-title")
            yield Label("Press Y to quit or N / ESC to cancel.", classes="modal-subtitle")
            with Horizontal(classes="modal-buttons"):
                yield Button("Quit", id="btn-yes", variant="error")
                yield Button("Cancel", id="btn-no", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#btn-no").focus()  # safe default: Cancel focused

    def on_key(self, event) -> None:
        if event.key == "y":
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            self.dismiss(False)

    @on(Button.Pressed, "#btn-yes")
    def on_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-no")
    def on_no(self) -> None:
        self.dismiss(False)


class CancellationReasonModal(ModalScreen):
    """Ask for a mandatory cancellation reason. Returns reason string or None."""

    def __init__(self, title: str, warning: str = "") -> None:
        super().__init__()
        self._title = title
        self._warning = warning

    def compose(self) -> ComposeResult:
        with Vertical(classes="confirm-dialog"):
            yield Label(self._title, classes="modal-title")
            if self._warning:
                yield Label(self._warning, classes="modal-subtitle")
            yield Label("Reason (required):")
            yield Input(placeholder="Cancellation reason...", id="f-reason")
            with Horizontal(classes="modal-buttons"):
                yield Button("Confirm Cancel", id="btn-yes", variant="warning")
                yield Button("Back", id="btn-no", variant="primary")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#f-reason", Input).focus()

    @on(Button.Pressed, "#btn-yes")
    def on_yes(self) -> None:
        reason = self.query_one("#f-reason", Input).value.strip()
        if not reason:
            self.notify("Reason is required.", severity="error")
            return
        self.dismiss(reason)

    @on(Button.Pressed, "#btn-no")
    def on_no(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class CleanDatabaseModal(ModalScreen[bool]):
    """PIN-protected confirmation for cleaning the entire database."""

    MAX_ATTEMPTS = 3

    def __init__(self) -> None:
        super().__init__()
        self._attempts = 0

    def compose(self) -> ComposeResult:
        with Vertical(classes="confirm-dialog"):
            yield Label("Clean Database", classes="modal-title")
            yield Label(
                "This will DELETE all data (master + transactional) "
                "and enter production mode. This cannot be undone.",
                classes="modal-subtitle",
            )
            yield Label("Enter admin PIN to confirm:")
            yield Input(
                placeholder="PIN", id="f-admin-pin",
                password=True, max_length=4,
            )
            yield Label("", id="pin-error")
            with Horizontal(classes="modal-buttons"):
                yield Button("Clean", id="btn-yes", variant="error")
                yield Button("Cancel", id="btn-no", variant="primary")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#f-admin-pin", Input).focus()

    def _validate_and_dismiss(self) -> None:
        from data.users import verify_admin_pin
        pin = self.query_one("#f-admin-pin", Input).value.strip()
        if not pin:
            self.query_one("#pin-error", Label).update("PIN is required.")
            return
        if not verify_admin_pin(pin):
            self._attempts += 1
            remaining = self.MAX_ATTEMPTS - self._attempts
            if remaining <= 0:
                self.query_one("#pin-error", Label).update(
                    "Too many failed attempts. Closing."
                )
                self.set_timer(1.5, lambda: self.dismiss(False))
                self.query_one("#btn-yes", Button).disabled = True
                self.query_one("#f-admin-pin", Input).disabled = True
                return
            self.query_one("#pin-error", Label).update(
                f"Invalid PIN. {remaining} attempt{'s' if remaining != 1 else ''} remaining."
            )
            self.query_one("#f-admin-pin", Input).value = ""
            self.query_one("#f-admin-pin", Input).focus()
            return
        self.dismiss(True)

    @on(Button.Pressed, "#btn-yes")
    def on_yes(self) -> None:
        self._validate_and_dismiss()

    @on(Button.Pressed, "#btn-no")
    def on_no(self) -> None:
        self.dismiss(False)

    @on(Input.Submitted, "#f-admin-pin")
    def on_pin_submitted(self) -> None:
        self._validate_and_dismiss()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class PickerModal(ModalScreen):
    """Reusable record picker. Returns the selected pk string or None."""

    def __init__(
        self,
        title: str,
        headers: list[tuple[str, int]],
        rows: list[list],
        pk_col: int = 0,
    ) -> None:
        super().__init__()
        self._title = title
        self._headers = headers
        self._all_rows = rows
        self._pk_col = pk_col

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(self._title, classes="modal-title")
            yield Input(placeholder="Filter...", id="picker-filter")
            yield DataTable(id="picker-tbl", cursor_type="row", zebra_stripes=True)
            with Horizontal(classes="modal-buttons"):
                yield Button("Select", id="btn-select", variant="primary")
                yield Button("Cancel", id="btn-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        tbl = self.query_one("#picker-tbl", DataTable)
        for label, width in self._headers:
            tbl.add_column(label, width=width)
        self._populate(self._all_rows)

    def _populate(self, rows: list) -> None:
        tbl = self.query_one("#picker-tbl", DataTable)
        tbl.clear()
        for row in rows:
            tbl.add_row(*[str(c) if c is not None else "" for c in row],
                        key=str(row[self._pk_col]))

    @on(Input.Changed, "#picker-filter")
    def on_filter(self, event: Input.Changed) -> None:
        term = event.value.lower()
        if term:
            filtered = [r for r in self._all_rows
                        if any(term in str(c).lower() for c in r)]
        else:
            filtered = self._all_rows
        self._populate(filtered)

    @on(DataTable.RowSelected, "#picker-tbl")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key:
            self.dismiss(event.row_key.value)

    @on(Button.Pressed, "#btn-select")
    def on_select(self) -> None:
        tbl = self.query_one("#picker-tbl", DataTable)
        if tbl.row_count == 0:
            self.dismiss(None)
            return
        try:
            pk = tbl.coordinate_to_cell_key(tbl.cursor_coordinate).row_key.value
            self.dismiss(pk)
        except Exception:
            self.dismiss(None)

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class ImportCSVModal(ModalScreen):
    """Import master data from a CSV file. Returns summary dict or None."""

    def __init__(self, table: str) -> None:
        super().__init__()
        self._table = table
        self._rows: list[dict] = []

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label(f"Import {self._table} from CSV", classes="modal-title")
            yield Label("File path:")
            yield Input(placeholder="~/Downloads/data.csv", id="f-path")
            with Horizontal(classes="modal-buttons"):
                yield Button("Browse...", id="btn-browse-csv")
                yield Button("Preview", id="btn-preview", variant="primary")
                yield Button("Cancel", id="btn-cancel-import")
            yield Static("", id="import-status", classes="import-status")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#f-path", Input).focus()

    @on(Button.Pressed, "#btn-browse-csv")
    def on_browse(self) -> None:
        def after(path):
            if path:
                self.query_one("#f-path", Input).value = path
        self.app.push_screen(
            FileSelectModal(title="Select CSV File", mode="open",
                default_path="~/Downloads", file_filter=".csv"),
            callback=after,
        )

    @on(Input.Submitted, "#f-path")
    def on_path_submitted(self) -> None:
        self._do_preview()

    @on(Button.Pressed, "#btn-preview")
    def on_preview(self) -> None:
        btn = self.query_one("#btn-preview", Button)
        if btn.label.plain.startswith("Import"):
            self._do_import()
        else:
            self._do_preview()

    def _do_preview(self) -> None:
        from data.csv_import import parse_csv, TABLE_CONFIGS

        path = self.query_one("#f-path", Input).value.strip()
        if not path:
            self._set_status("[b red]Please enter a file path.[/]")
            return

        rows, errors = parse_csv(path, self._table)
        cfg = TABLE_CONFIGS[self._table]

        if errors and not rows:
            self._set_status("\n".join(f"[b red]{e}[/]" for e in errors))
            return

        self._rows = rows
        lines: list[str] = []
        if errors:
            lines.extend(f"[yellow]{e}[/]" for e in errors)

        mapped_cols = set()
        for row in rows[:1]:
            mapped_cols = set(row.keys())
        lines.append(f"[b]Columns:[/] {', '.join(c for c in cfg['columns'] if c in mapped_cols)}")
        lines.append(f"[b]Rows:[/] {len(rows)}")

        lines.append("")
        for i, row in enumerate(rows[:3], start=1):
            vals = [f"{k}={v}" for k, v in row.items() if v is not None]
            lines.append(f"  {i}. {', '.join(vals[:4])}{'...' if len(vals) > 4 else ''}")
        if len(rows) > 3:
            lines.append(f"  ... and {len(rows) - 3} more rows")

        self._set_status("\n".join(lines))

        btn = self.query_one("#btn-preview", Button)
        btn.label = f"Import {len(rows)} rows"
        btn.variant = "success"

    def _do_import(self) -> None:
        from data.csv_import import import_rows

        if not self._rows:
            self._set_status("[b red]No rows to import. Preview first.[/]")
            return

        result = import_rows(self._table, self._rows)
        parts = [f"[b green]Inserted: {result['inserted']}[/]"]
        if result["skipped"]:
            parts.append(f"[b yellow]Skipped (duplicates): {result['skipped']}[/]")
        if result["errors"]:
            parts.append(f"[b red]Errors: {len(result['errors'])}[/]")
            for row_num, msg in result["errors"][:5]:
                parts.append(f"  Row {row_num}: {msg}")

        self._set_status("\n".join(parts))

        btn = self.query_one("#btn-preview", Button)
        btn.label = "Preview"
        btn.variant = "primary"
        self._rows = []

        self.dismiss(result)

    def _set_status(self, text: str) -> None:
        self.query_one("#import-status", Static).update(text)

    @on(Button.Pressed, "#btn-cancel-import")
    def on_cancel_import(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class _FilteredDirectoryTree(DirectoryTree):
    """DirectoryTree that filters files by extension."""

    def __init__(self, path: str, file_filter: str = "") -> None:
        super().__init__(path)
        self._file_filter = file_filter.lower()

    def filter_paths(self, paths):
        if not self._file_filter:
            return paths
        result = []
        for p in paths:
            if p.is_dir() or p.suffix.lower() == self._file_filter:
                result.append(p)
        return result


class FileSelectModal(ModalScreen[Optional[str]]):
    """File browser modal for open/save operations. Returns chosen path or None."""

    def __init__(
        self,
        title: str = "Select File",
        mode: str = "save",
        default_path: str = "~/Downloads",
        suggested_name: str = "",
        file_filter: str = "",
    ) -> None:
        super().__init__()
        self._title = title
        self._mode = mode  # "open" | "save"
        self._default_path = os.path.expanduser(default_path)
        self._suggested_name = suggested_name
        self._file_filter = file_filter

    def compose(self) -> ComposeResult:
        initial = self._default_path
        if self._mode == "save" and self._suggested_name:
            initial = os.path.join(self._default_path, self._suggested_name)

        action_label = "Save" if self._mode == "save" else "Open"
        tree_root = str(Path.home())

        with Vertical(classes="modal-dialog"):
            yield Label(self._title, classes="modal-title")
            yield Label("Path:")
            yield Input(value=initial, id="f-file-path")
            yield Label("Browse:")
            yield _FilteredDirectoryTree(tree_root, file_filter=self._file_filter)
            with Horizontal(classes="modal-buttons"):
                yield Button(action_label, id="btn-file-ok", variant="primary")
                yield Button("Cancel", id="btn-file-cancel")
            yield Label("ESC to close", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#f-file-path", Input).focus()

    @on(DirectoryTree.FileSelected)
    def on_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.query_one("#f-file-path", Input).value = str(event.path)

    @on(DirectoryTree.DirectorySelected)
    def on_dir_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        if self._mode == "save" and self._suggested_name:
            self.query_one("#f-file-path", Input).value = os.path.join(
                str(event.path), self._suggested_name
            )
        else:
            self.query_one("#f-file-path", Input).value = str(event.path)

    @on(Input.Submitted, "#f-file-path")
    def on_path_submitted(self) -> None:
        self._accept()

    @on(Button.Pressed, "#btn-file-ok")
    def on_ok(self) -> None:
        self._accept()

    @on(Button.Pressed, "#btn-file-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

    def _accept(self) -> None:
        path = self.query_one("#f-file-path", Input).value.strip()
        if not path:
            self.notify("Please enter a file path.", severity="error")
            return
        path = os.path.expanduser(path)
        if self._mode == "open":
            if not os.path.isfile(path):
                self.notify("File not found.", severity="error")
                return
        else:
            parent = os.path.dirname(path)
            if parent and not os.path.isdir(parent):
                self.notify("Directory does not exist.", severity="error")
                return
        self.dismiss(path)
