"""순간미분(포인트별 미분) — 계산과 그래프 (derivative.py / figure_derivative.py)."""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from fet_app.constants import DEFAULTS
from fet_app.curves import OutputBlock, OutputCurve, TransferCurve
from fet_app.derivative import (
    TRANSFER_MODES, moving_average, output_series, pointwise, transfer_series,
)
from fet_app.figure_derivative import (
    output_derivative_figure, transfer_derivative_figure,
)
from fet_app.metrics import transfer_metrics
from fet_app.params import DeviceParams

PARAMS = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)


def _transfer(dual=True):
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = -np.maximum(2e-8 * (v_g + 12.0) ** 2 * (v_g < -12.0), 1e-12)
    fwd = pd.DataFrame({"V_G": v_g, "I_G": np.full_like(v_g, 1e-11), "I_D": i_d})
    rev = fwd.iloc[::-1].reset_index(drop=True) if dual else None
    return TransferCurve(forward=fwd, reverse=rev, v_ds=-60.0, dual=dual)


def _output():
    v_d = np.arange(0, -61, -1, dtype=float)
    block = OutputBlock(v_g=-20.0, forward=pd.DataFrame({
        "V_D": v_d, "I_D": -1e-6 * np.tanh(v_d / -20.0), "I_G": np.full_like(v_d, 1e-12),
    }), reverse=None)
    return OutputCurve(blocks=[block])


def _settings(kind="transfer", **deriv):
    s = {
        "geom": copy.deepcopy(DEFAULTS[f"{kind}_geom"]),
        "style": copy.deepcopy(DEFAULTS["style"]),
        "axes": copy.deepcopy(DEFAULTS[f"{kind}_axes"]),
        "trace": copy.deepcopy(DEFAULTS[f"{kind}_style"]),
        "insets": copy.deepcopy(DEFAULTS["insets"]),
        "deriv": copy.deepcopy(DEFAULTS["derivative"]),
    }
    s["deriv"].update(deriv)
    return s


# ---------------- 계산 ----------------

def test_pointwise_matches_the_analytic_slope():
    x = np.linspace(0.0, 10.0, 101)
    assert np.allclose(pointwise(x, 3.0 * x + 5.0), 3.0)


def test_pointwise_handles_repeated_x_without_dividing_by_zero():
    """측정기가 반환점에서 같은 전압을 두 번 찍는 경우 — inf 가 나오면 안 된다."""
    x = np.array([0.0, 1.0, 1.0, 2.0, 3.0])
    d = pointwise(x, np.array([0.0, 2.0, 2.0, 4.0, 6.0]))
    assert np.isnan(d[2])
    assert np.allclose(d[[0, 1, 3, 4]], 2.0)


def test_pointwise_returns_all_nan_for_too_few_points():
    assert np.all(np.isnan(pointwise([1.0], [2.0])))


def test_moving_average_keeps_the_end_points_intact():
    """끝에서 값이 눌리면(창 밖의 0 을 끌어오면) 그 구간 미분이 통째로 틀어진다."""
    y = np.full(11, 5.0)
    assert np.allclose(moving_average(y, 5), 5.0)


def test_moving_average_preserves_a_straight_line_including_the_ends():
    """FIX: 잘린 창의 평균은 끝 h 개 점에서 기울기를 절반으로 만든다 (직선
    데이터에서 1E-6 이 5E-7 로 나왔다). 점대칭 패딩이라 1차 추세는 그대로다."""
    y = np.arange(20.0) * 1e-6
    smoothed = moving_average(y, 9)
    assert np.allclose(smoothed, y)
    assert np.allclose(pointwise(np.arange(20.0), smoothed), 1e-6)


def test_moving_average_is_a_no_op_for_window_one():
    y = np.array([1.0, 9.0, 2.0])
    assert np.allclose(moving_average(y, 1), y)


def test_pointwise_mu_matches_the_saturation_mobility_formula():
    """포인트별 μ 는 §2.1 의 식에 fit 기울기 대신 각 점의 기울기를 넣은 것이다 —
    fit 구간 안에서는 μ_sat 과 같은 크기가 나와야 한다."""
    c = _transfer(dual=False)
    m = transfer_metrics(c, PARAMS)
    v, mu = transfer_series(c.forward, "mu", PARAMS, 1)
    inside = (v >= min(m.fit.v_start, m.fit.v_end)) & (v <= max(m.fit.v_start, m.fit.v_end))
    assert abs(np.nanmedian(mu[inside]) - m.mu_sat) / m.mu_sat < 0.25


def test_pointwise_mu_needs_complete_device_params():
    c = _transfer(dual=False)
    assert transfer_series(c.forward, "mu", DeviceParams(), 1) is None
    # 파라미터가 필요 없는 모드는 그대로 나온다.
    assert transfer_series(c.forward, "gm", DeviceParams(), 1) is not None


def test_transfer_modes_are_all_non_negative():
    """부호는 극성에 따라 뒤집히므로 크기만 그린다 (log 축으로도 볼 수 있어야 한다)."""
    c = _transfer(dual=False)
    for mode in TRANSFER_MODES:
        v, y = transfer_series(c.forward, mode, PARAMS, 1)
        assert np.all(y[np.isfinite(y)] >= 0)


def test_output_series_peaks_in_the_linear_region():
    """g_d 는 원점 근처(선형영역)에서 가장 크고 포화영역에서 0 으로 간다."""
    b = _output().blocks[0]
    v, g = output_series(b.forward, 1)
    near_zero = np.nanmax(g[np.abs(v) < 5])
    deep = np.nanmax(g[v < -50])
    assert near_zero > deep * 5


# ---------------- 그래프 ----------------

def test_transfer_derivative_figure_draws_both_branches():
    c = _transfer(dual=True)
    fig = transfer_derivative_figure(c, PARAMS, _settings(), 1.0)
    dashes = [t.line.dash for t in fig.data]
    assert dashes == ["solid", "dash"]     # 진단용 그래프라 방향을 선으로 구분한다
    assert fig.layout.yaxis.title.text == "μ (cm<sup>2</sup>/Vs)"
    assert fig.layout.xaxis.title.text == "V<sub>G</sub> (V)"


def test_transfer_derivative_figure_follows_the_mode():
    c = _transfer(dual=False)
    fig = transfer_derivative_figure(c, PARAMS, _settings(transfer_mode="gm"), 1.0)
    assert "g" in fig.layout.yaxis.title.text
    assert fig.layout.yaxis.type == "linear"
    log_fig = transfer_derivative_figure(c, PARAMS, _settings(y_type="log"), 1.0)
    assert log_fig.layout.yaxis.type == "log"


def test_transfer_derivative_figure_is_empty_without_params_in_mu_mode():
    """UI 가 먼저 막지만, 그림 쪽도 조용히 비어 있어야지 터지면 안 된다."""
    c = _transfer(dual=False)
    fig = transfer_derivative_figure(c, DeviceParams(), _settings(), 1.0)
    assert not fig.data


def test_output_derivative_figure_keeps_the_block_colors_and_legend():
    fig = output_derivative_figure(_output(), _settings("output"), 1.0)
    assert len(fig.data) == 1
    assert fig.layout.yaxis.title.text.startswith("|g")
    # V_G 레전드 스와치(선 shape) + 라벨 주석이 그대로 붙는다.
    assert any(sh.type == "line" for sh in fig.layout.shapes)
    assert any("V<sub>G</sub>" in (a.text or "") for a in fig.layout.annotations)


def test_derivative_figures_scale_with_k():
    c = _transfer(dual=False)
    full = transfer_derivative_figure(c, PARAMS, _settings(), 1.0)
    half = transfer_derivative_figure(c, PARAMS, _settings(), 0.5)
    assert half.layout.width == full.layout.width // 2
    assert half.layout.yaxis.title.font.size == full.layout.yaxis.title.font.size // 2


def test_smoothing_tames_noise_without_moving_the_curve_off_scale():
    rng = np.random.default_rng(0)
    v = np.arange(0.0, 60.0, 0.5)
    noisy = pd.DataFrame({
        "V_G": v, "I_G": np.zeros_like(v),
        "I_D": 1e-6 * v + rng.normal(0, 2e-8, v.size),
    })
    _v, raw = transfer_series(noisy, "gm", PARAMS, 1)
    _v, smoothed = transfer_series(noisy, "gm", PARAMS, 9)
    assert np.nanstd(smoothed) < np.nanstd(raw)
    assert abs(np.nanmedian(smoothed) - 1e-6) < abs(np.nanmedian(raw) - 1e-6) + 1e-7
