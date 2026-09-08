# ad-intel-scraper

Find companies in a niche that are **actively running Meta ads and Google ads** — and turn them into a lead list.
No API keys, no login: uses the public Meta Ad Library and the Google Ads Transparency Center via headless Playwright.

Built for B2B prospecting (e.g. "all aesthetic surgeons in DACH with active Meta + Google campaigns").

**Deutsche Schritt-für-Schritt-Anleitung: [docs/ANLEITUNG.md](docs/ANLEITUNG.md)**

## Pipeline

| Step | Script | Source | Output |
|---|---|---|---|
| 1 | `scripts/meta_adlib.py` | Meta Ad Library (keyword × country, active ads, sorted by impressions) | `data/meta_<CC>.json` — advertiser, #ads, countries, terms, landing domain, FB page, first seen |
| 2 | `scripts/website_lookup.js` | Google search, run in your **own browser tab** (see notes) | `data/web_map.json` — `{advertiser: domain}` |
| 3 | `scripts/google_transparency.py` | Google Ads Transparency Center per domain | `data/google_cache.json` — ad count + registered advertiser |
| 4 | `scripts/build_list.py` | merge + filter | `out/leads.csv` + `.xlsx` |

## Quick start

```bash
pip install -r requirements.txt && playwright install chromium

# 1. Meta — run one process per country in parallel
for c in DE AT CH; do
  python3 scripts/meta_adlib.py --terms "Facelift,Brustvergrößerung,Fettabsaugung" --countries $c --scroll 60 --out data/meta_$c.json &
done; wait

# 2. Websites: landing URLs from ads cover ~15%. For the rest open google.com in Chrome, paste scripts/website_lookup.js
#    into DevTools with window.__names = [...advertiser names...], then save window.__res as data/web_map.json ({name: "domain"}).

# 3. Google Ads check
python3 scripts/google_transparency.py --from-webmap data/web_map.json --region DE

# 4. Lead list
python3 scripts/build_list.py --meta data/meta_*.json --webmap data/web_map.json --google data/google_cache.json \
  --include "chirurg|klinik|clinic|aesthet|ästhet|praxis|dr\." --exclude "dental|zahn" \
  --foreign "istanbul|turkey|\.com\.tr$|hospital" --out out/leads.csv
```

## Notes / lessons learned

- **Meta throttles infinite scroll.** Expect 25–150 ads per keyword×country even with 60 s scrolling. Results are sorted by impressions, so you get the *most active* advertisers, not all of them. Runs are resumable (`__done__` key).
- **Website discovery is the bottleneck.** DuckDuckGo/Brave/Bing via curl get blocked or return junk; headless DuckDuckGo hits a JS challenge. What works: same-origin `fetch('/search?q=…')` from a real, logged-in google.com tab (`website_lookup.js`). Google shows a captcha after ~100 queries — pause and resume.
- **Google Transparency Center** returns the *legal* advertiser name (often a person or GmbH), not the brand.
- Facebook page titles contain the city (`"Name | City"`), useful for geo-filtering; needs a browser, curl gets HTTP 400.
- Everything here reads public transparency data. Respect rate limits; don't hammer.

## Claude Code skill

`skill/SKILL.md` wraps this pipeline as a `/ad-intel` skill. Copy `skill/` to `~/.claude/skills/ad-intel/`.

## Example

`examples/` holds the column layout of a finished list (aesthetic surgeons DACH, Sept 2026): 354 advertisers with active Meta ads, 96 confirmed on Google Ads.

MIT © Boris Dittberner
