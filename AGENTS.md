This project explores the smallest verifiable STM32 + USB + Ethernet + SD hardware path. Favor explicit, checkable electrical interfaces over speculative board features.

The KiCad schematic includes KiCad edits that must be preserved. `manage.py` holds the interface contract: `check` verifies labels, ERC, and critical nets; `repair` fixes local label placement errors; `build` creates a schematic only when none exists. Use existing KiCad symbols. Catalog primary part documents in `README.md` and keep local PDFs in `docs/` when sources permit download.

The PCB has manual USB D+/D− copper preserved through `manage.py route`; the other signals are routed with pinned KiCadRoutingTools. Both layers retain thermal-relief GND pours. `manage.py audit` runs full DRC and checks every PCB pad net against the schematic. Current job: resolve two open GND connections and WIZ850io mechanical overlap, confirm J6 purpose and SD module header order, then validate USB power behavior before bring-up. The detailed evidence is in `docs/pcb_audit.md`.
Schematic components must be connected with wires and use proper power symbols not just a 'GND' label.
Use python to procedurally place and connect components rather than doing it manually.

Verify with kicad-cli erc and drc
