"""Tests for the structured logger and its pluggable writer sink."""

from __future__ import annotations

import io

from wkst.logging import Level, Logger


def _plain_logger() -> tuple[Logger, io.StringIO]:
    stream = io.StringIO()
    logger = Logger(level=Level.INFO, stream=stream)
    logger._color = False  # force plain output regardless of test environment
    return logger, stream


def test_levels_and_format() -> None:
    logger, stream = _plain_logger()
    logger.info("hello")
    out = stream.getvalue()
    assert "INFO: hello" in out
    assert out.startswith("[")  # timestamp prefix


def test_debug_suppressed_below_level() -> None:
    logger, stream = _plain_logger()
    logger.debug("noisy")
    assert stream.getvalue() == ""


def test_success_level_emits() -> None:
    logger, stream = _plain_logger()
    logger.success("done")
    assert "SUCCESS: done" in stream.getvalue()


def test_set_writer_reroutes_emit() -> None:
    logger, stream = _plain_logger()
    captured: list[str] = []
    logger.set_writer(captured.append)
    logger.info("via sink")
    assert stream.getvalue() == ""  # nothing went to the stream
    assert len(captured) == 1
    assert "INFO: via sink" in captured[0]


def test_reset_writer_restores_stream() -> None:
    logger, stream = _plain_logger()
    captured: list[str] = []
    logger.set_writer(captured.append)
    logger.reset_writer()
    logger.info("back to stream")
    assert captured == []
    assert "INFO: back to stream" in stream.getvalue()


def test_writer_respects_level_filter() -> None:
    logger, _ = _plain_logger()
    captured: list[str] = []
    logger.set_writer(captured.append)
    logger.debug("suppressed")
    assert captured == []
