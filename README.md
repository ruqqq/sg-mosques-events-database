# Singapore mosque events database

Public, versioned facts and source references for Singapore mosque events.
This pilot covers **Sultan, An-Nahdhah, Al-Firdaus, Assyafaah and An-Nur**. It is not a complete
Singapore mosque directory or a guarantee that every event is captured.

- `mosques/`: mosque identities and multiple social sources with confidence/evidence.
- `events/<event-id>.json`: canonical candidate events/series at stable UUID paths.
- `indexes/`: generated listings by month and mosque, plus recurring and undated events.
- `schemas/`: versioned JSON Schema contracts.
- `docs/events.md`: field semantics, time handling and provenance.
- `scripts/`: public data validation used by CI and the private worker.

Events retain stable IDs across reminders and corrections. Their source post IDs
are separate. `notes` is free-form text; `extra_data` holds other source-backed
JSON facts. Prayer-relative times remain literal. Collection outages do not
cancel events. Repeated, explicit source unavailability can soft-delete listings;
canonical records are retained and automatically restored when a source returns.

`review.state` distinguishes candidates from reviewed records. Unknown facts stay
null/unknown. Completion requires evidence; age alone is insufficient. Unresolved
recurrence rules must not be expanded into guessed dates.

Collection, model prompts, diagnostics, credentials, raw media and runtime state
are maintained separately by a private worker. This repository contains no crawler
or unattended AI runtime.

## Fetch directly

Start with [indexes/manifest.json](indexes/manifest.json) to discover available
months and mosque listings. Each listing contains display-ready summaries and
paths to full event records. See [the JSON access guide](docs/access.md) for fetch
examples, recurrence handling and consistent reads across files.

## Validate

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/validate_all.py
```

CI validates pushes and pull requests. These schemas are the canonical contracts
used by the worker; consumers should check `schema_version`.
See [event documentation](docs/events.md) and [event schema](schemas/event.schema.json).
