"""
Tests for domain models.
"""

import pendulum
import pytest
from datetime import time

from timeslotfinder.domain.models import TimeRange, WorkingHours


class TestTimeRange:
    """Tests for TimeRange model."""
    
    def test_create_valid_time_range(self):
        """Test creating a valid time range."""
        start = pendulum.parse("2024-11-25 09:00", tz="Europe/Berlin")
        end = pendulum.parse("2024-11-25 17:00", tz="Europe/Berlin")
        
        tr = TimeRange(start=start, end=end)
        
        assert tr.start == start
        assert tr.end == end
        assert tr.duration_minutes() == 480  # 8 hours
    
    def test_invalid_time_range_raises_error(self):
        """Test that creating an invalid time range raises ValueError."""
        start = pendulum.parse("2024-11-25 17:00", tz="Europe/Berlin")
        end = pendulum.parse("2024-11-25 09:00", tz="Europe/Berlin")
        
        with pytest.raises(ValueError, match="Start time .* must be before end time"):
            TimeRange(start=start, end=end)
    
    def test_overlaps(self):
        """Test overlap detection."""
        tr1 = TimeRange(
            start=pendulum.parse("2024-11-25 09:00", tz="Europe/Berlin"),
            end=pendulum.parse("2024-11-25 12:00", tz="Europe/Berlin")
        )
        tr2 = TimeRange(
            start=pendulum.parse("2024-11-25 11:00", tz="Europe/Berlin"),
            end=pendulum.parse("2024-11-25 14:00", tz="Europe/Berlin")
        )
        tr3 = TimeRange(
            start=pendulum.parse("2024-11-25 14:00", tz="Europe/Berlin"),
            end=pendulum.parse("2024-11-25 17:00", tz="Europe/Berlin")
        )
        
        assert tr1.overlaps(tr2)
        assert tr2.overlaps(tr1)
        assert not tr1.overlaps(tr3)
    
    def test_intersect(self):
        """Test intersection calculation."""
        tr1 = TimeRange(
            start=pendulum.parse("2024-11-25 09:00", tz="Europe/Berlin"),
            end=pendulum.parse("2024-11-25 12:00", tz="Europe/Berlin")
        )
        tr2 = TimeRange(
            start=pendulum.parse("2024-11-25 11:00", tz="Europe/Berlin"),
            end=pendulum.parse("2024-11-25 14:00", tz="Europe/Berlin")
        )
        
        intersection = tr1.intersect(tr2)
        
        assert intersection is not None
        assert intersection.start == pendulum.parse("2024-11-25 11:00", tz="Europe/Berlin")
        assert intersection.end == pendulum.parse("2024-11-25 12:00", tz="Europe/Berlin")
    
    def test_intersect_no_overlap(self):
        """Test intersection with no overlap returns None."""
        tr1 = TimeRange(
            start=pendulum.parse("2024-11-25 09:00", tz="Europe/Berlin"),
            end=pendulum.parse("2024-11-25 12:00", tz="Europe/Berlin")
        )
        tr2 = TimeRange(
            start=pendulum.parse("2024-11-25 14:00", tz="Europe/Berlin"),
            end=pendulum.parse("2024-11-25 17:00", tz="Europe/Berlin")
        )
        
        intersection = tr1.intersect(tr2)
        
        assert intersection is None


class TestWorkingHours:
    """Tests for WorkingHours model."""
    
    def test_is_working_day(self):
        """Test working day detection."""
        working_hours = WorkingHours(
            start_time=time(9, 30),
            end_time=time(17, 0),
            exclude_weekdays=[5, 6]  # Saturday, Sunday
        )
        
        # Monday
        monday = pendulum.parse("2024-11-25", tz="Europe/Berlin")
        assert working_hours.is_working_day(monday)
        
        # Saturday
        saturday = pendulum.parse("2024-11-23", tz="Europe/Berlin")
        assert not working_hours.is_working_day(saturday)
        
        # Sunday
        sunday = pendulum.parse("2024-11-24", tz="Europe/Berlin")
        assert not working_hours.is_working_day(sunday)
    
    def test_get_working_hours_for_day(self):
        """Test getting working hours for a specific day."""
        working_hours = WorkingHours(
            start_time=time(9, 30),
            end_time=time(17, 0),
            exclude_weekdays=[5, 6]
        )
        
        monday = pendulum.parse("2024-11-25", tz="Europe/Berlin")
        work_range = working_hours.get_working_hours_for_day(monday)
        
        assert work_range is not None
        assert work_range.start.hour == 9
        assert work_range.start.minute == 30
        assert work_range.end.hour == 17
        assert work_range.end.minute == 0
    
    def test_get_working_hours_for_weekend(self):
        """Test getting working hours for weekend returns None."""
        working_hours = WorkingHours(
            start_time=time(9, 30),
            end_time=time(17, 0),
            exclude_weekdays=[5, 6]
        )
        
        saturday = pendulum.parse("2024-11-23", tz="Europe/Berlin")
        work_range = working_hours.get_working_hours_for_day(saturday)
        
        assert work_range is None

