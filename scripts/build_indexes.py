"""Build deterministic static JSON read models from canonical records."""
import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('id', 'title', 'description', 'mosque_ids', 'categories', 'status',
          'schedule', 'location', 'people', 'languages', 'audience',
          'registration', 'pricing', 'review')


def months_between(start, end):
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    cursor = start.year * 12 + start.month - 1
    stop = end.year * 12 + end.month - 1
    while cursor <= stop:
        year, month = divmod(cursor, 12)
        yield f'{year:04d}-{month + 1:02d}'
        cursor += 1


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def build(root=ROOT):
    root = Path(root)
    mosques = {p.stem: json.loads(p.read_text()) for p in sorted((root / 'mosques').glob('*.json'))}
    buckets = defaultdict(list)
    for path in sorted((root / 'events').glob('*.json')):
        event = json.loads(path.read_text())
        summary = {key: event[key] for key in FIELDS}
        summary['path'] = path.relative_to(root).as_posix()
        matched = defaultdict(list)
        for occurrence in event['schedule']['occurrences']:
            for month in months_between(occurrence['date'], occurrence['end_date'] or occurrence['date']):
                matched[month].append(occurrence)
        scopes = [''] + [f'mosques/{ident}/' for ident in sorted(set(event['mosque_ids']))]
        for scope in scopes:
            for month, occurrences in matched.items():
                buckets[f'{scope}months/{month}.json'].append(dict(summary, matched_occurrences=occurrences))
            if event['schedule']['kind'] == 'recurring':
                buckets[f'{scope}recurring.json'].append(summary)
            elif not matched:
                buckets[f'{scope}undated.json'].append(summary)
    # Always expose empty special collections, including for mosques with no events.
    for scope in [''] + [f'mosques/{ident}/' for ident in mosques]:
        for name in ('recurring', 'undated'):
            buckets[f'{scope}{name}.json']
    output = {}
    for path, rows in sorted(buckets.items()):
        rows.sort(key=lambda row: (row.get('matched_occurrences', [{}])[0].get('date', ''), row['id']))
        output['indexes/' + path] = encode({'schema_version': '1.0', 'events': rows})
    def descriptor(path):
        return {'path': 'indexes/' + path, 'count': len(buckets[path])}
    def catalog(scope):
        prefix = scope + 'months/'
        return {
            'months': {path[len(prefix):-5]: descriptor(path) for path in sorted(buckets) if path.startswith(prefix)},
            'recurring': descriptor(scope + 'recurring.json'),
            'undated': descriptor(scope + 'undated.json'),
        }
    manifest = {'schema_version': '1.0', 'timezone': 'Asia/Singapore', **catalog(''), 'mosques': {}}
    for ident, mosque in mosques.items():
        manifest['mosques'][ident] = {'path': f'mosques/{ident}.json', **catalog(f'mosques/{ident}/')}
    output['indexes/manifest.json'] = encode(manifest)
    return output


def sync(root=ROOT, check=False):
    root = Path(root)
    expected = build(root)
    actual = {p.relative_to(root).as_posix(): p.read_text() for p in (root / 'indexes').rglob('*.json')}
    if check:
        if expected != actual:
            raise ValueError('Indexes missing or stale; run python scripts/build_indexes.py')
        return
    for name in actual.keys() - expected.keys():
        (root / name).unlink()
    for name, payload in expected.items():
        if actual.get(name) != payload:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    sync(check=args.check)
