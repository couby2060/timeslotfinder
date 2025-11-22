"""
Microsoft Graph API client for fetching calendar data.
"""

from typing import List, Dict, Any

import pendulum
import requests
from pendulum import DateTime
from rich.console import Console

from ..domain.models import TimeRange

console = Console()


class GraphClient:
    """
    Client for Microsoft Graph API calendar operations.
    
    Uses the /calendar/getSchedule endpoint to fetch free/busy information.
    """
    
    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, access_token: str):
        """
        Initialize the Graph API client.
        
        Args:
            access_token: Valid Microsoft Graph access token
        """
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def get_schedule(
        self,
        emails: List[str],
        start_time: DateTime,
        end_time: DateTime,
        timezone: str = "Europe/Berlin"
    ) -> Dict[str, List[TimeRange]]:
        """
        Get schedule (busy times) for multiple users.
        
        Uses the Microsoft Graph getSchedule API which returns free/busy information.
        
        Args:
            emails: List of user email addresses
            start_time: Start of the time window
            end_time: End of the time window
            timezone: IANA timezone identifier
            
        Returns:
            Dictionary mapping email -> list of busy TimeRange objects
            
        Raises:
            RuntimeError: If API call fails
        """
        url = f"{self.GRAPH_API_ENDPOINT}/me/calendar/getSchedule"
        
        # Prepare request body
        payload = {
            "schedules": emails,
            "startTime": {
                "dateTime": start_time.to_iso8601_string(),
                "timeZone": timezone
            },
            "endTime": {
                "dateTime": end_time.to_iso8601_string(),
                "timeZone": timezone
            },
            "availabilityViewInterval": 60  # 60-minute intervals for the availability view
        }
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to fetch schedule from Microsoft Graph: {e}")
        
        # Parse response
        return self._parse_schedule_response(data, timezone)
    
    def _parse_schedule_response(
        self,
        response_data: Dict[str, Any],
        timezone: str
    ) -> Dict[str, List[TimeRange]]:
        """
        Parse the getSchedule API response into our domain model.
        
        Response format:
        {
            "value": [
                {
                    "scheduleId": "user@example.com",
                    "availabilityView": "222200000000000000",
                    "scheduleItems": [
                        {
                            "status": "busy",
                            "start": {"dateTime": "...", "timeZone": "..."},
                            "end": {"dateTime": "...", "timeZone": "..."}
                        }
                    ]
                }
            ]
        }
        """
        busy_times: Dict[str, List[TimeRange]] = {}
        
        for schedule in response_data.get("value", []):
            email = schedule.get("scheduleId", "")
            schedule_items = schedule.get("scheduleItems", [])
            
            busy_ranges: List[TimeRange] = []
            
            for item in schedule_items:
                status = item.get("status", "").lower()
                
                # We consider these statuses as "busy"
                if status in ["busy", "tentative", "oof", "workingelsewhere"]:
                    try:
                        start = self._parse_datetime(
                            item["start"]["dateTime"],
                            timezone
                        )
                        end = self._parse_datetime(
                            item["end"]["dateTime"],
                            timezone
                        )
                        
                        busy_ranges.append(TimeRange(start=start, end=end))
                    
                    except (KeyError, ValueError) as e:
                        console.print(
                            f"[yellow]Warning: Could not parse schedule item: {e}[/yellow]"
                        )
                        continue
            
            busy_times[email] = busy_ranges
        
        return busy_times
    
    def _parse_datetime(self, datetime_str: str, timezone: str) -> DateTime:
        """
        Parse a datetime string to a pendulum DateTime in the specified timezone.
        
        Args:
            datetime_str: ISO 8601 datetime string
            timezone: IANA timezone identifier
            
        Returns:
            Pendulum DateTime object
        """
        # Parse the datetime (might be in any timezone)
        dt = pendulum.parse(datetime_str)
        
        # Convert to the target timezone
        if isinstance(dt, DateTime):
            return dt.in_timezone(timezone)
        
        # If parsing failed, raise error
        raise ValueError(f"Could not parse datetime: {datetime_str}")
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection and authentication by fetching user profile.
        
        Returns:
            User profile data
            
        Raises:
            RuntimeError: If connection test fails
        """
        url = f"{self.GRAPH_API_ENDPOINT}/me"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Connection test failed: {e}")

