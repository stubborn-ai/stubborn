"""Tests for bundled package fixtures."""

from __future__ import annotations

import pytest

from stubborn.fixtures import fixture_path, list_fixtures


def test_list_fixtures_includes_minimal() -> None:
    assert "minimal" in list_fixtures()


def test_fixture_path_resolves_package_file() -> None:
    path = fixture_path("minimal")
    assert path.is_file()
    assert path.name == "minimal.json"
    assert path.parent.name == "fixtures"


def test_fixture_path_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unknown fixture"):
        fixture_path("missing")
