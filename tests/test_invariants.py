"""Repo invariants that guard against silent drift.

- The Mason tool list has a single source (mason-tools.txt); the Neovim Lua
  config reads that file rather than carrying its own hardcoded copy.
- Every package that applies to a platform resolves to an installable backend,
  so the manifest can never declare a tool it cannot actually install.
"""

from __future__ import annotations

from pathlib import Path

from wkst import plugins
from wkst.manifest import load
from wkst.platform import OS, Arch, PlatformInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
MASON_LUA = REPO_ROOT / "dotfiles/config/.config/nvim/lua/plugins/mason-tools.lua"


def test_mason_tools_file_parses_to_nonempty_list() -> None:
    tools = plugins.read_mason_tools(REPO_ROOT)
    assert tools, "mason-tools.txt should yield a non-empty tool list"
    # Comments and blank lines must be stripped.
    assert all(t and not t.startswith("#") for t in tools)


def test_mason_lua_reads_shared_file_not_hardcoded_list() -> None:
    """Guard against re-introducing a duplicated hardcoded ensure_installed list."""
    lua = MASON_LUA.read_text(encoding="utf-8")
    assert "mason-tools.txt" in lua, "Lua config must read the shared mason-tools.txt"
    # The old duplication listed these inline; they should now live only in the txt.
    assert '"omnisharp"' not in lua
    assert '"debugpy"' not in lua


def test_every_applicable_package_resolves_a_backend() -> None:
    manifest = load(REPO_ROOT)
    platforms = [
        PlatformInfo(os=OS.MACOS, arch=Arch.ARM64, brew_prefix=None, home=Path.home()),
        PlatformInfo(os=OS.LINUX_DEBIAN, arch=Arch.ARM64, brew_prefix=None, home=Path.home()),
        PlatformInfo(
            os=OS.LINUX_DEBIAN,
            arch=Arch.ARM64,
            brew_prefix=None,
            home=Path.home(),
            is_wsl=True,
        ),
    ]
    for platform in platforms:
        unresolved = [
            p.name for p in manifest.for_platform(platform) if p.resolved_backend(platform) is None
        ]
        label = platform.os.value + ("/wsl" if platform.is_wsl else "")
        assert not unresolved, f"packages with no backend on {label}: {unresolved}"
