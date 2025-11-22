"""
Tests for slot calculator.
"""

import pendulum
from datetime import time

from timeslotfinder.domain.models import TimeRange, WorkingHours
from timeslotfinder.domain.slot_calculator import SlotCalculator


class TestSlotCalculator:
    """Tests for SlotCalculator."""
    
    def test_find_slots_no_busy_times(self):
        """Test finding slots when no one is busy."""
        working_hours = WorkingHours(
            start_time=time(9, 0),
            end_time=time(17, 0),
            exclude_weekdays=[5, 6],
            timezone="Europe/Berlin"
        )
        
        calculator = SlotCalculator(working_hours=working_hours)
        
        start = pendulum.parse("2024-11-25 00:00", tz="Europe/Berlin")  # Monday
        end = pendulum.parse("2024-11-25 23:59", tz="Europe/Berlin")
        
        busy_times = {
            "user1@example.com": [],
            "user2@example.com": []
        }
        
        slots = calculator.find_available_slots(
            start_date=start,
            end_date=end,
            busy_times=busy_times,
            min_duration_minutes=30
        )
        
        # Should have one full working day slot
        assert len(slots) == 1
        assert slots[0].time_range.duration_minutes() == 480  # 8 hours
    
    def test_find_slots_with_busy_times(self):
        """Test finding slots with some busy times."""
        working_hours = WorkingHours(
            start_time=time(9, 0),
            end_time=time(17, 0),
            exclude_weekdays=[5, 6],
            timezone="Europe/Berlin"
        )
        
        calculator = SlotCalculator(working_hours=working_hours)
        
        start = pendulum.parse("2024-11-25 00:00", tz="Europe/Berlin")
        end = pendulum.parse("2024-11-25 23:59", tz="Europe/Berlin")
        
        # User1 busy 10:00-12:00
        # User2 busy 14:00-15:00
        # Common free: 09:00-10:00, 12:00-14:00, 15:00-17:00
        busy_times = {
            "user1@example.com": [
                TimeRange(
                    start=pendulum.parse("2024-11-25 10:00", tz="Europe/Berlin"),
                    end=pendulum.parse("2024-11-25 12:00", tz="Europe/Berlin")
                )
            ],
            "user2@example.com": [
                TimeRange(
                    start=pendulum.parse("2024-11-25 14:00", tz="Europe/Berlin"),
                    end=pendulum.parse("2024-11-25 15:00", tz="Europe/Berlin")
                )
            ]
        }
        
        slots = calculator.find_available_slots(
            start_date=start,
            end_date=end,
            busy_times=busy_times,
            min_duration_minutes=30
        )
        
        # Should have 3 free slots
        assert len(slots) == 3
        
        # Check durations
        assert slots[0].time_range.duration_minutes() == 60   # 09:00-10:00
        assert slots[1].time_range.duration_minutes() == 120  # 12:00-14:00
        assert slots[2].time_range.duration_minutes() == 120  # 15:00-17:00
    
    def test_find_slots_minimum_duration_filter(self):
        """Test that slots below minimum duration are filtered out."""
        working_hours = WorkingHours(
            start_time=time(9, 0),
            end_time=time(17, 0),
            exclude_weekdays=[5, 6],
            timezone="Europe/Berlin"
        )
        
        calculator = SlotCalculator(working_hours=working_hours)
        
        start = pendulum.parse("2024-11-25 00:00", tz="Europe/Berlin")
        end = pendulum.parse("2024-11-25 23:59", tz="Europe/Berlin")
        
        # Create many small gaps
        busy_times = {
            "user1@example.com": [
                TimeRange(
                    start=pendulum.parse("2024-11-25 09:00", tz="Europe/Berlin"),
                    end=pendulum.parse("2024-11-25 09:45", tz="Europe/Berlin")
                ),
                TimeRange(
                    start=pendulum.parse("2024-11-25 10:00", tz="Europe/Berlin"),
                    end=pendulum.parse("2024-11-25 17:00", tz="Europe/Berlin")
                )
            ]
        }
        
        # Only 15 minute gap between 09:45-10:00
        slots_30min = calculator.find_available_slots(
            start_date=start,
            end_date=end,
            busy_times=busy_times,
            min_duration_minutes=30
        )
        
        slots_15min = calculator.find_available_slots(
            start_date=start,
            end_date=end,
            busy_times=busy_times,
            min_duration_minutes=15
        )
        
        # With 30min minimum, no slots found
        assert len(slots_30min) == 0
        
        # With 15min minimum, one slot found
        assert len(slots_15min) == 1
        assert slots_15min[0].time_range.duration_minutes() == 15
    
    def test_exclude_weekends(self):
        """Test that weekends are excluded."""
        working_hours = WorkingHours(
            start_time=time(9, 0),
            end_time=time(17, 0),
            exclude_weekdays=[5, 6],  # Saturday, Sunday
            timezone="Europe/Berlin"
        )
        
        calculator = SlotCalculator(working_hours=working_hours)
        
        # Search from Friday to Monday
        start = pendulum.parse("2024-11-22 00:00", tz="Europe/Berlin")  # Friday
        end = pendulum.parse("2024-11-25 23:59", tz="Europe/Berlin")    # Monday
        
        busy_times = {
            "user1@example.com": []
        }
        
        slots = calculator.find_available_slots(
            start_date=start,
            end_date=end,
            busy_times=busy_times,
            min_duration_minutes=30
        )
        
        # Should have 2 slots: Friday and Monday (not Saturday, Sunday)
        assert len(slots) == 2

