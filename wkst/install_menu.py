"""Interactive workstation menus for ``wkst install`` and ``wkst update``."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, cast

import click
from rich.console import Console
from rich.table import Table

from wkst import dotfiles, selection
from wkst.manifest import Manifest, Package
from wkst.platform import PlatformInfo
from wkst.preferences import InstallPreferences
from wkst.selection import InstallSelection
from wkst.tui import BACK, cancel_if_requested, checkbox_menu, choice_menu

_SETUP_LABELS = {
    "bootstrap": "Bootstrap prerequisites (Homebrew/APT prerequisites)",
    "post_bootstrap": "Post-package bootstrap (rustup, oh-my-posh, default shell)",
    "dotfiles": "Dotfile import/link into $HOME",
    "plugins": "Plugin setup/update (TPM, Zinit, navi cheats, LazyVim, Claude)",
    "metadata": "Package-manager metadata refresh (brew update / apt update)",
    "brew_formulae": "Homebrew formula bulk upgrade (brew upgrade)",
    "brew_casks": "Homebrew cask bulk upgrade (brew upgrade --cask)",
    "brew_cleanup": "Homebrew cleanup (brew cleanup)",
    "apt_upgrade": "APT package bulk upgrade (apt-get upgrade)",
}

_PACKAGE_UPDATE_SETUPS = {"metadata", "brew_formulae", "apt_upgrade"}

MainAction = Literal["install", "update", "customize_install", "uninstall"]


def choose_install_options(
    manifest: Manifest, repo_root: Path, *, show_setup_mode: bool = True
) -> InstallSelection:
    """Prompt for install tools, dotfiles, setup phases, and preferences."""
    return _choose_options(
        manifest=manifest,
        repo_root=repo_root,
        title="wkst install menu",
        package_action="install",
        setup_choices=["bootstrap", "post_bootstrap", "dotfiles", "plugins"],
        include_dotfiles=True,
        include_preferences=True,
        show_setup_mode=show_setup_mode,
    )


def choose_update_options(
    manifest: Manifest, repo_root: Path, platform_info: PlatformInfo
) -> InstallSelection:
    """Prompt for update tools and setup phases."""
    return _choose_options(
        manifest=manifest,
        repo_root=repo_root,
        title="wkst update menu",
        package_action="update",
        setup_choices=_update_setup_choices(platform_info),
        include_dotfiles=True,
        include_preferences=False,
    )


def choose_main_action() -> MainAction:
    """Prompt for the top-level ``wkst`` action."""
    result = choice_menu(
        title="wkst",
        help_text="Choose what you want to do with this workstation.",
        choices=[
            ("install", "Install everything with defaults"),
            ("update", "Update everything managed by wkst"),
            ("customize_install", "Customize installation"),
            ("uninstall", "Remove everything installed or linked by wkst"),
        ],
    )
    cancel_if_requested(result)
    return cast(MainAction, result)


def _update_setup_choices(platform_info: PlatformInfo) -> list[str]:
    choices = ["metadata"]
    if platform_info.is_macos:
        choices.extend(["brew_formulae", "brew_casks", "brew_cleanup"])
    if platform_info.is_linux:
        choices.append("apt_upgrade")
    choices.extend(["dotfiles", "post_bootstrap", "plugins"])
    return choices


def _choose_options(
    *,
    manifest: Manifest,
    repo_root: Path,
    title: str,
    package_action: str,
    setup_choices: list[str],
    include_dotfiles: bool,
    include_preferences: bool,
    show_setup_mode: bool = True,
) -> InstallSelection:
    console = Console()
    console.print()
    console.print(f"[bold cyan]{title}[/bold cyan]")
    if sys.stdin.isatty() and sys.stdout.isatty():
        console.print("Use ↑/↓, Space to toggle, Enter to continue, Backspace to go back.")
        console.print()
        return _choose_options_tui(
            console=console,
            manifest=manifest,
            repo_root=repo_root,
            package_action=package_action,
            setup_choices=setup_choices,
            include_dotfiles=include_dotfiles,
            include_preferences=include_preferences,
            show_setup_mode=show_setup_mode,
        )

    console.print("Everything is selected by default; answer 'n' only for things you do not want.")
    console.print()

    groups, package_names = _choose_packages_by_group(console, manifest, package_action)
    setup_names = _choose_setups(console, setup_choices)
    dotfile_packages = (
        _choose_dotfile_packages(console, repo_root)
        if include_dotfiles and _wants_setup(setup_names, "dotfiles")
        else []
    )
    preferences = _choose_preferences(console) if include_preferences else InstallPreferences()
    _render_selection_summary(
        console, groups, package_names, dotfile_packages, setup_names, preferences
    )

    return InstallSelection(
        groups=groups,
        package_names=package_names,
        dotfile_packages=dotfile_packages,
        setup_names=setup_names,
        preferences=preferences,
    )


def _choose_options_tui(
    *,
    console: Console,
    manifest: Manifest,
    repo_root: Path,
    package_action: str,
    setup_choices: list[str],
    include_dotfiles: bool,
    include_preferences: bool,
    show_setup_mode: bool = True,
) -> InstallSelection:
    available_tool_sections = selection.available_tool_sections(manifest)
    selected_tool_sections = {section_id for section_id, *_rest in available_tool_sections}
    selected_groups = selection.groups_for_tool_sections(manifest, selected_tool_sections)
    selected_package_names = {p.name for p in manifest.packages}
    selected_package_phase = True
    visible_setup_choices = _visible_setup_choices(setup_choices)
    package_setup_names = _package_setup_names(setup_choices)
    selected_setups = set(visible_setup_choices)
    dotfile_options = _dotfile_options(repo_root)
    selected_dotfiles = {spec for spec, _label in dotfile_options}
    selected_welcome_image = False
    preferences = InstallPreferences()

    mode = "customize"
    if show_setup_mode:
        chosen_mode = choice_menu(
            title="Setup mode",
            help_text="Choose whether to run the default full setup or customize it first.",
            choices=[
                ("everything", f"{package_action.title()} everything with defaults"),
                ("customize", "Customize phases, tools, packages, and options"),
            ],
        )
        cancel_if_requested(chosen_mode)
        mode = cast(str, chosen_mode)
    if mode == "everything":
        selected_groups_list, package_names = selection.package_selection(
            manifest, selected_package_names
        )
        setup_names = [*package_setup_names, *visible_setup_choices]
        dotfile_packages = [spec for spec, _label in dotfile_options]
        _render_selection_summary(
            console, selected_groups_list, package_names, dotfile_packages, setup_names, preferences
        )
        return InstallSelection(
            groups=selected_groups_list,
            package_names=package_names,
            dotfile_packages=dotfile_packages,
            setup_names=setup_names,
            preferences=preferences,
        )

    step = 0
    while True:
        has_options = include_preferences or (include_dotfiles and "dotfiles" in selected_setups)
        steps: list[str | tuple[str, str]] = ["phases"]
        if selected_package_phase:
            steps.append("package_categories")
            steps.extend(
                ("package_section", section_id)
                for section_id in _ordered_selected_package_sections(
                    available_tool_sections, selected_tool_sections, selected_groups
                )
            )
        if has_options:
            steps.append("options")
        if step >= len(steps):
            break
        current_step = steps[step]

        if current_step == "phases":
            phase_choices = [("phase:packages", _package_phase_label(package_action))]
            phase_choices.extend(
                (f"setup:{setup}", _phase_label(setup)) for setup in visible_setup_choices
            )
            phase_selected = {f"setup:{setup}" for setup in selected_setups}
            if selected_package_phase:
                phase_selected.add("phase:packages")
            result = checkbox_menu(
                title="Phases",
                help_text="Choose which install/update phases to run.",
                choices=phase_choices,
                selected=phase_selected,
                allow_back=False,
            )
            cancel_if_requested(result)
            selected = cast(set[str], result)
            selected_package_phase = "phase:packages" in selected
            selected_setups = {
                item.removeprefix("setup:") for item in selected if item.startswith("setup:")
            }
            if not selected_package_phase:
                selected_package_names = set()
            if not include_dotfiles or "dotfiles" not in selected_setups:
                selected_dotfiles = set()
            step += 1
            continue

        if current_step == "package_categories":
            result = checkbox_menu(
                title="Package categories",
                help_text="Choose package categories to install/update.",
                choices=[
                    (
                        section_id,
                        _tool_section_label(manifest, section_id, name, description, groups),
                    )
                    for section_id, name, description, groups in available_tool_sections
                ],
                selected=selected_tool_sections,
            )
            if result is BACK:
                step -= 1
                continue
            cancel_if_requested(result)
            previous_tool_sections = set(selected_tool_sections)
            selected_tool_sections = set(cast(set[str], result))
            selected_groups = _default_groups_after_tool_section_change(
                manifest, selected_tool_sections, previous_tool_sections, selected_groups
            )
            selected_package_names = _default_package_selection_after_group_change(
                manifest, selected_groups, selected_package_names
            )
            step += 1
            continue

        if isinstance(current_step, tuple) and current_step[0] == "package_section":
            section_id = current_step[1]
            _section_id, section_name, _description, _section_groups = _section_by_id(
                available_tool_sections, section_id
            )
            packages = _packages_for_section_menu(
                manifest, section_id, selected_tool_sections, available_tool_sections
            )
            result = checkbox_menu(
                title=f"{section_name} packages",
                help_text=f"Choose {section_name.lower()} packages to {package_action}.",
                choices=[(package.name, _package_label(package)) for package in packages],
                selected=selected_package_names & {package.name for package in packages},
            )
            if result is BACK:
                step -= 1
                continue
            cancel_if_requested(result)
            group_package_names = {package.name for package in packages}
            selected_package_names.difference_update(group_package_names)
            selected_package_names.update(cast(set[str], result))
            step += 1
            continue

        option_choices: list[tuple[str, str]] = []
        if include_dotfiles and "dotfiles" in selected_setups:
            option_choices.extend((f"dotfile:{spec}", label) for spec, label in dotfile_options)
        if include_preferences:
            option_choices.append(
                (
                    "pref:welcome_image",
                    "Preference: show a welcome image when future shell startup support is enabled",
                )
            )
        option_selected = {f"dotfile:{name}" for name in selected_dotfiles}
        if selected_welcome_image:
            option_selected.add("pref:welcome_image")
        result = checkbox_menu(
            title="Options",
            help_text="Choose dotfile packages and optional preferences.",
            choices=option_choices,
            selected=option_selected,
        )
        if result is BACK:
            step -= 1
            continue
        cancel_if_requested(result)
        selected = cast(set[str], result)
        selected_dotfiles = {
            item.removeprefix("dotfile:") for item in selected if item.startswith("dotfile:")
        }
        selected_welcome_image = "pref:welcome_image" in selected
        step += 1

    if selected_welcome_image:
        image = click.prompt(
            "Image path or name",
            default="wallpapers/abstract.png",
            show_default=True,
        ).strip()
        preferences = InstallPreferences(welcome_image=image or None)

    selected_groups_list, package_names = selection.package_selection(
        manifest, selected_package_names
    )
    if not selected_package_phase:
        selected_groups_list = []
        package_names = []
    setup_names = [setup for setup in visible_setup_choices if setup in selected_setups]
    if selected_package_phase:
        setup_names = [*package_setup_names, *setup_names]
    dotfile_packages = [spec for spec, _label in dotfile_options if spec in selected_dotfiles]
    if not package_names:
        console.print(
            f"[yellow]No packages selected; package {package_action} will be skipped.[/yellow]"
        )
    if not setup_names:
        console.print("[yellow]No setup phases selected.[/yellow]")
    if include_dotfiles and "dotfiles" in selected_setups and not dotfile_packages:
        console.print(
            "[yellow]No dotfile packages selected; dotfile linking will be skipped.[/yellow]"
        )

    _render_selection_summary(
        console, selected_groups_list, package_names, dotfile_packages, setup_names, preferences
    )
    return InstallSelection(
        groups=selected_groups_list,
        package_names=package_names,
        dotfile_packages=dotfile_packages,
        setup_names=setup_names,
        preferences=preferences,
    )


def _packages_for_section_menu(
    manifest: Manifest,
    section_id: str,
    selected_sections: set[str],
    sections: list[tuple[str, str, str, tuple[str, ...]]],
) -> list[Package]:
    section_groups = dict((item[0], item[3]) for item in sections)[section_id]
    section_group_set = set(section_groups)
    return [
        package
        for package in manifest.packages
        if set(package.groups) & section_group_set
        and _display_section_for_package(package, selected_sections, sections) == section_id
    ]


def _display_section_for_package(
    package: Package,
    selected_sections: set[str],
    sections: list[tuple[str, str, str, tuple[str, ...]]],
) -> str | None:
    package_groups = set(package.groups)
    for section_id, _name, _description, groups in sections:
        if section_id in selected_sections and package_groups & set(groups):
            return section_id
    return None


def _visible_setup_choices(setup_choices: list[str]) -> list[str]:
    return [setup for setup in setup_choices if setup not in _PACKAGE_UPDATE_SETUPS]


def _package_setup_names(setup_choices: list[str]) -> list[str]:
    return [setup for setup in setup_choices if setup in _PACKAGE_UPDATE_SETUPS]


def _package_phase_label(package_action: str) -> str:
    if package_action == "update":
        return "Phase: update/upgrade packages from manifest"
    return "Phase: install packages from manifest"


def _ordered_selected_package_sections(
    sections: list[tuple[str, str, str, tuple[str, ...]]],
    selected_sections: set[str],
    selected_groups: set[str],
) -> list[str]:
    section_ids: list[str] = []
    for section_id, _name, _description, section_groups in sections:
        if section_id not in selected_sections:
            continue
        if any(group in selected_groups for group in section_groups):
            section_ids.append(section_id)
    return section_ids


def _section_by_id(
    sections: list[tuple[str, str, str, tuple[str, ...]]], section_id: str
) -> tuple[str, str, str, tuple[str, ...]]:
    for section in sections:
        if section[0] == section_id:
            return section
    raise KeyError(section_id)


def _default_groups_after_tool_section_change(
    manifest: Manifest,
    selected_sections: set[str],
    previous_sections: set[str],
    selected_groups: set[str],
) -> set[str]:
    groups: set[str] = set()
    for section_id, _name, _description, section_groups in selection.available_tool_sections(
        manifest
    ):
        if section_id not in selected_sections:
            continue
        section_group_set = set(section_groups)
        if section_id in previous_sections:
            groups.update(selected_groups & section_group_set)
        else:
            groups.update(section_group_set)
    return groups


def _tool_section_label(
    manifest: Manifest,
    section_id: str,
    name: str,
    description: str,
    groups: tuple[str, ...],
) -> str:
    examples = _tool_examples(manifest, groups)
    group_names = ", ".join(groups)
    suffix = f" — e.g. {examples}" if examples else ""
    return f"Packages: {name} ({group_names}) — {description}{suffix}"


def _tool_examples(manifest: Manifest, groups: tuple[str, ...]) -> str:
    wanted = set(groups)
    examples: list[str] = []
    for package in manifest.packages:
        if not (wanted & package.groups):
            continue
        name = package.binary or package.name
        if name not in examples:
            examples.append(name)
        if len(examples) == 5:
            break
    if not examples:
        return ""
    text = ", ".join(examples)
    if any(
        wanted & package.groups and (package.binary or package.name) not in examples
        for package in manifest.packages
    ):
        text += ", …"
    return text


def _phase_label(setup: str) -> str:
    labels = {
        "bootstrap": "Phase: bootstrap prerequisites",
        "post_bootstrap": "Phase: post-package bootstrap",
        "dotfiles": "Phase: dotfile import",
        "plugins": "Phase: plugin install/update",
        "brew_casks": "Phase: upgrade Homebrew casks",
        "brew_cleanup": "Phase: Homebrew cleanup",
    }
    return labels.get(setup, f"Phase: {_SETUP_LABELS[setup]}")


def _dotfile_options(repo_root: Path) -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = []
    for package in dotfiles.iter_packages(repo_root):
        if package.name == "config":
            options.extend(_config_dotfile_options(package))
            continue
        options.append((package.name, f"Dotfiles: {_humanize_dotfile_name(package.name)}"))
    return options


def _config_dotfile_options(package: Path) -> list[tuple[str, str]]:
    config_root = package / ".config"
    options: list[tuple[str, str]] = []
    if config_root.is_dir():
        for child in sorted(config_root.iterdir()):
            spec = f"config:.config/{child.name}"
            options.append((spec, f"Dotfiles: {_humanize_dotfile_name(child.name)}"))
    for child in sorted(package.iterdir()):
        if child.name == ".config":
            continue
        spec = f"config:{child.name}"
        options.append((spec, f"Dotfiles: {_humanize_dotfile_name(child.name)}"))
    return options


def _humanize_dotfile_name(name: str) -> str:
    labels = {
        "atuin": "Atuin shell history",
        "claude": "Claude",
        "ghostty": "Ghostty terminal",
        "git": "Git",
        "k9s": "K9s",
        "navi": "navi cheatsheets",
        "nvim": "Neovim",
        "oh-my-posh": "oh-my-posh prompt",
        "tmux": "tmux",
        "vim": "Vim",
        "zsh": "Zsh",
    }
    return labels.get(name, name.replace("-", " "))


def _default_package_selection_after_group_change(
    manifest: Manifest, selected_groups: set[str], selected_package_names: set[str]
) -> set[str]:
    packages = selection.packages_for_groups(manifest, selected_groups)
    package_names = {package.name for package in packages}
    kept = selected_package_names & package_names
    return kept or package_names


def _package_label(package: Package) -> str:
    binary = package.binary or package.name
    description = f" — {package.description}" if package.description else ""
    return f"{package.name} ({binary}){description}"


def _choose_packages_by_group(
    console: Console,
    manifest: Manifest,
    package_action: str,
) -> tuple[list[str], list[str]]:
    console.print("[bold]Tools and packages[/bold]")
    selected_names: set[str] = set()
    selected_groups: set[str] = set()
    packages_by_name = {package.name: package for package in manifest.packages}

    for group in manifest.all_groups():
        packages = sorted(
            [package for package in manifest.packages if group in package.groups],
            key=lambda p: p.name,
        )
        if not packages:
            continue
        _render_group_packages(console, group, packages)
        if not click.confirm(f"{package_action.title()} {group} tools?", default=True):
            continue
        if click.confirm(f"Customize individual {group} packages?", default=False):
            chosen = [
                package
                for package in packages
                if click.confirm(f"  {package_action} {package.name}?", default=True)
            ]
        else:
            chosen = packages
        for package in chosen:
            selected_names.add(package.name)
            selected_groups.update(package.groups)

    if not selected_names:
        console.print(
            f"[yellow]No packages selected; package {package_action} will be skipped.[/yellow]"
        )
    ordered_names = [p.name for p in manifest.packages if p.name in selected_names]
    ordered_groups = [g for g in manifest.all_groups() if g in selected_groups]

    # Include all groups for selected multi-group tools so dependent setup/plugin
    # phases follow the actual package choices.
    for name in ordered_names:
        ordered_groups.extend(g for g in packages_by_name[name].groups if g not in ordered_groups)
    return ordered_groups, ordered_names


def _render_group_packages(console: Console, group: str, packages: list[Package]) -> None:
    table = Table(title=f"{group} tools", title_justify="left")
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("Binary", no_wrap=True)
    table.add_column("Description")
    for package in packages:
        table.add_row(package.name, package.binary or package.name, package.description or "")
    console.print(table)


def _choose_setups(console: Console, setup_choices: list[str]) -> list[str]:
    console.print()
    console.print("[bold]Setups[/bold]")
    selected: list[str] = []
    for setup in setup_choices:
        if click.confirm(_SETUP_LABELS[setup] + "?", default=True):
            selected.append(setup)
    if not selected:
        console.print("[yellow]No setup phases selected.[/yellow]")
    return selected


def _choose_dotfile_packages(console: Console, repo_root: Path) -> list[str]:
    packages = [pkg.name for pkg in dotfiles.iter_packages(repo_root)]
    if not packages:
        return []

    console.print()
    console.print("[bold]Dotfile import[/bold]")
    console.print("Every dotfile package is selected by default.")
    selected: list[str] = []
    for package in packages:
        if click.confirm(f"Import/link dotfiles/{package}?", default=True):
            selected.append(package)
    if not selected:
        console.print(
            "[yellow]No dotfile packages selected; dotfile linking will be skipped.[/yellow]"
        )
    return selected


def _choose_preferences(console: Console) -> InstallPreferences:
    console.print()
    console.print("[bold]Shell startup preferences[/bold]")
    if not click.confirm(
        "Show a welcome image when future shell startup support is enabled?", default=False
    ):
        return InstallPreferences()
    image = click.prompt(
        "Image path or name",
        default="wallpapers/abstract.png",
        show_default=True,
    ).strip()
    return InstallPreferences(welcome_image=image or None)


def _render_selection_summary(
    console: Console,
    groups: list[str] | None,
    package_names: list[str] | None,
    dotfile_packages: list[str] | None,
    setup_names: list[str] | None,
    preferences: InstallPreferences,
) -> None:
    console.print()
    if groups is None:
        console.print("Selected package groups: [bold]all[/bold]")
    else:
        console.print("Selected package groups: " + ", ".join(f"[bold]{g}[/bold]" for g in groups))
    if package_names is not None:
        if package_names:
            console.print(f"Selected packages: [bold]{len(package_names)} package(s)[/bold]")
        else:
            console.print("Selected packages: [yellow]none[/yellow]")
    if setup_names is not None:
        if setup_names:
            console.print("Selected setups: " + ", ".join(f"[bold]{s}[/bold]" for s in setup_names))
        else:
            console.print("Selected setups: [yellow]none[/yellow]")
    if dotfile_packages is not None:
        if dotfile_packages:
            console.print(
                "Dotfile import: " + ", ".join(f"[bold]{p}[/bold]" for p in dotfile_packages)
            )
        else:
            console.print("Dotfile import: [yellow]none[/yellow]")
    if preferences.welcome_image:
        console.print(f"Welcome image preference: [bold]{preferences.welcome_image}[/bold]")
    else:
        console.print("Welcome image preference: disabled")
    console.print()


def _wants_setup(setup_names: list[str] | None, setup: str) -> bool:
    return setup_names is None or setup in setup_names
