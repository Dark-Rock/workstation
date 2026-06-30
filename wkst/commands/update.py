"""``wkst update`` — refresh every backend and plugin source."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

from wkst import bootstrap, dotfiles, plugins
from wkst.backends import all_backends
from wkst.backends.apt import AptBackend
from wkst.backends.brew import BrewBackend
from wkst.commands.common import (
    ensure_supported_or_exit,
    load_manifest_or_exit,
    resolve_groups_or_exit,
    should_show_menu,
    wants_setup,
)
from wkst.install_menu import choose_update_options
from wkst.install_pipeline import render_summary, run_pipeline, update_op
from wkst.logging import log
from wkst.platform import PlatformInfo


def run(
    *,
    repo_root: Path,
    platform_info: PlatformInfo,
    groups: list[str] | None,
    profile: str | None,
    menu: bool | None,
    dry_run: bool,
) -> None:
    ensure_supported_or_exit(platform_info)

    log.info(
        f"update: platform={platform_info.os.value} arch={platform_info.arch.value} "
        f"dry_run={dry_run}"
    )

    manifest = load_manifest_or_exit(repo_root)

    dotfile_packages: list[str] | None = None
    package_names: list[str] | None = None
    setup_names: list[str] | None = None
    groups = resolve_groups_or_exit(manifest, groups=groups, profile=profile)
    show_menu = should_show_menu(menu, groups=groups, profile=profile)
    if show_menu:
        if groups is not None or profile:
            log.error("--menu cannot be combined with --groups or --profile.")
            sys.exit(2)
        selection = choose_update_options(manifest, repo_root, platform_info)
        groups = selection.groups
        package_names = selection.package_names
        dotfile_packages = selection.dotfile_packages
        setup_names = selection.setup_names

    log.info("phase 1/5: package-manager global update steps")
    _run_package_manager_steps(platform_info, setup_names=setup_names, dry_run=dry_run)

    log.info("phase 2/5: per-package upgrades from manifest")
    outcomes = run_pipeline(
        manifest=manifest,
        platform_info=platform_info,
        groups=groups,
        package_names=package_names,
        operation=update_op,
        operation_label="update",
        dry_run=dry_run,
    )

    if wants_setup(setup_names, "dotfiles"):
        log.info("phase 3/5: refresh dotfiles into $HOME")
        dot_results = dotfiles.sync_all(
            repo_root,
            platform_info.home,
            packages=dotfile_packages,
            dry_run=dry_run,
        )
        dotfiles.render_summary(dot_results)
    else:
        log.info("phase 3/5: dotfile refresh skipped by menu")

    if wants_setup(setup_names, "post_bootstrap"):
        log.info("phase 4/5: post-package update (rustup, oh-my-posh, colorscripts)")
        bootstrap.ensure_rustup(platform_info, dry_run=dry_run)
        bootstrap.ensure_oh_my_posh(platform_info, dry_run=dry_run)
        bootstrap.ensure_colorscripts(platform_info, dry_run=dry_run)
    else:
        log.info("phase 4/5: post-package update skipped by menu")

    plugin_rc = 0
    if wants_setup(setup_names, "plugins"):
        log.info("phase 5/5: refresh plugins (TPM, LazyVim, Zinit, Claude)")
        plugin_results = plugins.update_all(
            repo_root=repo_root,
            manifest=manifest,
            platform_info=platform_info,
            groups=groups,
            dry_run=dry_run,
        )
        plugin_rc = plugins.render_summary(plugin_results)
    else:
        log.info("phase 5/5: plugin refresh skipped by menu")

    pkg_rc = render_summary(outcomes)
    sys.exit(1 if pkg_rc or plugin_rc else 0)


def _run_package_manager_steps(
    platform_info: PlatformInfo, *, setup_names: list[str] | None, dry_run: bool
) -> None:
    backends = all_backends()
    brew = cast(BrewBackend, backends["brew"])
    if brew.is_available(platform_info):
        if wants_setup(setup_names, "metadata"):
            log.info("  brew update")
            brew.update_metadata(dry_run=dry_run)
        else:
            log.info("  brew update skipped by menu")
        if wants_setup(setup_names, "brew_formulae"):
            log.info("  brew upgrade")
            brew.upgrade_formulae(dry_run=dry_run)
        else:
            log.info("  brew upgrade skipped by menu")
        if wants_setup(setup_names, "brew_casks"):
            log.info("  brew upgrade --cask")
            brew.upgrade_casks(dry_run=dry_run)
        else:
            log.info("  brew upgrade --cask skipped by menu")
        if wants_setup(setup_names, "brew_cleanup"):
            log.info("  brew cleanup")
            brew.cleanup(dry_run=dry_run)
        else:
            log.info("  brew cleanup skipped by menu")

    apt = cast(AptBackend, backends["apt"])
    if apt.is_available(platform_info):
        if wants_setup(setup_names, "metadata"):
            log.info("  apt-get update")
            apt.update_metadata(dry_run=dry_run)
        else:
            log.info("  apt-get update skipped by menu")
        if wants_setup(setup_names, "apt_upgrade"):
            log.info("  apt-get upgrade")
            apt.upgrade_packages(dry_run=dry_run)
        else:
            log.info("  apt-get upgrade skipped by menu")
