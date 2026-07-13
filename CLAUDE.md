# CLAUDE.md

Guidance for working in this repo.

## Overview

`rddsketch` is a Rust-backed [DDSketch](https://arxiv.org/pdf/1908.10693.pdf)
quantile sketch exposed to Python via PyO3/maturin — a faster,
lower-memory (for many concurrent sketches) near-drop-in replacement for
DataDog's official `ddsketch` package.

The algorithm comes from an existing crate,
[`sketches-ddsketch`](https://github.com/mheffner/rust-sketches-ddsketch)
(mheffner) — a Rust port of DataDog's own Go/Java implementations. `src/lib.rs`
is a thin `#[pyclass]` wrapper: input validation and PyO3 glue only. Don't
reimplement mapping/store logic here — if quantile math looks wrong, check
`sketches-ddsketch` upstream first.

## Project layout

```
rddsketch/
├── Cargo.toml
├── pyproject.toml            # maturin config
├── src/
│   └── lib.rs                 # PyDDSketch: PyO3 wrapper over sketches_ddsketch::DDSketch
├── python/
│   └── rddsketch/
│       ├── __init__.py
│       └── __init__.pyi       # type stubs for the compiled extension
├── tests/                     # pytest suite
├── benchmarks/                # rddsketch vs the official ddsketch package
├── .github/workflows/
│   ├── ci.yml                 # rust fmt/clippy/test, python test matrix, ruff
│   └── release.yml            # build wheels (linux/macos/windows + sdist), publish
└── README.md
```

## Development commands

```sh
# Rust unit tests (wrapper logic only -- the algorithm is tested upstream
# in sketches-ddsketch; to_bytes/from_bytes need a GIL token so they're
# only covered by the pytest suite, not here):
cargo test --no-default-features

# Build + install into the current Python env, then run the Python suite:
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
maturin develop --release
pytest

# Lint (same checks CI runs):
cargo fmt --check
cargo clippy --no-default-features -- -D warnings
ruff check .
ruff format --check .

# Benchmarks (rddsketch vs ddsketch): throughput, accuracy, and two
# different memory scenarios (see benchmarks/results.md for why there are
# two — one giant sketch vs. many small ones tell very different stories).
python benchmarks/bench_insert.py
python benchmarks/bench_accuracy.py
python benchmarks/bench_memory.py
python benchmarks/bench_memory_many_sketches.py
```

Note: `extension-module` (the pyo3 feature that links against libpython) is
gated behind a Cargo feature that's on by default, so plain `cargo build`/
`cargo test` will try to link libpython and fail outside a Python venv
context unless you pass `--no-default-features`.

## Conventions

- `src/lib.rs` should stay a thin wrapper around `sketches_ddsketch`: input
  validation and `PyResult`/`PyValueError` marshalling only. If you find
  yourself adding bucket-mapping or bin-collapsing logic here, that
  probably belongs upstream instead.
- No `weight` parameter on `add()` — the underlying crate's store
  increments bin counts by 1 per call with no weighted-insert path. Don't
  fake it by looping `add()` `weight` times; that's a different (and much
  slower) semantic than a true weighted insert.
- Default `max_num_bins=2048` matches `LogCollapsingLowestDenseDDSketch`'s
  default bin limit, not the unbounded `ddsketch.DDSketch`. Keep this in
  mind when comparing against the official package in benchmarks/tests —
  compare like for like, or note the difference explicitly.
- Any behavior change to the public Python API needs a matching update to
  `python/rddsketch/__init__.pyi`.
- After changing `src/lib.rs`, rebuild with `maturin develop --release`
  before running `pytest`. An editable install does not pick up Rust
  changes automatically.
- `pyo3` is built with `abi3-py311` (`Cargo.toml`), matching
  `requires-python` in `pyproject.toml`. One wheel per platform covers
  every supported Python version; don't drop `abi3-pyXXX` without also
  widening the release matrix for per-version wheels.
- Keep the `version` field in `Cargo.toml` and `pyproject.toml` in sync.
  They aren't derived from each other.
- `to_bytes()`/`from_bytes()` are exactly `sketches_ddsketch`'s
  Java-compatible encoding (`to_java_bytes`/`from_java_bytes`), unmodified
  — bytes produced by `to_bytes()` are portable to any standard DDSketch
  consumer. Don't prepend a custom header to smuggle extra state through:
  an earlier version did that to recover `relative_accuracy` on
  `from_bytes()`, but it silently broke that portability. `relative_accuracy`
  isn't recoverable from the encoded bytes (`Config` only exposes the
  derived `gamma`, and only `pub(crate)`, on an already-constructed
  sketch), so `from_bytes()` takes it as an explicit argument instead —
  the caller already knows what accuracy they built the sketch with.

## Releasing

`.github/workflows/ci.yml` runs on every push/PR: `cargo fmt`/`clippy`/
`test`, `pytest` across Python 3.11-3.14, and `ruff`.

`.github/workflows/release.yml` builds wheels for Linux (x86_64/aarch64,
manylinux), Windows (x64), macOS (x86_64/aarch64), plus an sdist.

- `workflow_dispatch` (manual run from the Actions tab) publishes the
  build to TestPyPI as a dry run.
- Pushing a tag matching `v*` (e.g. `v0.1.0`) publishes to real PyPI.

Both publish jobs use PyPI Trusted Publishing (OIDC) via
`pypa/gh-action-pypi-publish`, not a stored API token. Before either can
succeed, a trusted publisher must be configured on the PyPI/TestPyPI side
for this repo — that's a one-time manual step on pypi.org / test.pypi.org,
not something in-repo config can do: project settings → Publishing → add
GitHub Actions publisher, pointing at owner `f4hy`, repo `rddsketch`,
workflow `release.yml`, and environment `pypi` (or `testpypi`). Neither is
configured yet, so neither publish job will succeed until that's done.

Before tagging a real release: bump `version` in both `Cargo.toml` and
`pyproject.toml`, and confirm a TestPyPI dry run installs and imports
cleanly first.
