"""Tests for ``wkst add`` (dotfiles.adopt) covering files, dirs, edge cases."""

from __future__ import annotations

from pathlib import Path

from wkst import dotfiles
from wkst.dotfiles import Action


def _setup_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Return (repo_root, fake_home) ready for adoption tests."""
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    (repo / "dotfiles").mkdir(parents=True)
    home.mkdir(parents=True)
    return repo, home


def test_adopt_single_file(tmp_path: Path) -> None:
    repo, home = _setup_repo(tmp_path)
    target = home / ".gitconfig"
    target.write_text("[user]\n  name = Alice\n")

    results = dotfiles.adopt(repo, home, target, dry_run=False)

    assert len(results) == 1
    assert results[0].action == Action.LINKED
    moved = repo / "dotfiles" / "git" / ".gitconfig"
    assert moved.is_file()
    assert target.is_symlink()
    assert target.resolve() == moved.resolve()


def test_adopt_directory_recursive(tmp_path: Path) -> None:
    repo, home = _setup_repo(tmp_path)
    cfg = home / ".config" / "zellij"
    (cfg / "themes").mkdir(parents=True)
    (cfg / "config.kdl").write_text("keybinds {}\n")
    (cfg / "themes" / "catppuccin.kdl").write_text("theme {}\n")
    (cfg / ".DS_Store").write_text("noise")

    results = dotfiles.adopt(repo, home, cfg, dry_run=False)

    # Two real files adopted, .DS_Store filtered out.
    linked = [r for r in results if r.action == Action.LINKED]
    assert len(linked) == 2
    assert (repo / "dotfiles" / "config" / ".config" / "zellij" / "config.kdl").is_file()
    assert (cfg / "config.kdl").is_symlink()
    assert (cfg / "themes" / "catppuccin.kdl").is_symlink()


def test_adopt_skips_existing_symlink(tmp_path: Path) -> None:
    repo, home = _setup_repo(tmp_path)
    repo_file = repo / "dotfiles" / "git" / ".gitconfig"
    repo_file.parent.mkdir(parents=True)
    repo_file.write_text("real")
    target = home / ".gitconfig"
    target.symlink_to(repo_file)

    results = dotfiles.adopt(repo, home, target, dry_run=False)

    assert len(results) == 1
    assert results[0].action == Action.SKIPPED
    assert "symlink" in (results[0].detail or "")


def test_adopt_rejects_outside_home(tmp_path: Path) -> None:
    repo, home = _setup_repo(tmp_path)
    rogue = tmp_path / "elsewhere.txt"
    rogue.write_text("nope")

    results = dotfiles.adopt(repo, home, rogue, dry_run=False)

    assert results[0].action == Action.FAILED
    assert "outside" in (results[0].detail or "")


def test_adopt_dry_run_does_not_move(tmp_path: Path) -> None:
    repo, home = _setup_repo(tmp_path)
    target = home / ".gitconfig"
    target.write_text("[user]\n  name = Alice\n")

    results = dotfiles.adopt(repo, home, target, dry_run=True)

    assert len(results) == 1
    assert results[0].action == Action.SKIPPED
    assert results[0].detail == "dry-run"
    assert target.is_file()
    assert not target.is_symlink()
    assert not (repo / "dotfiles" / "git" / ".gitconfig").exists()


def test_adopt_collision_with_existing_repo_file(tmp_path: Path) -> None:
    repo, home = _setup_repo(tmp_path)
    existing = repo / "dotfiles" / "git" / ".gitconfig"
    existing.parent.mkdir(parents=True)
    existing.write_text("already here")
    target = home / ".gitconfig"
    target.write_text("local copy")

    results = dotfiles.adopt(repo, home, target, dry_run=False)

    assert results[0].action == Action.FAILED
    assert "exists in repo" in (results[0].detail or "")
    # The home file must NOT have been moved.
    assert target.is_file()
    assert target.read_text() == "local copy"
