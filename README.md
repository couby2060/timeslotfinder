# 🗓️ Timeslotfinder

Ein CLI-Tool für macOS (und andere Betriebssysteme), das über die Microsoft Graph API verfügbare Termine findet und gemeinsame Zeitslots ausgibt.

## 🏗️ Architektur

Das Projekt folgt der **Hexagonal Architecture (Ports & Adapters)**:

```
src/
├── domain/           # Core Business Logic (reine Domänen-Logik)
│   ├── models.py           # TimeRange, TimeSlot, WorkingHours
│   └── slot_calculator.py  # Schnittmengen-Algorithmus
├── adapters/         # Externe Integrationen
│   ├── graph_authenticator.py  # MSAL Authentication (Device Code Flow)
│   └── graph_client.py          # MS Graph API Client
├── cli/              # User Interface (Typer)
│   └── app.py              # CLI Commands
└── config.py         # Configuration Management (Pydantic)
```

### Vorteile dieser Architektur

- **Testbarkeit**: Domain-Logik ist unabhängig von externen APIs
- **Austauschbarkeit**: Graph API könnte durch andere Adapter ersetzt werden
- **Wartbarkeit**: Klare Trennung der Verantwortlichkeiten

## ✨ Features

- 🔐 **Microsoft OAuth2 Authentication** (Device Code Flow)
- 📅 **Kalender-Integration** über Microsoft Graph API
- ⏰ **Intelligente Slot-Berechnung** mit konfigurierbaren Arbeitszeiten
- 👥 **Mehrere Teilnehmer** gleichzeitig berücksichtigen
- 🌍 **Timezone-aware** (Europa/Berlin als Standard)
- 💾 **Token-Caching** (keine ständige Re-Authentifizierung)
- 🎨 **Schöne CLI** mit Rich-Library

## 📋 Voraussetzungen

- Python 3.11 oder höher
- Microsoft 365 Account mit Kalender-Zugriff
- Azure AD App Registration (siehe Setup)

## 🚀 Installation

### Quick Install (mit Script)

```bash
./INSTALL.sh
```

### Manuelle Installation

#### 1. Repository klonen

```bash
git clone <repository-url>
cd 2025-ms-timeslotfinder
```

#### 2. Virtual Environment erstellen

```bash
python3 -m venv venv
source venv/bin/activate  # Auf Windows: venv\Scripts\activate
```

#### 3. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 4. Azure AD App Registration

1. Gehe zu [Azure Portal](https://portal.azure.com)
2. Navigiere zu **Azure Active Directory** → **App registrations** → **New registration**
3. Name: `Timeslotfinder` (oder ein beliebiger Name)
4. Supported account types: **Accounts in this organizational directory only**
5. Redirect URI: **Public client/native (mobile & desktop)** → `http://localhost`
6. Klicke **Register**
7. Notiere die **Application (client) ID** und **Directory (tenant) ID**
8. Gehe zu **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions**
9. Füge hinzu: `Calendars.Read.Shared` und `Calendars.Read`
10. Klicke **Grant admin consent** (falls verfügbar)

### 5. Konfiguration erstellen

```bash
cp config.example.yaml config.yaml
```

Bearbeite `config.yaml` und füge deine IDs ein:

```yaml
microsoft:
  client_id: "your-client-id-here"
  tenant_id: "your-tenant-id-here"

colleagues:
  - alias: "max"
    email: "max.mustermann@company.com"
    name: "Max Mustermann"
  # Weitere Kollegen...
```

## 📖 Verwendung

### 🎭 Mock-Modus (OHNE Azure-Setup)

Perfekt zum Testen während du auf Azure-Freischaltung wartest:

```bash
# Mit Mock-Daten testen
python timeslotfinder.py find johannes julia --mock
```

Das `--mock` Flag:
- ✅ Überspringt Authentifizierung
- ✅ Verwendet simulierte Kalender-Daten
- ✅ Testet die komplette Logik & UI

Siehe auch: `TEST_MOCK_MODE.md` für Details

### Authentifizierung testen

```bash
python timeslotfinder.py test-auth
```

Beim ersten Mal wirst du aufgefordert, dich im Browser anzumelden.

### Kollegen anzeigen

```bash
python timeslotfinder.py list-colleagues
```

### Verfügbare Slots finden

```bash
# Mit Kollegen-Alias
python timeslotfinder.py find max anna

# Mit E-Mail-Adressen
python timeslotfinder.py find max.mustermann@company.com anna.schmidt@company.com

# Mit Mock-Daten (ohne Azure Auth)
python timeslotfinder.py find max anna --mock

# Mit Datumsbereich
python timeslotfinder.py find max anna --start 2024-11-25 --end 2024-11-29

# Mit spezifischer Mindestdauer
python timeslotfinder.py find max anna --duration 60

# Alle Optionen
python timeslotfinder.py find max anna \
  --start 2024-11-25 \
  --end 2024-11-29 \
  --duration 30 \
  --config config.yaml \
  --mock
```

### Token-Cache löschen

```bash
python timeslotfinder.py clear-cache
```

### Hilfe anzeigen

```bash
python timeslotfinder.py --help
python timeslotfinder.py find --help
```

## ⚙️ Konfiguration

Die `config.yaml` unterstützt folgende Optionen:

```yaml
# Microsoft Graph API Konfiguration
microsoft:
  client_id: "deine-client-id"
  tenant_id: "deine-tenant-id"
  authority: "https://login.microsoftonline.com/{tenant_id}"

# Standard-Arbeitszeiten
working_hours:
  start: "09:30"
  end: "17:00"
  exclude_days: [5, 6]  # 0=Montag, 6=Sonntag (5,6 = Sa, So)

# Zeitzone
timezone: "Europe/Berlin"

# Kollegen-Definitionen
colleagues:
  - alias: "max"
    email: "max.mustermann@company.com"
    name: "Max Mustermann"

# Standard-Meeting-Dauer in Minuten
default_duration: 30
```

## 🔍 Wie funktioniert der Algorithmus?

1. **Arbeitszeiten-Blöcke erstellen**: Für jeden Tag im Suchzeitraum werden Arbeitszeiten-Blöcke erstellt (z.B. 09:30-17:00, ohne Wochenenden)

2. **Busy-Zeiten von MS Graph abrufen**: Via `/calendar/getSchedule` API werden alle "busy" Zeiten der Teilnehmer abgerufen

3. **Invertierung zu Free-Zeiten**: Für jeden Teilnehmer werden die "busy" Zeiten von den Arbeitszeiten subtrahiert → ergibt "free" Zeiten

4. **Schnittmengen-Berechnung**: Die "free" Zeiten aller Teilnehmer werden geschnitten → nur Zeiten, in denen ALLE frei sind, bleiben übrig

5. **Filterung**: Nur Slots, die mindestens die gewünschte Dauer haben, werden behalten

6. **Output**: Die kompletten verfügbaren Blöcke werden ausgegeben (nicht in kleinere Stücke zerhackt)

**Beispiel:**

```
Arbeitszeiten:     09:00 ━━━━━━━━━━━━━━━━━━━━━━━━━━ 17:00
Max busy:          09:00 ████ 11:00                 ████ 16:00
Anna busy:                     12:00 ████ 14:00
────────────────────────────────────────────────────────────
Gemeinsam frei:          11:00 ──── 12:00    14:00 ──── 16:00
```

## 🧪 Testing

```bash
# Unit Tests ausführen
pytest

# Mit Coverage
pytest --cov=src --cov-report=html
```

## 🛠️ Development

```bash
# Code formatieren
black src/

# Linting
ruff check src/

# Type checking
mypy src/
```

## 📝 Hinweise

### Token-Cache

Der Token wird standardmäßig in `~/.timeslotfinder_token_cache.json` gespeichert. Dieser Cache ermöglicht es, dass du dich nicht bei jedem Aufruf neu anmelden musst.

### Berechtigungen

Das Tool benötigt die folgenden Microsoft Graph Permissions:
- `Calendars.Read.Shared`: Zugriff auf geteilte Kalender
- `Calendars.Read`: Zugriff auf den eigenen Kalender

### Timezone-Handling

Alle Zeiten werden in der konfigurierten Timezone (default: `Europe/Berlin`) verarbeitet. Die API-Antworten werden automatisch konvertiert.

### Busy-Status

Folgende Kalender-Status werden als "busy" betrachtet:
- `busy`: Beschäftigt
- `tentative`: Mit Vorbehalt
- `oof`: Out of Office
- `workingelsewhere`: An anderem Ort arbeitend

Status `free` wird als verfügbar betrachtet.

## 🤝 Contributing

1. Fork das Repository
2. Erstelle einen Feature Branch (`git checkout -b feature/amazing-feature`)
3. Commit deine Änderungen (`git commit -m 'Add amazing feature'`)
4. Push zum Branch (`git push origin feature/amazing-feature`)
5. Öffne einen Pull Request

## 📄 Lizenz

MIT License - siehe LICENSE Datei

## 🐛 Troubleshooting

### "Config file not found"

Stelle sicher, dass `config.yaml` im aktuellen Verzeichnis existiert oder verwende `--config` Option.

### "Authentication failed"

1. Überprüfe `client_id` und `tenant_id` in der Config
2. Stelle sicher, dass die App in Azure AD korrekt registriert ist
3. Versuche den Token-Cache zu löschen: `python timeslotfinder.py clear-cache`

### "No slots found"

- Überprüfe, ob die Teilnehmer wirklich freie Zeiten haben
- Versuche einen längeren Zeitraum: `--start` und `--end`
- Reduziere die Mindestdauer: `--duration 15`

## 👨‍💻 Autor

Entwickelt als Senior Python Software Architect Projekt mit Hexagonal Architecture Pattern.

## 🙏 Danksagungen

- Microsoft Graph API Documentation
- MSAL Python Library
- Typer & Rich für die fantastische CLI-Entwicklung
- Pendulum für robustes Timezone-Handling

