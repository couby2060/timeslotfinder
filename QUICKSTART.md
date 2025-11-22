# 🚀 Quick Start Guide

Eine 5-Minuten-Anleitung zum Starten des Timeslotfinder.

## 1️⃣ Installation

```bash
# Python Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate  # Auf Windows: venv\Scripts\activate

# Dependencies installieren
pip install -r requirements.txt
```

## 2️⃣ Azure AD App erstellen (5 Minuten)

1. Gehe zu https://portal.azure.com
2. **Azure Active Directory** → **App registrations** → **New registration**
3. Name: `Timeslotfinder`
4. Supported account types: **Single tenant**
5. Redirect URI: **Public client** → `http://localhost`
6. Klicke **Register**

**Wichtig**: Notiere diese beiden IDs:
- ✅ **Application (client) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- ✅ **Directory (tenant) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

7. Gehe zu **API permissions** → **Add a permission**
8. **Microsoft Graph** → **Delegated permissions**
9. Suche und wähle:
   - ✅ `Calendars.Read`
   - ✅ `Calendars.Read.Shared`
10. Klicke **Add permissions**
11. Optional: **Grant admin consent** (beschleunigt die erste Anmeldung)

## 3️⃣ Config-Datei erstellen

```bash
# Beispiel-Config kopieren
cp config.example.yaml config.yaml

# Mit deinem Editor öffnen
nano config.yaml  # oder vi, vim, code, etc.
```

**Minimal-Config** (Pflichtfelder):

```yaml
microsoft:
  client_id: "DEINE-CLIENT-ID-HIER"
  tenant_id: "DEINE-TENANT-ID-HIER"

colleagues:
  - alias: "ich"
    email: "deine.email@company.com"
    name: "Dein Name"
```

Optional kannst du weitere Kollegen hinzufügen:

```yaml
colleagues:
  - alias: "max"
    email: "max.mustermann@company.com"
    name: "Max Mustermann"
  
  - alias: "anna"
    email: "anna.schmidt@company.com"
    name: "Anna Schmidt"
```

## 4️⃣ Authentifizierung testen

```bash
python timeslotfinder.py test-auth
```

Du wirst aufgefordert:
1. Eine URL im Browser zu öffnen (z.B. https://microsoft.com/devicelogin)
2. Einen Code einzugeben (wird angezeigt)
3. Dich mit deinem Microsoft-Account anzumelden
4. Die Berechtigungen zu akzeptieren

**Erfolgreich?** Du solltest sehen:

```
✓ Authentifizierung erfolgreich!

╭─────────────────────────────────────╮
│ ✓ Verbindungstest                   │
├─────────────────────────────────────┤
│ Benutzer: Dein Name                 │
│ E-Mail: deine.email@company.com     │
╰─────────────────────────────────────╯
```

## 5️⃣ Ersten Slot-Search ausführen

```bash
# Mit dir selbst (um zu testen)
python timeslotfinder.py find ich

# Mit Kollegen (Alias)
python timeslotfinder.py find max anna

# Mit E-Mail-Adressen
python timeslotfinder.py find max.mustermann@company.com

# Mit Datumsbereich
python timeslotfinder.py find max --start 2024-11-25 --end 2024-12-01

# Mit 60-Minuten Slots
python timeslotfinder.py find max anna --duration 60
```

## 🎉 Das war's!

Du solltest jetzt verfügbare Zeitslots sehen:

```
╭───────────────────────────────────────╮
│ 🔍 Timeslotfinder                     │
├───────────────────────────────────────┤
│ Teilnehmer: max@..., anna@...        │
│ Zeitraum: 25.11.2024 - 01.12.2024   │
│ Mindestdauer: 30 Minuten             │
│ Arbeitszeiten: 09:30 - 17:00        │
╰───────────────────────────────────────╯

✓ 12 verfügbare Zeitslot(s) gefunden!

┌────┬──────────────────────────────────┬────────┐
│ #  │ Datum & Uhrzeit                  │  Dauer │
├────┼──────────────────────────────────┼────────┤
│ 1  │ Montag, 25.11.2024 | 09:30 – ... │ 60 Min.│
│ 2  │ Montag, 25.11.2024 | 14:00 – ... │ 90 Min.│
...
```

## 🔧 Weitere Commands

```bash
# Alle konfigurierten Kollegen anzeigen
python timeslotfinder.py list-colleagues

# Token-Cache löschen (erzwingt neue Anmeldung)
python timeslotfinder.py clear-cache

# Hilfe anzeigen
python timeslotfinder.py --help
python timeslotfinder.py find --help
```

## ❓ Troubleshooting

### "Config file not found"
→ Stelle sicher, dass `config.yaml` im aktuellen Verzeichnis existiert

### "Authentication failed"
→ Überprüfe `client_id` und `tenant_id` in der Config
→ Stelle sicher, dass die Azure AD App korrekt eingerichtet ist

### "Unknown participant identifier"
→ Verwende einen konfigurierten Alias oder eine vollständige E-Mail-Adresse

### "No slots found"
→ Versuche einen längeren Zeitraum: `--start` und `--end`
→ Reduziere die Mindestdauer: `--duration 15`

## 📚 Weitere Dokumentation

- Vollständige Dokumentation: siehe `README.md`
- Architektur-Details: siehe `README.md` → Abschnitt "Architektur"
- API-Dokumentation: siehe Inline-Kommentare im Code

## 💡 Tipps

1. **Token wird gecacht**: Du musst dich nur einmal anmelden. Der Token wird in `~/.timeslotfinder_token_cache.json` gespeichert.

2. **Arbeitszeiten anpassen**: In `config.yaml` kannst du `working_hours` anpassen:
   ```yaml
   working_hours:
     start: "08:00"
     end: "18:00"
     exclude_days: [5, 6]  # 5=Samstag, 6=Sonntag
   ```

3. **Timezone ändern**: Standard ist `Europe/Berlin`, kann aber angepasst werden:
   ```yaml
   timezone: "America/New_York"
   ```

4. **Mehrere Personen**: Du kannst beliebig viele Teilnehmer angeben:
   ```bash
   python timeslotfinder.py find person1 person2 person3 person4
   ```

Happy slot hunting! 🎯

