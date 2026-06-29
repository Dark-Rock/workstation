"""Structured logger matching the existing install.sh format.

Lines look like: ``[2026-04-19 20:47:05] INFO: doing thing``

Output goes to stderr so stdout can be reserved for machine-readable data
(e.g. ``wkst manifest render-md`` writing markdown to stdout).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from datetime import datetime
from enum import IntEnum
from typing import TextIO

_TS_FMT = "%Y-%m-%d %H:%M:%S"


class Level(IntEnum):
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    SUCCESS = 25  # Between INFO and WARN to keep ordering sane.


# ANSI escape codes; auto-disabled when stderr is not a TTY or NO_COLOR is set.
_COLORS: dict[Level, str] = {
    Level.DEBUG: "\033[2;37m",  # dim white
    Level.INFO: "\033[0;36m",  # cyan
    Level.SUCCESS: "\033[1;32m",  # bold green
    Level.WARN: "\033[1;33m",  # bold yellow
    Level.ERROR: "\033[1;31m",  # bold red
}
_RESET = "\033[0m"


def _color_enabled(stream: TextIO) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("WKST_FORCE_COLOR"):
        return True
    return stream.isatty()


class Logger:
    """Minimal structured logger; one shared instance, configured at CLI entry."""

    def __init__(self, level: Level = Level.INFO, stream: TextIO | None = None) -> None:
        self.level = level
        self.stream = stream or sys.stderr
        self._color = _color_enabled(self.stream)
        # Optional sink that takes over emission (e.g. a rich live region routes
        # log lines through its console so they don't tear the progress bar).
        self._writer: Callable[[str], None] | None = None

    def set_level(self, level: Level) -> None:
        self.level = level

    def set_writer(self, writer: Callable[[str], None]) -> None:
        """Route emitted lines through ``writer`` instead of ``self.stream``.

        Used by the rich progress layer to keep log output and the live region
        from corrupting each other. Pair with :meth:`reset_writer`.
        """
        self._writer = writer

    def reset_writer(self) -> None:
        """Restore direct-to-stream emission."""
        self._writer = None

    def _emit(self, level: Level, msg: str) -> None:
        if level < self.level:
            return
        ts = datetime.now().strftime(_TS_FMT)
        label = level.name
        if self._color:
            color = _COLORS.get(level, "")
            line = f"[{ts}] {color}{label}{_RESET}: {msg}"
        else:
            line = f"[{ts}] {label}: {msg}"
        if self._writer is not None:
            self._writer(line)
        else:
            print(line, file=self.stream, flush=True)

    def debug(self, msg: str) -> None:
        self._emit(Level.DEBUG, msg)

    def info(self, msg: str) -> None:
        self._emit(Level.INFO, msg)

    def warn(self, msg: str) -> None:
        self._emit(Level.WARN, msg)

    def error(self, msg: str) -> None:
        self._emit(Level.ERROR, msg)

    def success(self, msg: str) -> None:
        self._emit(Level.SUCCESS, msg)


log = Logger()


def configure(*, verbose: bool = False, quiet: bool = False) -> None:
    """Configure the global logger from CLI flags."""
    if quiet:
        log.set_level(Level.WARN)
    elif verbose:
        log.set_level(Level.DEBUG)
    else:
        log.set_level(Level.INFO)
