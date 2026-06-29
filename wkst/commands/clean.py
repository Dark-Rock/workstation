"""``wkst clean`` — prune accumulated ``.bak.*`` files and tool caches."""

from __future__ import annotations

import re
from pathlib import Path

from wkst.logging import log
from wkst.platform import PlatformInfo

# Match the timestamped pattern that `install.sh` and `wkst sync --force` use.
_BAK_RE = re.compile(r"\.bak\.\d{8}-?\d{0,6}$")

# Subtrees of $HOME we are willing to scan. Bounded to keep this safe.
_SCAN_DIRS = (
    Path(),  # $HOME root (depth 1)
    Path(".config"),
    Path(".claude"),
    Path(".tmux"),
)


def run(*, repo_root: Path, platform_info: PlatformInfo, dry_run: bool) -> None:
    home = platform_info.home
    found: list[Path] = []
    for sub in _SCAN_DIRS:
        root = home / sub
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if _BAK_RE.search(path.name):
                found.append(path)

    if not found:
        log.success("clean: no backup files found")
        return

    log.info(f"clean: found {len(found)} backup file(s)")
    for p in found:
        log.info(f"  rm {p}")
        if not dry_run:
            try:
                p.unlink()
            except OSError as exc:
                log.warn(f"  failed to remove {p}: {exc}")
    log.success(f"clean: {'would remove' if dry_run else 'removed'} {len(found)} file(s)")
