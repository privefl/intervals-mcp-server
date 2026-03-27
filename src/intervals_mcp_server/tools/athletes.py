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

    lines = [f"Coached Athletes ({len(athletes)} total):\n"]
    for athlete in athletes:
        if not isinstance(athlete, dict):
            continue
        athlete_id = athlete.get("id", "N/A")
        name = athlete.get("name") or athlete.get("firstname", "") + " " + athlete.get("lastname", "")
        name = name.strip() or "Unknown"
        sex = athlete.get("sex", "")
        city = athlete.get("city", "")
        country = athlete.get("country", "")
        sport = athlete.get("defaultSport", athlete.get("sport", ""))

        line = f"- [{athlete_id}] {name}"
        if sport:
            line += f" | {sport}"
        if sex:
            line += f" | {sex}"
        if city or country:
            location = ", ".join(filter(None, [city, country]))
            line += f" | {location}"
        lines.append(line)

    return "\n".join(lines)
