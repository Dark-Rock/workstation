"""Tests for macOS defaults helpers."""

from __future__ import annotations

from pathlib import Path

from wkst import macos


def test_discover_appends_only_new_scalar_settings(monkeypatch, tmp_path: Path) -> None:
    settings_path = tmp_path / "macos" / "settings.toml"
    macos.save_settings(
        settings_path,
        [
            macos.Setting(
                "com.apple.dock",
                "autohide",
                True,
                "bool",
                "Auto-hide the Dock",
            )
        ],
    )

    monkeypatch.setattr(
        macos, "_domain_keys", lambda domain: ["autohide", "tilesize", "persistent-apps"]
    )
    monkeypatch.setattr(
        macos,
        "_read_type",
        lambda domain, key: {
            "autohide": "bool",
            "tilesize": "float",
            "persistent-apps": "array",
        }[key],
    )
    monkeypatch.setattr(
        macos,
        "_read_value",
        lambda domain, key, type_hint: {
            "autohide": True,
            "tilesize": 57.0,
        }[key],
    )

    rc = macos.discover(tmp_path, domains=["com.apple.dock"], adopt=True, dry_run=False)

    assert rc == 0
    settings = macos.load_settings(settings_path)
    assert [(s.domain, s.key, s.value, s.type) for s in settings] == [
        ("com.apple.dock", "autohide", True, "bool"),
        ("com.apple.dock", "tilesize", 57.0, "float"),
    ]
    assert settings[1].description == "Discovered from current Mac"


def test_domain_keys_parses_defaults_dictionary() -> None:
    raw = """
{
    autohide = 1;
    largesize = 128;
    "autohide-time-modifier" = "0.5";
    "persistent-apps" =     (
        "ignored nested value"
    );
}
"""

    assert macos._parse_defaults_keys(raw) == [
        "autohide",
        "largesize",
        "autohide-time-modifier",
        "persistent-apps",
    ]
