"""Insert-throughput benchmark: rddsketch vs the official ddsketch package.

Usage: python benchmarks/bench_insert.py
"""

from __future__ import annotations

import random
import time

from _bench_common import lognormal_values, official_ddsketch_class
from rddsketch import DDSketch as RDDSketch

OfficialDDSketch = official_ddsketch_class()

SIZES = [10_000, 100_000, 1_000_000, 10_000_000]
RELATIVE_ACCURACY = 0.01


def make_values(n: int) -> list[float]:
    return list(lognormal_values(n, random.Random(1234)))


def bench(make_sketch, values: list[float]) -> float:
    s = make_sketch()
    start = time.perf_counter()
    for v in values:
        s.add(v)
    return time.perf_counter() - start


def main() -> None:
    print(f"{'n':>10} | {'rddsketch':>10} | {'ddsketch':>12} | {'speedup':>8}")
    print("-" * 50)
    for n in SIZES:
        values = make_values(n)
        r_t = bench(lambda: RDDSketch(relative_accuracy=RELATIVE_ACCURACY), values)
        d_t = (
            bench(lambda: OfficialDDSketch(relative_accuracy=RELATIVE_ACCURACY), values)
            if OfficialDDSketch
            else float("nan")
        )
        speedup = d_t / r_t if OfficialDDSketch else float("nan")
        print(f"{n:>10} | {r_t:>9.3f}s | {d_t:>11.3f}s | {speedup:>7.1f}x")


if __name__ == "__main__":
    main()
