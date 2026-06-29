"""Stow-style dotfile linker.

Layout:

    dotfiles/<pkg>/<relative-path-from-$HOME>

Example: ``dotfiles/zsh/.zshrc`` symlinks to ``$HOME/.zshrc``.

Algorithm: walk each package, find every regular file (and broken-symlink
file), and create a symlink in ``$HOME`` at the equivalent path. Parent
directories are real dirs in ``$HOME`` (we never replace ``$HOME/.config``
with a symlink — only individual files inside it).
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from wkst.logging import log


class Action(Enum):
    LINKED = "linked"
    ALREADY = "already"
    REPLACED = "replaced"
    BACKED_UP = "backed-up"
    RESTORED = "restored"
    PURGED = "purged"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class LinkResult:
    target: Path  # path in $HOME
    source: Path  # path in repo
    action: Action
    detail: str = ""


def dotfiles_root(repo_root: Path) -> Path:
    return repo_root / "dotfiles"


def iter_packages(repo_root: Path) -> list[Path]:
    root = dotfiles_root(repo_root)
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir())


def iter_files(pkg_root: Path) -> Iterable[Path]:
    """All regular files (or broken symlinks) under ``pkg_root``, recursive."""
    for p in pkg_root.rglob("*"):
        if p.is_dir():
            continue
        # Skip macOS metadata cruft.
        if p.name == ".DS_Store":
            continue
        yield p


def sync_all(
    repo_root: Path,
    home: Path,
    *,
    packages: list[str] | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> list[LinkResult]:
    results: list[LinkResult] = []
    wanted_packages, wanted_prefixes = _parse_package_specs(packages)
    for pkg in iter_packages(repo_root):
        prefixes = wanted_prefixes.get(pkg.name, ())
        if wanted_packages is not None and pkg.name not in wanted_packages and not prefixes:
            log.info(f"sync: {pkg.name:<10s} skipped by menu")
            continue
        pkg_results: list[LinkResult] = []
        for source in iter_files(pkg):
            rel = source.relative_to(pkg)
            if (
                wanted_packages is not None
                and pkg.name not in wanted_packages
                and not _matches_prefix(rel, prefixes)
            ):
                continue
            target = home / rel
            pkg_results.append(_link_one(source, target, force=force, dry_run=dry_run))
        results.extend(pkg_results)
        log.info(f"sync: {pkg.name:<10s} {_pkg_summary(pkg_results)}")
    return results


def _parse_package_specs(
    packages: list[str] | None,
) -> tuple[set[str] | None, dict[str, tuple[Path, ...]]]:
    """Parse whole-package and package-subtree menu selections."""
    if packages is None:
        return None, {}
    wanted_packages: set[str] = set()
    prefixes: dict[str, list[Path]] = {}
    for spec in packages:
        if ":" not in spec:
            wanted_packages.add(spec)
            continue
        package, prefix = spec.split(":", 1)
        prefixes.setdefault(package, []).append(Path(prefix))
    return wanted_packages, {package: tuple(paths) for package, paths in prefixes.items()}


def _matches_prefix(rel: Path, prefixes: tuple[Path, ...]) -> bool:
    return any(rel == prefix or rel.is_relative_to(prefix) for prefix in prefixes)


def _pkg_summary(results: list[LinkResult]) -> str:
    """One-line per-package summary like ``80 files: 1 linked, 78 ok, 1 conflict``."""
    total = len(results)
    counts: dict[Action, int] = {}
    for r in results:
        counts[r.action] = counts.get(r.action, 0) + 1
    parts: list[str] = []
    if counts.get(Action.LINKED):
        parts.append(f"{counts[Action.LINKED]} linked")
    if counts.get(Action.ALREADY):
        parts.append(f"{counts[Action.ALREADY]} ok")
    if counts.get(Action.SKIPPED):
        parts.append(f"{counts[Action.SKIPPED]} conflict")
    if counts.get(Action.FAILED):
        parts.append(f"{counts[Action.FAILED]} failed")
    summary = ", ".join(parts) if parts else "no files"
    return f"{total:>3} files: {summary}"


def adopt(
    repo_root: Path,
    home: Path,
    target_path: Path,
    *,
    dry_run: bool = False,
) -> list[LinkResult]:
    """Move an existing $HOME file (or every file in a $HOME directory) into
    the repo and re-symlink each one.

    The target must live inside $HOME. The repo destination is derived by
    placing each file under the appropriate package: top-level dotfiles go
    under ``dotfiles/<basename-without-leading-dot>/`` and
    ``$HOME/.config/<x>/...`` files go under ``dotfiles/config/.config/<x>/...``.

    Symlinks (already-adopted files, OS junk like Finder aliases) are skipped.
    """
    target = target_path.expanduser()
    # We don't fully resolve() so that already-adopted symlinks can be detected
    # before we follow them into the repo.
    if not target.exists() and not target.is_symlink():
        log.error(f"add: {target} does not exist")
        return [LinkResult(target, target, Action.FAILED, "missing")]

    if target.is_symlink():
        log.warn(f"add: {target} is already a symlink — skipping")
        return [LinkResult(target, target, Action.SKIPPED, "already a symlink")]

    target = target.resolve()
    try:
        target.relative_to(home)
    except ValueError:
        log.error(f"add: {target} is not inside {home}")
        return [LinkResult(target, target, Action.FAILED, "outside $HOME")]

    if target.is_file():
        return [_adopt_one(repo_root, home, target, dry_run=dry_run)]
    if target.is_dir():
        return _adopt_dir(repo_root, home, target, dry_run=dry_run)
    log.error(f"add: {target} is neither a file nor a directory")
    return [LinkResult(target, target, Action.FAILED, "unsupported file type")]


def _adopt_dir(
    repo_root: Path,
    home: Path,
    directory: Path,
    *,
    dry_run: bool,
) -> list[LinkResult]:
    """Recursively adopt every regular file inside ``directory``."""
    results: list[LinkResult] = []
    files = sorted(p for p in directory.rglob("*") if _adoptable(p))
    if not files:
        log.warn(f"add: {directory} contains no adoptable files")
        return results
    log.info(f"add: {directory} ({len(files)} file(s))")
    for f in files:
        results.append(_adopt_one(repo_root, home, f, dry_run=dry_run))
    return results


def _adoptable(path: Path) -> bool:
    """Files we should adopt: regular files, no symlinks, no junk."""
    if path.is_symlink():
        return False
    if not path.is_file():
        return False
    if path.name == ".DS_Store":
        return False
    # Skip nested git/lock metadata: don't accidentally swallow another repo.
    parts = set(path.parts)
    return ".git" not in parts and "node_modules" not in parts


def _adopt_one(
    repo_root: Path,
    home: Path,
    target: Path,
    *,
    dry_run: bool,
) -> LinkResult:
    rel = target.relative_to(home)
    pkg = _pick_package(rel)
    source = dotfiles_root(repo_root) / pkg / rel
    if source.exists():
        log.error(f"add: {source} already exists in repo")
        return LinkResult(target, source, Action.FAILED, "exists in repo")

    log.info(f"add: {target} -> dotfiles/{pkg}/{rel}")
    if dry_run:
        return LinkResult(target, source, Action.SKIPPED, "dry-run")

    source.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(target), str(source))
    return _link_one(source, target, force=False, dry_run=False)


def _pick_package(rel: Path) -> str:
    # ``.config/foo/bar`` -> ``config``
    if rel.parts[:1] == (".config",):
        return "config"
    # ``.claude/...`` -> ``claude``
    if rel.parts[:1] == (".claude",):
        return "claude"
    # ``.zshrc`` -> ``zsh``; ``.vimrc`` -> ``vim``; ``.gitconfig`` -> ``git``
    head = rel.parts[0]
    name = head.lstrip(".")
    aliases = {"zshrc": "zsh", "zprofile": "zsh", "vimrc": "vim", "gitconfig": "git"}
    return aliases.get(name, name or "misc")


def _link_one(source: Path, target: Path, *, force: bool, dry_run: bool) -> LinkResult:
    if not source.exists() and not source.is_symlink():
        return LinkResult(target, source, Action.FAILED, "source missing")

    # Already linked correctly?
    if target.is_symlink():
        try:
            existing = target.resolve(strict=False)
        except OSError as exc:
            return LinkResult(target, source, Action.FAILED, str(exc))
        if existing == source.resolve():
            return LinkResult(target, source, Action.ALREADY)

    # Conflict: real file or wrong link.
    if target.exists() or target.is_symlink():
        if not force:
            log.debug(f"  conflict: {target} (use --force to replace)")
            return LinkResult(target, source, Action.SKIPPED, "conflict")
        backup = _backup_path(target)
        log.info(f"  backup {target.name} -> {backup.name}")
        if not dry_run:
            target.replace(backup)
        # else dry-run: simulate as if it moved.

    log.debug(f"  link {target} -> {source}")
    if dry_run:
        return LinkResult(target, source, Action.LINKED, "dry-run")

    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.symlink_to(source)
    except OSError as exc:
        return LinkResult(target, source, Action.FAILED, str(exc))
    return LinkResult(target, source, Action.LINKED)


def _backup_path(target: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return target.with_name(f"{target.name}.bak.{ts}")


def remove(
    repo_root: Path,
    home: Path,
    target_path: Path,
    *,
    purge: bool = False,
    dry_run: bool = False,
) -> list[LinkResult]:
    """Inverse of :func:`adopt`. Detach a $HOME path from the repo.

    Default (restore) mode: replace each managed symlink in $HOME with the
    real file from the repo, then delete the now-empty repo entry.

    Purge mode (``purge=True``): delete both the symlink and the repo entry —
    you lose the file content. Use only if you don't want the config anymore.

    Accepts a single file or a directory; directories are walked recursively
    and only files that are managed symlinks (pointing into ``dotfiles/``) are
    touched.
    """
    target = target_path.expanduser()
    if not target.exists() and not target.is_symlink():
        log.error(f"remove: {target} does not exist")
        return [LinkResult(target, target, Action.FAILED, "missing")]

    # Don't resolve up front: a managed symlink should be inspected as-is.
    if target.is_symlink() or target.is_file():
        return [_remove_one(repo_root, home, target, purge=purge, dry_run=dry_run)]
    if target.is_dir():
        return _remove_dir(repo_root, home, target, purge=purge, dry_run=dry_run)
    log.error(f"remove: {target} is neither a file nor a directory")
    return [LinkResult(target, target, Action.FAILED, "unsupported file type")]


def unlink_all(repo_root: Path, home: Path, *, dry_run: bool = False) -> list[LinkResult]:
    """Remove managed symlinks from $HOME without deleting repo files."""
    repo_dotfiles = dotfiles_root(repo_root).resolve()
    results: list[LinkResult] = []
    for pkg in iter_packages(repo_root):
        for source in iter_files(pkg):
            target = home / source.relative_to(pkg)
            if not _is_managed_symlink(target, repo_dotfiles):
                continue
            log.info(f"unlink: {target}")
            if dry_run:
                results.append(LinkResult(target, source, Action.SKIPPED, "dry-run"))
                continue
            try:
                target.unlink()
            except OSError as exc:
                results.append(LinkResult(target, source, Action.FAILED, str(exc)))
            else:
                results.append(LinkResult(target, source, Action.RESTORED, "unlinked"))
    return results


def _remove_dir(
    repo_root: Path,
    home: Path,
    directory: Path,
    *,
    purge: bool,
    dry_run: bool,
) -> list[LinkResult]:
    repo_dotfiles = dotfiles_root(repo_root).resolve()
    candidates = sorted(p for p in directory.rglob("*") if p.is_symlink() or p.is_file())
    managed = [p for p in candidates if _is_managed_symlink(p, repo_dotfiles)]
    if not managed:
        log.warn(f"remove: {directory} contains no managed symlinks")
        return []
    log.info(f"remove: {directory} ({len(managed)} managed file(s))")
    return [_remove_one(repo_root, home, p, purge=purge, dry_run=dry_run) for p in managed]


def _is_managed_symlink(path: Path, repo_dotfiles: Path) -> bool:
    if not path.is_symlink():
        return False
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        return False
    try:
        resolved.relative_to(repo_dotfiles)
    except ValueError:
        return False
    return True


def _remove_one(
    repo_root: Path,
    home: Path,
    target: Path,
    *,
    purge: bool,
    dry_run: bool,
) -> LinkResult:
    repo_dotfiles = dotfiles_root(repo_root).resolve()

    # Refuse anything outside $HOME.
    try:
        target.resolve(strict=False).parent.relative_to(home)
    except ValueError:
        # Allow $HOME itself or top-level dotfiles; only reject true outsiders.
        try:
            target.relative_to(home)
        except ValueError:
            log.error(f"remove: {target} is not inside {home}")
            return LinkResult(target, target, Action.FAILED, "outside $HOME")

    if not target.is_symlink():
        log.warn(f"remove: {target} is not a symlink — not managed by wkst")
        return LinkResult(target, target, Action.SKIPPED, "not a symlink")

    try:
        source = target.resolve(strict=False)
    except OSError as exc:
        log.error(f"remove: cannot resolve {target}: {exc}")
        return LinkResult(target, target, Action.FAILED, str(exc))

    try:
        source.relative_to(repo_dotfiles)
    except ValueError:
        log.warn(f"remove: {target} -> {source} (outside repo, skipping)")
        return LinkResult(target, source, Action.SKIPPED, "external symlink")

    if purge:
        log.info(f"remove: PURGE {target}  (deletes repo file too)")
        if dry_run:
            return LinkResult(target, source, Action.SKIPPED, "dry-run")
        try:
            target.unlink()
            if source.exists():
                source.unlink()
        except OSError as exc:
            return LinkResult(target, source, Action.FAILED, str(exc))
        _prune_empty_parents(source.parent, stop_at=repo_dotfiles)
        return LinkResult(target, source, Action.PURGED)

    log.info(f"remove: restore {target}  (move repo copy back into $HOME)")
    if dry_run:
        return LinkResult(target, source, Action.SKIPPED, "dry-run")

    if not source.exists():
        log.error(f"remove: {source} missing in repo (broken symlink?)")
        try:
            target.unlink()
        except OSError as exc:
            return LinkResult(target, source, Action.FAILED, str(exc))
        return LinkResult(target, source, Action.FAILED, "broken symlink")

    try:
        target.unlink()
        shutil.move(str(source), str(target))
    except OSError as exc:
        return LinkResult(target, source, Action.FAILED, str(exc))
    _prune_empty_parents(source.parent, stop_at=repo_dotfiles)
    return LinkResult(target, source, Action.RESTORED)


def _prune_empty_parents(start: Path, *, stop_at: Path) -> None:
    """rmdir empty parent dirs up to (but not including) stop_at."""
    p = start
    while p != stop_at and p.is_dir():
        try:
            next(p.iterdir())
            return  # not empty
        except StopIteration:
            try:
                p.rmdir()
            except OSError:
                return
            p = p.parent


def diff_all(repo_root: Path, home: Path) -> list[LinkResult]:
    """Report which files in the repo are not properly symlinked from $HOME."""
    results: list[LinkResult] = []
    for pkg in iter_packages(repo_root):
        for source in iter_files(pkg):
            rel = source.relative_to(pkg)
            target = home / rel
            if target.is_symlink():
                try:
                    if target.resolve() == source.resolve():
                        continue
                except OSError:
                    pass
                results.append(LinkResult(target, source, Action.FAILED, "wrong link"))
            elif target.exists():
                results.append(LinkResult(target, source, Action.FAILED, "real file"))
            else:
                results.append(LinkResult(target, source, Action.FAILED, "missing"))
    return results


def render_summary(results: list[LinkResult], *, force: bool = False) -> int:
    by_action: dict[Action, int] = {}
    for r in results:
        by_action[r.action] = by_action.get(r.action, 0) + 1
    log.info("===== sync summary =====")
    for action in Action:
        if action in by_action:
            log.info(f"  {action.value:9s}: {by_action[action]}")

    skipped = by_action.get(Action.SKIPPED, 0)
    if skipped and not force:
        log.warn(f"{skipped} dotfile(s) diverge from the repo. Next steps:")
        log.warn("  wkst diff             # see exactly which files and how")
        log.warn("  wkst sync --force     # back up real files + symlink everything")
        log.warn("  wkst sync -v          # re-run with per-file detail")

    failed = by_action.get(Action.FAILED, 0)
    return 1 if failed else 0
