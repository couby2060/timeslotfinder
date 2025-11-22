# 🏗️ Architecture Documentation

## Hexagonal Architecture (Ports & Adapters)

Dieses Projekt folgt dem Hexagonal Architecture Pattern, auch bekannt als Ports & Adapters Pattern.

### Warum Hexagonal Architecture?

1. **Testbarkeit**: Domain-Logik kann ohne externe Dependencies getestet werden
2. **Flexibilität**: Adapter können einfach ausgetauscht werden (z.B. Google Calendar statt MS Graph)
3. **Wartbarkeit**: Klare Trennung zwischen Business-Logik und technischer Implementierung
4. **Domain-First**: Die Business-Logik ist im Zentrum, nicht die Technologie

## Schichten-Übersicht

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                             │
│                    (User Interface)                          │
│                    src/cli/app.py                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ calls
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Adapter Layer                             │
│               (External Integrations)                        │
│                                                              │
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │ GraphAuthenticator│        │  GraphClient     │          │
│  │  (MSAL / OAuth)  │        │ (MS Graph API)   │          │
│  └──────────────────┘        └──────────────────┘          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ uses
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer                             │
│                 (Pure Business Logic)                        │
│                                                              │
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │    TimeRange     │        │  SlotCalculator  │          │
│  │   WorkingHours   │        │  (Core Logic)    │          │
│  │    TimeSlot      │        │                  │          │
│  └──────────────────┘        └──────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                         ▲
                         │
                         │ configured by
                         │
┌─────────────────────────────────────────────────────────────┐
│                   Configuration                              │
│                   src/config.py                              │
│                   (Pydantic Models)                          │
└─────────────────────────────────────────────────────────────┘
```

## Layer Details

### 1. Domain Layer (`src/domain/`)

**Verantwortung**: Reine Business-Logik, keine externe Dependencies

**Komponenten**:

#### `models.py`
- `TimeRange`: Immutable Zeitspanne mit Start/End
- `WorkingHours`: Konfiguration für Arbeitszeiten
- `TimeSlot`: Gefundener verfügbarer Slot

**Invarianten**:
- TimeRange: Start muss vor End sein
- Alle Zeiten sind timezone-aware (Pendulum DateTime)

#### `slot_calculator.py`
- `SlotCalculator`: Kernalgorithmus zur Slot-Berechnung

**Algorithmus**:
```
1. Get Working Blocks (nur Arbeitstage, Arbeitszeiten)
2. Für jeden Teilnehmer:
   - Invertiere Busy → Free (innerhalb Working Hours)
3. Berechne Schnittmenge aller Free-Times
4. Filter nach Mindestdauer
5. Gib komplette Blöcke zurück (nicht gesplittet)
```

**Wichtig**: Diese Schicht kennt KEINE APIs, keine Datenbanken, kein I/O.

### 2. Adapter Layer (`src/adapters/`)

**Verantwortung**: Integration mit externen Systemen

#### `graph_authenticator.py`
- Implementiert OAuth2 Device Code Flow mit MSAL
- Token-Caching (spart Re-Authentifizierung)
- User-freundliche Console-Ausgaben

**Flow**:
```
1. Check Token Cache
2. If expired/missing:
   - Initiate Device Flow
   - Display Code & URL
   - Wait for User Login
   - Store Token
3. Return Access Token
```

#### `graph_client.py`
- Microsoft Graph API Client
- Verwendet `/calendar/getSchedule` Endpoint
- Parsed API Response → Domain Models (TimeRange)

**Warum getSchedule statt findMeetingTimes?**
- Mehr Kontrolle über die Logik
- findMeetingTimes ist manchmal zu restriktiv
- getSchedule liefert raw free/busy Daten

### 3. CLI Layer (`src/cli/`)

**Verantwortung**: User Interface

#### `app.py`
- Typer-basierte CLI Commands
- Rich-basierte Pretty Printing
- Orchestriert Domain + Adapters

**Commands**:
- `find`: Hauptfunktion - suche Slots
- `list-colleagues`: Zeige konfigurierte Kollegen
- `test-auth`: Teste MS Graph Connection
- `clear-cache`: Lösche Token Cache
- `version`: Zeige Version

**Flow im `find` Command**:
```python
1. Load Config (config.yaml)
2. Parse & Validate Arguments
3. Authenticate (get Access Token)
4. Fetch Schedules (Graph API)
5. Calculate Slots (Domain Logic)
6. Display Results (Rich Tables)
```

### 4. Configuration (`src/config.py`)

**Verantwortung**: Typsichere Konfiguration

- Pydantic-basierte Models
- YAML-Loading
- Validation (z.B. Zeit-Format)
- Helper-Funktionen (z.B. Alias → Email Resolution)

## Data Flow

### Beispiel: "Find Slots for Max & Anna"

```
User:
  python timeslotfinder.py find max anna --start 2024-11-25

CLI (app.py):
  1. Parse arguments: ["max", "anna"], start_date="2024-11-25"
  2. Load config.yaml → resolve "max" → max@company.com
  3. Call GraphAuthenticator.get_access_token()
     → Returns: "eyJ0eXAiOi..."
  
Adapter (graph_client.py):
  4. GraphClient.get_schedule(["max@...", "anna@..."], start, end)
     → POST to https://graph.microsoft.com/v1.0/me/calendar/getSchedule
     → Parse Response
     → Returns: Dict[str, List[TimeRange]]
        {
          "max@...": [TimeRange(10:00-12:00), TimeRange(14:00-15:00)],
          "anna@...": [TimeRange(11:00-13:00)]
        }

Domain (slot_calculator.py):
  5. SlotCalculator.find_available_slots(...)
     → Working Blocks: [09:30-17:00]
     → Max Free: [09:30-10:00, 12:00-14:00, 15:00-17:00]
     → Anna Free: [09:30-11:00, 13:00-17:00]
     → Intersection: [09:30-10:00, 13:00-14:00, 15:00-17:00]
     → Filter: alle >= 30min
     → Returns: [TimeSlot(...), TimeSlot(...), ...]

CLI (app.py):
  6. Format & Display Results (Rich Table)
```

## Design Decisions

### Warum Pendulum statt Arrow oder datetime?

- Bessere Timezone-Unterstützung
- Intuitivere API
- Immutable DateTime Objects
- Bessere Parsing-Fähigkeiten

### Warum Device Code Flow?

- Best Practice für CLI/Terminal Apps
- Kein lokaler Web Server nötig
- User kann Browser auf anderem Gerät nutzen
- Sicherer als Client Credentials Flow

### Warum Typer statt Click oder argparse?

- Moderne Type Hints
- Automatische Validierung
- Bessere DX (Developer Experience)
- Integration mit Pydantic

### Warum Rich?

- Schöne Tables, Panels, Progress Bars
- Syntax Highlighting
- Cross-Platform Console Support

## Testing Strategy

### Unit Tests
```
tests/test_domain_models.py
  → Teste TimeRange, WorkingHours (reine Logik)

tests/test_slot_calculator.py
  → Teste SlotCalculator mit verschiedenen Szenarien
  → Keine API-Calls (isoliert)
```

### Integration Tests (TODO)
```
tests/test_graph_client.py
  → Mocke MS Graph API Responses
  → Teste Parsing-Logik

tests/test_cli.py
  → Teste CLI Commands (Typer CliRunner)
```

## Extension Points

### Neuer Calendar Provider (z.B. Google Calendar)

1. Erstelle `src/adapters/google_client.py`
2. Implementiere gleiche Interface wie `GraphClient`
3. In CLI: wähle Adapter basierend auf Config

```python
# config.yaml
provider: "microsoft"  # oder "google"

# src/cli/app.py
if config.provider == "microsoft":
    client = GraphClient(...)
elif config.provider == "google":
    client = GoogleClient(...)

# Domain Logic bleibt unverändert!
```

### Neues Output-Format (z.B. JSON)

```python
# src/cli/formatters.py
def format_json(slots: List[TimeSlot]) -> str:
    ...

def format_table(slots: List[TimeSlot]) -> Table:
    ...

# In CLI:
if output_format == "json":
    print(format_json(slots))
else:
    console.print(format_table(slots))
```

### Persistenz (z.B. Slot-History)

```python
# src/adapters/repository.py
class SlotRepository:
    def save(self, slots: List[TimeSlot]) -> None:
        ...
    
    def get_history(self) -> List[TimeSlot]:
        ...
```

## Dependency Flow Rule

```
┌─────────────┐
│     CLI     │  ← Depends on everything
└──────┬──────┘
       │
┌──────▼──────┐
│  Adapters   │  ← Depends on Domain
└──────┬──────┘
       │
┌──────▼──────┐
│   Domain    │  ← Depends on NOTHING (pure logic)
└─────────────┘
```

**Regel**: Dependencies zeigen immer nach innen (zur Domain).

Die Domain kennt keine Adapter, keine CLI, keine externe Welt.

## Weitere Resourcen

- [Hexagonal Architecture (Alistair Cockburn)](https://alistair.cockburn.us/hexagonal-architecture/)
- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Microsoft Graph API Docs](https://learn.microsoft.com/en-us/graph/)

