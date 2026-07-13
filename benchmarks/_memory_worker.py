"""Worker for bench_memory.py: builds one sketch with n values, prints peak RSS.

Usage: python _memory_worker.py <rddsketch|ddsketch> <n>
"""

from __future__ import annotations

import random
import sys

from _bench_common import lognormal_values, peak_rss_kb, sketch_class


def main() -> None:
    impl, n = sys.argv[1], int(sys.argv[2])
    sketch = sketch_class(impl)(relative_accuracy=0.01)
    for v in lognormal_values(n, random.Random(7)):
        sketch.add(v)
    print(peak_rss_kb())


if __name__ == "__main__":
    main()
