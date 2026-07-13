"""Peak process memory for many independent, lightly-populated sketches.

Stresses per-object overhead rather than per-bin overhead, unlike
bench_memory.py (one giant sketch), which found no difference.

Usage: python benchmarks/bench_memory_many_sketches.py
"""

from __future__ import annotations

from pathlib import Path

from _bench_common import run_memory_bench

COUNTS = [100, 1_000, 10_000, 100_000]
WORKER = Path(__file__).parent / "_memory_worker_many.py"

if __name__ == "__main__":
    run_memory_bench(WORKER, COUNTS, "sketches")
