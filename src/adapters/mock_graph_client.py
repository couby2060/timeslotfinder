"""
Mock Microsoft Graph API client for testing without Azure authentication.
"""

import json
from pathlib import Path
from typing import List, Dict

import pendulum
from pendulum import DateTime

from ..domain.models import TimeRange


class MockGraphClient:
    """
    Mock client that simulates Microsoft Graph API responses.
    
    This client loads realistic calendar data from mock_calendar_data.json
    for testing purposes, without requiring actual Microsoft authentication
    or API access.
    """
    
    def __init__(self, access_token: str = "mock_token", config=None):
        """
        Initialize the mock client.
        
        Args:
            access_token: Dummy token (not used, but kept for interface compatibility)
            config: Optional AppConfig for calendar_id mapping
        """
        self.access_token = access_token
        self.config = config
        self._load_calendar_data()
    
    def _load_calendar_data(self):
        """Load mock calendar data from JSON file."""
        data_file = Path(__file__).parent / "mock_calendar_data.json"
        
        if data_file.exists():
            with open(data_file, "r", encoding="utf-8") as f:
                self.calendar_events = json.load(f)
        else:
            # Fallback to empty if file doesn't exist
            self.calendar_events = []
    
    def _get_calendar_id_for_email(self, email: str) -> str:
        """Map email to calendar_id using config."""
        if self.config:
            colleague = self.config.find_colleague_by_email(email)
            if colleague and colleague.calendar_id:
                return colleague.calendar_id
        
        # Fallback: use email as calendar_id
        return email
    
    def get_schedule(
        self,
        emails: List[str],
        start_time: DateTime,
        end_time: DateTime,
        timezone: str = "Europe/Berlin"
    ) -> Dict[str, List[TimeRange]]:
        """
        Load busy times from mock calendar data (JSON file).
        
        Args:
            emails: List of user email addresses
            start_time: Start of the time window
            end_time: End of the time window
            timezone: IANA timezone identifier
            
        Returns:
            Dictionary mapping email -> list of busy TimeRange objects
        """
        busy_times: Dict[str, List[TimeRange]] = {}
        
        for email in emails:
            calendar_id = self._get_calendar_id_for_email(email)
            user_busy_times: List[TimeRange] = []
            
            # Filter events for this calendar that overlap with the time window
            for event in self.calendar_events:
                if event.get("calendarId") != calendar_id:
                    continue
                
                try:
                    # Parse event times
                    event_start = pendulum.parse(event["start"], tz=timezone)
                    event_end = pendulum.parse(event["end"], tz=timezone)
                    
                    # Check if event overlaps with requested time window
                    if event_start < end_time and event_end > start_time:
                        user_busy_times.append(TimeRange(start=event_start, end=event_end))
                
                except (KeyError, ValueError) as e:
                    # Skip invalid events
                    continue
            
            busy_times[email] = user_busy_times
        
        return busy_times
    
    def test_connection(self) -> Dict[str, any]:
        """
        Mock connection test.
        
        Returns:
            Mock user profile data
        """
        return {
            "displayName": "Mock User",
            "mail": "mock.user@example.com",
            "userPrincipalName": "mock.user@example.com"
        }


class MockGraphAuthenticator:
    """
    Mock authenticator that bypasses actual Microsoft authentication.
    
    This is useful for testing the application without requiring
    Azure AD setup or credentials.
    """
    
    def __init__(self, client_id: str = "mock", tenant_id: str = "mock", **kwargs):
        """
        Initialize the mock authenticator.
        
        Args:
            client_id: Dummy client ID (not used)
            tenant_id: Dummy tenant ID (not used)
            **kwargs: Additional arguments (ignored for compatibility)
        """
        self.client_id = client_id
        self.tenant_id = tenant_id
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Return a mock access token.
        
        Args:
            force_refresh: Ignored in mock mode
            
        Returns:
            Mock token string
        """
        return "mock_access_token_12345"
    
    def clear_cache(self) -> None:
        """Mock cache clear (does nothing)."""
        pass

