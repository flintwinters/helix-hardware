"""The route selector must prefer shorter complete nets quadratically."""

import unittest

import manage


class BoardText:
    def __init__(self, text):
        self.text = text

    def read_text(self):
        return self.text


def segment(net, x2, y2=0, layer='F.Cu'):
    return (f'(segment (start 0 0) (end {x2} {y2}) '
            f'(layer "{layer}") (net "{net}"))')


class RouteScoreTest(unittest.TestCase):
    def test_long_net_cost_grows_quadratically(self):
        short = BoardText('(pcb ' + segment('/A', 10) + ')')
        long = BoardText('(pcb ' + segment('/A', 20) + ')')
        self.assertEqual(manage.route_score(long), 4 * manage.route_score(short))

    def test_off_axis_and_manual_usb(self):
        horizontal = BoardText('(pcb ' + segment('/A', 10) + ')')
        vertical = BoardText('(pcb ' + segment('/A', 0, 10) + ')')
        with_usb = BoardText('(pcb ' + segment('/A', 10) + segment('/USB_DP', 100) + ')')
        self.assertGreater(manage.route_score(vertical), manage.route_score(horizontal))
        self.assertEqual(manage.route_score(with_usb), manage.route_score(horizontal))
