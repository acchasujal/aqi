"""EXP-010 weight contract checks."""
import numpy as np
import pytest

from mumbai_pm25.forecast import combine_forecasts


@pytest.mark.parametrize("weight,expected", [(0.0, 20.0), (0.25, 25.0),
                                             (0.5, 30.0), (0.75, 35.0), (1.0, 40.0)])
def test_weight_formula(weight, expected):
    assert combine_forecasts(20.0, 40.0, weight) == expected


@pytest.mark.parametrize("weight", [-0.1, 1.1, np.nan])
def test_invalid_weight(weight):
    with pytest.raises(ValueError, match="seasonal_weight"):
        combine_forecasts(20.0, 40.0, weight)


def test_fallback_independent_of_weight():
    for weight in (0.0, 0.5, 1.0):
        assert combine_forecasts(None, 40.0, weight) == 40.0
        assert combine_forecasts(20.0, None, weight) == 20.0
        with pytest.raises(ValueError, match="Neither"):
            combine_forecasts(None, None, weight)
