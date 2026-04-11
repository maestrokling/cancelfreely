#!/usr/bin/env python3
"""
Build script: converts cancel-database/services/*.yaml →
  - /tmp/cancelfreely/public/data/services.json  (SPA data)
  - /tmp/cancelfreely/public/cancel/<slug>/index.html  (static SEO pages)
  - /tmp/cancelfreely/public/sitemap.xml
Run from workspace root: python3 cancel-database/build.py
"""
import yaml, json, os, glob, html
from datetime import date

SERVICES_DIR = os.path.dirname(__file__)
PUBLIC_DIR   = os.path.join(os.path.dirname(__file__), "public")
OUTPUT_PATH  = os.path.join(PUBLIC_DIR, "data", "services.json")
CANCEL_DIR   = os.path.join(PUBLIC_DIR, "cancel")
SITE_URL     = "https://cancelfreely.com"

# Slugs that also have a DeleteFreely data-deletion page
# Slugs that have a DitchTheMega full ecosystem exit guide
DITCHTHEMEGA_SLUGS = {
    "amazon-prime", "amazon-prime-video", "audible", "kindle-unlimited",
}

DELETEFREELY_SLUGS = {
    "23andme", "ancestry", "att", "bumble", "credit-karma",
    "dropbox", "evernote", "experian", "grammarly", "hinge",
    "match", "netflix", "notion", "peloton", "robinhood",
    "slack", "spectrum", "spotify", "t-mobile", "tinder",
    "verizon", "zoom",
}

DIFF_LABEL = ["", "Easy", "Simple", "Moderate", "Difficult", "Very Hard"]
DIFF_CLASS = ["", "d1", "d2", "d3", "d4", "d5"]

def escape(s):
    return html.escape(str(s or ""), quote=True)

def convert(data):
    steps = []
    for s in data.get("steps", []):
        if isinstance(s, dict):
            line = s.get("instruction", "")
            note = s.get("note", "")
            steps.append(f"{line} {note}".strip() if note else line)
        else:
            steps.append(str(s))

    dark = data.get("dark_patterns", []) or []
    friction_notes = "; ".join(
        d.get("description", "") for d in dark if isinstance(d, dict)
    ) if dark else ""

    retention = data.get("retention_tactics", []) or []
    if retention and friction_notes:
        friction_notes += " | Retention tactics: " + "; ".join(str(r) for r in retention)
    elif retention:
        friction_notes = "Retention tactics: " + "; ".join(str(r) for r in retention)

    alts = data.get("free_alternatives", []) or []
    alt_list = []
    for a in alts:
        if isinstance(a, dict):
            alt_list.append({
                "name": a.get("name", ""),
                "url": a.get("url") or "",
                "note": a.get("note", "")
            })

    return {
        "name":             data.get("name", ""),
        "slug":             data.get("slug", ""),
        "url":              data.get("url", ""),
        "category":         data.get("category", ""),
        "cancel_method":    data.get("cancel_method", ""),
        "cancel_difficulty": data.get("friction_score") or 0,
        "cancel_steps":     steps,
        "cancel_url":       data.get("direct_cancel_url") or "",
        "known_friction":   friction_notes[:500] if friction_notes else "",
        "free_alternatives": alt_list,
        "last_verified":    str(data.get("last_verified") or ""),
        "notes":            data.get("notes", "") or "",
        "dark_patterns":    dark,
        "retention_tactics": retention,
    }

def render_jsonld(s):
    import json as _json
    steps = [{"@type": "HowToStep", "text": step} for step in s["cancel_steps"]]
    lbl = DIFF_LABEL[s["cancel_difficulty"]] if 0 < s["cancel_difficulty"] <= 5 else ""
    data = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": f"How to Cancel {s['name']}",
        "description": f"Step-by-step instructions to cancel your {s['name']} subscription. Difficulty: {lbl}.",
        "step": steps
    }
    return f'<script type="application/ld+json">{_json.dumps(data, ensure_ascii=False)}</script>'


def render_page(s):
    name     = escape(s["name"])
    slug     = s["slug"]
    cfs      = s["cancel_difficulty"]
    label    = DIFF_LABEL[cfs] if 0 < cfs <= 5 else "Unknown"
    cls      = DIFF_CLASS[cfs] if 0 < cfs <= 5 else ""
    method   = escape(s["cancel_method"])
    verified = escape(s["last_verified"])
    notes    = escape(s["notes"])
    site_url = escape(s["url"])

    # Steps
    steps_html = "".join(
        f'<li>{escape(step)}</li>' for step in s["cancel_steps"]
    )

    # Direct cancel button
    cancel_btn = ""
    if s["cancel_url"]:
        cancel_btn = f'<a class="cancel-btn-lg" href="{escape(s["cancel_url"])}" target="_blank" rel="noopener">Go to cancel page →</a>'

    # Dark patterns
    dark_html = ""
    for dp in s.get("dark_patterns", []):
        if isinstance(dp, dict):
            t = escape(dp.get("type", ""))
            d = escape(dp.get("description", ""))
            slug_link = t.lower().replace(" ", "-").replace("/","-")
            dark_html += f'<div class="dark-item"><strong>⚠ {t}</strong><p>{d}</p><a href="/dark-patterns/#{slug_link}" class="pattern-link">What is {t.lower()}? →</a></div>'
    if dark_html:
        dark_html = f'<section class="watch-out"><h2>⚠ Watch Out — Dark Patterns</h2>{dark_html}</section>'

    # Retention tactics
    retention_html = ""
    for r in s.get("retention_tactics", []):
        retention_html += f'<li>{escape(str(r))}</li>'
    if retention_html:
        retention_html = f'''<section class="retention">
  <h2>What to Expect (Retention Tactics)</h2>
  <p>If you contact support, they will likely offer:</p>
  <ul>{retention_html}</ul>
  <p class="retention-tip">You do not need to accept any of these. Say: <em>"I would like to cancel my account completely."</em> Repeat as needed. You do not need to provide a reason.</p>
</section>'''

    # Free alternatives
    alts_html = ""
    for a in s.get("free_alternatives", []):
        n = escape(a.get("name", ""))
        u = escape(a.get("url", ""))
        note = escape(a.get("note", ""))
        link = f'<a href="{u}" target="_blank" rel="noopener">{n}</a>' if u else n
        alts_html += f'<li>{link}{(" — " + note) if note else ""}</li>'
    if alts_html:
        alts_html = f'<section class="alts"><h2>Free Alternatives</h2><ul>{alts_html}</ul></section>'

    # DitchTheMega cross-link (Amazon ecosystem pages)
    ditchthemega_html = ""
    if slug in DITCHTHEMEGA_SLUGS:
        ditchthemega_html = f'''<div class="delete-link-box" style="background:#1a1205;border-color:#78350f;">
  <strong style="color:#f59e0b;">🚪 Want to leave the entire Amazon ecosystem?</strong>
  <p style="color:#d1d5db;">Canceling {name} is step one. DitchTheMega has free, step-by-step guides to leaving every Amazon service — Kindle, Alexa, Ring, Photos, Prime Video, and more. <a href="https://ditchthemega.com/amazon/" style="color:#f59e0b;">See the complete Amazon exit guide →</a></p>
</div>'''

    # DeleteFreely cross-link
    delete_link_html = ""
    if slug in DELETEFREELY_SLUGS:
        delete_link_html = f'''<div class="delete-link-box">
  <strong>🗑 Want to also delete your {name} data?</strong>
  <p>Canceling removes your subscription. Your account and data may still exist. <a href="https://deletefreely.com/companies/{slug}/">See how to delete your {name} data →</a></p>
</div>'''

    meta_desc = f"How to cancel {s['name']} — step-by-step instructions, dark patterns to watch for, and free alternatives. Friction score: {label}."

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>How to Cancel {name} — CancelFreely</title>
  <meta name="description" content="{escape(meta_desc)}">
  <link rel="canonical" href="{SITE_URL}/cancel/{slug}/">
  <meta property="og:title" content="How to Cancel {name} — CancelFreely">
  <meta property="og:description" content="{escape(meta_desc)}">
  <meta property="og:url" content="{SITE_URL}/cancel/{slug}/">
  <meta property="og:type" content="article">
  <meta name="twitter:card" content="summary">
  {render_jsonld(s)}
  <link rel="stylesheet" href="../../style.css">
  <style>
    .svc-header  {{ max-width:740px; margin:2rem auto 0; padding:0 1rem; }}
    .svc-body    {{ max-width:740px; margin:1.5rem auto 4rem; padding:0 1rem; }}
    .svc-meta    {{ font-size:0.8rem; color:#888; margin:0.4rem 0 1.25rem; }}
    .svc-meta a  {{ color:#16a34a; }}
    .cancel-btn-lg {{ display:block; background:#16a34a; color:#fff; text-align:center; padding:0.85rem 1rem; border-radius:8px; font-size:1rem; font-weight:600; text-decoration:none; margin:1.25rem 0; }}
    .cancel-btn-lg:hover {{ background:#15803d; }}
    .svc-body h2 {{ font-size:0.95rem; font-weight:700; margin:2rem 0 0.6rem; color:#111; text-transform:uppercase; letter-spacing:0.04em; }}
    .steps       {{ padding-left:1.4rem; color:#333; font-size:0.9rem; line-height:1.7; }}
    .steps li    {{ margin-bottom:0.6rem; }}
    .watch-out   {{ background:#fef2f2; border:1px solid #fecaca; border-radius:10px; padding:1rem 1.25rem; margin:1.5rem 0; }}
    .watch-out h2 {{ color:#991b1b; margin-top:0; }}
    .dark-item   {{ margin-bottom:1rem; }}
    .dark-item strong {{ color:#991b1b; display:block; margin-bottom:0.2rem; }}
    .dark-item p {{ font-size:0.875rem; color:#7f1d1d; margin:0 0 0.25rem; }}
    .pattern-link {{ font-size:0.78rem; color:#b91c1c; }}
    .retention   {{ background:#fffbeb; border:1px solid #fde68a; border-radius:10px; padding:1rem 1.25rem; margin:1.5rem 0; }}
    .retention h2 {{ color:#92400e; margin-top:0; }}
    .retention ul {{ padding-left:1.2rem; font-size:0.875rem; color:#78350f; }}
    .retention li {{ margin-bottom:0.3rem; }}
    .retention-tip {{ font-size:0.85rem; color:#78350f; margin-top:0.75rem; margin-bottom:0; background:rgba(0,0,0,0.04); padding:0.6rem 0.75rem; border-radius:6px; }}
    .alts        {{ margin-top:1.5rem; }}
    .alts ul     {{ padding-left:1.2rem; font-size:0.875rem; color:#333; }}
    .alts li     {{ margin-bottom:0.3rem; }}
    .notes-box   {{ background:#f9f9f9; border:1px solid #e5e5e5; border-radius:8px; padding:1rem; font-size:0.85rem; color:#555; margin-top:1.5rem; }}
    .related     {{ border-top:1px solid #e5e5e5; margin-top:2.5rem; padding-top:1.25rem; }}
    .related h2  {{ font-size:0.85rem; color:#888; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.5rem; }}
    .related ul  {{ padding-left:1.2rem; font-size:0.875rem; }}
    .related li  {{ margin-bottom:0.3rem; }}
    .related a   {{ color:#16a34a; }}
    .report-row  {{ margin-top:1.5rem; font-size:0.8rem; color:#aaa; }}
    .report-row a {{ color:#aaa; }}
    .back-link   {{ display:inline-block; margin:1.5rem 1rem 0; font-size:0.85rem; color:#16a34a; text-decoration:none; }}
    .back-link:hover {{ text-decoration:underline; }}
    .delete-link-box {{ background:#eff6ff; border:1px solid #bfdbfe; border-radius:10px; padding:1rem 1.25rem; margin:1.5rem 0; font-size:0.875rem; }}
    .delete-link-box strong {{ display:block; margin-bottom:0.3rem; color:#1e3a5f; }}
    .delete-link-box p {{ margin:0; color:#374151; }}
    .delete-link-box a {{ color:#2563eb; }}
    @media(max-width:600px) {{
      .cancel-btn-lg {{ position:sticky; bottom:1rem; z-index:10; box-shadow:0 2px 8px rgba(0,0,0,0.15); }}
    }}
  </style>
</head>
<body>
  <header>
    <h1><a href="/" style="color:inherit;text-decoration:none;">CancelFreely</a></h1>
    <p class="tagline">Cancel any subscription. Free instructions. No tracking. No upsells.</p>
  </header>
  <a class="back-link" href="/cancel/">← All services</a>
  <div class="svc-header">
    <h1 style="font-size:1.5rem;margin-bottom:0.3rem;">How to Cancel {name}</h1>
    <span class="difficulty {cls}" style="font-size:0.85rem;">{label} — CFS {cfs}/5</span>
    <div class="svc-meta">Method: {method} · Last verified: {verified}{(' · <a href="' + site_url + '" target="_blank" rel="noopener">Official site</a>') if site_url else ''}</div>
  </div>
  <div class="svc-body">
    {cancel_btn}
    <h2>Cancellation Steps</h2>
    <ol class="steps">{steps_html}</ol>
    {dark_html}
    {retention_html}
    {alts_html}
    {('<div class="notes-box"><strong>Notes:</strong> ' + notes + '</div>') if notes else ''}
    {ditchthemega_html}
    {delete_link_html}
    <div class="related">
      <h2>Need more help?</h2>
      <ul>
        <li><a href="/cancellation-rights-by-state/">Your cancellation rights by state</a></li>
        <li><a href="/file-a-complaint/">How to file a complaint when they won't cancel</a></li>
        <li><a href="/chargeback-guide/">How to dispute a charge (chargeback guide)</a></li>
        <li><a href="/dark-patterns/">Dark pattern glossary</a></li>
        <li>Closing accounts on behalf of someone who has passed away? <a href="https://closingaccounts.com">See Closing Accounts →</a></li>
      </ul>
    </div>
    <div class="report-row">Something wrong? <a href="https://github.com/maestrokling/cancelfreely/issues/new?title=Issue+with+{slug}&labels=user-report" target="_blank" rel="noopener">Let us know →</a></div>
  </div>
  <footer>
    <p style="margin-bottom:-4px;">CancelFreely is free and never tracks you. No account required. No bank credentials. No tricks.</p>
    <p><a href="/about/">About</a> · <a href="/cancel/">All services</a> · <a href="/dark-patterns/">Dark Patterns</a> · <a href="/ftc-click-to-cancel/">FTC Rule</a> · <a href="/alternatives/">Services We Trust</a> · <a href="https://ko-fi.com/cancelfreely" target="_blank" rel="noopener">☕ Ko-fi</a></p>
    <p style="margin-top:.35rem;font-size:.8rem;"><a href="/privacy/" style="color:#aaa;">Privacy Policy</a> · <a href="/terms/" style="color:#aaa;">Terms of Use</a></p>
    <p style="margin-top:.5rem;font-size:.8rem;color:#aaa;">Part of the data sovereignty toolkit: <a href="https://deletefreely.com" style="color:#aaa;">DeleteFreely</a> · <a href="https://ditchthemega.com" style="color:#aaa;">DitchTheMega</a> · <a href="https://closingaccounts.com" style="color:#aaa;">Closing Accounts</a></p>
  </footer>
</body>
</html>"""

def build_sitemap(slugs):
    today = date.today().isoformat()
    urls = [
        f"  <url><loc>{SITE_URL}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>",
        f"  <url><loc>{SITE_URL}/about/</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>",
        f"  <url><loc>{SITE_URL}/find-your-subscriptions/</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>",
        f"  <url><loc>{SITE_URL}/alternatives/</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>",
        f"  <url><loc>{SITE_URL}/privacy/</loc><lastmod>{today}</lastmod><changefreq>yearly</changefreq><priority>0.3</priority></url>",
        f"  <url><loc>{SITE_URL}/terms/</loc><lastmod>{today}</lastmod><changefreq>yearly</changefreq><priority>0.3</priority></url>",
    ]
    for slug in slugs:
        urls.append(f'  <url><loc>{SITE_URL}/cancel/{slug}/</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>')
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>"

# ── Main ──────────────────────────────────────────────────────────────────────

files = sorted(glob.glob(os.path.join(SERVICES_DIR, "*.yaml")))
services = []
errors = []

for f in files:
    try:
        with open(f) as fh:
            data = yaml.safe_load(fh)
        if data and data.get("name"):
            services.append(convert(data))
    except Exception as e:
        errors.append(f"{os.path.basename(f)}: {e}")

services.sort(key=lambda s: (s["category"], s["name"].lower()))

# 1. Write services.json (strip extra fields not needed by SPA)
spa_fields = ["name","slug","url","category","cancel_method","cancel_difficulty",
              "cancel_steps","cancel_url","known_friction","free_alternatives",
              "last_verified","notes"]
spa_services = [{k: s[k] for k in spa_fields} for s in services]
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w") as fh:
    json.dump(spa_services, fh, indent=2)
print(f"Built {len(services)} services → {OUTPUT_PATH}")

# 2. Write static per-service pages
os.makedirs(CANCEL_DIR, exist_ok=True)
page_count = 0
for s in services:
    slug = s["slug"]
    if not slug:
        continue
    page_dir = os.path.join(CANCEL_DIR, slug)
    os.makedirs(page_dir, exist_ok=True)
    with open(os.path.join(page_dir, "index.html"), "w") as fh:
        fh.write(render_page(s))
    page_count += 1
print(f"Generated {page_count} static service pages → {CANCEL_DIR}/")

# 3. Write privacy and terms pages
privacy_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Privacy Policy — CancelFreely</title>
  <meta name="description" content="CancelFreely collects no personal data. No analytics. No cookies. No tracking.">
  <link rel="canonical" href="https://cancelfreely.com/privacy/">
  <link rel="stylesheet" href="../style.css">
  <style>
    .prose { max-width: 640px; margin: 2rem auto; padding: 0 1rem; }
    .prose h1 { font-size: 1.5rem; font-weight: 700; color: #16a34a; margin-bottom: 1rem; }
    .prose p { margin-bottom: 1rem; font-size: 0.95rem; line-height: 1.75; color: #333; }
    .prose a { color: #16a34a; }
  </style>
</head>
<body>
  <header>
    <h1><a href="/" style="color:inherit;text-decoration:none;">CancelFreely</a></h1>
    <p class="tagline">Cancel any subscription. Free instructions. No tracking. No upsells.</p>
  </header>
  <div class="prose">
    <h1>Privacy Policy</h1>
    <p>CancelFreely collects no personal data. We use no analytics. We set no cookies. We don't track your browsing. We don't know who you are. We don't want to know who you are.</p>
    <p>Our cancel database is open source and hosted on GitHub. The site is static HTML served through Cloudflare Pages. No server-side code processes your requests. No database stores your visits.</p>
    <p>If you use the service request form, it opens a GitHub Issue in a public repository. GitHub's <a href="https://docs.github.com/en/site-policy/privacy-policies/github-privacy-statement" target="_blank" rel="noopener">privacy policy</a> applies to that interaction, not ours, because we have nothing to apply.</p>
    <p>If you email us at <a href="mailto:info@cancelfreely.com">info@cancelfreely.com</a>, we receive your email. We don't add you to a list. We don't sell your address. We reply if a reply is needed and that's the end of it.</p>
    <p>This site exists to help you take control of your data. We start by not taking any of it.</p>
    <p style="color:#aaa;font-size:0.8rem;">Last updated: April 2026</p>
  </div>
  <footer>
    <p style="margin-bottom:-4px;">CancelFreely is free and never tracks you. No account required. No bank credentials. No tricks.</p>
    <p><a href="/about/">About</a> · <a href="/cancel/">All services</a> · <a href="/privacy/">Privacy Policy</a> · <a href="/terms/">Terms of Use</a></p>
  </footer>
</body>
</html>"""

terms_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Terms of Use — CancelFreely</title>
  <meta name="description" content="CancelFreely provides general cancellation information. Not legal advice. Use at your own risk.">
  <link rel="canonical" href="https://cancelfreely.com/terms/">
  <link rel="stylesheet" href="../style.css">
  <style>
    .prose { max-width: 640px; margin: 2rem auto; padding: 0 1rem; }
    .prose h1 { font-size: 1.5rem; font-weight: 700; color: #16a34a; margin-bottom: 1rem; }
    .prose p { margin-bottom: 1rem; font-size: 0.95rem; line-height: 1.75; color: #333; }
    .prose a { color: #16a34a; }
  </style>
</head>
<body>
  <header>
    <h1><a href="/" style="color:inherit;text-decoration:none;">CancelFreely</a></h1>
    <p class="tagline">Cancel any subscription. Free instructions. No tracking. No upsells.</p>
  </header>
  <div class="prose">
    <h1>Terms of Use</h1>
    <p>CancelFreely provides general information about subscription cancellation. It is not legal advice. We make reasonable efforts to keep instructions accurate and current but cannot guarantee accuracy. Use at your own risk.</p>
    <p>Links to third-party sites are not endorsements. We are not responsible for the practices of the services we document.</p>
    <p>The CancelFreely database is open source and available on GitHub. Content may be used and contributed under the terms of the repository license.</p>
    <p style="color:#aaa;font-size:0.8rem;">Last updated: April 2026</p>
  </div>
  <footer>
    <p style="margin-bottom:-4px;">CancelFreely is free and never tracks you. No account required. No bank credentials. No tricks.</p>
    <p><a href="/about/">About</a> · <a href="/cancel/">All services</a> · <a href="/privacy/">Privacy Policy</a> · <a href="/terms/">Terms of Use</a></p>
  </footer>
</body>
</html>"""

os.makedirs(os.path.join(PUBLIC_DIR, "privacy"), exist_ok=True)
with open(os.path.join(PUBLIC_DIR, "privacy", "index.html"), "w") as fh:
    fh.write(privacy_html)
print(f"Built privacy page")

os.makedirs(os.path.join(PUBLIC_DIR, "terms"), exist_ok=True)
with open(os.path.join(PUBLIC_DIR, "terms", "index.html"), "w") as fh:
    fh.write(terms_html)
print(f"Built terms page")

# 5. Write sitemap
sitemap = build_sitemap([s["slug"] for s in services if s["slug"]])
with open(os.path.join(PUBLIC_DIR, "sitemap.xml"), "w") as fh:
    fh.write(sitemap)
print(f"Sitemap → {PUBLIC_DIR}/sitemap.xml")

if errors:
    print(f"\nErrors ({len(errors)}):")
    for e in errors:
        print(f"  {e}")
