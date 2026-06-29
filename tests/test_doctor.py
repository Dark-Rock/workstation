"""Tests for ``wkst doctor`` package presence checks."""

from __future__ import annotations

from pathlib import Path

from wkst.commands import doctor
from wkst.manifest import Manifest, Package
from wkst.platform import OS, Arch, PlatformInfo


class _BackendStub:
    def __init__(self, *, available: bool, installed: bool) -> None:
        self._available = available
        self._installed = installed
        self.calls: list[tuple[str, dict[str, object]]] = []

    def is_available(self, _: PlatformInfo) -> bool:
        return self._available

    def is_installed(self, ident: str, **kwargs: object) -> bool:
        self.calls.append((ident, kwargs))
        return self._installed


def test_check_packages_uses_backend_state_for_casks(monkeypatch) -> None:
    platform = PlatformInfo(os=OS.MACOS, arch=Arch.ARM64, brew_prefix=None, home=Path.home())
    backend = _BackendStub(available=True, installed=True)
    monkeypatch.setattr(doctor, "all_backends", lambda: {"brew": backend})
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)

    manifest = Manifest(
        description="x",
        updated="y",
        packages=(
            Package(
                name="ghostty",
                brew="ghostty",
                brew_type="cask",
                groups=frozenset({"terminal"}),
                platforms=frozenset({OS.MACOS}),
            ),
        ),
        claude_plugins=(),
    )

    checks = doctor._check_packages(manifest, platform)

    assert checks[0].ok
    assert backend.calls == [("ghostty", {"brew_type": "cask"})]


def test_check_packages_font_present_via_font_dir(monkeypatch, tmp_path) -> None:
    """Fonts are detected by a matching file in a font dir, not the package mgr."""
    platform = PlatformInfo(os=OS.MACOS, arch=Arch.ARM64, brew_prefix=None, home=Path.home())
    (tmp_path / "FiraCodeNerdFont-Regular.ttf").write_text("")
    monkeypatch.setattr(doctor, "_font_dirs", lambda _: [tmp_path])
    backend = _BackendStub(available=True, installed=False)
    monkeypatch.setattr(doctor, "all_backends", lambda: {"brew": backend})

    manifest = Manifest(
        description="x",
        updated="y",
        packages=(
            Package(
                name="font-fira-code-nerd-font",
                brew="font-fira-code-nerd-font",
                brew_type="cask",
                groups=frozenset({"fonts"}),
                platforms=frozenset({OS.MACOS}),
            ),
        ),
        claude_plugins=(),
    )

    checks = doctor._check_packages(manifest, platform)

    assert checks[0].ok
    # Fonts must NOT consult the package-manager backend.
    assert backend.calls == []


def test_check_packages_font_missing_when_absent(monkeypatch, tmp_path) -> None:
    platform = PlatformInfo(os=OS.MACOS, arch=Arch.ARM64, brew_prefix=None, home=Path.home())
    monkeypatch.setattr(doctor, "_font_dirs", lambda _: [tmp_path])  # empty dir
    monkeypatch.setattr(
        doctor, "all_backends", lambda: {"brew": _BackendStub(available=True, installed=False)}
    )

    manifest = Manifest(
        description="x",
        updated="y",
        packages=(
            Package(
                name="font-fira-code-nerd-font",
                brew="font-fira-code-nerd-font",
                brew_type="cask",
                groups=frozenset({"fonts"}),
                platforms=frozenset({OS.MACOS}),
            ),
        ),
        claude_plugins=(),
    )

    checks = doctor._check_packages(manifest, platform)

    assert not checks[0].ok
    assert "font-fira-code-nerd-font" in checks[0].detail


def test_check_packages_falls_back_to_binary_when_backend_unavailable(monkeypatch) -> None:
    platform = PlatformInfo(os=OS.MACOS, arch=Arch.ARM64, brew_prefix=None, home=Path.home())
    backend = _BackendStub(available=False, installed=False)
    monkeypatch.setattr(doctor, "all_backends", lambda: {"brew": backend})
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/fake/{name}")

    manifest = Manifest(
        description="x",
        updated="y",
        packages=(
            Package(
                name="fake-tool",
                binary="fake-bin",
                brew="fake-tool",
                groups=frozenset({"dev"}),
                platforms=frozenset({OS.MACOS}),
            ),
        ),
        claude_plugins=(),
    )

    checks = doctor._check_packages(manifest, platform)

    assert checks[0].ok
    assert backend.calls == []


def test_check_packages_marks_missing_when_backend_unavailable_and_binary_absent(
    monkeypatch,
) -> None:
    platform = PlatformInfo(os=OS.MACOS, arch=Arch.ARM64, brew_prefix=None, home=Path.home())
    backend = _BackendStub(available=False, installed=False)
    monkeypatch.setattr(doctor, "all_backends", lambda: {"brew": backend})
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)

    manifest = Manifest(
        description="x",
        updated="y",
        packages=(
            Package(
                name="fake-tool",
                binary="fake-bin",
                brew="fake-tool",
                groups=frozenset({"dev"}),
                platforms=frozenset({OS.MACOS}),
            ),
        ),
        claude_plugins=(),
    )

    checks = doctor._check_packages(manifest, platform)

    assert not checks[0].ok
    assert "fake-tool" in checks[0].detail
    assert backend.calls == []


def test_check_packages_marks_missing_when_backend_available_but_not_installed(monkeypatch) -> None:
    platform = PlatformInfo(os=OS.MACOS, arch=Arch.ARM64, brew_prefix=None, home=Path.home())
    backend = _BackendStub(available=True, installed=False)
    monkeypatch.setattr(doctor, "all_backends", lambda: {"brew": backend})
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)

    manifest = Manifest(
        description="x",
        updated="y",
        packages=(
            Package(
                name="fake-tool",
                binary="fake-bin",
                brew="fake-tool",
                groups=frozenset({"dev"}),
                platforms=frozenset({OS.MACOS}),
            ),
        ),
        claude_plugins=(),
    )

    checks = doctor._check_packages(manifest, platform)

    assert not checks[0].ok
    assert "fake-tool" in checks[0].detail
    assert backend.calls == [("fake-tool", {})]
