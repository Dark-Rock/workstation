"""Textual full-screen dashboard for ``wkst``.

Browse and select packages by section, view a health summary, and launch
install / update / sync without leaving the TUI. Long-running commands run in a
suspended terminal (``App.suspend()``) so the streaming installer and the rich
progress bar own the real screen, then control returns to the dashboard.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import DataTable, Footer, Header, SelectionList, Static, TabbedContent, TabPane
from textual.widgets.selection_list import Selection

from wkst import selection
from wkst.dashboard import actions
from wkst.manifest import Package, load
from wkst.platform import PlatformInfo


class WkstApp(App[int]):
    """Interactive workstation dashboard."""

    TITLE = "wkst"
    SUB_TITLE = "workstation dashboard"

    CSS = """
    SelectionList { height: 1fr; }
    DataTable { height: 1fr; }
    #doctor_status { padding: 1 0 0 0; color: $text-muted; }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("i", "install", "Install selected"),
        Binding("u", "update", "Update selected"),
        Binding("s", "sync", "Sync dotfiles"),
        Binding("d", "doctor", "Run doctor"),
        Binding("a", "select_all", "Select all"),
        Binding("n", "select_none", "Select none"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, repo_root: Path, platform_info: PlatformInfo) -> None:
        super().__init__()
        self._repo_root = repo_root
        self._platform = platform_info
        self._manifest = load(repo_root)

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Packages", id="packages"):
                yield SelectionList[str](*self._package_options(), id="pkglist")
            with TabPane("Doctor", id="doctor"):
                yield DataTable(id="doctor_table")
                yield Static("Press [b]d[/b] to run health checks.", id="doctor_status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#doctor_table", DataTable)
        table.add_columns("Check", "Status", "Detail")
        self.query_one("#pkglist", SelectionList).border_title = "Packages (Space toggles)"

    # -- package selection -------------------------------------------------- #

    def _package_options(self) -> list[Selection[str]]:
        applicable = self._manifest.for_platform(self._platform)
        section_index = self._section_index()
        ordered = sorted(
            applicable,
            key=lambda p: (self._package_section_rank(p, section_index), p.name),
        )
        options: list[Selection[str]] = []
        for pkg in ordered:
            section = self._package_section(pkg, section_index)
            detail = pkg.description or pkg.binary or pkg.name
            options.append(Selection(f"\\[{section}] {pkg.name} — {detail}", pkg.name, True))
        return options

    def _section_index(self) -> dict[str, tuple[int, str]]:
        index: dict[str, tuple[int, str]] = {}
        for rank, (_id, name, _desc, groups) in enumerate(
            selection.available_tool_sections(self._manifest)
        ):
            for group in groups:
                index.setdefault(group, (rank, name))
        return index

    def _package_section_rank(self, pkg: Package, index: dict[str, tuple[int, str]]) -> int:
        ranks = [index[g][0] for g in pkg.groups if g in index]
        return min(ranks) if ranks else len(index) + 1

    def _package_section(self, pkg: Package, index: dict[str, tuple[int, str]]) -> str:
        named = sorted((index[g] for g in pkg.groups if g in index), key=lambda t: t[0])
        return named[0][1] if named else "Misc"

    def _selected_names(self) -> list[str]:
        return list(self.query_one("#pkglist", SelectionList).selected)

    # -- actions ------------------------------------------------------------ #

    def action_select_all(self) -> None:
        self.query_one("#pkglist", SelectionList).select_all()

    def action_select_none(self) -> None:
        self.query_one("#pkglist", SelectionList).deselect_all()

    def action_install(self) -> None:
        sel = actions.build_install_selection(self._manifest, self._selected_names())
        with self.suspend():
            rc = actions.run_install(
                repo_root=self._repo_root, platform_info=self._platform, sel=sel
            )
        self.notify(f"install finished (exit {rc})", severity="information" if rc == 0 else "error")

    def action_update(self) -> None:
        sel = actions.build_install_selection(self._manifest, self._selected_names())
        with self.suspend():
            rc = actions.run_update(
                repo_root=self._repo_root, platform_info=self._platform, sel=sel
            )
        self.notify(f"update finished (exit {rc})", severity="information" if rc == 0 else "error")

    def action_sync(self) -> None:
        with self.suspend():
            rc = actions.run_sync(repo_root=self._repo_root, platform_info=self._platform)
        self.notify(f"sync finished (exit {rc})", severity="information" if rc == 0 else "error")

    def action_doctor(self) -> None:
        self.query_one("#doctor_status", Static).update("Running health checks…")
        self._run_doctor()

    @work(thread=True)
    def _run_doctor(self) -> None:
        from wkst.commands import doctor

        checks = [
            *doctor._check_packages(self._manifest, self._platform),
            *doctor._check_dotfiles(self._repo_root, self._platform),
            *doctor._check_shell(self._platform),
        ]
        self.call_from_thread(self._show_doctor, checks)

    def _show_doctor(self, checks: list[object]) -> None:
        table = self.query_one("#doctor_table", DataTable)
        table.clear()
        failed = 0
        for check in checks:
            ok = bool(getattr(check, "ok", False))
            failed += 0 if ok else 1
            status = "[green]✓ ok[/]" if ok else "[red]✗ fail[/]"
            table.add_row(getattr(check, "name", "?"), status, getattr(check, "detail", "") or "")
        summary = f"{len(checks)} checks, {failed} failed."
        self.query_one("#doctor_status", Static).update(summary)
