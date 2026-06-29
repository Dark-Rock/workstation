"""``wkst doctor`` — quickly summarize what's installed vs. expected."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from wkst import dotfiles, render
from wkst.backends import all_backends
from wkst.logging import log
from wkst.manifest import ManifestError, load
from wkst.platform import PlatformInfo


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    fix: str | None = None  # remediation command surfaced as a fix hint


def run(*, repo_root: Path, platform_info: PlatformInfo) -> int:
    log.info(f"doctor: platform={platform_info.os.value} arch={platform_info.arch.value}")

    try:
        manifest = load(repo_root)
    except ManifestError as exc:
        log.error(str(exc))
        return 1

    checks: list[Check] = []
    checks.extend(_check_packages(manifest, platform_info))
    checks.extend(_check_dotfiles(repo_root, platform_info))
    checks.extend(_check_shell(platform_info))

    return _render(checks)


def _check_packages(manifest, platform_info: PlatformInfo) -> list[Check]:
    out: list[Check] = []
    applicable = manifest.for_platform(platform_info)
    backends = all_backends()
    missing: list[str] = []
    for p in applicable:
        # Fonts have no binary on PATH and may be installed outside the package
        # manager (e.g. dropped into ~/Library/Fonts), so check the font dirs.
        if _is_font(p):
            if not _font_present(p, platform_info):
                missing.append(f"{p.name} (font)")
            continue

        binary = p.binary or p.name
        if shutil.which(binary):
            continue

        resolved = p.resolved_backend(platform_info)
        if resolved is None:
            missing.append(f"{p.name} (no backend for {platform_info.os.value})")
            continue

        backend_name, ident = resolved
        backend = backends.get(backend_name)
        if backend is None:
            log.warn(f"doctor: unknown backend {backend_name!r} for package {p.name!r}")
            missing.append(f"{p.name} ({backend_name}?)")
            continue
        kwargs: dict[str, object] = {}
        if backend_name == "brew" and p.brew_type == "cask":
            kwargs["brew_type"] = "cask"

        installed = backend.is_available(platform_info) and backend.is_installed(ident, **kwargs)

        if not installed:
            missing.append(f"{p.name} ({backend_name}:{ident})")
    if missing:
        out.append(
            Check(
                name=f"packages: {len(applicable) - len(missing)}/{len(applicable)} present",
                ok=False,
                detail="missing: " + ", ".join(sorted(missing)),
                fix="wkst install",
            )
        )
    else:
        out.append(Check(name=f"packages: {len(applicable)}/{len(applicable)} present", ok=True))
    return out


def _is_font(pkg) -> bool:
    return "fonts" in pkg.groups or pkg.name.startswith("font-")


def _font_dirs(platform_info: PlatformInfo) -> list[Path]:
    home = platform_info.home
    if platform_info.is_macos:
        return [home / "Library" / "Fonts", Path("/Library/Fonts")]
    return [home / ".local" / "share" / "fonts", Path("/usr/share/fonts")]


def _font_present(pkg, platform_info: PlatformInfo) -> bool:
    """Heuristic: a Nerd Font cask is present if a matching file exists in a
    font directory, regardless of how it was installed (brew cask or manual)."""
    token = pkg.name.removeprefix("font-").removesuffix("-nerd-font")
    token = token.replace("-mono", "").replace("-", "")
    if not token:
        return False
    for directory in _font_dirs(platform_info):
        if not directory.is_dir():
            continue
        for entry in directory.rglob("*"):
            if not entry.is_file():
                continue
            normalized = "".join(c for c in entry.name.lower() if c.isalnum())
            if token in normalized:
                return True
    return False


def _check_dotfiles(repo_root: Path, platform_info: PlatformInfo) -> list[Check]:
    drift = dotfiles.diff_all(repo_root, platform_info.home)
    if not drift:
        return [Check(name="dotfiles: in sync", ok=True)]
    return [
        Check(
            name=f"dotfiles: {len(drift)} drifted",
            ok=False,
            detail="relink to repair (backs up real files)",
            fix="wkst sync --force",
        )
    ]


def _check_shell(platform_info: PlatformInfo) -> list[Check]:
    out: list[Check] = []
    zsh = shutil.which("zsh")
    if not zsh:
        out.append(Check(name="shell: zsh on PATH", ok=False, detail="zsh missing"))
    else:
        out.append(Check(name=f"shell: zsh -> {zsh}", ok=True))
        current = os.environ.get("SHELL", "")
        out.append(
            Check(
                name="shell: $SHELL is zsh",
                ok=current == zsh,
                detail=f"current={current!r}",
            )
        )
    omp = shutil.which("oh-my-posh")
    out.append(Check(name="shell: oh-my-posh on PATH", ok=bool(omp), detail=omp or ""))

    # Quick sanity check: TPM cloned, Zinit cloned.
    tpm = platform_info.home / ".tmux" / "plugins" / "tpm" / ".git"
    out.append(Check(name="plugins: TPM cloned", ok=tpm.is_dir(), detail=str(tpm.parent)))
    zinit = platform_info.home / ".local" / "share" / "zinit" / "zinit.git" / ".git"
    out.append(Check(name="plugins: Zinit cloned", ok=zinit.is_dir(), detail=str(zinit.parent)))
    return out


def _render(checks: list[Check]) -> int:
    failed = [c for c in checks if not c.ok]

    if render.rich_enabled():
        render.console().print(render.doctor_table(checks))
        for c in failed:
            render.print_failure(
                title=c.name,
                lines=[c.detail] if c.detail else [],
                hint=c.fix,
            )
    else:
        for c in checks:
            marker = "OK   " if c.ok else "FAIL "
            suffix = f" — {c.detail}" if c.detail else ""
            if c.ok:
                log.success(f"{marker}{c.name}{suffix}")
            else:
                log.warn(f"{marker}{c.name}{suffix}")
                if c.fix:
                    log.warn(f"       fix: {c.fix}")

    if failed:
        log.warn(f"doctor: {len(failed)} check(s) failed")
        return 1
    log.success("doctor: all checks passed")
    return 0
