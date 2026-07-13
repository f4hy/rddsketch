"""Worker for bench_memory_many_sketches.py: builds k sketches, prints peak RSS.

Usage: python _memory_worker_many.py <rddsketch|ddsketch> <k>
"""

from __future__ import annotations

import random
import sys

from _bench_common import lognormal_values, peak_rss_kb, sketch_class


def main() -> None:
    impl, k = sys.argv[1], int(sys.argv[2])
    cls = sketch_class(impl)
    rng = random.Random(11)

    sketches = []
    for _ in range(k):
        s = cls(relative_accuracy=0.01)
        for v in lognormal_values(50, rng):
            s.add(v)
        sketches.append(s)

    print(peak_rss_kb())


if __name__ == "__main__":
    main()
