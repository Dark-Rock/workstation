"""Shared command helpers for wkst subcommands."""

from __future__ import annotations

import sys
from pathlib import Path

from wkst.logging import log
from wkst.manifest import Manifest, ManifestError, load
from wkst.platform import OS, PlatformInfo

_UNSUPPORTED_PLATFORM = "Unsupported platform; only macOS and Debian/Ubuntu are supported."


def ensure_supported_or_exit(platform_info: PlatformInfo) -> None:
    if platform_info.os is OS.UNSUPPORTED:
        log.error(_UNSUPPORTED_PLATFORM)
        sys.exit(2)


def load_manifest_or_exit(repo_root: Path) -> Manifest:
    try:
        return load(repo_root)
    except ManifestError as exc:
        log.error(str(exc))
        sys.exit(1)


def resolve_groups_or_exit(
    manifest: Manifest,
    *,
    groups: list[str] | None,
    profile: str | None,
) -> list[str] | None:
    if profile and groups:
        log.error("Use either --profile or --groups, not both.")
        sys.exit(2)
    if not profile:
        return groups
    try:
        return manifest.groups_for_profile(profile)
    except ManifestError as exc:
        log.error(str(exc))
        sys.exit(2)


def should_show_menu(
    menu: bool | None,
    *,
    groups: list[str] | None,
    profile: str | None,
) -> bool:
    if menu is not None:
        return menu
    if groups is not None or profile:
        return False
    return sys.stdin.isatty()


def wants_setup(setup_names: list[str] | None, setup: str) -> bool:
    return setup_names is None or setup in setup_names
