"""Smoke tests for the Textual dashboard dispatch + graceful degradation.

These avoid running a real TUI; they exercise the pure dispatch helpers and the
lazy-import fallback so the suite stays fast and headless-safe.
"""

from __future__ import annotations

import builtins
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from wkst import selection
from wkst.dashboard import actions
from wkst.manifest import Manifest, Package
from wkst.platform import OS, Arch, PlatformInfo


def _manifest() -> Manifest:
    return Manifest(
        description="x",
        updated="y",
        packages=(
            Package(name="ripgrep", binary="rg", groups=frozenset({"search"})),
            Package(name="fd", groups=frozenset({"search"})),
            Package(name="neovim", binary="nvim", groups=frozenset({"editor"})),
        ),
        claude_plugins=(),
    )


def test_build_install_selection_matches_package_selection() -> None:
    manifest = _manifest()
    chosen = ["ripgrep", "neovim"]
    sel = actions.build_install_selection(manifest, chosen)
    groups, names = selection.package_selection(manifest, set(chosen))
    assert sel.package_names == names
    assert sel.groups == groups
    assert sel.dotfile_packages is None
    assert sel.setup_names is None


def test_build_install_selection_empty() -> None:
    sel = actions.build_install_selection(_manifest(), [])
    assert sel.package_names == []
    assert sel.groups == []


def test_exit_code_translates_systemexit() -> None:
    assert actions.exit_code(lambda: None) == 0

    def _exit_one() -> None:
        raise SystemExit(1)

    assert actions.exit_code(_exit_one) == 1

    def _exit_none() -> None:
        raise SystemExit(None)

    assert actions.exit_code(_exit_none) == 0

    def _exit_str() -> None:
        raise SystemExit("boom")

    assert actions.exit_code(_exit_str) == 1


def test_launch_handles_missing_textual(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """If Textual can't be imported, launch() reports an error and returns 1."""
    from wkst import dashboard

    real_import = builtins.__import__

    def fake_import(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> object:
        if name == "wkst.dashboard.app" or name.startswith("textual"):
            raise ImportError("textual missing")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    platform = PlatformInfo(os=OS.MACOS, arch=Arch.ARM64, brew_prefix=None, home=tmp_path)
    assert dashboard.launch(tmp_path, platform) == 1
