"""OS, architecture, and PATH detection."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class OS(StrEnum):
    MACOS = "macos"
    LINUX_DEBIAN = "linux-debian"
    UNSUPPORTED = "unsupported"


class Arch(StrEnum):
    ARM64 = "arm64"
    X86_64 = "x86_64"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PlatformInfo:
    os: OS
    arch: Arch
    brew_prefix: Path | None
    home: Path
    is_wsl: bool = False
    wsl_distro: str | None = None

    @property
    def is_macos(self) -> bool:
        return self.os is OS.MACOS

    @property
    def is_linux(self) -> bool:
        return self.os is OS.LINUX_DEBIAN

    @property
    def variants(self) -> frozenset[str]:
        variants: set[str] = set()
        if self.is_wsl:
            variants.add("wsl")
        return frozenset(variants)


def _detect_arch() -> Arch:
    machine = platform.machine().lower()
    if machine in {"arm64", "aarch64"}:
        return Arch.ARM64
    if machine in {"x86_64", "amd64"}:
        return Arch.X86_64
    return Arch.UNKNOWN


def _detect_brew_prefix(arch: Arch) -> Path | None:
    """Honor an existing brew on PATH first, then fall back to default prefix."""
    found = shutil.which("brew")
    if found:
        try:
            out = subprocess.check_output([found, "--prefix"], text=True).strip()
            if out:
                return Path(out)
        except (subprocess.CalledProcessError, OSError):
            pass
    candidate = Path("/opt/homebrew") if arch is Arch.ARM64 else Path("/usr/local")
    return candidate if candidate.exists() else None


def _detect_os() -> OS:
    if sys.platform == "darwin":
        return OS.MACOS
    if sys.platform.startswith("linux"):
        # Only apt-based distros are supported in phase 1.
        if shutil.which("apt-get") is not None:
            return OS.LINUX_DEBIAN
    return OS.UNSUPPORTED


def _detect_wsl() -> tuple[bool, str | None]:
    distro = os.environ.get("WSL_DISTRO_NAME")
    if distro:
        return True, distro
    for path in (Path("/proc/sys/kernel/osrelease"), Path("/proc/version")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if "microsoft" in text or "wsl" in text:
            return True, distro
    return False, None


def detect() -> PlatformInfo:
    arch = _detect_arch()
    os_kind = _detect_os()
    brew_prefix = _detect_brew_prefix(arch) if os_kind is OS.MACOS else None
    is_wsl, wsl_distro = _detect_wsl() if os_kind is OS.LINUX_DEBIAN else (False, None)
    return PlatformInfo(
        os=os_kind,
        arch=arch,
        brew_prefix=brew_prefix,
        home=Path("~").expanduser(),
        is_wsl=is_wsl,
        wsl_distro=wsl_distro,
    )


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None
