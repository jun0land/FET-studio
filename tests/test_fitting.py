import math

import numpy as np
import pytest

from fet_app.constants import FIT_MIN_POINTS, FIT_TIE_TOLERANCE
from fet_app.fitting import (
    _best_window_by_r2, auto_fit_sqrt, fit_window, linear_fit, manual_fit_sqrt,
)


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
    """후보 영역 안이 완전한 직선이면 모든 창이 R^2=1 동점 -> 가장 긴 창을 고른다.

    off 바닥을 1e-12 로 깔아 on-영역 필터(|I_D| > 100 x I_off)가 실제로 동작하게 한 뒤,
    통과한 50점 중 최대 허용 창(50 x 0.60 = 30점)이 선택되는지 정확한 값으로 본다.
    """
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = -np.maximum(2e-8 * (v_g + 10.0) ** 2 * (v_g < -10), 1e-12)
    fit = auto_fit_sqrt(v_g, i_d)
    assert fit is not None
    assert fit.r2 > 0.9999
    assert fit.n_points == 30


def test_auto_fit_on_region_filter_survives_an_exact_zero_reading():
    """|I_D| 에 정확히 0 이 한 점 섞여도 on-영역 필터가 무력화되면 안 된다.

    I_off 를 0 으로 잡으면 임계가 0 이 되어 노이즈 바닥까지 후보에 들어온다.
    0 을 제외하고 최솟값을 구해야 한다.
    """
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = -np.maximum(2e-8 * (v_g + 12.0) ** 2 * (v_g < -12), 1e-12)
    i_d[5] = 0.0                      # 계측 분해능/클램프로 0 이 찍힌 점
    fit = auto_fit_sqrt(v_g, i_d)
    assert fit is not None
    # off 구간(V_G > -12)이 fit 에 끌려들어오지 않아야 한다
    assert max(fit.v_start, fit.v_end) <= -12.0
    assert math.isclose(-fit.intercept / fit.slope, -12.0, abs_tol=0.3)


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


def _brute_force_best(x, y, w_min, w_max):
    """_best_window_by_r2 의 참조 구현 — 창마다 np.polyfit 을 다시 돌린다.

    최적화 전의 auto_fit_sqrt 이중 루프와 같은 비교 순서/규칙.
    """
    n = x.size
    best = None
    best_r2 = 0.0
    best_n = 0
    for w in range(w_min, w_max + 1):
        for s in range(0, n - w + 1):
            _slope, _icept, r2 = linear_fit(x[s:s + w], y[s:s + w])
            if best is None:
                best, best_r2, best_n = (s, w), r2, w
            elif r2 > best_r2 + FIT_TIE_TOLERANCE:
                best, best_r2, best_n = (s, w), r2, w
            elif abs(r2 - best_r2) <= FIT_TIE_TOLERANCE and w > best_n:
                best, best_r2, best_n = (s, w), r2, w
            elif w == best_n and r2 > best_r2:
                best, best_r2, best_n = (s, w), r2, w
    return best


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_fast_window_search_matches_brute_force(seed):
    """누적합 O(1) 탐색이 창마다 polyfit 하는 참조 구현과 같은 창을 고른다.

    누적합 차분은 큰 수끼리 빼는 만큼 자리수 손실 위험이 있어(catastrophic
    cancellation), "선택되는 창이 바뀌지 않는다"를 직접 못박아 둔다.
    """
    rng = np.random.default_rng(seed)
    v_g = np.arange(0, -60, -1, dtype=float)
    i_d = _square_law(v_g, v_th=-8.0, k=2e-8)
    i_d = i_d * (1 + rng.normal(0, 0.02, i_d.size))
    y = np.sqrt(np.abs(i_d))
    assert _best_window_by_r2(v_g, y, FIT_MIN_POINTS, 30) == \
        _brute_force_best(v_g, y, FIT_MIN_POINTS, 30)


def test_fast_window_search_matches_brute_force_on_example(transfer_files):
    """실제 계측 데이터(작은 sqrt|I_D| x 큰 V_G)에서도 창 선택이 같아야 한다."""
    from fet_app import curves, parsing

    path = transfer_files[0]
    blob = path.read_bytes()
    sheets, engine = parsing.load_sheets(blob)
    info = parsing.SettingsInfo(
        parsing.parse_settings(parsing.settings_frame(blob, sheets, engine)))
    df = curves.build_transfer(parsing.data_sheet(sheets), info).forward

    v_g = df["V_G"].to_numpy(dtype=float)
    y = np.sqrt(np.abs(df["I_D"].to_numpy(dtype=float)))
    assert _best_window_by_r2(v_g, y, FIT_MIN_POINTS, 25) == \
        _brute_force_best(v_g, y, FIT_MIN_POINTS, 25)


def test_fast_window_search_degenerate_x_scores_zero():
    """x 가 상수인 창은 linear_fit 규약대로 R^2=0 -> 전부 동점이라 가장 긴 창."""
    x = np.zeros(30)
    y = np.arange(30, dtype=float)
    assert _best_window_by_r2(x, y, FIT_MIN_POINTS, 18) == (0, 18)


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
