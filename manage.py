#!/usr/bin/env python3
"""Check or surgically repair a KiCad schematic; build a new one separately."""

from pathlib import Path
import json
import math
import os
import re
import shutil
import subprocess
import unittest
import uuid

ROOT = Path(__file__).resolve().parent
FALLBACK = Path('/home/iron/projects/headgames/electrode/.kicad-appimage/AppDir/usr')
LIB = next((p for p in (Path(os.environ.get('KICAD_SYMBOL_DIR', '/usr/share/kicad/symbols')),
                         FALLBACK / 'share/kicad/symbols') if p.is_dir()), None)
CLI = shutil.which('kicad-cli') or str(FALLBACK / 'bin/kicad-cli')


def parse(source):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', source)
    stack = []
    for token in tokens:
        if token == '(':
            item = []
            if stack:
                stack[-1].append(item)
            stack.append(item)
        elif token == ')':
            result = stack.pop()
        else:
            stack[-1].append(token)
    return result


def emit(tree):
    return '(' + ' '.join(emit(x) if isinstance(x, list) else x for x in tree) + ')'


def child(tree, key):
    return next(x for x in tree if isinstance(x, list) and x[0] == key)


def quote(value):
    return json.dumps(str(value), ensure_ascii=False)


def uid(key):
    return quote(uuid.uuid5(uuid.NAMESPACE_URL, 'helix-minimal/' + key))


def symbol(group, name):
    if (group, name) == ('WIZ850io', 'WIZ850io'):
        node = child(parse((ROOT / 'vendor/wiz850io/WIZ850io.kicad_sym').read_text()), 'symbol')
        node[1] = quote(f'{group}:{name}')
        return node
    if (group, name) == ('Helix', 'STM32C071FBPx'):
        node = child(parse((ROOT / 'symbols' / 'STM32C071FBPx.kicad_sym').read_text()), 'symbol')
        node[1] = quote(f'{group}:{name}')
        return node
    if LIB is None:
        raise SystemExit('KiCad symbol library missing; set KICAD_SYMBOL_DIR')
    source_group = 'Regulator_Linear' if group == 'Helix' else group
    path = LIB / f'{source_group}.kicad_symdir' / f'{name}.kicad_sym'
    node = child(parse(path.read_text()), 'symbol')
    parent = next((x for x in node if isinstance(x, list) and x[0] == 'extends'), None)
    if parent:
        base_name = json.loads(parent[1])
        base = symbol(source_group, base_name)
        node.remove(parent)
        for part in base:
            if isinstance(part, list) and part[0] == 'symbol':
                part[1] = part[1].replace(base_name + '_', name + '_')
                node.append(part)
    node[1] = quote(f'{group}:{name}')
    return node


def pins(node):
    result = {}
    for unit in (x for x in node if isinstance(x, list) and x[0] == 'symbol'):
        for pin in (x for x in unit if isinstance(x, list) and x[0] == 'pin'):
            number = json.loads(child(pin, 'number')[1])
            result[number] = (json.loads(child(pin, 'name')[1]), child(pin, 'at')[1:])
    return result


def lint_component_labels(schematic):
    """Keep visible component text within one grid margin of its symbol pins."""
    library = {json.loads(node[1]): node for node in child(schematic, 'lib_symbols')[1:]
               if isinstance(node, list) and node[0] == 'symbol'}
    problems = []
    for part in (node for node in schematic if isinstance(node, list) and node[0] == 'symbol'):
        lib_id = json.loads(child(part, 'lib_id')[1])
        x, y = map(float, child(part, 'at')[1:3])
        pin_positions = [position for _, position in pins(library[lib_id]).values()]
        half_width = max((abs(float(p[0])) for p in pin_positions), default=0)
        half_height = max((abs(float(p[1])) for p in pin_positions), default=0)
        properties = {json.loads(p[1]): p for p in part
                      if isinstance(p, list) and p[0] == 'property'}
        ref = json.loads(properties['Reference'][2])
        for name in ('Reference', 'Value'):
            prop = properties[name]
            effects = child(prop, 'effects')
            if any(isinstance(item, list) and item[0] == 'hide' and item[1] == 'yes'
                   for item in prop + effects):
                continue
            px, py = map(float, child(prop, 'at')[1:3])
            outside_x = max(abs(px - x) - half_width, 0)
            outside_y = max(abs(py - y) - half_height, 0)
            if math.hypot(outside_x, outside_y) > 7.62:
                problems.append(f'{ref} {name} is too far from its symbol')
    if problems:
        raise ValueError('\n'.join(problems))


def top_level_symbols(source):
    """Yield byte spans of placed symbols, leaving all other KiCad text untouched."""
    depth = 0
    start = None
    quoted = escaped = False
    for index, char in enumerate(source):
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == '(':
            if depth == 1:
                start = index
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 1 and start is not None:
                block = source[start:index + 1]
                if re.match(r'\(symbol(?:\s|\()', block):
                    yield start, index + 1, block
                start = None


def repair_component_labels(source):
    """Move only visibly misplaced Reference/Value coordinates in placed symbols."""
    schematic = parse(source)
    library = {json.loads(node[1]): node for node in child(schematic, 'lib_symbols')[1:]
               if isinstance(node, list) and node[0] == 'symbol'}
    edits = []
    for start, end, block in top_level_symbols(source):
        part = parse(block)
        lib_id = json.loads(child(part, 'lib_id')[1])
        x, y = map(float, child(part, 'at')[1:3])
        pin_positions = [position for _, position in pins(library[lib_id]).values()]
        half_width = max((abs(float(p[0])) for p in pin_positions), default=0)
        half_height = max((abs(float(p[1])) for p in pin_positions), default=0)
        properties = {json.loads(p[1]): p for p in part
                      if isinstance(p, list) and p[0] == 'property'}
        ref = json.loads(properties['Reference'][2])
        for name, offset in (('Reference', 2.54), ('Value', 5.08)):
            prop = properties[name]
            effects = child(prop, 'effects')
            if any(isinstance(item, list) and item[:2] == ['hide', 'yes']
                   for item in prop + effects):
                continue
            px, py = map(float, child(prop, 'at')[1:3])
            if math.hypot(max(abs(px - x) - half_width, 0),
                          max(abs(py - y) - half_height, 0)) <= 7.62:
                continue
            pattern = (r'\(property\s+"' + name +
                       r'"\s+"(?:\\.|[^"\\])*"\s*\(at\s+[^()]*\)')
            match = re.search(pattern, block)
            if not match:
                raise ValueError(f'{ref} {name}: cannot locate field coordinates')
            at_match = re.search(r'\(at\s+[^()]*\)$', match.group())
            original = at_match.group()
            angle = child(prop, 'at')[3]
            replacement = f'(at {x:g} {y-half_height-offset:g} {angle})'
            edits.append((start + match.start() + at_match.start(),
                          start + match.start() + at_match.end(), replacement, ref, name))
    for first, last, replacement, _, _ in reversed(edits):
        source = source[:first] + replacement + source[last:]
    return source, [(ref, name) for _, _, _, ref, name in edits]


def repair():
    path = ROOT / 'helix_minimal.kicad_sch'
    source = path.read_text()
    fixed, changes = repair_component_labels(source)
    if changes:
        path.write_text(fixed)
    print(f'Repaired {len(changes)} component labels; other schematic text preserved')


SYMBOLS = {
    'U1': ('Helix', 'STM32C071FBPx', 'STM32C071FBP6', 207, 112),
    'J1': ('Connector', 'USB_C_Receptacle_USB2.0_16P', 'USB-C', 48, 80),
    'U2': ('Helix', 'AP2112K-3.3', 'AP2112K-3.3', 121, 75),
    'U3': ('WIZ850io', 'WIZ850io', 'WIZ850io', 249, 104),
    'J4': ('Connector_Generic', 'Conn_01x06', '3V3 microSD SPI breakout', 315, 190),
    'J5': ('Connector_Generic', 'Conn_01x05', 'SWD', 75, 190),
    '#PWR01': ('power', 'PWR_FLAG', 'PWR_FLAG', 105, 48),
    '#PWR02': ('power', 'PWR_FLAG', 'PWR_FLAG', 121, 48),
    'R1': ('Device', 'R', '5.1k', 76, 129),
    'R2': ('Device', 'R', '5.1k', 93, 129),
    'R3': ('Device', 'R', '10k', 274, 147),
    'R4': ('Device', 'R', '10k', 258, 147),
    'R5': ('Device', 'R', '10k', 242, 147),
    'C1': ('Device', 'C', '1uF', 106, 100),
    'C2': ('Device', 'C', '1uF', 140, 100),
    'C3': ('Device', 'C', '100nF', 172, 100),
}


NETS = {
    'U1': {'4': '3V3', '5': 'GND', '6': 'NRST', '7': 'WIZ_RST', '10': 'WIZ_INT',
           '11': 'WIZ_CS', '12': 'SPI_SCK', '13': 'SPI_MISO', '14': 'SPI_MOSI',
           '15': 'SD_CS', '16': 'USB_DM', '17': 'USB_DP', '18': 'SWDIO', '19': 'SWCLK'},
    'J1': {'A1': 'GND', 'A4': 'VBUS', 'A5': 'CC1', 'A6': 'USB_DP', 'A7': 'USB_DM',
           'A8': None, 'A9': 'VBUS', 'A12': 'GND', 'B1': 'GND', 'B4': 'VBUS',
           'B5': 'CC2', 'B6': 'USB_DP', 'B7': 'USB_DM', 'B8': None,
           'B9': 'VBUS', 'B12': 'GND', 'SH': 'GND'},
    'U2': {'1': 'VBUS', '2': 'GND', '3': 'VBUS', '5': '3V3'},
    # Module pads 1-6 are J1.1-6; pads 7-12 are J2.6-1 on the sourced footprint.
    'U3': {'1': 'GND', '2': 'GND', '3': 'SPI_MOSI', '4': 'SPI_SCK',
           '5': 'WIZ_CS', '6': 'WIZ_INT', '7': 'SPI_MISO', '8': 'WIZ_RST',
           '9': None, '10': '3V3', '11': '3V3', '12': 'GND'},
    'J4': {'1': 'GND', '2': '3V3', '3': 'SPI_MISO', '4': 'SPI_MOSI', '5': 'SPI_SCK', '6': 'SD_CS'},
    'J5': {'1': '3V3', '2': 'SWDIO', '3': 'SWCLK', '4': 'GND', '5': 'NRST'},
    '#PWR01': {'1': 'VBUS'}, '#PWR02': {'1': 'GND'},
    'R1': {'1': 'CC1', '2': 'GND'}, 'R2': {'1': 'CC2', '2': 'GND'},
    'R3': {'1': '3V3', '2': 'WIZ_RST'}, 'R4': {'1': '3V3', '2': 'WIZ_CS'},
    'R5': {'1': '3V3', '2': 'SD_CS'},
    'C1': {'1': 'VBUS', '2': 'GND'}, 'C2': {'1': '3V3', '2': 'GND'},
    'C3': {'1': '3V3', '2': 'GND'},
}

# STM32C071FBP6 TSSOP20 pad functions verified against ST DS14693, figure 4.
MCU_FUNCTIONS = {'4': 'VDD', '5': 'VSS', '6': 'PF2', '7': 'PA0',
                 '10': 'PA3', '11': 'PA4', '12': 'PA5', '13': 'PA6',
                 '14': 'PA7', '15': 'PA8', '16': 'PA11', '17': 'PA12',
                 '18': 'PA13', '19': 'PA14/PA15'}

FOOTPRINTS = {
    'J1': 'Connector_USB:USB_C_Receptacle_GCT_USB4110',
    'U3': 'Helix:WIZ850io',
    'J4': 'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical',
    'J5': 'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical',
}
for ref in SYMBOLS:
    if ref.startswith('R'):
        FOOTPRINTS[ref] = 'Resistor_SMD:R_0603_1608Metric'
    if ref.startswith('C'):
        FOOTPRINTS[ref] = 'Capacitor_SMD:C_0603_1608Metric'
POWER_SYMBOLS = {'GND': 'GND', '3V3': '+3V3', 'VBUS': 'VBUS'}


def build():
    if (ROOT / 'helix_minimal.kicad_sch').exists():
        raise SystemExit('Build creates a new schematic only; existing schematic preserved')
    library = {}
    for group, name, _, _, _ in SYMBOLS.values():
        library[f'{group}:{name}'] = symbol(group, name)
    for name in POWER_SYMBOLS.values():
        library[f'power:{name}'] = symbol('power', name)
    sheet_id = json.loads(uid('sheet'))
    parts = []
    labels = []
    wires = []
    power_index = 100
    for ref, (group, name, value, x, y) in SYMBOLS.items():
        x, y = round(x / 1.27) * 1.27, round(y / 1.27) * 1.27
        lib_id = f'{group}:{name}'
        node = library[lib_id]
        part_id = json.loads(uid('part/' + ref))
        pin_map = pins(node)
        unknown = set(NETS.get(ref, {})) - set(pin_map)
        if unknown:
            raise ValueError(f'{ref}: unknown symbol pins {sorted(unknown)}')
        if ref == 'U1':
            for pad, function in MCU_FUNCTIONS.items():
                if pin_map[pad][0] != function:
                    raise ValueError(f'STM32 pad {pad}: expected {function}, got {pin_map[pad][0]}')
        top = max((abs(float(position[1])) for _, position in pin_map.values()), default=0)
        properties = [f'(property "Reference" {quote(ref)} (at {x} {round(y-top-2.54, 4)} 0) (effects (font (size 1.27 1.27))))',
                      f'(property "Value" {quote(value)} (at {x} {round(y-top-5.08, 4)} 0) (effects (font (size 1.27 1.27))))']
        footprint = FOOTPRINTS.get(ref) or next((json.loads(p[2]) for p in node if isinstance(p, list) and p[0] == 'property' and p[1] == '"Footprint"'), '')
        if footprint:
            properties.append(f'(property "Footprint" {quote(footprint)} (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))')
        parts.append(f'(symbol (lib_id {quote(lib_id)}) (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {quote(part_id)}) {" ".join(properties)} (instances (project "helix_minimal" (path "/{sheet_id}" (reference {quote(ref)}) (unit 1)))))')
        seen = set()
        for number, (pin_name, (dx, dy, angle)) in pin_map.items():
            net = NETS.get(ref, {}).get(number)
            px, py = round(x + float(dx), 4), round(y - float(dy), 4)
            if net:
                if (px, py) in seen:
                    continue
                seen.add((px, py))
                radians = math.radians(float(angle))
                tx = round(px - 5.08 * math.cos(radians), 4)
                ty = round(py + 5.08 * math.sin(radians), 4)
                wires.append(f'(wire (pts (xy {px} {py}) (xy {tx} {ty})) (stroke (width 0) (type default)) (uuid {uid("wire/" + ref + "/" + number)}))')
                if net in POWER_SYMBOLS:
                    power_index += 1
                    power_name = POWER_SYMBOLS[net]
                    power_ref = f'#PWR{power_index}'
                    power_id = f'power:{power_name}'
                    parts.append(f'(symbol (lib_id {quote(power_id)}) (at {tx} {ty} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid {uid("power/" + ref + "/" + number)}) (property "Reference" {quote(power_ref)} (at {tx} {ty} 0) (effects (font (size 1.27 1.27)) (hide yes))) (property "Value" {quote(power_name)} (at {tx} {ty-2.54} 0) (effects (font (size 1.27 1.27)))) (instances (project "helix_minimal" (path "/{sheet_id}" (reference {quote(power_ref)}) (unit 1)))))')
                else:
                    justify = 'right bottom' if tx < px else 'left bottom'
                    labels.append(f'(label {quote(net)} (at {tx} {ty} 0) (effects (font (size 1.0 1.0)) (justify {justify})) (uuid {uid("label/" + ref + "/" + number)}))')
            else:
                labels.append(f'(no_connect (at {px} {py}) (uuid {uid("nc/" + ref + "/" + number)}))')
    schematic = f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid {quote(sheet_id)})
      (paper "A3") (title_block (title "Helix minimal vertical slice") (rev "0.1"))
      (lib_symbols {' '.join(emit(x) for x in library.values())})
      {' '.join(wires)} {' '.join(labels)} {' '.join(parts)})'''
    (ROOT / 'helix_minimal.kicad_sch').write_text(schematic + '\n')
    if not (ROOT / 'helix_minimal.kicad_pro').exists():
        (ROOT / 'helix_minimal.kicad_pro').write_text('{}\n')
    local_symbols = []
    for name in ('AP2112K-3.3', 'STM32C071FBPx'):
        local = symbol('Helix', name)
        local[1] = quote(name)
        local_symbols.append(emit(local))
    (ROOT / 'helix_symbols.kicad_sym').write_text(f'(kicad_symbol_lib (version 20251024) (generator "kicad_symbol_editor") {" ".join(local_symbols)})\n')
    (ROOT / 'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Helix") (type "KiCad") (uri "${KIPRJMOD}/helix_symbols.kicad_sym") (options "") (descr "Project symbols")) (lib (name "WIZ850io") (type "KiCad") (uri "${KIPRJMOD}/vendor/wiz850io/WIZ850io.kicad_sym") (options "") (descr "Imported WIZ850io module symbol")))\n')
    print(f'Wrote schematic: {len(parts)} parts, {len(labels)} pin terminations')


def check():
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), top_level_dir=str(ROOT))
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    if not result.wasSuccessful():
        raise SystemExit('Python checks failed')
    schematic = parse((ROOT / 'helix_minimal.kicad_sch').read_text())
    try:
        lint_component_labels(schematic)
    except ValueError as error:
        raise SystemExit(f'Component label lint failed:\n{error}') from error
    placed = {json.loads(child(s, 'lib_id')[1]) for s in schematic
              if isinstance(s, list) and s[0] == 'symbol'}
    expected_power = {f'power:{name}' for name in POWER_SYMBOLS.values()}
    if not expected_power <= placed:
        raise SystemExit(f'Missing power symbols: {sorted(expected_power - placed)}')
    labels = {json.loads(label[1]) for label in schematic
              if isinstance(label, list) and label[0] == 'label'}
    if {'GND', '3V3', 'VBUS'} & labels:
        raise SystemExit('Use power symbols for GND, 3V3, and VBUS')
    result = subprocess.run([str(CLI), 'sch', 'erc', '-o', str(ROOT / 'erc.txt'),
                             str(ROOT / 'helix_minimal.kicad_sch')], cwd=ROOT)
    report = (ROOT / 'erc.txt').read_text() if (ROOT / 'erc.txt').exists() else ''
    # The restored KiCad save embeds a user-edited J1 symbol; KiCad reports its
    # library mismatch even though the electrical netlist remains verifiable.
    tolerated_j1 = ("[lib_symbol_mismatch]: Symbol 'USB_C_Receptacle_USB2.0_16P' "
                    "doesn't match copy in library 'Connector'")
    clean = '** ERC messages: 0  Errors 0  Warnings 0' in report
    known_warning = ('** ERC messages: 1  Errors 0  Warnings 1' in report
                     and tolerated_j1 in report)
    if result.returncode or not (clean or known_warning):
        print(report[:5000])
        raise SystemExit('ERC failed')
    result = subprocess.run([str(CLI), 'sch', 'export', 'netlist', '-o',
                             str(ROOT / 'helix_minimal.net'), str(ROOT / 'helix_minimal.kicad_sch')],
                            cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(result.stderr)
    netlist = parse((ROOT / 'helix_minimal.net').read_text())
    actual = {}
    for net in child(netlist, 'nets')[1:]:
        net_name = json.loads(child(net, 'name')[1]).lstrip('/')
        actual[net_name] = {(json.loads(child(n, 'ref')[1]), json.loads(child(n, 'pin')[1]))
                            for n in net if isinstance(n, list) and n[0] == 'node'}
    # These physical pad assignments are the interface contract with the STM32 and both modules.
    required = {
        'SPI_SCK': {('U1', '12'), ('U3', '4'), ('J4', '5')},
        'SPI_MISO': {('U1', '13'), ('U3', '7'), ('J4', '3')},
        'SPI_MOSI': {('U1', '14'), ('U3', '3'), ('J4', '4')},
        'WIZ_CS': {('U1', '11'), ('U3', '5')},
        'WIZ_RST': {('U1', '7'), ('U3', '8'), ('R3', '2')},
        'WIZ_INT': {('U1', '10'), ('U3', '6')},
        'SD_CS': {('U1', '15'), ('J4', '6')},
        'USB_DM': {('U1', '16'), ('J1', 'A7'), ('J1', 'B7')},
        'USB_DP': {('U1', '17'), ('J1', 'A6'), ('J1', 'B6')},
        'VBUS': {('U2', '1'), ('U2', '3'), ('J1', 'A4')},
        '+3V3': {('U2', '5'), ('U1', '4'), ('U3', '10'), ('U3', '11'), ('J4', '2')},
        'GND': {('U1', '5'), ('U3', '1'), ('U3', '2'), ('U3', '12'), ('J4', '1')},
        'CC1': {('J1', 'A5'), ('R1', '1')},
        'CC2': {('J1', 'B5'), ('R2', '1')},
    }
    for name, pads in required.items():
        if not pads <= actual.get(name, set()):
            raise SystemExit(f'{name}: missing {sorted(pads - actual.get(name, set()))}')
    print(f'ERC: 0 errors, {0 if clean else 1} known J1 library warning; '
          f'{len(required)} critical nets verified against exported netlist')


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2 or sys.argv[1] not in ('build', 'repair', 'check'):
        print('Usage: python3 manage.py build|repair|check\nbuild: new schematic only; repair: fix misplaced component labels; check: run tests, ERC, and netlist checks')
        raise SystemExit(2)
    {'build': build, 'repair': repair, 'check': check}[sys.argv[1]]()
