This project explores the smallest verifiable STM32 + USB + Ethernet + SD hardware path. Favor explicit, checkable electrical interfaces over speculative board features.

The KiCad schematic is generated from the connection table in `manage.py`; `python3 manage.py check` runs ERC and verifies critical pads in the exported netlist. Use existing KiCad symbols. Catalog primary part documents in `README.md` and keep local PDFs in `docs/` when sources permit download.

Current job: validate module choice, USB power behavior, and mechanics before designing a PCB; then prove the interface with firmware and hardware measurements.
Schematic components must be connected with wires and use proper power symbols not just a 'GND' label.
Use python to procedurally place and connect components rather than doing it manually.

Verify with kicad-cli erc and drc
