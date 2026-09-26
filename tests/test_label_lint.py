"""Regression cases for schematic component text placement."""

import copy
import unittest
from unittest.mock import patch

import manage


class ComponentLabelLintTest(unittest.TestCase):
    def setUp(self):
        self.schematic = manage.parse((manage.ROOT / 'helix_minimal.kicad_sch').read_text())

    def test_current_schematic(self):
        manage.lint_component_labels(self.schematic)

    def test_displaced_reference_is_rejected(self):
        schematic = copy.deepcopy(self.schematic)
        resistor = next(part for part in schematic if isinstance(part, list)
                        and part[0] == 'symbol'
                        and any(isinstance(p, list) and p[:3] == ['property', '"Reference"', '"R1"']
                                for p in part))
        reference = next(p for p in resistor if isinstance(p, list)
                         and p[:2] == ['property', '"Reference"'])
        manage.child(reference, 'at')[1] = '500'
        with self.assertRaisesRegex(ValueError, 'R1 Reference is too far'):
            manage.lint_component_labels(schematic)

    def test_kicad_hidden_reference_is_ignored(self):
        symbol = next(part for part in self.schematic if isinstance(part, list)
                      and part[0] == 'symbol'
                      and manage.child(part, 'lib_id')[1] == '"power:GND"')
        reference = next(p for p in symbol if isinstance(p, list)
                         and p[:2] == ['property', '"Reference"'])
        manage.child(reference, 'at')[1] = '500'
        manage.lint_component_labels(self.schematic)

    def test_repair_changes_only_misplaced_field(self):
        source = (manage.ROOT / 'helix_minimal.kicad_sch').read_text()
        part = next(p for p in self.schematic if isinstance(p, list) and p[0] == 'symbol'
                    and any(isinstance(field, list) and field[:3] == ['property', '"Reference"', '"R1"']
                            for field in p))
        old_at = manage.emit(manage.child(next(field for field in part if isinstance(field, list)
                                               and field[:2] == ['property', '"Reference"']), 'at'))
        old_field = '"Reference" "R1" ' + old_at
        displaced = source.replace(old_field, '"Reference" "R1" (at 500 500 0)', 1)
        self.assertNotEqual(source, displaced)
        repaired, changes = manage.repair_component_labels(displaced)
        self.assertEqual(changes, [('R1', 'Reference')])
        self.assertEqual(repaired, source)

    def test_repair_is_noop_on_valid_schematic(self):
        source = (manage.ROOT / 'helix_minimal.kicad_sch').read_text()
        self.assertEqual(manage.repair_component_labels(source), (source, []))

    def test_build_refuses_existing_schematic(self):
        with patch.object(manage, 'ROOT', manage.ROOT):
            with self.assertRaisesRegex(SystemExit, 'existing schematic preserved'):
                manage.build()


if __name__ == '__main__':
    unittest.main()
