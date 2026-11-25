"""
Unit tests for the race detection tool (find_race_candidates).
"""

import asyncio
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.tools.races import (  # pylint: disable=wrong-import-position
    find_race_candidates,
    prepare_runs,
    score_run,
)


def _run(start, km, speed, **extra):
    moving = round(km * 1000 / speed)
    return {
        "id": extra.pop("id", start),
        "type": "Run",
        "name": extra.pop("name", "Course à pied"),
        "start_date_local": start,
        "distance": km * 1000,
        "average_speed": speed,
        "moving_time": moving,
        "elapsed_time": extra.pop("elapsed_time", moving),
        **extra,
    }


def _easy_runs(speed):
    """Ten easy weekday runs that set the athlete's usual pace."""
    return [_run(f"2026-10-{day:02d}T18:12:00", 8, speed, elapsed_time=3000) for day in range(5, 15)]


ACTIVITIES = {
    "i2": _easy_runs(3.0) + [
        _run("2026-11-21T15:47:00", 5, 3.0, elapsed_time=1800, id="easy-saturday"),
        _run("2026-11-22T08:10:43", 4, 2.5, elapsed_time=2090, id="warm-up"),
        _run("2026-11-22T09:00:19", 9.98, 3.93, id="race-i2", name="10 km Vénissieux",
             average_heartrate=159, lthr=162, icu_intensity=97),
    ],
    "i3": _easy_runs(2.9) + [
        _run("2026-11-22T09:00:36", 10.02, 3.72, id="race-i3", icu_intensity=97),
        {"start_date_local": "2026-11-23T09:31:42", "source": "STRAVA", "type": None},
    ],
    "i1": _easy_runs(3.2) + [
        _run("2026-11-22T09:00:05", 10.0, 4.2, id="race-coach", icu_intensity=98),
    ],
}
SUMMARY = [
    {"athlete_id": "i2", "athlete_name": "Steph"},
    {"athlete_id": "i3", "athlete_name": "Benoit"},
    {"athlete_id": "i1", "athlete_name": "Coach"},
]


async def fake_request(url, *_args, **_kwargs):
    if url.endswith("athlete-summary"):
        return SUMMARY
    return ACTIVITIES[url.split("/")[2]]


def _by_day(runs):
    by_day = {}
    for run in runs:
        by_day.setdefault(run["start"].date(), []).append(run)
    return by_day


def test_score_run_separates_race_from_easy_run():
    """A race with warm-up and a club mate at the start scores high; an easy run does not."""
    runs = prepare_runs({aid: (aid, acts) for aid, acts in ACTIVITIES.items() if aid != "i1"})
    by_day = _by_day(runs)
    race = next(r for r in runs if r["id"] == "race-i2")
    easy = next(r for r in runs if r["id"] == "easy-saturday")

    race_points, race_reasons = score_run(race, by_day)
    easy_points, _ = score_run(easy, by_day)

    assert race_points >= 8
    assert "warm-up before" in race_reasons
    assert "same start as i3" in race_reasons
    assert easy_points < 5


def test_find_race_candidates_lists_races(monkeypatch):
    """The tool lists both races, skips easy runs and the coach, and reports Strava blind spots."""
    monkeypatch.setattr("intervals_mcp_server.tools.races.make_intervals_request", fake_request)
    result = asyncio.run(find_race_candidates(start_date="2026-11-16", end_date="2026-11-25"))

    assert "2 athletes scanned" in result
    assert "Steph (i2) | 09:00 | 10 km Vénissieux | 9.98 km" in result
    assert "activity race-i3" in result
    assert "easy-saturday" not in result
    assert "race-coach" not in result
    assert "Strava activities without data (not scanned): Benoit 1" in result


def test_find_race_candidates_include_self(monkeypatch):
    """include_self also scans the coach's own account."""
    monkeypatch.setattr("intervals_mcp_server.tools.races.make_intervals_request", fake_request)
    result = asyncio.run(
        find_race_candidates(start_date="2026-11-16", end_date="2026-11-25", include_self=True)
    )
    assert "activity race-coach" in result


def test_find_race_candidates_rejects_bad_dates():
    """Dates must be valid and in order."""
    assert "Error" in asyncio.run(find_race_candidates(start_date="22/11/2026"))
    assert "Error" in asyncio.run(
        find_race_candidates(start_date="2026-11-25", end_date="2026-11-01")
    )
