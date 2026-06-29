"""Tests for platform and WSL detection helpers."""

from __future__ import annotations

from pathlib import Path

from wkst import platform as wkst_platform
from wkst.platform import OS, Arch, PlatformInfo


def test_platform_variants_include_wsl_only_when_detected() -> None:
    native = PlatformInfo(
        os=OS.LINUX_DEBIAN,
        arch=Arch.X86_64,
        brew_prefix=None,
        home=Path.home(),
    )
    wsl = PlatformInfo(
        os=OS.LINUX_DEBIAN,
        arch=Arch.X86_64,
        brew_prefix=None,
        home=Path.home(),
        is_wsl=True,
        wsl_distro="Ubuntu",
    )

    assert native.variants == frozenset()
    assert wsl.variants == frozenset({"wsl"})


def test_detect_wsl_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")

    assert wkst_platform._detect_wsl() == (True, "Ubuntu")
