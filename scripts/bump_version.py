"""
Utility to bump the Fire-Prox version consistently.

Updates both the `pyproject.toml` version field and the
`src/fire_prox/__init__.py` `__version__` assignment.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
INIT_PATH = PROJECT_ROOT / "src" / "fire_prox" / "__init__.py"

VERSION_RE = re.compile(r'^version = "(?P<version>[^"]+)"$', re.MULTILINE)
INIT_VERSION_RE = re.compile(r'^__version__ = "(?P<version>[^"]+)"$', re.MULTILINE)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bump Fire-Prox version in pyproject.toml and __init__.py."
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--version",
        help="Explicit version string to set (e.g. 0.4.0).",
    )
    group.add_argument(
        "--bump",
        choices=("major", "minor", "patch"),
        help="Increment the current version (defaults to patch).",
    )
    return parser.parse_args()


def _read_versions() -> str:
    text = PYPROJECT_PATH.read_text(encoding="utf-8")
    match = VERSION_RE.search(text)
    if not match:
        raise RuntimeError("Could not locate version in pyproject.toml")
    return match.group("version")


def _format_bump(version: str, bump: str) -> str:
    try:
        major, minor, patch = (int(part) for part in version.split("."))
    except ValueError as exc:
        raise ValueError(f"Version '{version}' is not in MAJOR.MINOR.PATCH format") from exc

    if bump == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1
    return f"{major}.{minor}.{patch}"


def _update_file(path: Path, pattern: re.Pattern[str], new_version: str) -> None:
    original = path.read_text(encoding="utf-8")
    updated, count = pattern.subn(
        lambda m: m.group(0).replace(m.group("version"), new_version), original, count=1
    )
    if count != 1:
        raise RuntimeError(f"Failed to update version in {path}")
    path.write_text(updated, encoding="utf-8")


def bump_version(new_version: str) -> None:
    """Update both pyproject.toml and __init__.py to the provided version."""
    _update_file(PYPROJECT_PATH, VERSION_RE, new_version)
    _update_file(INIT_PATH, INIT_VERSION_RE, new_version)


def main() -> None:
    args = _parse_args()
    current = _read_versions()
    target = args.version or _format_bump(current, args.bump or "patch")

    bump_version(target)
    print(f"Bumped version: {current} -> {target}")


if __name__ == "__main__":
    main()
