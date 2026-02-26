"""
app.py — Northwind Traders v2.0
Textual TUI entry point.
"""
from __future__ import annotations

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
from screens.modals     import QuitConfirmModal
from screens.charts     import ChartsPanel


_SECTIONS = [
    ("dashboard",  "Dashboard"),
    ("customers",  "Customers"),
    ("orders",     "Orders"),
    ("products",   "Products"),
    ("employees",  "Employees"),
    ("suppliers",  "Suppliers"),
    ("categories", "Categories"),
    ("shippers",   "Shippers"),
    ("regions",    "Regions"),
    ("reports",    "Reports"),
    ("charts",     "Charts"),
    # Admin-only sections (hidden for non-admin users)
    ("sql",        "SQL Query"),
    ("users",      "Users"),
    ("settings",   "Settings"),
]

# IDs of sections visible only to admins
_ADMIN_SECTIONS = {"sql", "users", "settings"}


class SidebarNav(Widget):
    """Left navigation sidebar."""

    def compose(self) -> ComposeResult:
        yield Label("Northwind", id="sidebar-title")
        with ListView(id="nav-list"):
            for key, label in _SECTIONS:
                yield ListItem(Label(label), id=f"nav-{key}")

    @on(ListView.Selected, "#nav-list")
    def on_nav_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        if item_id and item_id.startswith("nav-"):
            section = item_id[4:]
            self.app.switch_section(section)


class NorthwindApp(App):
    TITLE = "Northwind Traders v2.0"
    CSS_PATH = "northwind.tcss"

    BINDINGS = [
        Binding("ctrl+q", "confirm_quit", "Quit"),
        Binding("n",      "new",          "New",    show=True),
        Binding("f",      "search",       "Search", show=True),
        Binding("escape", "escape",       "Back",   show=False),
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
                yield SqlPanel(id="sql")
                yield UsersPanel(id="users")
                yield SettingsPanel(id="settings")
        yield Footer()

    def on_mount(self) -> None:
        init_db()
        self.push_screen(LoginScreen(), callback=self._on_login)

    def _on_login(self, user: dict) -> None:
        from data.settings import get_theme_name
        self._current_user = user
        nav = self.query_one("#nav-list", ListView)
        nav.index = 0
        self._apply_role_visibility()
        self.theme = get_theme_name()

    def watch_theme(self, theme: str) -> None:
        """Auto-save theme whenever it changes (via ^p palette or settings)."""
        if self._current_user is not None:
            from data.settings import set_setting
            set_setting("theme", theme)

    def _apply_role_visibility(self) -> None:
        """Show admin-only sidebar items only for admin users."""
        is_admin = self._current_user and self._current_user["role"] == "admin"
        for section_id in _ADMIN_SECTIONS:
            try:
                item = self.query_one(f"#nav-{section_id}", ListItem)
                item.display = is_admin
            except Exception:
                pass

    def switch_section(self, section: str) -> None:
        """Switch the active content panel and update sidebar highlight."""
        self.query_one(ContentSwitcher).current = section
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

    def action_confirm_quit(self) -> None:
        """Show a confirmation dialog before quitting."""
        self.push_screen(QuitConfirmModal(), self._on_quit_confirmed)

    def _on_quit_confirmed(self, confirmed: bool) -> None:
        if confirmed:
            self.exit()

    def action_escape(self) -> None:
        """ESC is handled by individual modals; here it's a no-op at top level."""
        pass


if __name__ == "__main__":
    NorthwindApp().run()
