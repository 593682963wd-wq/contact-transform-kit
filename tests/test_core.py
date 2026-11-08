"""作者：Wangyuan；日期：2026-10-29；职责：合成号码、名单歧义与纯文本模板回归。"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from core import run
from phone import NumberPolicy, normalize
from roster import compare, compare_groups, classify
from templates import build_plan, select_devices, render_template, verify_targets

NUMBER = '2025550101'
POLICY = NumberPolicy([10], country_code='1', international_prefix='00', trunk_prefix='0')


class NumberTests(unittest.TestCase):
    def test_international_separators_trunk(self):
        for text in ['+1 (202) 555-0101', '001 202-555-0101', '0' + NUMBER, NUMBER]:
            self.assertEqual(normalize(text, POLICY)['national'], NUMBER)
        self.assertTrue(normalize('0' + NUMBER, POLICY)['trunk_removed'])
        self.assertFalse(normalize(NUMBER, POLICY)['country_removed'])

    def test_no_implicit_country_or_region(self):
        result = normalize('+1 ' + NUMBER, NumberPolicy([10]))
        self.assertFalse(result['valid'])
        self.assertEqual(result['reason'], 'country_code_mismatch')
        self.assertNotIn('region', normalize('0' + NUMBER, POLICY))
        bare = NumberPolicy([10], country_code='1', allow_bare_country_code=True)
        self.assertEqual(normalize('1' + NUMBER, bare)['national'], NUMBER)
        self.assertFalse(normalize('1' + NUMBER, POLICY)['valid'])

    def test_invalid_inputs_not_silently_digit_stripped(self):
        for value in [None, '', 'call ' + NUMBER, NUMBER + ' ext 2', NUMBER + '/' + NUMBER, '202)5550101', '20+25550101']:
            self.assertFalse(normalize(value, POLICY)['valid'])
        with self.assertRaises(TypeError):
            normalize(int(NUMBER), POLICY)
        with self.assertRaises(ValueError):
            NumberPolicy([True])
        with self.assertRaises(ValueError):
            NumberPolicy([10], international_prefix='00')

    def test_explicit_lengths_and_prefixes(self):
        policy = NumberPolicy([4], national_prefixes=['7'])
        self.assertTrue(normalize('7-123', policy)['valid'])
        self.assertFalse(normalize('8-123', policy)['valid'])
        self.assertFalse(normalize('7-1234', policy)['valid'])
        self.assertEqual(run({'action': 'normalize', 'policy': {'national_lengths': [4]}, 'numbers': ['1234', 'bad']})['invalid_count'], 1)


class RosterTests(unittest.TestCase):
    def test_difference_and_parenthetical_option(self):
        result = compare(['Synthetic A (team)', 'Synthetic B'], ['Synthetic A', 'Synthetic C'])
        self.assertEqual(result['matched'][0]['key'], 'Synthetic A')
        self.assertEqual(result['only_left'], ['Synthetic B'])
        self.assertEqual(result['only_right'], ['Synthetic C'])
        self.assertFalse(compare(['Synthetic A (team)'], ['Synthetic A'], False)['matched'])

    def test_ambiguous_normalized_names_not_overwritten(self):
        result = compare(['Synthetic A (one)', 'Synthetic A (two)'], ['Synthetic A'])
        self.assertEqual(result['matched'], [])
        self.assertEqual(len(result['ambiguous'][0]['left']), 2)
        with self.assertRaises(ValueError):
            compare(['(empty)'], [])

    def test_groups_multiple_membership_and_non_mutation(self):
        people = [{'name': 'Synthetic A', 'groups': ['old']}, {'name': 'Synthetic B'}, {'name': 'Synthetic C'}]
        original = deepcopy(people)
        groups = {'one': 'Synthetic A, Synthetic B', 'two': ['Synthetic A', 'Synthetic D']}
        result = classify(people, groups)
        self.assertEqual(people, original)
        self.assertEqual(result['people'][0]['groups'], ['one', 'two'])
        self.assertEqual(result['people'][2]['groups'], [])
        self.assertEqual(result['comparison']['per_group']['two']['missing_in_table'], ['Synthetic D'])
        self.assertEqual(result['comparison']['extra_in_table'], ['Synthetic C'])

    def test_group_duplicates_block_automatic_classification(self):
        result = compare_groups([{'name': 'Synthetic A'}], {'one': ['Synthetic A', 'Synthetic A (tag)']})
        self.assertTrue(result['classified'][0]['ambiguous'])
        self.assertEqual(result['classified'][0]['groups'], [])
        self.assertEqual(result['per_group']['one']['count'], 1)


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.devices = [{'key': 'a', 'type': 'demo'}, {'key': 'b', 'type': 'demo'}]
        self.templates = {'demo': {'variants': {'plain': {'template': 'DEMO {target}'},
                                              'prefixed': {'template': 'DEMO {target}', 'target_prefix': '0'}},
                                   'cancel_template': 'CLEAR {device_key}'}}

    def test_preview_unknown_and_confirmed_variants(self):
        result = build_plan({'number': NUMBER}, self.devices, self.templates, POLICY)
        self.assertEqual(len(result['plan'][0]['instructions']), 3)
        self.assertTrue(result['plan'][0]['requires_variant_confirmation'])
        self.assertFalse(result['sent'])
        known = build_plan({'number': NUMBER, 'variant_confirmed': True, 'variant': 'plain'}, self.devices, self.templates, POLICY)
        self.assertEqual(len(known['plan'][0]['instructions']), 2)
        with self.assertRaises(ValueError):
            build_plan({'number': NUMBER, 'variant_confirmed': True, 'variant': 'unknown'}, self.devices, self.templates, POLICY)

    def test_selection_order_unknown_and_duplicates(self):
        self.assertEqual([d['key'] for d in select_devices(self.devices, ['b', 'a'])], ['b', 'a'])
        for keys in [['x'], ['a', 'a']]:
            with self.assertRaises(ValueError):
                select_devices(self.devices, keys)
        with self.assertRaises(ValueError):
            select_devices(self.devices + [self.devices[0]], ['a'])

    def test_template_field_traversal_and_missing_target(self):
        for text in ['{target.__class__}', '{target[0]}', '{target!r}', '{target:>20}', 'literal', '{target}{target}']:
            with self.assertRaises(ValueError):
                render_template(text, {'target': NUMBER}, require_target=True)

    def test_structured_target_check_rejects_changed_destination(self):
        plan = build_plan({'number': NUMBER}, self.devices, self.templates, POLICY)['plan']
        self.assertTrue(verify_targets(plan, NUMBER, ['', '0'])['ok'])
        plan[0]['instructions'][0]['text'] = 'DEMO 2025550199'
        self.assertFalse(verify_targets(plan, NUMBER, ['', '0'])['ok'])
        self.assertFalse(verify_targets(plan, NUMBER, ['', '0'])['template_semantics_verified'])


class CliTests(unittest.TestCase):
    def test_example_no_overwrite_and_missing_policy(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'result.json'
            command = [sys.executable, '-B', str(root / 'cli.py'), str(root / 'example.json'), '--output', str(output)]
            done = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            content = output.read_bytes()
            self.assertEqual(json.loads(content)['state'], 'preview_only')
            again = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(again.returncode, 2)
            self.assertEqual(output.read_bytes(), content)
            bad = Path(temp) / 'bad.json'
            bad.write_text('{"action":"normalize","numbers":[]}')
            failed = subprocess.run([sys.executable, '-B', str(root / 'cli.py'), str(bad)], capture_output=True, text=True)
            self.assertEqual(failed.returncode, 2)
            self.assertNotIn('Traceback', failed.stderr)
            self.assertEqual(failed.stdout, '')


if __name__ == '__main__':
    unittest.main()
