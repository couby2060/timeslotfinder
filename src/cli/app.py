"""
Main CLI application using Typer.
"""

from pathlib import Path
from typing import List, Optional, Annotated

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
from ..adapters.mock_graph_client import MockGraphClient

app = typer.Typer(
    name="timeslotfinder",
    help="Find available meeting slots using Microsoft Graph API",
    add_completion=False
)

console = Console()


def _run_interactive_wizard(config: AppConfig, console: Console, skip_dates: bool = False, start_date=None, end_date=None) -> dict:
    """
    Run the interactive wizard to gather meeting parameters from the user.
    
    Args:
        config: Application configuration
        console: Rich console for output
        skip_dates: If True, skip date prompts (used when --this-week or --next-week is set)
        start_date: Pre-set start date (when skip_dates=True)
        end_date: Pre-set end date (when skip_dates=True)
        
    Returns:
        Dictionary with keys: participants, start, end, duration_minutes
    """
    tz = config.timezone
    
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
    
    # 3. ZEITRAUM (skip if dates are pre-set)
    if skip_dates and start_date and end_date:
        start = start_date
        end = end_date
        console.print(f"\n[bold]3️⃣  Zeitraum[/bold]: {start.format('DD.MM.YYYY')} - {end.format('DD.MM.YYYY')} (vorgegeben)")
    else:
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
        
        # Parse dates with error handling
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
    
    console.print("\n" + "="*60 + "\n")
    
    return {
        "participants": participant_list,
        "start": start,
        "end": end,
        "duration_minutes": min_duration
    }


def _determine_time_range(
    *,
    console: Console,
    tz: str,
    this_week: bool,
    next_week: bool,
    start_option: Optional[str],
    end_option: Optional[str]
):
    """
    Resolve the desired time window based on shortcut flags or explicit dates.
    Returns (start_date, end_date, time_preset_flag).
    """
    if this_week and next_week:
        console.print("[red]Fehler: --this-week und --next-week können nicht gleichzeitig verwendet werden.[/red]")
        raise typer.Exit(1)

    now = pendulum.now(tz)

    if this_week:
        return now, now.end_of("week"), True

    if next_week:
        next_monday = now.next(pendulum.MONDAY).start_of("day")
        end_of_week = next_monday.add(days=6).end_of("day")
        return next_monday, end_of_week, True

    if start_option:
        try:
            start_date = pendulum.from_format(start_option, "YYYY-MM-DD", tz=tz).start_of("day")
        except Exception as e:
            console.print(f"[red]Fehler beim Parsen des Startdatums: {e}[/red]")
            raise typer.Exit(1)
    else:
        start_date = now.start_of("day")

    if end_option:
        try:
            end_date = pendulum.from_format(end_option, "YYYY-MM-DD", tz=tz).end_of("day")
        except Exception as e:
            console.print(f"[red]Fehler beim Parsen des Enddatums: {e}[/red]")
            raise typer.Exit(1)
    else:
        end_date = start_date.add(days=7).end_of("day")

    return start_date, end_date, False


@app.command()
def find(
    participants: Annotated[Optional[List[str]], typer.Argument(help="Teilnehmernamen (z. B. 'ich max'). Ohne Eingabe startet der Assistent.")] = None,
    config_file: Annotated[Optional[Path], typer.Option("--config", "-c", help="Path to config file. Defaults to ./config.yaml")] = None,
    start: Annotated[Optional[str], typer.Option("--start", help="Start date (YYYY-MM-DD)")] = None,
    end: Annotated[Optional[str], typer.Option("--end", help="End date (YYYY-MM-DD)")] = None,
    duration: Annotated[Optional[int], typer.Option("--duration", "-d", help="Meeting duration in minutes")] = None,
    mock: Annotated[bool, typer.Option("--mock", help="Mock-Daten nutzen und Authentifizierung überspringen.")] = False,
    this_week: Annotated[bool, typer.Option("--this-week", help="Suche von jetzt bis Ende der aktuellen Woche.")] = False,
    next_week: Annotated[bool, typer.Option("--next-week", help="Suche in der kommenden Woche (Montag–Sonntag).")] = False,
):
    """
    Find available meeting slots - Supports Interactive and Batch mode.
    
    Examples:
    
        # Interactive mode
        timeslotfinder find
        
        # Batch mode with participants
        timeslotfinder find ich max
        timeslotfinder find alice bob --duration 60
        
        # Quick time shortcuts
        timeslotfinder find ich max --this-week
        timeslotfinder find --next-week
        
        # Custom date range
        timeslotfinder find ich max --start 2024-01-15 --end 2024-01-19
        
        # Use mock data (for testing without Azure)
        timeslotfinder find --mock
        timeslotfinder find ich max --mock --next-week
    """
    
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
        
        time_start, time_end, time_preset = _determine_time_range(
            console=console,
            tz=tz,
            this_week=this_week,
            next_week=next_week,
            start_option=start,
            end_option=end
        )

        if mock:
            console.print("[yellow]⚠  MOCK-MODUS: Verwende Test-Daten[/yellow]\n")
        
        participant_args = participants or []

        if participant_args:
            participant_list = list(participant_args)
            min_duration = duration if duration is not None else config.defaults.duration_minutes
            start_date = time_start
            end_date = time_end
        else:
            wizard_result = _run_interactive_wizard(
                config,
                console,
                skip_dates=time_preset,
                start_date=time_start,
                end_date=time_end
            )
            participant_list = wizard_result["participants"]
            start_date = wizard_result["start"]
            end_date = wizard_result["end"]
            min_duration = wizard_result["duration_minutes"]
        
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
        console.print(f"   Zeitraum: {start_date.format('DD.MM.YYYY HH:mm')} - {end_date.format('DD.MM.YYYY HH:mm')}")
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
            start_time=start_date,
            end_time=end_date,
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
            start_date=start_date,
            end_date=end_date,
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

