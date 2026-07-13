import pytest

from rddsketch import DDSketch

try:
    from ddsketch import DDSketch as OfficialDDSketch
except ImportError:
    OfficialDDSketch = None


@pytest.mark.parametrize("n", [1_000, 10_000, 100_000])
def test_quantile_within_relative_accuracy_uniform(n):
    alpha = 0.01
    s = DDSketch(relative_accuracy=alpha)
    values = list(range(1, n + 1))
    for v in values:
        s.add(float(v))

    values.sort()
    for q in (0.01, 0.1, 0.5, 0.9, 0.99):
        # Matches the sketch's own rank definition (floor(q * (count - 1))),
        # not a rounded index -- see sketches_ddsketch::DDSketch::quantile.
        expected = values[int(q * (n - 1))]
        got = s.quantile(q)
        error = abs(got - expected) / expected
        assert error <= alpha * 1.2, f"q={q} got={got} expected={expected} error={error:.3%}"


def test_negative_and_zero_values():
    s = DDSketch(relative_accuracy=0.01)
    for v in range(-500, 501):
        s.add(float(v))

    assert abs(s.quantile(0.5)) < 5.0
    assert abs(s.quantile(0.0) - (-500.0)) / 500.0 < 0.02
    assert abs(s.quantile(1.0) - 500.0) / 500.0 < 0.02


def test_count_sum_min_max_avg():
    s = DDSketch(relative_accuracy=0.01)
    for v in (1.0, 2.0, 3.0, 4.0):
        s.add(v)

    assert s.count == 4
    assert s.sum == pytest.approx(10.0)
    assert s.min == pytest.approx(1.0)
    assert s.max == pytest.approx(4.0)
    assert s.avg == pytest.approx(2.5)


@pytest.mark.skipif(OfficialDDSketch is None, reason="ddsketch not installed")
def test_quantile_close_to_official_ddsketch():
    n = 50_000
    values = [float(i) for i in range(1, n + 1)]

    rs = DDSketch(relative_accuracy=0.01)
    os_ = OfficialDDSketch(relative_accuracy=0.01)
    for v in values:
        rs.add(v)
        os_.add(v)

    for q in (0.1, 0.5, 0.9, 0.99):
        r = rs.quantile(q)
        o = os_.get_quantile_value(q)
        assert abs(r - o) / o < 0.02, f"q={q} rddsketch={r} ddsketch={o}"
