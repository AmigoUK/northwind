"""
app.py — Northwind Traders v2.10
Textual TUI entry point.
"""
from __future__ import annotations

import atexit
import os
import signal
import sys

# Ensure consistent 24-bit color rendering across machines.
# The x86_64 Mac has COLORTERM unset, which makes Textual fall back to
# 256 colors. Terminal.app supports truecolor when told explicitly.
if "COLORTERM" not in os.environ:
    os.environ["COLORTERM"] = "truecolor"

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import (
    ContentSwitcher,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
)
from textual import on

from db import init_db
from screens.dashboard  import DashboardPanel
from screens.customers  import CustomersPanel
from screens.orders     import OrdersPanel
from screens.products   import ProductsPanel
from screens.employees  import EmployeesPanel
from screens.suppliers  import SuppliersPanel
from screens.categories import CategoriesPanel
from screens.shippers   import ShippersPanel
from screens.regions    import RegionsPanel
from screens.reports    import ReportsPanel
from screens.login      import LoginScreen
from screens.sql        import SqlPanel
from screens.users      import UsersPanel
from screens.settings   import SettingsPanel
from screens.modals          import QuitConfirmModal
from screens.charts          import ChartsPanel
from screens.dn              import DNPanel
from screens.inv             import INVPanel
from screens.gr              import GRPanel
from screens.stock_movements import StockMovementsPanel
from screens.cash            import CashPanel
from screens.bank            import BankPanel
from screens.cn              import CNPanel
from screens.business        import BusinessDetailsPanel
from screens.help            import HelpPanel

# ── Terminal cleanup ──────────────────────────────────────────────────────────
# Textual enables mouse reporting via escape sequences on startup. If the app
# is killed by SIGTERM/SIGHUP (e.g. terminal close, SSH drop), Textual's normal
# cleanup never runs, leaving mouse reporting active. Every subsequent mouse
# movement then dumps raw escape codes into the shell, making the terminal
# unusable. iTerm2 detects this: "mouse reporting was left on when an app
# misbehaved." This atexit handler is our safety net.

_MOUSE_CLEANUP = (
    "\x1b[?1000l"  # disable normal mouse tracking
    "\x1b[?1003l"  # disable any-event mouse tracking
    "\x1b[?1015l"  # disable urxvt mouse mode
    "\x1b[?1006l"  # disable SGR extended mouse mode
    "\x1b[?1016l"  # disable SGR pixel mouse mode (Textual enables but never disables)
    "\x1b[?2004l"  # disable bracketed paste mode
)


def _reset_terminal_modes():
    """Last-resort cleanup: disable mouse reporting and bracketed paste."""
    try:
        sys.stdout.write(_MOUSE_CLEANUP)
        sys.stdout.flush()
    except Exception:
        pass


atexit.register(_reset_terminal_modes)


_NAV_GROUPS = [
    ("── Master Data ──", "nav-group-master", [
        ("dashboard",  "Dashboard"),
        ("customers",  "Customers"),
        ("orders",     "Orders"),
        ("products",   "Products"),
        ("employees",  "Employees"),
        ("suppliers",  "Suppliers"),
        ("categories", "Categories"),
        ("shippers",   "Shippers"),
        ("regions",    "Regions"),
    ]),
    ("── Documents ──", "nav-group-docs", [
        ("dn",         "DN — Delivery Note"),
        ("inv",        "INV — Invoices"),
        ("cn",         "CN — Credit Notes"),
        ("gr",         "GR — Goods Receipt"),
        ("movements",  "SI/SO — Stock"),
    ]),
    ("── Finance ──", "nav-group-finance", [
        ("cash",       "Cash Register"),
        ("bank",       "Bank Account"),
    ]),
    ("── Analytics ──", "nav-group-analytics", [
        ("reports",    "Reports"),
        ("charts",     "Charts"),
    ]),
    ("── Admin ──", "nav-group-admin", [
        ("sql",        "SQL Query"),
        ("users",      "Users"),
        ("business",   "Business Details"),
        ("settings",   "Settings"),
    ]),
    ("── Help ──", "nav-group-help", [
        ("help",       "Help"),
    ]),
]

# Flat list derived from groups for use in switch_section() iteration
_SECTIONS = [(key, label) for _, _, items in _NAV_GROUPS for key, label in items]

# IDs of sections visible only to admins
_ADMIN_SECTIONS = {"sql", "users", "business", "settings"}


class SidebarNav(Widget):
    """Left navigation sidebar."""

    def compose(self) -> ComposeResult:
        yield Label("Northwind", id="sidebar-title")
        with ListView(id="nav-list"):
            for group_label, group_id, items in _NAV_GROUPS:
                yield ListItem(Label(group_label), id=group_id,
                               classes="nav-group-header")
                for key, label in items:
                    yield ListItem(Label(label), id=f"nav-{key}")

    @on(ListView.Selected, "#nav-list")
    def on_nav_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        if item_id and item_id.startswith("nav-") and not item_id.startswith("nav-group-"):
            section = item_id[4:]
            self.app.switch_section(section)


class NorthwindApp(App):
    TITLE = "Northwind Traders v2.10"
    CSS_PATH = "northwind.tcss"

    BINDINGS = [
        Binding("ctrl+q", "confirm_quit", "Quit"),
        Binding("n",      "new",          "New",    show=True),
        Binding("f",      "search",       "Search", show=True),
        Binding("ctrl+x", "export_csv",   "Export", show=True),
        Binding("ctrl+i", "import_csv",   "Import", show=True),
        Binding("escape", "escape",       "Back",   show=False),
        Binding("question_mark", "open_help", "Help", show=True, key_display="?"),
    ]

    _current_user: dict | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield SidebarNav(id="sidebar")
            with ContentSwitcher(id="content", initial="dashboard"):
                yield DashboardPanel(id="dashboard")
                yield CustomersPanel(id="customers")
                yield OrdersPanel(id="orders")
                yield ProductsPanel(id="products")
                yield EmployeesPanel(id="employees")
                yield SuppliersPanel(id="suppliers")
                yield CategoriesPanel(id="categories")
                yield ShippersPanel(id="shippers")
                yield RegionsPanel(id="regions")
                yield ReportsPanel(id="reports")
                yield ChartsPanel(id="charts")
                yield DNPanel(id="dn")
                yield INVPanel(id="inv")
                yield CNPanel(id="cn")
                yield GRPanel(id="gr")
                yield StockMovementsPanel(id="movements")
                yield CashPanel(id="cash")
                yield BankPanel(id="bank")
                yield SqlPanel(id="sql")
                yield UsersPanel(id="users")
                yield BusinessDetailsPanel(id="business")
                yield SettingsPanel(id="settings")
                yield HelpPanel(id="help")
        yield Footer()

    def on_mount(self) -> None:
        init_db()
        # SIGTERM is being sent by an external process (endpoint security
        # agent?) on the x86_64 machine. Ignore it — the app has Ctrl+Q
        # for intentional quit, and SIGHUP handles real terminal close.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGHUP, self._handle_termination_signal)
        self.push_screen(LoginScreen(), callback=self._on_login)

    def _handle_termination_signal(self, signum: int, frame) -> None:
        """Gracefully exit on SIGHUP so Textual disables mouse reporting."""
        self.exit()

    def _on_login(self, user: dict) -> None:
        self._current_user = user
        nav = self.query_one("#nav-list", ListView)
        nav.index = 0
        self._apply_role_visibility()
        self.call_later(self._apply_saved_theme)

    def _apply_saved_theme(self) -> None:
        """Apply the user's saved theme after the widget tree is stable."""
        try:
            from data.settings import get_theme_name
            self.theme = get_theme_name()
        except Exception:
            pass

    def watch_theme(self, theme: str) -> None:
        """Auto-save theme whenever it changes (via ^p palette or settings)."""
        if self._current_user is not None:
            from data.settings import set_setting
            set_setting("theme", theme)

    def _apply_role_visibility(self) -> None:
        """Show admin-only sidebar items only for admin users."""
        from data.users import has_permission
        is_admin = has_permission(self._current_user, "admin")
        for section_id in _ADMIN_SECTIONS:
            try:
                item = self.query_one(f"#nav-{section_id}", ListItem)
                item.display = is_admin
            except Exception:
                pass
        try:
            self.query_one("#nav-group-admin", ListItem).display = is_admin
        except Exception:
            pass

    def switch_section(self, section: str) -> None:
        """Switch the active content panel and update sidebar highlight."""
        self.query_one(ContentSwitcher).current = section
        try:
            panel = self.query_one(f"#{section}")
            if hasattr(panel, "refresh_data"):
                panel.refresh_data()
        except Exception:
            pass
        for key, _ in _SECTIONS:
            try:
                item = self.query_one(f"#nav-{key}", ListItem)
                if key == section:
                    item.add_class("active-nav")
                else:
                    item.remove_class("active-nav")
            except Exception:
                pass

    def action_new(self) -> None:
        """Delegate N key to the active panel."""
        current = self.query_one(ContentSwitcher).current
        try:
            panel = self.query_one(f"#{current}")
            panel.action_new_record()
        except Exception:
            pass

    def action_search(self) -> None:
        """Delegate F key to the active panel."""
        current = self.query_one(ContentSwitcher).current
        try:
            panel = self.query_one(f"#{current}")
            panel.action_focus_search()
        except Exception:
            pass

    def action_export_csv(self) -> None:
        """Delegate Ctrl+X to the active panel's export action."""
        current = self.query_one(ContentSwitcher).current
        try:
            panel = self.query_one(f"#{current}")
            panel.action_export_csv()
        except Exception:
            pass

    def action_import_csv(self) -> None:
        """Delegate Ctrl+I to the active panel's import action."""
        current = self.query_one(ContentSwitcher).current
        try:
            panel = self.query_one(f"#{current}")
            panel.action_import_csv()
        except Exception:
            pass

    def action_confirm_quit(self) -> None:
        """Show a confirmation dialog before quitting."""
        self.push_screen(QuitConfirmModal(), self._on_quit_confirmed)

    def _on_quit_confirmed(self, confirmed: bool) -> None:
        if confirmed:
            self.exit()

    def action_open_help(self) -> None:
        """Switch to the Help panel."""
        self.switch_section("help")

    def action_escape(self) -> None:
        """ESC is handled by individual modals; here it's a no-op at top level."""
        pass


if __name__ == "__main__":
    NorthwindApp().run()
