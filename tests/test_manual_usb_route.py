"""The autorouter must leave manually drawn USB data copper intact."""

import copy
import unittest

import manage


class ManualUsbRouteTest(unittest.TestCase):
    def setUp(self):
        self.board = manage.parse('''(kicad_pcb
            (segment (start 1 2) (end 3 4) (width 0.15) (layer "F.Cu")
                     (net "/USB_DP") (uuid "dp"))
            (segment (start 5 6) (end 7 8) (width 0.15) (layer "B.Cu")
                     (net "/USB_DM") (uuid "dm"))
            (via (at 7 8) (size 0.4) (drill 0.2) (layers "F.Cu" "B.Cu")
                 (net "/USB_DM") (uuid "dm-via"))
            (arc (start 3 4) (mid 3.5 4.5) (end 4 5) (width 0.15)
                 (layer "F.Cu") (net "/USB_DP") (uuid "dp-arc"))
            (segment (start 9 10) (end 11 12) (width 0.3) (layer "F.Cu")
                     (net "/SPI_SCK") (uuid "sck")))''')

    def test_manual_tracks_and_vias_survive_route_preparation(self):
        clean, protected = manage.prepare_route_input(self.board)
        self.assertEqual(set(protected), {'dp', 'dm', 'dm-via', 'dp-arc'})
        self.assertEqual(manage.copper_snapshot(clean, manage.MANUAL_ROUTE_NETS), protected)
        self.assertEqual(sum(isinstance(x, list) and x[0] in ('segment', 'arc', 'via') for x in clean), 4)

    def test_missing_manual_net_blocks_autorouter(self):
        board = copy.deepcopy(self.board)
        board = [x for x in board if not (isinstance(x, list) and x[0] in ('segment', 'arc')
                                           and manage.child(x, 'net')[1] == '"/USB_DP"')]
        with self.assertRaisesRegex(ValueError, 'Route /USB_DP and /USB_DM manually'):
            manage.prepare_route_input(board)

    def test_modified_manual_geometry_blocks_candidate(self):
        _, protected = manage.prepare_route_input(self.board)
        board = copy.deepcopy(self.board)
        segment = next(x for x in board if isinstance(x, list) and x[0] == 'segment'
                       and manage.child(x, 'net')[1] == '"/USB_DP"')
        manage.child(segment, 'end')[1] = '3.5'
        with self.assertRaisesRegex(ValueError, 'changed manually routed USB'):
            manage.require_manual_copper_preserved(board, protected)


if __name__ == '__main__':
    unittest.main()
