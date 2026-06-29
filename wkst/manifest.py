"""Parse and resolve ``packages.toml``.

The manifest is the single source of truth for everything `wkst` installs.
It is intentionally cross-platform: each ``[[package]]`` entry declares which
backends it can be installed from on which OS, and resolution picks the
preferred one at install time.
"""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from wkst.platform import OS, PlatformInfo

# Backends in priority order: when multiple are declared for the current
# platform, the first available one wins. Backed by wkst.backends.*.
BACKEND_PRIORITY: dict[OS, tuple[str, ...]] = {
    OS.MACOS: ("brew", "cargo", "npm", "pipx"),
    OS.LINUX_DEBIAN: ("apt", "cargo", "npm", "pipx"),
    OS.UNSUPPORTED: (),
}

# Backends that take a brew-style "type" qualifier (formula vs cask).
_BREW_TYPES = frozenset({"formula", "cask"})


@dataclass(frozen=True)
class Package:
    """A single installable tool, possibly available via several backends."""

    name: str
    binary: str | None = None
    groups: frozenset[str] = field(default_factory=frozenset)
    platforms: frozenset[OS] = field(default_factory=frozenset)
    exclude_variants: frozenset[str] = field(default_factory=frozenset)
    description: str | None = None

    # Per-backend identifiers (None when unavailable on that backend).
    brew: str | None = None
    brew_type: str = "formula"
    apt: str | None = None
    cargo: str | None = None
    npm: str | None = None
    pipx: str | None = None

    def applies_to(self, platform_info: PlatformInfo) -> bool:
        if self.exclude_variants & platform_info.variants:
            return False
        if not self.platforms:
            return True
        return platform_info.os in self.platforms

    def resolved_backend(self, platform_info: PlatformInfo) -> tuple[str, str] | None:
        """Pick the preferred backend for this platform.

        Returns a ``(backend_name, package_id)`` tuple, or ``None`` if this
        package has no installable backend on the current platform.
        """
        if not self.applies_to(platform_info):
            return None
        for backend in BACKEND_PRIORITY.get(platform_info.os, ()):
            ident = getattr(self, backend)
            if ident:
                return backend, ident
        return None


@dataclass(frozen=True)
class ClaudePlugin:
    name: str
    source: str = "marketplace"


@dataclass(frozen=True)
class Manifest:
    description: str
    updated: str
    packages: tuple[Package, ...]
    claude_plugins: tuple[ClaudePlugin, ...]
    profiles: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def for_platform(self, platform_info: PlatformInfo) -> tuple[Package, ...]:
        return tuple(p for p in self.packages if p.applies_to(platform_info))

    def in_groups(
        self, packages: tuple[Package, ...], groups: list[str] | None
    ) -> tuple[Package, ...]:
        if not groups:
            return packages
        wanted = set(groups)
        return tuple(p for p in packages if wanted & p.groups)

    def all_groups(self) -> list[str]:
        seen: set[str] = set()
        for p in self.packages:
            seen.update(p.groups)
        return sorted(seen)

    def available_profiles(self) -> list[tuple[str, list[str] | None]]:
        """Return install profiles, expanding ``*`` to mean all groups."""
        out: list[tuple[str, list[str] | None]] = []
        for name, groups in self.profiles.items():
            out.append((name, None if groups == ("*",) else list(groups)))
        return out

    def groups_for_profile(self, profile: str) -> list[str] | None:
        """Resolve a profile name to package groups, or ``None`` for all packages."""
        try:
            groups = self.profiles[profile]
        except KeyError as exc:
            known = ", ".join(sorted(self.profiles))
            raise ManifestError(
                f"Unknown install profile {profile!r}; valid profiles: {known}"
            ) from exc
        if groups == ("*",):
            return None
        return list(groups)


class ManifestError(Exception):
    """Raised when the manifest fails validation."""


def manifest_path(repo_root: Path) -> Path:
    return repo_root / "packages.toml"


def load(repo_root: Path) -> Manifest:
    path = manifest_path(repo_root)
    if not path.is_file():
        raise ManifestError(f"packages.toml not found at {path}")

    try:
        with path.open("rb") as fh:
            raw = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(f"packages.toml is not valid TOML: {exc}") from exc

    meta = raw.get("meta", {})
    description = str(meta.get("description", ""))
    updated = str(meta.get("updated", ""))

    package_dicts = raw.get("package", [])
    if not isinstance(package_dicts, list):
        raise ManifestError("Top-level `package` must be an array of tables.")

    packages: list[Package] = []
    seen_names: set[str] = set()
    for idx, entry in enumerate(package_dicts):
        if not isinstance(entry, dict):
            raise ManifestError(f"package[{idx}] is not a table.")
        pkg = _parse_package(entry, idx)
        if pkg.name in seen_names:
            raise ManifestError(f"Duplicate package name: {pkg.name!r}")
        seen_names.add(pkg.name)
        packages.append(pkg)

    profiles = _parse_profiles(raw.get("profiles", {}))

    claude_section = raw.get("plugins", {}).get("claude", {})
    if not isinstance(claude_section, dict):
        raise ManifestError("[plugins.claude] must be a table.")
    claude_plugins = tuple(
        ClaudePlugin(name=name, source=str(source)) for name, source in claude_section.items()
    )

    return Manifest(
        description=description,
        updated=updated,
        packages=tuple(packages),
        claude_plugins=claude_plugins,
        profiles=profiles,
    )


def _parse_profiles(raw_profiles: object) -> dict[str, tuple[str, ...]]:
    if not isinstance(raw_profiles, dict):
        raise ManifestError("[profiles] must be a table of profile = [groups].")

    profiles: dict[str, tuple[str, ...]] = {}
    for name, raw_groups in raw_profiles.items():
        if not isinstance(raw_groups, list):
            raise ManifestError(f"profile {name!r}: value must be a list of group names.")
        groups = tuple(str(g).strip() for g in raw_groups if str(g).strip())
        if not groups:
            raise ManifestError(f"profile {name!r}: must include at least one group or '*'.")
        if "*" in groups and groups != ("*",):
            raise ManifestError(f"profile {name!r}: '*' must be the only entry when used.")
        profiles[str(name)] = groups
    return profiles


def _parse_package(entry: dict, idx: int) -> Package:
    try:
        name = str(entry["name"])
    except KeyError as exc:
        raise ManifestError(f"package[{idx}] missing required field 'name'.") from exc

    brew_type = str(entry.get("brew_type", "formula"))
    if brew_type not in _BREW_TYPES:
        raise ManifestError(
            f"package[{idx}] {name!r}: brew_type must be one of {sorted(_BREW_TYPES)}"
        )

    raw_platforms = entry.get("platforms")
    platforms: frozenset[OS]
    if raw_platforms is None:
        platforms = frozenset()
    else:
        if not isinstance(raw_platforms, list):
            raise ManifestError(f"{name!r}: 'platforms' must be a list of strings.")
        try:
            platforms = frozenset(OS(p) for p in raw_platforms)
        except ValueError as exc:
            valid = ", ".join(sorted(o.value for o in OS if o is not OS.UNSUPPORTED))
            raise ManifestError(f"{name!r}: unknown platform; valid: {valid}") from exc

    raw_groups = entry.get("groups", [])
    if not isinstance(raw_groups, list):
        raise ManifestError(f"{name!r}: 'groups' must be a list of strings.")
    groups = frozenset(str(g) for g in raw_groups)

    pkg = Package(
        name=name,
        binary=_opt_str(entry.get("binary")),
        groups=groups,
        platforms=platforms,
        exclude_variants=_parse_string_set(entry.get("exclude_variants"), name, "exclude_variants"),
        description=_opt_str(entry.get("description")),
        brew=_opt_str(entry.get("brew")),
        brew_type=brew_type,
        apt=_opt_str(entry.get("apt")),
        cargo=_opt_str(entry.get("cargo")),
        npm=_opt_str(entry.get("npm")),
        pipx=_opt_str(entry.get("pipx")),
    )

    if not any([pkg.brew, pkg.apt, pkg.cargo, pkg.npm, pkg.pipx]):
        raise ManifestError(
            f"{name!r}: must declare at least one backend (brew/apt/cargo/npm/pipx)."
        )

    return pkg


def _parse_string_set(raw: object, package_name: str, field_name: str) -> frozenset[str]:
    if raw is None:
        return frozenset()
    if not isinstance(raw, list):
        raise ManifestError(f"{package_name!r}: '{field_name}' must be a list of strings.")
    return frozenset(str(item).strip() for item in raw if str(item).strip())


def _opt_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def main_validate(repo_root: Path) -> int:
    """Validation entry point used by ``wkst manifest validate``."""
    try:
        m = load(repo_root)
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"OK: {len(m.packages)} packages, {len(m.claude_plugins)} claude plugins")
    return 0
