# workstation

A reproducible, cross-platform workstation for macOS (Apple Silicon + Intel)
and Debian/Ubuntu Linux. One Python CLI (`wkst`) drives installation, updates,
dotfile linking, and health checks; one TOML file (`packages.toml`) is the
single source of truth for every tool.

## Cold start (fresh machine)

```bash
curl -fsSL https://raw.githubusercontent.com/Dark-Rock/workstation/main/bootstrap.sh | bash
```

Forks and mirrors can override the clone source with `WKST_REPO_URL` and the
destination with `WKST_REPO_DIR`.

That's it. `bootstrap.sh` will:

1. Detect the OS (macOS or Debian/Ubuntu).
2. Install Xcode CLT + Homebrew (macOS), or `curl`/`git`/`build-essential` (Linux).
3. Install [`uv`](https://docs.astral.sh/uv/) — a static binary, no Python required.
4. Clone this repo to `~/Programming/workstation` if missing.
5. Install the `wkst` CLI globally via `uv tool install --editable .`.
6. `exec wkst install` — Python takes over and finishes the install.

For CI smoke tests, you can stop before step 6:

```bash
WKST_SKIP_FINAL_INSTALL=1 bash bootstrap.sh
```

## Installing `wkst` on an existing machine

If you already cloned the repo manually, install the CLI once with:

```bash
just install-cli
# or, equivalently:
uv tool install --editable .
```

This drops a `wkst` binary into `~/.local/bin/`. Because the install is
*editable*, every `git pull` updates the CLI immediately — no reinstall
needed. Make sure `~/.local/bin` is on your `PATH` (the bundled `.zshrc`
already does this).

To remove the global CLI: `just uninstall-cli` (or `uv tool uninstall wkst`).

## Daily use

After install, run `wkst` from anywhere:

```bash
wkst help              # rich overview of every command + workflows
wkst                   # bare command opens the full-screen dashboard (TTY)
wkst dashboard         # open the dashboard explicitly
wkst install           # interactive default-on installer (also self-repair)
wkst install --no-menu # non-interactive full install for automation
wkst install --profile=minimal  # install a named profile from packages.toml
wkst update            # interactive default-on updater
wkst update --no-menu  # non-interactive full update for automation
wkst doctor            # health check: missing tools, dotfile drift, shell sanity
wkst sync              # re-link dotfiles into $HOME (use --force to replace conflicts)
wkst diff              # show drift between repo dotfiles and $HOME
wkst add ~/.foo        # adopt a $HOME file/dir into the repo
wkst remove ~/.foo     # detach a file from the repo (restore to $HOME)
wkst macos export      # capture tracked macOS defaults into macos/settings.toml
wkst macos discover    # preview untracked scalar defaults, Dock by default
wkst macos import      # apply macos/settings.toml to this Mac (alias: apply)
wkst clean             # prune accumulated .bak.* files
```

`just` recipes are still available as shortcuts for repo-development tasks
(linting, tests, regenerating `TOOLS.md`, running CI locally). See
`just --list`.

## Repository layout

```text
bootstrap.sh                  # cold-start installer (bash, macOS + Debian)
packages.toml                 # single source of truth for every tool
wkst/                         # Python CLI
  cli.py                      # click entry point + PATH augmentation
  manifest.py                 # parse and resolve packages.toml
  bootstrap.py                # idempotent prereqs (brew/apt/rustup/oh-my-posh)
  install_pipeline.py         # shared install/update orchestration
  dotfiles.py                 # stow-style symlink engine
  plugins.py                  # TPM, LazyVim, Zinit, Claude Code plugins
  process.py                  # subprocess + retry helper
  platform.py                 # OS / arch / brew prefix detection
  logging.py                  # structured logger
  backends/                   # brew, apt, cargo, npm, pipx, claude
  commands/                   # one module per CLI subcommand
dotfiles/                     # stow-style packages, mirrored into $HOME
  zsh/.zshrc
  vim/.vimrc
  git/.gitconfig
  config/.config/{atuin,ghostty,k9s,nvim,oh-my-posh,tmux}/...
  claude/.claude/{rules,settings.json,CLAUDE.md}
tests/                        # pytest suite
TOOLS.md                      # auto-generated from packages.toml
justfile                      # task runner
pyproject.toml                # Python package definition
```

## Adding a new tool

Edit [`packages.toml`](packages.toml) and add an entry. Per-backend identifiers
let you declare different package names per backend; `wkst` picks the preferred
backend automatically per platform.

```toml
[[package]]
name = "ripgrep"
binary = "rg"             # used by `wkst doctor` to check presence
brew = "ripgrep"
apt = "ripgrep"
cargo = "ripgrep"         # fallback if neither system pkg is available
groups = ["search"]
description = "Fast recursive grep"
```

Then:

```bash
just validate              # confirm parse + backend resolution
just install               # install just the new tool (idempotent)
just docs                  # regenerate TOOLS.md
```

## Installation profiles and menu

`packages.toml` also defines user-facing profiles under `[profiles]`. Profiles
are just lists of package groups, so categorizing a tool remains a package-level
concern:

- `minimal`: core shell, terminal, search, and git basics.
- `developer`: daily coding workstation (`minimal` plus languages, dev, quality).
- `sre`: operations toolkit (`developer` plus Kubernetes, containers, API, DB,
  secrets, IaC, and system diagnostics).
- `full`: every package applicable to the current OS.

In an interactive shell, `wkst install` and `wkst update` open a menu by default.
Every tool package is selected by default; the menu renders packages by category
so you can uncheck whole groups or individual packages you do not want. The
update menu also lets you skip global steps such as `brew update`, `brew upgrade`,
`brew upgrade --cask`, `brew cleanup`, dotfile sync, post-bootstrap, and plugin
refresh. Use `--no-menu` for non-interactive automation, `--profile=sre` for a
repeatable preset, or `--groups=terminal,shell,git` for an explicit subset.

The install menu also covers setup phases and dotfile linking. Dotfile import is
default-on for every package under `dotfiles/`, but you can uncheck packages such
as `claude`, `config`, `git`, `vim`, or `zsh` for a particular machine. The menu
can also capture per-machine shell startup preferences such as a future welcome
image into `~/.config/wkst/settings.toml` without changing the package manifest.

### Neovim Mason tools

The Neovim language servers, formatters, and debuggers that Mason installs are
listed once in [`dotfiles/config/.config/nvim/mason-tools.txt`](dotfiles/config/.config/nvim/mason-tools.txt)
(one package per line, `#` comments allowed). That single file is read by both
the Neovim config (`lua/plugins/mason-tools.lua`, via `ensure_installed`) and
`wkst` (headless `:MasonInstall` during `wkst install`), so the two never drift.
Add or remove a Mason tool by editing that file only; `test_invariants.py`
enforces that the Lua never re-introduces a hardcoded copy.

## Exporting/importing macOS settings

macOS user defaults are managed separately from dotfiles because they live in the
system defaults database instead of `$HOME` files. The portable snapshot lives in
`macos/settings.toml`.

On the source Mac, configure macOS normally, then export the tracked settings:

```bash
wkst macos export --dry-run   # preview changed tracked defaults
wkst macos export             # write macos/settings.toml
git add macos/settings.toml
git commit -m 'chore: update macOS settings'
```

To make tracking more extensive without editing TOML by hand, discover untracked
scalar defaults and adopt only the domains you want:

```bash
wkst macos discover --domain com.apple.dock           # preview untracked Dock keys
wkst macos discover --domain com.apple.finder --adopt # append new scalar Finder keys
wkst macos discover --all --dry-run --adopt           # preview every readable domain
```

Discovery only adopts values that `wkst macos import` can safely restore today:
booleans, integers, floats, and strings. It skips arrays, dictionaries, binary
data, and unreadable keys so machine-local state such as recent items and opaque
preference blobs does not get tracked accidentally.

On a new Mac, import the committed settings:

```bash
wkst macos import --dry-run   # preview defaults writes
wkst macos import             # apply settings; restarts Dock/Finder if needed
```

`wkst macos import` is an alias for `wkst macos apply`. Use
`--no-restart` if you want to apply values without restarting Dock/Finder during
that run. Some global settings still require logout/login before macOS fully
picks them up.

## Adding a new dotfile

Drop it into `dotfiles/<package>/<path-relative-to-$HOME>`:

```text
dotfiles/zsh/.zshrc                          -> $HOME/.zshrc
dotfiles/config/.config/foo/bar.conf         -> $HOME/.config/foo/bar.conf
dotfiles/claude/.claude/settings.json        -> $HOME/.claude/settings.json
```

Then `just sync` (use `--force` to back up and replace existing real files).

To move an existing file out of `$HOME` and into the repo:

```bash
uv run wkst sync --adopt ~/.tmux.conf
```

## Supported platforms

| OS | Status |
|----|--------|
| macOS 13+ (Apple Silicon) | tier 1 |
| macOS 13+ (Intel)         | tier 1 |
| Debian 12 / Ubuntu 22.04+ | tier 2 (no GUI casks; some k8s tools via apt only) |

Anything else exits with an unsupported-platform error.

## See also

- [TOOLS.md](TOOLS.md) — auto-generated tool cheatsheet
- [docs/terminal-command-discovery.md](docs/terminal-command-discovery.md) — how to discover the right command from the terminal, including aliases, tldr, cheat.sh, Atuin, fzf, and suggested next steps
- [packages.toml](packages.toml) — manifest schema lives at the top
- [CLAUDE.md](CLAUDE.md) — global SRE guidelines (canonical at `dotfiles/claude/.claude/CLAUDE.md`; symlinked at repo root for the workspace rule loader and into `$HOME/.claude/CLAUDE.md` by `wkst sync`)
