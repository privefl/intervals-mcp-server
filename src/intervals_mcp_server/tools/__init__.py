"""
MCP tools registry for Intervals.icu MCP Server.

This module registers all available MCP tools with the FastMCP server instance.
"""

from mcp.server.fastmcp import FastMCP  # pylint: disable=import-error


def register_tools(mcp_instance: FastMCP) -> None:
    """
    Register all MCP tools with the FastMCP server instance.

    Imports are deferred to this function so that @mcp.tool() decorators only
    execute after mcp_instance.mcp has been assigned in server.py.

    Args:
        mcp_instance (FastMCP): The FastMCP server instance to register tools with.
    """
    _ = mcp_instance
    # Importing here triggers @mcp.tool() registration, which requires mcp to be set.
    from intervals_mcp_server.tools.activities import (  # noqa: F401
        get_activities,
        get_activity_details,
        get_activity_file,
        get_activity_intervals,
        get_activity_streams,
    )
    from intervals_mcp_server.tools.events import (  # noqa: F401
        add_or_update_event,
        delete_event,
        delete_events_by_date_range,
        get_event_by_id,
        get_events,
    )
    from intervals_mcp_server.tools.wellness import get_wellness_data  # noqa: F401
    from intervals_mcp_server.tools.athletes import get_coached_athletes  # noqa: F401


__all__ = [
    "register_tools",
]
