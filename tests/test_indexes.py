from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_indexes import build, sync


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in ('events', 'mosques'):
            shutil.copytree(ROOT / folder, self.root / folder)

    def rows(self, output, path):
        return json.loads(output['indexes/' + path])['events']

    def test_multisession_and_ambiguous_recurrence(self):
        output = build(self.root)
        ident = '839afd2b-73c4-4124-8a32-9ed71026ec7f'
        sept = next(e for e in self.rows(output, 'months/2026-09.json') if e['id'] == ident)
        octo = next(e for e in self.rows(output, 'months/2026-10.json') if e['id'] == ident)
        self.assertEqual(len(sept['matched_occurrences']), 1)
        self.assertEqual(len(octo['matched_occurrences']), 2)
        self.assertEqual(sept['path'], octo['path'])
        recurring = self.rows(output, 'mosques/sultan/recurring.json')
        self.assertEqual(len(recurring), 1)
        self.assertFalse(any(e['id'] == recurring[0]['id'] for e in self.rows(output, 'months/2026-09.json')))

    def test_cross_year_span_joint_mosques_and_status_preserved(self):
        path = next((self.root / 'events').glob('*.json'))
        event = json.loads(path.read_text())
        event['mosque_ids'] = ['sultan', 'an-nahdhah']
        event['status'] = 'cancelled'
        event['schedule']['kind'] = 'one_off'
        event['schedule']['occurrences'] = [{'date': '2026-12-31', 'end_date': '2027-01-02', 'start_time': None, 'end_time': None}]
        path.write_text(json.dumps(event))
        output = build(self.root)
        for month in ('2026-12', '2027-01'):
            for scope in ('', 'mosques/sultan/', 'mosques/an-nahdhah/'):
                row = next(e for e in self.rows(output, scope + 'months/' + month + '.json') if e['id'] == event['id'])
                self.assertEqual(row['status'], 'cancelled')

    def test_correction_removes_obsolete_buckets_and_detects_stale_output(self):
        sync(self.root)
        before = build(self.root)
        sync(self.root)
        self.assertEqual(before, build(self.root))
        for path in (self.root / 'events').glob('*.json'):
            event = json.loads(path.read_text())
            event['schedule'].update(kind='unspecified', occurrences=[], recurrence=None)
            path.write_text(json.dumps(event))
        with self.assertRaisesRegex(ValueError, 'stale'):
            sync(self.root, check=True)
        sync(self.root)
        sync(self.root, check=True)
        self.assertFalse(list((self.root / 'indexes/months').glob('*.json')))
        self.assertEqual(len(self.rows(build(self.root), 'undated.json')), 7)

    def test_every_manifest_and_event_link_resolves(self):
        output = build(self.root)
        manifest = json.loads(output['indexes/manifest.json'])
        for scope in [manifest, *manifest['mosques'].values()]:
            for descriptor in [*scope['months'].values(), scope['recurring'], scope['undated']]:
                rows = json.loads(output[descriptor['path']])['events']
                self.assertEqual(len(rows), descriptor['count'])
                for row in rows:
                    self.assertEqual(json.loads((self.root / row['path']).read_text())['id'], row['id'])

    def test_soft_deleted_event_is_retained_but_only_in_tombstones(self):
        path = self.root/'events/839afd2b-73c4-4124-8a32-9ed71026ec7f.json'
        event = json.loads(path.read_text())
        event['deleted_at'] = '2026-09-24T17:00:00+00:00'
        event['deletion_reason'] = 'all_sources_unavailable'
        for source in event['sources']:
            source['availability'] = {'state':'unavailable','since':event['deleted_at'],'reason':'repeated_dead_page'}
        path.write_text(json.dumps(event))
        from validate_events import errors
        self.assertEqual(errors(event), [])
        output = build(self.root)
        self.assertTrue(path.exists())
        self.assertIn(event['id'], [r['id'] for r in self.rows(output,'deleted.json')])
        for name, payload in output.items():
            if name not in ('indexes/deleted.json', 'indexes/manifest.json'):
                self.assertNotIn(event['id'], [r['id'] for r in json.loads(payload)['events']])
        event['deleted_at'] = None
        self.assertTrue(errors(event))
