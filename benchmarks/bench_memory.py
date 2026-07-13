"""Peak process memory: rddsketch vs ddsketch, one sketch, many inserts.

Each (impl, n) is measured via `resource.ru_maxrss` in a fresh subprocess,
since Rust-heap allocations don't go through tracemalloc's allocator.

Usage: python benchmarks/bench_memory.py
"""

from __future__ import annotations

from pathlib import Path

from _bench_common import run_memory_bench

SIZES = [10_000, 100_000, 1_000_000, 10_000_000]
WORKER = Path(__file__).parent / "_memory_worker.py"

if __name__ == "__main__":
    run_memory_bench(WORKER, SIZES, "n")
