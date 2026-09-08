#!/usr/bin/env python3
"""Check domains in the Google Ads Transparency Center (headless): ad count + registered advertiser names.

Usage:
  python3 scripts/google_transparency.py --domains example.de,example.at --region DE
  python3 scripts/google_transparency.py --from-webmap data/web_map.json --cache data/google_cache.json

Cache JSON: {domain: {"n": ad_count, "adv": [advertiser names]}}  (n=-1 on error; n forced to 1 if names found but counter unreadable)
"""
import argparse, json, os, re, time
from playwright.sync_api import sync_playwright

NAMES_JS = """()=>[...new Set([...document.querySelectorAll('div,span')]
  .filter(e=>e.children.length===0&&e.nextElementSibling&&/Bestätigt|Verified/.test(e.nextElementSibling.textContent||''))
  .map(e=>e.textContent.trim()).filter(Boolean))].slice(0,4)"""

def check(domains, region="DE", cache_path="data/google_cache.json", wait=5):
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    todo = [d for d in domains if d and d not in cache]
    print(f"{len(todo)} domains to check", flush=True)
    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True); pg = br.new_context(locale="de-DE").new_page()
        for i, d in enumerate(todo, 1):
            try:
                pg.goto(f"https://adstransparency.google.com/?region={region}&domain={d}", timeout=40000, wait_until="domcontentloaded")
                time.sleep(wait)
                t = pg.inner_text("body")
                nums = [int(re.sub(r"[.   ]", "", x)) for x in re.findall(r"(\d[\d.   ]*)\s*(?:Anzeigen|ads)\b", t)]
                names = pg.evaluate(NAMES_JS)
                n = max(nums) if nums else 0
                if n == 0 and names: n = 1
                cache[d] = {"n": n, "adv": names}
            except Exception as e:
                cache[d] = {"n": -1, "adv": [], "err": str(e)[:80]}
            json.dump(cache, open(cache_path, "w"), ensure_ascii=False, indent=0)
            print(f"  [{i}/{len(todo)}] {d:40} {cache[d]['n']:>5} {', '.join(cache[d]['adv'])[:60]}", flush=True)
        br.close()
    return cache

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--domains", help="comma-separated domains")
    ap.add_argument("--from-webmap", help="JSON {name: domain} — checks all unique domains")
    ap.add_argument("--region", default="DE")
    ap.add_argument("--cache", default="data/google_cache.json")
    a = ap.parse_args()
    doms = []
    if a.domains: doms += [d.strip() for d in a.domains.split(",")]
    if a.from_webmap: doms += sorted({v for v in json.load(open(a.from_webmap)).values() if v})
    if not doms: ap.error("give --domains or --from-webmap")
    check(doms, a.region, a.cache)
