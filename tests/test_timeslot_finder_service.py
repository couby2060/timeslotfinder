"""
Tests for the TimeslotFinderService orchestration layer.
"""

import asyncio
from datetime import time
from typing import Dict, List

import pendulum

from src.domain.models import TimeRange, WorkingHours
from src.domain.slot_calculator import SlotCalculator
from src.services.timeslot_finder import TimeslotFinderService


class StubCalendarClient:
    """Minimal stub matching CalendarClientProtocol."""

    def __init__(self, schedule: Dict[str, List[TimeRange]]):
        self._schedule = schedule
        self.calls: List[Dict[str, str]] = []

    async def get_schedule(self, emails, start_time, end_time, timezone):
        self.calls.append(
            {
                "emails": tuple(emails),
                "start": start_time.to_datetime_string(),
                "end": end_time.to_datetime_string(),
                "timezone": timezone,
            }
        )
        return self._schedule


def _build_service(schedule: Dict[str, List[TimeRange]]) -> TimeslotFinderService:
    working_hours = WorkingHours(
        start_time=time(9, 0),
        end_time=time(17, 0),
        exclude_weekdays=[5, 6],
        timezone="Europe/Berlin",
    )
    calculator = SlotCalculator(working_hours=working_hours)
    return TimeslotFinderService(calendar_client=StubCalendarClient(schedule), slot_calculator=calculator)


def test_fetch_busy_times_includes_missing_participants():
    """Participants without schedule entries should still appear in the map."""
    service = _build_service(schedule={"a@example.com": []})
    start = pendulum.parse("2024-11-25 00:00", tz="Europe/Berlin")
    end = pendulum.parse("2024-11-25 23:59", tz="Europe/Berlin")

    busy_times = asyncio.run(
        service.fetch_busy_times(
            participants=["a@example.com", "b@example.com"],
            start_date=start,
            end_date=end,
            timezone="Europe/Berlin",
        )
    )

    assert set(busy_times.keys()) == {"a@example.com", "b@example.com"}
    assert busy_times["b@example.com"] == []


def test_find_slots_uses_calendar_data_and_calculator():
    """End-to-end call should yield calculated slots."""
    slot_start = pendulum.parse("2024-11-25 09:00", tz="Europe/Berlin")
    slot_end = pendulum.parse("2024-11-25 17:00", tz="Europe/Berlin")
    busy_ranges = [
        TimeRange(
            start=pendulum.parse("2024-11-25 11:00", tz="Europe/Berlin"),
            end=pendulum.parse("2024-11-25 12:00", tz="Europe/Berlin"),
        )
    ]

    schedule = {
        "a@example.com": busy_ranges,
        "b@example.com": [],
    }
    service = _build_service(schedule=schedule)

    slots = asyncio.run(
        service.find_slots(
            participants=["a@example.com", "b@example.com"],
            start_date=slot_start,
            end_date=slot_end,
            timezone="Europe/Berlin",
            min_duration_minutes=30,
        )
    )

    assert len(slots) == 2  # 09-11 and 12-17 total
    assert slots[0].time_range.start.hour == 9
    assert slots[-1].time_range.end.hour == 17

