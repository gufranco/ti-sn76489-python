# TI SN76489

The Texas Instruments SN76489AN and SN76494N sound generators in Python, advanced one input clock at a time and held to TI's data sheet.

English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/ti-sn76489-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/ti-sn76489-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/ti-sn76489-python)](https://github.com/gufranco/ti-sn76489-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**348** distinct SG-1000 images booted for **600** frames each, **0** property failures, **17** quotes located in the data sheet, **2** parts, **603** tests, **100%** statement and branch coverage, no dependencies

```python
import sn76489

part = sn76489.Chip("sn76489an")


def write(value):
    part.write(value)
    while not part.ready:
        part.tick()


for value in (0x85, 0x00, 0x90, 0xBF, 0xDF, 0xFF):
    write(value)

for _ in range(1024):
    part.clock()

sampled = []
for _ in range(12):
    part.clock()
    sampled.append(part.bits[0])
print(sampled)
print(part.periods[0], part.steps, round(part.level, 3))
```

```
[0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
5 [0, 15, 15, 15] 0.0
```

A part powers up with every register scrambled, as a discrete part does. Two bytes give tone 1 a period of 5, a third sets its attenuation to 0, and three more turn the other channels off. A write sets the period, not the counter, so the first toggle can be up to 1,024 periods away; after that the flip-flop toggles every 5 periods, which is the data sheet's `f = N/32n`.

## Install

| Requirement | Version                      |
| :---------- | :--------------------------- |
| Python      | 3.12 or newer                |
| git         | Any, to fetch the submodules |

```bash
git clone --recurse-submodules https://github.com/gufranco/ti-sn76489-python.git
cd ti-sn76489-python
python3 sn76489/doctor.py
```

The package imports nothing outside the standard library. The submodule is `ti-tms9918-python`, with `zilog-z80-python` inside it, and only the census uses them. A source archive from the download-zip link has no submodules: there the census and its tests report why they cannot run, and everything else works.

The doctor checks the machine and the checkout and ends with one line. Paste its whole output into any bug report.

```
  10 checks, nothing to report
```

Releases follow [Semantic Versioning](https://semver.org/) and are cut from the commit history by semantic-release. Every release is tagged and listed on the [releases page](https://github.com/gufranco/ti-sn76489-python/releases).

## The interface

`sn76489.Chip(model, seed=UNSET_SEED)` builds one part. `model` is required. `seed` sets the power-on scramble of every register, counter, flip-flop and the shift register.

| Model       | Aliases                         | Input clock divided by | Input clocks to load a byte |
| :---------- | :------------------------------ | :--------------------- | :-------------------------- |
| `sn76489an` | `sn76489a`, `76489an`, `76489a` | 16                     | 32                          |
| `sn76494n`  | `sn76494`, `76494n`, `76494`    | 2                      | 4                           |

### Calls

| Call           | Effect                                                                                                                                                                                                                                               |
| :------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `write(value)` | One byte on the data bus with CE and WE strobed. A byte with bit 7 set addresses a register and sets its four low bits; one without it sets the six high bits of the tone period last addressed, or the four bits of any other register. READY falls |
| `tick()`       | One input clock                                                                                                                                                                                                                                      |
| `clock()`      | One prescaled period: 16 input clocks on the SN76489AN, 2 on the SN76494N                                                                                                                                                                            |
| `reset()`      | The part has no reset pin, so nothing changes. Returns the part. The part is defined only once software has written all eight registers: three periods, four attenuations and the noise control                                                      |

### State

| Attribute | Meaning                                                                           |
| :-------- | :-------------------------------------------------------------------------------- |
| `ready`   | The READY pin: false from a write until the byte has loaded                       |
| `loading` | Input clocks left before READY rises                                              |
| `periods` | The three tone periods, 10 bits each                                              |
| `steps`   | The four attenuation steps, 0 for full volume to 15 for off                       |
| `control` | The noise control: bit 2 selects white noise, bits 0 and 1 the rate               |
| `shift`   | The 15-bit noise shift register                                                   |
| `latched` | The register the last first byte addressed                                        |
| `bits`    | Each channel's output bit: the three flip-flops, then bit 0 of the shift register |
| `gains`   | Each channel's gain from Table 1's weights, 1.0 at step 0 and 0.0 when off        |
| `level`   | The sum of the gains of the channels whose bit is high                            |
| `ticks`   | Input clocks since the part was built                                             |
| `model`   | The canonical model name                                                          |
| `part`    | The `Model` record: `prescale`, `load_clocks`, `aliases`, `summary`               |

### Module contents

| Name                        | Content                                                                          |
| :-------------------------- | :------------------------------------------------------------------------------- |
| `sn76489.MODELS`            | The two `Model` records, keyed by canonical name                                 |
| `sn76489.UnknownModelError` | Raised for a missing or unknown model name. The message lists the names accepted |
| `sn76489.UNSET_SEED`        | The seed a part is scrambled from when none is given                             |
| `sn76489.__version__`       | The installed version                                                            |

```python
import sn76489

for name, model in sn76489.MODELS.items():
    print(name, model.aliases, model.prescale, model.load_clocks)

try:
    sn76489.Chip("sn76496")
except sn76489.UnknownModelError as error:
    print(error)
```

```
sn76489an ('sn76489a', '76489an', '76489a') 16 32
sn76494n ('sn76494', '76494n', '76494') 2 4
sn76496 is not a model this package covers; it has sn76489an, sn76494n
```

The two parts differ in the prescaler and in the clocks a byte takes to load, 32 against 4. The same period of 3 holds tone 1's flip-flop for 48 input clocks on the SN76489AN and 6 on the SN76494N.

```python
import sn76489

for part in (sn76489.Chip("sn76489an"), sn76489.Chip("sn76494n")):
    for value in (0x83, 0x00):
        part.write(value)
        while not part.ready:
            part.tick()
    edges = []
    while len(edges) < 3:
        before = part.bits[0]
        part.tick()
        if part.bits[0] != before:
            edges.append(part.ticks)
    print(part.model, edges[2] - edges[1], edges[1] - edges[0])
```

```
sn76489an 48 48
sn76494n 6 6
```

## READY and the noise generator

```python
import sn76489

part = sn76489.Chip("sn76489an")
part.write(0xE4)
held = 0
while not part.ready:
    part.tick()
    held += 1
print(held, hex(part.shift))

shifts = 0
for _ in range(32 * 4):
    before = part.shift
    part.clock()
    shifts += part.shift != before
print(shifts, hex(part.shift))
```

```
32 0x4000
4 0x400
```

One byte selects white noise at N/512. READY stays low for the 32 input clocks the data sheet gives for a load, and the write clears the shift register to its top bit, as the data sheet requires. The register then shifts once every 32 periods, which is 512 input clocks. With bits 0 and 1 both clear, each of the first four shifts feeds back a zero.

The data sheet never describes the shift register. Its width, its taps and where the output is taken come from SMS Power's notes, which cite data taken on an SC-3000H carrying a discrete SN76489AN. MAME builds the same sequence with the output two shifts later. Both are recorded in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md).

## The census

```bash
python3 -m conformance.census /path/to/sg1000/library --frames 600 --jobs 10
```

SG-1000 software writes the sound port only once its processor and video chip are running, so the census boots every image on [`ti-tms9918-python`](https://github.com/gufranco/ti-tms9918-python)'s SG-1000 board, with the `zilog-z80-python` processor and this part on ports `0x40` to `0x7F`, ticked once per processor clock. It accepts directories, zip archives and single images, and counts each distinct image once by digest. It prints a summary, writes [`conformance/corpus.json`](conformance/corpus.json), and exits 1 when a property breaks.

Two properties gate the run: the model raises no exception on any image, and the shift register never reaches zero. Writes made before the previous byte finished loading are counted and named per image but gate nothing, because the data sheet does not say what the chip does with them.

| Observation                                                            | Images, of 348     |
| :--------------------------------------------------------------------- | :----------------- |
| Never wrote the sound port                                             | 35                 |
| Latched a tone period, tones 1, 2 and 3                                | 174, 140, 140      |
| Latched an attenuation, tones 1, 2 and 3 and noise                     | 312, 312, 311, 312 |
| Latched the noise control                                              | 49                 |
| Sent a second byte after a period latch, tones 1, 2 and 3              | 174, 140, 140      |
| Sent a second byte after an attenuation latch, tones 1 and 2 and noise | 4, 4, 2            |
| Sent a second byte after the noise control latch                       | 4                  |
| Wrote noise control 0, 3, 4, 5, 6 and 7                                | 22, 8, 4, 3, 3, 13 |
| Wrote noise control 1 or 2                                             | 0                  |
| Turned a channel off with attenuation 15                               | 313                |
| Wrote a period of zero                                                 | 38                 |

Across all images the part took 1,629,574 writes. 117,926 of them on retail images, and 873,222 on the rest, arrived before the previous byte finished loading.

[`conformance/corpus.json`](conformance/corpus.json) holds those counts and nothing from any cartridge, so the suite checks them on a machine with no library.

## Is it right

Every fact TI printed that a test can reach is held to the code. [`conformance/hardware.json`](conformance/hardware.json) carries each fact with its sentence and page, and [`conformance/hardware.test.py`](conformance/hardware.test.py) compares them with the constants in the package. `python3 -m conformance.quotes` finds every quoted sentence in the data sheet.

Every value the data sheet does not print sits under `notStated` in the same file, marked unverified, with its source and the measurement that would settle it. [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) lists them. The places where the data sheet contradicts itself are in [`conformance/divergences.json`](conformance/divergences.json).

## Working on it

| Need                                                            | Where                                                                 |
| :-------------------------------------------------------------- | :-------------------------------------------------------------------- |
| Every gate and the order to run them                            | [CONTRIBUTING.md](CONTRIBUTING.md)                                    |
| The same material for a coding agent                            | [AGENTS.md](AGENTS.md)                                                |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md)                                                |
| Bug reports                                                     | [GitHub Issues](https://github.com/gufranco/ti-sn76489-python/issues) |
| Security reports                                                | [SECURITY.md](SECURITY.md)                                            |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
python3 sn76489/core.test.py
```

Each module has a test file beside it, named after it, and each runs on its own as above. Coverage is a hard gate at 100% statement and branch.

## References

- _SN76489AN Digital Complex Sound Generator_ data sheet, Texas Instruments, undated. 9 pages, 342,317 bytes, SHA-256 `ad2b99beee0f4f7979828c4f3d9f2bf013deac39fa6263309875232e78a99f91`. It is not redistributable and is not in this repository. Its only known copy is at https://wiki.console5.com/tw/images/b/b0/SN76489.pdf, behind a challenge page that a script cannot pass, so put your copy in `docs/manufacturer/` and `python3 -m conformance.documents --check` refuses any other file.
- _SN76489AN Digital Complex Sound Generator_ data sheet, a second scan of the same printing with no later hand on it, Texas Instruments, undated. 9 pages, 1,711,168 bytes, SHA-256 `af0a54394d3a92a50cbf25a13b384e8d44687cd2c58314d39cb15d58f6eba2d0`, at https://github.com/MajicDesigns/MD_SN76489/raw/30b974c97d99aface74a780dec1046b308f48317/media/doc/SN76489AN%20DataSheet.pdf. It has no text layer, so it is read as page images. It settles what TI printed on pages 3 and 4. `python3 -m conformance.documents` fetches it into `docs/manufacturer/`.
- SMS Power, _SN76489_, https://www.smspower.org/Development/SN76489, for the noise shift register and the power-on state of discrete parts. Facts only; no code is taken.
- MAME, `src/devices/sound/sn76496.cpp` at commit `92f8878050f78c55c6961b688d4960b078150c6a`, https://github.com/mamedev/mame, for behaviour the data sheet leaves unstated. Facts only; no code is taken.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE).
