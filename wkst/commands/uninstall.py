"""``wkst uninstall`` — remove packages and managed dotfile links."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from wkst import dotfiles
from wkst.commands.common import (
    ensure_supported_or_exit,
    load_manifest_or_exit,
    resolve_groups_or_exit,
)
from wkst.install_pipeline import render_summary, run_pipeline, uninstall_op
from wkst.logging import log
from wkst.platform import PlatformInfo


def run(
    *,
    repo_root: Path,
    platform_info: PlatformInfo,
    groups: list[str] | None,
    profile: str | None,
    dry_run: bool,
    yes: bool,
) -> None:
    ensure_supported_or_exit(platform_info)

    manifest = load_manifest_or_exit(repo_root)
    groups = resolve_groups_or_exit(manifest, groups=groups, profile=profile)

    if not dry_run and not yes:
        click.confirm(
            "This will uninstall manifest packages and unlink wkst-managed dotfiles. Continue?",
            abort=True,
        )

    log.info(f"uninstall: platform={platform_info.os.value} dry_run={dry_run}")
    outcomes = run_pipeline(
        manifest=manifest,
        platform_info=platform_info,
        groups=groups,
        package_names=None,
        operation=uninstall_op,
        operation_label="uninstall",
        dry_run=dry_run,
    )

    dot_results = dotfiles.unlink_all(repo_root, platform_info.home, dry_run=dry_run)
    dot_rc = dotfiles.render_summary(dot_results, force=True)
    pkg_rc = render_summary(outcomes)
    sys.exit(1 if pkg_rc or dot_rc else 0)
