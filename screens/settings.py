"""screens/settings.py — App settings panel (currency, theme, stock, demo data).

Educational patterns:
- on_mount() to pre-populate inputs from the DB
- INSERT OR REPLACE upsert via the settings data layer
- notify() for lightweight user feedback without a modal
- ConfirmActionModal for destructive actions (demo data insert/clean)
- @work(thread=True) to run long operations without freezing the TUI
"""
import os

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Static, Switch
from textual.worker import Worker, WorkerState
from textual import on, work

import data.settings as app_settings
from data.demo import has_demo_data, insert_demo_data, clean_demo_data, demo_status
from screens.modals import ConfirmActionModal, CleanDatabaseModal, TestModeWarningModal

# Document keys to show in the notification (excludes metadata like elapsed_seconds)
_DOC_KEYS = {"DN", "INV", "GR", "CN", "SI", "SO", "CR", "CP", "BankEntry"}


class SettingsPanel(Widget):
    _mode_switching: bool = False

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Label("Settings", classes="panel-title")
            with Vertical(classes="settings-section"):
                yield Label("Currency", classes="settings-label")
                with Horizontal(classes="form-row"):
                    with Vertical(classes="form-field"):
                        yield Label("Symbol (e.g. $, £, €, zl)")
                        yield Input(placeholder="$", id="f-currency-symbol")
                    with Vertical(classes="form-field"):
                        yield Label("Name (e.g. USD, GBP, PLN)")
                        yield Input(placeholder="USD", id="f-currency-name")
            with Vertical(classes="settings-section"):
                yield Label("Appearance", classes="settings-label")
                yield Label("Theme (also changeable via Ctrl+P)")
                yield Select([], id="f-theme", allow_blank=True)
            with Vertical(classes="settings-section"):
                yield Label("Stock Control", classes="settings-label")
                with Horizontal(classes="setting-row"):
                    yield Label("Allow Backorders")
                    yield Switch(id="f-backorder", value=False)
                with Horizontal(classes="setting-row"):
                    yield Label("Show Discontinued Products")
                    yield Switch(id="f-show-disc", value=False)
            with Vertical(classes="settings-section"):
                yield Label("Demo Data", classes="settings-label")
                with Horizontal(classes="setting-row"):
                    yield Label("Mode")
                    yield Switch(id="f-mode", value=False)
                    yield Label("Production", id="mode-label")
                yield Static(
                    "Populate all data (master + transactional) for demos, "
                    "or clean everything for production use.",
                    id="demo-description",
                )
                yield Static("Checking...", id="demo-status")
                with Horizontal(classes="toolbar"):
                    yield Button(
                        "Insert Demo Data", id="btn-demo-insert", variant="success",
                    )
                    yield Button(
                        "Clean Database", id="btn-demo-clean", variant="error",
                    )
            with Vertical(classes="settings-section"):
                yield Label("Backup & Restore", classes="settings-label")
                yield Label("Backup Directory (blank = app folder)")
                with Horizontal(classes="logo-browse-row"):
                    yield Input(placeholder="~/backups", id="f-backup-path")
                    yield Button("Browse...", id="btn-browse-backup")
                yield Label("Restore Database", classes="settings-label")
                yield Static(
                    "Replaces the live database with a chosen backup file. "
                    "The app will exit and must be relaunched.",
                    classes="modal-subtitle",
                )
                yield Button("Restore from Backup...", id="btn-restore", variant="warning")
            yield Button("Save Settings", id="btn-save", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#f-currency-symbol", Input).value = app_settings.get_setting(
            "currency_symbol", "$"
        )
        self.query_one("#f-currency-name", Input).value = app_settings.get_setting(
            "currency_name", "USD"
        )
        theme_select = self.query_one("#f-theme", Select)
        available = [
            (name, name)
            for name in self.app.available_themes
            if name != "textual-ansi"
        ]
        theme_select.set_options(available)
        theme_select.value = app_settings.get_theme_name()
        self.query_one("#f-backorder", Switch).value = app_settings.get_backorder_allowed()
        self.query_one("#f-show-disc", Switch).value = (
            app_settings.get_setting("show_discontinued", "false").lower() == "true"
        )
        is_test = app_settings.get_setting("production_mode", "false").lower() != "true"
        self.query_one("#f-mode", Switch).value = is_test
        self.query_one("#mode-label", Label).update("Test Mode" if is_test else "Production")
        self.query_one("#f-backup-path", Input).value = app_settings.get_backup_path()
        self._refresh_demo_status()

    def _refresh_demo_status(self) -> None:
        status = self.query_one("#demo-status", Static)
        status.update(f"Status: {demo_status()}")
        demo_exists = has_demo_data()
        self.query_one("#btn-demo-insert", Button).disabled = demo_exists
        self.query_one("#btn-demo-clean", Button).disabled = not demo_exists
        is_test = app_settings.get_setting("production_mode", "false").lower() != "true"
        self._mode_switching = True
        self.query_one("#f-mode", Switch).value = is_test
        self._mode_switching = False
        self.query_one("#mode-label", Label).update("Test Mode" if is_test else "Production")

    def refresh_data(self) -> None:
        """Called by app.switch_section() to keep demo status current."""
        self._refresh_demo_status()

    @on(Button.Pressed, "#btn-save")
    def do_save(self) -> None:
        symbol = self.query_one("#f-currency-symbol", Input).value.strip()
        name   = self.query_one("#f-currency-name",   Input).value.strip()
        theme  = self.query_one("#f-theme", Select).value
        if symbol:
            app_settings.set_setting("currency_symbol", symbol)
        if name:
            app_settings.set_setting("currency_name", name)
        if theme and theme != Select.BLANK:
            self.app.theme = theme  # watch_theme() in app.py auto-saves to DB
        backorder = self.query_one("#f-backorder", Switch).value
        app_settings.set_setting("backorder_allowed", "true" if backorder else "false")
        show_disc = self.query_one("#f-show-disc", Switch).value
        app_settings.set_setting("show_discontinued", "true" if show_disc else "false")
        backup_path = self.query_one("#f-backup-path", Input).value.strip()
        app_settings.set_setting("backup_path", backup_path)
        self.notify("Settings saved.", severity="information")

    @on(Switch.Changed, "#f-mode")
    def on_mode_changed(self, event: Switch.Changed) -> None:
        if self._mode_switching:
            return
        # Ignore programmatic syncs: Switch.Changed is posted asynchronously so
        # _mode_switching is already False by the time the message is delivered.
        # If the new value already matches the persisted DB state it is not a
        # real user toggle — skip it.
        db_is_test = app_settings.get_setting("production_mode", "false").lower() != "true"
        if event.value == db_is_test:
            return
        if event.value:                          # OFF → ON  (Production → Test)
            self._mode_switching = True
            event.switch.value = False           # revert until confirmed
            self._mode_switching = False
            self.app.push_screen(TestModeWarningModal(), self._on_test_mode_confirmed)
        else:                                    # ON → OFF  (Test → Production)
            self._mode_switching = True
            event.switch.value = True            # revert until confirmed
            self._mode_switching = False
            self.app.push_screen(CleanDatabaseModal(), self._on_demo_clean_confirmed)

    def _on_test_mode_confirmed(self, confirmed: bool) -> None:
        if not confirmed:
            return
        self.query_one("#btn-demo-insert", Button).disabled = True
        self.query_one("#btn-demo-clean",  Button).disabled = True
        self.query_one("#demo-status", Static).update("Status: Inserting demo data...")
        self._run_demo_insert()

    @on(Button.Pressed, "#btn-demo-insert")
    def do_demo_insert(self) -> None:
        self.app.push_screen(
            ConfirmActionModal(
                "Insert Demo Data?",
                "This will create sample DN, INV, GR, CN, SI/SO, "
                "and cash/bank documents.",
                confirm_label="Insert",
            ),
            self._on_demo_insert_confirmed,
        )

    def _on_demo_insert_confirmed(self, confirmed: bool) -> None:
        if not confirmed:
            return
        self.query_one("#btn-demo-insert", Button).disabled = True
        self.query_one("#btn-demo-clean", Button).disabled = True
        self.query_one("#demo-status", Static).update("Status: Inserting demo data...")
        self._run_demo_insert()

    @work(thread=True)
    def _run_demo_insert(self) -> None:
        """Run demo insertion in a background thread to keep the TUI responsive."""
        try:
            counts = insert_demo_data()
            parts = [f"{v} {k}" for k, v in counts.items()
                     if k in _DOC_KEYS and v]
            elapsed = counts.get("elapsed_seconds", 0)
            msg = f"Demo inserted: {', '.join(parts)} ({elapsed}s)."
            self.app.call_from_thread(
                self.notify, msg, severity="information"
            )
        except ValueError as exc:
            self.app.call_from_thread(
                self.notify, str(exc), severity="error"
            )
        self.app.call_from_thread(self._refresh_demo_status)

    @on(Button.Pressed, "#btn-demo-clean")
    def do_demo_clean(self) -> None:
        self.app.push_screen(
            CleanDatabaseModal(),
            self._on_demo_clean_confirmed,
        )

    def _on_demo_clean_confirmed(self, confirmed: bool) -> None:
        if not confirmed:
            self._mode_switching = True
            self.query_one("#f-mode", Switch).value = True   # revert to Test
            self._mode_switching = False
            self.query_one("#mode-label", Label).update("Test Mode")
            return
        deleted = clean_demo_data()
        total = sum(deleted.values())
        self.notify(f"Cleaned {total} rows across {len(deleted)} tables. "
                    "Production mode enabled.",
                    severity="warning")
        self._refresh_demo_status()

    @on(Button.Pressed, "#btn-browse-backup")
    def on_browse_backup(self) -> None:
        from screens.modals import FileSelectModal

        def after(path) -> None:
            if not path:
                return
            directory = os.path.dirname(path)
            self.query_one("#f-backup-path", Input).value = directory
            app_settings.set_setting("backup_path", directory)

        self.app.push_screen(
            FileSelectModal(
                title="Choose Backup Directory",
                mode="save",
                default_path=app_settings.get_backup_path() or "~/",
                suggested_name="northwind_backup.db",
                file_filter=".db",
            ),
            after,
        )

    @on(Button.Pressed, "#btn-restore")
    def on_restore(self) -> None:
        from screens.modals import FileSelectModal, ConfirmActionModal

        def do_restore(confirmed: bool) -> None:
            if not confirmed:
                return
            import shutil as _shutil
            import sqlite3 as _sqlite3
            try:
                src = _sqlite3.connect(self._restore_path)
                dst = _sqlite3.connect("northwind.db")
                src.backup(dst)
                src.close()
                dst.close()
                self.notify("Database restored. Relaunching...", timeout=3)
                self.app.set_timer(1.5, self.app.exit)
            except Exception as e:
                self.notify(f"Restore failed: {e}", severity="error", timeout=8)

        def after_pick(path) -> None:
            if not path:
                return
            self._restore_path = path
            self.app.push_screen(
                ConfirmActionModal(
                    title="Restore Database?",
                    message=f"Replace live DB with:\n{path}\n\nApp will exit after restore.",
                    confirm_label="Restore & Exit",
                ),
                do_restore,
            )

        self.app.push_screen(
            FileSelectModal(
                title="Select Backup File",
                mode="open",
                default_path=app_settings.get_backup_path() or "~/",
                file_filter=".db",
            ),
            after_pick,
        )
