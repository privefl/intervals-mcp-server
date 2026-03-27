"""
Unit tests for the main MCP server tool functions in intervals_mcp_server.server.

These tests use monkeypatching to mock API responses and verify the formatting and output of each tool function:
- get_activities
- get_activity_details
- get_events
- get_event_by_id
- get_wellness_data
- get_activity_intervals
- get_activity_streams

The tests ensure that the server's public API returns expected strings and handles data correctly.
"""

import asyncio
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from unittest.mock import AsyncMock, MagicMock

from intervals_mcp_server.server import (  # pylint: disable=wrong-import-position
    get_activities,
    get_activity_details,
    get_activity_file,
    get_events,
    get_event_by_id,
    get_wellness_data,
    get_activity_intervals,
    get_activity_streams,
    add_or_update_event,
    get_custom_items,
    get_custom_item_by_id,
    create_custom_item,
    update_custom_item,
    delete_custom_item,
)
from tests.sample_data import INTERVALS_DATA  # pylint: disable=wrong-import-position


def test_get_activities(monkeypatch):
    """
    Test get_activities returns a formatted string containing activity details when given a sample activity.
    """
    sample = {
        "name": "Morning Ride",
        "id": 123,
        "type": "Ride",
        "startTime": "2024-01-01T08:00:00Z",
        "distance": 1000,
        "duration": 3600,
    }

    async def fake_request(*_args, **_kwargs):
        return [sample]

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activities(athlete_id="1", limit=1, include_unnamed=True))
    assert "Morning Ride" in result
    assert "Activities:" in result


def test_get_activity_details(monkeypatch):
    """
    Test get_activity_details returns a formatted string with the activity name and details.
    """
    sample = {
        "name": "Morning Ride",
        "id": 123,
        "type": "Ride",
        "startTime": "2024-01-01T08:00:00Z",
        "distance": 1000,
        "duration": 3600,
    }

    async def fake_request(*_args, **_kwargs):
        return sample

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_details(123))
    assert "Activity: Morning Ride" in result


def test_get_events(monkeypatch):
    """
    Test get_events returns a formatted string containing event details when given a sample event.
    """
    event = {
        "date": "2024-01-01",
        "id": "e1",
        "name": "Test Event",
        "description": "desc",
        "race": True,
    }

    async def fake_request(*_args, **_kwargs):
        return [event]

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.events.make_intervals_request", fake_request)
    result = asyncio.run(get_events(athlete_id="1", start_date="2024-01-01", end_date="2024-01-02"))
    assert "Test Event" in result
    assert "Events:" in result


def test_get_event_by_id(monkeypatch):
    """
    Test get_event_by_id returns a formatted string with event details for a given event ID.
    """
    event = {
        "id": "e1",
        "date": "2024-01-01",
        "name": "Test Event",
        "description": "desc",
        "race": True,
    }

    async def fake_request(*_args, **_kwargs):
        return event

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.events.make_intervals_request", fake_request)
    result = asyncio.run(get_event_by_id("e1", athlete_id="1"))
    assert "Event Details:" in result
    assert "Test Event" in result


def test_get_wellness_data(monkeypatch):
    """
    Test get_wellness_data returns a formatted string containing wellness data for a given athlete.
    """
    wellness = {
        "2024-01-01": {
            "id": "2024-01-01",
            "ctl": 75,
            "sleepSecs": 28800,
        }
    }

    async def fake_request(*_args, **_kwargs):
        return wellness

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.wellness.make_intervals_request", fake_request)
    result = asyncio.run(get_wellness_data(athlete_id="1"))
    assert "Wellness Data:" in result
    assert "2024-01-01" in result


def test_get_activity_intervals(monkeypatch):
    """
    Test get_activity_intervals returns a formatted string with interval analysis for a given activity.
    """

    async def fake_request(*_args, **_kwargs):
        return INTERVALS_DATA

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_intervals("123"))
    assert "Intervals Analysis:" in result
    assert "Rep 1" in result


def test_get_activity_streams(monkeypatch):
    """
    Test get_activity_streams returns a formatted string with stream data for a given activity.
    """
    sample_streams = [
        {
            "type": "time",
            "name": "time",
            "data": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "data2": [],
            "valueType": "time_units",
            "valueTypeIsArray": False,
            "anomalies": None,
            "custom": False,
        },
        {
            "type": "watts",
            "name": "watts",
            "data": [150, 155, 160, 165, 170, 175, 180, 185, 190, 195, 200],
            "data2": [],
            "valueType": "power_units",
            "valueTypeIsArray": False,
            "anomalies": None,
            "custom": False,
        },
        {
            "type": "heartrate",
            "name": "heartrate",
            "data": [120, 125, 130, 135, 140, 145, 150, 155, 160, 165, 170],
            "data2": [],
            "valueType": "hr_units",
            "valueTypeIsArray": False,
            "anomalies": None,
            "custom": False,
        },
    ]

    async def fake_request(*_args, **_kwargs):
        return sample_streams

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_streams("i107537962"))
    assert "Activity Streams" in result
    assert "time" in result
    assert "watts" in result
    assert "heartrate" in result
    assert "Data Points: 11" in result


def test_add_or_update_event(monkeypatch):
    """
    Test add_or_update_event successfully posts an event and returns the response data.
    """
    expected_response = {
        "id": "e123",
        "start_date_local": "2024-01-15T00:00:00",
        "category": "WORKOUT",
        "name": "Test Workout",
        "type": "Ride",
    }

    async def fake_post_request(*_args, **_kwargs):
        return expected_response

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_post_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.events.make_intervals_request", fake_post_request
    )
    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1", start_date="2024-01-15", name="Test Workout", workout_type="Ride"
        )
    )
    assert "Successfully created event:" in result
    assert '"id": "e123"' in result
    assert '"name": "Test Workout"' in result


def test_get_custom_items(monkeypatch):
    """
    Test get_custom_items returns a formatted string containing custom item details.
    """
    custom_items = [
        {"id": 1, "name": "HR Zones", "type": "ZONES", "description": "Heart rate zones"},
        {"id": 2, "name": "Power Chart", "type": "FITNESS_CHART", "description": None},
    ]

    async def fake_request(*_args, **_kwargs):
        return custom_items

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(get_custom_items(athlete_id="1"))
    assert "Custom Items:" in result
    assert "HR Zones" in result
    assert "ZONES" in result
    assert "Power Chart" in result


def test_get_custom_item_by_id(monkeypatch):
    """
    Test get_custom_item_by_id returns formatted details of a single custom item.
    """
    custom_item = {
        "id": 1,
        "name": "HR Zones",
        "type": "ZONES",
        "description": "Heart rate zones",
        "visibility": "PRIVATE",
        "index": 0,
    }

    async def fake_request(*_args, **_kwargs):
        return custom_item

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(get_custom_item_by_id(item_id=1, athlete_id="1"))
    assert "Custom Item Details:" in result
    assert "HR Zones" in result
    assert "ZONES" in result
    assert "Heart rate zones" in result
    assert "PRIVATE" in result


def test_create_custom_item(monkeypatch):
    """
    Test create_custom_item returns a success message with formatted item details.
    """
    created_item = {
        "id": 10,
        "name": "New Chart",
        "type": "FITNESS_CHART",
        "description": "A new fitness chart",
        "visibility": "PRIVATE",
    }

    async def fake_request(*_args, **_kwargs):
        return created_item

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_custom_item(name="New Chart", item_type="FITNESS_CHART", athlete_id="1")
    )
    assert "Successfully created custom item:" in result
    assert "New Chart" in result
    assert "FITNESS_CHART" in result


def test_create_custom_item_with_string_content(monkeypatch):
    """
    Test create_custom_item correctly parses content when passed as a JSON string.
    """
    captured: dict = {}

    async def fake_request(*_args, **kwargs):
        captured["data"] = kwargs.get("data")
        return {
            "id": 11,
            "name": "Activity Field",
            "type": "ACTIVITY_FIELD",
            "content": {"expression": "icu_training_load"},
        }

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_custom_item(
            name="Activity Field",
            item_type="ACTIVITY_FIELD",
            athlete_id="1",
            content='{"expression": "icu_training_load"}',  # type: ignore[arg-type]
        )
    )
    assert "Successfully created custom item:" in result
    # Verify the content was parsed from string to dict before being sent
    assert isinstance(captured["data"]["content"], dict)
    assert captured["data"]["content"]["expression"] == "icu_training_load"


def test_update_custom_item(monkeypatch):
    """
    Test update_custom_item returns a success message with formatted item details.
    """
    updated_item = {
        "id": 1,
        "name": "Updated Chart",
        "type": "FITNESS_CHART",
        "description": "Updated description",
        "visibility": "PUBLIC",
    }

    async def fake_request(*_args, **_kwargs):
        return updated_item

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(
        update_custom_item(item_id=1, name="Updated Chart", athlete_id="1")
    )
    assert "Successfully updated custom item:" in result
    assert "Updated Chart" in result
    assert "PUBLIC" in result


def test_delete_custom_item(monkeypatch):
    """
    Test delete_custom_item returns the API response.
    """

    async def fake_request(*_args, **_kwargs):
        return {}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(delete_custom_item(item_id=1, athlete_id="1"))
    assert "Successfully deleted" in result


def test_create_custom_item_with_invalid_json_content(monkeypatch):
    """
    Test create_custom_item returns an error message when content is an invalid JSON string.
    """

    async def fake_request(*_args, **_kwargs):
        return {}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_custom_item(
            name="Bad Item",
            item_type="FITNESS_CHART",
            athlete_id="1",
            content="not valid json",  # type: ignore[arg-type]
        )
    )
    assert "Error: content must be valid JSON when passed as a string." in result


def _make_fit_field(fitdecode_module, name, value):
    field = MagicMock(spec=fitdecode_module.types.FieldData)
    field.name = name
    field.value = value
    return field


def _make_fit_frame(fitdecode_module, frame_name, fields):
    frame = MagicMock(spec=fitdecode_module.FitDataMessage)
    frame.name = frame_name
    frame.fields = fields
    return frame


def _mock_fit_reader(monkeypatch, frames):
    mock_reader = MagicMock()
    mock_reader.__enter__ = MagicMock(return_value=iter(frames))
    mock_reader.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.fitdecode.FitReader", lambda _: mock_reader
    )


def _mock_http_client(monkeypatch, content=b"FIT_BINARY_DATA"):
    fake_response = MagicMock()
    fake_response.content = content
    fake_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=fake_response)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities._get_httpx_client",
        AsyncMock(return_value=mock_client),
    )


def test_get_activity_file_laps(monkeypatch):
    """Test get_activity_file returns parsed lap data."""
    import fitdecode

    fields = [
        _make_fit_field(fitdecode, "total_elapsed_time", 3600.0),
        _make_fit_field(fitdecode, "total_distance", 10000.0),
    ]
    _mock_fit_reader(monkeypatch, [_make_fit_frame(fitdecode, "lap", fields)])
    _mock_http_client(monkeypatch)

    result = asyncio.run(get_activity_file("A123456", data_types="laps"))

    assert "FIT file data for activity A123456" in result
    assert "Laps (1)" in result
    assert "total_elapsed_time" in result
    assert "3600.0" in result
    assert "total_distance" in result
    assert "10000.0" in result


def test_get_activity_file_session(monkeypatch):
    """Test get_activity_file returns session summary."""
    import fitdecode

    fields = [
        _make_fit_field(fitdecode, "total_elapsed_time", 7200.0),
        _make_fit_field(fitdecode, "total_distance", 42000.0),
        _make_fit_field(fitdecode, "avg_heart_rate", 145),
    ]
    _mock_fit_reader(monkeypatch, [_make_fit_frame(fitdecode, "session", fields)])
    _mock_http_client(monkeypatch)

    result = asyncio.run(get_activity_file("A123456", data_types="session"))

    assert "Session summary" in result
    assert "total_elapsed_time" in result
    assert "7200.0" in result
    assert "avg_heart_rate" in result
    assert "145" in result


def test_get_activity_file_records(monkeypatch):
    """Test get_activity_file returns record data points."""
    import fitdecode

    frames = [
        _make_fit_frame(fitdecode, "record", [
            _make_fit_field(fitdecode, "heart_rate", 140 + i),
            _make_fit_field(fitdecode, "power", 200 + i),
        ])
        for i in range(3)
    ]
    _mock_fit_reader(monkeypatch, frames)
    _mock_http_client(monkeypatch)

    result = asyncio.run(get_activity_file("A123456", data_types="records"))

    assert "Records (3 data points)" in result
    assert "heart_rate" in result
    assert "power" in result


def test_get_activity_file_all_types(monkeypatch):
    """Test get_activity_file returns all data types when none specified."""
    import fitdecode

    session_frame = _make_fit_frame(fitdecode, "session", [
        _make_fit_field(fitdecode, "total_distance", 42000.0),
    ])
    lap_frame = _make_fit_frame(fitdecode, "lap", [
        _make_fit_field(fitdecode, "total_elapsed_time", 3600.0),
    ])
    record_frame = _make_fit_frame(fitdecode, "record", [
        _make_fit_field(fitdecode, "heart_rate", 150),
    ])
    _mock_fit_reader(monkeypatch, [session_frame, lap_frame, record_frame])
    _mock_http_client(monkeypatch)

    result = asyncio.run(get_activity_file("A123456"))

    assert "Session summary" in result
    assert "Laps (1)" in result
    assert "Records (1 data points)" in result


def test_get_activity_file(monkeypatch):
    """
    Test get_activity_file returns parsed lap data from a FIT file response.
    """
    import fitdecode

    # Build fake FIT field and message objects
    fake_field_elapsed = MagicMock(spec=fitdecode.types.FieldData)
    fake_field_elapsed.name = "total_elapsed_time"
    fake_field_elapsed.value = 3600.0

    fake_field_distance = MagicMock(spec=fitdecode.types.FieldData)
    fake_field_distance.name = "total_distance"
    fake_field_distance.value = 10000.0

    fake_lap = MagicMock(spec=fitdecode.FitDataMessage)
    fake_lap.name = "lap"
    fake_lap.fields = [fake_field_elapsed, fake_field_distance]

    # Mock FitReader as a context manager yielding one lap frame
    mock_reader = MagicMock()
    mock_reader.__enter__ = MagicMock(return_value=iter([fake_lap]))
    mock_reader.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr("intervals_mcp_server.tools.activities.fitdecode.FitReader", lambda _: mock_reader)

    # Mock httpx client returning raw bytes (not gzip-compressed)
    fake_response = MagicMock()
    fake_response.content = b"FIT_BINARY_DATA"
    fake_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=fake_response)

    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities._get_httpx_client",
        AsyncMock(return_value=mock_client),
    )

    result = asyncio.run(get_activity_file("A123456", data_types="laps"))

    assert "FIT file data for activity A123456" in result
    assert "Laps (1)" in result
    assert "total_elapsed_time" in result
    assert "3600.0" in result
    assert "total_distance" in result
    assert "10000.0" in result
