#!/usr/bin/env python3
"""
Build script: converts cancel-database/services/*.yaml → cancelfreely site JSON.
Run from workspace root: python3 cancel-database/build.py
"""
import yaml, json, os, glob

SERVICES_DIR = os.path.join(os.path.dirname(__file__), "services")
OUTPUT_PATH = "/tmp/cancelfreely/public/data/services.json"

def convert(data):
    """Map our YAML schema to the site's JSON schema."""
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
            name = a.get("name", "")
            url = a.get("url") or ""
            note = a.get("note", "")
            alt_list.append({"name": name, "url": url, "note": note})

    return {
        "name": data.get("name", ""),
        "slug": data.get("slug", ""),
        "url": data.get("url", ""),
        "category": data.get("category", ""),
        "cancel_method": data.get("cancel_method", ""),
        "cancel_difficulty": data.get("friction_score") or 0,
        "cancel_steps": steps,
        "cancel_url": data.get("direct_cancel_url") or "",
        "known_friction": friction_notes[:500] if friction_notes else "",
        "free_alternatives": alt_list,
        "last_verified": str(data.get("last_verified") or ""),
        "notes": data.get("notes", "") or "",
    }

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

# Sort by category then name
services.sort(key=lambda s: (s["category"], s["name"].lower()))

with open(OUTPUT_PATH, "w") as fh:
    json.dump(services, fh, indent=2)

print(f"Built {len(services)} services → {OUTPUT_PATH}")
if errors:
    print(f"Errors ({len(errors)}):")
    for e in errors:
        print(f"  {e}")
