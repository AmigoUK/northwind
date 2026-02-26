"""screens/settings.py — App settings panel (currency symbol & name).

Educational patterns:
- on_mount() to pre-populate inputs from the DB
- INSERT OR REPLACE upsert via the settings data layer
- notify() for lightweight user feedback without a modal
"""
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Switch
from textual import on

import data.settings as app_settings


class SettingsPanel(Widget):
    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Label("Settings", classes="panel-title")
            with Vertical(classes="settings-section"):
                yield Label("Currency", classes="settings-label")
                yield Label("Symbol (e.g. $, £, €, zł)")
                yield Input(placeholder="$", id="f-currency-symbol")
                yield Label("Name (e.g. USD, GBP, PLN)")
                yield Input(placeholder="USD", id="f-currency-name")
            with Vertical(classes="settings-section"):
                yield Label("Appearance", classes="settings-label")
                yield Label("Theme (also changeable via Ctrl+P)")
                yield Select([], id="f-theme", allow_blank=True)
            with Vertical(classes="settings-section"):
                yield Label("Stock Control", classes="settings-label")
                yield Label("Allow Backorders")
                yield Switch(id="f-backorder", value=False)
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
        self.notify("Settings saved.", severity="information")
