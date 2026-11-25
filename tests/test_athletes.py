"""
Unit tests for get_coached_athletes.
"""

import asyncio
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.tools.athletes import get_coached_athletes  # pylint: disable=wrong-import-position

SUMMARY = [
    {"athlete_id": "i2", "athlete_name": "Neil", "date": "2026-11-23", "count": 4,
     "fitness": 50.2, "fatigue": 60.1, "form": -9.9},
    {"athlete_id": "i2", "athlete_name": "Neil", "date": "2026-11-16", "count": 5},
    {"athlete_id": "i3", "athlete_name": "Marion", "date": "2026-11-23", "count": 0,
     "fitness": 3.0, "fatigue": 1.0, "form": 2.0},
]
PROFILES = {
    "i2": {"status": "ACTIVE", "icu_last_seen": "2026-11-02T16:27:54.850+00:00", "icu_permission": "WRITE",
           "email": "neil@example.com", "icu_api_key": "secret-key"},
    "i3": {"status": "DORMANT", "icu_last_seen": "2026-01-17T10:00:00+00:00", "icu_permission": "READ"},
}
LATEST = {"i2": [{"start_date_local": "2026-11-24T18:26:00"}], "i3": [{"start_date_local": "2026-04-16T19:03:00"}]}


def _patch(monkeypatch, calls):
    async def fake_request(url, *_args, **_kwargs):
        calls.append(url)
        if url.endswith("athlete-summary"):
            return SUMMARY
        aid = url.split("/")[2]
        return LATEST[aid] if url.endswith("/activities") else PROFILES[aid]

    monkeypatch.setattr("intervals_mcp_server.tools.athletes.make_intervals_request", fake_request)


def test_get_coached_athletes_shows_sync_status(monkeypatch):
    """Each athlete shows last activity, last visit, permission and status; dormant ones are flagged."""
    calls: list[str] = []
    _patch(monkeypatch, calls)
    result = asyncio.run(get_coached_athletes())

    assert "Coached Athletes (2 total)" in result
    assert "1 DORMANT (sync paused)" in result
    assert "- [i3] Marion | activities 0/0" in result
    assert "last activity 2026-04-16 | last visit 2026-01-17 | coach READ | DORMANT (sync paused" in result
    assert "- [i2] Neil | activities 4/5 | CTL 50, ATL 60, form -10 | last activity 2026-11-24" in result
    assert "coach WRITE | ACTIVE" in result
    assert "secret-key" not in result and "neil@example.com" not in result
    assert result.index("[i3] Marion") < result.index("[i2] Neil")


def test_get_coached_athletes_without_sync_check(monkeypatch):
    """check_sync=False only calls the summary endpoint."""
    calls: list[str] = []
    _patch(monkeypatch, calls)
    result = asyncio.run(get_coached_athletes(check_sync=False))

    assert calls == ["/athlete/0/athlete-summary"]
    assert "last visit" not in result
    assert "- [i2] Neil | activities 4/5" in result
