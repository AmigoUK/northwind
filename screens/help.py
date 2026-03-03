"""screens/help.py — Help panel with searchable topic browser."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import DataTable, Input, Label, Static
from textual import on

from data.help_topics import HELP_TOPICS


class HelpPanel(Widget):

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel-container"):
            yield Label("Help", classes="panel-title")
            yield Input(placeholder="Filter help topics…", id="help-search")
            with Horizontal():
                with Vertical(id="help-sidebar"):
                    yield DataTable(
                        id="help-topics-tbl",
                        cursor_type="row",
                        zebra_stripes=True,
                    )
                with Vertical(id="help-content"):
                    yield Label("", id="help-topic-title")
                    yield Static("", id="help-topic-body")

    def on_mount(self) -> None:
        tbl = self.query_one("#help-topics-tbl", DataTable)
        tbl.add_columns("Category", "Topic")
        self._populate()

    # ── Data helpers ──────────────────────────────────────────────────────────

    def _populate(self, filter_text: str = "") -> None:
        tbl = self.query_one("#help-topics-tbl", DataTable)
        tbl.clear()

        terms = filter_text.lower().split()
        self._visible: list[int] = []

        for idx, topic in enumerate(HELP_TOPICS):
            if terms:
                haystack = " ".join([
                    topic.category,
                    topic.title,
                    topic.body,
                    " ".join(topic.keywords),
                ]).lower()
                if not all(t in haystack for t in terms):
                    continue
            tbl.add_row(topic.category, topic.title, key=str(idx))
            self._visible.append(idx)

        if self._visible:
            tbl.move_cursor(row=0)
            self._show_topic(self._visible[0])
        else:
            self.query_one("#help-topic-title", Label).update("")
            self.query_one("#help-topic-body", Static).update(
                "[i]No topics match your search.[/i]"
            )

    def _show_topic(self, idx: int) -> None:
        topic = HELP_TOPICS[idx]
        header = f"{topic.category}  ›  {topic.title}"
        self.query_one("#help-topic-title", Label).update(header)
        self.query_one("#help-topic-body", Static).update(topic.body)

    # ── Event handlers ────────────────────────────────────────────────────────

    @on(Input.Changed, "#help-search")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self._populate(event.value)

    @on(DataTable.RowHighlighted, "#help-topics-tbl")
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value is not None:
            self._show_topic(int(event.row_key.value))

    def refresh_data(self) -> None:
        """Called by switch_section() — no-op, content is static."""
        pass

    def open_with_context(self, query: str) -> None:
        """Pre-filter help for the calling panel's context. Called by action_open_help."""
        self.query_one("#help-search", Input).value = query
