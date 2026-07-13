"""Quantile accuracy + query speed: rddsketch vs the official ddsketch package.

Inserts a known latency-shaped dataset into each library and reports
per-quantile error against the true (sorted) value, plus insert/query time.

Usage: python benchmarks/bench_accuracy.py
"""

from __future__ import annotations

import random
import time

from _bench_common import lognormal_values, official_ddsketch_class
from rddsketch import DDSketch as RDDSketch

OfficialDDSketch = official_ddsketch_class()

N = 1_000_000
RELATIVE_ACCURACY = 0.01
QUANTILES = [0.5, 0.9, 0.99, 0.999]


def make_values(n: int) -> list[float]:
    return list(lognormal_values(n, random.Random(42)))


def run(
    name: str, make_sketch, insert, quantile, values: list[float], sorted_values: list[float]
) -> None:
    sketch = make_sketch()

    start = time.perf_counter()
    for v in values:
        insert(sketch, v)
    insert_time = time.perf_counter() - start

    print(f"\n{name}: insert={insert_time:.3f}s")
    print(f"{'q':>7} | {'estimate':>12} | {'true':>12} | {'error':>8} | {'query time':>10}")
    for q in QUANTILES:
        start = time.perf_counter()
        estimate = quantile(sketch, q)
        query_time = time.perf_counter() - start

        true_value = sorted_values[int(q * (len(sorted_values) - 1))]
        error_pct = abs(estimate - true_value) / true_value * 100
        print(
            f"{q:>7} | {estimate:>12.4f} | {true_value:>12.4f} | "
            f"{error_pct:>7.3f}% | {query_time:>9.6f}s"
        )


def main() -> None:
    values = make_values(N)
    sorted_values = sorted(values)

    run(
        "rddsketch",
        lambda: RDDSketch(relative_accuracy=RELATIVE_ACCURACY),
        lambda s, v: s.add(v),
        lambda s, q: s.quantile(q),
        values,
        sorted_values,
    )

    if OfficialDDSketch:
        run(
            "ddsketch",
            lambda: OfficialDDSketch(relative_accuracy=RELATIVE_ACCURACY),
            lambda s, v: s.add(v),
            lambda s, q: s.get_quantile_value(q),
            values,
            sorted_values,
        )
    else:
        print("\nddsketch not installed, skipping")


if __name__ == "__main__":
    main()
