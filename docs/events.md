# Event data model, version 1.0

The [JSON Schema](../schemas/event.schema.json) defines one independently identifiable
event or recurring series. [Records](../events/) contain source-backed candidates
from Sultan, An-Nahdhah, Al-Firdaus, Assyafaah and An-Nur. This is not a
comprehensive calendar.

## Core fields

| Field | Meaning |
| --- | --- |
| `schema_version` | Data contract version (`1.0`) |
| `id` | UUID allocated once and retained through reminders, corrections and cancellations |
| `title`, `description`, `categories` | Normalized event facts; do not copy a whole promotional caption |
| `mosque_ids` | Associated mosque identifiers; can contain more than one mosque |
| `status` | `scheduled`, `cancelled`, `postponed`, `completed`, or `unknown` |
| `schedule` | One-off, explicit multiple sessions, recurring series, or unresolved schedule |
| `location` | Physical/online/hybrid mode, venue, address, and online URL where known |
| `people`, `languages`, `audience` | Named contributors, BCP-47 language tags, audience labels |
| `registration` | Requirement, URL, deadline date and instructions |
| `pricing` | Free/paid/donation/unknown, named prices and currency |
| `sources` | Multiple source posts, actual author IDs/handles, publication and retrieval timestamps |
| `evidence` | Source IDs and caption/slide locators supporting specific fields |
| `review` | Candidate/reviewed state and explicit unresolved questions |
| **`notes`** | **Free-form text for contextual details** |
| **`extra_data`** | **An open JSON object for any other source-backed data** |

Unknown is not false: `null`, `unknown` or an empty list means the source did not
establish a fact. Absence of a stated fee does not mean free. A general mosque
donation appeal does not mean donation-priced admission. An event date in the
past does not by itself prove completion. `completed`, `cancelled` and
`postponed` require a source citation and explicit evidence excerpt.

All core objects reject misspelled or unknown fields. Only `extra_data` accepts
arbitrary keys and nested JSON. A new field can be promoted into the schema when
it proves common enough to filter, display, or reconcile consistently. Extras
must not override core fields or contain raw media, secrets, or full captions.

For example, the real lunch record includes:

```json
{
  "notes": "Lunch and a closed-door question-and-answer session; no age limits stated.",
  "extra_data": {
    "facilities": ["air-conditioned room"],
    "session_format": "closed-door Q&A"
  }
}
```

Other examples preserve a book title, historical schedule wording, an adhan time
distinct from the event start, English subtitle availability, and a livestream
channel without inventing its URL.

## Dates and times

`schedule.timezone` is an IANA timezone, normally `Asia/Singapore`. Dates are
local calendar dates (`YYYY-MM-DD`); clock times are local `HH:MM`. Source
timestamps remain full timestamps with an offset. Publication time is never an
event time.

- `one_off`: one occurrence with a date; start/end times may be unknown.
- `multi_session`: two or more explicitly listed occurrences. An-Nahdhah's
  Hadith class lists 18 September, 2 October and 16 October; this is not silently
  turned into an indefinite fortnightly recurrence.
- `recurring`: a recurrence object with frequency, weekdays, literal rule,
  optional date bounds, times, and explicit excluded dates. Sultan's “2nd & 4th
  Week of the Month” remains literal; it is not assumed to mean the second and
  fourth Wednesday. No occurrence-expansion engine is implemented yet.
- `unspecified`: preserve `schedule.text`, leave the normalized schedule empty,
  and explain the uncertainty.

A time is `null` or one of:

```json
{"kind": "clock", "local_time": "18:15", "literal": "6.15 PM"}
```

```json
{"kind": "prayer_relative", "prayer": "jumuah", "relation": "after", "offset_minutes": null, "literal": "After Jumaat Prayers!"}
```

```json
{"kind": "unspecified", "literal": "Kuliah Subuh"}
```

`offset_minutes` is nonnegative and interpreted with `before`/`after`/`at`.
“After Maghrib” has no numeric offset; “30 minutes before Zuhr” has offset 30.
“Kuliah Subuh” does not say before or after, so it stays unspecified. A separate
`end_date` handles overnight or multi-day occurrences. Optional `label` preserves
explicit session names such as “Session 1” and “Session 2” when both happen on
the same date but clock times are unknown. Session labels are not clock times.
Duplicate date/start-time/label combinations are rejected.

## Evidence and reconciliation

Instagram post identity and event identity are separate. One carousel can
describe many events; several posts can describe one event. Preserve the actual
author separately from `discovered_via`: both new accounts returned a
partner-authored post in their discovery results.

Evidence `supports` values are JSON Pointers such as `/schedule/occurrences/0/date`.
Locators such as `caption` and `slide:1` identify inspectable source material.
Source IDs must exist and pointers must resolve. Schema validity checks structure,
not whether a quoted claim is true. Candidate records are machine-extracted;
publication does not imply human verification.

The collection worker maintains event identity separately from post identity.
Reviewed source links preserve the original event ID and retain all earlier
source evidence. The unattended worker publishes valid new events and unambiguous
updates automatically. Conflicting or ambiguous changes are skipped, preserving
existing facts, without a required review queue. Collection outages never delete
or cancel a record.

## Run validation

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/validate_all.py
```

The validator checks JSON Schema, actual calendar dates, IANA timezones, clock
ordering, duplicate event/source identities, and evidence references. Cancellation
and completion evidence is structurally required. Unresolved recurrence wording
is retained literally; the validator does not prove real-world source truth.

## File layout and listings

Canonical records use `events/<event-id>.json`. Generated month and mosque
listings support direct JSON access; see [the access guide](access.md).

## Source availability and soft deletion

Optional `sources[].availability` records operational `available`/`unavailable`
state, transition time (`since`) and reason (`retrieved`/`repeated_dead_page`).
Optional `deleted_at` and `deletion_reason` describe an event's reversible soft
deletion. Validation requires deletion exactly when all source states are
unavailable. Event `status` remains independent. See [the access guide](access.md#soft-deletion-and-restoration)
for listing behavior and the automatic failure/restoration policy.
