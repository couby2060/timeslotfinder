"""
Configuration management using Pydantic Settings.
"""

from datetime import time
from pathlib import Path
from typing import List, Sequence

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class DefaultsConfig(BaseModel):
    """Default settings for search."""
    duration_minutes: int = 30
    start_hour: int = 9
    end_hour: int = 17

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        """Ensure meeting duration is positive."""
        if value <= 0:
            raise ValueError("duration_minutes must be greater than zero")
        return value

    @field_validator("start_hour", "end_hour")
    @classmethod
    def validate_hour(cls, v: int) -> int:
        """Validate hour is between 0 and 23."""
        if not 0 <= v <= 23:
            raise ValueError(f"Hour must be between 0 and 23, got {v}")
        return v

    @model_validator(mode="after")
    def validate_hours_order(self) -> "DefaultsConfig":
        """Ensure the configured window opens before it closes."""
        if self.end_hour <= self.start_hour:
            raise ValueError("end_hour must be later than start_hour")
        return self

    def get_start_time(self) -> time:
        """Get start time as time object."""
        return time(hour=self.start_hour, minute=0)
    
    def get_end_time(self) -> time:
        """Get end time as time object."""
        return time(hour=self.end_hour, minute=0)


class Colleague(BaseModel):
    """Colleague/Participant configuration."""
    name: str  # Used as alias
    email: str
    calendar_id: str = ""  # Optional: for mock data mapping
    
    def display_name(self) -> str:
        """Get display name."""
        return self.name


class AppConfig(BaseModel):
    """Application configuration."""
    client_id: str
    tenant_id: str
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    timezone: str = "Europe/Berlin"
    colleagues: List[Colleague] = Field(default_factory=list)
    exclude_days: List[int] = Field(default_factory=lambda: [5, 6])  # Saturday, Sunday

    @field_validator("exclude_days")
    @classmethod
    def validate_exclude_days(cls, value: List[int]) -> List[int]:
        """Ensure weekdays are in valid range and deduplicated."""
        invalid_days = [day for day in value if day not in range(7)]
        if invalid_days:
            raise ValueError(f"exclude_days must be between 0 and 6, got {invalid_days}")
        # Preserve order while removing duplicates
        seen: set[int] = set()
        deduped: List[int] = []
        for day in value:
            if day not in seen:
                deduped.append(day)
                seen.add(day)
        return deduped

    @field_validator("colleagues")
    @classmethod
    def validate_colleagues(cls, value: List[Colleague]) -> List[Colleague]:
        """Ensure colleague aliases and emails are unique."""
        seen_names: set[str] = set()
        seen_emails: set[str] = set()
        for colleague in value:
            name_key = colleague.name.lower()
            email_key = colleague.email.lower()
            if name_key in seen_names:
                raise ValueError(f"Duplicate colleague name detected: {colleague.name}")
            if email_key in seen_emails:
                raise ValueError(f"Duplicate colleague email detected: {colleague.email}")
            seen_names.add(name_key)
            seen_emails.add(email_key)
        return value
    
    def get_authority_url(self) -> str:
        """Get the formatted authority URL."""
        return f"https://login.microsoftonline.com/{self.tenant_id}"
    
    @classmethod
    def load_from_yaml(cls, config_path: Path) -> "AppConfig":
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to the YAML config file
            
        Returns:
            AppConfig instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n"
                f"Please create a config.yaml file. See config.example.yaml for reference."
            )
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in {config_path}: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError("Config file must contain a mapping at the root level.")

        return cls(**data)
    
    def find_colleague_by_name(self, name: str) -> Colleague | None:
        """Find a colleague by their name (alias)."""
        for colleague in self.colleagues:
            if colleague.name.lower() == name.lower():
                return colleague
        return None
    
    def find_colleague_by_email(self, email: str) -> Colleague | None:
        """Find a colleague by their email."""
        for colleague in self.colleagues:
            if colleague.email.lower() == email.lower():
                return colleague
        return None
    
    def resolve_participant(self, identifier: str) -> str:
        """
        Resolve a participant identifier (name/alias or email) to an email address.
        
        Args:
            identifier: Name/alias or email address
            
        Returns:
            Email address
            
        Raises:
            ValueError: If identifier cannot be resolved
        """
        # Check if it's an email (contains @)
        if "@" in identifier:
            return identifier.lower()
        
        # Try to find by name (alias)
        colleague = self.find_colleague_by_name(identifier)
        if colleague:
            return colleague.email.lower()
        
        raise ValueError(
            f"Unknown participant identifier: '{identifier}'. "
            f"Use an email address or a configured name."
        )

    def resolve_participants(self, identifiers: Sequence[str]) -> List[str]:
        """
        Resolve multiple participant identifiers, ensuring uniqueness.

        Args:
            identifiers: Iterable of participant aliases or email addresses.

        Returns:
            List of unique participant email addresses.
        """
        if not identifiers:
            raise ValueError("No participants provided.")

        resolved_emails: List[str] = []
        unknown_identifiers: List[str] = []

        for identifier in identifiers:
            try:
                email = self.resolve_participant(identifier)
            except ValueError:
                unknown_identifiers.append(identifier)
                continue

            if email not in resolved_emails:
                resolved_emails.append(email)

        if unknown_identifiers:
            missing = ", ".join(sorted(set(unknown_identifiers)))
            raise ValueError(
                f"Unknown participant identifier(s): {missing}. "
                "Ensure they exist in the configuration or provide valid email addresses."
            )

        return resolved_emails


def get_default_config_path() -> Path:
    """Get the default configuration file path."""
    # Look for config.yaml in current directory
    current_dir = Path.cwd()
    config_path = current_dir / "config.yaml"
    
    if not config_path.exists():
        # Try in the project root (parent of src/)
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config.yaml"
    
    return config_path

