"""``wkst help`` — friendly overview of every command with worked examples."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from wkst import __version__

# Sections are (heading, [(command, description, example)]).
_SECTIONS: list[tuple[str, list[tuple[str, str, str]]]] = [
    (
        "Setup & lifecycle",
        [
            (
                "install",
                "Install packages, link dotfiles, install plugins. Opens a default-on menu "
                "in interactive shells; use --no-menu for automation.",
                "wkst install\nwkst install --no-menu --dry-run\nwkst install --profile=minimal",
            ),
            (
                "update",
                "Upgrade selected tools and setup phases. The menu can skip brew update, "
                "brew formula/cask upgrades, dotfiles, post-bootstrap, and plugins.",
                "wkst update\nwkst update --no-menu --dry-run\nwkst update --groups=editor",
            ),
            (
                "doctor",
                "Health check: missing binaries, dotfile drift, shell sanity. "
                "Exit code is non-zero when anything is wrong.",
                "wkst doctor",
            ),
        ],
    ),
    (
        "Dotfiles",
        [
            (
                "add",
                "Adopt one or more $HOME files/dirs into the repo and symlink "
                "them back. Picks the right dotfiles/<pkg>/ destination "
                "automatically. Recurses into directories.",
                "wkst add ~/.gitconfig\nwkst add ~/.config/zellij\nwkst add --dry-run ~/.config/foo",
            ),
            (
                "remove",
                "Inverse of `add`. Move the repo copy back into $HOME (so you "
                "keep the file) and drop the entry from dotfiles/. Use --purge "
                "to also delete the file from $HOME.",
                "wkst remove ~/.gitconfig\nwkst remove --dry-run ~/.config/zellij\n"
                "wkst remove --purge ~/.config/old",
            ),
            (
                "sync",
                "Symlink dotfiles from dotfiles/<pkg>/ into $HOME (stow-style). "
                "Default is non-destructive; use --force to back up + replace conflicts.",
                "wkst sync --dry-run\nwkst sync --force",
            ),
            (
                "diff",
                "List dotfiles that exist in the repo but are not symlinked from $HOME, "
                "with the drift type for each (real-file / wrong-link / missing).",
                "wkst diff",
            ),
            (
                "clean",
                "Prune accumulated <name>.bak.<timestamp> files in $HOME, $HOME/.config, "
                "$HOME/.claude, $HOME/.tmux.",
                "wkst clean --dry-run\nwkst clean",
            ),
        ],
    ),
    (
        "macOS settings",
        [
            (
                "macos export",
                "Capture the tracked macOS system defaults from this machine into "
                "macos/settings.toml. Commit that file to make the settings portable.",
                "wkst macos export --dry-run\nwkst macos export",
            ),
            (
                "macos import",
                "Import macos/settings.toml onto this Mac. This is an alias for "
                "`wkst macos apply`; by default it restarts Dock/Finder for affected settings.",
                "wkst macos import --dry-run\nwkst macos import\nwkst macos import --no-restart",
            ),
            (
                "macos discover",
                "Find scalar defaults keys that are not tracked yet. Preview by default; "
                "use --adopt to append safe bool/int/float/string values to macos/settings.toml.",
                "wkst macos discover --domain com.apple.dock\n"
                "wkst macos discover --domain com.apple.finder --adopt\n"
                "wkst macos discover --all --dry-run --adopt",
            ),
            (
                "macos apply",
                "Same as `macos import`; kept as the explicit implementation verb for applying "
                "settings.toml to the current machine.",
                "wkst macos apply --dry-run\nwkst macos apply",
            ),
        ],
    ),
    (
        "Manifest inspection",
        [
            (
                "manifest validate",
                "Parse packages.toml and confirm every package resolves to an "
                "installable backend on the current platform.",
                "wkst manifest validate",
            ),
            (
                "manifest list",
                "Show packages applicable to this OS, optionally filtered by group.",
                "wkst manifest list\nwkst manifest list --groups=k8s",
            ),
            (
                "manifest render-md",
                "Emit a Markdown cheatsheet of the manifest on stdout. "
                "Used by `just docs` to regenerate TOOLS.md.",
                "wkst manifest render-md > TOOLS.md",
            ),
        ],
    ),
]

_WORKFLOWS: list[tuple[str, list[str]]] = [
    (
        "Fresh machine (cold start)",
        [
            "curl -fsSL https://raw.githubusercontent.com/Dark-Rock/workstation/main/bootstrap.sh | bash",
            "  # bootstrap.sh installs Xcode CLT/brew (macOS) or apt prereqs (Linux),",
            "  # then uv, clones the repo, installs `wkst` globally,",
            "  # then exec's `wkst install`.",
        ],
    ),
    (
        "Install the wkst CLI globally (existing machine)",
        [
            "just install-cli                  # one command, recommended",
            "  # OR, equivalently:",
            "uv tool install --editable .      # creates ~/.local/bin/wkst",
            "  # `--editable` means `git pull` updates apply with no reinstall.",
            "wkst help                         # confirm it's on PATH",
        ],
    ),
    (
        "Existing machine — first run after refactor",
        [
            "wkst doctor                       # see what's missing / drifted",
            "wkst install --menu               # choose minimal/developer/sre/full/custom",
            "wkst sync --adopt ~/.zshrc        # for any files you edit in $HOME",
            "wkst sync --force --dry-run       # preview backups for the rest",
            "wkst sync --force                 # back up real files + symlink everything",
            "wkst install                      # fill any gaps the new manifest adds",
        ],
    ),
    (
        "Daily / weekly upkeep",
        [
            "wkst update                       # upgrade everything (idempotent)",
            "wkst doctor                       # confirm nothing has drifted",
            "wkst clean                        # sweep .bak.* files when comfortable",
        ],
    ),
    (
        "Adding a tool",
        [
            "$EDITOR packages.toml             # add a new [[package]] entry",
            "wkst manifest validate            # confirm the entry is well-formed",
            "wkst install --groups=<group>     # install just that area",
            "just docs                         # regenerate TOOLS.md from the manifest",
        ],
    ),
    (
        "Export/import macOS settings",
        [
            "wkst macos export --dry-run       # preview captured tracked defaults",
            "wkst macos export                 # write macos/settings.toml",
            "wkst macos discover --domain com.apple.dock",
            "  # preview untracked scalar Dock defaults",
            "wkst macos discover --domain com.apple.finder --adopt",
            "  # append newly found safe scalar Finder defaults",
            "git add macos/settings.toml       # commit the portable settings snapshot",
            "wkst macos import --dry-run       # preview writes on a new Mac",
            "wkst macos import                 # apply settings and restart Dock/Finder if needed",
        ],
    ),
    (
        "Adding a dotfile or config dir",
        [
            "wkst add ~/.foo                   # single file",
            "wkst add ~/.config/zellij         # whole directory, recursive",
            "git add dotfiles/                 # then commit the new files",
            "git commit -m 'feat: adopt zellij config'",
        ],
    ),
    (
        "Removing a dotfile from the repo",
        [
            "wkst remove ~/.gitconfig          # restore the file to $HOME, drop from repo",
            "wkst remove --purge ~/.old-thing  # delete from repo AND $HOME",
            "git add -A dotfiles/              # stage the deletions",
            "git commit -m 'chore: unsync gitconfig'",
        ],
    ),
]

_GLOBAL_FLAGS = [
    ("-v / --verbose", "Enable DEBUG logging."),
    ("-q / --quiet", "Suppress INFO logging — warnings and errors only."),
    ("--version", "Print the wkst version and exit."),
    ("-h / --help", "Standard click help (one-liners). Use `wkst help` for this view."),
]


def show() -> None:
    """Print the rich help overview to stdout."""
    console = Console()

    console.print()
    console.print(
        Panel.fit(
            Text.assemble(
                ("wkst ", "bold cyan"),
                (f"v{__version__}", "dim"),
                "\n",
                "Cross-platform workstation installer, updater, and doctor.",
            ),
            border_style="cyan",
        )
    )

    for heading, rows in _SECTIONS:
        table = Table(
            title=heading,
            title_style="bold",
            title_justify="left",
            show_lines=True,
            expand=True,
            border_style="dim",
        )
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("What it does")
        table.add_column("Example", style="green")
        for cmd, desc, example in rows:
            table.add_row(cmd, desc, example)
        console.print(table)
        console.print()

    console.print(Text("Common workflows", style="bold underline"))
    for title, lines in _WORKFLOWS:
        console.print()
        console.print(Text(f"  {title}", style="bold yellow"))
        for line in lines:
            style = "dim italic" if line.lstrip().startswith("#") else "green"
            console.print(Text(f"    {line}", style=style))
    console.print()

    console.print(Text("Global flags", style="bold underline"))
    flag_table = Table(show_header=False, box=None, padding=(0, 2))
    flag_table.add_column(style="cyan", no_wrap=True)
    flag_table.add_column()
    for name, desc in _GLOBAL_FLAGS:
        flag_table.add_row(name, desc)
    console.print(flag_table)
    console.print()

    console.print(
        Text(
            "More: see README.md for the full architecture, TOOLS.md for the "
            "auto-generated tool cheatsheet, packages.toml for the manifest schema.",
            style="dim",
        )
    )
    console.print()
