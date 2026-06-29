"""npm globals backend."""

from __future__ import annotations

from wkst.platform import PlatformInfo, command_exists
from wkst.process import run


class NpmBackend:
    name = "npm"

    def is_available(self, _: PlatformInfo) -> bool:
        return command_exists("npm")

    def is_installed(self, ident: str, **_: object) -> bool:
        result = run(
            ["npm", "list", "-g", "--depth=0", "--parseable", ident],
            capture=True,
            quiet=True,
        )
        return result.ok and bool(result.stdout.strip())

    def install(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        return run(
            ["npm", "install", "-g", f"{ident}@latest"],
            dry_run=dry_run,
            retries=1,
            capture=False,
        ).ok

    def update(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        return self.install(ident, dry_run=dry_run)

    def uninstall(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        return run(["npm", "uninstall", "-g", ident], dry_run=dry_run, capture=False).ok

    def update_all(self, *, dry_run: bool = False) -> bool:
        return run(
            ["npm", "update", "-g"],
            dry_run=dry_run,
            capture=False,
        ).ok
