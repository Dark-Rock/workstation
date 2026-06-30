"""Tests for wkst.manifest."""

from __future__ import annotations

from pathlib import Path

import pytest

from wkst import install_menu, selection
from wkst.manifest import Manifest, ManifestError, load
from wkst.platform import OS, Arch, PlatformInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
MAC = PlatformInfo(os=OS.MACOS, arch=Arch.ARM64, brew_prefix=None, home=Path.home())
LIN = PlatformInfo(os=OS.LINUX_DEBIAN, arch=Arch.X86_64, brew_prefix=None, home=Path.home())
WSL = PlatformInfo(
    os=OS.LINUX_DEBIAN,
    arch=Arch.X86_64,
    brew_prefix=None,
    home=Path.home(),
    is_wsl=True,
)


@pytest.fixture
def manifest() -> Manifest:
    return load(REPO_ROOT)


def test_manifest_loads(manifest: Manifest) -> None:
    assert manifest.packages, "expected at least one package"
    assert manifest.description


def test_unique_package_names(manifest: Manifest) -> None:
    names = [p.name for p in manifest.packages]
    assert len(names) == len(set(names))


def test_every_package_has_a_backend(manifest: Manifest) -> None:
    for p in manifest.packages:
        assert any([p.brew, p.apt, p.cargo, p.npm, p.pipx]), p.name


def test_every_package_resolves_on_at_least_one_platform(manifest: Manifest) -> None:
    for p in manifest.packages:
        if not p.applies_to(MAC) and not p.applies_to(LIN):
            pytest.fail(f"{p.name}: not applicable to any platform")
        for plat in (MAC, LIN):
            if p.applies_to(plat):
                resolved = p.resolved_backend(plat)
                assert resolved, f"{p.name}: no backend resolves on {plat.os}"


def test_groups_consistent(manifest: Manifest) -> None:
    # Every package must have at least one group (so --groups always works).
    for p in manifest.packages:
        assert p.groups, f"{p.name}: must declare at least one group"


def test_install_profiles_reference_existing_groups(manifest: Manifest) -> None:
    assert {"minimal", "developer", "sre", "full"}.issubset(manifest.profiles)

    known_groups = set(manifest.all_groups())
    for name, groups in manifest.available_profiles():
        if groups is None:
            assert name == "full"
            continue
        assert groups, f"profile {name}: must include at least one group"
        assert set(groups) <= known_groups


def test_package_menu_sections_are_coarse(manifest: Manifest) -> None:
    sections = selection.available_tool_sections(manifest)

    assert [section_id for section_id, *_rest in sections] == [
        "dev",
        "ops",
        "tools",
        "misc",
    ]
    assert [name for _section_id, name, *_rest in sections] == [
        "Dev",
        "Ops",
        "Tools",
        "Misc",
    ]


def test_package_section_menus_partition_packages(manifest: Manifest) -> None:
    sections = selection.available_tool_sections(manifest)
    selected_sections = {section_id for section_id, *_rest in sections}

    menu_packages = [
        package.name
        for section_id, *_rest in sections
        for package in install_menu._packages_for_section_menu(
            manifest, section_id, selected_sections, sections
        )
    ]

    assert set(menu_packages) == {package.name for package in manifest.packages}
    assert len(menu_packages) == len(set(menu_packages))


def test_full_profile_means_all_groups(manifest: Manifest) -> None:
    assert manifest.groups_for_profile("full") is None


def test_wsl_excludes_wsl_incompatible_packages(manifest: Manifest) -> None:
    native_linux = {p.name for p in manifest.for_platform(LIN)}
    wsl_linux = {p.name for p in manifest.for_platform(WSL)}

    assert "docker.io" in native_linux
    assert "docker.io" not in wsl_linux
    assert wsl_linux < native_linux


def test_install_pipeline_can_filter_individual_packages(manifest: Manifest) -> None:
    from wkst.install_pipeline import run_pipeline

    outcomes = run_pipeline(
        manifest=manifest,
        platform_info=MAC,
        groups=["git", "editor"],
        package_names=["gh"],
        operation=lambda _backend, _ident, _kwargs, _dry_run: True,
        operation_label="test",
        dry_run=True,
    )

    assert [outcome.package for outcome in outcomes] == ["gh"]


def test_invalid_toml_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "packages.toml"
    bad.write_text('[meta]\ndescription = "x"\n[[package]]\nname = "broken"\n')
    with pytest.raises(ManifestError):
        load(tmp_path)
