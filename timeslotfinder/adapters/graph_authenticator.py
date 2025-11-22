"""
Microsoft Graph API authentication using MSAL (Device Code Flow).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import msal
from rich.console import Console

from ..domain.exceptions import AuthenticationError

try:
    import keyring
    from keyring.errors import KeyringError
except ImportError:  # pragma: no cover - optional dependency at runtime
    keyring = None  # type: ignore[assignment]

    class KeyringError(Exception):  # type: ignore[override]
        """Fallback error type when keyring is unavailable."""


logger = logging.getLogger(__name__)

console = Console()


KEYRING_SERVICE_NAME = "timeslotfinder"


class GraphAuthenticator:
    """
    Handles authentication with Microsoft Graph API using Device Code Flow.
    
    This flow is ideal for CLI applications:
    1. User requests access
    2. App displays a code and URL
    3. User visits URL in browser and enters code
    4. User grants permissions
    5. App receives access token
    """
    
    # Required scopes for calendar access
    SCOPES = ["Calendars.Read.Shared", "Calendars.Read"]
    
    def __init__(
        self,
        client_id: str,
        tenant_id: str,
        authority_url: str | None = None,
        cache_file: Path | None = None
    ):
        """
        Initialize the authenticator.
        
        Args:
            client_id: Azure AD application (client) ID
            tenant_id: Azure AD tenant ID
            authority_url: Optional custom authority URL
            cache_file: Optional path to token cache file
        """
        self.client_id = client_id
        self.tenant_id = tenant_id
        
        # Build authority URL
        if authority_url:
            self.authority = authority_url
        else:
            self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        
        # Token cache
        self.cache_file = cache_file or Path.home() / ".timeslotfinder_token_cache.json"
        self._key_identifier = f"{self.client_id}:{self.tenant_id}"
        self._keyring_supported = keyring is not None
        self._cache_backend = "keyring" if self._keyring_supported else "file"
        self._insecure_storage_warning: Optional[str] = None
        if not self._keyring_supported:
            self._set_insecure_storage_warning(
                "Python keyring backend unavailable; using plaintext file cache."
            )
        self.cache = self._load_cache()
        
        # Create MSAL PublicClientApplication
        self.app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=self.authority,
            token_cache=self.cache
        )
    
    @property
    def cache_backend(self) -> str:
        """Return the active cache backend (keyring or file)."""
        return self._cache_backend

    @property
    def insecure_storage_warning(self) -> Optional[str]:
        """Provide a warning message when the cache falls back to plaintext storage."""
        return self._insecure_storage_warning

    def _load_cache(self) -> msal.SerializableTokenCache:
        """Load token cache from keyring or disk if it exists."""
        cache = msal.SerializableTokenCache()

        serialized = self._load_cache_from_keyring()
        if serialized is None:
            serialized = self._load_cache_from_file()

        if serialized:
            try:
                cache.deserialize(serialized)
            except ValueError as exc:
                logger.warning("Could not deserialize token cache: %s", exc)

        return cache

    def _load_cache_from_keyring(self) -> Optional[str]:
        if not self._keyring_supported:
            return None

        try:
            return keyring.get_password(KEYRING_SERVICE_NAME, self._key_identifier)
        except KeyringError as exc:  # pragma: no cover - environment dependent
            self._handle_keyring_failure(f"reading credentials failed: {exc}")
            return None

    def _load_cache_from_file(self) -> Optional[str]:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as file_handle:
                    return file_handle.read()
            except OSError as exc:
                logger.warning("Could not load token cache file %s: %s", self.cache_file, exc)
        return None
    
    def _save_cache(self) -> None:
        """Save token cache to the configured backend."""
        if not self.cache.has_state_changed:
            return

        serialized = self.cache.serialize()

        if self._keyring_supported and self._save_cache_to_keyring(serialized):
            return

        self._save_cache_to_file(serialized)

    def _save_cache_to_keyring(self, serialized: str) -> bool:
        if not self._keyring_supported:
            return False

        try:
            keyring.set_password(
                KEYRING_SERVICE_NAME,
                self._key_identifier,
                serialized,
            )
            self._cache_backend = "keyring"
            return True
        except KeyringError as exc:  # pragma: no cover - environment dependent
            self._handle_keyring_failure(f"writing credentials failed: {exc}")
            return False

    def _save_cache_to_file(self, serialized: str) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as file_handle:
                file_handle.write(serialized)
            self.cache_file.chmod(0o600)
        except OSError as exc:
            logger.warning("Could not save token cache to %s: %s", self.cache_file, exc)

    def _handle_keyring_failure(self, reason: str) -> None:
        if self._keyring_supported:
            logger.warning(
                "Secure credential storage unavailable (%s). Falling back to plaintext cache.",
                reason,
            )
        self._keyring_supported = False
        self._cache_backend = "file"
        self._set_insecure_storage_warning(
            f"Secure credential storage unavailable ({reason}). "
            f"Falling back to plaintext cache at {self.cache_file}."
        )

    def _set_insecure_storage_warning(self, message: str) -> None:
        if self._insecure_storage_warning:
            return
        self._insecure_storage_warning = message
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get a valid access token, using cache or requesting new one.
        
        Args:
            force_refresh: Force authentication even if cached token exists
            
        Returns:
            Access token string
            
        Raises:
            AuthenticationError: If authentication fails
        """
        # Try to get token silently from cache first
        if not force_refresh:
            accounts = self.app.get_accounts()
            if accounts:
                result = self.app.acquire_token_silent(
                    scopes=self.SCOPES,
                    account=accounts[0]
                )
                if result and "access_token" in result:
                    self._save_cache()
                    return result["access_token"]
        
        # Need to authenticate interactively
        return self._authenticate_device_code_flow()
    
    def _authenticate_device_code_flow(self) -> str:
        """
        Perform device code flow authentication.
        
        Returns:
            Access token
            
        Raises:
            AuthenticationError: If authentication fails
        """
        console.print("\n[bold cyan]🔐 Microsoft Authentication Required[/bold cyan]")
        console.print("You need to sign in to access calendar information.\n")
        
        # Initiate device flow
        try:
            flow = self.app.initiate_device_flow(scopes=self.SCOPES)
        except Exception as exc:  # pragma: no cover - MSAL internal failure
            raise AuthenticationError(f"Failed to initiate device flow: {exc}") from exc
        
        if "user_code" not in flow:
            raise AuthenticationError(
                f"Failed to initiate device flow: {flow.get('error_description', 'Unknown error')}"
            )
        
        # Display instructions to user
        console.print("[bold]Please follow these steps:[/bold]")
        console.print(f"1. Open a browser and go to: [bold cyan]{flow['verification_uri']}[/bold cyan]")
        console.print(f"2. Enter this code: [bold yellow]{flow['user_code']}[/bold yellow]")
        console.print("3. Sign in with your Microsoft account")
        console.print("4. Grant the requested permissions\n")
        console.print("[dim]Waiting for authentication...[/dim]\n")
        
        # Wait for user to complete authentication
        result = self.app.acquire_token_by_device_flow(flow)
        
        if "access_token" not in result:
            error = result.get("error_description", "Unknown error")
            raise AuthenticationError(f"Authentication failed: {error}")
        
        console.print("[bold green]✓ Authentication successful![/bold green]\n")
        
        # Save the cache
        self._save_cache()
        
        return result["access_token"]
    
    def clear_cache(self) -> None:
        """Clear the token cache (force re-authentication next time)."""
        if self.cache_file.exists():
            self.cache_file.unlink()
        if keyring is not None:
            try:
                keyring.delete_password(KEYRING_SERVICE_NAME, self._key_identifier)
            except KeyringError as exc:  # pragma: no cover - environment dependent
                logger.warning("Could not remove credentials from keyring: %s", exc)
        self.cache = msal.SerializableTokenCache()
        console.print("[green]Token cache cleared. You will need to re-authenticate.[/green]")

