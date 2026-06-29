#!/usr/bin/env bash
# bootstrap.sh — cold-start a brand-new workstation.
#
# This is the only file you should ever need to fetch manually. It runs on
# the bash that ships with macOS 13+ (3.2.57) and any modern Debian/Ubuntu.
# It installs the bare minimum to be able to run `uv run wkst install`.
#
# One-liner from a fresh machine:
#
#   curl -fsSL https://raw.githubusercontent.com/Dark-Rock/workstation/main/bootstrap.sh | bash
#
# Steps (idempotent — safe to re-run):
#   1. Detect OS (macOS or Debian/Ubuntu — anything else aborts).
#   2. macOS: install Xcode Command Line Tools, then Homebrew.
#      Linux: install curl + git + sudo prereqs via apt.
#   3. Install `uv` (static binary; no Python required).
#   4. git clone this repo to ~/Programming/workstation if missing.
#   5. `uv tool install --editable .` — installs `wkst` into ~/.local/bin/.
#   6. exec `wkst install` — the global Python CLI takes over from here.

set -euo pipefail

REPO_URL_DEFAULT="https://github.com/Dark-Rock/workstation.git"
REPO_URL_HTTPS_DEFAULT="${REPO_URL_DEFAULT}"
REPO_URL="${WKST_REPO_URL:-${REPO_URL_DEFAULT}}"
REPO_DIR="${WKST_REPO_DIR:-${HOME}/Programming/workstation}"
SKIP_FINAL_INSTALL="${WKST_SKIP_FINAL_INSTALL:-0}"
UV_INSTALL_URL="https://astral.sh/uv/install.sh"

# ----- logging ---------------------------------------------------------------

log() { printf '[%s] \033[0;36mINFO\033[0m: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
ok() { printf '[%s] \033[1;32mOK\033[0m: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
warn() { printf '[%s] \033[1;33mWARN\033[0m: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; }
fail() {
    printf '[%s] \033[1;31mERROR\033[0m: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2
    exit 1
}

# ----- OS detection ----------------------------------------------------------

detect_os() {
    case "$(uname -s)" in
    Darwin) echo "macos" ;;
    Linux)
        if command -v apt-get >/dev/null 2>&1; then
            echo "linux-debian"
        else
            fail "Unsupported Linux distribution (apt-get not found)."
        fi
        ;;
    *) fail "Unsupported OS: $(uname -s)" ;;
    esac
}

detect_wsl() {
    [ -n "${WSL_DISTRO_NAME:-}" ] && return 0
    if [ -r /proc/sys/kernel/osrelease ] && grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease; then
        return 0
    fi
    if [ -r /proc/version ] && grep -qiE 'microsoft|wsl' /proc/version; then
        return 0
    fi
    return 1
}

# ----- macOS: Xcode CLT + Homebrew -------------------------------------------

ensure_xcode_clt() {
    if xcode-select -p >/dev/null 2>&1; then
        log "Xcode Command Line Tools already installed"
        return 0
    fi
    log "Installing Xcode Command Line Tools (a GUI prompt will appear)"
    xcode-select --install >/dev/null 2>&1 || true
    log "Waiting for Xcode CLT to finish installing — accept the prompt..."
    while ! xcode-select -p >/dev/null 2>&1; do
        sleep 5
    done
    ok "Xcode Command Line Tools installed"
}

ensure_homebrew() {
    if command -v brew >/dev/null 2>&1; then
        log "Homebrew already installed"
        return 0
    fi
    log "Installing Homebrew"
    NONINTERACTIVE=1 /bin/bash -c \
        "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for this shell so we can use it immediately.
    if [ -x /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    ok "Homebrew installed"
}

# ----- Linux: apt prereqs ----------------------------------------------------

ensure_apt_prereqs() {
    if [ "$(id -u)" -ne 0 ] && ! command -v sudo >/dev/null 2>&1; then
        fail "sudo is required on Linux; please install it manually first."
    fi
    log "Installing apt prereqs: curl git ca-certificates gnupg build-essential"
    sudo_run apt-get update -qq
    DEBIAN_FRONTEND=noninteractive sudo_run apt-get install -y \
        curl git ca-certificates gnupg lsb-release build-essential
    ok "apt prereqs installed"
}

sudo_run() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

# ----- uv (Python tool runner) -----------------------------------------------

ensure_uv() {
    if command -v uv >/dev/null 2>&1; then
        log "uv already installed ($(uv --version))"
        return 0
    fi
    log "Installing uv (static binary)"
    curl -LsSf "${UV_INSTALL_URL}" | sh
    # uv installs to ~/.local/bin by default; add to PATH for this shell.
    export PATH="${HOME}/.local/bin:${PATH}"
    if ! command -v uv >/dev/null 2>&1; then
        fail "uv installer reported success but uv is not on PATH"
    fi
    ok "uv installed ($(uv --version))"
}

# ----- repo clone ------------------------------------------------------------

ensure_repo() {
    if [ -d "${REPO_DIR}/.git" ]; then
        log "Repo already present at ${REPO_DIR}"
        return 0
    fi
    log "Cloning ${REPO_URL} to ${REPO_DIR}"
    mkdir -p "$(dirname "${REPO_DIR}")"
    git clone "${REPO_URL}" "${REPO_DIR}"
    ok "Repo cloned"
}

# ----- main ------------------------------------------------------------------

main() {
    log "wkst bootstrap starting"
    log "  REPO_URL=${REPO_URL}"
    log "  REPO_DIR=${REPO_DIR}"
    log "  SKIP_FINAL_INSTALL=${SKIP_FINAL_INSTALL}"

    OS_KIND="$(detect_os)"
    log "  OS=${OS_KIND}"
    if [ "${OS_KIND}" = "linux-debian" ] && detect_wsl; then
        log "  VARIANT=wsl"
        if [ -z "${WKST_REPO_URL:-}" ]; then
            REPO_URL="${REPO_URL_HTTPS_DEFAULT}"
            log "  WSL detected; using HTTPS clone URL by default"
        fi
    fi

    case "${OS_KIND}" in
    macos)
        ensure_xcode_clt
        ensure_homebrew
        ;;
    linux-debian)
        ensure_apt_prereqs
        ;;
    esac

    ensure_uv
    ensure_repo
    ensure_wkst_cli

    if [ "${SKIP_FINAL_INSTALL}" = "1" ]; then
        ok "Bootstrap prerequisites completed (skipping final 'wkst install')."
        return 0
    fi

    cd "${REPO_DIR}"
    log "Handing control to: wkst install"
    exec wkst install "$@"
}

# ----- wkst CLI (global install) ---------------------------------------------

ensure_wkst_cli() {
    # Make sure ~/.local/bin (where uv tool installs) is on PATH for this shell.
    case ":${PATH}:" in
    *":${HOME}/.local/bin:"*) ;;
    *) export PATH="${HOME}/.local/bin:${PATH}" ;;
    esac

    if command -v wkst >/dev/null 2>&1; then
        log "wkst CLI already installed at $(command -v wkst) ($(wkst --version 2>/dev/null || echo unknown))"
        return 0
    fi
    log "Installing wkst CLI globally (uv tool install --editable .)"
    (cd "${REPO_DIR}" && uv tool install --editable . --force)
    if ! command -v wkst >/dev/null 2>&1; then
        fail "wkst was installed but is not on PATH; check ${HOME}/.local/bin"
    fi
    ok "wkst CLI installed ($(wkst --version))"
}

main "$@"
