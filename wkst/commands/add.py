"""``wkst add`` — adopt files or directories from $HOME into the repo."""

from __future__ import annotations

import sys
from pathlib import Path

from wkst import dotfiles
from wkst.dotfiles import Action, LinkResult
from wkst.logging import log
from wkst.platform import PlatformInfo


def run(
    *,
    repo_root: Path,
    platform_info: PlatformInfo,
    paths: tuple[Path, ...],
    dry_run: bool,
) -> None:
    if not paths:
        log.error("add: no paths given")
        sys.exit(2)

    home = platform_info.home
    all_results: list[LinkResult] = []
    for raw in paths:
        results = dotfiles.adopt(repo_root, home, raw, dry_run=dry_run)
        all_results.extend(results)

    rc = _summarize(all_results, dry_run=dry_run)
    sys.exit(rc)


def _summarize(results: list[LinkResult], *, dry_run: bool) -> int:
    by_action: dict[Action, int] = {}
    for r in results:
        by_action[r.action] = by_action.get(r.action, 0) + 1

    log.info("===== add summary =====")
    for action in Action:
        if action in by_action:
            log.info(f"  {action.value:9s}: {by_action[action]}")

    failed = by_action.get(Action.FAILED, 0)
    adopted = by_action.get(Action.LINKED, 0) + by_action.get(Action.SKIPPED, 0)

    if dry_run:
        log.info("dry-run: no files moved. Re-run without --dry-run to apply.")
        return 1 if failed else 0

    if adopted and not failed:
        log.success(f"adopted {adopted} file(s).")
        log.info("Next steps:")
        log.info("  git add dotfiles/        # stage the adopted files")
        log.info("  git commit -m 'feat: adopt new dotfiles'")
        log.info("  wkst diff                # confirm everything is in sync")

    return 1 if failed else 0
