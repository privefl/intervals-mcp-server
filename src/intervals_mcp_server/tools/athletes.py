"""
Athlete-related MCP tools for Intervals.icu.

This module contains tools for retrieving athlete and coaching information.
"""

import asyncio
from datetime import date, timedelta

from intervals_mcp_server.api.client import make_intervals_request

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

MAX_PARALLEL_REQUESTS = 4
LAST_ACTIVITY_LOOKBACK_DAYS = 3 * 365


async def _sync_status(aid: str, api_key: str | None, limiter: asyncio.Semaphore) -> str:
    """Account status, last visit, coach permission and last synced activity of one athlete.

    Only these fields are read from the athlete profile, which also holds private data.
    """
    today = date.today()
    async with limiter:
        profile = await make_intervals_request(url=f"/athlete/{aid}", api_key=api_key)
        latest = await make_intervals_request(
            url=f"/athlete/{aid}/activities",
            api_key=api_key,
            params={
                "oldest": (today - timedelta(days=LAST_ACTIVITY_LOOKBACK_DAYS)).isoformat(),
                "newest": today.isoformat(),
                "limit": 1,
            },
        )
    if not isinstance(profile, dict) or "error" in profile:
        return " | sync status unavailable"
    last_activity = "none"
    if isinstance(latest, list) and latest:
        last_activity = (latest[0].get("start_date_local") or "?")[:10]
    status = profile.get("status") or "?"
    text = (
        f" | last activity {last_activity} | last visit {(profile.get('icu_last_seen') or 'never')[:10]}"
        f" | coach {profile.get('icu_permission') or '?'} | {status}"
    )
    if status == "DORMANT":
        text += " (sync paused: the athlete must log in again, then reconnect Garmin if needed)"
    return text


@mcp.tool()
async def get_coached_athletes(
    api_key: str | None = None,
    check_sync: bool = True,
) -> str:
    """Get the list of athletes coached by the authenticated user from Intervals.icu.

    Uses the special athlete ID "0" which resolves to the coach's own account
    and returns athlete summaries for all coached athletes.

    With check_sync, each athlete also shows their last synced activity, last visit to
    Intervals.icu, the coach's permission (READ or WRITE) and the account status.
    Free accounts become DORMANT about 3 months after the athlete's last visit and stop
    syncing new activities; athletes giving the coach WRITE permission stayed ACTIVE.
    A long gap in activities can therefore be a paused sync rather than an injury.

    Args:
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        check_sync: Also check each athlete's sync status (2 extra requests per athlete, default True)
    """
    result = await make_intervals_request(
        url="/athlete/0/athlete-summary",
        api_key=api_key,
    )

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching coached athletes: {error_message}"

    if not result:
        return "No coached athletes found."

    athletes = result if isinstance(result, list) else [result]

    if not athletes:
        return "No coached athletes found."

    # athlete-summary renvoie une ligne par athlète ET par semaine (champ `date`,
    # lundi de la semaine), avec athlete_id / athlete_name (pas id / name).
    par_athlete: dict[str, list[dict]] = {}
    for athlete in athletes:
        if isinstance(athlete, dict):
            aid = athlete.get("athlete_id") or athlete.get("id") or "N/A"
            par_athlete.setdefault(aid, []).append(athlete)
    semaines = sorted({a.get("date", "") for rows in par_athlete.values() for a in rows},
                      reverse=True)

    ordered = sorted(par_athlete.items(), key=lambda kv: (kv[1][0].get("athlete_name") or "").lower())
    sync: dict[str, str] = {}
    if check_sync:
        limiter = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)
        statuses = await asyncio.gather(*(_sync_status(aid, api_key, limiter) for aid, _ in ordered))
        sync = {aid: status for (aid, _), status in zip(ordered, statuses, strict=True)}

    lines = [f"Coached Athletes ({len(par_athlete)} total)"]
    if semaines:
        lines[0] += " | activities per week starting " + ", ".join(semaines)
    dormant = sum("DORMANT" in s for s in sync.values())
    if dormant:
        lines[0] += f" | {dormant} DORMANT (sync paused)"
    lines[0] += ":\n"
    for aid, rows in ordered:
        rows.sort(key=lambda a: a.get("date", ""), reverse=True)
        last = rows[0]
        name = (last.get("athlete_name") or last.get("name") or "").strip() or "Unknown"
        line = f"- [{aid}] {name}"
        counts = {a.get("date", ""): a.get("count", 0) for a in rows}
        if semaines:
            line += " | activities " + "/".join(str(counts.get(s, 0)) for s in semaines)
        fitness, fatigue, form = (last.get(k) for k in ("fitness", "fatigue", "form"))
        if fitness is not None:
            line += f" | CTL {fitness:.0f}, ATL {fatigue or 0:.0f}, form {form or 0:+.0f}"
        lines.append(line + sync.get(aid, ""))

    return "\n".join(lines)
