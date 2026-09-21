# Fetching the JSON directly

Start with `indexes/manifest.json`. It lists available months, mosque IDs and
listing paths with event counts. All paths in the API are relative to the
repository root, not to the file containing the link. The index contract has
`schema_version: "1.0"`, independently of the event contract.

| Query | File |
| --- | --- |
| Discover available listings | `indexes/manifest.json` |
| All explicitly dated events in September | `indexes/months/2026-09.json` |
| An-Nahdhah's explicitly dated September events | `indexes/mosques/an-nahdhah/months/2026-09.json` |
| All recurring series | `indexes/recurring.json` |
| Sultan's recurring series | `indexes/mosques/sultan/recurring.json` |
| Events without resolved dates | `indexes/undated.json` |
| A mosque's events without resolved dates | `indexes/mosques/<mosque-id>/undated.json` |
| Full event, including evidence and extras | `events/<event-id>.json` |
| Full mosque record | `mosques/<mosque-id>.json` |

Month files exist only when populated. The manifest is authoritative: an absent
month means no explicitly dated records in this dataset, not that no events exist
in the real world. Recurring and undated files always exist, including empty
files for each registered mosque. Each listing is `{schema_version, events}`.
Counts are event/series counts, not session counts.

## Rendering a calendar or list

Rows contain title, description, associated mosque IDs, categories, status,
schedule, venue, people, languages, audience, registration, pricing and review
state. They also include `id` and `path` for fetching the full record. No detail
request is necessary to render a basic event listing. Evidence, sources, notes
and arbitrary extra data remain in the canonical record.

Month rows include `matched_occurrences`: only explicit occurrences overlapping
that month. The full schedule remains available in `schedule`. A series appears
once per relevant month; a multi-day occurrence appears in every month it touches,
including across years. Joint events appear in each associated mosque's listing.
Deduplicate by event ID when combining lists, or by ID plus occurrence when
rendering individual sessions. Rows sort by first matched occurrence date, then
ID; prayer-relative times are not assigned invented clock values.

Use Singapore local dates for the current month and date filters. A week crossing
a month boundary needs both month files. Test interval overlap using occurrence
`date` and `end_date` (or `date` if null), rather than filtering start dates alone.
There is deliberately no generated `today` or `upcoming` file that becomes stale
merely because midnight passes.

Recurring series are listed separately and are **not expanded into dates**.
Show them in a recurring-programmes section, retaining their literal schedule
and known bounds. Undated events are separate again. Neither list promises that
a programme is currently running. Date, status and review state are independent:
old scheduled records are not automatically marked completed; cancelled and
postponed events remain visible with their status. Clients choose their display
policy, and should visibly distinguish candidate records from reviewed records.

## Example

```js
// Use a known full commit SHA instead of "main" for consistent multi-file reads.
const ref = "main";
const base = `https://raw.githubusercontent.com/ruqqq/sg-mosques-events-database/${ref}/`;
async function read(path) {
  const response = await fetch(new URL(path, base));
  if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
  return response.json();
}
const manifest = await read("indexes/manifest.json");
const mosque = manifest.mosques["an-nahdhah"];
const listing = mosque.months["2026-09"];
const events = listing ? (await read(listing.path)).events : [];
const recurring = (await read(mosque.recurring.path)).events;
// Fetch read(events[0].path) when full details are needed.
```

All paths can also be served unchanged from a static host. Fetching `main` is
convenient but separate requests can straddle commits or cached versions. Pin all
requests for a session to the same full commit SHA when consistency matters.
Do not treat retrieval time as collection freshness; source retrieval timestamps
are retained in full event records, while worker health is private.

## Maintaining the read models

Canonical records live at stable UUID paths; the initial descriptive filenames
were migrated to this convention. Generate indexes after changing events or
mosques:

```sh
python scripts/build_indexes.py
python scripts/validate_all.py
python -m unittest discover -s tests -v
```

Commit canonical changes and generated indexes together. Do not edit indexes by
hand. Generation is deterministic and removes obsolete month files; unchanged
inputs produce unchanged bytes. Validation and CI reject missing, extra or stale
JSON indexes. The private writer regenerates, validates and commits indexes with
the reviewed event, restoring both if publication preparation fails.
