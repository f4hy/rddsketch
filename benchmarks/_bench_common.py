"""Shared helpers for the benchmark scripts."""

from __future__ import annotations

import random
import resource
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path


def official_ddsketch_class():
    """The official `ddsketch.DDSketch`, or None if it isn't installed."""
    try:
        from ddsketch import DDSketch

        return DDSketch
    except ImportError:
        return None


def sketch_class(impl: str):
    if impl == "rddsketch":
        from rddsketch import DDSketch

        return DDSketch
    if impl == "ddsketch":
        from ddsketch import DDSketch

        return DDSketch
    raise ValueError(f"unknown impl {impl!r}")


def lognormal_values(n: int, rng: random.Random) -> Iterator[float]:
    # Log-normal-ish latency distribution: mostly small, long tail.
    for _ in range(n):
        yield rng.lognormvariate(0, 1)


def peak_rss_kb() -> int:
    """Peak RSS of the current process, in KB."""
    peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        peak_kb //= 1024
    return peak_kb


def measure_subprocess(worker: Path, impl: str, arg: int) -> int:
    """Peak RSS (KB) of a fresh `python worker impl arg` run."""
    out = subprocess.run(
        [sys.executable, str(worker), impl, str(arg)],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(out.stdout.strip())


def run_memory_bench(worker: Path, values: list[int], label: str) -> None:
    have_official = official_ddsketch_class() is not None
    print(f"{label:>10} | {'rddsketch (MB)':>15} | {'ddsketch (MB)':>14} | {'ratio':>8}")
    print("-" * 58)
    for v in values:
        r_kb = measure_subprocess(worker, "rddsketch", v)
        d_kb = measure_subprocess(worker, "ddsketch", v) if have_official else None
        r_mb = r_kb / 1024
        if d_kb is not None:
            d_mb = d_kb / 1024
            ratio = d_mb / r_mb
            print(f"{v:>10} | {r_mb:>14.1f} | {d_mb:>13.1f} | {ratio:>7.1f}x")
        else:
            print(f"{v:>10} | {r_mb:>14.1f} | {'skipped':>13} | {'n/a':>8}")
