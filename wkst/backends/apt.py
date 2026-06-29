"""APT backend (Debian/Ubuntu)."""

from __future__ import annotations

from wkst.logging import log
from wkst.platform import PlatformInfo, command_exists
from wkst.process import run


class AptBackend:
    name = "apt"

    def __init__(self) -> None:
        self._updated = False

    def is_available(self, platform_info: PlatformInfo) -> bool:
        return platform_info.is_linux and command_exists("apt-get")

    def _ensure_metadata(self, *, dry_run: bool) -> None:
        if self._updated:
            return
        log.info("apt: refreshing package lists")
        run(["sudo", "apt-get", "update"], dry_run=dry_run, retries=2, capture=False)
        self._updated = True

    def is_installed(self, ident: str, **_: object) -> bool:
        return run(["dpkg", "-s", ident], capture=True, quiet=True).ok

    def install(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        self._ensure_metadata(dry_run=dry_run)
        return run(
            ["sudo", "apt-get", "install", "-y", ident],
            dry_run=dry_run,
            retries=2,
            capture=False,
            env={"DEBIAN_FRONTEND": "noninteractive"},
        ).ok

    def update(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        # apt-get install -y on an installed package upgrades it if available.
        return self.install(ident, dry_run=dry_run)

    def uninstall(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        return run(
            ["sudo", "apt-get", "remove", "-y", ident],
            dry_run=dry_run,
            capture=False,
            env={"DEBIAN_FRONTEND": "noninteractive"},
        ).ok

    def update_all(self, *, dry_run: bool = False) -> bool:
        self.update_metadata(dry_run=dry_run)
        return self.upgrade_packages(dry_run=dry_run)

    def update_metadata(self, *, dry_run: bool = False) -> bool:
        self._ensure_metadata(dry_run=dry_run)
        return True

    def upgrade_packages(self, *, dry_run: bool = False) -> bool:
        self._ensure_metadata(dry_run=dry_run)
        return run(
            ["sudo", "apt-get", "upgrade", "-y"],
            dry_run=dry_run,
            capture=False,
            env={"DEBIAN_FRONTEND": "noninteractive"},
        ).ok
