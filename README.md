# rddsketch

Python bindings, via [PyO3](https://pyo3.rs), for
[`sketches-ddsketch`](https://github.com/mheffner/rust-sketches-ddsketch) —
a Rust port of DataDog's Go/Java [DDSketch](https://arxiv.org/pdf/1908.10693.pdf)
implementations. A near-drop-in, faster replacement for DataDog's official
[`ddsketch`](https://github.com/DataDog/sketches-py) Python package.

## Install

```sh
pip install rddsketch
```

Prebuilt wheels (Linux/macOS/Windows, Python 3.11+) via `abi3`, no Rust
toolchain needed at install time.

## Usage

```python
from rddsketch import DDSketch

s = DDSketch(relative_accuracy=0.01)   # default: 1% relative error
s.add(12.3)
s.add(45.6)

s.quantile(0.5)                        # -> float | None
s.count, s.sum, s.min, s.max

s2 = DDSketch(relative_accuracy=0.01)
s2.add(100.0)
s.merge(s2)                            # in-place, requires matching config

s3 = s.copy()
data = s.to_bytes()
restored = DDSketch.from_bytes(data, relative_accuracy=0.01)
```

`add`/`quantile`/`get_quantile_value`/`merge`/`count`/`sum`/`min`/`max`
match `ddsketch.DDSketch` directly. Differences: no `weight` param on
`add`, constructor args and serialization format differ, `avg` is an added
convenience property.

## Benchmarks

Single-threaded, release build, `rddsketch` vs. `ddsketch`:

| n | rddsketch | ddsketch | speedup |
|---|---|---|---|
| 10,000 | 0.001s | 0.012s | 14.9x |
| 100,000 | 0.009s | 0.069s | 7.4x |
| 1,000,000 | 0.084s | 0.642s | 7.6x |
| 10,000,000 | 0.795s | 6.741s | 8.5x |

Quantile accuracy is identical (same algorithm). Memory usage is similar
for a single sketch; for many independent sketches `rddsketch` uses
meaningfully less. Full numbers and methodology:
[`benchmarks/results.md`](./benchmarks/results.md).

## Design notes

- **Algorithm**: [`sketches-ddsketch`](https://crates.io/crates/sketches-ddsketch)
  does the real work; this crate validates inputs and wraps it for Python.
- **Bin store**: dense, collapsing, bounded by `max_num_bins` (default
  2048, matching `LogCollapsingLowestDenseDDSketch`) — not the unbounded
  `ddsketch.DDSketch`.
- **Serialization**: `to_bytes()`/`from_bytes()` use DataDog's
  Java-compatible binary encoding unmodified. `from_bytes()` needs
  `relative_accuracy` passed back in — it can't be recovered from the
  bytes alone.
- **No `weight` param**: the underlying store counts unweighted.
