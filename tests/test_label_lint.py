"""Regression cases for schematic component text placement."""

import copy
import unittest

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


if __name__ == '__main__':
    unittest.main()
