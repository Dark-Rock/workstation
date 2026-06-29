"""Plugin/extension installers for stuff outside any package manager.

- TPM (Tmux Plugin Manager) and its plugins
- LazyVim plugins (Lazy sync + Treesitter update)
- Zinit (zsh plugin manager bootstrap; .zshrc handles plugin loading)
- Claude Code plugins (delegated to ClaudeBackend)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wkst.backends import ClaudeBackend
from wkst.logging import log
from wkst.manifest import Manifest
from wkst.platform import PlatformInfo, command_exists
from wkst.process import run

TPM_REPO = "https://github.com/tmux-plugins/tpm"
ZINIT_REPO = "https://github.com/zdharma-continuum/zinit.git"
# Community cheatsheets that auto-populate navi (Ctrl-G) with hundreds of
# default-command recipes (git, docker, kubectl, tar, gpg, ...). Cloned into
# navi's data cheats dir; the curated workstation cheats live in dotfiles.
NAVI_CHEATS_REPO = "https://github.com/denisidoro/cheats"

# Single source of truth for the Mason tool list, shared with the Neovim config
# (lua/plugins/mason-tools.lua reads the same file). Keeping one list avoids the
# two drifting apart.
MASON_TOOLS_FILE = Path("dotfiles/config/.config/nvim/mason-tools.txt")


def read_mason_tools(repo_root: Path) -> list[str]:
    """Parse the shared mason-tools.txt (one package per line, ``#`` comments)."""
    path = repo_root / MASON_TOOLS_FILE
    if not path.is_file():
        log.warn(f"plugins: mason tool list not found at {path}")
        return []
    tools: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            tools.append(stripped)
    return tools


@dataclass
class PluginResult:
    name: str
    ok: bool
    detail: str = ""


def install_all(
    *,
    repo_root: Path,
    manifest: Manifest,
    platform_info: PlatformInfo,
    groups: list[str] | None,
    dry_run: bool,
) -> list[PluginResult]:
    selected = set(groups) if groups is not None else None
    results: list[PluginResult] = []
    if _wants(selected, "terminal"):
        results.append(_ensure_tpm(platform_info, dry_run=dry_run))
        results.append(_run_tpm_install(platform_info, dry_run=dry_run))
    if _wants(selected, "shell"):
        results.append(_ensure_zinit(platform_info, dry_run=dry_run))
    if _wants(selected, "shell") or _wants(selected, "search"):
        results.append(_ensure_navi_cheats(platform_info, dry_run=dry_run))
    if _wants(selected, "editor"):
        results.append(_lazyvim_sync(repo_root=repo_root, dry_run=dry_run))
    if _wants(selected, "ai"):
        results.extend(_install_claude_plugins(manifest, dry_run=dry_run))
    return results


def _wants(selected: set[str] | None, group: str) -> bool:
    return selected is None or group in selected


def update_all(
    *,
    repo_root: Path,
    manifest: Manifest,
    platform_info: PlatformInfo,
    groups: list[str] | None,
    dry_run: bool,
) -> list[PluginResult]:
    selected = set(groups) if groups is not None else None
    results: list[PluginResult] = []
    if _wants(selected, "terminal"):
        results.append(_update_tpm(platform_info, dry_run=dry_run))
        results.append(_run_tpm_update(platform_info, dry_run=dry_run))
    if _wants(selected, "shell"):
        results.append(_update_zinit(platform_info, dry_run=dry_run))
    if _wants(selected, "shell") or _wants(selected, "search"):
        results.append(_update_navi_cheats(platform_info, dry_run=dry_run))
    if _wants(selected, "editor"):
        results.append(_lazyvim_sync(repo_root=repo_root, dry_run=dry_run))
    if _wants(selected, "ai"):
        results.extend(_update_claude_plugins(manifest, dry_run=dry_run))
    return results


# --- tmux / TPM --------------------------------------------------------------


def _tpm_dir(platform_info: PlatformInfo) -> Path:
    return platform_info.home / ".tmux" / "plugins" / "tpm"


def _ensure_tpm(platform_info: PlatformInfo, *, dry_run: bool) -> PluginResult:
    target = _tpm_dir(platform_info)
    if (target / ".git").is_dir():
        return PluginResult("tpm", True, "already cloned")
    log.info(f"plugins: cloning TPM into {target}")
    if dry_run:
        return PluginResult("tpm", True, "dry-run")
    target.parent.mkdir(parents=True, exist_ok=True)
    ok = run(["git", "clone", "--depth=1", TPM_REPO, str(target)], capture=False).ok
    return PluginResult("tpm", ok)


def _update_tpm(platform_info: PlatformInfo, *, dry_run: bool) -> PluginResult:
    target = _tpm_dir(platform_info)
    if not (target / ".git").is_dir():
        return _ensure_tpm(platform_info, dry_run=dry_run)
    log.info(f"plugins: updating TPM in {target}")
    ok = run(["git", "-C", str(target), "pull", "--ff-only"], dry_run=dry_run).ok
    return PluginResult("tpm", ok)


def _run_tpm_install(platform_info: PlatformInfo, *, dry_run: bool) -> PluginResult:
    """Headless TPM plugin install (no tmux server required)."""
    script = _tpm_dir(platform_info) / "bin" / "install_plugins"
    if not script.is_file():
        return PluginResult("tpm-plugins", True, "tpm not installed yet")
    log.info("plugins: TPM install_plugins")
    ok = run([str(script)], dry_run=dry_run, capture=False).ok
    return PluginResult("tpm-plugins", ok)


def _run_tpm_update(platform_info: PlatformInfo, *, dry_run: bool) -> PluginResult:
    script = _tpm_dir(platform_info) / "bin" / "update_plugins"
    if not script.is_file():
        return PluginResult("tpm-plugins", True, "tpm not installed yet")
    log.info("plugins: TPM update_plugins all")
    ok = run([str(script), "all"], dry_run=dry_run, capture=False).ok
    return PluginResult("tpm-plugins", ok)


# --- zsh / Zinit -------------------------------------------------------------


def _zinit_dir(platform_info: PlatformInfo) -> Path:
    return platform_info.home / ".local" / "share" / "zinit" / "zinit.git"


def _ensure_zinit(platform_info: PlatformInfo, *, dry_run: bool) -> PluginResult:
    target = _zinit_dir(platform_info)
    if (target / ".git").is_dir():
        return PluginResult("zinit", True, "already cloned")
    log.info(f"plugins: cloning Zinit into {target}")
    if dry_run:
        return PluginResult("zinit", True, "dry-run")
    target.parent.mkdir(parents=True, exist_ok=True)
    ok = run(["git", "clone", "--depth=1", ZINIT_REPO, str(target)], capture=False).ok
    return PluginResult("zinit", ok)


def _update_zinit(platform_info: PlatformInfo, *, dry_run: bool) -> PluginResult:
    target = _zinit_dir(platform_info)
    if not (target / ".git").is_dir():
        return _ensure_zinit(platform_info, dry_run=dry_run)
    log.info("plugins: updating Zinit")
    ok = run(["git", "-C", str(target), "pull", "--ff-only"], dry_run=dry_run).ok
    if not ok:
        return PluginResult("zinit", False)
    # `zinit self-update` and `zinit update --all` need an interactive zsh; the
    # next interactive shell will pick up the new repo. We deliberately skip
    # spawning zsh here to avoid hanging in CI.
    return PluginResult("zinit", True)


# --- navi community cheats ---------------------------------------------------


def _navi_cheats_dir(platform_info: PlatformInfo) -> Path:
    # navi's default data cheats dir; the dir name mirrors `navi repo add`.
    return platform_info.home / ".local" / "share" / "navi" / "cheats" / "denisidoro__cheats"


def _ensure_navi_cheats(platform_info: PlatformInfo, *, dry_run: bool) -> PluginResult:
    """Clone the community cheats so navi (Ctrl-G) is pre-populated.

    We clone directly instead of ``navi repo add`` because the latter opens an
    interactive fzf picker that would hang headless/CI runs.
    """
    if not command_exists("navi"):
        return PluginResult("navi-cheats", True, "navi not installed")
    target = _navi_cheats_dir(platform_info)
    if (target / ".git").is_dir():
        return PluginResult("navi-cheats", True, "already cloned")
    log.info(f"plugins: cloning navi community cheats into {target}")
    if dry_run:
        return PluginResult("navi-cheats", True, "dry-run")
    target.parent.mkdir(parents=True, exist_ok=True)
    ok = run(["git", "clone", "--depth=1", NAVI_CHEATS_REPO, str(target)], capture=False).ok
    return PluginResult("navi-cheats", ok)


def _update_navi_cheats(platform_info: PlatformInfo, *, dry_run: bool) -> PluginResult:
    if not command_exists("navi"):
        return PluginResult("navi-cheats", True, "navi not installed")
    target = _navi_cheats_dir(platform_info)
    if not (target / ".git").is_dir():
        return _ensure_navi_cheats(platform_info, dry_run=dry_run)
    log.info("plugins: updating navi community cheats")
    ok = run(["git", "-C", str(target), "pull", "--ff-only"], dry_run=dry_run).ok
    return PluginResult("navi-cheats", ok)


# --- nvim / LazyVim ----------------------------------------------------------


def _lazyvim_sync(*, repo_root: Path, dry_run: bool) -> PluginResult:
    if not command_exists("nvim"):
        return PluginResult("lazyvim", True, "nvim not installed")
    log.info("plugins: nvim Lazy sync + Mason tools + TSUpdate")
    mason_tools = read_mason_tools(repo_root)
    cmd = ["nvim", "--headless", "+Lazy! sync"]
    # `mason.nvim` and `nvim-treesitter` are lazy-loaded, so their commands and
    # PATH setup don't exist yet right after a sync — invoking :MasonInstall
    # headless fails with `E492: Not an editor command`. Force-load both plugins
    # first: this registers :MasonInstall and puts Mason's bin dir on nvim's PATH
    # (so the `tree-sitter` CLI that nvim-treesitter's `main` branch needs to
    # compile parsers is found).
    cmd.append("+Lazy! load mason.nvim nvim-treesitter")
    if mason_tools:
        cmd.append("+MasonInstall " + " ".join(mason_tools))
        # :MasonInstall is asynchronous; block until every tool reports
        # installed, otherwise +qall quits and kills the in-flight downloads.
        # This also runs before the Treesitter update, so a Mason-provided
        # `tree-sitter` CLI is installed in time for parser compilation.
        cmd.append("+" + _mason_wait_expr(mason_tools))
    # nvim-treesitter's `main` branch dropped :TSUpdateSync; update parsers via
    # the Lua API instead and block on the returned async task (10-minute cap).
    cmd.append("+" + _treesitter_update_expr())
    cmd.append("+qall")
    ok = run(cmd, dry_run=dry_run, capture=False).ok
    return PluginResult("lazyvim", ok)


def _mason_wait_expr(tools: list[str]) -> str:
    """Build a `lua` ex-command that blocks until all Mason tools are installed.

    Waits up to 10 minutes, polling every 500ms; returns as soon as every tool
    reports installed. Unknown tool names are ignored so a typo can't hang.
    """
    tool_literals = ",".join(f"'{t}'" for t in tools)
    return (
        f"lua local r=require('mason-registry'); local t={{{tool_literals}}}; "
        "vim.wait(600000, function() for _,n in ipairs(t) do "
        "local ok,p=pcall(r.get_package,n); "
        "if ok and not p:is_installed() then return false end end "
        "return true end, 500)"
    )


def _treesitter_update_expr() -> str:
    """Build a `lua` ex-command that updates all Treesitter parsers synchronously.

    On the `main` branch `update()` returns an async task; ``:wait`` blocks until
    it finishes (capped at 10 minutes). Wrapped in ``pcall`` so a single parser
    build failure doesn't abort the whole headless run.
    """
    return (
        "lua local ok,ts=pcall(require,'nvim-treesitter.install'); "
        "if ok then pcall(function() ts.update(nil,{summary=true}):wait(600000) end) end"
    )


# --- claude code -------------------------------------------------------------


def _install_claude_plugins(manifest: Manifest, *, dry_run: bool) -> list[PluginResult]:
    if not manifest.claude_plugins:
        return []
    backend = ClaudeBackend()
    if not command_exists("claude"):
        log.warn("claude CLI not on PATH; skipping plugin install")
        return [PluginResult(p.name, True, "claude not installed") for p in manifest.claude_plugins]
    out: list[PluginResult] = []
    for plug in manifest.claude_plugins:
        log.info(f"plugins: claude install {plug.name}")
        ok = backend.install(plug.name, dry_run=dry_run)
        out.append(PluginResult(f"claude:{plug.name}", ok))
    return out


def _update_claude_plugins(manifest: Manifest, *, dry_run: bool) -> list[PluginResult]:
    if not manifest.claude_plugins:
        return []
    backend = ClaudeBackend()
    if not command_exists("claude"):
        log.warn("claude CLI not on PATH; skipping plugin update")
        return []
    log.info("plugins: claude update --all")
    ok = backend.update_all(dry_run=dry_run)
    return [PluginResult("claude:all", ok)]


def render_summary(results: list[PluginResult]) -> int:
    failed = [r for r in results if not r.ok]
    log.info("===== plugin summary =====")
    log.info(f"  ok:     {len(results) - len(failed)}")
    if failed:
        log.warn(f"  failed: {len(failed)}")
        for r in failed:
            log.warn(f"    - {r.name}: {r.detail}")
        return 1
    return 0
