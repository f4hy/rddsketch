import pytest

from rddsketch import DDSketch


def test_round_trip_preserves_stats():
    s = DDSketch(relative_accuracy=0.01)
    for i in range(5_000):
        s.add(float(i))

    restored = DDSketch.from_bytes(s.to_bytes(), s.relative_accuracy)

    assert restored.count == s.count
    assert restored.sum == pytest.approx(s.sum)
    assert restored.min == pytest.approx(s.min)
    assert restored.max == pytest.approx(s.max)
    assert restored.relative_accuracy == pytest.approx(s.relative_accuracy)
    assert restored.quantile(0.5) == pytest.approx(s.quantile(0.5))


def test_round_trip_empty_sketch():
    s = DDSketch()
    restored = DDSketch.from_bytes(s.to_bytes(), s.relative_accuracy)
    assert restored.count == 0
    assert restored.quantile(0.5) is None


def test_round_trip_with_negative_and_zero_values():
    s = DDSketch()
    for v in (-3.0, -2.0, -1.0, 0.0, 0.0, 1.0, 2.0, 3.0):
        s.add(v)

    restored = DDSketch.from_bytes(s.to_bytes(), s.relative_accuracy)
    assert restored.count == s.count
    assert restored.quantile(0.5) == pytest.approx(s.quantile(0.5))


def test_from_bytes_rejects_truncated_buffer():
    with pytest.raises(ValueError):
        DDSketch.from_bytes(b"short", 0.01)


def test_from_bytes_rejects_invalid_relative_accuracy():
    s = DDSketch()
    s.add(1.0)
    with pytest.raises(ValueError):
        DDSketch.from_bytes(s.to_bytes(), 0.0)
