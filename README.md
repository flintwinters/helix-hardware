# Helix minimal hardware slice

KiCad 10 schematic for a USB powered STM32C071FBP6 with one shared SPI bus. The WIZ850io W5500 module and a **3.3 V, six wire microSD SPI breakout** have separate chip selects. SWD is available for first firmware bring-up.

Open `helix_minimal.kicad_pro` in KiCad. Run `python3 manage.py check` for ERC and physical pad netlist checks; `python3 manage.py make` regenerates the schematic from the connection table. Regeneration needs the KiCad 10 symbol library (`KICAD_SYMBOL_DIR` can point to it); the checked-in schematic and local symbol are self-contained. `make` preserves the KiCad project settings.

## Interfaces

| Interface | STM32 pads | Connector pins |
| --- | --- | --- |
| SPI1 SCK / MISO / MOSI | PA5 / PA6 / PA7 | WIZ850io J1.4 / J2.6 / J1.3; microSD J4.3 / J4.5 / J4.4 |
| W5500 select / interrupt / reset | PA4 / PA3 / PA0 | WIZ850io J1.5 / J1.6 / J2.5 |
| microSD select | PA8 | J4.6 |
| USB D− / D+ | PA11 / PA12 | J1 A7+B7 / A6+B6 |
| SWDIO / SWCLK / NRST | PA13 / PA14 / PF2 | J5.2 / J5.3 / J5.5 |

J4 is a **project-defined jumper header**, not a claimed footprint for a particular SD module: 1=3V3, 2=GND, 3=CLK, 4=SI/MOSI, 5=SO/MISO, 6=CS. Check the chosen breakout's physical pin order before wiring it. The WIZ850io sockets use its published J1/J2 pin numbering; their relative PCB placement remains to be designed. Firmware should hold WIZ_RST low for at least 500 µs, then wait 50 ms after release before SPI access. Keep both CS lines high while neither device is selected.

The USB-C receptacle uses separate 5.1 kΩ CC pull-downs and a 3.3 V AP2112K regulator. C1 and C2 are the regulator's required 1 µF input/output capacitors; C3 is the MCU's 100 nF decoupling capacitor. VBUS, +3V3, and GND use KiCad power symbols connected by wires. The board currently has a schematic only: there is no routed PCB, enclosure, firmware, USB ESD protection, or measured power budget. WIZ850io can draw about 141 mA by itself, so USB bus power behavior before configuration needs design review before claiming USB compliance.

## Source catalog

| Part | Local document | Verified design facts |
| --- | --- | --- |
| [STM32C071FBP6](https://www.st.com/resource/en/datasheet/stm32c071fb.pdf) | Official ST PDF linked; ST download endpoint timed out here | TSSOP20 pinout, SPI1 PA5/6/7, USB PA11/12, 2–3.6 V supply |
| [WIZ850io](https://docs.wiznet.io/Product/ioModule/WIZ850io) / [W5500](https://docs.wiznet.io/assets/files/W5500_ds_v110e-226ffec190c588b69f88d629789585e1.pdf) | `docs/wiz850io_schematic.pdf`, `docs/w5500.pdf` | 3.3 V module; two 1×6 headers; reset timing; about 141 mA normal operating current |
| [AP2112K-3.3](https://www.diodes.com/datasheet/download/AP2112.pdf) | `docs/ap2112.pdf` | SOT-23-5, 600 mA rating, 1 µF input/output ceramic capacitors |
| [GCT USB4110](https://gct.co/files/specs/usb4110-spec.pdf) | `docs/usb4110.pdf` | USB 2.0 Type-C receptacle footprint and contact arrangement |
| [Adafruit 3 V microSD breakout guide](https://learn.adafruit.com/adafruit-microsd-spi-sdio/pinouts) | `docs/adafruit_microsd_breakout.pdf` | 3.3 V-only SPI signals; generic J4 follows signal names rather than its physical header order |

The local `Helix:AP2112K-3.3` symbol is the KiCad 10 library's inherited AP2112K symbol flattened for portability. All other schematic symbols come directly from the installed KiCad library.
