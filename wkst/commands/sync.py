"""``wkst sync`` — symlink dotfiles from the repo into $HOME (stow-style)."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from wkst import dotfiles
from wkst.logging import log
from wkst.platform import PlatformInfo


def run(
    *,
    repo_root: Path,
    platform_info: PlatformInfo,
    adopt_path: Path | None,
    force: bool,
    dry_run: bool,
    yes: bool = False,
) -> None:
    home = platform_info.home

    if adopt_path is not None:
        results = dotfiles.adopt(repo_root, home, adopt_path, dry_run=dry_run)
        failed = any(r.action == dotfiles.Action.FAILED for r in results)
        sys.exit(1 if failed or not results else 0)

    # --force backs up and replaces real files in $HOME; confirm interactively
    # so an accidental run cannot clobber unmanaged configs. Non-interactive
    # shells (CI / pipes) are never blocked, preserving scriptability.
    if force and not dry_run and not yes and sys.stdin.isatty():
        click.confirm(
            "sync --force will back up and replace conflicting real files in $HOME. Continue?",
            abort=True,
        )

    results = dotfiles.sync_all(repo_root, home, force=force, dry_run=dry_run)
    rc = dotfiles.render_summary(results, force=force)
    if rc == 0:
        log.success("sync complete")
    sys.exit(rc)
