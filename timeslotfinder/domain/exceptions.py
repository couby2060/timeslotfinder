"""
Domain-specific exception hierarchy for the timeslot finder application.
"""


class TimeslotError(Exception):
    """Base class for all application-level errors."""


class CalendarAPIError(TimeslotError):
    """Raised when calendar data cannot be fetched or parsed."""


class AuthenticationError(TimeslotError):
    """Raised when authentication or token handling fails."""


