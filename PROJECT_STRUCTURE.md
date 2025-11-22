# 📁 Project Structure

```
2025-ms-timeslotfinder/
│
├── 📄 README.md                      # Hauptdokumentation
├── 📄 QUICKSTART.md                  # 5-Minuten Setup Guide
├── 📄 ARCHITECTURE.md                # Architektur-Dokumentation
├── 📄 PROJECT_STRUCTURE.md           # Diese Datei
│
├── 📄 pyproject.toml                 # Python Project Config & Dependencies
├── 📄 Makefile                       # Build & Dev Commands
├── 📄 LICENSE                        # MIT License
├── 📄 .python-version                # Python Version (pyenv)
├── 📄 .gitignore                     # Git Ignore Rules
│
├── 📄 config.example.yaml            # Beispiel-Konfiguration
├── 📄 timeslotfinder.py              # Convenience Entry Point
│
├── 📁 src/                           # Source Code
│   ├── 📄 __init__.py                # Package Init
│   ├── 📄 __main__.py                # Module Entry Point
│   ├── 📄 config.py                  # Configuration Management
│   │
│   ├── 📁 domain/                    # 🎯 CORE BUSINESS LOGIC
│   │   ├── 📄 __init__.py
│   │   ├── 📄 models.py              # TimeRange, WorkingHours, TimeSlot
│   │   └── 📄 slot_calculator.py     # Slot-Berechnungs-Algorithmus
│   │
│   ├── 📁 adapters/                  # 🔌 EXTERNAL INTEGRATIONS
│   │   ├── 📄 __init__.py
│   │   ├── 📄 graph_authenticator.py # MS OAuth (MSAL)
│   │   └── 📄 graph_client.py        # MS Graph API Client
│   │
│   └── 📁 cli/                       # 💻 USER INTERFACE
│       ├── 📄 __init__.py
│       └── 📄 app.py                 # Typer CLI Commands
│
└── 📁 tests/                         # 🧪 TESTS
    ├── 📄 __init__.py
    ├── 📄 test_domain_models.py      # Domain Model Tests
    └── 📄 test_slot_calculator.py    # Calculator Logic Tests
```

## File Descriptions

### 📚 Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Vollständige Projekt-Dokumentation mit Features, Installation, Usage |
| `QUICKSTART.md` | 5-Minuten Setup Guide für neue User |
| `ARCHITECTURE.md` | Detaillierte Architektur-Dokumentation (Hexagonal Architecture) |
| `PROJECT_STRUCTURE.md` | Diese Datei - Übersicht der Projektstruktur |

### ⚙️ Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Projekt-Metadaten, Dependencies und Tool-Konfiguration |
| `Makefile` | Development Commands (make format, make test, etc.) |
| `.python-version` | Python Version für pyenv |
| `.gitignore` | Git Ignore Rules |
| `config.example.yaml` | Template für user config.yaml (nicht in Git) |

### 🎯 Core Source Files

#### Domain Layer (Pure Business Logic)

**`src/domain/models.py`**
- `TimeRange`: Immutable Zeitspanne (start, end)
- `WorkingHours`: Arbeitszeiten-Konfiguration
- `TimeSlot`: Gefundener verfügbarer Slot

**`src/domain/slot_calculator.py`**
- `SlotCalculator`: Kern-Algorithmus
  - Berechnet Working Blocks
  - Invertiert Busy → Free
  - Berechnet Schnittmengen
  - Filtert nach Min-Duration

#### Adapter Layer (External Integrations)

**`src/adapters/graph_authenticator.py`**
- `GraphAuthenticator`: OAuth2 Authentication
  - Device Code Flow (MSAL)
  - Token Caching
  - User-Friendly Console Output

**`src/adapters/graph_client.py`**
- `GraphClient`: Microsoft Graph API
  - `/calendar/getSchedule` Endpoint
  - Response Parsing → Domain Models
  - Error Handling

#### CLI Layer (User Interface)

**`src/cli/app.py`**
- Typer Commands:
  - `find`: Suche Slots
  - `list-colleagues`: Zeige Kollegen
  - `test-auth`: Teste Auth
  - `clear-cache`: Lösche Token Cache
  - `version`: Zeige Version

#### Configuration

**`src/config.py`**
- Pydantic Models für Config
- YAML Loading
- Validation
- Helper Functions (Alias → Email)

### 🧪 Test Files

| File | Tests |
|------|-------|
| `tests/test_domain_models.py` | TimeRange, WorkingHours Tests |
| `tests/test_slot_calculator.py` | SlotCalculator Logic Tests |

### 🚀 Entry Points

| File | Usage |
|------|-------|
| `timeslotfinder.py` | Direct execution: `python timeslotfinder.py` |
| `src/__main__.py` | Module execution: `python -m src` |
| After install | Command: `timeslotfinder` (defined in pyproject) |

## Directory Guidelines

### `src/domain/` - THE CORE

**Regeln**:
- ✅ Nur pure Python Business Logic
- ✅ Keine External Dependencies (außer Hilfsbibliotheken wie Pendulum)
- ✅ Keine API Calls
- ✅ Keine Database Access
- ✅ Keine I/O Operations
- ✅ 100% testbar ohne Mocks

**Warum?**
- Maximum Testability
- Maximum Reusability
- Technology-agnostic

### `src/adapters/` - THE PLUGINS

**Regeln**:
- ✅ Darf Domain Models nutzen
- ✅ Implementiert externe Integrationen
- ✅ Konvertiert External Data → Domain Models
- ❌ Kennt keine CLI Details
- ❌ Keine Business Logic (nur Adapter-Code)

**Warum?**
- Austauschbare Adapter (MS Graph → Google Calendar)
- Klare Verantwortlichkeit

### `src/cli/` - THE INTERFACE

**Regeln**:
- ✅ Darf alles nutzen (Domain + Adapters)
- ✅ User Interaction & Presentation
- ✅ Orchestrierung
- ❌ Keine Business Logic (delegiert an Domain)

**Warum?**
- UI-Logik getrennt von Business-Logik
- Könnte durch Web-UI ersetzt werden

### `tests/` - THE SAFETY NET

**Struktur**:
```
tests/
  test_domain_models.py       → Testet src/domain/models.py
  test_slot_calculator.py     → Testet src/domain/slot_calculator.py
  test_graph_client.py        → (TODO) Testet src/adapters/graph_client.py
  test_cli.py                 → (TODO) Testet src/cli/app.py
```

**Naming Convention**: `test_{module_name}.py`

## File Size Guidelines

| Layer | File | Lines | Status |
|-------|------|-------|--------|
| Domain | models.py | ~150 | ✅ Good |
| Domain | slot_calculator.py | ~250 | ✅ Good |
| Adapter | graph_authenticator.py | ~150 | ✅ Good |
| Adapter | graph_client.py | ~120 | ✅ Good |
| CLI | app.py | ~300 | ✅ Good |
| Config | config.py | ~130 | ✅ Good |

**Guideline**: Halte Dateien unter 500 Zeilen. Bei größer → split in Module.

## Import Guidelines

```python
# ✅ GOOD - Explicit imports
from src.domain.models import TimeRange, TimeSlot
from src.adapters.graph_client import GraphClient

# ❌ BAD - Star imports
from src.domain.models import *

# ✅ GOOD - Relative imports innerhalb Package
# In src/cli/app.py:
from ..domain.models import TimeRange
from ..adapters.graph_client import GraphClient

# ✅ GOOD - Absolute imports von außen
# In tests/test_domain_models.py:
from src.domain.models import TimeRange
```

## Configuration Files Location

```
User Config (NOT in Git):
  ./config.yaml                    # Current directory
  oder: Custom via --config flag

Token Cache (NOT in Git):
  ~/.timeslotfinder_token_cache.json

Example Config (IN Git):
  ./config.example.yaml
```

## Development Workflow

```bash
# 1. Setup
python3 -m venv venv
source venv/bin/activate
pip install .[dev]

# 2. Run
python timeslotfinder.py find max anna

# 3. Test
make test
# oder: pytest

# 4. Format & Lint
make format
make lint

# 5. Type Check
make type-check
```

## Future Additions (Possible)

```
2025-ms-timeslotfinder/
│
├── 📁 docs/                          # Sphinx Documentation
│   ├── conf.py
│   └── index.rst
│
├── 📁 scripts/                       # Helper Scripts
│   ├── setup_azure_app.py            # Auto-Setup für Azure AD
│   └── migrate_config.py             # Config Migration
│
├── 📁 src/adapters/
│   └── google_client.py              # Google Calendar Adapter
│
└── 📁 src/web/                       # Web UI (FastAPI)
    ├── app.py
    └── templates/
```

## Key Takeaways

1. **Hexagonal Architecture**: Domain im Zentrum, Adapters drum herum
2. **Clear Separation**: Jede Schicht hat klare Verantwortlichkeiten
3. **Testability**: Domain kann ohne External Dependencies getestet werden
4. **Documentation**: Jede wichtige Komponente ist dokumentiert
5. **Type Safety**: Pydantic & Type Hints überall

## Quick Navigation

- **Business Logic verstehen?** → `src/domain/slot_calculator.py`
- **MS Graph Integration anpassen?** → `src/adapters/graph_client.py`
- **CLI Command hinzufügen?** → `src/cli/app.py`
- **Config erweitern?** → `src/config.py`
- **Tests schreiben?** → `tests/test_*.py`
- **Setup für User?** → `QUICKSTART.md`
- **Architektur verstehen?** → `ARCHITECTURE.md`

