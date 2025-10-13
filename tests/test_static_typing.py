from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent


def _run_pyright(config: str) -> subprocess.CompletedProcess[str]:
    """Execute pyright with the provided project configuration."""
    return subprocess.run(
        ["uv", "run", "pyright", "--project", config],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_static_typing_positive() -> None:
    """The positive fixture should type check cleanly."""
    result = _run_pyright("pyrightconfig.json")
    assert result.returncode == 0, result.stderr + result.stdout


@pytest.mark.parametrize("config", ["pyrightconfig.negative.json"])
def test_static_typing_negative(config: str) -> None:
    """The negative fixture should surface type checking failures."""
    result = _run_pyright(config)
    assert result.returncode != 0
    assert "error" in result.stderr.lower() or "error" in result.stdout.lower()
