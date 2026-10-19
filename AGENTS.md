# Working in this repository

Read [FAMILY.md](FAMILY.md) first. It is the standard every member of this
family carries, byte for byte, and it decides most questions before they are
asked. What follows is only what is true of this member. [README.md](README.md)
is the document written for a person.

## What this project is, in one paragraph

A model of the Texas Instruments SN76489AN and SN76494N sound generators,
advanced one input clock at a time. It covers the write interface and the READY
handshake, the three tone generators, the noise generator and its shift
register, and the four attenuators. What the data sheet prints comes from TI's
own sheet, read twice. What it does not print comes from SMS Power's notes and
MAME, marked unverified. What real software asks of the part comes from a census
over the SG-1000 library.

## The interface a caller drives

- `sn76489.Chip(model)` builds a part. `model` is `sn76489an` or `sn76494n`.
  Everything comes up scrambled, as a discrete part does, and there is no reset
  pin, so `reset()` hands the part back unchanged.
- `write(value)` is one byte on the data bus with CE and WE strobed together.
  `ready` is the READY pin: false from a write until the byte has loaded.
- `tick()` advances one input clock. `clock()` advances one prescaled period,
  16 input clocks on the SN76489AN and 2 on the SN76494N.
- `bits`, `steps`, `gains` and `level` describe the output after each period:
  each channel's flip-flop or shift register bit, its attenuation step, its gain
  from Table 1's weights, and their sum.

Everything the package raises lives in
[`sn76489/errors.py`](sn76489/errors.py) and nowhere else.

This is a part, not a clocked part in the family's sense. It runs no program, so
it has no `step`, and it is built by `Chip`.

## The authority ladder

1. **[`conformance/hardware.json`](conformance/hardware.json) facts**, quoted
   from TI's data sheet and matched against its text layer by
   [`conformance/quotes.py`](conformance/quotes.py). Its tables were also read
   from the page image.
2. **The SG-1000 library**, through
   [`conformance/census.py`](conformance/census.py), for what real software
   writes.
3. **SMS Power's notes** for the noise shift register, and **MAME** for what
   neither covers, each under `notStated` with `verified: false`.

[`conformance/divergences.json`](conformance/divergences.json) records every
place two sources part, including the places the data sheet contradicts itself.

## What is settled and what is not

**Settled: everything the data sheet prints and a test can reach.** Each fact in
[`conformance/hardware.json`](conformance/hardware.json) is held to the code by
[`conformance/hardware.test.py`](conformance/hardware.test.py).

**Not settled: 10 things**, every entry under `notStated` and three
places the data sheet contradicts itself, each in
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with what would close it. Do not close one
by argument.

## The census runs on member 2's board

SG-1000 software only writes the sound port once its processor and video chip are
running, so the census boots each image on
[`ti-tms9918-python`](https://github.com/gufranco/ti-tms9918-python)'s board,
pinned as a submodule, with this part on ports `0x40` to `0x7F`. The package
itself imports nothing from it; only [`conformance/board.py`](conformance/board.py)
does.

**That repository has its own `conformance` package.** `board.py` loads it under
the name `tms9918_conformance` so the two never shadow each other. Import member
2's code through `board.borrowed()`, never with a plain `import conformance`.

**Two machine names are exempt, and only two.** The SN76489AN was a catalogue
part, so no tracked file names a machine it shipped in, and
[`conformance/family_member.py`](conformance/family_member.py) holds the list it
sweeps for. The SG-1000 is named because its library is the census's oracle.
The SC-3000H is named because SMS Power's cited measurement was taken on one.
Any other mention names the part by its number.

## Test cartridges

[`conformance/testroms.json`](conformance/testroms.json) lists every test
cartridge that exercises this part, by SHA-256, as FAMILY.md's fifth
requirement asks.

Neither cartridge reports a verdict about sound: both are stimulus only, meant
to be heard. What each run holds is what the part was left set to, against what
the program itself says it set.

- **Run, stimulus only: the SG-1000 M2 check program**, from the SG-1000 set's
  `5 Programs & Tools.zip` under `~/sms-artifacts/htgdb/`. It boots on member
  2's board with this part on the sound port.
  [`conformance/testroms.py`](conformance/testroms.py) reads its screen every ten
  frames for 480 frames and, while a `CHANNEL - n` screen is up, keeps what the
  part holds: the four attenuation steps, the three periods and the noise
  control. On each of the four screens only the channel it names is sounding,
  at period `0B3h`, then white noise.
- **Run, stimulus only: Sound Test 1.1** from the Master EverDrive set's
  `5 Tools & Service Test Carts.zip`. It is an interactive register editor. With
  no input it writes its starting values every frame, and after 60 frames the
  part holds period `3FFh` and attenuation `Fh` on every channel, the values its
  own screen opens with.

```bash
python3 -m conformance.testroms [--write] <zip, folder or image ...>
```

With no argument it reads the folders and zips named in `TEST_CARTRIDGES`. With
none present it says so and exits 2, and CI turns that into a notice.
[`conformance/testroms.test.py`](conformance/testroms.test.py) replays the
recorded verdict with no image present.

## Every gate, in the order to run them

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
uvx yamllint==1.38.0 --strict .
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for f in $(find sn76489 conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$f" || echo "FAILED $f"
done
"${cov[@]}" report
```

Then the ones outside the coverage step:

```bash
python3 -m conformance.corpus
python3 -m conformance.speed
python3 -m conformance.documents --check
python3 -m conformance.quotes
```

And, with an SG-1000 library present, the one that walks it:

```bash
python3 -m conformance.census <library> [library ...] [--frames N] [--jobs N]
```

Everything under [`conformance/`](conformance) runs as a module. Run as a
script, its own directory goes on the import path and a file there shadows any
standard library module of the same name.

## Conventions that are not negotiable

| Thing                       | Rule                                                                                                                                              |
| :-------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------ |
| Language                    | Python only                                                                                                                                       |
| Comments                    | None in source or in build files, and a docstring counts as one. Names, small functions, constants and types carry what a comment would have said |
| Test layout                 | `<module>.test.py` beside the module it covers                                                                                                    |
| Test shape                  | Arrange, act, assert, each opened by its bare marker                                                                                              |
| Coverage                    | 100% statements and branches, enforced                                                                                                            |
| Types                       | `mypy` at strict, plus every optional error class                                                                                                 |
| Package manager for tooling | pnpm, never npm                                                                                                                                   |
| Commits                     | Conventional Commits, subject at most 50 characters                                                                                               |
| Documents                   | Read, quoted and pinned by digest. Never committed                                                                                                |
| Cartridges                  | Never committed, in any form, for any reason                                                                                                      |

The linter's ignores in [`pyproject.toml`](pyproject.toml) carry no comments, so
their reasons live here:

- `N818`: some exceptions are signals rather than failures. The standard
  library names those without the suffix too.
- `N999` and `PLR2004` in tests: a test file is named after its module with a
  dot, and its literals are the expected values.
- `T201` in `conformance/`, the doctor and `environment.py`: printing is their
  output.
- `BLE001` in the doctor, `environment.py` and the census: a check that throws
  has to become a line in the report rather than end the run. One image that
  raises must not throw away the census's results for every other image.
- `PLC0415` in the doctor: it imports the package inside its checks, so a
  package that fails to import becomes a line in the report rather than a
  traceback before the report starts.
- The `tms9918.*` and `z80.*` override in mypy: the submodules are checked in
  their own repositories, against their own gates.
- `@unittest\.skipUnless\(CLOCKED,` in the coverage exclusions: this member is
  not a clocked part, so the family tests that drive a clock are skipped here
  and their bodies never run.

The formatter's ignores in [`.prettierignore`](.prettierignore) carry no
comments either, so their reasons live here:

- `pnpm-lock.yaml` and `package-lock.json`: the package manager writes them, in
  its own layout, on every install.
- `node_modules/`, `.venv/`, `venv/`, `build/`, `dist/` and `*.egg-info/`:
  installed or built, never written by hand.
- `.coverage`, `coverage.json`, `htmlcov/` and the tool caches: the output of a
  run, never committed.
- `docs/`, `specs/`, `.work/` and `.claude/`: local working material, never
  committed.
- `ti-tms9918-python/`: a submodule. It is a member that formats and checks
  itself, and the commit pinned here is not this repository's to change.

## Layout

```
sn76489/
  core.py         the part: the write interface, READY, the prescaler and the generators
  models.py       the two parts and what differs between them
  tone.py         the 10-stage tone counter and the two byte forms of a period
  noise.py        the shift register, its feedback and its rates
  attenuation.py  Table 1's weights and the gain they give
  errors.py       everything this package raises
  doctor.py       what the machine and the package look like, for a report
  environment.py  what the doctor reads about the machine
  version.py      rewritten by the release job and by nothing else
conformance/
  board.py          member 2's SG-1000 board with this part on the sound port
  census.py         boots every SG-1000 image in a library you own and counts what it writes
  corpus.json       those counts, holding nothing from any cartridge
  corpus.py         replays them
  testroms.json     every test cartridge that exercises the part, and the verdict of each one run
  testroms.py       runs the ones you hold on member 2's board and keeps what the part was set to
  documents.json    the data sheet, by digest
  documents.py      checks a copy you hold and refuses any other file
  hardware.json     TI's data sheet, fact by fact, and every value it does not print
  divergences.json  every place two sources part
  manual.py         the data sheet's text, flattened to letters and digits
  quotes.py         every quote the records carry, found in the data sheet
  links.py          the weekly check that every cited address still answers
  speed.py          the throughput floor
  package.py        the wheel audit
  source.py         the check that no documentation string remains
  family_*.test.py  the family standard, held as tests, one topic a file
  family_member.py  what this member answers to them
  family_shared.py  what more than one of them reads
ti-tms9918-python/  the board the census runs on, a pinned submodule
```

## Things that will bite you

**The held scan cannot be fetched by a script.** Its only known host answers
with a challenge page, so `documents.py` verifies a copy you already hold in
`docs/manufacturer/` and never tries to download it. The unretouched scan sits
in a public repository at a pinned commit, and `documents.py` fetches it.

**A later hand marked pages 3 and 4 of the held scan.** It retyped the data
formats on page 4, labelling the bits the opposite way to TI's prose, and
retyped Table 4's second row. The second, unretouched scan in
[`conformance/documents.json`](conformance/documents.json) shows what TI
printed: page 4 agrees with the prose, and Table 4 gives tone 1's frequency
and attenuation the same address.

**A tone counter powers up anywhere in 0 to 1,023.** A write sets the period,
not the count, so the first toggle after a write can be up to 1,024 periods
away. A test that measures a period skips the first toggle.

**`clock()` is a convenience over `tick()`.** READY and the prescaler move on
`tick()`; a board that paces the part by the processor clock calls `tick()`.

## Before calling anything finished

[`FAMILY.md`](FAMILY.md) carries a checklist under "What a new repository has to
have before it is a member". Every line on it was a defect found in one of these
repositories and fixed in all of them. Read it before adding a surface, and read
it again before saying a change is done.

**A check nobody has seen fail is not known to work.** Drive it, once,
deliberately, against input that should fail it.

**Silence and success produce the same output.** A census that walked no file
says so, and exits non-zero.

## What a change is expected to leave behind

A gate that would have caught the bug. A change to a generator, the prescaler or
the write interface also runs the census over a real library. The tests check
what the data sheet says. The census checks what software that ran on the chip
still does.
