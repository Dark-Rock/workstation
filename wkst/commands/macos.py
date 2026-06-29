"""``wkst macos`` subcommands — export / apply macOS system defaults."""

from __future__ import annotations

import sys
from pathlib import Path

from wkst import macos as _macos
from wkst.logging import log
from wkst.platform import PlatformInfo


def export(*, repo_root: Path, platform_info: PlatformInfo, dry_run: bool) -> None:
    """Read current macOS defaults and write them to macos/settings.toml."""
    if not platform_info.is_macos:
        log.error("macos export: only supported on macOS")
        sys.exit(2)
    rc = _macos.export(repo_root, dry_run=dry_run)
    sys.exit(rc)


def apply(
    *,
    repo_root: Path,
    platform_info: PlatformInfo,
    dry_run: bool,
    no_restart: bool,
) -> None:
    """Apply macos/settings.toml to the current macOS system."""
    if not platform_info.is_macos:
        log.error("macos apply: only supported on macOS")
        sys.exit(2)
    rc = _macos.apply(repo_root, dry_run=dry_run, restart_ui=not no_restart)
    sys.exit(rc)


def discover(
    *,
    repo_root: Path,
    platform_info: PlatformInfo,
    domains: list[str],
    adopt: bool,
    dry_run: bool,
) -> None:
    """Discover scalar macOS defaults and optionally append them to settings.toml."""
    if not platform_info.is_macos:
        log.error("macos discover: only supported on macOS")
        sys.exit(2)
    rc = _macos.discover(repo_root, domains=domains, adopt=adopt, dry_run=dry_run)
    sys.exit(rc)
