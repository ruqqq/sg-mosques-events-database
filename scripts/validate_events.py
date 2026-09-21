"""Validate public event records and deterministic cross-field constraints."""
from datetime import date
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'schemas/event.schema.json').read_text())
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def pointer_exists(document, pointer):
    current = document
    try:
        for token in pointer.split('/')[1:]:
            token = token.replace('~1', '/').replace('~0', '~')
            if isinstance(current, list):
                if not token.isdigit() or (len(token) > 1 and token.startswith('0')):
                    return False
                current = current[int(token)]
            else:
                current = current[token]
        return True
    except (KeyError, IndexError, ValueError, TypeError):
        return False


def errors(event):
    issues = [f'{e.json_path}: {e.message}' for e in VALIDATOR.iter_errors(event)]
    if issues:
        return issues
    unavailable = all(source.get('availability', {}).get('state') == 'unavailable' for source in event['sources'])
    if bool(event.get('deleted_at')) != unavailable:
        issues.append('deleted_at must be set exactly when all sources are unavailable')
    if event.get('deletion_reason') != ('all_sources_unavailable' if unavailable else None):
        issues.append('deletion_reason must match source availability')
    for source in event['sources']:
        availability = source.get('availability')
        if availability and availability['reason'] != ('repeated_dead_page' if availability['state'] == 'unavailable' else 'retrieved'):
            issues.append('source availability reason does not match state')
    schedule = event['schedule']
    try:
        ZoneInfo(schedule['timezone'])
    except (ZoneInfoNotFoundError, ValueError):
        issues.append('schedule.timezone: unknown IANA timezone')
    sources = [source['id'] for source in event['sources']]
    if len(set(sources)) != len(sources):
        issues.append('sources: duplicate source IDs')
    for proof in event['evidence'] + event.get('status_evidence', []):
        if proof['source_id'] not in sources:
            issues.append('evidence: unknown source_id ' + proof['source_id'])
        for pointer in proof.get('supports', []):
            if not pointer_exists(event, pointer):
                issues.append('evidence: missing field ' + pointer)
    seen = set()
    for occurrence in schedule['occurrences']:
        start = date.fromisoformat(occurrence['date'])
        end = date.fromisoformat(occurrence['end_date'] or occurrence['date'])
        if end < start:
            issues.append('schedule: end_date precedes date')
        start_time, end_time = occurrence['start_time'], occurrence['end_time']
        if start == end and start_time and end_time and start_time['kind'] == end_time['kind'] == 'clock':
            if end_time['local_time'] <= start_time['local_time']:
                issues.append('schedule: clock end must follow start; supply end_date for overnight events')
        identity = (occurrence['date'], json.dumps(start_time, sort_keys=True), occurrence.get('label'))
        if identity in seen:
            issues.append('schedule: duplicate occurrence')
        seen.add(identity)
    recurrence = schedule['recurrence']
    if recurrence and recurrence['starts_on'] and recurrence['ends_on'] and recurrence['ends_on'] < recurrence['starts_on']:
        issues.append('recurrence: ends_on precedes starts_on')
    pricing = event.get('pricing', {})
    if pricing.get('kind') == 'free' and any(p['amount'] != 0 for p in pricing['prices']):
        issues.append('pricing: free event cannot have positive prices')
    return issues


def validate(event):
    issues = errors(event)
    if issues:
        raise ValueError('\n'.join(issues))


def main(paths):
    failures, ids = [], set()
    for path in paths:
        event = json.loads(path.read_text())
        failures.extend(f'{path}: {issue}' for issue in errors(event))
        if event.get('id') in ids:
            failures.append(f'{path}: duplicate event ID')
        ids.add(event.get('id'))
    if failures:
        print('\n'.join(failures), file=sys.stderr)
        return 1
    print(f'Validated {len(paths)} event records')
    return 0


if __name__ == '__main__':
    paths = [Path(arg) for arg in sys.argv[1:]] if len(sys.argv) > 1 else sorted((ROOT / 'events').glob('*.json'))
    if not paths:
        raise SystemExit('No event records found')
    raise SystemExit(main(paths))
