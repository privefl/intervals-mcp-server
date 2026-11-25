"""
Race detection tool for Intervals.icu.

Scans the runs of coached athletes and flags those that look like races, so the coach can
check them and record official times. The clues were calibrated on known races:
start on a round time, no stops, pace well above the athlete's usual pace, threshold heart
rate, official distance, a warm-up just before, and other athletes starting at the same time.
"""

import asyncio
import statistics
from datetime import date, datetime, timedelta
from typing import Any

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.validation import validate_date

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()

RUN_TYPES = ("Run", "TrailRun")
OFFICIAL_KM = (5.0, 10.0, 21.1, 42.2)
BASELINE_DAYS = 120  # history before the window, used for the athlete's usual pace
MIN_SCORED_SECONDS = 12 * 60  # shorter runs are only used as warm-ups
MIN_KEPT_SECONDS = 5 * 60
SAME_START = timedelta(minutes=10)
WARMUP_GAP = timedelta(minutes=60)
MAX_PARALLEL_REQUESTS = 4


def prepare_runs(activities_by_athlete: dict[str, tuple[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    """Keep timed runs and add athlete, start, end and speed relative to the athlete's median.

    Args:
        activities_by_athlete: athlete ID -> (athlete name, raw activities from the API).
    """
    runs: list[dict[str, Any]] = []
    for aid, (name, activities) in activities_by_athlete.items():
        kept = [
            a for a in activities
            if a.get("type") in RUN_TYPES and a.get("start_date_local") and a.get("average_speed")
            and (a.get("moving_time") or 0) >= MIN_KEPT_SECONDS
        ]
        timed = [a["average_speed"] for a in kept if a["moving_time"] >= MIN_SCORED_SECONDS]
        if not timed:
            continue
        usual_speed = statistics.median(timed)
        for a in kept:
            start = datetime.fromisoformat(a["start_date_local"])
            runs.append({
                **a,
                "athlete_id": aid,
                "athlete_name": name,
                "start": start,
                "end": start + timedelta(seconds=a.get("elapsed_time") or a["moving_time"]),
                "relative_speed": a["average_speed"] / usual_speed,
            })
    return runs


def score_run(run: dict[str, Any], runs_by_day: dict[date, list[dict[str, Any]]]) -> tuple[int, list[str]]:
    """Score how much a run looks like a race, with the reasons.

    On known races, road races scored 5 to 9 and about 3% of other weekend runs reached 5.

    Args:
        run: A run returned by prepare_runs.
        runs_by_day: All prepared runs (every athlete), grouped by start date.
    """
    points, reasons = 0, []
    km = (run.get("distance") or 0) / 1000
    moving = run.get("moving_time") or 0
    elapsed = run.get("elapsed_time") or moving
    start = run["start"]

    if start.minute <= 6 or 30 <= start.minute <= 36:
        points += 1
        reasons.append(f"start {start:%H:%M}")
    if elapsed and moving / elapsed >= 0.99:
        points += 1
        reasons.append("no stops")
    if run["relative_speed"] >= 1.25:
        points += 2
        reasons.append(f"pace x{run['relative_speed']:.2f} usual")
    elif run["relative_speed"] >= 1.12:
        points += 1
        reasons.append(f"pace x{run['relative_speed']:.2f} usual")
    hr, lthr = run.get("average_heartrate"), run.get("lthr")
    if (run.get("icu_intensity") or 0) >= 88 or (hr and lthr and hr / lthr >= 0.91):
        points += 1
        reasons.append("threshold effort")
    if any(abs(km - official) / official <= 0.03 for official in OFFICIAL_KM):
        points += 1
        reasons.append("official distance")
    if moving >= 3 * 3600 and km >= 30:
        points += 2
        reasons.append("very long")
    if moving >= 6 * 3600:
        points += 3
        reasons.append("ultra")

    same_day = runs_by_day.get(start.date(), [])
    if any(
        other is not run and other["athlete_id"] == run["athlete_id"]
        and timedelta(0) <= start - other["end"] <= WARMUP_GAP and other["relative_speed"] < 1.0
        for other in same_day
    ):
        points += 1
        reasons.append("warm-up before")
    others = sorted({
        other["athlete_name"] for other in same_day
        if other["athlete_id"] != run["athlete_id"] and abs(other["start"] - start) <= SAME_START
        and other["relative_speed"] >= 1.05
    })
    if others:
        points += 2
        reasons.append("same start as " + ", ".join(others))
    return points, reasons


def _duration(seconds: int) -> str:
    if seconds >= 3600:
        return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"
    return f"{seconds // 60}:{seconds % 60:02d}"


def _pace(speed: float) -> str:
    seconds_per_km = round(1000 / speed)
    return f"{seconds_per_km // 60}:{seconds_per_km % 60:02d}/km"


@mcp.tool()
async def find_race_candidates(
    start_date: str | None = None,
    end_date: str | None = None,
    min_score: int = 5,
    weekends_only: bool = True,
    include_self: bool = False,
    api_key: str | None = None,
) -> str:
    """Find coached athletes' runs that look like races, to check and record their times.

    Each run gets a score from clues seen on known races: start on a round time, no stops,
    pace well above the athlete's usual pace, threshold heart rate, official distance
    (5, 10, 21.1, 42.2 km), a warm-up just before, other coached athletes starting at the
    same time, and very long or ultra duration. A score of 5 or more caught every known road
    race. Times shown are the watch's moving time, not the official chip time.
    Activities synced from Strava have no data through the API: they are counted as blind spots.

    Args:
        start_date: Start date (YYYY-MM-DD), defaults to 30 days ago
        end_date: End date (YYYY-MM-DD), defaults to today
        min_score: Minimum score to list a run (default 5; 4 also shows borderline runs)
        weekends_only: Only Saturday and Sunday runs (default True)
        include_self: Also scan the coach's own account (default False)
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
    """
    try:
        end = date.fromisoformat(validate_date(end_date)) if end_date else date.today()
        start = date.fromisoformat(validate_date(start_date)) if start_date else end - timedelta(days=30)
    except ValueError as exc:
        return f"Error: {exc}"
    if start > end:
        return "Error: start_date must be before end_date."

    summary = await make_intervals_request(url="/athlete/0/athlete-summary", api_key=api_key)
    if isinstance(summary, dict) and "error" in summary:
        return f"Error fetching coached athletes: {summary.get('message', 'Unknown error')}"
    rows = summary if isinstance(summary, list) else [summary]
    athletes: dict[str, str] = {}
    for row in rows:
        aid = row.get("athlete_id") or row.get("id")
        if aid and (include_self or aid != config.athlete_id):
            athletes[aid] = (row.get("athlete_name") or row.get("name") or aid).strip()
    if not athletes:
        return "No coached athletes found."

    limiter = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)
    oldest = (start - timedelta(days=BASELINE_DAYS)).isoformat()

    async def fetch(aid: str) -> dict[str, Any] | list[dict[str, Any]]:
        async with limiter:
            return await make_intervals_request(
                url=f"/athlete/{aid}/activities",
                api_key=api_key,
                params={"oldest": oldest, "newest": end.isoformat()},
            )

    responses = await asyncio.gather(*(fetch(aid) for aid in athletes))
    activities_by_athlete: dict[str, tuple[str, list[dict[str, Any]]]] = {}
    errors, blind_spots = [], []
    for aid, response in zip(athletes, responses, strict=True):
        name = athletes[aid]
        if isinstance(response, dict):
            errors.append(f"{name}: {response.get('message', 'Unknown error')}")
            continue
        activities_by_athlete[aid] = (name, response)
        stubs = sum(
            1 for a in response
            if a.get("source") == "STRAVA" and not a.get("type")
            and start.isoformat() <= (a.get("start_date_local") or "")[:10] <= end.isoformat()
        )
        if stubs:
            blind_spots.append(f"{name} {stubs}")

    runs = prepare_runs(activities_by_athlete)
    runs_by_day: dict[date, list[dict[str, Any]]] = {}
    for run in runs:
        runs_by_day.setdefault(run["start"].date(), []).append(run)

    found = []
    for run in runs:
        day = run["start"].date()
        if not start <= day <= end or run["moving_time"] < MIN_SCORED_SECONDS:
            continue
        if weekends_only and day.weekday() < 5:
            continue
        points, reasons = score_run(run, runs_by_day)
        if points >= min_score:
            found.append((run, points, reasons))
    found.sort(key=lambda item: (item[0]["start"], item[0]["athlete_name"].lower()))

    header = (
        f"Race candidates {start} to {end} (score >= {min_score}"
        f"{', weekends only' if weekends_only else ''}), {len(activities_by_athlete)} athletes scanned"
    )
    lines = [header + (":" if found else ": none found.")]
    current_day = None
    for run, points, reasons in found:
        day = run["start"].date()
        if day != current_day:
            lines.append(f"\n{day} ({run['start']:%a})")
            current_day = day
        lines.append(
            f"- [{points}] {run['athlete_name']} ({run['athlete_id']}) | {run['start']:%H:%M} | "
            f"{(run.get('name') or '').strip()} | {(run.get('distance') or 0) / 1000:.2f} km | "
            f"{_duration(run['moving_time'])} | {_pace(run['average_speed'])} | "
            f"D+ {round(run.get('total_elevation_gain') or 0)} | activity {run.get('id')} | "
            + ", ".join(reasons)
        )
    if blind_spots:
        lines.append("\nStrava activities without data (not scanned): " + ", ".join(blind_spots))
    if errors:
        lines.append("\nErrors: " + "; ".join(errors))
    lines.append("\nTimes are the watch's moving time, not the official chip time.")
    return "\n".join(lines)
