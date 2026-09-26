# Helix minimal hardware slice

KiCad 10 schematic for a USB powered STM32C071FBP6 with one shared SPI bus. The WIZ850io W5500 module and a **3.3 V, six wire microSD SPI breakout** have separate chip selects. SWD is available for first firmware bring-up.

Open `helix_minimal.kicad_pro` in KiCad. Run `python3 manage.py check` for label lint, ERC, and physical pad netlist checks. `python3 manage.py repair` fixes misplaced component reference/value fields in the existing schematic without rebuilding it. `python3 manage.py build` creates a schematic only when none exists. Building needs the KiCad 10 symbol library (`KICAD_SYMBOL_DIR` can point to it); the checked-in schematic and local symbols are self-contained.

## PCB routing

The PCB was routed with pinned [KiCadRoutingTools](https://github.com/drandyhaas/KiCadRoutingTools) (`git submodule update --init`). Board Setup specifies 0.30 mm tracks and 0.20 mm clearance for ordinary nets. The USB connector escape class uses 0.15 mm tracks and clearance for USB D±, CC1/CC2, VBUS, and GND; cross-class clearance is 0.20 mm. The route uses 0.40/0.20 mm vias, a 0.10 mm same-net pad-to-via gap, and no size escalation. A 0.05 mm router grid was needed to escape the USB connector without vias in pads.

```sh
python3 vendor/KiCadRoutingTools/py_router/route.py input.kicad_pcb usb_escape.kicad_pcb --nets '/USB_DM' '/USB_DP' '/CC1' '/CC2' VBUS GND --layers F.Cu B.Cu --track-width 0.15 --clearance 0.15 --same-net-pad-clearance 0.1 --grid-step 0.05 --via-size 0.4 --via-drill 0.2 --escalation off --fab-tier advanced --strict-sizes --no-fix-drc-settings
python3 vendor/KiCadRoutingTools/py_router/route.py usb_escape.kicad_pcb bulk_route.kicad_pcb --nets '*' --layers F.Cu B.Cu --keep-input-copper --track-width 0.2 --clearance 0.2 --same-net-pad-clearance 0.1 --grid-step 0.05 --via-size 0.4 --via-drill 0.2 --escalation off --fab-tier advanced --strict-sizes --no-fix-drc-settings
```

These commands start from an unrouted copy with the existing GND zone; use matching `.kicad_pro` copies for the staged files. They produce routing candidates, then local clearance corrections and DRC-guided widening are required. The committed route has 388.6 mm (81%) of non-USB routed length at 0.30 mm; constrained sections are 0.20 mm. The USB escape remains 0.15 mm. KiCad DRC reports zero copper errors, zero unconnected items, and zero schematic parity issues. The router's pad-overlap checker reports zero in-pad vias. The 19 remaining DRC messages concern text height and a footprint library mismatch. Review the WIZ850io mechanics before fabrication.

## Interfaces

| Interface | STM32 pads | Connector pins |
| --- | --- | --- |
| SPI1 SCK / MISO / MOSI | PA5 / PA6 / PA7 | WIZ850io U3.4 / U3.7 / U3.3; microSD J4.5 / J4.3 / J4.4 |
| W5500 select / interrupt / reset | PA4 / PA3 / PA0 | WIZ850io U3.5 / U3.6 / U3.8 |
| microSD select | PA8 | J4.6 |
| USB D− / D+ | PA11 / PA12 | J1 A7+B7 / A6+B6 |
| SWDIO / SWCLK / NRST | PA13 / PA14 / PF2 | J5.2 / J5.3 / J5.5 |

J4 is a **project-defined jumper header**, not a claimed footprint for a particular SD module: 1=GND, 2=3V3, 3=SO/MISO, 4=SI/MOSI, 5=CLK, 6=CS. Check the chosen breakout's physical pin order before wiring it. U3 combines WIZ850io J1 pins 1–6 with J2 pins 6–1 as footprint pads 1–12. Its board placement remains subject to DRC and mechanical review. Firmware should hold WIZ_RST low for at least 500 µs, then wait 50 ms after release before SPI access. Keep both CS lines high while neither device is selected.

The USB-C receptacle uses separate 5.1 kΩ CC pull-downs and a 3.3 V AP2112K regulator. C1 and C2 are the regulator's required 1 µF input/output capacitors; C3 is the MCU's 100 nF decoupling capacitor. VBUS, +3V3, and GND use KiCad power symbols connected by wires. The PCB is still being placed and routed; there is no enclosure, firmware, USB ESD protection, or measured power budget. WIZ850io can draw about 141 mA by itself, so USB bus power behavior before configuration needs design review before claiming USB compliance.

## Source catalog

| Part | Local document | Verified design facts |
| --- | --- | --- |
| [STM32C071FBP6](https://www.st.com/resource/en/datasheet/stm32c071fb.pdf) | Official ST PDF linked; ST download endpoint timed out here | TSSOP20 pinout, SPI1 PA5/6/7, USB PA11/12, 2–3.6 V supply |
| [WIZ850io](https://docs.wiznet.io/Product/ioModule/WIZ850io) / [W5500](https://docs.wiznet.io/assets/files/W5500_ds_v110e-226ffec190c588b69f88d629789585e1.pdf) | `docs/wiz850io_schematic.pdf`, `docs/w5500.pdf` | 3.3 V module; two 1×6 headers; reset timing; about 141 mA normal operating current |
| [WIZ850io KiCad library](https://github.com/lorenzofattori/WIZ850io-KiCad-library) | `vendor/wiz850io/WIZ850io.lib`, `vendor/wiz850io/WIZ850io.kicad_sym`, `footprints/Helix.pretty/WIZ850io.kicad_mod` | Imported 12-pad symbol/footprint; 20.32 mm row spacing and 2.54 mm pitch match the module drawing. Socket pad drill enlarged from 0.762 to 1.0 mm to match the prior KiCad pin-socket footprints; module outline moved from silk to fabrication layer for clearance. Library is third-party; verify the actual module revision and mating socket before fabrication. |
| [AP2112K-3.3](https://www.diodes.com/datasheet/download/AP2112.pdf) | `docs/ap2112.pdf` | SOT-23-5, 600 mA rating, 1 µF input/output ceramic capacitors |
| [GCT USB4110](https://gct.co/files/specs/usb4110-spec.pdf) | `docs/usb4110.pdf` | USB 2.0 Type-C receptacle footprint and contact arrangement |
| [Adafruit 3 V microSD breakout guide](https://learn.adafruit.com/adafruit-microsd-spi-sdio/pinouts) | `docs/adafruit_microsd_breakout.pdf` | 3.3 V-only SPI signals; generic J4 follows signal names rather than its physical header order |

The local `Helix:AP2112K-3.3` symbol is the KiCad 10 library's inherited AP2112K symbol flattened for portability. The edited STM32 pin layout is stored in `symbols/STM32C071FBPx.kicad_sym`. The WIZ850io symbol was converted from the linked KiCad library with `kicad-cli sym upgrade`; its footprint was upgraded with `kicad-cli fp upgrade`. Other symbols come from the installed KiCad library.
