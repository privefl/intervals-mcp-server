"""
Unit tests for get_coached_athletes.
"""

import asyncio
import os
import pathlib
import sys
from datetime import date, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.tools.athletes import get_coached_athletes  # pylint: disable=wrong-import-position


def _days_ago(days):
    return (date.today() - timedelta(days=days)).isoformat()


SUMMARY = [
    {"athlete_id": "i2", "athlete_name": "Neil", "date": "2026-11-23", "count": 4,
     "fitness": 50.2, "fatigue": 60.1, "form": -9.9},
    {"athlete_id": "i2", "athlete_name": "Neil", "date": "2026-11-16", "count": 5},
    {"athlete_id": "i3", "athlete_name": "Marion", "date": "2026-11-23", "count": 0,
     "fitness": 3.0, "fatigue": 1.0, "form": 2.0},
    {"athlete_id": "i4", "athlete_name": "Sylvie", "date": "2026-11-23", "count": 2},
    {"athlete_id": "i5", "athlete_name": "Stephane", "date": "2026-11-23", "count": 3},
    {"athlete_id": "i6", "athlete_name": "Lydia", "date": "2026-11-23", "count": 1},
]
PROFILES = {
    "i2": {"status": "ACTIVE", "icu_last_seen": f"{_days_ago(23)}T16:27:54.850+00:00", "icu_permission": "READ",
           "email": "neil@example.com", "icu_api_key": "secret-key"},
    "i3": {"status": "DORMANT", "icu_last_seen": "2026-01-17T10:00:00+00:00", "icu_permission": "READ"},
    "i4": {"status": "ACTIVE", "icu_last_seen": f"{_days_ago(400)}T10:00:00+00:00", "icu_permission": "WRITE"},
    "i5": {"status": "ACTIVE", "icu_last_seen": f"{_days_ago(70)}T10:00:00+00:00", "icu_permission": "READ"},
    "i6": {"status": "ACTIVE", "icu_last_seen": f"{_days_ago(95)}T10:00:00+00:00", "icu_permission": "READ"},
}
LATEST = {aid: [{"start_date_local": "2026-11-24T18:26:00"}] for aid in PROFILES}
LATEST["i3"] = [{"start_date_local": "2026-04-16T19:03:00"}]


def _patch(monkeypatch, calls):
    async def fake_request(url, *_args, **_kwargs):
        calls.append(url)
        if url.endswith("athlete-summary"):
            return SUMMARY
        aid = url.split("/")[2]
        return LATEST[aid] if url.endswith("/activities") else PROFILES[aid]

    monkeypatch.setattr("intervals_mcp_server.tools.athletes.make_intervals_request", fake_request)


def _line(result, name):
    return next(line for line in result.splitlines() if f"] {name} " in line)


def test_get_coached_athletes_shows_sync_status(monkeypatch):
    """Each athlete shows last activity, last visit, permission and status; dormant ones are flagged."""
    calls: list[str] = []
    _patch(monkeypatch, calls)
    result = asyncio.run(get_coached_athletes())

    assert "Coached Athletes (5 total)" in result
    assert "1 DORMANT (sync paused) | 2 soon dormant" in result
    assert _line(result, "Marion").endswith(
        "last activity 2026-04-16 | last visit 2026-01-17 | coach READ | DORMANT "
        "(sync paused: the athlete must log in again, then reconnect Garmin if needed)"
    )
    assert _line(result, "Neil").startswith(
        "- [i2] Neil | activities 4/5 | CTL 50, ATL 60, form -10 | last activity 2026-11-24"
    )
    assert "secret-key" not in result and "neil@example.com" not in result
    assert result.index("[i3] Marion") < result.index("[i2] Neil")


def test_get_coached_athletes_warns_before_dormancy(monkeypatch):
    """READ athletes without a visit for 60+ days are warned; recent visits and WRITE are not."""
    _patch(monkeypatch, [])
    result = asyncio.run(get_coached_athletes())

    assert _line(result, "Stephane").endswith(
        "(dormant in about 20 days: the athlete should log in to intervals.icu)"
    )
    assert _line(result, "Lydia").endswith("(dormant any day now: the athlete should log in to intervals.icu)")
    assert _line(result, "Neil").endswith("coach READ | ACTIVE")
    assert _line(result, "Sylvie").endswith("coach WRITE | ACTIVE")


def test_get_coached_athletes_without_sync_check(monkeypatch):
    """check_sync=False only calls the summary endpoint."""
    calls: list[str] = []
    _patch(monkeypatch, calls)
    result = asyncio.run(get_coached_athletes(check_sync=False))

    assert calls == ["/athlete/0/athlete-summary"]
    assert "last visit" not in result
    assert "- [i2] Neil | activities 4/5" in result
