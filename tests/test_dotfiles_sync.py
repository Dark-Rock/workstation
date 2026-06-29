"""Tests for dotfile sync selection."""

from __future__ import annotations

from pathlib import Path

from wkst import dotfiles
from wkst.dotfiles import Action


def test_sync_all_can_filter_dotfile_packages(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    (repo / "dotfiles" / "git").mkdir(parents=True)
    (repo / "dotfiles" / "zsh").mkdir(parents=True)
    home.mkdir()
    (repo / "dotfiles" / "git" / ".gitconfig").write_text("[user]\n", encoding="utf-8")
    (repo / "dotfiles" / "zsh" / ".zshrc").write_text("# zsh\n", encoding="utf-8")

    results = dotfiles.sync_all(repo, home, packages=["git"], dry_run=False)

    assert [result.action for result in results] == [Action.LINKED]
    assert (home / ".gitconfig").is_symlink()
    assert not (home / ".zshrc").exists()


def test_sync_all_can_filter_dotfile_subtrees(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    config = repo / "dotfiles" / "config" / ".config"
    (config / "nvim").mkdir(parents=True)
    (config / "tmux").mkdir(parents=True)
    home.mkdir()
    (config / "nvim" / "init.lua").write_text("-- nvim\n", encoding="utf-8")
    (config / "tmux" / "tmux.conf").write_text("# tmux\n", encoding="utf-8")

    results = dotfiles.sync_all(repo, home, packages=["config:.config/nvim"], dry_run=False)

    assert [result.action for result in results] == [Action.LINKED]
    assert (home / ".config" / "nvim" / "init.lua").is_symlink()
    assert not (home / ".config" / "tmux" / "tmux.conf").exists()
