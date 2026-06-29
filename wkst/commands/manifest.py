"""``wkst manifest`` subcommand: validate, list, render-md."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from wkst.logging import log
from wkst.manifest import Manifest, ManifestError, load, manifest_path
from wkst.platform import OS, PlatformInfo


def validate(repo_root: Path, platform_info: PlatformInfo) -> int:
    try:
        m = load(repo_root)
    except ManifestError as exc:
        log.error(str(exc))
        return 1

    log.success(
        f"Manifest OK: {len(m.packages)} packages, "
        f"{len(m.claude_plugins)} claude plugin(s), "
        f"{len(m.all_groups())} groups."
    )

    applicable = m.for_platform(platform_info)
    log.info(f"Applicable on {platform_info.os.value}: {len(applicable)} package(s).")

    unresolved = [p for p in applicable if p.resolved_backend(platform_info) is None]
    if unresolved:
        log.warn(f"{len(unresolved)} package(s) have no installable backend on this platform:")
        for p in unresolved:
            log.warn(f"  - {p.name}")
        return 2
    return 0


def list_packages(
    repo_root: Path,
    platform_info: PlatformInfo,
    groups: list[str] | None,
) -> None:
    try:
        m = load(repo_root)
    except ManifestError as exc:
        log.error(str(exc))
        sys.exit(1)

    selected = m.in_groups(m.for_platform(platform_info), groups)
    by_group: dict[str, list[str]] = defaultdict(list)
    for p in selected:
        for g in sorted(p.groups) or ["(ungrouped)"]:
            by_group[g].append(p.name)

    for group_name in sorted(by_group):
        names = sorted(by_group[group_name])
        print(f"\n[{group_name}]  ({len(names)})")
        for n in names:
            print(f"  - {n}")


def add_package(
    repo_root: Path,
    name: str,
    brew: str | None,
    brew_type: str,
    apt: str | None,
    cargo: str | None,
    npm: str | None,
    pipx: str | None,
    binary: str | None,
    groups: list[str],
    platforms: list[str],
    description: str | None,
    dry_run: bool,
) -> int:
    """Append a new [[package]] entry to packages.toml."""
    if not any([brew, apt, cargo, npm, pipx]):
        log.error("Specify at least one backend: --brew, --apt, --cargo, --npm, or --pipx.")
        return 1

    try:
        m = load(repo_root)
    except ManifestError as exc:
        log.error(str(exc))
        return 1

    if any(p.name == name for p in m.packages):
        log.error(f"Package {name!r} already exists in packages.toml.")
        return 1

    block = _build_toml_block(
        name, brew, brew_type, apt, cargo, npm, pipx, binary, groups, platforms, description
    )

    if dry_run:
        log.info("Would append to packages.toml:\n")
        print(block)
        return 0

    path = manifest_path(repo_root)
    text = path.read_text()
    path.write_text(_insert_package(text, block))
    log.success(f"Added {name!r} to packages.toml.")
    return 0


def _build_toml_block(
    name: str,
    brew: str | None,
    brew_type: str,
    apt: str | None,
    cargo: str | None,
    npm: str | None,
    pipx: str | None,
    binary: str | None,
    groups: list[str],
    platforms: list[str],
    description: str | None,
) -> str:
    lines = ["[[package]]", f'name = "{name}"']
    if binary:
        lines.append(f'binary = "{binary}"')
    if brew:
        lines.append(f'brew = "{brew}"')
        if brew_type != "formula":
            lines.append(f'brew_type = "{brew_type}"')
    if apt:
        lines.append(f'apt = "{apt}"')
    if cargo:
        lines.append(f'cargo = "{cargo}"')
    if npm:
        lines.append(f'npm = "{npm}"')
    if pipx:
        lines.append(f'pipx = "{pipx}"')
    if groups:
        groups_toml = ", ".join(f'"{g}"' for g in groups)
        lines.append(f"groups = [{groups_toml}]")
    if platforms:
        plat_toml = ", ".join(f'"{p}"' for p in platforms)
        lines.append(f"platforms = [{plat_toml}]")
    if description:
        escaped = description.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'description = "{escaped}"')
    return "\n".join(lines) + "\n"


def _insert_package(text: str, block: str) -> str:
    """Insert block before the plugins section, preserving the comment separator."""
    marker = "\n[plugins.claude]"
    if marker not in text:
        return text.rstrip() + "\n\n" + block
    before, after = text.split(marker, 1)
    # Place new entry just before the separator comment that precedes [plugins.claude]
    last_sep = before.rfind("\n# ---")
    if last_sep != -1:
        return before[:last_sep] + "\n\n" + block + before[last_sep:] + marker + after
    return before.rstrip() + "\n\n" + block + marker + after


def render_md(repo_root: Path) -> None:
    """Render manifest as Markdown table grouped by category — for docs/TOOLS.md."""
    try:
        m = load(repo_root)
    except ManifestError as exc:
        log.error(str(exc))
        sys.exit(1)

    sys.stdout.write(_render_md(m))


def _render_md(m: Manifest) -> str:
    lines: list[str] = []
    lines.append("# Workstation Tools Cheatsheet")
    lines.append("")
    lines.append(f"_Auto-generated from `packages.toml` (updated {m.updated})._")
    lines.append("")
    lines.append("Edit `packages.toml`, then run `just docs` to regenerate this file.")
    lines.append("")

    by_group: dict[str, list] = defaultdict(list)
    for p in m.packages:
        for g in sorted(p.groups) or ["other"]:
            by_group[g].append(p)

    for group in sorted(by_group):
        rows = sorted(by_group[group], key=lambda x: x.name)
        lines.append(f"## {group}")
        lines.append("")
        lines.append("| Package | Binary | macOS | Linux (apt) | Description |")
        lines.append("|---------|--------|-------|-------------|-------------|")
        for p in rows:
            macos_cell = _cell_for(p, OS.MACOS)
            linux_cell = _cell_for(p, OS.LINUX_DEBIAN)
            binary = f"`{p.binary}`" if p.binary else f"`{p.name}`"
            desc = p.description or ""
            lines.append(f"| `{p.name}` | {binary} | {macos_cell} | {linux_cell} | {desc} |")
        lines.append("")

    if m.claude_plugins:
        lines.append("## claude plugins")
        lines.append("")
        lines.append("| Plugin | Source |")
        lines.append("|--------|--------|")
        for plug in m.claude_plugins:
            lines.append(f"| `{plug.name}` | {plug.source} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _cell_for(pkg, os_kind: OS) -> str:
    if pkg.platforms and os_kind not in pkg.platforms:
        return "—"
    if os_kind is OS.MACOS:
        if pkg.brew:
            tag = "cask" if pkg.brew_type == "cask" else "brew"
            return f"`{tag}: {pkg.brew}`"
    elif os_kind is OS.LINUX_DEBIAN and pkg.apt:
        return f"`apt: {pkg.apt}`"
    for backend in ("cargo", "npm", "pipx"):
        ident = getattr(pkg, backend)
        if ident:
            return f"`{backend}: {ident}`"
    return "—"
