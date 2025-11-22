# 🧪 Mock-Modus Test-Anleitung

Der Mock-Modus ist jetzt implementiert! So kannst du ihn testen:

## 1️⃣ Setup (falls noch nicht geschehen)

```bash
# Virtual Environment erstellen
python3 -m venv venv

# Aktivieren
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt
```

## 2️⃣ Mock-Modus testen

### Basis-Test (mit deinen konfigurierten Kollegen)

```bash
python timeslotfinder.py find johannes julia --mock
```

### Test für morgen

```bash
python timeslotfinder.py find johannes julia --mock --start $(date -v+1d +%Y-%m-%d) --end $(date -v+1d +%Y-%m-%d)
```

### Test mit 3+ Teilnehmern

```bash
python timeslotfinder.py find johannes julia test@example.com --mock
```

## 🎭 Mock-Szenario

Der MockGraphClient generiert folgende Test-Daten (relativ zu MORGEN):

### Für 2 Teilnehmer:
- **Johannes (User 1)**: Busy morgen 09:00-11:00
- **Julia (User 2)**: Busy morgen 10:00-12:00

**Erwartete freie Slots (bei Arbeitszeiten 9-17 Uhr):**
- ✅ **12:00 - 17:00** (5 Stunden gemeinsam frei)

### Für 3+ Teilnehmer:
- **User 1**: Busy 09:00-11:00
- **User 2**: Busy 10:00-12:00  
- **User 3+**: Busy 13:00-14:00

**Erwartete freie Slots:**
- ✅ **12:00 - 13:00** (1 Stunde)
- ✅ **14:00 - 17:00** (3 Stunden)

## 📸 Erwarteter Output

```
⚠ Running in MOCK mode using simulated data

╭─────────────────────────────────────────────────────────╮
│ 🔍 Timeslotfinder                                       │
├─────────────────────────────────────────────────────────┤
│ Teilnehmer: johannes.wilhelm@pinuts.de, julia@...     │
│ Zeitraum: 23.11.2024 - 23.11.2024                     │
│ Mindestdauer: 30 Minuten                               │
│ Arbeitszeiten: 9:00 - 17:00                           │
│ Modus: MOCK (Test-Daten)                              │
╰─────────────────────────────────────────────────────────╯

Schritt 1/3: Authentifizierung...
⊘ Übersprungen (Mock-Modus)

Schritt 2/3: Kalender-Daten abrufen...
⊘ Verwende Mock-Daten
✓ Mock-Daten generiert

Schritt 3/3: Verfügbare Slots berechnen...

✓ X verfügbare Zeitslot(s) gefunden!

┌────┬──────────────────────────────────┬─────────┐
│ #  │ Datum & Uhrzeit                  │   Dauer │
├────┼──────────────────────────────────┼─────────┤
│ 1  │ Samstag, 23.11.2024 | 12:00 – …│ XXX Min.│
└────┴──────────────────────────────────┴─────────┘
```

## 🔄 Normaler Modus (ohne --mock)

```bash
# Versuche den normalen Modus (erfordert Azure Auth)
python timeslotfinder.py find johannes julia

# → Wird Auth-Error geben, bis Azure App freigegeben ist
```

## ✅ Was getestet wird

Mit dem Mock-Modus kannst du testen:
- ✅ CLI Interface (Argumente, Flags)
- ✅ Config-Loading
- ✅ Domain-Logik (Slot-Berechnung)
- ✅ UI (Rich Tables, Panels)
- ✅ Zeitbereichs-Handling
- ✅ Mehrere Teilnehmer

**OHNE** auf Azure-Freischaltung warten zu müssen!

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'pendulum'"
→ Aktiviere das venv: `source venv/bin/activate`
→ Installiere Dependencies: `pip install -r requirements.txt`

### "No slots found"
→ Normal! Die Mock-Daten sind für MORGEN
→ Nutze `--start $(date -v+1d +%Y-%m-%d)`

### Config-Fehler
→ Stelle sicher, dass `config.yaml` existiert und valide ist
→ Du kannst dummy-IDs verwenden im Mock-Modus

## 🎯 Nächste Schritte

Sobald die Azure App freigegeben ist:
1. Füge die echten IDs in `config.yaml` ein
2. Teste mit: `python timeslotfinder.py test-auth`
3. Dann: `python timeslotfinder.py find johannes julia` (ohne --mock)

Happy Testing! 🚀

