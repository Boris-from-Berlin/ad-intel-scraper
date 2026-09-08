#!/usr/bin/env python3
"""Merge Meta advertisers + website map + Google cache into a lead list (CSV + XLSX).

Usage:
  python3 scripts/build_list.py --meta data/meta_DE.json data/meta_AT.json --webmap data/web_map.json \
      --google data/google_cache.json --include "chirurg|klinik|clinic|aesthet" --exclude "dental|zahn" --out out/leads.csv
"""
import argparse, csv, json, os, re, collections

def main(a):
    st = {}
    for f in a.meta:
        d = json.load(open(f)); d.pop("__done__", None)
        for k, v in d.items():
            m = st.setdefault(k, {"n": 0, "c": {}, "t": {}, "u": {}, "pl": "", "s": ""})
            m["n"] += v["n"]; m["c"].update(v["c"]); m["t"].update(v["t"]); m["u"].update(v["u"])
            if v["pl"] and not m["pl"]: m["pl"] = v["pl"]
            if v["s"] and (not m["s"] or v["s"] < m["s"]): m["s"] = v["s"]
    web = json.load(open(a.webmap)) if a.webmap and os.path.exists(a.webmap) else {}
    g = json.load(open(a.google)) if a.google and os.path.exists(a.google) else {}
    inc = re.compile(a.include, re.I) if a.include else None
    exc = re.compile(a.exclude, re.I) if a.exclude else None
    foreign = re.compile(a.foreign, re.I) if a.foreign else None
    SKIP = re.compile(r"facebook|wa\.me|t\.ly|amazon|doctolib|linktr")
    rows = []
    for k, v in st.items():
        if inc and not inc.search(k): continue
        if exc and exc.search(k): continue
        dom = ""
        for u in v["u"]:
            d = u.split("/")[2].removeprefix("www.")
            if not SKIP.search(d): dom = re.sub(r"^(link|lp|termin|angebote|go|shop)\.", "", d); break
        if not dom: dom = (web.get(k) or "").split(" ")[0]
        gg = g.get(dom, {}) if dom else {}; gn = gg.get("n")
        rows.append({"name": k, "countries_meta": "/".join(sorted(v["c"])), "website": dom, "meta_ads_active": v["n"],
                     "meta_since": v["s"], "meta_terms": ", ".join(sorted(v["t"])),
                     "google_ads": "yes" if gn and gn > 0 else ("no" if gn == 0 else "unchecked"),
                     "google_ads_count": gn if gn not in (None, -1) else "", "google_advertiser": ", ".join(gg.get("adv", [])),
                     "both": "yes" if gn and gn > 0 else "", "likely_foreign": "yes" if foreign and (foreign.search(k) or (dom and foreign.search(dom))) else "",
                     "facebook_page": v["pl"]})
    rows.sort(key=lambda r: (r["likely_foreign"], 0 if r["both"] else 1, -r["meta_ads_active"]))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    try:
        import openpyxl
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "leads"; ws.append(list(rows[0].keys()))
        for r in rows: ws.append(list(r.values()))
        for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = min(60, max(12, max(len(str(c.value or "")) for c in col) + 2))
        ws.freeze_panes = "A2"; wb.save(re.sub(r"\.csv$", ".xlsx", a.out))
    except ImportError: pass
    print(len(rows), "rows |", dict(collections.Counter(r["google_ads"] for r in rows)), "| both:", sum(1 for r in rows if r["both"]))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--meta", nargs="+", required=True); ap.add_argument("--webmap"); ap.add_argument("--google")
    ap.add_argument("--include"); ap.add_argument("--exclude"); ap.add_argument("--foreign", help="regex marking likely non-target-market advertisers")
    ap.add_argument("--out", default="out/leads.csv")
    main(ap.parse_args())
