"""Shared package-installation pipeline used by ``install`` and ``update``.

This module owns the per-package "resolve backend, dispatch, accumulate
results" logic so install/update behave identically aside from which backend
method they call. It enforces an install order: ``core`` group first (so
languages/runtimes are present before per-language backends run).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from wkst import render
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
    with render.live_progress(len(ordered), operation_label) as bar:
        for pkg in ordered:
            outcome = _process(
                pkg=pkg,
                backends=backends,
                platform_info=platform_info,
                operation=operation,
                operation_label=operation_label,
                dry_run=dry_run,
                bar=bar,
            )
            outcomes.append(outcome)
            bar.advance(package=outcome.package, ok=outcome.ok, skipped=outcome.skipped)
    return outcomes


def _process(
    *,
    pkg: Package,
    backends: dict[str, Backend],
    platform_info: PlatformInfo,
    operation: Operation,
    operation_label: str,
    dry_run: bool,
    bar: render._NoOpProgress | render._RichProgress,
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
    # Pause the live region around the backend op: some backends (notably brew)
    # stream directly to the TTY and would otherwise collide with the bar.
    bar.pause()
    try:
        ok = operation(backend, ident, kwargs, dry_run)
    finally:
        bar.resume()
    if not ok:
        log.warn(f"  {pkg.name}: {operation_label} failed")
    return Outcome(package=pkg.name, backend=backend_name, ok=ok)


def render_summary(outcomes: list[Outcome]) -> int:
    """Render a final summary; return a process exit code.

    Rich path: a colored outcome table plus per-failure panels with fix hints.
    Always emits a single machine-readable tally line so scripts/CI grepping the
    output stay stable regardless of TTY/rich state.
    """
    failed = [o for o in outcomes if not o.ok]
    skipped = [o for o in outcomes if o.skipped]
    succeeded = [o for o in outcomes if o.ok and not o.skipped]

    if render.rich_enabled():
        render.console().print(render.outcome_table(outcomes))
    else:
        log.info("===== summary =====")
        log.info(f"  ok:      {len(succeeded)}")
        log.info(f"  skipped: {len(skipped)}")

    # Always-on, parseable tally (stable contract for automation).
    log.info(f"summary: ok={len(succeeded)} skipped={len(skipped)} failed={len(failed)}")

    if failed:
        for o in failed:
            render.print_failure(
                title=f"{o.package} failed",
                lines=[f"backend: {o.backend}"],
                hint=render.fix_hint_for(o),
            )
        return 1
    log.success("All operations completed successfully")
    return 0
