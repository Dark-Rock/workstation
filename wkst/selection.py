"""Pure package-selection logic shared by the install menu and the dashboard.

This module holds the manifest-driven helpers that map high-level "tool
sections" to package groups and resolve a chosen set of package names back into
``(groups, names)``. It has **no** dependency on prompt-toolkit, rich, or any
interactive layer, so both the prompt-toolkit wizard (``install_menu``) and the
Textual dashboard (``dashboard``) can reuse it without drift.
"""

from __future__ import annotations

from dataclasses import dataclass

from wkst.manifest import Manifest, Package
from wkst.preferences import InstallPreferences

# High-level groupings shown to the user. Each entry is
# ``(section_id, display_name, description, member_groups)``.
TOOL_SECTIONS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("core", "Core", "Base dependencies shared by the rest of the setup", ("core",)),
    (
        "dev",
        "Dev",
        "Development, languages, APIs, databases, quality, editor, and Git tools",
        ("dev", "db", "languages", "api", "quality", "editor", "git"),
    ),
    (
        "term",
        "Term",
        "Terminal, shell, search, navigation, and local system tooling",
        ("terminal", "shell", "search", "system"),
    ),
    (
        "ops",
        "Ops",
        "Containers, Kubernetes, performance, IaC, and security tooling",
        ("containers", "k8s", "perf", "iac", "secrets"),
    ),
    ("desktop", "Desktop", "GUI apps, fonts, and document utilities", ("gui", "fonts", "docs")),
    ("ai", "AI", "AI assistants and coding-agent tools", ("ai",)),
)


@dataclass(frozen=True)
class InstallSelection:
    """Interactive install/update selections (shared by menu and dashboard)."""

    groups: list[str] | None
    package_names: list[str] | None
    dotfile_packages: list[str] | None
    setup_names: list[str] | None
    preferences: InstallPreferences


def available_tool_sections(
    manifest: Manifest,
) -> list[tuple[str, str, str, tuple[str, ...]]]:
    """Tool sections trimmed to the groups that exist in this manifest.

    Any manifest groups not covered by ``TOOL_SECTIONS`` are bundled into a
    trailing "Misc" section so nothing becomes unreachable.
    """
    known_groups = set(manifest.all_groups())
    sections = [
        (section_id, name, description, tuple(group for group in groups if group in known_groups))
        for section_id, name, description, groups in TOOL_SECTIONS
    ]
    sections = [section for section in sections if section[3]]

    grouped = {group for *_prefix, groups in sections for group in groups}
    misc_groups = tuple(sorted(known_groups - grouped))
    if misc_groups:
        sections.append(("misc", "Misc", "Other tools", misc_groups))
    return sections


def groups_for_tool_sections(manifest: Manifest, selected_sections: set[str]) -> set[str]:
    """All package groups belonging to the selected tool sections."""
    groups: set[str] = set()
    for section_id, _name, _description, section_groups in available_tool_sections(manifest):
        if section_id in selected_sections:
            groups.update(section_groups)
    return groups


def packages_for_groups(manifest: Manifest, groups: set[str]) -> list[Package]:
    """Every package that belongs to at least one of ``groups``."""
    return [package for package in manifest.packages if set(package.groups) & groups]


def package_selection(
    manifest: Manifest, selected_package_names: set[str]
) -> tuple[list[str], list[str]]:
    """Resolve a chosen set of package names into ``(groups, names)``.

    Names and groups are returned in manifest order. Groups include every group
    of each selected package so dependent setup/plugin phases follow the actual
    package choices.
    """
    selected_names = [p.name for p in manifest.packages if p.name in selected_package_names]
    selected_groups: list[str] = []
    for package in manifest.packages:
        if package.name not in selected_package_names:
            continue
        selected_groups.extend(g for g in package.groups if g not in selected_groups)
    return selected_groups, selected_names
