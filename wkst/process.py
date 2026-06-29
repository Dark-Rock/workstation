"""Subprocess helpers with retry, dry-run, and structured logging."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from wkst.logging import log


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run(
    cmd: Sequence[str],
    *,
    dry_run: bool = False,
    check: bool = False,
    retries: int = 0,
    backoff: float = 2.0,
    capture: bool = True,
    env: Mapping[str, str] | None = None,
    quiet: bool = False,
) -> RunResult:
    """Run a command with optional retry and dry-run.

    Args:
        cmd: Argument vector.
        dry_run: Log the command and return a stub success result.
        check: Raise CalledProcessError on non-zero exit (after retries exhausted).
        retries: Number of additional attempts after the first failure.
        backoff: Base seconds for exponential backoff (1, 2, 4, 8 ...).
        capture: Capture stdout/stderr (set False to stream to terminal).
        env: Environment overrides; merged on top of os.environ.
        quiet: Suppress the per-attempt INFO log line (still logs failures).
    """
    if not quiet:
        log.info(f"$ {_format_cmd(cmd)}")

    if dry_run:
        return RunResult(returncode=0, stdout="", stderr="")

    full_env = None
    if env is not None:
        full_env = {**os.environ, **env}

    last: RunResult | None = None
    for attempt in range(retries + 1):
        try:
            proc = subprocess.run(
                list(cmd),
                capture_output=capture,
                text=capture,
                env=full_env,
                check=False,
            )
        except FileNotFoundError as exc:
            log.error(f"Command not found: {cmd[0]} ({exc})")
            if check:
                raise
            return RunResult(returncode=127, stdout="", stderr=str(exc))

        last = RunResult(
            returncode=proc.returncode,
            stdout=proc.stdout if capture else "",
            stderr=proc.stderr if capture else "",
        )

        if last.ok:
            return last

        if attempt < retries:
            wait = backoff**attempt
            log.warn(
                f"command failed (rc={last.returncode}), retrying in {wait:.0f}s "
                f"({attempt + 1}/{retries})"
            )
            time.sleep(wait)
            continue
        break

    assert last is not None
    if check:
        raise subprocess.CalledProcessError(
            last.returncode, list(cmd), output=last.stdout, stderr=last.stderr
        )
    return last


def _format_cmd(cmd: Sequence[str]) -> str:
    parts: list[str] = []
    for part in cmd:
        if any(c.isspace() for c in part) or not part:
            parts.append(f'"{part}"')
        else:
            parts.append(part)
    return " ".join(parts)
