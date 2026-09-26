# Helix minimal hardware slice

KiCad 10 schematic for a USB powered STM32C071FBP6 with one shared SPI bus. The WIZ850io W5500 module and a **3.3 V, six wire microSD SPI breakout** have separate chip selects. SWD is available for first firmware bring-up.

Open `helix_minimal.kicad_pro` in KiCad. Run `python3 manage.py check` for ERC and physical pad netlist checks; `python3 manage.py make` regenerates the schematic from the connection table. Regeneration needs the KiCad 10 symbol library (`KICAD_SYMBOL_DIR` can point to it); the checked-in schematic embeds all its library symbols. `make` preserves KiCad project settings.

## Interfaces

| Interface | STM32 pads | Connector pins |
| --- | --- | --- |
| SPI1 SCK / MISO / MOSI | PA5 / PA6 / PA7 | WIZ850io J1.4 / J2.6 / J1.3; microSD J4.3 / J4.5 / J4.4 |
| W5500 select / interrupt / reset | PA4 / PA3 / PA0 | WIZ850io J1.5 / J1.6 / J2.5 |
| microSD select | PA8 | J4.6 |
| Peripheral rail enable | PA1 | TPS22917 ON |
| USB D− / D+ | PA11 / PA12 | J1 A7+B7 / A6+B6 |
| SWDIO / SWCLK / NRST | PA13 / PA14 / PF2 | J5.2 / J5.3 / J5.5 |

J4 is a **project-defined jumper header**, not a claimed footprint for a particular SD module: 1=switched 3V3, 2=GND, 3=CLK, 4=SI/MOSI, 5=SO/MISO, 6=CS. Check the chosen breakout's physical pin order before wiring it. The WIZ850io sockets use its published J1/J2 pin numbering; their relative PCB placement remains to be designed.

## Power sequence

USB-C VBUS passes a 6 V TVS and a 0.75 A hold PPTC fuse before feeding the AP63203 3.3 V buck. The 0.75 A fuse has lower resistance than the 0.5 A option, leaving more input voltage margin at low USB VBUS. The buck has a 10 µF input capacitor, 100 nF bootstrap capacitor, 6.8 µH shielded inductor, and two 22 µF output capacitors. This inductor is the part used on the manufacturer's 3.3 V evaluation board; its 6.5 A rating exceeds the buck's peak current limit. The MCU has local 100 nF and 4.7 µF decoupling. The TPS22917 switches the WIZ850io and SD breakout rail; its 100 kΩ ON pulldown holds them off at reset, 1 nF CT slows inrush, and 1 kΩ QOD resistor discharges the rail after shutdown. USBLC6 protects D+ and D−.

Firmware must leave the SPI pins high impedance and `PERIPH_EN` low until USB configuration permits the required current, then enable the peripheral rail, pull `WIZ_RST` low for at least 500 µs, release it, and wait 50 ms before W5500 SPI access. Drive both CS lines high before SPI traffic. WIZ850io uses about 141 mA in normal operation; the SD module's peak current depends on the chosen module and card. The PPTC fuse protects faults but does **not** enforce a USB current budget. Measure startup, steady state, and SD write current before claiming USB compliance.

This is still a schematic slice: there is no routed PCB, enclosure, firmware, or measured power budget. The buck's input loop, SW node, ground return, and feedback trace require layout review before fabrication.

## Source catalog

| Part | Local document | Verified design facts |
| --- | --- | --- |
| [STM32C071FBP6](https://www.st.com/resource/en/datasheet/stm32c071fb.pdf) | Official ST PDF linked; ST download endpoint timed out here | TSSOP20 pinout, SPI1 PA5/6/7, USB PA11/12, 2–3.6 V supply |
| [WIZ850io](https://docs.wiznet.io/Product/ioModule/WIZ850io) / [W5500](https://docs.wiznet.io/assets/files/W5500_ds_v110e-226ffec190c588b69f88d629789585e1.pdf) | `docs/wiz850io_schematic.pdf`, `docs/w5500.pdf` | 3.3 V module; two 1×6 headers; reset timing; about 141 mA normal operating current |
| [AP63203](https://www.diodes.com/datasheet/download/AP63200-AP63201-AP63203-AP63205.pdf) and [evaluation board](https://www.diodes.com/assets/Evaluation-Boards/AP63203WU-EVM-User-Guide.pdf) | `docs/ap63203.pdf`, `docs/ap63203_evm.pdf` | Fixed 3.3 V, 2 A buck; 3.8 V minimum input; required bootstrap and input/output capacitors |
| [TPS22917](https://www.ti.com/lit/ds/symlink/tps22917.pdf) | `docs/tps22917.pdf` | Active-high 2 A switch; CT inrush control and resistor-configured QOD discharge |
| [Würth 74439346068](https://www.we-online.com/katalog/datasheet/74439346068.pdf) | `docs/74439346068.pdf` | 6.8 µH shielded inductor, 6.5 A rated, XHMI-6060 footprint |
| [Bourns MF-MSMF075](https://www.bourns.com/docs/product-datasheets/mf-msmf.pdf) | `docs/mf_msmf.pdf` | 1812 PPTC with 0.75 A hold and 1.5 A trip; fault protection only |
| [Vishay SMF6V0A](https://www.vishay.com/docs/49426/49426.pdf) | `docs/smf_tvs.pdf` | 6 V standoff VBUS TVS; cathode on VBUS, anode on GND |
| [ST USBLC6-2SC6](https://www.st.com/resource/en/datasheet/usblc6-2.pdf) | Official ST PDF linked; ST download endpoint rejected the request | Dual USB data-line ESD protection, VBUS-referenced |
| [GCT USB4110](https://gct.co/files/specs/usb4110-spec.pdf) | `docs/usb4110.pdf` | USB 2.0 Type-C receptacle footprint and contact arrangement |
| [Adafruit 3 V microSD breakout guide](https://learn.adafruit.com/adafruit-microsd-spi-sdio/pinouts) | `docs/adafruit_microsd_breakout.pdf` | 3.3 V-only SPI signals; generic J4 follows signal names rather than its physical header order |

All schematic symbols are from the KiCad library. Power and ground connections use KiCad power symbols; the switched peripheral rail uses its own named net.
