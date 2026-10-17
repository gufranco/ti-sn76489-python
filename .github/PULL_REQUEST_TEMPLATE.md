## What this changes

One or two sentences. What is different afterwards, and why it needed to be.

## How it was checked

Paste the output rather than describing it. A claim that the tests pass is not
evidence that they did.

```text
```

- [ ] `ruff format --check .` and `ruff check .` are clean
- [ ] `mypy` reports nothing
- [ ] Every test file runs, and coverage is 100% of statements and branches
- [ ] Every new check was run once against input that should fail it

## If this changes a generator, the prescaler or the write interface

The tests alone do not check a change here. Run the census over an SG-1000 library
you own and paste what it prints:

```text
  ok    the model raises on no image: 0 broken
  ok    the shift register never reaches zero: 0 broken
  observed  writes made before the last byte finished loading: N images
```

Deduplicate by digest before quoting a count. A library organised by series
lists the same image several times.

## What it does not carry

- [ ] No cartridge, no fragment of one, and no digest fine enough to rebuild one
- [ ] Nothing that says where to obtain them
