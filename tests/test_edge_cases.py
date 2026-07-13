import math

import pytest

from rddsketch import DDSketch


def test_empty_sketch():
    s = DDSketch()
    assert s.count == 0
    assert s.quantile(0.5) is None
    assert s.min is None
    assert s.max is None
    assert s.sum is None
    assert s.avg is None


def test_single_value():
    s = DDSketch()
    s.add(42.0)
    assert s.count == 1
    assert s.quantile(0.5) == pytest.approx(42.0, rel=0.01)


@pytest.mark.parametrize("relative_accuracy", [1e-6, 0.01, 0.5, 0.999999])
def test_relative_accuracy_bounds_are_valid(relative_accuracy):
    DDSketch(relative_accuracy=relative_accuracy)


@pytest.mark.parametrize("relative_accuracy", [0.0, 1.0, -0.1, 1.5])
def test_relative_accuracy_out_of_range_raises(relative_accuracy):
    with pytest.raises(ValueError):
        DDSketch(relative_accuracy=relative_accuracy)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_add_raises(bad_value):
    s = DDSketch()
    with pytest.raises(ValueError):
        s.add(bad_value)


@pytest.mark.parametrize("q", [-0.1, 1.1])
def test_quantile_out_of_range_raises(q):
    s = DDSketch()
    s.add(1.0)
    with pytest.raises(ValueError):
        s.quantile(q)


def test_quantile_boundaries():
    s = DDSketch()
    s.add(1.0)
    assert s.quantile(0.0) == pytest.approx(1.0, rel=0.01)
    assert s.quantile(1.0) == pytest.approx(1.0, rel=0.01)
    assert not math.isnan(s.quantile(0.5))


def test_max_num_bins_zero_raises():
    with pytest.raises(ValueError):
        DDSketch(max_num_bins=0)


def test_min_value_nonpositive_raises():
    with pytest.raises(ValueError):
        DDSketch(min_value=0.0)
    with pytest.raises(ValueError):
        DDSketch(min_value=-1.0)


def test_merge_requires_matching_config():
    a = DDSketch(relative_accuracy=0.01)
    b = DDSketch(relative_accuracy=0.02)
    with pytest.raises(ValueError):
        a.merge(b)


def test_len_reflects_bin_capacity():
    s = DDSketch()
    assert len(s) == 0
    s.add(1.0)
    assert len(s) > 0
