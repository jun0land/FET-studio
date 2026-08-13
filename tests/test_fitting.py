import math

import numpy as np

from fet_app.constants import FIT_MIN_POINTS
from fet_app.fitting import auto_fit_sqrt, fit_window, linear_fit, manual_fit_sqrt


def _square_law(v_g, v_th=-10.0, k=2e-8, floor=1e-12):
    """이상적 p-type 포화 전류. V_G > V_th 에서는 off 바닥으로 깔린다."""
    on = v_g < v_th
    i = np.full_like(v_g, floor, dtype=float)
    i[on] = k * (v_g[on] - v_th) ** 2
    return -i  # p-type 이라 음수


def test_linear_fit_exact():
    x = np.arange(10, dtype=float)
    y = 3.0 * x - 4.0
    slope, intercept, r2 = linear_fit(x, y)
    assert math.isclose(slope, 3.0, rel_tol=1e-12)
    assert math.isclose(intercept, -4.0, abs_tol=1e-12)
    assert math.isclose(r2, 1.0, abs_tol=1e-12)


def test_linear_fit_degenerate_returns_zero_r2():
    x = np.zeros(5)
    y = np.arange(5, dtype=float)
    _slope, _intercept, r2 = linear_fit(x, y)
    assert r2 == 0.0


def test_fit_window_records_bounds():
    x = np.arange(20, dtype=float)
    y = 2.0 * x
    fit = fit_window(x, y, 5, 15)
    assert fit.i_start == 5 and fit.i_end == 15 and fit.n_points == 10
    assert fit.v_start == 5.0 and fit.v_end == 14.0


def test_auto_fit_recovers_ideal_square_law():
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = _square_law(v_g, v_th=-10.0, k=2e-8)
    fit = auto_fit_sqrt(v_g, i_d)
    assert fit is not None
    assert fit.r2 > 0.9999
    # x 절편 = V_th
    assert math.isclose(-fit.intercept / fit.slope, -10.0, abs_tol=0.2)
    assert fit.n_points >= FIT_MIN_POINTS


def test_auto_fit_prefers_longer_window_on_tie():
    """완벽한 직선이면 어느 창이든 R^2=1 -> 가장 긴 창을 골라야 한다."""
    v_g = np.arange(0, -61, -1, dtype=float)
    i_d = -((v_g * 1e-5) ** 2)
    fit = auto_fit_sqrt(v_g, i_d)
    assert fit is not None
    n_candidates = v_g.size
    assert fit.n_points >= int(n_candidates * 0.55)


def test_auto_fit_survives_noise():
    rng = np.random.default_rng(0)
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = _square_law(v_g, v_th=-10.0, k=2e-8)
    i_d = i_d * (1 + rng.normal(0, 0.01, i_d.size))
    fit = auto_fit_sqrt(v_g, i_d)
    assert fit is not None
    assert math.isclose(-fit.intercept / fit.slope, -10.0, abs_tol=1.5)


def test_auto_fit_returns_none_when_all_noise_floor():
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = np.full(v_g.size, -1e-12)
    assert auto_fit_sqrt(v_g, i_d) is None


def test_manual_fit_uses_given_range():
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = _square_law(v_g, v_th=-10.0, k=2e-8)
    fit = manual_fit_sqrt(v_g, i_d, v_lo=-50.0, v_hi=-30.0)
    assert fit is not None
    assert fit.v_start <= -30.0 and fit.v_end >= -50.0
    assert fit.n_points == 21


def test_manual_fit_too_few_points_returns_none():
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = _square_law(v_g)
    assert manual_fit_sqrt(v_g, i_d, v_lo=-31.0, v_hi=-30.0) is None
