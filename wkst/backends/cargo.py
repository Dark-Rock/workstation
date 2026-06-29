"""Cargo (Rust) backend."""

from __future__ import annotations

from wkst.platform import PlatformInfo, command_exists
from wkst.process import run


class CargoBackend:
    name = "cargo"

    def is_available(self, _: PlatformInfo) -> bool:
        return command_exists("cargo")

    def is_installed(self, ident: str, **_: object) -> bool:
        # `cargo install --list` lines like "<crate> v<version>:" — match the head.
        result = run(["cargo", "install", "--list"], capture=True, quiet=True)
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
            ["cargo", "install", "--locked", ident],
            dry_run=dry_run,
            retries=1,
            capture=False,
        ).ok

    def update(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        # cargo-update provides the proper upgrade path; fall back to reinstall.
        if command_exists("cargo-install-update"):
            return run(
                ["cargo", "install-update", ident],
                dry_run=dry_run,
                capture=False,
            ).ok
        return run(
            ["cargo", "install", "--locked", "--force", ident],
            dry_run=dry_run,
            capture=False,
        ).ok

    def uninstall(self, ident: str, *, dry_run: bool = False, **_: object) -> bool:
        return run(["cargo", "uninstall", ident], dry_run=dry_run, capture=False).ok

    def update_all(self, *, dry_run: bool = False) -> bool:
        if command_exists("cargo-install-update"):
            return run(
                ["cargo", "install-update", "-a"],
                dry_run=dry_run,
                capture=False,
            ).ok
        return True
