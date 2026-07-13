import pytest

from rddsketch import DDSketch


def test_merge_matches_combined_insert():
    alpha = 0.01
    a = DDSketch(relative_accuracy=alpha)
    b = DDSketch(relative_accuracy=alpha)
    combined = DDSketch(relative_accuracy=alpha)

    for i in range(1, 50_001):
        a.add(float(i))
        combined.add(float(i))
    for i in range(50_001, 100_001):
        b.add(float(i))
        combined.add(float(i))

    a.merge(b)

    assert a.count == combined.count
    assert a.sum == pytest.approx(combined.sum)
    for q in (0.1, 0.5, 0.9):
        assert a.quantile(q) == pytest.approx(combined.quantile(q), rel=1e-6)


def test_merge_into_empty_sketch():
    a = DDSketch()
    b = DDSketch()
    for i in range(1, 101):
        b.add(float(i))

    a.merge(b)
    assert a.count == 100
    assert a.quantile(0.5) == pytest.approx(50.0, rel=0.02)


def test_merge_with_empty_sketch_is_noop():
    a = DDSketch()
    for i in range(1, 101):
        a.add(float(i))
    before = a.quantile(0.5)

    a.merge(DDSketch())
    assert a.count == 100
    assert a.quantile(0.5) == before


def test_merge_is_order_independent():
    a = DDSketch()
    b = DDSketch()
    for i in range(1_000):
        a.add(float(i))
        b.add(float(i + 500))

    merged_ab = a.copy()
    merged_ab.merge(b)

    merged_ba = b.copy()
    merged_ba.merge(a)

    assert merged_ab.count == merged_ba.count
    assert merged_ab.quantile(0.5) == pytest.approx(merged_ba.quantile(0.5))
