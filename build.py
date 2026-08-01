#!/usr/bin/env python3
"""Turn the Bizzabo agenda dump into a single self-contained non-linear schedule grid.

Input : data/sessions.json, data/speakers.json, data/settings.json
Output: index.html
"""

import datetime
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).parent
DATA = ROOT / "data"

VENUE_TZ = "America/Los_Angeles"
VENUE_OFFSET = datetime.timedelta(hours=-7)  # PDT, verified against every session

# ---------------------------------------------------------------- classification

# Continuous drop-in fixtures: they run for most of the day and belong in the
# "runs all day" band rather than as 9-hour bars inside the grid.
AMBIENT_PREFIX = (
    "registration",
    "hallway track",
    "gophercon exhibition",
    "attendee services",
    "challenge series:",
    "microsoft azure + github lounge",
)

GROUP_ORDER = [
    "Main Stage",
    "Workshops (separate ticket)",
    "Community Day",
    "Sponsor Sessions",
    "Food & Breaks",
    "Evening & Off-site",
]


def classify(title):
    """Order matters: the most specific prefix wins."""
    t = title.lower()
    if t.startswith(AMBIENT_PREFIX):
        return "ambient"
    if re.match(r"(half|full)-day workshop", t):
        return "workshop"
    if t.startswith("sponsored "):
        return "sponsor"
    if t.startswith(("community day", "contributors")):
        return "community"
    if "meetup" in t or "unite!" in t:
        return "social"
    if any(k in t for k in ("lunch", "coffee", "break", "beverage")):
        return "food"
    return "talk"


CAT_GROUP = {
    "talk": "Main Stage",
    "workshop": "Workshops (separate ticket)",
    "community": "Community Day",
    "sponsor": "Sponsor Sessions",
    "food": "Food & Breaks",
    "social": "Evening & Off-site",
}


def short_room(name):
    """Collapse 'Meeting Room 433, Level 4, SCC | Summit' -> 'MR 433'."""
    head = name.split(",")[0].strip()
    m = re.match(r"Meeting Rooms? ([\d\s&]+)$", head)
    if m:
        return "MR " + m.group(1).replace(" & ", "–").strip()
    if not is_onsite(name):
        return "Off-site venues"
    if head.startswith("Signature Lounge"):
        return "Signature Lounge area"
    if head.startswith("Paramount Lounge"):
        return "Paramount Lounge"
    if head.startswith("Terrace Suite"):
        return "Terrace Suite"
    if head.startswith("Overlook"):
        return "Overlook / Olympic View"
    return head


def is_onsite(name):
    return "SCC" in name or "Level 4" in name or "Level 5" in name


def room_sort_key(short):
    m = re.search(r"(\d{3})", short)
    return (0, int(m.group(1))) if m else (1, short)


# ---------------------------------------------------------------- load + shape

sessions_raw = json.loads((DATA / "sessions.json").read_text())["sessions"]
speakers_raw = json.loads((DATA / "speakers.json").read_text())
settings = json.loads((DATA / "settings.json").read_text())
locations = {l["id"]: l["name"] for l in settings["locations"]}

sp_index, speakers = {}, []
for s in speakers_raw:
    sp_index[s["id"]] = len(speakers)
    speakers.append(
        {
            "n": f"{s.get('firstname','')} {s.get('lastname','')}".strip(),
            "t": s.get("title") or "",
            "co": s.get("company") or "",
            "im": s.get("thumbnailUrl") or "",
            "b": s.get("bio") or "",
            "li": s.get("linkedinProfile") or "",
            "w": s.get("blog") or "",
        }
    )


def clean_html(h):
    h = re.sub(r"<(script|iframe|style)\b.*?</\1>", "", h, flags=re.S | re.I)
    return re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", h, flags=re.I)


def to_ms(iso):
    return int(
        datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000
    )


sessions = []
for x in sessions_raw:
    if x.get("hidden") or x.get("visibility", {}).get("type") != "PUBLIC":
        continue
    full_room = locations.get(x["locationId"], "TBA")
    venue_start = (
        datetime.datetime.fromisoformat(x["startTime"].replace("Z", "+00:00"))
        + VENUE_OFFSET
    )
    cat = classify(x["title"])
    sessions.append(
        {
            "i": x["id"],
            "t": x["title"],
            "s": to_ms(x["startTime"]),
            "e": to_ms(x["endTime"]),
            "sm": x["startMinute"],
            "em": x["endMinute"],
            "d": venue_start.strftime("%Y-%m-%d"),
            "r": short_room(full_room),
            "rf": full_room,
            "c": cat,
            "g": CAT_GROUP.get(cat, "Main Stage"),
            "sp": [
                [sp_index[p["speakerId"]], p.get("role") or "Speaker"]
                for p in x["speakers"]
                if p["speakerId"] in sp_index
            ],
            "x": clean_html(x.get("descriptionHtml") or ""),
        }
    )

sessions.sort(key=lambda s: (s["d"], s["sm"], s["r"]))

DAY_NOTE = {
    "2026-08-03": "Pre-conference",
    "2026-08-04": "Workshops + Community Day",
    "2026-08-05": "Conference Day 1",
    "2026-08-06": "Conference Day 2",
}

days = []
for d in sorted({s["d"] for s in sessions}):
    todays = [s for s in sessions if s["d"] == d]
    grid = [s for s in todays if s["c"] != "ambient"]
    cols = {}
    for s in grid:
        cols.setdefault(s["r"], set()).add(s["g"])
    ordered = sorted(
        cols,
        key=lambda r: (
            min(GROUP_ORDER.index(g) for g in cols[r]),
            room_sort_key(r),
        ),
    )
    date = datetime.date.fromisoformat(d)
    note = DAY_NOTE.get(d, "")
    days.append(
        {
            "d": d,
            "label": date.strftime("%a %-d %b"),
            "note": note,
            # the day to land on before the conference starts
            "main": note == "Conference Day 1",
            "cols": [
                {"r": r, "g": GROUP_ORDER[min(GROUP_ORDER.index(g) for g in cols[r])]}
                for r in ordered
            ],
            "start": min((s["sm"] for s in grid), default=480) // 60 * 60,
            "end": -(-max((s["em"] for s in grid), default=1080) // 60) * 60,
        }
    )

payload = {"days": days, "sessions": sessions, "speakers": speakers, "venueTz": VENUE_TZ}

# ---------------------------------------------------------------- emit

template = (ROOT / "template.html").read_text()
out = template.replace("/*__DATA__*/null", json.dumps(payload, ensure_ascii=False))
(ROOT / "index.html").write_text(out, encoding="utf-8")

print(f"index.html  {len(out)/1024:.0f} KB")
print(f"  {len(sessions)} sessions, {len(speakers)} speakers, {len(days)} days")
for d in days:
    print(f"  {d['d']} {d['note']:<28} {len(d['cols'])} columns  "
          f"{d['start']//60:02d}:00-{d['end']//60:02d}:00")
