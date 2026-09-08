---
name: ad-intel
description: Build a lead list of companies in a niche that actively run Meta ads and Google ads (DACH or any country). Uses the ad-intel-scraper repo (Meta Ad Library + Google Ads Transparency Center, headless, no login). Trigger on "wer schaltet Ads", "Meta und Google Ads Liste", "advertisers in <branche>", "ad intelligence lead list".
---

# /ad-intel — advertisers running Meta + Google ads

Repo: `~/Claude-Code-Projekte/ad-intel-scraper` (GitHub: Boris-from-Berlin/ad-intel-scraper).

## Workflow
1. **Clarify** niche keywords (5–12 German search terms as users would see them in ad copy) and countries (default DE,AT,CH). Work in a new folder `Research AI /<niche>-ads/` with `data/` + `out/`.
2. **Meta Ad Library** — first try the Meta MCP tool `ads_library_search` (fast, no browser). If token expired or results thin, run headless per country in parallel:
   `python3 <repo>/scripts/meta_adlib.py --terms "…" --countries DE --scroll 60 --out data/meta_DE.json &` (same for AT, CH). ~3 min per keyword×country. Resumable.
3. **Filter** advertisers by name regex (`--include/--exclude` in build_list.py); noise = cosmetics brands, dentists, medical-tourism brokers.
4. **Websites** — landing domains from ads cover ~15%. Rest: open google.com in the user's Chrome (claude-in-chrome), inject `scripts/website_lookup.js` with `window.__names`, poll `window.__res`, dump via DOM + get_page_text (JS tool output truncates at ~1 KB). Google captcha after ~100 queries → pause 10 min. Never guess domains from names; only keep verified hits.
5. **Google Ads** — `python3 <repo>/scripts/google_transparency.py --from-webmap data/web_map.json --region DE` (split domains over 2–3 processes with separate `--cache` files, merge after).
6. **Build** — `python3 <repo>/scripts/build_list.py --meta data/meta_*.json --webmap data/web_map.json --google data/google_cache.json --include … --exclude … --foreign … --out out/<niche>_leads.csv`. Deliver XLSX + short README with counts and limitations.

## Known traps
- curl to facebook.com → HTTP 400; DDG/Brave/Bing via curl → blocked or junk. Only real-browser Google works.
- JS tool output is truncated ~1 KB: write data into `document.body` and read with get_page_text; keep state in `window.name` (localStorage gets wiped by Facebook).
- browser_batch times out at ~40 s: one Ad Library page per call, or start background scrollers and collect later.
- Google Transparency advertiser = legal entity name, not brand.
