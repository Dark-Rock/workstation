"""Small prompt-toolkit menus shared by interactive wkst flows."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from typing import TypeVar, cast

import click
from prompt_toolkit import Application
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

BACK = object()
CANCEL = object()
_T = TypeVar("_T")
_STYLE = Style.from_dict(
    {
        "title": "bold ansicyan",
        "help": "ansibrightblack",
        "cursor": "reverse",
    }
)


def checkbox_menu(
    *,
    title: str,
    help_text: str,
    choices: Sequence[tuple[_T, str]],
    selected: set[_T],
    allow_back: bool = True,
) -> set[_T] | object:
    """Render a checkbox TUI and return selected values, BACK, or CANCEL."""
    click.clear()
    current = 0
    scroll_top = 0
    selected_values = set(selected)
    values = [value for value, _ in choices]

    def visible_height() -> int:
        # Header uses four lines. Keep one spare line so prompt-toolkit can redraw
        # cleanly in short terminals.
        return max(1, shutil.get_terminal_size((80, 24)).lines - 5)

    def adjust_scroll() -> None:
        nonlocal scroll_top
        height = visible_height()
        if current < scroll_top:
            scroll_top = current
        elif current >= scroll_top + height:
            scroll_top = current - height + 1

    def formatted_text() -> AnyFormattedText:
        lines: list[tuple[str, str]] = [
            ("class:title", f"{title}\n"),
            ("class:help", f"{help_text}\n"),
            (
                "class:help",
                "↑/↓ move  Space toggle  Enter continue"
                + ("  Backspace previous" if allow_back else "")
                + "  q/Esc cancel"
                + "\n\n",
            ),
        ]
        if not choices:
            lines.append(("class:help", "No choices available. Press Enter to continue.\n"))
            return cast(AnyFormattedText, lines)
        height = visible_height()
        end = min(len(choices), scroll_top + height)
        if scroll_top > 0:
            lines.append(("class:help", f"  ↑ {scroll_top} more above\n"))
        for index, (value, label) in enumerate(choices[scroll_top:end], start=scroll_top):
            marker = "☑" if value in selected_values else "☐"
            prefix = ">" if index == current else " "
            style = "class:cursor" if index == current else ""
            lines.append((style, f"{prefix} {marker} {label}\n"))
        remaining = len(choices) - end
        if remaining > 0:
            lines.append(("class:help", f"  ↓ {remaining} more below\n"))
        return cast(AnyFormattedText, lines)

    control = FormattedTextControl(formatted_text, focusable=True)
    window = Window(content=control, always_hide_cursor=True)
    bindings = KeyBindings()

    @bindings.add("up")
    @bindings.add("k")
    def _up(event: object) -> None:
        nonlocal current
        if not choices:
            return
        current = (current - 1) % len(choices)
        adjust_scroll()

    @bindings.add("down")
    @bindings.add("j")
    def _down(event: object) -> None:
        nonlocal current
        if not choices:
            return
        current = (current + 1) % len(choices)
        adjust_scroll()

    @bindings.add(" ")
    def _toggle(event: object) -> None:
        if not choices:
            return
        value = values[current]
        if value in selected_values:
            selected_values.remove(value)
        else:
            selected_values.add(value)

    @bindings.add("enter")
    def _accept(event: object) -> None:
        event.app.exit(result=set(selected_values))  # type: ignore[attr-defined]

    @bindings.add("backspace")
    @bindings.add("c-h")
    def _back(event: object) -> None:
        if allow_back:
            event.app.exit(result=BACK)  # type: ignore[attr-defined]

    @bindings.add("q")
    @bindings.add("escape")
    @bindings.add("c-c")
    def _cancel(event: object) -> None:
        event.app.exit(result=CANCEL)  # type: ignore[attr-defined]

    app: Application[set[_T] | object] = Application(
        layout=Layout(HSplit([window])),
        key_bindings=bindings,
        style=_STYLE,
        full_screen=False,
    )
    return app.run()


def choice_menu(
    *,
    title: str,
    help_text: str,
    choices: Sequence[tuple[_T, str]],
) -> _T | object:
    """Render a single-choice TUI and return one value or CANCEL."""
    click.clear()
    current = 0
    values = [value for value, _ in choices]

    def formatted_text() -> AnyFormattedText:
        lines: list[tuple[str, str]] = [
            ("class:title", f"{title}\n"),
            ("class:help", f"{help_text}\n"),
            ("class:help", "↑/↓ move  Enter choose  q/Esc cancel\n\n"),
        ]
        for index, (_value, label) in enumerate(choices):
            prefix = ">" if index == current else " "
            marker = "●" if index == current else "○"
            style = "class:cursor" if index == current else ""
            lines.append((style, f"{prefix} {marker} {label}\n"))
        return cast(AnyFormattedText, lines)

    control = FormattedTextControl(formatted_text, focusable=True)
    window = Window(content=control, always_hide_cursor=True)
    bindings = KeyBindings()

    @bindings.add("up")
    @bindings.add("k")
    def _up(event: object) -> None:
        nonlocal current
        current = (current - 1) % len(choices)

    @bindings.add("down")
    @bindings.add("j")
    def _down(event: object) -> None:
        nonlocal current
        current = (current + 1) % len(choices)

    @bindings.add("enter")
    def _accept(event: object) -> None:
        event.app.exit(result=values[current])  # type: ignore[attr-defined]

    @bindings.add("q")
    @bindings.add("escape")
    @bindings.add("c-c")
    def _cancel(event: object) -> None:
        event.app.exit(result=CANCEL)  # type: ignore[attr-defined]

    app: Application[_T | object] = Application(
        layout=Layout(HSplit([window])),
        key_bindings=bindings,
        style=_STYLE,
        full_screen=False,
    )
    return app.run()


def cancel_if_requested(result: set[object] | object) -> None:
    if result is CANCEL:
        raise click.Abort()
