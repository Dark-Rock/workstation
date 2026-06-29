"""Tests for wkst.commands.manifest helpers."""

from __future__ import annotations

from pathlib import Path

from wkst.commands import manifest as cmd_manifest

MINIMAL_MANIFEST = """[meta]
description = "test manifest"
updated = "2026-05-19"

[[package]]
name = "git"
brew = "git"
apt = "git"
groups = ["core"]

[plugins.claude]
"""


def test_add_package_writes_valid_package_before_plugin_section(tmp_path: Path) -> None:
    manifest_path = tmp_path / "packages.toml"
    manifest_path.write_text(MINIMAL_MANIFEST)

    rc = cmd_manifest.add_package(
        repo_root=tmp_path,
        name="taplo",
        brew="taplo",
        brew_type="formula",
        apt=None,
        cargo="taplo-cli",
        npm=None,
        pipx=None,
        binary=None,
        groups=["quality", "dev"],
        platforms=[],
        description="TOML formatter/language server",
        dry_run=False,
    )

    assert rc == 0
    text = manifest_path.read_text()
    assert 'name = "taplo"' in text
    assert text.index('name = "taplo"') < text.index("[plugins.claude]")

    loaded = cmd_manifest.load(tmp_path)
    added = next(p for p in loaded.packages if p.name == "taplo")
    assert added.brew == "taplo"
    assert added.cargo == "taplo-cli"
    assert added.groups == frozenset({"quality", "dev"})


def test_rendered_tools_doc_is_current() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    expected = cmd_manifest._render_md(cmd_manifest.load(repo_root))
    actual = (repo_root / "TOOLS.md").read_text()

    assert actual == expected
