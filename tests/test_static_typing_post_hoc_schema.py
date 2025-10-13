"""Invoke Pyright over the static typing fixtures for schema support."""

from __future__ import annotations

import subprocess
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent / "static_typing"


def _run_pyright(target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "pyright", str(target)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_pyright_accepts_typed_collections() -> None:
    result = _run_pyright(FIXTURE_DIR / "post_hoc_schema_pass.py")
    assert result.returncode == 0, result.stdout + result.stderr


def test_pyright_rejects_incorrect_assignments() -> None:
    result = _run_pyright(FIXTURE_DIR / "post_hoc_schema_fail.py")
    assert result.returncode != 0, "Pyright should flag typing errors in the negative fixture"
    combined_output = result.stdout.lower() + result.stderr.lower()
    assert "error" in combined_output, result.stdout + result.stderr
