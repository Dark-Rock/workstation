"""``wkst diff`` — show drift between dotfiles in the repo and $HOME."""

from __future__ import annotations

from pathlib import Path

from wkst import dotfiles
from wkst.logging import log
from wkst.platform import PlatformInfo


def run(*, repo_root: Path, platform_info: PlatformInfo) -> int:
    home = platform_info.home
    drift = dotfiles.diff_all(repo_root, home)
    if not drift:
        log.success("dotfiles in sync")
        return 0
    log.warn(f"{len(drift)} dotfile(s) out of sync:")
    for r in drift:
        log.warn(f"  {r.target}  ({r.detail}) -> {r.source}")
    return 1
