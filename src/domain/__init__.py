"""
Domain layer - Pure business logic without external dependencies.
"""

from .models import TimeRange, TimeSlot, WorkingHours
from .slot_calculator import SlotCalculator

__all__ = ["TimeRange", "TimeSlot", "WorkingHours", "SlotCalculator"]

