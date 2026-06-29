"""Tests for ``wkst remove`` (dotfiles.remove)."""

from __future__ import annotations

from pathlib import Path

from wkst import dotfiles
from wkst.dotfiles import Action


def _adopted(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Create a repo + home with one adopted file and a small adopted dir."""
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    (repo / "dotfiles").mkdir(parents=True)
    home.mkdir(parents=True)

    # Single file: ~/.gitconfig
    gitconfig = home / ".gitconfig"
    gitconfig.write_text("[user]\n  name = Alice\n")
    dotfiles.adopt(repo, home, gitconfig, dry_run=False)

    # Directory: ~/.config/zellij with two files
    zellij = home / ".config" / "zellij"
    (zellij / "themes").mkdir(parents=True)
    (zellij / "config.kdl").write_text("kb {}\n")
    (zellij / "themes" / "catppuccin.kdl").write_text("theme {}\n")
    dotfiles.adopt(repo, home, zellij, dry_run=False)

    return repo, home, gitconfig, zellij


def test_remove_restores_single_file(tmp_path: Path) -> None:
    repo, home, gitconfig, _ = _adopted(tmp_path)
    repo_file = repo / "dotfiles" / "git" / ".gitconfig"
    assert gitconfig.is_symlink() and repo_file.is_file()

    results = dotfiles.remove(repo, home, gitconfig, purge=False, dry_run=False)

    assert len(results) == 1
    assert results[0].action == Action.RESTORED
    assert gitconfig.is_file() and not gitconfig.is_symlink()
    assert gitconfig.read_text() == "[user]\n  name = Alice\n"
    assert not repo_file.exists()
    # Empty package dir cleaned up.
    assert not (repo / "dotfiles" / "git").exists()


def test_remove_directory_walks_managed_symlinks(tmp_path: Path) -> None:
    repo, home, _, zellij = _adopted(tmp_path)

    results = dotfiles.remove(repo, home, zellij, purge=False, dry_run=False)

    restored = [r for r in results if r.action == Action.RESTORED]
    assert len(restored) == 2
    assert (zellij / "config.kdl").is_file()
    assert not (zellij / "config.kdl").is_symlink()
    assert (zellij / "themes" / "catppuccin.kdl").is_file()
    # Repo entries gone.
    assert not (repo / "dotfiles" / "config" / ".config" / "zellij").exists()


def test_remove_purge_deletes_everywhere(tmp_path: Path) -> None:
    repo, home, gitconfig, _ = _adopted(tmp_path)

    results = dotfiles.remove(repo, home, gitconfig, purge=True, dry_run=False)

    assert results[0].action == Action.PURGED
    assert not gitconfig.exists()
    assert not (repo / "dotfiles" / "git").exists()


def test_remove_skips_non_symlink(tmp_path: Path) -> None:
    repo, home, _, _ = _adopted(tmp_path)
    real = home / ".bashrc"
    real.write_text("# real file, never adopted\n")

    results = dotfiles.remove(repo, home, real, purge=False, dry_run=False)

    assert results[0].action == Action.SKIPPED
    assert real.is_file()  # unchanged


def test_remove_skips_external_symlink(tmp_path: Path) -> None:
    repo, home, _, _ = _adopted(tmp_path)
    elsewhere = tmp_path / "elsewhere.txt"
    elsewhere.write_text("not in repo")
    link = home / ".somelink"
    link.symlink_to(elsewhere)

    results = dotfiles.remove(repo, home, link, purge=False, dry_run=False)

    assert results[0].action == Action.SKIPPED
    assert link.is_symlink()  # unchanged
    assert elsewhere.is_file()


def test_remove_dry_run_changes_nothing(tmp_path: Path) -> None:
    repo, home, gitconfig, _ = _adopted(tmp_path)
    repo_file = repo / "dotfiles" / "git" / ".gitconfig"

    results = dotfiles.remove(repo, home, gitconfig, purge=False, dry_run=True)

    assert results[0].action == Action.SKIPPED
    assert results[0].detail == "dry-run"
    assert gitconfig.is_symlink()
    assert repo_file.is_file()


def test_remove_directory_with_no_managed_files(tmp_path: Path) -> None:
    repo, home, _, _ = _adopted(tmp_path)
    plain = home / ".config" / "plain"
    plain.mkdir(parents=True)
    (plain / "file.txt").write_text("just a file")

    results = dotfiles.remove(repo, home, plain, purge=False, dry_run=False)

    assert results == []
    # Real file still there.
    assert (plain / "file.txt").is_file()
