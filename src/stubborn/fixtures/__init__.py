"""Bundled SCIP JSON fixtures shipped with stubborn-stub on PyPI."""

from __future__ import annotations

from pathlib import Path

_FIXTURE_NAMES = frozenset({"minimal"})
_PACKAGE_DIR = Path(__file__).resolve().parent


def list_fixtures() -> tuple[str, ...]:
    """Return bundled fixture base names (without extension)."""
    return tuple(sorted(_FIXTURE_NAMES))


def fixture_path(name: str = "minimal", *, suffix: str = ".json") -> Path:
    """Resolve a bundled fixture to a readable filesystem path.

    Fixtures ship inside the installed package so ``pip install stubborn-stub``
    users can run the 30-second quickstart without cloning the git repo.
    """
    if name not in _FIXTURE_NAMES:
        known = ", ".join(sorted(_FIXTURE_NAMES))
        raise ValueError(f"Unknown fixture {name!r}; known: {known}")

    path = _PACKAGE_DIR / f"{name}{suffix}"
    if not path.is_file():
        raise FileNotFoundError(f"Bundled fixture missing from package: {path}")
    return path
