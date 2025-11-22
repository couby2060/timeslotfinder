"""
Mock Microsoft Graph API client for testing without Azure authentication.
"""

from typing import List, Dict

import pendulum
from pendulum import DateTime

from ..domain.models import TimeRange


class MockGraphClient:
    """
    Mock client that simulates Microsoft Graph API responses.
    
    This client generates realistic busy times for testing purposes,
    without requiring actual Microsoft authentication or API access.
    
    The mock data is generated relative to the current date to ensure
    consistent testing regardless of when the code is run.
    """
    
    def __init__(self, access_token: str = "mock_token"):
        """
        Initialize the mock client.
        
        Args:
            access_token: Dummy token (not used, but kept for interface compatibility)
        """
        self.access_token = access_token
    
    def get_schedule(
        self,
        emails: List[str],
        start_time: DateTime,
        end_time: DateTime,
        timezone: str = "Europe/Berlin"
    ) -> Dict[str, List[TimeRange]]:
        """
        Generate mock schedule (busy times) for multiple users.
        
        Mock Scenario:
        - First user: Busy tomorrow 09:00-11:00
        - Second user: Busy tomorrow 10:00-12:00
        - Third+ users: Busy tomorrow 13:00-14:00
        
        This creates a realistic scenario where:
        - Morning before 09:00 is free for all
        - 09:00-10:00 is free only for users 2+
        - 10:00-11:00 is busy for users 1 & 2
        - 11:00-12:00 is busy only for user 2
        - 12:00-13:00 is free for all
        - 13:00-14:00 is busy for users 3+
        - 14:00-17:00 is free for all
        
        Args:
            emails: List of user email addresses
            start_time: Start of the time window
            end_time: End of the time window
            timezone: IANA timezone identifier
            
        Returns:
            Dictionary mapping email -> list of busy TimeRange objects
        """
        busy_times: Dict[str, List[TimeRange]] = {}
        
        # Get tomorrow's date in the specified timezone
        now = pendulum.now(timezone)
        tomorrow = now.add(days=1)
        
        # Generate busy times for each user
        for idx, email in enumerate(emails):
            user_busy_times: List[TimeRange] = []
            
            if idx == 0:
                # First user: Busy 09:00-11:00 tomorrow
                busy_start = tomorrow.set(hour=9, minute=0, second=0, microsecond=0)
                busy_end = tomorrow.set(hour=11, minute=0, second=0, microsecond=0)
                
                # Only add if it overlaps with the requested time window
                if busy_start < end_time and busy_end > start_time:
                    user_busy_times.append(TimeRange(start=busy_start, end=busy_end))
            
            elif idx == 1:
                # Second user: Busy 10:00-12:00 tomorrow
                busy_start = tomorrow.set(hour=10, minute=0, second=0, microsecond=0)
                busy_end = tomorrow.set(hour=12, minute=0, second=0, microsecond=0)
                
                if busy_start < end_time and busy_end > start_time:
                    user_busy_times.append(TimeRange(start=busy_start, end=busy_end))
            
            else:
                # Third+ users: Busy 13:00-14:00 tomorrow
                busy_start = tomorrow.set(hour=13, minute=0, second=0, microsecond=0)
                busy_end = tomorrow.set(hour=14, minute=0, second=0, microsecond=0)
                
                if busy_start < end_time and busy_end > start_time:
                    user_busy_times.append(TimeRange(start=busy_start, end=busy_end))
                
                # Add another busy time for today if requested range includes today
                today_busy_start = now.set(hour=15, minute=0, second=0, microsecond=0)
                today_busy_end = now.set(hour=16, minute=0, second=0, microsecond=0)
                
                if today_busy_start < end_time and today_busy_end > start_time:
                    user_busy_times.append(TimeRange(start=today_busy_start, end=today_busy_end))
            
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

