"""Fixtures. Home Assistant wird nicht in die Datumstests gezogen."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def hass_config_dir(tmp_path: Path) -> str:
    """Config in ein temporäres Verzeichnis, die Integration per Symlink."""
    config = tmp_path / "config"
    paket = config / "custom_components"
    paket.mkdir(parents=True)
    quelle = Path(__file__).resolve().parents[1] / "custom_components"
    (paket / "__init__.py").write_text('"""Testpaket."""\n', encoding="utf-8")
    (paket / "ferien").symlink_to(quelle / "ferien", target_is_directory=True)
    return str(config)


@pytest.fixture(autouse=True)
def _uhr(freezer: Any) -> None:
    """Ein fester Mittwoch in der Abdeckung des Bayern-Fixtures."""
    freezer.move_to("2026-11-11T12:00:00+01:00")


@pytest.fixture(autouse=True)
def _custom(request: pytest.FixtureRequest) -> None:
    """Custom Integrations nur laden, wenn der Test Home Assistant benutzt."""
    if "hass" in request.fixturenames:
        request.getfixturevalue("enable_custom_integrations")
