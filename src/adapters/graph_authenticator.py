"""
Microsoft Graph API authentication using MSAL (Device Code Flow).
"""

import json
from pathlib import Path
from typing import Dict, Any

import msal
from rich.console import Console

console = Console()


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
        self.cache = self._load_cache()
        
        # Create MSAL PublicClientApplication
        self.app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=self.authority,
            token_cache=self.cache
        )
    
    def _load_cache(self) -> msal.SerializableTokenCache:
        """Load token cache from disk if it exists."""
        cache = msal.SerializableTokenCache()
        
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    cache.deserialize(f.read())
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load token cache: {e}[/yellow]")
        
        return cache
    
    def _save_cache(self) -> None:
        """Save token cache to disk."""
        if self.cache.has_state_changed:
            try:
                with open(self.cache_file, "w") as f:
                    f.write(self.cache.serialize())
                # Set restrictive permissions (owner only)
                self.cache_file.chmod(0o600)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not save token cache: {e}[/yellow]")
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get a valid access token, using cache or requesting new one.
        
        Args:
            force_refresh: Force authentication even if cached token exists
            
        Returns:
            Access token string
            
        Raises:
            RuntimeError: If authentication fails
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
            RuntimeError: If authentication fails
        """
        console.print("\n[bold cyan]🔐 Microsoft Authentication Required[/bold cyan]")
        console.print("You need to sign in to access calendar information.\n")
        
        # Initiate device flow
        flow = self.app.initiate_device_flow(scopes=self.SCOPES)
        
        if "user_code" not in flow:
            raise RuntimeError(
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
            raise RuntimeError(f"Authentication failed: {error}")
        
        console.print("[bold green]✓ Authentication successful![/bold green]\n")
        
        # Save the cache
        self._save_cache()
        
        return result["access_token"]
    
    def clear_cache(self) -> None:
        """Clear the token cache (force re-authentication next time)."""
        if self.cache_file.exists():
            self.cache_file.unlink()
        self.cache = msal.SerializableTokenCache()
        console.print("[green]Token cache cleared. You will need to re-authenticate.[/green]")

