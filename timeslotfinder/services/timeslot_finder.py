"""
Application services for finding shared meeting slots.

The service coordinates fetching busy times via a calendar client adapter and
delegates the actual availability calculation to the domain-level
``SlotCalculator``. This keeps the CLI thin and improves testability by
allowing the calendar dependency to be mocked via a simple protocol.
"""

from __future__ import annotations

from typing import Dict, List, Protocol, Sequence

from pendulum import DateTime

from ..domain.models import TimeRange, TimeSlot
from ..domain.slot_calculator import SlotCalculator


class CalendarClientProtocol(Protocol):
    """Protocol describing the calendar client behaviour needed by the service."""

    async def get_schedule(
        self,
        emails: List[str],
        start_time: DateTime,
        end_time: DateTime,
        timezone: str,
    ) -> Dict[str, List[TimeRange]]:
        """Return busy time ranges per participant."""


class TimeslotFinderService:
    """
    Orchestrates busy-time retrieval and slot calculation.

    Dependency inversion toward a protocol makes it easy to plug in the real
    Microsoft Graph adapter or the mock implementation in tests.
    """

    def __init__(
        self,
        calendar_client: CalendarClientProtocol,
        slot_calculator: SlotCalculator,
    ) -> None:
        self._calendar_client = calendar_client
        self._slot_calculator = slot_calculator

    async def find_slots(
        self,
        *,
        participants: Sequence[str],
        start_date: DateTime,
        end_date: DateTime,
        timezone: str,
        min_duration_minutes: int,
    ) -> List[TimeSlot]:
        """
        Retrieve busy data, normalize it, and compute available slots.
        """
        busy_times = await self.fetch_busy_times(
            participants=participants,
            start_date=start_date,
            end_date=end_date,
            timezone=timezone,
        )

        return self.calculate_slots(
            start_date=start_date,
            end_date=end_date,
            busy_times=busy_times,
            min_duration_minutes=min_duration_minutes,
        )

    async def fetch_busy_times(
        self,
        *,
        participants: Sequence[str],
        start_date: DateTime,
        end_date: DateTime,
        timezone: str,
    ) -> Dict[str, List[TimeRange]]:
        """Fetch busy times for the requested participants."""
        participant_list = list(participants)

        busy_times = await self._calendar_client.get_schedule(
            emails=participant_list,
            start_time=start_date,
            end_time=end_date,
            timezone=timezone,
        )

        return self._ensure_busy_time_entries(
            participant_list,
            busy_times,
        )

    def calculate_slots(
        self,
        *,
        start_date: DateTime,
        end_date: DateTime,
        busy_times: Dict[str, List[TimeRange]],
        min_duration_minutes: int,
    ) -> List[TimeSlot]:
        """Calculate available time slots from busy data."""
        return self._slot_calculator.find_available_slots(
            start_date=start_date,
            end_date=end_date,
            busy_times=busy_times,
            min_duration_minutes=min_duration_minutes,
        )

    @staticmethod
    def _ensure_busy_time_entries(
        participants: Sequence[str],
        busy_times: Dict[str, List[TimeRange]],
    ) -> Dict[str, List[TimeRange]]:
        """
        Ensure every requested participant appears in the busy-time map.

        Some API responses might omit users if no events exist; we normalise
        that to an explicit empty list for deterministic downstream behaviour.
        """
        normalized: Dict[str, List[TimeRange]] = {}

        for participant in participants:
            normalized[participant] = busy_times.get(participant, [])

        # Include any additional entries provided by the client as-is.
        for participant, ranges in busy_times.items():
            if participant not in normalized:
                normalized[participant] = ranges

        return normalized

