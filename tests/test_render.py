"""Tests for the rich presentation layer (wkst/render.py).

All rendering must degrade to a no-op / plain text when rich is disabled so the
non-interactive path stays byte-stable.
"""

from __future__ import annotations

import pytest

from wkst import render
from wkst.commands.doctor import Check
from wkst.dotfiles import Action, LinkResult
from wkst.install_pipeline import Outcome
from wkst.logging import log


@pytest.fixture(autouse=True)
def _clean_color_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Neutralize ambient color env so each test sets its own gate explicitly.
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("WKST_FORCE_COLOR", raising=False)
    monkeypatch.delenv("WKST_NO_RICH", raising=False)


def test_rich_disabled_by_no_color(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    assert render.rich_enabled() is False


def test_rich_disabled_by_wkst_no_rich(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WKST_FORCE_COLOR", "1")  # would otherwise enable
    monkeypatch.setenv("WKST_NO_RICH", "1")
    assert render.rich_enabled() is False


def test_rich_disabled_when_not_a_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stderr.isatty", lambda: False, raising=False)
    assert render.rich_enabled() is False


def test_rich_enabled_by_force_color(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WKST_FORCE_COLOR", "1")
    assert render.rich_enabled() is True


def test_live_progress_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WKST_NO_RICH", "1")
    assert log._writer is None
    with render.live_progress(total=3, description="install") as bar:
        bar.advance(package="ripgrep", ok=True)  # inert, no exception
        assert log._writer is None  # logger untouched in the disabled path
    assert log._writer is None


def test_live_progress_sets_and_restores_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WKST_FORCE_COLOR", "1")
    assert log._writer is None
    with render.live_progress(total=2, description="install") as bar:
        assert log._writer is not None  # routed through the progress console
        bar.advance(package="fd", ok=True)
        bar.pause()
        bar.resume()
    assert log._writer is None  # restored on exit


def test_outcome_table_rows() -> None:
    outcomes = [
        Outcome(package="rg", backend="brew", ok=True),
        Outcome(package="x", backend="-", ok=True, skipped=True, reason="no backend"),
        Outcome(package="y", backend="cargo", ok=False),
    ]
    table = render.outcome_table(outcomes)
    assert table.row_count == 3
    assert len(table.columns) == 3


def test_doctor_table_rows() -> None:
    checks = [Check(name="a", ok=True), Check(name="b", ok=False, detail="bad")]
    table = render.doctor_table(checks)
    assert table.row_count == 2


def test_diff_table_rows(tmp_path) -> None:
    results = [
        LinkResult(tmp_path / ".zshrc", tmp_path / "repo/.zshrc", Action.FAILED, "real file"),
    ]
    table = render.diff_table(results)
    assert table.row_count == 1


def test_fix_hint_for() -> None:
    assert render.fix_hint_for(Outcome("rg", "brew", ok=False)) == "brew doctor"
    assert render.fix_hint_for(Outcome("rg", "cargo", ok=False)) == "wkst doctor"
    assert render.fix_hint_for(Outcome("rg", "-", ok=True, skipped=True)) is None


def test_print_failure_plain_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    # Capture via the logger's own stream — the global logger binds a stream at
    # import time, so neither capsys nor capfd reliably observes its output.
    import io

    monkeypatch.setenv("WKST_NO_RICH", "1")
    buf = io.StringIO()
    monkeypatch.setattr(log, "stream", buf)
    monkeypatch.setattr(log, "_color", False)
    render.print_failure("bootstrap failed", ["brew not found"], hint="see https://brew.sh")
    err = buf.getvalue()
    assert "bootstrap failed" in err
    assert "brew not found" in err
    assert "Fix: see https://brew.sh" in err
