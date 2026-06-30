"""Idempotent bootstrap steps run before the package pipeline.

Handles the chicken-and-egg cases that backends can't:

- Homebrew install on macOS (provides ``brew`` for the brew backend).
- APT prerequisites on Linux (curl/git/build-essential).
- rustup install (provides ``cargo`` so cargo-backend tools can run).
- oh-my-posh install on Linux (no apt package).
- shell-color-scripts install (no brew/apt package; provides ``colorscript``).
"""

from __future__ import annotations

import os

from wkst.logging import log
from wkst.platform import PlatformInfo, command_exists
from wkst.process import run

_HOMEBREW_INSTALL_URL = "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
_RUSTUP_INSTALL_URL = "https://sh.rustup.rs"
_OMP_INSTALL_URL = "https://ohmyposh.dev/install.sh"
_COLORSCRIPTS_REPO = "https://gitlab.com/dwt1/shell-color-scripts.git"


def ensure_homebrew(platform_info: PlatformInfo, *, dry_run: bool) -> bool:
    if not platform_info.is_macos:
        return True
    if command_exists("brew"):
        return True
    log.info("bootstrap: installing Homebrew")
    if dry_run:
        log.info("(dry-run) would run Homebrew installer")
        return True
    cmd = f'NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL {_HOMEBREW_INSTALL_URL})"'
    return run(["bash", "-c", cmd], capture=False, retries=1).ok


def ensure_apt_prereqs(platform_info: PlatformInfo, *, dry_run: bool) -> bool:
    if not platform_info.is_linux:
        return True
    needed = [
        "curl",
        "git",
        "ca-certificates",
        "gnupg",
        "lsb-release",
        "build-essential",
    ]
    missing = [pkg for pkg in needed if not _dpkg_installed(pkg)]
    if not missing:
        return True
    log.info(f"bootstrap: installing apt prereqs: {' '.join(missing)}")
    ok = run(["sudo", "apt-get", "update"], dry_run=dry_run, capture=False).ok
    if not ok:
        return False
    return run(
        ["sudo", "apt-get", "install", "-y", *missing],
        dry_run=dry_run,
        capture=False,
        env={"DEBIAN_FRONTEND": "noninteractive"},
    ).ok


def ensure_rustup(platform_info: PlatformInfo, *, dry_run: bool) -> bool:
    """Install rustup on Linux (and run rustup update on both OSes)."""
    if not command_exists("rustup"):
        if platform_info.is_macos:
            # On macOS, brew provides rustup-init -> let the brew backend handle it.
            return True
        log.info("bootstrap: installing rustup via official installer")
        if dry_run:
            log.info("(dry-run) would install rustup")
            return True
        cmd = (
            f"curl --proto '=https' --tlsv1.2 -sSf {_RUSTUP_INSTALL_URL} | "
            "sh -s -- -y --no-modify-path --default-toolchain stable"
        )
        if not run(["bash", "-c", cmd], capture=False, retries=1).ok:
            return False
    log.info("bootstrap: rustup update")
    return run(["rustup", "update"], dry_run=dry_run, capture=False).ok


def ensure_oh_my_posh(platform_info: PlatformInfo, *, dry_run: bool) -> bool:
    """On Linux, oh-my-posh has no apt package — use the official installer."""
    if not platform_info.is_linux:
        return True
    if command_exists("oh-my-posh"):
        log.info("bootstrap: oh-my-posh already installed; updating")
    else:
        log.info("bootstrap: installing oh-my-posh")
    home = platform_info.home
    bin_dir = home / ".local" / "bin"
    if not dry_run:
        bin_dir.mkdir(parents=True, exist_ok=True)
    cmd = f"curl -fsSL {_OMP_INSTALL_URL} | bash -s -- -d {bin_dir}"
    return run(["bash", "-c", cmd], dry_run=dry_run, capture=False, retries=1).ok


def ensure_colorscripts(platform_info: PlatformInfo, *, dry_run: bool) -> bool:
    """Install dwt1's shell-color-scripts (provides ``colorscript`` for the
    shell greeter's visual init). Not packaged in brew/apt, so clone + build.

    Upstream's Makefile installs the binary under ``/usr/local/bin`` and the art
    under ``/opt/shell-color-scripts/colorscripts`` (hardcoded), which needs
    sudo. Idempotent: skips when ``colorscript`` is already on PATH.
    """
    if command_exists("colorscript"):
        return True
    log.info("bootstrap: installing shell-color-scripts")
    if dry_run:
        log.info("(dry-run) would clone + 'make install' shell-color-scripts")
        return True
    # Clone to a throwaway temp dir, install with sudo (matches upstream), clean up.
    cmd = (
        "set -e; tmp=$(mktemp -d); "
        f'git clone --depth 1 {_COLORSCRIPTS_REPO} "$tmp"; '
        'sudo make -C "$tmp" install; '
        'rm -rf "$tmp"'
    )
    return run(["bash", "-c", cmd], capture=False, retries=1).ok


def ensure_zsh_default_shell(platform_info: PlatformInfo, *, dry_run: bool) -> bool:
    """Set zsh as the default login shell if it isn't already."""
    if platform_info.is_wsl:
        log.info("bootstrap: WSL detected; skipping default-shell change")
        return True
    zsh = _which("zsh")
    if not zsh:
        log.warn("bootstrap: zsh not on PATH; skipping default-shell change")
        return True
    current = os.environ.get("SHELL", "")
    if current == zsh:
        return True
    log.info(f"bootstrap: changing default shell to {zsh}")
    # Ensure /etc/shells lists zsh; required by chsh on some systems.
    if not dry_run:
        shells_file = "/etc/shells"
        try:
            with open(shells_file) as fh:  # noqa: PTH123 - need plain file IO here
                listed = zsh in fh.read()
        except OSError:
            listed = False
        if not listed:
            log.info(f"bootstrap: appending {zsh} to /etc/shells")
            cmd = f'echo "{zsh}" | sudo tee -a /etc/shells'
            run(["bash", "-c", cmd], capture=False)
    return run(["chsh", "-s", zsh], dry_run=dry_run, capture=False).ok


def _dpkg_installed(pkg: str) -> bool:
    return run(["dpkg", "-s", pkg], capture=True, quiet=True).ok


def _which(name: str) -> str | None:
    import shutil

    return shutil.which(name)
