"""Shared package-installation pipeline used by ``install`` and ``update``.

This module owns the per-package "resolve backend, dispatch, accumulate
results" logic so install/update behave identically aside from which backend
method they call. It enforces an install order: ``core`` group first (so
languages/runtimes are present before per-language backends run).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from wkst.backends import Backend, all_backends
from wkst.logging import log
from wkst.manifest import Manifest, Package
from wkst.platform import PlatformInfo

Operation = Callable[[Backend, str, dict[str, object], bool], bool]


@dataclass
class Outcome:
    package: str
    backend: str
    ok: bool
    skipped: bool = False
    reason: str = ""


def install_op(backend: Backend, ident: str, kwargs: dict[str, object], dry_run: bool) -> bool:
    return backend.install(ident, dry_run=dry_run, **kwargs)


def update_op(backend: Backend, ident: str, kwargs: dict[str, object], dry_run: bool) -> bool:
    return backend.update(ident, dry_run=dry_run, **kwargs)


def uninstall_op(backend: Backend, ident: str, kwargs: dict[str, object], dry_run: bool) -> bool:
    return backend.uninstall(ident, dry_run=dry_run, **kwargs)


def run_pipeline(
    *,
    manifest: Manifest,
    platform_info: PlatformInfo,
    groups: list[str] | None,
    operation: Operation,
    operation_label: str,
    dry_run: bool,
    package_names: list[str] | None = None,
) -> list[Outcome]:
    """Run ``operation`` for every applicable package, in dependency order."""
    backends = all_backends()
    applicable = manifest.for_platform(platform_info)
    selected = manifest.in_groups(applicable, groups)
    if package_names is not None:
        wanted_packages = set(package_names)
        selected = tuple(p for p in selected if p.name in wanted_packages)

    # Install order: anything in `core` first (langs/runtimes), then the rest.
    # This guarantees brew/apt installs node/python/cargo before npm/pipx/cargo
    # backends try to install their per-language globals.
    core = [p for p in selected if "core" in p.groups]
    rest = [p for p in selected if "core" not in p.groups]
    ordered = core + rest

    log.info(
        f"{operation_label}: {len(selected)} package(s) "
        f"(core={len(core)}, other={len(rest)}) on {platform_info.os.value}"
    )

    outcomes: list[Outcome] = []
    for pkg in ordered:
        outcomes.append(
            _process(
                pkg=pkg,
                backends=backends,
                platform_info=platform_info,
                operation=operation,
                operation_label=operation_label,
                dry_run=dry_run,
            )
        )
    return outcomes


def _process(
    *,
    pkg: Package,
    backends: dict[str, Backend],
    platform_info: PlatformInfo,
    operation: Operation,
    operation_label: str,
    dry_run: bool,
) -> Outcome:
    resolved = pkg.resolved_backend(platform_info)
    if resolved is None:
        log.warn(f"  {pkg.name}: no installable backend on this platform — skipping")
        return Outcome(
            package=pkg.name,
            backend="-",
            ok=True,
            skipped=True,
            reason="no backend on platform",
        )

    backend_name, ident = resolved
    backend = backends[backend_name]

    if not backend.is_available(platform_info):
        log.warn(f"  {pkg.name}: backend {backend_name!r} not available — skipping")
        return Outcome(
            package=pkg.name,
            backend=backend_name,
            ok=True,
            skipped=True,
            reason=f"{backend_name} not on PATH",
        )

    kwargs: dict[str, object] = {}
    if backend_name == "brew":
        if pkg.brew_type == "cask":
            kwargs["brew_type"] = "cask"
        kwargs["binary"] = pkg.binary or pkg.name

    log.info(f"  {operation_label} {pkg.name} via {backend_name} ({ident})")
    ok = operation(backend, ident, kwargs, dry_run)
    if not ok:
        log.warn(f"  {pkg.name}: {operation_label} failed")
    return Outcome(package=pkg.name, backend=backend_name, ok=ok)


def render_summary(outcomes: list[Outcome]) -> int:
    """Log a final summary; return a process exit code."""
    failed = [o for o in outcomes if not o.ok]
    skipped = [o for o in outcomes if o.skipped]
    succeeded = [o for o in outcomes if o.ok and not o.skipped]

    log.info("===== summary =====")
    log.info(f"  ok:      {len(succeeded)}")
    log.info(f"  skipped: {len(skipped)}")
    if failed:
        log.warn(f"  failed:  {len(failed)}")
        for o in failed:
            log.warn(f"    - {o.package} ({o.backend})")
        return 1
    log.success("All operations completed successfully")
    return 0
