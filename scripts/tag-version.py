#!/usr/bin/env python3
"""Create and push a git tag matching the current project version, then release."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from bump_version import PYPROJECT_PATH, VERSION_RE  # type: ignore[import-error]

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=PROJECT_ROOT, check=check, text=True, capture_output=True)


def get_version() -> str:
    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    match = VERSION_RE.search(content)
    if not match:
        raise RuntimeError("Unable to extract version from pyproject.toml")
    return match.group("version")


def ensure_clean_worktree() -> None:
    result = run(["git", "status", "--porcelain"], check=True)
    if result.stdout.strip():
        raise SystemExit("Aborting: repository has uncommitted changes.")


def ensure_gh_cli() -> None:
    if shutil.which("gh") is None:
        raise SystemExit("Aborting: GitHub CLI 'gh' is not available in PATH.")


def main() -> None:
    ensure_clean_worktree()
    ensure_gh_cli()
    version = get_version()
    run(["git", "tag", version], check=True)
    run(["git", "push", "origin", version], check=True)
    run(
        [
            "gh",
            "release",
            "create",
            version,
            "--title",
            f"Release {version}",
            "--notes",
            "",
        ],
        check=True,
    )
    print(f"Tagged, pushed, and published release {version}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr or exc.stdout)
        raise
