"""``wkst install`` — bootstrap, install packages, link dotfiles, install plugins."""

from __future__ import annotations

import sys
from pathlib import Path

from wkst import bootstrap, dotfiles, plugins, render
from wkst.commands.common import (
    ensure_supported_or_exit,
    load_manifest_or_exit,
    resolve_groups_or_exit,
    should_show_menu,
    wants_setup,
)
from wkst.install_menu import choose_install_options
from wkst.install_pipeline import install_op, render_summary, run_pipeline
from wkst.logging import log
from wkst.platform import PlatformInfo
from wkst.preferences import InstallPreferences, write_preferences


def run(
    *,
    repo_root: Path,
    platform_info: PlatformInfo,
    groups: list[str] | None,
    profile: str | None,
    menu: bool | None,
    dry_run: bool,
    customize_only: bool = False,
) -> None:
    ensure_supported_or_exit(platform_info)

    log.info(
        f"install: platform={platform_info.os.value} arch={platform_info.arch.value} "
        f"dry_run={dry_run}"
    )

    manifest = load_manifest_or_exit(repo_root)

    preferences = InstallPreferences()
    package_names: list[str] | None = None
    dotfile_packages: list[str] | None = None
    setup_names: list[str] | None = None
    groups = resolve_groups_or_exit(manifest, groups=groups, profile=profile)
    show_menu = should_show_menu(menu, groups=groups, profile=profile)
    if show_menu:
        if groups is not None or profile:
            log.error("--menu cannot be combined with --groups or --profile.")
            sys.exit(2)
        selection = choose_install_options(manifest, repo_root, show_setup_mode=not customize_only)
        groups = selection.groups
        package_names = selection.package_names
        dotfile_packages = selection.dotfile_packages
        setup_names = selection.setup_names
        preferences = selection.preferences

    if wants_setup(setup_names, "bootstrap"):
        log.info("phase 1/5: bootstrap prerequisites")
        if not bootstrap.ensure_apt_prereqs(platform_info, dry_run=dry_run):
            render.print_failure(
                "APT prerequisites failed — install aborted",
                ["Could not install base build/curl/git packages via apt."],
                hint="re-run with -v to see the failing command",
            )
            sys.exit(1)
        if not bootstrap.ensure_homebrew(platform_info, dry_run=dry_run):
            render.print_failure(
                "Homebrew install failed — install aborted",
                ["Homebrew is required for package installation on this platform."],
                hint="re-run with -v for details; see https://brew.sh",
            )
            sys.exit(1)
    else:
        log.info("phase 1/5: bootstrap prerequisites skipped by menu")

    log.info("phase 2/5: install packages from manifest")
    pkg_outcomes = run_pipeline(
        manifest=manifest,
        platform_info=platform_info,
        groups=groups,
        package_names=package_names,
        operation=install_op,
        operation_label="install",
        dry_run=dry_run,
    )

    if wants_setup(setup_names, "post_bootstrap"):
        log.info("phase 3/5: post-package bootstrap (rustup, oh-my-posh, shell)")
        bootstrap.ensure_rustup(platform_info, dry_run=dry_run)
        bootstrap.ensure_oh_my_posh(platform_info, dry_run=dry_run)
        bootstrap.ensure_zsh_default_shell(platform_info, dry_run=dry_run)
    else:
        log.info("phase 3/5: post-package bootstrap skipped by menu")

    if wants_setup(setup_names, "dotfiles"):
        log.info("phase 4/5: link dotfiles into $HOME")
        dot_results = dotfiles.sync_all(
            repo_root,
            platform_info.home,
            packages=dotfile_packages,
            dry_run=dry_run,
        )
        dotfiles.render_summary(dot_results)
    else:
        log.info("phase 4/5: dotfile linking skipped by menu")
    write_preferences(platform_info.home, preferences, dry_run=dry_run)

    plugin_rc = 0
    if wants_setup(setup_names, "plugins"):
        log.info("phase 5/5: install editor / shell plugins (TPM, LazyVim, Zinit, Claude)")
        plugin_results = plugins.install_all(
            repo_root=repo_root,
            manifest=manifest,
            platform_info=platform_info,
            groups=groups,
            dry_run=dry_run,
        )
        plugin_rc = plugins.render_summary(plugin_results)
    else:
        log.info("phase 5/5: plugin setup skipped by menu")

    pkg_rc = render_summary(pkg_outcomes)
    sys.exit(1 if pkg_rc or plugin_rc else 0)
