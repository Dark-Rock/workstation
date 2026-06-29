"""Homebrew (formula + cask) backend."""

from __future__ import annotations

from wkst.logging import log
from wkst.platform import PlatformInfo, command_exists
from wkst.process import run


class BrewBackend:
    name = "brew"

    def __init__(self) -> None:
        self._updated = False

    def is_available(self, platform_info: PlatformInfo) -> bool:
        return platform_info.is_macos and command_exists("brew")

    def _ensure_metadata(self, *, dry_run: bool) -> None:
        if self._updated:
            return
        log.info("brew: refreshing metadata")
        run(["brew", "update"], dry_run=dry_run, retries=2, capture=False)
        self._updated = True

    def is_installed(self, ident: str, *, brew_type: object = "formula", **_: object) -> bool:
        flag = "--cask" if brew_type == "cask" else "--formula"
        return run(["brew", "list", flag, ident], capture=True, quiet=True).ok

    def install(
        self,
        ident: str,
        *,
        dry_run: bool = False,
        brew_type: object = "formula",
        binary: object = None,
        **_: object,
    ) -> bool:
        self._ensure_metadata(dry_run=dry_run)
        binary_name = str(binary) if binary is not None else None
        if not dry_run:
            brew_managed = self.is_installed(ident, brew_type=brew_type)
            if not brew_managed and binary_name and command_exists(binary_name):
                log.info(f"brew: {binary_name!r} already installed outside Homebrew — skipping")
                return True
            if brew_managed:
                return self.update(ident, dry_run=dry_run, brew_type=brew_type, binary=binary_name)
        cmd = ["brew", "install"]
        if brew_type == "cask":
            cmd.append("--cask")
        cmd.append(ident)
        return run(cmd, dry_run=dry_run, retries=2, capture=False).ok

    def update(
        self,
        ident: str,
        *,
        dry_run: bool = False,
        brew_type: object = "formula",
        binary: object = None,
        **_: object,
    ) -> bool:
        self._ensure_metadata(dry_run=dry_run)
        binary_name = str(binary) if binary is not None else None
        if (
            not dry_run
            and binary_name
            and command_exists(binary_name)
            and not self.is_installed(ident, brew_type=brew_type)
        ):
            log.info(f"brew: {binary_name!r} already installed outside Homebrew — skipping upgrade")
            return True
        cmd = ["brew", "upgrade"]
        if brew_type == "cask":
            cmd.append("--cask")
        cmd.append(ident)
        result = run(cmd, dry_run=dry_run, capture=True)
        if result.ok:
            return True
        # `brew upgrade` returns non-zero when there is no upgrade available.
        if "already installed" in (result.stderr + result.stdout).lower():
            return True
        log.warn(f"brew upgrade {ident} returned rc={result.returncode}")
        return False

    def uninstall(
        self,
        ident: str,
        *,
        dry_run: bool = False,
        brew_type: object = "formula",
        **_: object,
    ) -> bool:
        cmd = ["brew", "uninstall"]
        if brew_type == "cask":
            cmd.append("--cask")
        cmd.append(ident)
        return run(cmd, dry_run=dry_run, capture=False).ok

    def update_all(self, *, dry_run: bool = False) -> bool:
        self.update_metadata(dry_run=dry_run)
        ok = True
        ok &= self.upgrade_formulae(dry_run=dry_run)
        ok &= self.upgrade_casks(dry_run=dry_run)
        self.cleanup(dry_run=dry_run)
        return ok

    def update_metadata(self, *, dry_run: bool = False) -> bool:
        self._ensure_metadata(dry_run=dry_run)
        return True

    def upgrade_formulae(self, *, dry_run: bool = False) -> bool:
        self._ensure_metadata(dry_run=dry_run)
        return run(["brew", "upgrade"], dry_run=dry_run, capture=False).ok

    def upgrade_casks(self, *, dry_run: bool = False) -> bool:
        self._ensure_metadata(dry_run=dry_run)
        return run(["brew", "upgrade", "--cask"], dry_run=dry_run, capture=False).ok

    def cleanup(self, *, dry_run: bool = False) -> bool:
        return run(["brew", "cleanup"], dry_run=dry_run, capture=False).ok
