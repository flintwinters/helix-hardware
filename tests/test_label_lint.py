"""Regression cases for schematic component text placement."""

import copy
import unittest
from unittest.mock import Mock

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

    def test_make_preserves_existing_edits(self):
        path = Mock()
        path.exists.return_value = True
        path.read_text.return_value = 'user edit'
        with self.assertRaisesRegex(ValueError, 'would overwrite'):
            manage.write_schematic_if_unmodified(path, 'generated')
        path.write_text.assert_not_called()


if __name__ == '__main__':
    unittest.main()
