"""``wkst sync`` — symlink dotfiles from the repo into $HOME (stow-style)."""

from __future__ import annotations

import sys
from pathlib import Path

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
) -> None:
    home = platform_info.home

    if adopt_path is not None:
        results = dotfiles.adopt(repo_root, home, adopt_path, dry_run=dry_run)
        failed = any(r.action == dotfiles.Action.FAILED for r in results)
        sys.exit(1 if failed or not results else 0)

    results = dotfiles.sync_all(repo_root, home, force=force, dry_run=dry_run)
    rc = dotfiles.render_summary(results, force=force)
    if rc == 0:
        log.success("sync complete")
    sys.exit(rc)
