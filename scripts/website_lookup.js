// Find advertiser websites via Google search — run in the DevTools console of an OPEN google.com tab
// (same-origin fetch uses your real browser session; curl/headless search engines get blocked).
// 1) Paste this file, 2) set NAMES, 3) wait, 4) copy(JSON.stringify(window.__res)) -> save as data/web_map_raw.json
// Google shows a captcha after ~100 queries — pause 10+ minutes, then re-run (already resolved names are skipped).
const NAMES = window.__names || []; // e.g. from data/meta_adv.json keys
const SKIP = /facebook\.com|instagram\.com|tiktok|youtube|linkedin|jameda|doctolib|groupon|amazon\.|wikipedia|google\.|yelp|golocal|11880|gelbeseiten|dasoertliche|cylex|kununu|xing\.com|pinterest|threads\.net|linktr|herold\.at|local\.ch|search\.ch|northdata|trustpilot|provenexpert|tripadvisor|booking\.com|gstatic|googleapis|schema\.org|w3\.org|youtu\.be|x\.com|twitter|wa\.me|bit\.ly|infobel|doctify|sellwerk|klinikbewertungen/i;
window.__res = window.__res || {}; window.__err = 0;
window.__worker = async (list) => {
  for (const q of list) {
    if (window.__res[q] && !['CAPTCHA', 'ERR'].includes(window.__res[q])) continue;
    try {
      const r = await fetch('/search?q=' + encodeURIComponent(q) + '&hl=de&num=10', { credentials: 'include' });
      const h = await r.text();
      if (/unusual traffic|ungewöhnlichen Datenverkehr/i.test(h)) { window.__res[q] = 'CAPTCHA'; if (++window.__err > 6) return; await new Promise(x => setTimeout(x, 20000)); continue; }
      const d = new DOMParser().parseFromString(h, 'text/html');
      const doms = [...new Set([...d.querySelectorAll('a[href^="http"]')].map(a => a.href).filter(u => !SKIP.test(u))
        .map(u => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return ''; } }))].filter(Boolean);
      window.__res[q] = doms.slice(0, 3).join(' ');
    } catch (e) { window.__res[q] = 'ERR'; }
    await new Promise(x => setTimeout(x, 1000 + Math.random() * 600));
  }
};
// 3 parallel workers
const third = Math.ceil(NAMES.length / 3);
window.__worker(NAMES.slice(0, third)); window.__worker(NAMES.slice(third, 2 * third)); window.__worker(NAMES.slice(2 * third));
console.log('started', NAMES.length, 'names; check window.__res');
