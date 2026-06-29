"""Dispatch layer between the Textual dashboard and the existing commands.

This module does **not** reimplement install/update/sync logic — it collects the
dashboard's selection into the shared :class:`InstallSelection` shape and calls
the existing command ``run`` functions. Those call ``sys.exit``; the dashboard
runs them inside ``App.suspend()`` and relies on :func:`exit_code` to capture
the status instead of letting ``SystemExit`` tear down the TUI.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from wkst import selection as selection_mod
from wkst.manifest import Manifest
from wkst.platform import PlatformInfo
from wkst.preferences import InstallPreferences
from wkst.selection import InstallSelection


def build_install_selection(manifest: Manifest, selected_names: list[str]) -> InstallSelection:
    """Map a set of chosen package names to the shared selection shape."""
    groups, names = selection_mod.package_selection(manifest, set(selected_names))
    return InstallSelection(
        groups=groups,
        package_names=names,
        dotfile_packages=None,
        setup_names=None,
        preferences=InstallPreferences(),
    )


def exit_code(func: Callable[[], None]) -> int:
    """Run ``func`` and translate its ``SystemExit`` into an int exit code."""
    try:
        func()
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        return 1
    return 0


def run_install(*, repo_root: Path, platform_info: PlatformInfo, sel: InstallSelection) -> int:
    from wkst.commands import install as cmd

    return exit_code(
        lambda: cmd.run(
            repo_root=repo_root,
            platform_info=platform_info,
            groups=sel.groups,
            profile=None,
            menu=False,
            dry_run=False,
            package_names=sel.package_names,
        )
    )


def run_update(*, repo_root: Path, platform_info: PlatformInfo, sel: InstallSelection) -> int:
    from wkst.commands import update as cmd

    return exit_code(
        lambda: cmd.run(
            repo_root=repo_root,
            platform_info=platform_info,
            groups=sel.groups,
            profile=None,
            menu=False,
            dry_run=False,
            package_names=sel.package_names,
        )
    )


def run_sync(*, repo_root: Path, platform_info: PlatformInfo) -> int:
    from wkst.commands import sync as cmd

    return exit_code(
        lambda: cmd.run(
            repo_root=repo_root,
            platform_info=platform_info,
            adopt_path=None,
            force=False,
            dry_run=False,
            yes=True,
        )
    )
