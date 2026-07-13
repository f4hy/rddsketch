# Benchmark results

Machine / environment:

- CPU: Intel(R) Xeon(R) W-2123 @ 3.60GHz (8 threads), Linux 7.1.3-arch1-2 x86_64
- Python: 3.14.6
- Rust: rustc 1.97.0
- `rddsketch`: 0.1.0 (this commit), wrapping `sketches-ddsketch` 0.4.0
- `ddsketch` (DataDog's official package): 3.0.1

Release build (`maturin develop --release`), single run, single-threaded,
no warmup. Directional, not statistically rigorous.

## Insert throughput

`python benchmarks/bench_insert.py`, log-normal ("latency-shaped") data:

| n | rddsketch | ddsketch | speedup |
|---|---|---|---|
| 10,000 | 0.001s | 0.012s | 14.9x |
| 100,000 | 0.009s | 0.069s | 7.4x |
| 1,000,000 | 0.084s | 0.642s | 7.6x |
| 10,000,000 | 0.795s | 6.741s | 8.5x |

7-15x faster. `ddsketch.add()` is one `math.log` call plus a few
list/dict ops, so there's less pure-Python overhead per call for Rust to
strip out compared to e.g. a hash-heavy sketch.

## Quantile accuracy + query speed

`python benchmarks/bench_accuracy.py`, 1,000,000 log-normal samples,
`relative_accuracy=0.01`:

| q | rddsketch error | ddsketch error | rddsketch query | ddsketch query |
|---|---|---|---|---|
| 0.5 | 0.924% | 0.924% | 0.000004s | 0.000035s |
| 0.9 | 0.857% | 0.857% | 0.000002s | 0.000027s |
| 0.99 | 0.804% | 0.804% | 0.000001s | 0.000026s |
| 0.999 | 0.289% | 0.289% | 0.000001s | 0.000027s |

Identical accuracy (same algorithm). Insert was 0.103s (`rddsketch`) vs.
0.683s (`ddsketch`), ~6.6x. Queries are ~10-25x faster, but at microsecond
magnitudes that's mostly fixed call overhead, not algorithmic cost.

## Memory: one sketch, many inserts

`python benchmarks/bench_memory.py` -- peak RSS (`resource.ru_maxrss`),
each `(impl, n)` in its own subprocess, values streamed from a generator
(a materialized list would itself dominate the measurement):

| n | rddsketch (MB) | ddsketch (MB) | ratio |
|---|---|---|---|
| 10,000 | 15.0 | 15.0 | 1.0x |
| 100,000 | 15.0 | 15.0 | 1.0x |
| 1,000,000 | 15.0 | 15.0 | 1.0x |
| 10,000,000 | 15.0 | 15.0 | 1.0x |

No difference, and that's real, not a bug: DDSketch's memory scales with
*value range*, not sample count. Log-normal data has a bounded range, so
both implementations stay near the ~15MB process baseline regardless of
`n`. Algorithm-level, not implementation-level.

## Memory: many independent sketches

`python benchmarks/bench_memory_many_sketches.py` stresses per-*object*
overhead instead, by creating many separate sketches (50 samples each):

| sketches | rddsketch (MB) | ddsketch (MB) | ratio |
|---|---|---|---|
| 100 | 14.9 | 14.9 | 1.0x |
| 1,000 | 15.2 | 18.1 | 1.2x |
| 10,000 | 37.7 | 61.2 | 1.6x |
| 100,000 | 263.2 | 491.7 | 1.9x |

This is where the memory win shows up, growing with sketch count:
`ddsketch.DDSketch` is four `__dict__`-based Python objects (the sketch +
`LogarithmicMapping` + two `DenseStore`s) vs. one flat Rust struct with two
initially-empty `Vec<u64>`s. At 100,000 sketches, `rddsketch` uses about
half the memory.

## Takeaway

One sketch ingesting a lot of samples: `rddsketch` is a **speed** win
(7-15x). Many independent sketches, each lightly populated: it's a speed
*and* **memory** win, and the memory gap widens with sketch count.

## Reproducing

```sh
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
maturin develop --release
python benchmarks/bench_insert.py
python benchmarks/bench_accuracy.py
python benchmarks/bench_memory.py
python benchmarks/bench_memory_many_sketches.py
```
