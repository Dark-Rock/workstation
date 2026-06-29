"""Tests for destructive-operation confirmation guards.

Confirmations must fire only for interactive TTY sessions without ``--yes``;
non-interactive shells (CI / pipes) must never be blocked, preserving
scriptability.
"""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from wkst.commands import remove, sync
from wkst.platform import OS, Arch, PlatformInfo


def _platform(tmp_path: Path) -> PlatformInfo:
    return PlatformInfo(os=OS.MACOS, arch=Arch.ARM64, brew_prefix=None, home=tmp_path)


# --- sync --force ----------------------------------------------------------- #


def test_sync_force_non_interactive_does_not_prompt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    confirmed = {"called": False}
    monkeypatch.setattr(click, "confirm", lambda *a, **k: confirmed.__setitem__("called", True))
    # Stub the actual work so we only exercise the guard.
    monkeypatch.setattr(sync.dotfiles, "sync_all", lambda *a, **k: [])
    monkeypatch.setattr(sync.dotfiles, "render_summary", lambda *a, **k: 0)

    with pytest.raises(SystemExit):
        sync.run(
            repo_root=tmp_path,
            platform_info=_platform(tmp_path),
            adopt_path=None,
            force=True,
            dry_run=False,
        )
    assert confirmed["called"] is False


def test_sync_force_interactive_prompts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    calls: list[bool] = []

    def fake_confirm(*_a: object, **_k: object) -> bool:
        calls.append(True)
        raise click.Abort()

    monkeypatch.setattr(click, "confirm", fake_confirm)
    monkeypatch.setattr(sync.dotfiles, "sync_all", lambda *a, **k: [])

    with pytest.raises(click.Abort):
        sync.run(
            repo_root=tmp_path,
            platform_info=_platform(tmp_path),
            adopt_path=None,
            force=True,
            dry_run=False,
        )
    assert calls == [True]


def test_sync_force_yes_skips_prompt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr(
        click, "confirm", lambda *a, **k: (_ for _ in ()).throw(AssertionError("prompted"))
    )
    monkeypatch.setattr(sync.dotfiles, "sync_all", lambda *a, **k: [])
    monkeypatch.setattr(sync.dotfiles, "render_summary", lambda *a, **k: 0)

    with pytest.raises(SystemExit):
        sync.run(
            repo_root=tmp_path,
            platform_info=_platform(tmp_path),
            adopt_path=None,
            force=True,
            dry_run=False,
            yes=True,
        )


# --- remove --purge --------------------------------------------------------- #


def test_remove_purge_non_interactive_does_not_prompt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr(
        click, "confirm", lambda *a, **k: (_ for _ in ()).throw(AssertionError("prompted"))
    )
    monkeypatch.setattr(remove.dotfiles, "remove", lambda *a, **k: [])

    with pytest.raises(SystemExit):
        remove.run(
            repo_root=tmp_path,
            platform_info=_platform(tmp_path),
            paths=(tmp_path / ".foo",),
            purge=True,
            dry_run=False,
        )


def test_remove_purge_interactive_prompts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    calls: list[bool] = []

    def fake_confirm(*_a: object, **_k: object) -> bool:
        calls.append(True)
        raise click.Abort()

    monkeypatch.setattr(click, "confirm", fake_confirm)

    with pytest.raises(click.Abort):
        remove.run(
            repo_root=tmp_path,
            platform_info=_platform(tmp_path),
            paths=(tmp_path / ".foo",),
            purge=True,
            dry_run=False,
        )
    assert calls == [True]
