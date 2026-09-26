"""Keep the sourced WIZ850io pin pattern and module nets aligned."""

import json
import unittest

import manage


class Wiz850ioTest(unittest.TestCase):
    def test_footprint_geometry_and_pin_order(self):
        footprint = manage.parse((manage.ROOT / 'footprints/Helix.pretty/WIZ850io.kicad_mod').read_text())
        pads = {json.loads(pad[1]): pad for pad in footprint
                if isinstance(pad, list) and pad[0] == 'pad'}
        self.assertEqual(set(pads), {str(n) for n in range(1, 13)})
        for number in range(1, 7):
            left = manage.child(pads[str(number)], 'at')
            right = manage.child(pads[str(13 - number)], 'at')
            self.assertEqual(tuple(map(float, left[1:3])), (-10.16, (number - 1) * 2.54))
            self.assertEqual(tuple(map(float, right[1:3])), (10.16, (number - 1) * 2.54))
        for pad in pads.values():
            self.assertEqual(manage.child(pad, 'size')[1:], ['1.7', '1.7'])
            self.assertEqual(manage.child(pad, 'drill')[1:], ['1'])

    def test_module_symbol_matches_mating_headers(self):
        symbol = manage.child(manage.parse(
            (manage.ROOT / 'vendor/wiz850io/WIZ850io.kicad_sym').read_text()), 'symbol')
        names = {number: name for number, (name, _) in manage.pins(symbol).items()}
        self.assertEqual(names, {'1': 'GND', '2': 'GND', '3': 'MOSI', '4': 'SCLK',
                                 '5': 'SCNn', '6': '~{INTn}', '7': 'MISO',
                                 '8': '~{RST}', '9': 'NC', '10': '3.3V',
                                 '11': '3.3V', '12': 'GND'})

    def test_board_uses_one_module_footprint(self):
        board = manage.parse((manage.ROOT / 'helix_minimal.kicad_pcb').read_text())
        modules = [part for part in board if isinstance(part, list) and part[0] == 'footprint'
                   and part[1] == '"Helix:WIZ850io"']
        self.assertEqual(len(modules), 1)
        module = modules[0]
        self.assertTrue(any(isinstance(p, list) and p[:3] == ['property', '"Reference"', '"U3"']
                            for p in module))
        pads = {json.loads(p[1]): p for p in module if isinstance(p, list) and p[0] == 'pad'}
        expected = {'1': 'GND', '2': 'GND', '3': '/SPI_MOSI', '4': '/SPI_SCK',
                    '5': '/WIZ_CS', '6': '/WIZ_INT', '7': '/SPI_MISO',
                    '8': '/WIZ_RST', '10': '+3V3', '11': '+3V3', '12': 'GND'}
        for number, net in expected.items():
            self.assertEqual(json.loads(manage.child(pads[number], 'net')[1]), net)


if __name__ == '__main__':
    unittest.main()
