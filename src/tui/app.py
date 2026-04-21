import logging
import re
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Label, Tab, Tabs

from cybershoke.models import Server
from tui.service import ServerService


def _ping_cell(ms: int | None) -> Text:
    if ms is None:
        return Text("󰣼", style="#F44336")
    if ms <= 25:
        return Text(f"󰣺 {ms}ms", style="#4CAF50")
    if ms <= 50:
        return Text(f"󰣸 {ms}ms", style="#8BC34A")
    if ms <= 90:
        return Text(f"󰣶 {ms}ms", style="#FFC107")
    if ms <= 140:
        return Text(f"󰣴 {ms}ms", style="#FF9800")
    if ms >= 140:
        return Text(f"󰣾 {ms}ms", style="#FF9800")
    return Text(f"󰣼 {ms}ms", style="#F44336")


def _ping_server(ip: str, port: int, timeout: float = 1.0) -> int | None:
    try:
        start = time.monotonic()
        with socket.create_connection((ip, port), timeout=timeout):
            pass
        return round((time.monotonic() - start) * 1000)
    except Exception:
        return None


def _cat_id(cat: str) -> str:
    """Return a valid Textual widget ID for a category name."""
    return "cat-" + re.sub(r"[^a-zA-Z0-9_-]", "_", cat)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Log debug output to cybershoke-debug.log")
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(
            filename="cybershoke-debug.log",
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(message)s",
        )
        logging.debug("Debug logging enabled")
    CybershokeApp().run()


class CybershokeApp(App):
    DEFAULT_CSS = """
    Screen {
        layout: vertical;
    }

    #mode-bar {
        height: 3;
    }

    #category-bar {
        height: 3;
    }

    #category-bar.hidden {
        display: none;
    }

    #server-table {
        height: 1fr;
    }

    #status-bar {
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $text-muted;
    }
    """

    BINDINGS = [
        # quit
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),

        # actions
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "connect", "Connect", show=True),

        # cursor movement
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g", "cursor_top", "Top", show=False),
        Binding("G", "cursor_bottom", "Bottom", show=False),

        # paging
        Binding("ctrl+d", "half_page_down", "½ Page Down", show=False),
        Binding("ctrl+u", "half_page_up", "½ Page Up", show=False),

        # mode navigation
        Binding("h", "prev_mode", "Prev Mode", show=False, priority=True),
        Binding("l", "next_mode", "Next Mode", show=False, priority=True),

        # category navigation
        Binding("H", "prev_category", "Prev Cat", show=False, priority=True),
        Binding("L", "next_category", "Next Cat", show=False, priority=True),

        # sorting
        Binding("s", "toggle_sort", "Sort", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._service = ServerService()
        self._row_map: dict[int, Server] = {}
        self._seconds_since_refresh: int = 0
        self._mode: str = ""
        self._category: str = ""
        self._sort: str = "players"
        self._refreshing: bool = False
        self._loaded: bool = False
        self._pings: dict[int, int | None] = {}
        self._ping_token: int = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Tabs(id="mode-bar")
        yield Tabs(id="category-bar")
        yield DataTable(id="server-table", cursor_type="row")
        yield Label("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#server-table", DataTable)
        table.add_columns("NUM", "MODE", "MAP", "PLAYERS", "FACEIT", "LOCATION", "PING")
        self.set_interval(30, self.action_refresh)
        self.set_interval(1, self._tick_timer)
        self.run_worker(self._do_refresh, thread=True, exclusive=True)

    # ── workers ──────────────────────────────────────────────────────────────

    def _do_refresh(self) -> None:
        logging.debug("Fetching server data")
        try:
            self._service.refresh()
        except ValueError as e:
            logging.error("Refresh failed: %s", e)
            self.call_from_thread(self.notify, str(e), severity="error")
            return
        logging.debug("Server data fetched successfully")
        self.call_from_thread(self._after_refresh)

    async def _after_refresh(self) -> None:
        self._loaded = True
        self._seconds_since_refresh = 0
        modes = self._service.get_modes()
        mode_bar = self.query_one("#mode-bar", Tabs)

        prev_mode = self._mode
        prev_category = self._category

        self._refreshing = True
        try:
            await mode_bar.clear()
            for mode in modes:
                await mode_bar.add_tab(Tab(mode, id=f"mode-{mode}"))
        finally:
            self._refreshing = False

        target_mode = prev_mode if prev_mode in modes else (modes[0] if modes else "")
        if not target_mode:
            return

        target_cats = self._service.get_categories(target_mode)
        target_cat = (
            prev_category
            if prev_category in target_cats
            else (target_cats[0] if target_cats else "")
        )

        self._mode = target_mode
        self._category = target_cat
        mode_bar.active = f"mode-{target_mode}"
        await self._rebuild_categories(target_mode)
        self._start_pinging(target_mode)

    def _start_pinging(self, mode: str) -> None:
        self._ping_token += 1
        token = self._ping_token
        self._pings.clear()
        self._populate_table()
        self.run_worker(lambda: self._do_ping(mode, token), thread=True)

    def _do_ping(self, mode: str, token: int) -> None:
        servers: dict[int, Server] = {}
        for cat in self._service.get_categories(mode):
            for srv in self._service.get_servers(mode, cat):
                servers[srv.id] = srv

        def ping_one(srv: Server) -> tuple[int, int | None]:
            samples = sorted(s for s in [_ping_server(srv.ip, srv.port) for _ in range(3)] if s is not None)
            return srv.id, samples[len(samples) // 2] if samples else None

        logging.debug("Pinging %d servers", len(servers))
        with ThreadPoolExecutor(max_workers=50) as ex:
            results = list(ex.map(ping_one, servers.values()))

        if token != self._ping_token:
            logging.debug("Ping results discarded (stale token)")
            return

        for srv_id, ms in results:
            self._pings[srv_id] = ms

        logging.debug("Ping complete: %d results", len(results))
        self.call_from_thread(self._populate_table)

    # ── tab events ───────────────────────────────────────────────────────────

    async def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tab is None or self._refreshing:
            return
        tab_id = event.tab.id or ""
        if tab_id.startswith("mode-"):
            mode = tab_id[len("mode-") :]
            if mode != self._mode:
                self._mode = mode
                await self._rebuild_categories(mode)
                self._start_pinging(mode)
        elif tab_id.startswith("cat-"):
            # Reverse the ID back to the category name via the current cats list
            cats = self._service.get_categories(self._mode)
            cat = next((c for c in cats if _cat_id(c) == tab_id), "")
            if cat != self._category:
                self._category = cat
                self._populate_table()

    async def _rebuild_categories(self, mode: str) -> None:
        cats = self._service.get_categories(mode)
        cat_bar = self.query_one("#category-bar", Tabs)
        self._refreshing = True
        try:
            await cat_bar.clear()
            for cat in cats:
                await cat_bar.add_tab(Tab(cat, id=_cat_id(cat)))
        finally:
            self._refreshing = False

        if len(cats) <= 1:
            cat_bar.add_class("hidden")
        else:
            cat_bar.remove_class("hidden")

        preserved = (
            self._category if self._category in cats else (cats[0] if cats else "")
        )
        self._category = preserved
        if preserved and preserved != cats[0]:
            cat_bar.active = _cat_id(preserved)
        self._populate_table()

    # ── table ─────────────────────────────────────────────────────────────────

    def _populate_table(self) -> None:
        table = self.query_one("#server-table", DataTable)
        try:
            cursor_row = table.cursor_row
        except Exception:
            cursor_row = 0

        table.clear()
        self._row_map = {}

        servers = self._service.get_servers(self._mode, self._category)
        if self._sort == "ping":
            servers = sorted(servers, key=lambda s: self._pings.get(s.id) or 9999)
        elif self._sort == "mode":
            servers = sorted(servers, key=lambda s: s.mode, reverse=True)
        else:
            servers = sorted(servers, key=lambda s: s.players, reverse=True)
        for i, srv in enumerate(servers):
            full = srv.players >= srv.maxplayers
            style = "red" if full else "green"
            faceit = str(srv.faceit_avg) if srv.faceit_avg else "-"

            def cell(value: str) -> Text:
                return Text(value, style=style)

            ping = _ping_cell(self._pings[srv.id]) if srv.id in self._pings else Text("...", style=style)

            table.add_row(
                cell(str(srv.num) if srv.num is not None else "-"),
                cell(srv.modeAlt),
                cell(srv.map),
                cell(f"{srv.players}/{srv.maxplayers}"),
                cell(faceit),
                cell(srv.location),
                ping,
            )
            self._row_map[i] = srv

        if servers:
            table.move_cursor(row=min(cursor_row, len(servers) - 1))

        self._update_status_bar()

    # ── status bar ────────────────────────────────────────────────────────────

    def _tick_timer(self) -> None:
        self._seconds_since_refresh += 1
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        if not self._loaded:
            self.query_one("#status-bar", Label).update("Loading...")
            return
        total = self._total_online()
        self.query_one("#status-bar", Label).update(
            f"Updated {self._seconds_since_refresh}s ago  |  Sort: {self._sort}  |  Online: {total}"
        )

    def _total_online(self) -> int:
        seen: set[int] = set()
        total = 0
        for mode in self._service.get_modes():
            for cat in self._service.get_categories(mode):
                for srv in self._service.get_servers(mode, cat):
                    if srv.id not in seen:
                        seen.add(srv.id)
                        total += srv.players
        return total

    # ── actions ──────────────────────────────────────────────────────────────

    def action_toggle_sort(self) -> None:
        order = ["players", "ping", "mode"]
        self._sort = order[(order.index(self._sort) + 1) % len(order)]
        self._populate_table()

    def action_refresh(self) -> None:
        self.run_worker(self._do_refresh, thread=True, exclusive=True)

    def action_connect(self) -> None:
        table = self.query_one("#server-table", DataTable)
        server = self._row_map.get(table.cursor_row)
        if server is None:
            return
        url = f"steam://rungameid/730//+connect%20{server.ip}:{server.port}"
        logging.debug("Connecting to %s:%d (%s)", server.ip, server.port, server.map)
        subprocess.Popen(["xdg-open", url])
        self.notify(f"Connecting to {server.map} ({server.location})")

    def action_cursor_down(self) -> None:
        self.query_one("#server-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#server-table", DataTable).action_cursor_up()

    def action_cursor_top(self) -> None:
        self.query_one("#server-table", DataTable).move_cursor(row=0)

    def action_cursor_bottom(self) -> None:
        table = self.query_one("#server-table", DataTable)
        table.move_cursor(row=table.row_count - 1)

    def action_half_page_down(self) -> None:
        table = self.query_one("#server-table", DataTable)
        half = max(1, table.size.height // 2)
        table.move_cursor(row=min(table.cursor_row + half, table.row_count - 1))

    def action_half_page_up(self) -> None:
        table = self.query_one("#server-table", DataTable)
        half = max(1, table.size.height // 2)
        table.move_cursor(row=max(0, table.cursor_row - half))

    def action_prev_mode(self) -> None:
        self.query_one("#mode-bar", Tabs).action_previous_tab()

    def action_next_mode(self) -> None:
        self.query_one("#mode-bar", Tabs).action_next_tab()

    def action_prev_category(self) -> None:
        cat_bar = self.query_one("#category-bar", Tabs)
        if "hidden" not in cat_bar.classes:
            cat_bar.action_previous_tab()

    def action_next_category(self) -> None:
        cat_bar = self.query_one("#category-bar", Tabs)
        if "hidden" not in cat_bar.classes:
            cat_bar.action_next_tab()
