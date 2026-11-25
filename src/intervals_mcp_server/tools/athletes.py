"""
Athlete-related MCP tools for Intervals.icu.

This module contains tools for retrieving athlete and coaching information.
"""

import json

from intervals_mcp_server.api.client import make_intervals_request

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401


@mcp.tool()
async def get_coached_athletes(
    api_key: str | None = None,
) -> str:
    """Get the list of athletes coached by the authenticated user from Intervals.icu.

    Uses the special athlete ID "0" which resolves to the coach's own account
    and returns athlete summaries for all coached athletes.

    Args:
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
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

    lines = [f"Coached Athletes ({len(par_athlete)} total)"]
    if semaines:
        lines[0] += " | activities per week starting " + ", ".join(semaines)
    lines[0] += ":\n"
    for aid, rows in sorted(par_athlete.items(),
                            key=lambda kv: (kv[1][0].get("athlete_name") or "").lower()):
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
        lines.append(line)

    return "\n".join(lines)
