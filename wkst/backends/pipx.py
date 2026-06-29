"""pipx backend."""

from __future__ import annotations

from wkst.platform import PlatformInfo, command_exists
from wkst.process import run


class PipxBackend:
    name = "pipx"

    def is_available(self, _: PlatformInfo) -> bool:
        return command_exists("pipx")

    def is_installed(self, ident: str, **_: object) -> bool:
        result = run(["pipx", "list", "--short"], capture=True, quiet=True)
        if not result.ok:
            return False
        for line in result.stdout.splitlines():
            head = line.split()
            if head and head[0] == ident:
                return True
        return False

    def install(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        if self.is_installed(ident):
            return self.update(ident, dry_run=dry_run)
        return run(
            ["pipx", "install", ident],
            dry_run=dry_run,
            retries=1,
            capture=False,
        ).ok

    def update(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        return run(["pipx", "upgrade", ident], dry_run=dry_run, capture=False).ok

    def uninstall(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        return run(["pipx", "uninstall", ident], dry_run=dry_run, capture=False).ok

    def update_all(self, *, dry_run: bool = False) -> bool:
        return run(["pipx", "upgrade-all"], dry_run=dry_run, capture=False).ok
