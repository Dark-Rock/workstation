"""Claude Code plugins backend.

Plugins are installed/updated via the ``claude`` CLI itself (which we install
as an npm global). They are not regular packages, so this backend only exposes
``install`` and ``update``; package_id is the plugin name.
"""

from __future__ import annotations

from wkst.platform import PlatformInfo, command_exists
from wkst.process import run


class ClaudeBackend:
    name = "claude"

    def is_available(self, _: PlatformInfo) -> bool:
        return command_exists("claude")

    def is_installed(self, ident: str, **_: object) -> bool:
        # `claude plugin list` formats vary; treat presence in stdout as installed.
        result = run(["claude", "plugin", "list"], capture=True, quiet=True)
        if not result.ok:
            return False
        return ident in result.stdout

    def install(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        return run(
            ["claude", "plugin", "install", ident],
            dry_run=dry_run,
            retries=1,
            capture=False,
        ).ok

    def update(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        return run(
            ["claude", "plugin", "update", ident],
            dry_run=dry_run,
            capture=False,
        ).ok

    def uninstall(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        return run(
            ["claude", "plugin", "remove", ident],
            dry_run=dry_run,
            capture=False,
        ).ok

    def update_all(self, *, dry_run: bool = False) -> bool:
        return run(
            ["claude", "plugin", "update", "--all"],
            dry_run=dry_run,
            capture=False,
        ).ok
