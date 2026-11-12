"""Live-Vertrag. Läuft nur, wenn API_LIVE gesetzt ist."""

from __future__ import annotations

import os
from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.contract
pytest.importorskip("aiohttp")

LAEUFT = os.environ.get("API_LIVE") == "true"
BASIS = "https://schulferienrechner.de"


@pytest.mark.skipif(not LAEUFT, reason="API_LIVE ist nicht gesetzt")
async def test_live_termine_decken_zwoelf_monate() -> None:
    """Die echte API hält den Vertrag und reicht mindestens ein Jahr."""
    import aiohttp

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for pfad in (
            "/api/v1/meta",
            "/api/v1/laender",
            "/api/v1/laender/BY/termine",
            "/api/v1/laender/BY/status",
        ):
            async with session.get(BASIS + pfad) as antwort:
                assert antwort.status == 200, pfad
                assert antwort.headers.get("ETag")
        async with session.get(BASIS + "/api/v1/laender/BY/termine") as antwort:
            etag = antwort.headers["ETag"]
            payload = await antwort.json()
        assert date.fromisoformat(payload["bis"]) >= date.today() + timedelta(days=365)
        async with session.get(
            BASIS + "/api/v1/laender/BY/termine",
            headers={"If-None-Match": etag},
        ) as erneut:
            assert erneut.status == 304
