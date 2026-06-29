"""Per-tool installation backends (brew/apt/cargo/npm/pipx).

Every backend implements the :class:`Backend` protocol so the install/update
commands can iterate generically over packages and dispatch to the right one.
"""

from __future__ import annotations

from typing import Protocol, cast

from wkst.platform import PlatformInfo


class Backend(Protocol):
    """Common interface every backend must satisfy."""

    name: str

    def is_available(self, platform_info: PlatformInfo, /) -> bool:
        """True if this backend can run on the current platform."""
        ...

    def is_installed(self, ident: str, /, **kwargs: object) -> bool:
        """True if the package is already installed."""
        ...

    def install(self, ident: str, /, *, dry_run: bool = False, **kwargs: object) -> bool:
        """Install the package; return True on success."""
        ...

    def update(self, ident: str, /, *, dry_run: bool = False, **kwargs: object) -> bool:
        """Update the package; return True on success."""
        ...

    def uninstall(self, ident: str, /, *, dry_run: bool = False, **kwargs: object) -> bool:
        """Uninstall the package; return True on success."""
        ...

    def update_all(self, *, dry_run: bool = False) -> bool:
        """Update everything this backend manages globally; True on success."""
        ...


from wkst.backends.apt import AptBackend  # noqa: E402
from wkst.backends.brew import BrewBackend  # noqa: E402
from wkst.backends.cargo import CargoBackend  # noqa: E402
from wkst.backends.claude import ClaudeBackend  # noqa: E402
from wkst.backends.npm import NpmBackend  # noqa: E402
from wkst.backends.pipx import PipxBackend  # noqa: E402


def all_backends() -> dict[str, Backend]:
    """Return one shared instance of each backend."""
    backends = {
        "brew": BrewBackend(),
        "apt": AptBackend(),
        "cargo": CargoBackend(),
        "npm": NpmBackend(),
        "pipx": PipxBackend(),
        "claude": ClaudeBackend(),
    }
    return cast(dict[str, Backend], backends)


__all__ = [
    "AptBackend",
    "Backend",
    "BrewBackend",
    "CargoBackend",
    "ClaudeBackend",
    "NpmBackend",
    "PipxBackend",
    "all_backends",
]
