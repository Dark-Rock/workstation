"""Shared rich-based presentation layer for the ``wkst`` CLI.

This is the single home for spinners, progress bars, result tables, and error
panels. Everything here degrades cleanly: when stderr is not a TTY, ``NO_COLOR``
is set, or ``WKST_NO_RICH`` is set, ``rich_enabled()`` returns ``False`` and the
helpers become no-ops so callers fall back to plain log lines. This keeps the
non-interactive (CI / ``--no-menu`` / piped) path byte-stable and scriptable.

Output is on **stderr** (like the logger) so stdout stays reserved for
machine-readable data such as ``wkst manifest render-md``.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from wkst import logging as wkst_logging
from wkst.logging import log

if TYPE_CHECKING:  # annotations only — avoids a runtime circular import
    from wkst.commands.doctor import Check
    from wkst.dotfiles import LinkResult
    from wkst.install_pipeline import Outcome


def rich_enabled() -> bool:
    """Whether rich output should be used for the current stderr stream.

    Reuses the logger's color gate (honors ``NO_COLOR`` / ``WKST_FORCE_COLOR``)
    and adds a ``WKST_NO_RICH`` escape hatch for tests and paranoid automation.
    """
    if os.environ.get("WKST_NO_RICH"):
        return False
    return wkst_logging._color_enabled(sys.stderr)


def console() -> Console:
    """A stderr-bound console honoring the current capability gate."""
    return Console(file=sys.stderr, no_color=not rich_enabled())


# --------------------------------------------------------------------------- #
# Live progress
# --------------------------------------------------------------------------- #


class _NoOpProgress:
    """Handle returned when rich is disabled; every method is inert."""

    def advance(self, *, package: str = "", ok: bool = True, skipped: bool = False) -> None:
        return None

    def pause(self) -> None:
        return None

    def resume(self) -> None:
        return None


class _RichProgress:
    """Drives a rich ``Progress`` bar over a known number of items."""

    def __init__(self, progress: Progress, task_id: TaskID) -> None:
        self._progress = progress
        self._task_id = task_id

    def advance(self, *, package: str = "", ok: bool = True, skipped: bool = False) -> None:
        if package:
            mark = "[yellow]⊘[/]" if skipped else ("[green]✓[/]" if ok else "[red]✗[/]")
            self._progress.update(self._task_id, description=f"{mark} {package}")
        self._progress.advance(self._task_id, 1)

    def pause(self) -> None:
        """Stop the live region so a streaming subprocess owns the terminal."""
        self._progress.stop()

    def resume(self) -> None:
        self._progress.start()


@contextmanager
def live_progress(total: int, description: str) -> Generator[_NoOpProgress | _RichProgress]:
    """Context manager yielding a progress handle.

    While the rich region is active, log output is routed through the progress
    console so log lines and the bar don't corrupt each other. Restores the
    logger on exit. When rich is disabled, yields an inert handle and leaves the
    logger untouched — the existing per-item log lines remain the sole feedback.
    """
    if not rich_enabled():
        yield _NoOpProgress()
        return

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console(),
        transient=True,
    )
    task_id = progress.add_task(description, total=total)
    progress.start()
    log.set_writer(lambda line: progress.console.print(Text.from_ansi(line)))
    try:
        yield _RichProgress(progress, task_id)
    finally:
        log.reset_writer()
        progress.stop()


# --------------------------------------------------------------------------- #
# Result tables
# --------------------------------------------------------------------------- #


def _status_cell(ok: bool, skipped: bool, reason: str = "") -> str:
    if skipped:
        return "[yellow]⊘ skipped[/]" + (f" — {reason}" if reason else "")
    if ok:
        return "[green]✓ ok[/]"
    return "[red]✗ failed[/]"


def outcome_table(outcomes: list[Outcome]) -> Table:
    table = Table(title="summary", title_justify="left", expand=False)
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("Backend")
    table.add_column("Status")
    for o in outcomes:
        table.add_row(o.package, o.backend, _status_cell(o.ok, o.skipped, o.reason))
    return table


def doctor_table(checks: list[Check]) -> Table:
    table = Table(title="doctor", title_justify="left", expand=False)
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Detail", overflow="fold")
    for c in checks:
        status = "[green]✓ ok[/]" if c.ok else "[red]✗ fail[/]"
        table.add_row(c.name, status, c.detail or "")
    return table


def diff_table(results: list[LinkResult]) -> Table:
    table = Table(title="dotfile drift", title_justify="left", expand=False)
    table.add_column("Target", style="cyan", overflow="fold")
    table.add_column("State", style="yellow")
    table.add_column("Source", overflow="fold")
    for r in results:
        state = r.detail or getattr(r.action, "value", str(r.action))
        table.add_row(str(r.target), state, str(r.source))
    return table


# --------------------------------------------------------------------------- #
# Error panels + fix hints
# --------------------------------------------------------------------------- #


def fix_hint_for(outcome: Outcome) -> str | None:
    """Single source of truth for "run this to fix" hints on failed packages."""
    if outcome.skipped:
        return None
    if outcome.backend == "brew":
        return "brew doctor"
    return "wkst doctor"


def failure_panel(title: str, lines: list[str], hint: str | None = None) -> Panel:
    body = Text("\n".join(lines))
    if hint:
        body.append(f"\nTry: {hint}", style="dim")
    return Panel(body, title=title, border_style="red", title_align="left")


def print_failure(title: str, lines: list[str], hint: str | None = None) -> None:
    """Render a failure as a panel (rich) or plain log lines (non-TTY)."""
    if rich_enabled():
        console().print(failure_panel(title, lines, hint))
        return
    log.error(title)
    for line in lines:
        log.warn(f"  {line}")
    if hint:
        log.warn(f"  Fix: {hint}")
