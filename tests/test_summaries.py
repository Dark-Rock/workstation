"""Tests that summary rendering preserves exit codes and the parseable tally.

The non-interactive contract: regardless of rich state, ``render_summary`` must
return the right exit code and emit one ``summary: ok=.. skipped=.. failed=..``
line that automation can grep.
"""

from __future__ import annotations

import io

import pytest

from wkst import install_pipeline
from wkst.install_pipeline import Outcome
from wkst.logging import log


@pytest.fixture()
def captured_log(monkeypatch: pytest.MonkeyPatch) -> io.StringIO:
    """Force plain output and capture the logger's own stream."""
    monkeypatch.setenv("WKST_NO_RICH", "1")
    buf = io.StringIO()
    monkeypatch.setattr(log, "stream", buf)
    monkeypatch.setattr(log, "_color", False)
    return buf


def test_all_ok_returns_zero_and_tally(captured_log: io.StringIO) -> None:
    outcomes = [Outcome("rg", "brew", ok=True), Outcome("fd", "cargo", ok=True)]
    rc = install_pipeline.render_summary(outcomes)
    out = captured_log.getvalue()
    assert rc == 0
    assert "summary: ok=2 skipped=0 failed=0" in out


def test_failure_returns_one_and_tally(captured_log: io.StringIO) -> None:
    outcomes = [
        Outcome("rg", "brew", ok=True),
        Outcome("x", "-", ok=True, skipped=True, reason="no backend"),
        Outcome("y", "cargo", ok=False),
    ]
    rc = install_pipeline.render_summary(outcomes)
    out = captured_log.getvalue()
    assert rc == 1
    assert "summary: ok=1 skipped=1 failed=1" in out
    # Fix hint surfaced for the failed package.
    assert "wkst doctor" in out


def test_empty_outcomes_is_success(captured_log: io.StringIO) -> None:
    rc = install_pipeline.render_summary([])
    assert rc == 0
    assert "summary: ok=0 skipped=0 failed=0" in captured_log.getvalue()


def test_doctor_render_exit_codes(captured_log: io.StringIO) -> None:
    from wkst.commands import doctor

    assert doctor._render([doctor.Check(name="a", ok=True)]) == 0
    assert doctor._render([doctor.Check(name="b", ok=False, detail="bad", fix="wkst install")]) == 1
    # Non-TTY path surfaces the fix command as a plain line.
    assert "fix: wkst install" in captured_log.getvalue()
