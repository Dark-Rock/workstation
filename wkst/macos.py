"""macOS system defaults management.

Reads/writes macOS user defaults (via the ``defaults`` CLI) and persists a
curated snapshot in ``macos/settings.toml``.

Workflow
--------
1. Configure macOS the way you like it.
2. ``wkst macos export``  — captures current values into ``macos/settings.toml``.
3. Commit the file.
4. On a new machine: ``wkst macos apply``.
"""

from __future__ import annotations

import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from wkst.logging import log

SETTINGS_RELATIVE = Path("macos") / "settings.toml"

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Setting:
    domain: str
    key: str
    value: bool | int | float | str
    type: str  # "bool" | "int" | "float" | "string"
    description: str = field(default="")


# Curated list — used when no settings.toml exists yet.
_DEFAULTS: list[Setting] = [
    # ── Global ──────────────────────────────────────────────────────────────
    Setting(
        "NSGlobalDomain",
        "ApplePressAndHoldEnabled",
        False,
        "bool",
        "Key repeat on hold (false=repeat keys, true=accent popup)",
    ),
    Setting(
        "NSGlobalDomain",
        "KeyRepeat",
        2,
        "int",
        "Key repeat rate — lower is faster (system minimum: 2)",
    ),
    Setting(
        "NSGlobalDomain",
        "InitialKeyRepeat",
        15,
        "int",
        "Delay before key repeat starts — lower is shorter",
    ),
    Setting(
        "NSGlobalDomain",
        "AppleShowScrollBars",
        "Always",
        "string",
        "Scroll bar visibility: Always / Automatic / WhenScrolling",
    ),
    Setting("NSGlobalDomain", "NSAutomaticQuoteSubstitutionEnabled", False, "bool", "Smart quotes"),
    Setting("NSGlobalDomain", "NSAutomaticDashSubstitutionEnabled", False, "bool", "Smart dashes"),
    Setting(
        "NSGlobalDomain",
        "NSAutomaticSpellingCorrectionEnabled",
        False,
        "bool",
        "Auto-correct spelling",
    ),
    Setting(
        "NSGlobalDomain",
        "NSDocumentSaveNewDocumentsToCloud",
        False,
        "bool",
        "Save new documents to iCloud by default",
    ),
    # ── Dock ────────────────────────────────────────────────────────────────
    Setting("com.apple.dock", "autohide", True, "bool", "Auto-hide the Dock"),
    Setting(
        "com.apple.dock",
        "autohide-delay",
        0.0,
        "float",
        "Delay before Dock appears when auto-hidden (seconds)",
    ),
    Setting(
        "com.apple.dock",
        "autohide-time-modifier",
        0.5,
        "float",
        "Animation duration when Dock shows/hides",
    ),
    Setting("com.apple.dock", "tilesize", 36, "int", "Dock icon size in pixels"),
    Setting("com.apple.dock", "magnification", True, "bool", "Magnify Dock icons on hover"),
    Setting("com.apple.dock", "largesize", 128.0, "float", "Dock icon magnification size"),
    Setting(
        "com.apple.dock",
        "minimize-to-application",
        True,
        "bool",
        "Minimize windows into the application icon",
    ),
    Setting("com.apple.dock", "show-recents", False, "bool", "Show recently-used apps in the Dock"),
    Setting("com.apple.dock", "launchanim", False, "bool", "Bounce animation when launching apps"),
    Setting("com.apple.dock", "mineffect", "scale", "string", "Minimize animation: scale / genie"),
    # ── Finder ──────────────────────────────────────────────────────────────
    Setting(
        "com.apple.finder",
        "ShowPathbar",
        True,
        "bool",
        "Show path bar at the bottom of Finder windows",
    ),
    Setting(
        "com.apple.finder",
        "ShowStatusBar",
        True,
        "bool",
        "Show status bar at the bottom of Finder windows",
    ),
    Setting(
        "com.apple.finder",
        "AppleShowAllFiles",
        False,
        "bool",
        "Show hidden files (names starting with .)",
    ),
    Setting(
        "com.apple.finder",
        "FXEnableExtensionChangeWarning",
        False,
        "bool",
        "Warn when changing a file's extension",
    ),
    Setting(
        "com.apple.finder",
        "FXPreferredViewStyle",
        "Nlsv",
        "string",
        "Default view: Nlsv=list, icnv=icon, clmv=column, Flwv=gallery",
    ),
    Setting(
        "com.apple.finder",
        "FXDefaultSearchScope",
        "SCcf",
        "string",
        "Default search scope: SCcf=current folder, SCev=everywhere",
    ),
    Setting(
        "com.apple.finder",
        "_FXShowPosixPathInTitle",
        False,
        "bool",
        "Show full POSIX path in Finder title bar",
    ),
    # ── Screensaver ─────────────────────────────────────────────────────────
    Setting(
        "com.apple.screensaver",
        "askForPassword",
        1,
        "int",
        "Require password after screensaver activates (1=yes, 0=no)",
    ),
    Setting(
        "com.apple.screensaver",
        "askForPasswordDelay",
        0,
        "int",
        "Seconds before password is required after screensaver starts",
    ),
]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def settings_path(repo_root: Path) -> Path:
    return repo_root / SETTINGS_RELATIVE


def load_settings(path: Path) -> list[Setting]:
    """Return settings from *path*, or the built-in defaults if the file is absent."""
    if not path.exists():
        return list(_DEFAULTS)
    with path.open("rb") as f:
        data = tomllib.load(f)
    return [
        Setting(
            domain=entry["domain"],
            key=entry["key"],
            value=entry["value"],
            type=entry["type"],
            description=entry.get("description", ""),
        )
        for entry in data.get("setting", [])
    ]


def save_settings(path: Path, settings: list[Setting]) -> None:
    """Serialise *settings* to a ``[[setting]]``-array TOML file at *path*."""
    header = (
        "# macOS system defaults — managed by ``wkst macos export``\n"
        "# Apply with:  wkst macos apply\n"
        "# Add or remove [[setting]] blocks to control which keys are tracked.\n"
        "\n"
    )
    blocks: list[str] = []
    for s in settings:
        lines = ["[[setting]]"]
        lines.append(f'domain      = "{_esc(s.domain)}"')
        lines.append(f'key         = "{_esc(s.key)}"')
        if s.type == "bool":
            lines.append(f"value       = {'true' if s.value else 'false'}")
        elif s.type == "string":
            lines.append(f'value       = "{_esc(str(s.value))}"')
        else:
            lines.append(f"value       = {s.value}")
        lines.append(f'type        = "{s.type}"')
        if s.description:
            lines.append(f'description = "{_esc(s.description)}"')
        blocks.append("\n".join(lines))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n\n".join(blocks) + "\n")


def export(repo_root: Path, *, dry_run: bool = False) -> int:
    """Read current system defaults for all tracked keys; update settings file.

    Keys absent on this system (never explicitly set) are kept at their
    existing file value so the file stays stable across machines.
    """
    path = settings_path(repo_root)
    settings = load_settings(path)

    updated: list[Setting] = []
    n_ok = n_changed = n_skipped = n_failed = 0

    for s in settings:
        actual_type = _read_type(s.domain, s.key)

        if actual_type is None:
            log.warn(f"  missing : {s.domain}  {s.key}  (not set — keeping existing value)")
            updated.append(s)
            n_skipped += 1
            continue

        if actual_type in ("array", "dictionary", "data"):
            log.debug(f"  skip    : {s.domain}  {s.key}  (type={actual_type}, not supported)")
            updated.append(s)
            n_skipped += 1
            continue

        value = _read_value(s.domain, s.key, actual_type)
        if value is None:
            log.error(f"  fail    : {s.domain}  {s.key}  (read error)")
            updated.append(s)
            n_failed += 1
            continue

        new_s = Setting(s.domain, s.key, value, actual_type, s.description)
        updated.append(new_s)

        if value != s.value:
            log.info(f"  changed : {s.domain}  {s.key}  {s.value!r} → {value!r}")
            n_changed += 1
        else:
            log.debug(f"  same    : {s.domain}  {s.key}  = {value!r}")
            n_ok += 1

    log.success(
        f"export: {n_ok + n_changed} read ({n_changed} changed), "
        f"{n_skipped} skipped, {n_failed} failed"
    )

    if not dry_run:
        save_settings(path, updated)
        log.info(f"  written → {path.relative_to(repo_root)}")
    else:
        log.info("  (dry-run: file not written)")

    return 1 if n_failed else 0


def apply(repo_root: Path, *, dry_run: bool = False, restart_ui: bool = True) -> int:
    """Write settings from the file into macOS system defaults."""
    path = settings_path(repo_root)
    if not path.exists():
        log.error(f"apply: {path} not found — run `wkst macos export` first")
        return 1

    settings = load_settings(path)
    n_ok = n_skipped = n_failed = 0
    affected: set[str] = set()

    for s in settings:
        flag = _TYPE_FLAGS.get(s.type)
        if flag is None:
            log.warn(f"  skip    : {s.domain}  {s.key}  (unsupported type {s.type!r})")
            n_skipped += 1
            continue

        # The defaults CLI expects YES/NO for booleans.
        value_str = "YES" if s.value is True else ("NO" if s.value is False else str(s.value))
        log.info(f"  write   : {s.domain}  {s.key}  = {s.value!r}")

        if dry_run:
            n_ok += 1
            continue

        res = subprocess.run(
            ["defaults", "write", s.domain, s.key, flag, value_str],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            n_ok += 1
            affected.add(s.domain)
        else:
            log.error(f"  FAIL    : {s.domain}  {s.key}  — {res.stderr.strip()}")
            n_failed += 1

    log.success(f"apply: {n_ok} written, {n_skipped} skipped, {n_failed} failed")

    if not dry_run and restart_ui and affected:
        _restart_ui(affected)

    return 1 if n_failed else 0


def discover(
    repo_root: Path,
    *,
    domains: list[str],
    adopt: bool = False,
    dry_run: bool = False,
) -> int:
    """Discover scalar defaults keys and optionally append them to settings.toml.

    This is intentionally conservative: it only records simple scalar values that
    ``apply`` already knows how to restore. Arrays, dictionaries, and binary data
    are reported as skipped instead of being tracked automatically.
    """
    path = settings_path(repo_root)
    settings = load_settings(path)
    seen = {(s.domain, s.key) for s in settings}
    discovered: list[Setting] = []
    n_existing = n_skipped = n_failed = 0

    for domain in _expand_domains(domains):
        keys = _domain_keys(domain)
        if not keys:
            log.warn(f"  empty   : {domain}  (no readable keys)")
            continue

        for key in keys:
            if (domain, key) in seen:
                n_existing += 1
                continue

            actual_type = _read_type(domain, key)
            if actual_type is None:
                log.warn(f"  missing : {domain}  {key}  (type unreadable)")
                n_failed += 1
                continue
            if actual_type not in _TYPE_FLAGS:
                log.debug(f"  skip    : {domain}  {key}  (type={actual_type}, not supported)")
                n_skipped += 1
                continue

            value = _read_value(domain, key, actual_type)
            if value is None:
                log.error(f"  fail    : {domain}  {key}  (read error)")
                n_failed += 1
                continue

            setting = Setting(domain, key, value, actual_type, "Discovered from current Mac")
            discovered.append(setting)
            seen.add((domain, key))
            log.info(f"  new     : {domain}  {key}  = {value!r} ({actual_type})")

    log.success(
        f"discover: {len(discovered)} new, {n_existing} already tracked, "
        f"{n_skipped} skipped, {n_failed} failed"
    )

    if not adopt:
        log.info("  preview only: rerun with --adopt to append new scalar settings")
        return 1 if n_failed else 0

    if dry_run:
        log.info("  (dry-run: file not written)")
        return 1 if n_failed else 0

    save_settings(path, settings + discovered)
    log.info(f"  written → {path.relative_to(repo_root)}")
    return 1 if n_failed else 0


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

_TYPE_FLAGS: dict[str, str] = {
    "bool": "-bool",
    "int": "-int",
    "float": "-float",
    "string": "-string",
}

_TYPE_MAP: dict[str, str] = {
    "Type is boolean": "bool",
    "Type is integer": "int",
    "Type is float": "float",
    "Type is string": "string",
    "Type is array": "array",
    "Type is dictionary": "dictionary",
    "Type is data": "data",
}


def _expand_domains(domains: list[str]) -> list[str]:
    if domains != ["all"]:
        return domains

    res = subprocess.run(["defaults", "domains"], capture_output=True, text=True)
    if res.returncode != 0:
        log.error(f"discover: cannot read defaults domains — {res.stderr.strip()}")
        return []
    return sorted(d.strip() for d in res.stdout.split(",") if d.strip())


def _domain_keys(domain: str) -> list[str]:
    res = subprocess.run(["defaults", "read", domain], capture_output=True, text=True)
    if res.returncode != 0:
        return []
    return _parse_defaults_keys(res.stdout)


def _parse_defaults_keys(raw: str) -> list[str]:
    """Return top-level keys from ``defaults read <domain>`` dictionary output."""
    keys: list[str] = []
    depth = 0
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "{":
            depth += 1
            continue
        if stripped in ("}", ");"):
            depth = max(0, depth - 1)
            continue
        if depth == 1 and " = " in stripped:
            key = stripped.split(" = ", 1)[0].strip().strip('"')
            if key:
                keys.append(key)
        depth += stripped.count("(") + stripped.count("{")
        depth -= stripped.count(")") + stripped.count("}")
        depth = max(0, depth)
    return keys


def _read_type(domain: str, key: str) -> str | None:
    res = subprocess.run(
        ["defaults", "read-type", domain, key],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        return None
    return _TYPE_MAP.get(res.stdout.strip())


def _read_value(domain: str, key: str, type_hint: str) -> bool | int | float | str | None:
    res = subprocess.run(
        ["defaults", "read", domain, key],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        return None
    raw = res.stdout.strip()
    if type_hint == "bool":
        return raw == "1"
    if type_hint == "int":
        try:
            return int(raw)
        except ValueError:
            return None
    if type_hint == "float":
        try:
            return float(raw)
        except ValueError:
            return None
    return raw  # string


def _restart_ui(domains: set[str]) -> None:
    if "com.apple.dock" in domains:
        log.info("  → restarting Dock")
        subprocess.run(["killall", "Dock"], capture_output=True)
    if "com.apple.finder" in domains:
        log.info("  → restarting Finder")
        subprocess.run(["killall", "Finder"], capture_output=True)
    if "NSGlobalDomain" in domains:
        log.info("  → note: some NSGlobalDomain changes require logout to fully apply")


def _esc(s: str) -> str:
    """Minimal TOML string escaping (backslash and double-quote)."""
    return s.replace("\\", "\\\\").replace('"', '\\"')
