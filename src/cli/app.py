"""
Main CLI application using Typer.
"""

from pathlib import Path
from typing import List, Optional, Annotated
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
from ..adapters.mock_graph_client import MockGraphClient, MockGraphAuthenticator

app = typer.Typer(
    name="timeslotfinder",
    help="Find available meeting slots using Microsoft Graph API",
    add_completion=False
)

console = Console()


@app.command()
def find(
    config_file: Annotated[Optional[Path], typer.Option("--config", "-c", help="Path to config file. Defaults to ./config.yaml")] = None,
    mock: Annotated[Optional[bool], typer.Option("--mock", help="Use mock data instead of real Microsoft Graph API (for testing)")] = None
):
    """
    Find available meeting slots - Interactive mode.
    
    Examples:
    
        # Start the interactive slot finder
        timeslotfinder find
        
        # Use mock data (for testing without Azure)
        timeslotfinder find --mock
    """
    # Handle mock flag manually via sys.argv (workaround for Typer issue)
    import sys
    if mock is None:
        mock = "--mock" in sys.argv
    
    try:
        # Load configuration
        config_path = config_file or get_default_config_path()
        config = AppConfig.load_from_yaml(config_path)
        
        # Set pendulum timezone
        pendulum.set_locale("de")
        tz = config.timezone
        
        # Show header
        console.print("\n" + "="*60)
        console.print("[bold cyan]🗓️  Timeslotfinder - Verfügbare Termine finden[/bold cyan]")
        console.print("="*60 + "\n")
        
        if mock:
            console.print("[yellow]⚠  MOCK-MODUS: Verwende Test-Daten[/yellow]\n")
        
        # 1. TEILNEHMER AUSWÄHLEN
        console.print("[bold]1️⃣  Teilnehmer auswählen[/bold]")
        console.print("\nVerfügbare Kollegen:")
        for idx, colleague in enumerate(config.colleagues, 1):
            console.print(f"  {idx}. {colleague.name} ({colleague.email})")
        
        participant_input = typer.prompt(
            "\n→ Teilnehmer (Namen oder Nummern durch Leerzeichen getrennt)",
            default="1"
        )
        
        # Parse input - can be names or numbers
        participant_list = []
        for item in participant_input.split():
            item = item.strip()
            # Check if it's a number
            if item.isdigit():
                idx = int(item) - 1  # Convert to 0-based index
                if 0 <= idx < len(config.colleagues):
                    participant_list.append(config.colleagues[idx].name)
                else:
                    console.print(f"[yellow]Warnung: Nummer {item} ungültig, überspringe[/yellow]")
            else:
                # It's a name
                participant_list.append(item)
        
        # 2. MEETING-DAUER
        console.print(f"\n[bold]2️⃣  Meeting-Dauer[/bold]")
        min_duration = typer.prompt(
            "→ Mindestdauer in Minuten",
            default=config.defaults.duration_minutes,
            type=int
        )
        
        # 3. ZEITRAUM
        console.print(f"\n[bold]3️⃣  Zeitraum festlegen[/bold]")
        
        default_start = pendulum.now(tz).format("YYYY-MM-DD")
        start_date_str = typer.prompt(
            "→ Startdatum (YYYY-MM-DD)",
            default=default_start
        ).strip()
        
        # Parse start date to calculate default end
        try:
            start_temp = pendulum.parse(start_date_str, tz=tz)
            default_end = start_temp.add(days=7).format("YYYY-MM-DD")
        except Exception:
            default_end = pendulum.now(tz).add(days=7).format("YYYY-MM-DD")
        
        end_date_str = typer.prompt(
            "→ Enddatum (YYYY-MM-DD)",
            default=default_end
        ).strip()
        
        console.print("\n" + "="*60 + "\n")
        
        # Parse dates with better error handling
        try:
            start = pendulum.from_format(start_date_str, "YYYY-MM-DD", tz=tz).start_of("day")
        except Exception as e:
            console.print(f"[red]Fehler beim Parsen des Startdatums: {e}[/red]")
            raise typer.Exit(1)
        
        try:
            end = pendulum.from_format(end_date_str, "YYYY-MM-DD", tz=tz).end_of("day")
        except Exception as e:
            console.print(f"[red]Fehler beim Parsen des Enddatums: {e}[/red]")
            raise typer.Exit(1)
        
        # Resolve participant emails
        try:
            participant_emails = [
                config.resolve_participant(p) for p in participant_list
            ]
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(1)
        
        # Display search summary
        console.print("[bold cyan]📊 Zusammenfassung:[/bold cyan]")
        console.print(f"   Teilnehmer: {', '.join(participant_emails)}")
        console.print(f"   Zeitraum: {start.format('DD.MM.YYYY')} - {end.format('DD.MM.YYYY')}")
        console.print(f"   Mindestdauer: {min_duration} Minuten")
        console.print(f"   Arbeitszeiten: {config.defaults.start_hour}:00 - {config.defaults.end_hour}:00")
        console.print()
        
        # Authenticate (skip in mock mode)
        if mock:
            console.print("[bold]Schritt 1/3:[/bold] Authentifizierung...")
            console.print("[yellow]⊘ Übersprungen (Mock-Modus)[/yellow]")
            access_token = "mock_token"
        else:
            console.print("[bold]Schritt 1/3:[/bold] Authentifizierung...")
            authenticator = GraphAuthenticator(
                client_id=config.client_id,
                tenant_id=config.tenant_id,
                authority_url=config.get_authority_url()
            )
            access_token = authenticator.get_access_token(force_refresh=False)
            console.print("[green]✓ Authentifizierung erfolgreich[/green]")
        
        # Fetch schedules (use mock client in mock mode)
        console.print("\n[bold]Schritt 2/3:[/bold] Kalender-Daten abrufen...")
        
        if mock:
            client = MockGraphClient(access_token=access_token, config=config)
            console.print("[yellow]⊘ Verwende Mock-Daten aus Kalender-JSON[/yellow]")
        else:
            client = GraphClient(access_token=access_token)
        
        busy_times = client.get_schedule(
            emails=participant_emails,
            start_time=start,
            end_time=end,
            timezone=tz
        )
        
        if mock:
            console.print("[green]✓ Mock-Daten generiert[/green]")
        else:
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
            console.print(f"[bold green]✓ {len(slots)} verfügbare Zeitslot(s) gefunden:[/bold green]\n")
            
            # Simple list output
            for slot in slots:
                console.print(f"  {slot.format_display()}")
        
        console.print()
    
    except FileNotFoundError as e:
        console.print(f"[bold red]Fehler:[/bold red] {e}")
        raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[bold red]Fehler:[/bold red] {e}")
        import sys
        if "--debug" in sys.argv:
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

