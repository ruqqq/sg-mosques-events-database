"""Validate schemas, source registry and event references in the public database."""
import json
from pathlib import Path
import sys
from jsonschema import Draft202012Validator, FormatChecker
from validate_events import main as validate_events
from build_indexes import sync

ROOT = Path(__file__).resolve().parents[1]


def main():
    for path in (ROOT / 'schemas').glob('*.json'):
        Draft202012Validator.check_schema(json.loads(path.read_text()))
    validator = Draft202012Validator(json.loads((ROOT / 'schemas/mosque.schema.json').read_text()), format_checker=FormatChecker())
    known = set()
    for path in sorted((ROOT / 'mosques').glob('*.json')):
        record = json.loads(path.read_text())
        validator.validate(record)
        if path.stem != record['id'] or record['id'] in known:
            raise ValueError(f'Invalid or duplicate mosque filename: {path.name}')
        logo = ROOT / record['logo']['path']
        if not logo.is_file():
            raise ValueError(f'Missing mosque logo: {record["logo"]["path"]}')
        known.add(record['id'])
    if not known:
        raise ValueError('Empty mosque registry')
    paths = sorted((ROOT / 'events').glob('*.json'))
    for path in paths:
        event = json.loads(path.read_text())
        if path.stem != event['id']:
            raise ValueError(f'Event filename must match its stable ID: {path.name}')
        if set(event['mosque_ids']) - known:
            raise ValueError(f'Unknown mosque reference: {path.name}')
    result = validate_events(paths)
    if result == 0:
        sync(ROOT, check=True)
    print(f'Validated {len(known)} mosque records and generated indexes')
    return result


if __name__ == '__main__':
    sys.exit(main())
