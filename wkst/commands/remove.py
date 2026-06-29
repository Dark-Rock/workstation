"""``wkst remove`` — detach files from the repo (inverse of ``wkst add``)."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from wkst import dotfiles
from wkst.dotfiles import Action, LinkResult
from wkst.logging import log
from wkst.platform import PlatformInfo


def run(
    *,
    repo_root: Path,
    platform_info: PlatformInfo,
    paths: tuple[Path, ...],
    purge: bool,
    dry_run: bool,
    yes: bool = False,
) -> None:
    if not paths:
        log.error("remove: no paths given")
        sys.exit(2)

    # --purge deletes the file from BOTH the repo and $HOME (content is lost);
    # confirm interactively. Non-interactive shells are never blocked.
    if purge and not dry_run and not yes and sys.stdin.isatty():
        click.confirm(
            "remove --purge will delete these files from the repo AND $HOME. Continue?",
            abort=True,
        )

    home = platform_info.home
    all_results: list[LinkResult] = []
    for raw in paths:
        results = dotfiles.remove(repo_root, home, raw, purge=purge, dry_run=dry_run)
        all_results.extend(results)

    rc = _summarize(all_results, purge=purge, dry_run=dry_run)
    sys.exit(rc)


def _summarize(results: list[LinkResult], *, purge: bool, dry_run: bool) -> int:
    by_action: dict[Action, int] = {}
    for r in results:
        by_action[r.action] = by_action.get(r.action, 0) + 1

    log.info("===== remove summary =====")
    for action in Action:
        if action in by_action:
            log.info(f"  {action.value:9s}: {by_action[action]}")

    failed = by_action.get(Action.FAILED, 0)
    handled = by_action.get(Action.RESTORED, 0) + by_action.get(Action.PURGED, 0)

    if dry_run:
        log.info("dry-run: nothing changed. Re-run without --dry-run to apply.")
        return 1 if failed else 0

    if handled and not failed:
        verb = "purged" if purge else "restored"
        log.success(f"{verb} {handled} file(s).")
        log.info("Next steps:")
        log.info("  git status               # see the deletions under dotfiles/")
        log.info("  git add -A dotfiles/     # stage the removals")
        log.info(
            "  git commit -m '"
            + ("chore: drop dotfile" if purge else "chore: unsync dotfile")
            + "'"
        )

    return 1 if failed else 0
