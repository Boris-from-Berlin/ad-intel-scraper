# Bedienungsanleitung (Deutsch)

Ziel: Eine Liste von Firmen einer Branche, die **gerade aktiv Meta-Anzeigen (Facebook/Instagram) und Google-Anzeigen** schalten – mit Website, Anzahl Anzeigen und eingetragenem Werbetreibenden. Alles aus öffentlichen Transparenz-Datenbanken, ohne API-Keys, ohne Login.

Dauer für eine Branche in DACH: ca. 1–2 Stunden, davon der Großteil Wartezeit.

---

## 0. Einmalige Installation

Voraussetzungen: macOS/Linux/Windows, Python 3.9+, Google Chrome.

```bash
git clone https://github.com/Boris-from-Berlin/ad-intel-scraper.git
cd ad-intel-scraper
pip install -r requirements.txt
playwright install chromium
mkdir -p data out
```

---

## 1. Suchbegriffe festlegen

Nimm 5–12 Begriffe, die **in Anzeigentexten** vorkommen – also Leistungen, nicht Berufsbezeichnungen.

| Branche | gute Begriffe |
|---|---|
| Schönheitschirurgie | Brustvergrößerung, Facelift, Fettabsaugung, Nasenkorrektur, Lidstraffung, Bauchdeckenstraffung |
| Zahnärzte | Implantate, Bleaching, Invisalign, Zahnersatz, Angstpatienten |
| Fitnessstudios | Probetraining, Mitgliedschaft, Personal Training, Abnehmen |
| Immobilienmakler | Immobilie verkaufen, Wertermittlung, Hausverkauf |

Tipp: Zu allgemeine Begriffe („Beauty", „Facelift") liefern Kosmetik-Marken, Autos, Möbel als Rauschen. Das filtert Schritt 5 wieder raus, kostet aber Zeit.

---

## 2. Meta Ad Library scrapen

Ein Prozess pro Land, parallel:

```bash
for c in DE AT CH; do
  python3 scripts/meta_adlib.py \
    --terms "Brustvergrößerung,Facelift,Fettabsaugung,Nasenkorrektur,Lidstraffung" \
    --countries $c --scroll 60 --out data/meta_$c.json --log data/meta_$c.log &
done
wait
```

- Pro Begriff × Land ca. 1–3 Minuten.
- Fortschritt: `tail -f data/meta_DE.log`
- Abbruch mit Ctrl-C ist ok. Erneuter Start überspringt fertige Begriffe (Schlüssel `__done__` in der JSON).
- **Wichtig:** Facebook bremst das Nachladen. Pro Seite kommen meist 25–150 Anzeigen, sortiert nach Reichweite. Du bekommst die *aktivsten* Werbetreibenden, nicht alle. Mehr Begriffe = mehr Abdeckung.

Ergebnis `data/meta_DE.json`:
```json
"Dr. Muster - Plastische Chirurgie": {
  "n": 12,                          // aktive Anzeigen gesehen
  "c": {"DE": 1, "AT": 1},          // Länder
  "t": {"Facelift": 1},             // gefundene Begriffe
  "u": {"https://dr-muster.de": 1}, // Landing-Domain (nur bei ~15 % der Anzeigen sichtbar)
  "pl": "https://www.facebook.com/drmuster/",
  "s": "03.05.2026"                 // früheste „seit dem"-Angabe
}
```

---

## 3. Websites ermitteln

Nur Werbetreibende mit Website können auf Google Ads geprüft werden. Aus den Anzeigen kennt man ca. 15 % der Domains. Für den Rest:

**Warum nicht automatisch?** Suchmaschinen per Skript (DuckDuckGo, Bing, Brave) blocken oder liefern Müll. Zuverlässig ist nur eine Google-Suche aus deinem eigenen, eingeloggten Browser.

1. Namen ohne Website sammeln:
   ```bash
   python3 - <<'EOF'
   import json,glob,re
   st={}
   for f in glob.glob("data/meta_*.json"):
       d=json.load(open(f)); d.pop("__done__",None); st.update(d)
   need=[k for k,v in st.items() if not any("facebook" not in u for u in v["u"])]
   print("window.__names="+json.dumps(need,ensure_ascii=False)+";")
   EOF
   ```
2. Chrome: `google.com` öffnen, irgendetwas suchen, dann DevTools (⌥⌘I) → Console.
3. Die Zeile `window.__names=[...]` aus Schritt 1 einfügen, Enter. Danach den kompletten Inhalt von `scripts/website_lookup.js` einfügen, Enter.
4. Warten. Fortschritt: `Object.keys(window.__res).length`. Tempo ca. 3 Namen pro 10 Sekunden.
5. **Captcha:** Nach ca. 100 Suchen zeigt Google „ungewöhnlicher Datenverkehr". Dann 10–15 Minuten Pause, Seite neu laden, Schritt 3 wiederholen (fertige Namen werden übersprungen, aber `window.__res` vorher sichern!).
6. Ergebnis sichern: `copy(JSON.stringify(window.__res))` in der Console, dann in `data/web_map_raw.json` einfügen.
7. Bereinigen → `data/web_map.json` im Format `{"Name": "domain.de"}`. Erste Domain nehmen, aber **Sichtprüfung**: Finanzierungs-Portale, Bewertungsseiten, Kliniken-Vermittler rauswerfen. Domains nicht raten.

---

## 4. Google Ads prüfen

```bash
python3 scripts/google_transparency.py --from-webmap data/web_map.json --region DE --cache data/google_cache.json
```

- Ca. 6 Sekunden pro Domain. Bei vielen Domains: Liste teilen, 2–3 Prozesse mit eigener `--cache`-Datei, danach JSONs zusammenführen.
- `--region` = Land, in dem die Anzeigen erscheinen (DE, AT, CH …).
- Ergebnis: Anzahl Anzeigen + Name des eingetragenen Werbetreibenden. Das ist oft der **Rechtsträger** („Max Mustermann", „Muster GmbH"), nicht der Markenname.
- Einzelne Domains direkt: `--domains dr-muster.de,klinik-beispiel.at`

---

## 5. Liste bauen

```bash
python3 scripts/build_list.py \
  --meta data/meta_DE.json data/meta_AT.json data/meta_CH.json \
  --webmap data/web_map.json --google data/google_cache.json \
  --include "chirurg|klinik|clinic|aesthet|ästhet|praxis|dr\." \
  --exclude "dental|zahn|kosmetik" \
  --foreign "istanbul|turkey|hospital|\.com\.tr$" \
  --out out/schoenheitschirurgen_dach.csv
```

| Parameter | Bedeutung |
|---|---|
| `--include` | Regex auf den Namen – nur Treffer bleiben (Branchenfilter) |
| `--exclude` | Regex – Treffer fliegen raus (Rauschen) |
| `--foreign` | Regex auf Name/Domain – markiert Werbetreibende außerhalb des Zielmarkts (z. B. Medizintourismus), bleiben in der Liste, landen unten |
| `--out` | CSV; XLSX wird daneben erzeugt, wenn `openpyxl` installiert ist |

Spalten der Liste:

| Spalte | Inhalt |
|---|---|
| name | Name der Facebook-/Instagram-Seite |
| countries_meta | Länder, in denen Meta-Anzeigen gefunden wurden |
| website | Domain (aus Anzeige oder Schritt 3) |
| meta_ads_active | Anzahl gefundener aktiver Meta-Anzeigen |
| meta_since | früheste Laufzeit-Angabe |
| meta_terms | Suchbegriffe, unter denen die Seite auftauchte |
| google_ads | yes / no / unchecked |
| google_ads_count | Anzeigen im Google Transparency Center |
| google_advertiser | eingetragener Werbetreibender (Rechtsträger) |
| both | yes = Meta **und** Google aktiv |
| likely_foreign | yes = vermutlich außerhalb Zielmarkt |
| facebook_page | Link zur Seite |

Sortierung: Zielmarkt zuerst, dann „both", dann nach Anzahl Meta-Anzeigen.

---

## 6. Typische Probleme

| Problem | Lösung |
|---|---|
| Meta-Seite lädt nur 25 Anzeigen | Normal (Drosselung). Mehr Begriffe nutzen, später erneut laufen lassen. |
| `playwright` Fehler „Executable doesn't exist" | `playwright install chromium` |
| Google-Captcha in Schritt 3 | 10–15 Min Pause, `window.__res` vorher sichern |
| Google Transparency zeigt 0, aber Werbetreibender steht da | Zähler nicht lesbar, Skript setzt dann 1. Manuell prüfen: `https://adstransparency.google.com/?region=DE&domain=…` |
| Facebook-Seite per curl → HTTP 400 | Nur im Browser (Playwright) lesbar. Der Seitentitel enthält die Stadt („Name \| Stadt"). |
| Cookie-Banner blockiert | Skript klickt „Nur erforderliche Cookies"; bei neuem Text den Selektor in `COOKIE_BUTTONS` ergänzen |

---

## 7. Mit Claude Code

Ordner `skill/` nach `~/.claude/skills/ad-intel/` kopieren. Dann reicht:

> `/ad-intel` Zahnärzte DACH, Begriffe: Implantate, Bleaching, Invisalign

Claude führt die Schritte aus, nutzt für Schritt 3 den echten Chrome-Tab und liefert die XLSX.

---

## Rechtliches

Beide Quellen sind öffentliche Transparenz-Register (Meta: DSA-Pflicht in der EU, Google: Ads Transparency Center). Die Skripte lesen nur, was jeder Besucher sieht. Bitte Rate-Limits respektieren und die Daten DSGVO-konform verarbeiten (B2B-Kontaktdaten von Firmen, kein Profiling von Privatpersonen).
