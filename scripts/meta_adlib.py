#!/usr/bin/env python3
"""Scrape the public Meta Ad Library (no login) headlessly and aggregate advertisers.

Usage:
  python3 scripts/meta_adlib.py --terms "Facelift,Brustvergrößerung" --countries DE,AT,CH --scroll 60 --out data/meta_DE.json

Output JSON: {advertiser_name: {n, c:{country:1}, t:{term:1}, u:{landing_origin:1}, pl: fb_page_url, s: first_seen}}
Resumable: finished (country|term) pairs are stored under "__done__".
Note: Facebook throttles infinite scroll; expect ~25-150 ads per page, sorted by impressions (top advertisers first).
"""
import argparse, json, os, time, urllib.parse
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
EXTRACT_JS = r"""()=>{const out=[];
[...document.querySelectorAll('span')].filter(e=>e.children.length===0&&/^(Bibliotheks-ID|Library ID)/.test(e.textContent.trim())).forEach(el=>{
  let p=el;for(let i=0;i<7;i++)p=p.parentElement;
  const t=(p.innerText||'').replace(/​/g,'');
  if((t.match(/Bibliotheks-ID|Library ID/g)||[]).length!==1)return;
  const L=t.split('\n').map(s=>s.trim()).filter(Boolean);
  let i=L.indexOf('Anzeigendetails ansehen'); if(i<0)i=L.indexOf('See ad details');
  const name=i>=0?L[i+1]:null; if(!name)return;
  const a=[...p.querySelectorAll('a')].find(x=>x.innerText.trim()===name);
  const pl=a?a.getAttribute('href').split('?')[0]:'';
  const u=(t.match(/https?:\/\/[^\s]+/i)||[''])[0].toLowerCase().split('/').slice(0,3).join('/');
  const s=(t.match(/(?:Seit dem|Started running on) ([^\n]+?)(?: ausgeliefert)?$/m)||['',''])[1];
  out.push({name,pl,u,s});});
return out;}"""
COOKIE_BUTTONS = ['button:has-text("Nur erforderliche Cookies")', 'button:has-text("Alle ablehnen")',
                  'button:has-text("Decline optional cookies")', 'button:has-text("Only allow essential cookies")']

def log(msg, logfile):
    print(msg, flush=True)
    if logfile:
        with open(logfile, "a") as f: f.write(time.strftime("%H:%M:%S ") + msg + "\n")

def scrape(terms, countries, scroll_s, out, logfile=None, active_only=True):
    st = json.load(open(out)) if os.path.exists(out) else {}
    done = set(st.get("__done__", []))
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        pg = br.new_context(locale="de-DE", user_agent=UA, viewport={"width": 1400, "height": 900}).new_page()
        for term in terms:
            for c in countries:
                key = f"{c}|{term}"
                if key in done: continue
                url = ("https://www.facebook.com/ads/library/?ad_type=all&media_type=all&search_type=keyword_unordered"
                       f"&active_status={'active' if active_only else 'all'}&country={c}&q={urllib.parse.quote(term)}")
                try:
                    pg.goto(url, timeout=60000, wait_until="domcontentloaded"); time.sleep(4)
                    for sel in COOKIE_BUTTONS:
                        try:
                            if pg.locator(sel).first.is_visible(timeout=800): pg.locator(sel).first.click(); time.sleep(1); break
                        except Exception: pass
                    t0 = time.time(); last = 0; same = 0
                    while time.time() - t0 < scroll_s and same < 12:
                        pg.mouse.wheel(0, 20000); time.sleep(1.2)
                        h = pg.evaluate("document.body.scrollHeight"); same = same + 1 if h == last else 0; last = h
                    cards = pg.evaluate(EXTRACT_JS)
                except Exception as e:
                    log(f"ERROR {key}: {e}", logfile); continue
                for card in cards:
                    v = st.setdefault(card["name"], {"n": 0, "c": {}, "t": {}, "u": {}, "pl": "", "s": ""})
                    v["n"] += 1; v["c"][c] = 1; v["t"][term] = 1
                    if card["u"] and "facebook" not in card["u"]: v["u"][card["u"]] = 1
                    if card["pl"] and not v["pl"]: v["pl"] = card["pl"]
                    if card["s"] and (not v["s"] or card["s"] < v["s"]): v["s"] = card["s"]
                done.add(key); st["__done__"] = sorted(done)
                os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
                json.dump(st, open(out, "w"), ensure_ascii=False, indent=0)
                log(f"{key}: {len(cards)} ads, {len(st) - 1} advertisers total", logfile)
        br.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--terms", required=True, help="comma-separated search terms")
    ap.add_argument("--countries", default="DE,AT,CH", help="ISO-2 codes, comma-separated")
    ap.add_argument("--scroll", type=int, default=60, help="seconds to scroll per page")
    ap.add_argument("--out", default="data/meta_adv.json")
    ap.add_argument("--log", default=None)
    ap.add_argument("--all-status", action="store_true", help="include inactive ads")
    a = ap.parse_args()
    scrape([t.strip() for t in a.terms.split(",") if t.strip()], [c.strip().upper() for c in a.countries.split(",")],
           a.scroll, a.out, a.log, not a.all_status)
