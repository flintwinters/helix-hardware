This project explores the smallest verifiable STM32 + USB + Ethernet + SD hardware path. Favor explicit, checkable electrical interfaces over speculative board features.

The KiCad schematic includes KiCad edits that must be preserved. `manage.py` holds the interface contract: `check` verifies labels, ERC, and critical nets; `repair` fixes local label placement errors; `build` creates a schematic only when none exists. Use existing KiCad symbols. Catalog primary part documents in `README.md` and keep local PDFs in `docs/` when sources permit download.

The PCB has a two-layer signal route made with pinned KiCadRoutingTools, strict 0.30 mm ordinary-net traces, fine-pitch USB escapes, and no in-pad vias. Both layers have GND pours with thermal reliefs by default; GND was excluded from autorouting, and one GND zone connection remains for manual review. Current job: resolve that connection and remaining text/footprint DRC messages, then validate USB power behavior and WIZ850io mechanics before bring-up.
Schematic components must be connected with wires and use proper power symbols not just a 'GND' label.
Use python to procedurally place and connect components rather than doing it manually.

Verify with kicad-cli erc and drc
