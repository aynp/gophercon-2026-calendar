# GopherCon 2026 — non-linear schedule

`index.html` is a self-contained grid view of the GopherCon 2026 agenda: time runs
down, rooms run across. No build step, no network calls, no dependencies — open the
file and it works offline.

    open index.html

## Why

The official agenda at <https://www.gophercon.com/agenda> is a single linear list, and
Bizzabo re-renders every time in *your browser's* timezone. From Tokyo that means a
Wednesday 09:00 Seattle keynote shows up as Thursday 01:00, so the list appears to
jumble days together. Underneath, the data is unambiguous: all 80 sessions are stored
in a single timezone (PDT, UTC−7) — verified in `build.py`.

This view fixes both problems:

- **Non-linear.** Parallel tracks sit side by side, so you can see what you're giving
  up by choosing a session.
- **One explicit timezone.** Pick Seattle / Tokyo / UTC / your local zone. Days stay
  grouped by the *venue's* calendar day (that's what "Day 1" means), and a `+1d` tag
  plus a banner flag where the date rolls over for you.

## Features

| | |
|---|---|
| Day tabs | Mon 3 → Thu 6 Aug; opens on today, or on Conference Day 1 beforehand |
| Timezone | Seattle · Tokyo · UTC · your local zone, remembered between visits |
| Filters | Toggle talks / workshops / community / sponsor / food / social / all-day |
| Search | Filter by title, speaker or room; non-matches dim rather than vanish |
| ★ Picks | Star sessions, then **★ My picks** to see only those |
| Export | **Export .ics** downloads your starred sessions (RFC 5545, validated) |
| Detail | Click any block for the abstract, speaker bios, and times in every zone |
| Links | `index.html#s=<sessionId>` deep-links a session, for sharing |
| Density | Compact / Normal / Roomy row heights |

Everything stays local — starred sessions live in `localStorage`, the `.ics` is
generated in-browser.

## Layout rules

- Columns are rooms, banded under a group header (Main Stage, Workshops, Community
  Day, Sponsor Sessions, Food & Breaks, Evening & Off-site).
- Off-site evening venues collapse into one **Off-site venues** column instead of
  adding a near-empty column per bar.
- All-day drop-in fixtures (registration, exhibition, hallway track, lounges, the
  Challenge Series) go in the **Runs all day** band rather than as 9-hour bars.
- Same-room overlaps split into side-by-side lanes.
- A 5-minute item is floored at 16px so it stays readable; the block below it is
  nudged down, and any real gap in the schedule absorbs the drift.

## Regenerating

`index.html` is generated from a snapshot in `data/`:

    python3 build.py        # data/*.json + template.html -> index.html

Edit `template.html` for markup/CSS/JS, `build.py` for classification and layout.

To re-pull the agenda (the site is a Bizzabo event, account 134118 / event 802722):

    curl -s "https://api.bizzabo.com/api/v2/agenda/events/802722/sessions" -o data/sessions.json
    curl -s "https://api.bizzabo.com/api/v2/agenda/events/802722/speakers" -o data/speakers.json
    curl -s "https://api.bizzabo.com/api/v2/agenda/events/802722/settings" -o data/settings.json
    python3 build.py

`build.py` prints a per-day summary so a changed agenda is easy to spot.

> Snapshot taken 1 Aug 2026: 80 sessions, 57 speakers, 4 days. Session times, rooms
> and abstracts can still change — check the official agenda before committing to a
> travel plan.
