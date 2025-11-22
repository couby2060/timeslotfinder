"""
Core business logic for calculating available time slots.

This is the heart of the application - pure domain logic without any
external dependencies (no API calls, no database, no I/O).
"""

from typing import Dict, List

import pendulum
from pendulum import DateTime

from .models import TimeRange, TimeSlot, WorkingHours


class SlotCalculator:
    """
    Calculates available meeting slots based on busy times and working hours.
    
    Algorithm:
    1. Get working hours for the date range
    2. For each participant, invert their busy times to get free times
    3. Calculate intersection of all participants' free times
    4. Filter by minimum duration
    5. Return complete blocks (not split into smaller chunks)
    """
    
    def __init__(self, working_hours: WorkingHours):
        self.working_hours = working_hours
    
    def find_available_slots(
        self,
        start_date: DateTime,
        end_date: DateTime,
        busy_times: Dict[str, List[TimeRange]],
        min_duration_minutes: int = 30
    ) -> List[TimeSlot]:
        """
        Find all available time slots for all participants.
        
        Args:
            start_date: Start of the search period
            end_date: End of the search period
            busy_times: Dict mapping participant email to their busy time ranges
            min_duration_minutes: Minimum duration for a slot to be considered
            
        Returns:
            List of TimeSlot objects representing available meeting times
        """
        participants = list(busy_times.keys())
        
        if not participants:
            return []
        
        # Step 1: Get all working hours blocks in the date range
        working_blocks = self._get_working_blocks(start_date, end_date)
        
        if not working_blocks:
            return []
        
        # Step 2: For each participant, calculate their free times
        participant_free_times: Dict[str, List[TimeRange]] = {}
        
        for email, busy_ranges in busy_times.items():
            free_times = self._invert_busy_to_free(
                working_blocks=working_blocks,
                busy_ranges=busy_ranges
            )
            participant_free_times[email] = free_times
        
        # Step 3: Calculate intersection of all participants' free times
        common_free_times = self._intersect_all_participants(
            participant_free_times=participant_free_times
        )
        
        # Step 4: Filter by minimum duration
        valid_slots = [
            tr for tr in common_free_times
            if tr.duration_minutes() >= min_duration_minutes
        ]
        
        # Step 5: Convert to TimeSlot objects
        slots = [
            TimeSlot(time_range=tr, participants=participants)
            for tr in valid_slots
        ]
        
        return slots
    
    def _get_working_blocks(
        self,
        start_date: DateTime,
        end_date: DateTime
    ) -> List[TimeRange]:
        """
        Generate all working hour blocks within the date range.
        
        Returns a list of TimeRange objects, one for each working day.
        """
        blocks: List[TimeRange] = []
        
        # Iterate through each day in the range
        current = start_date.start_of("day")
        
        while current <= end_date:
            working_hours = self.working_hours.get_working_hours_for_day(current)
            
            if working_hours:
                # Clip to the search range
                clipped = self._clip_range_to_bounds(
                    working_hours,
                    start_date,
                    end_date
                )
                if clipped:
                    blocks.append(clipped)
            
            current = current.add(days=1)
        
        return blocks
    
    def _clip_range_to_bounds(
        self,
        time_range: TimeRange,
        min_bound: DateTime,
        max_bound: DateTime
    ) -> TimeRange | None:
        """
        Clip a time range to fit within bounds.
        Returns None if the range is completely outside bounds.
        """
        if time_range.end <= min_bound or time_range.start >= max_bound:
            return None
        
        clipped_start = max(time_range.start, min_bound)
        clipped_end = min(time_range.end, max_bound)
        
        return TimeRange(start=clipped_start, end=clipped_end)
    
    def _invert_busy_to_free(
        self,
        working_blocks: List[TimeRange],
        busy_ranges: List[TimeRange]
    ) -> List[TimeRange]:
        """
        Convert busy times to free times within working hours.
        
        This is a key algorithm:
        - Start with working hour blocks (the "universe" of possible time)
        - Subtract all busy times
        - What remains is free time
        """
        free_times: List[TimeRange] = []
        
        # Sort busy ranges by start time
        sorted_busy = sorted(busy_ranges, key=lambda r: r.start)
        
        for working_block in working_blocks:
            # Find all busy times that overlap with this working block
            overlapping_busy = [
                busy for busy in sorted_busy
                if working_block.overlaps(busy)
            ]
            
            if not overlapping_busy:
                # Entire working block is free
                free_times.append(working_block)
                continue
            
            # Subtract busy times from the working block
            free_times.extend(
                self._subtract_busy_from_block(working_block, overlapping_busy)
            )
        
        return free_times
    
    def _subtract_busy_from_block(
        self,
        working_block: TimeRange,
        busy_ranges: List[TimeRange]
    ) -> List[TimeRange]:
        """
        Subtract busy times from a working block, yielding free time ranges.
        
        Example:
        Working: 09:00 - 17:00
        Busy: [10:00-11:00, 14:00-15:00]
        Result: [09:00-10:00, 11:00-14:00, 15:00-17:00]
        """
        free_ranges: List[TimeRange] = []
        current_start = working_block.start
        
        # Sort busy ranges by start time
        sorted_busy = sorted(busy_ranges, key=lambda r: r.start)
        
        for busy in sorted_busy:
            # Clip busy range to working block
            clipped_busy_start = max(busy.start, working_block.start)
            clipped_busy_end = min(busy.end, working_block.end)
            
            # If there's free time before this busy period
            if current_start < clipped_busy_start:
                free_ranges.append(
                    TimeRange(start=current_start, end=clipped_busy_start)
                )
            
            # Move current pointer to end of busy period
            current_start = max(current_start, clipped_busy_end)
        
        # Add remaining free time after last busy period
        if current_start < working_block.end:
            free_ranges.append(
                TimeRange(start=current_start, end=working_block.end)
            )
        
        return free_ranges
    
    def _intersect_all_participants(
        self,
        participant_free_times: Dict[str, List[TimeRange]]
    ) -> List[TimeRange]:
        """
        Calculate the intersection of free times across all participants.
        
        Only times when ALL participants are free will be returned.
        """
        if not participant_free_times:
            return []
        
        # Start with the first participant's free times
        participants = list(participant_free_times.keys())
        result = participant_free_times[participants[0]]
        
        # Intersect with each subsequent participant
        for participant in participants[1:]:
            result = self._intersect_two_lists(
                result,
                participant_free_times[participant]
            )
            
            # Early exit if no common time
            if not result:
                return []
        
        return result
    
    def _intersect_two_lists(
        self,
        list1: List[TimeRange],
        list2: List[TimeRange]
    ) -> List[TimeRange]:
        """
        Calculate intersection of two lists of time ranges.
        
        Returns all overlapping periods between any ranges in list1 and list2.
        """
        intersections: List[TimeRange] = []
        
        for range1 in list1:
            for range2 in list2:
                intersection = range1.intersect(range2)
                if intersection:
                    intersections.append(intersection)
        
        # Merge overlapping or adjacent intersections
        return self._merge_adjacent_ranges(intersections)
    
    def _merge_adjacent_ranges(
        self,
        ranges: List[TimeRange]
    ) -> List[TimeRange]:
        """
        Merge overlapping or adjacent time ranges.
        
        Example: [09:00-10:00, 10:00-11:00] -> [09:00-11:00]
        """
        if not ranges:
            return []
        
        # Sort by start time
        sorted_ranges = sorted(ranges, key=lambda r: r.start)
        merged: List[TimeRange] = [sorted_ranges[0]]
        
        for current in sorted_ranges[1:]:
            last = merged[-1]
            
            # Check if ranges overlap or are adjacent (no gap)
            if current.start <= last.end:
                # Merge by extending the end time
                merged[-1] = TimeRange(
                    start=last.start,
                    end=max(last.end, current.end)
                )
            else:
                # No overlap, add as separate range
                merged.append(current)
        
        return merged

