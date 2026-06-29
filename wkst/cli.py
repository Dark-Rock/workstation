"""``wkst`` command-line entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from wkst import __version__
from wkst.logging import configure, log
from wkst.platform import PlatformInfo, detect

REPO_ROOT = Path(__file__).resolve().parent.parent


def _augment_path(platform_info: PlatformInfo) -> None:
    """Prepend standard tool dirs to PATH so freshly-installed tools are found.

    Without this, ``wkst install`` from a non-login shell (e.g. CI, ``curl |
    bash`` flows) wouldn't see brew/cargo/uv even though they're on disk.
    """
    home = platform_info.home
    candidates: list[Path] = []
    if platform_info.brew_prefix:
        candidates.append(platform_info.brew_prefix / "bin")
        candidates.append(platform_info.brew_prefix / "sbin")
    candidates += [
        home / ".local" / "bin",
        home / ".cargo" / "bin",
    ]
    existing = os.environ.get("PATH", "").split(os.pathsep)
    extra = [str(p) for p in candidates if p.is_dir() and str(p) not in existing]
    if extra:
        os.environ["PATH"] = os.pathsep.join(extra + existing)


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.version_option(version=__version__, prog_name="wkst")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
@click.option("-q", "--quiet", is_flag=True, help="Only warnings and errors.")
@click.pass_context
def main(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """Cross-platform workstation installer, updater, and doctor.

    Run ``wkst help`` for a tour of every command with examples.
    """
    configure(verbose=verbose, quiet=quiet)
    ctx.ensure_object(dict)
    ctx.obj["repo_root"] = REPO_ROOT
    info = detect()
    _augment_path(info)
    ctx.obj["platform"] = info

    # Bare `wkst` in a terminal opens the main action menu. Non-interactive
    # invocations keep the help overview so scripts do not hang on a TUI.
    if ctx.invoked_subcommand is None:
        if sys.stdin.isatty():
            _run_main_menu(ctx)
        else:
            from wkst.commands import help as cmd

            cmd.show()


def _run_main_menu(ctx: click.Context) -> None:
    from wkst.install_menu import choose_main_action

    action = choose_main_action()
    if action == "install":
        from wkst.commands import install as cmd

        cmd.run(
            repo_root=ctx.obj["repo_root"],
            platform_info=ctx.obj["platform"],
            groups=None,
            profile=None,
            menu=False,
            dry_run=False,
            customize_only=False,
        )
    if action == "update":
        from wkst.commands import update as cmd

        cmd.run(
            repo_root=ctx.obj["repo_root"],
            platform_info=ctx.obj["platform"],
            groups=None,
            profile=None,
            menu=False,
            dry_run=False,
        )
    if action == "customize_install":
        from wkst.commands import install as cmd

        cmd.run(
            repo_root=ctx.obj["repo_root"],
            platform_info=ctx.obj["platform"],
            groups=None,
            profile=None,
            menu=True,
            dry_run=False,
            customize_only=True,
        )
    if action == "uninstall":
        from wkst.commands import uninstall as cmd

        cmd.run(
            repo_root=ctx.obj["repo_root"],
            platform_info=ctx.obj["platform"],
            groups=None,
            profile=None,
            dry_run=False,
            yes=False,
        )


@main.command()
def help() -> None:
    """Show a rich overview of every command with worked examples."""
    from wkst.commands import help as cmd

    cmd.show()


@main.command()
@click.option("--groups", help="Comma-separated package groups (default: all).")
@click.option(
    "--profile", help="Install profile from packages.toml (minimal, developer, sre, full)."
)
@click.option("--menu/--no-menu", default=None, help="Show or skip the interactive menu.")
@click.option("--dry-run", is_flag=True, help="Show what would happen without doing it.")
@click.pass_context
def install(
    ctx: click.Context,
    groups: str | None,
    profile: str | None,
    menu: bool | None,
    dry_run: bool,
) -> None:
    """Install everything (packages + dotfiles + plugins)."""
    from wkst.commands import install as cmd

    cmd.run(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
        groups=_split_groups(groups),
        profile=profile,
        menu=menu,
        dry_run=dry_run,
        customize_only=False,
    )


@main.command()
@click.option("--groups", help="Comma-separated package groups (default: all).")
@click.option(
    "--profile", help="Update profile from packages.toml (minimal, developer, sre, full)."
)
@click.option("--menu/--no-menu", default=None, help="Show or skip the interactive menu.")
@click.option("--dry-run", is_flag=True, help="Show what would happen without doing it.")
@click.pass_context
def update(
    ctx: click.Context,
    groups: str | None,
    profile: str | None,
    menu: bool | None,
    dry_run: bool,
) -> None:
    """Update everything (brew/apt/cargo/npm/pipx/claude/plugins)."""
    from wkst.commands import update as cmd

    cmd.run(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
        groups=_split_groups(groups),
        profile=profile,
        menu=menu,
        dry_run=dry_run,
    )


@main.command()
@click.option("--groups", help="Comma-separated package groups (default: all).")
@click.option(
    "--profile", help="Uninstall profile from packages.toml (minimal, developer, sre, full)."
)
@click.option("--yes", is_flag=True, help="Do not prompt before uninstalling.")
@click.option("--dry-run", is_flag=True, help="Show what would happen without doing it.")
@click.pass_context
def uninstall(
    ctx: click.Context,
    groups: str | None,
    profile: str | None,
    yes: bool,
    dry_run: bool,
) -> None:
    """Uninstall manifest packages and unlink wkst-managed dotfiles."""
    from wkst.commands import uninstall as cmd

    cmd.run(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
        groups=_split_groups(groups),
        profile=profile,
        dry_run=dry_run,
        yes=yes,
    )


@main.command()
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Report missing tools, version drift, and dotfile drift."""
    from wkst.commands import doctor as cmd

    rc = cmd.run(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
    )
    sys.exit(rc)


@main.command()
@click.option(
    "--adopt",
    "adopt_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Move a $HOME file into the repo and re-symlink it.",
)
@click.option("--force", is_flag=True, help="Backup and replace conflicting real files.")
@click.option("--dry-run", is_flag=True, help="Show what would happen without doing it.")
@click.pass_context
def sync(ctx: click.Context, adopt_path: Path | None, force: bool, dry_run: bool) -> None:
    """Symlink dotfiles from the repo into $HOME (stow-style)."""
    from wkst.commands import sync as cmd

    cmd.run(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
        adopt_path=adopt_path,
        force=force,
        dry_run=dry_run,
    )


@main.command()
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path), required=True)
@click.option("--dry-run", is_flag=True, help="Show what would happen without doing it.")
@click.pass_context
def add(ctx: click.Context, paths: tuple[Path, ...], dry_run: bool) -> None:
    """Adopt one or more $HOME files/dirs into the repo and symlink them back.

    Examples:

        wkst add ~/.gitconfig
        wkst add ~/.config/foo ~/.config/bar
        wkst add --dry-run ~/.config/zellij
    """
    from wkst.commands import add as cmd

    cmd.run(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
        paths=paths,
        dry_run=dry_run,
    )


@main.command()
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path), required=True)
@click.option(
    "--purge",
    is_flag=True,
    help="Delete the file from the repo AND $HOME (you lose the content).",
)
@click.option("--dry-run", is_flag=True, help="Show what would happen without doing it.")
@click.pass_context
def remove(ctx: click.Context, paths: tuple[Path, ...], purge: bool, dry_run: bool) -> None:
    """Detach $HOME files/dirs from the repo (inverse of ``wkst add``).

    Default: replace each managed symlink in $HOME with the real file from
    the repo, then drop the (now empty) entry from dotfiles/. You keep the
    config; the repo just no longer manages it.

    With ``--purge``: delete the symlink AND the repo file. Use only if you
    want the config gone entirely.

    Examples:

        wkst remove ~/.gitconfig
        wkst remove ~/.config/zellij
        wkst remove --purge ~/.config/old-thing
        wkst remove --dry-run ~/.tmux.conf
    """
    from wkst.commands import remove as cmd

    cmd.run(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
        paths=paths,
        purge=purge,
        dry_run=dry_run,
    )


@main.command()
@click.pass_context
def diff(ctx: click.Context) -> None:
    """Show divergence between dotfiles in the repo and $HOME."""
    from wkst.commands import diff as cmd

    rc = cmd.run(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
    )
    sys.exit(rc)


@main.command()
@click.option("--dry-run", is_flag=True, help="Show what would happen without doing it.")
@click.pass_context
def clean(ctx: click.Context, dry_run: bool) -> None:
    """Prune legacy .bak.* files and tool caches."""
    from wkst.commands import clean as cmd

    cmd.run(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
        dry_run=dry_run,
    )


@main.group()
def manifest() -> None:
    """Inspect the package manifest."""


@manifest.command("validate")
@click.pass_context
def manifest_validate(ctx: click.Context) -> None:
    """Validate that packages.toml parses and references known backends."""
    from wkst.commands import manifest as cmd

    rc = cmd.validate(repo_root=ctx.obj["repo_root"], platform_info=ctx.obj["platform"])
    sys.exit(rc)


@manifest.command("render-md")
@click.pass_context
def manifest_render_md(ctx: click.Context) -> None:
    """Render the manifest to Markdown on stdout (for docs/TOOLS.md)."""
    from wkst.commands import manifest as cmd

    cmd.render_md(repo_root=ctx.obj["repo_root"])


@manifest.command("add")
@click.argument("name")
@click.option("--brew", default=None, help="Homebrew formula/cask name.")
@click.option("--brew-type", default="formula", show_default=True, help="formula or cask.")
@click.option("--apt", default=None, help="APT package name.")
@click.option("--cargo", default=None, help="cargo crate name.")
@click.option("--npm", default=None, help="npm package name.")
@click.option("--pipx", default=None, help="pipx package name.")
@click.option("--binary", default=None, help="Binary name on PATH (if different from name).")
@click.option("--groups", "pkg_groups", default="", help="Comma-separated groups (e.g. editor,ai).")
@click.option("--platforms", default="", help="Comma-separated platforms (macos, linux-debian).")
@click.option("--description", default=None, help="Short human description.")
@click.option("--dry-run", is_flag=True, help="Print the entry without writing it.")
@click.pass_context
def manifest_add(
    ctx: click.Context,
    name: str,
    brew: str | None,
    brew_type: str,
    apt: str | None,
    cargo: str | None,
    npm: str | None,
    pipx: str | None,
    binary: str | None,
    pkg_groups: str,
    platforms: str,
    description: str | None,
    dry_run: bool,
) -> None:
    """Add a new package entry to packages.toml.

    Examples:

        wkst manifest add ripgrep --brew ripgrep --apt ripgrep --groups search
        wkst manifest add ghostty --brew ghostty --brew-type cask --groups terminal --platforms macos
        wkst manifest add hermes-agent --brew hermes-agent --groups ai --dry-run
    """
    from wkst.commands import manifest as cmd

    rc = cmd.add_package(
        repo_root=ctx.obj["repo_root"],
        name=name,
        brew=brew,
        brew_type=brew_type,
        apt=apt,
        cargo=cargo,
        npm=npm,
        pipx=pipx,
        binary=binary,
        groups=[g.strip() for g in pkg_groups.split(",") if g.strip()],
        platforms=[p.strip() for p in platforms.split(",") if p.strip()],
        description=description,
        dry_run=dry_run,
    )
    sys.exit(rc)


@manifest.command("list")
@click.option("--groups", help="Comma-separated groups to list (default: all).")
@click.pass_context
def manifest_list(ctx: click.Context, groups: str | None) -> None:
    """List packages applicable to this platform."""
    from wkst.commands import manifest as cmd

    cmd.list_packages(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
        groups=_split_groups(groups),
    )


@main.group()
def macos() -> None:
    """Export and apply macOS system defaults (macOS only)."""


@macos.command("export")
@click.option("--dry-run", is_flag=True, help="Show what would be written without saving.")
@click.pass_context
def macos_export(ctx: click.Context, dry_run: bool) -> None:
    """Capture current macOS defaults into macos/settings.toml."""
    from wkst.commands import macos as cmd

    cmd.export(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
        dry_run=dry_run,
    )


@macos.command("apply")
@click.option("--dry-run", is_flag=True, help="Show what would be written without applying.")
@click.option("--no-restart", is_flag=True, help="Skip restarting Dock/Finder after applying.")
@click.pass_context
def macos_apply(ctx: click.Context, dry_run: bool, no_restart: bool) -> None:
    """Apply macos/settings.toml to the current macOS system."""
    from wkst.commands import macos as cmd

    cmd.apply(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
        dry_run=dry_run,
        no_restart=no_restart,
    )


@macos.command("import")
@click.option("--dry-run", is_flag=True, help="Show what would be written without applying.")
@click.option("--no-restart", is_flag=True, help="Skip restarting Dock/Finder after applying.")
@click.pass_context
def macos_import(ctx: click.Context, dry_run: bool, no_restart: bool) -> None:
    """Import macos/settings.toml onto the current macOS system."""
    from wkst.commands import macos as cmd

    cmd.apply(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
        dry_run=dry_run,
        no_restart=no_restart,
    )


@macos.command("discover")
@click.option(
    "--domain",
    "domains",
    multiple=True,
    help="Defaults domain to inspect; repeatable. Use --all for every readable domain.",
)
@click.option("--all", "all_domains", is_flag=True, help="Inspect every readable defaults domain.")
@click.option(
    "--adopt", is_flag=True, help="Append newly discovered scalar settings to macos/settings.toml."
)
@click.option("--dry-run", is_flag=True, help="Preview adoption without writing settings.toml.")
@click.pass_context
def macos_discover(
    ctx: click.Context,
    domains: tuple[str, ...],
    all_domains: bool,
    adopt: bool,
    dry_run: bool,
) -> None:
    """Find untracked scalar defaults keys, optionally adopting them."""
    from wkst.commands import macos as cmd

    selected_domains = ["all"] if all_domains else list(domains or ("com.apple.dock",))
    cmd.discover(
        repo_root=ctx.obj["repo_root"],
        platform_info=ctx.obj["platform"],
        domains=selected_domains,
        adopt=adopt,
        dry_run=dry_run,
    )


def _split_groups(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [g.strip() for g in raw.split(",") if g.strip()]


if __name__ == "__main__":  # pragma: no cover
    try:
        main()
    except KeyboardInterrupt:
        log.warn("Interrupted by user.")
        sys.exit(130)
