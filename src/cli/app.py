"""
Main CLI application using Typer.
"""

from pathlib import Path
from typing import List, Optional
from datetime import datetime

import pendulum
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..config import AppConfig, get_default_config_path
from ..domain.models import WorkingHours
from ..domain.slot_calculator import SlotCalculator
from ..adapters.graph_authenticator import GraphAuthenticator
from ..adapters.graph_client import GraphClient

app = typer.Typer(
    name="timeslotfinder",
    help="Find available meeting slots using Microsoft Graph API",
    add_completion=False
)

console = Console()


@app.command()
def find(
    participants: List[str] = typer.Argument(
        ...,
        help="Participants (aliases or email addresses)"
    ),
    start_date: str = typer.Option(
        None,
        "--start", "-s",
        help="Start date (YYYY-MM-DD). Defaults to today."
    ),
    end_date: str = typer.Option(
        None,
        "--end", "-e",
        help="End date (YYYY-MM-DD). Defaults to 7 days from start."
    ),
    duration: Optional[int] = typer.Option(
        None,
        "--duration", "-d",
        help="Minimum slot duration in minutes. Uses config default if not specified."
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to config file. Defaults to ./config.yaml"
    ),
    force_auth: bool = typer.Option(
        False,
        "--force-auth",
        help="Force re-authentication (ignore cached token)"
    )
):
    """
    Find available meeting slots for specified participants.
    
    Examples:
    
        # Find slots for Max and Anna (using aliases from config)
        timeslotfinder find max anna
        
        # Find slots with specific date range
        timeslotfinder find max anna --start 2024-11-25 --end 2024-11-29
        
        # Find 60-minute slots
        timeslotfinder find max.mustermann@company.com anna --duration 60
    """
    try:
        # Load configuration
        config_path = config_file or get_default_config_path()
        config = AppConfig.load_from_yaml(config_path)
        
        # Set pendulum timezone
        pendulum.set_locale("de")
        
        # Parse dates
        tz = config.timezone
        if start_date:
            start = pendulum.parse(start_date, tz=tz)
        else:
            start = pendulum.now(tz)
        
        # Ensure start is at beginning of day
        start = start.start_of("day")
        
        if end_date:
            end = pendulum.parse(end_date, tz=tz)
        else:
            end = start.add(days=7)
        
        # Ensure end is at end of day
        end = end.end_of("day")
        
        # Get duration
        min_duration = duration if duration else config.defaults.duration_minutes
        
        # Resolve participant emails
        try:
            participant_emails = [
                config.resolve_participant(p) for p in participants
            ]
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(1)
        
        # Display search parameters
        console.print()
        console.print(Panel.fit(
            f"[bold cyan]Suche verfügbare Zeitslots[/bold cyan]\n\n"
            f"[bold]Teilnehmer:[/bold] {', '.join(participant_emails)}\n"
            f"[bold]Zeitraum:[/bold] {start.format('DD.MM.YYYY')} - {end.format('DD.MM.YYYY')}\n"
            f"[bold]Mindestdauer:[/bold] {min_duration} Minuten\n"
            f"[bold]Arbeitszeiten:[/bold] {config.defaults.start_hour}:00 - {config.defaults.end_hour}:00",
            title="🔍 Timeslotfinder"
        ))
        
        # Authenticate
        console.print("\n[bold]Schritt 1/3:[/bold] Authentifizierung...")
        authenticator = GraphAuthenticator(
            client_id=config.client_id,
            tenant_id=config.tenant_id,
            authority_url=config.get_authority_url()
        )
        
        access_token = authenticator.get_access_token(force_refresh=force_auth)
        console.print("[green]✓ Authentifizierung erfolgreich[/green]")
        
        # Fetch schedules
        console.print("\n[bold]Schritt 2/3:[/bold] Kalender-Daten abrufen...")
        client = GraphClient(access_token=access_token)
        
        busy_times = client.get_schedule(
            emails=participant_emails,
            start_time=start,
            end_time=end,
            timezone=tz
        )
        
        console.print("[green]✓ Daten erfolgreich abgerufen[/green]")
        
        # Calculate available slots
        console.print("\n[bold]Schritt 3/3:[/bold] Verfügbare Slots berechnen...")
        
        working_hours = WorkingHours(
            start_time=config.defaults.get_start_time(),
            end_time=config.defaults.get_end_time(),
            exclude_weekdays=config.exclude_days,
            timezone=tz
        )
        
        calculator = SlotCalculator(working_hours=working_hours)
        
        slots = calculator.find_available_slots(
            start_date=start,
            end_date=end,
            busy_times=busy_times,
            min_duration_minutes=min_duration
        )
        
        # Display results
        console.print()
        if not slots:
            console.print(
                "[yellow]⚠ Keine verfügbaren Zeitslots gefunden.[/yellow]\n"
                "Versuchen Sie einen längeren Zeitraum oder eine kürzere Mindestdauer."
            )
        else:
            console.print(f"[bold green]✓ {len(slots)} verfügbare Zeitslot(s) gefunden![/bold green]\n")
            
            # Create table
            table = Table(
                title="Verfügbare Zeitslots",
                show_header=True,
                header_style="bold cyan"
            )
            table.add_column("#", style="dim", width=4)
            table.add_column("Datum & Uhrzeit", style="bold")
            table.add_column("Dauer", justify="right", style="cyan")
            
            for idx, slot in enumerate(slots, 1):
                table.add_row(
                    str(idx),
                    slot.format_display().rsplit("(", 1)[0].strip(),
                    f"{slot.time_range.duration_minutes()} Min."
                )
            
            console.print(table)
        
        console.print()
    
    except FileNotFoundError as e:
        console.print(f"[bold red]Fehler:[/bold red] {e}")
        raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[bold red]Fehler:[/bold red] {e}")
        if "--debug" in typer.Context.args:
            raise
        raise typer.Exit(1)


@app.command()
def list_colleagues(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to config file"
    )
):
    """
    List all configured colleagues.
    """
    try:
        config_path = config_file or get_default_config_path()
        config = AppConfig.load_from_yaml(config_path)
        
        if not config.colleagues:
            console.print("[yellow]Keine Kollegen in der Config-Datei definiert.[/yellow]")
            return
        
        table = Table(
            title="Konfigurierte Kollegen",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Name (Alias)", style="bold yellow")
        table.add_column("E-Mail", style="dim")
        
        for colleague in config.colleagues:
            table.add_row(
                colleague.name,
                colleague.email
            )
        
        console.print()
        console.print(table)
        console.print()
    
    except FileNotFoundError as e:
        console.print(f"[bold red]Fehler:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def test_auth(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to config file"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force re-authentication"
    )
):
    """
    Test Microsoft Graph authentication.
    """
    try:
        config_path = config_file or get_default_config_path()
        config = AppConfig.load_from_yaml(config_path)
        
        console.print("\n[bold]Testing Microsoft Graph authentication...[/bold]\n")
        
        # Authenticate
        authenticator = GraphAuthenticator(
            client_id=config.client_id,
            tenant_id=config.tenant_id,
            authority_url=config.get_authority_url()
        )
        
        access_token = authenticator.get_access_token(force_refresh=force)
        
        # Test connection
        client = GraphClient(access_token=access_token)
        user_info = client.test_connection()
        
        # Display success
        console.print(Panel.fit(
            f"[bold green]✓ Authentifizierung erfolgreich![/bold green]\n\n"
            f"[bold]Benutzer:[/bold] {user_info.get('displayName', 'N/A')}\n"
            f"[bold]E-Mail:[/bold] {user_info.get('mail') or user_info.get('userPrincipalName', 'N/A')}",
            title="✓ Verbindungstest"
        ))
        console.print()
    
    except Exception as e:
        console.print(f"\n[bold red]✗ Fehler:[/bold red] {e}\n")
        raise typer.Exit(1)


@app.command()
def clear_cache(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to config file"
    )
):
    """
    Clear the authentication token cache.
    """
    try:
        config_path = config_file or get_default_config_path()
        config = AppConfig.load_from_yaml(config_path)
        
        authenticator = GraphAuthenticator(
            client_id=config.client_id,
            tenant_id=config.tenant_id
        )
        
        authenticator.clear_cache()
        console.print("\n[green]✓ Token-Cache gelöscht.[/green]")
        console.print("Sie müssen sich beim nächsten Aufruf neu authentifizieren.\n")
    
    except Exception as e:
        console.print(f"[bold red]Fehler:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def version():
    """
    Show version information.
    """
    from .. import __version__
    console.print(f"\n[bold cyan]timeslotfinder[/bold cyan] version [bold]{__version__}[/bold]\n")


if __name__ == "__main__":
    app()

