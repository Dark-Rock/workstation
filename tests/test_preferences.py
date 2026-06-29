"""Tests for per-machine wkst preferences."""

from __future__ import annotations

from wkst.preferences import InstallPreferences, _render_preferences, write_preferences


def test_render_welcome_image_preference() -> None:
    text = _render_preferences(InstallPreferences(welcome_image="wallpapers/abstract.png"))

    assert "[shell]" in text
    assert 'welcome_image = "wallpapers/abstract.png"' in text


def test_write_preferences_creates_settings_file(tmp_path) -> None:
    write_preferences(
        tmp_path,
        InstallPreferences(welcome_image="wallpapers/abstract.png"),
        dry_run=False,
    )

    settings = tmp_path / ".config" / "wkst" / "settings.toml"
    assert settings.read_text(encoding="utf-8").endswith(
        'welcome_image = "wallpapers/abstract.png"\n'
    )
