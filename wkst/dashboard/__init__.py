"""Full-screen Textual dashboard for ``wkst`` (lazy-loaded).

``launch`` imports Textual lazily so a missing optional dependency or a
non-interactive environment never breaks the rest of the CLI at import time.
"""

from __future__ import annotations

from pathlib import Path

from wkst.platform import PlatformInfo


def launch(repo_root: Path, platform_info: PlatformInfo) -> int:
    """Run the dashboard; return a process exit code.

    Returns non-zero (and prints an actionable panel) when Textual is not
    installed, leaving the caller free to fall back to the prompt-toolkit menu.
    """
    try:
        from wkst.dashboard.app import WkstApp
    except ImportError:
        from wkst import render

        render.print_failure(
            "dashboard unavailable",
            ["Textual is not installed in this environment."],
            hint="reinstall wkst: uv tool install --editable .",
        )
        return 1

    app = WkstApp(repo_root, platform_info)
    result = app.run()
    return int(result or 0)
