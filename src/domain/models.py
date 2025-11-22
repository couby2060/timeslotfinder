"""
Domain models for time range and slot calculations.
"""

from dataclasses import dataclass
from datetime import time
from typing import List

import pendulum
from pendulum import DateTime


@dataclass(frozen=True)
class TimeRange:
    """
    Represents an immutable time range with start and end datetime.
    
    Invariant: start must be before end.
    """
    start: DateTime
    end: DateTime
    
    def __post_init__(self):
        if self.start >= self.end:
            raise ValueError(f"Start time {self.start} must be before end time {self.end}")
    
    def duration_minutes(self) -> int:
        """Return the duration in minutes."""
        return int((self.end - self.start).total_seconds() / 60)
    
    def overlaps(self, other: "TimeRange") -> bool:
        """Check if this range overlaps with another."""
        return self.start < other.end and self.end > other.start
    
    def intersect(self, other: "TimeRange") -> "TimeRange | None":
        """
        Calculate the intersection of two time ranges.
        Returns None if there is no overlap.
        """
        if not self.overlaps(other):
            return None
        
        start = max(self.start, other.start)
        end = min(self.end, other.end)
        
        return TimeRange(start=start, end=end)
    
    def __str__(self) -> str:
        return f"{self.start.format('DD.MM.YYYY HH:mm')} - {self.end.format('HH:mm')}"


@dataclass
class WorkingHours:
    """
    Configuration for working hours.
    """
    start_time: time
    end_time: time
    exclude_weekdays: List[int]  # 0=Monday, 6=Sunday
    timezone: str = "Europe/Berlin"
    
    def is_working_day(self, dt: DateTime) -> bool:
        """Check if a given datetime falls on a working day."""
        return dt.day_of_week not in self.exclude_weekdays
    
    def get_working_hours_for_day(self, date: DateTime) -> TimeRange | None:
        """
        Get the working hours range for a specific day.
        Returns None if it's not a working day.
        """
        if not self.is_working_day(date):
            return None
        
        # Create datetime objects for the working hours on this day
        start = date.set(
            hour=self.start_time.hour,
            minute=self.start_time.minute,
            second=0,
            microsecond=0
        )
        end = date.set(
            hour=self.end_time.hour,
            minute=self.end_time.minute,
            second=0,
            microsecond=0
        )
        
        return TimeRange(start=start, end=end)


@dataclass
class TimeSlot:
    """
    Represents a found available time slot.
    """
    time_range: TimeRange
    participants: List[str]  # Email addresses of participants
    
    def format_display(self) -> str:
        """
        Format the slot for display.
        Format: Wochentag, DD.MM.YYYY | HH:MM – HH:MM Uhr
        """
        start = self.time_range.start
        end = self.time_range.end
        
        # Get German weekday name
        weekday_names = {
            0: "Montag",
            1: "Dienstag",
            2: "Mittwoch",
            3: "Donnerstag",
            4: "Freitag",
            5: "Samstag",
            6: "Sonntag"
        }
        
        weekday = weekday_names[start.day_of_week]
        date_str = start.format("DD.MM.YYYY")
        time_str = f"{start.format('HH:mm')} – {end.format('HH:mm')} Uhr"
        duration = self.time_range.duration_minutes()
        
        return f"{weekday}, {date_str} | {time_str} ({duration} Min.)"

