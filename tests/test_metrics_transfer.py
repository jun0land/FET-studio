import math

import numpy as np
import pandas as pd

from fet_app.curves import TransferCurve
from fet_app.metrics import (
    on_off_ratio, subthreshold_swing, transfer_metrics,
)
from fet_app.params import DeviceParams

# 합성 데이터의 정답값
W_UM, L_UM, EPS_R, D_NM = 1000.0, 50.0, 3.9, 300.0
PARAMS = DeviceParams(w_um=W_UM, l_um=L_UM, eps_r=EPS_R, d_nm=D_NM)
TRUE_MU = 0.05          # cm^2/Vs
TRUE_VTH = -12.0        # V


def _ideal_transfer(v_th=TRUE_VTH, mu=TRUE_MU, floor=1e-12, ss_mv=200.0):
    """I_D = (W/2L) mu C_ox (V_G - V_th)^2, off 쪽은 지수 꼬리를 붙인다."""
    v_g = np.arange(20, -61, -1, dtype=float)
    c_ox = PARAMS.c_ox()
    k = (PARAMS.w_cm() / (2 * PARAMS.l_cm())) * mu * c_ox
    i = np.where(v_g < v_th, k * (v_g - v_th) ** 2, 0.0)
    # 서브스레숄드: V_th 위쪽에서 ss_mv mV/dec 로 감소
    tail_at_vth = k * 1.0
    tail = tail_at_vth * 10.0 ** (-(v_g - v_th) / (ss_mv / 1000.0))
    i = np.maximum(i, np.where(v_g >= v_th, tail, 0.0))
    i = np.maximum(i, floor)
    return v_g, -i  # p-type


def _curve(v_g, i_d, i_g=None):
    df = pd.DataFrame({"V_G": v_g, "I_G": i_g if i_g is not None else np.zeros_like(v_g),
                       "I_D": i_d})
    return TransferCurve(forward=df, reverse=None, v_ds=-60.0, dual=False)


def test_recovers_mobility_and_threshold_within_1_percent():
    v_g, i_d = _ideal_transfer()
    m = transfer_metrics(_curve(v_g, i_d), PARAMS)
    assert m.mu_sat is not None
    assert abs(m.mu_sat - TRUE_MU) / TRUE_MU < 0.01
    assert abs(m.v_th - TRUE_VTH) < 0.3


def test_mobility_scales_with_channel_length():
    """L 을 2배로 하면 mu 도 2배로 나와야 한다 (mu = 2L/(W C_ox) m^2)."""
    v_g, i_d = _ideal_transfer()
    m1 = transfer_metrics(_curve(v_g, i_d), PARAMS)
    p2 = DeviceParams(w_um=W_UM, l_um=L_UM * 2, eps_r=EPS_R, d_nm=D_NM)
    m2 = transfer_metrics(_curve(v_g, i_d), p2)
    assert math.isclose(m2.mu_sat, 2 * m1.mu_sat, rel_tol=1e-9)


def test_on_off_ratio():
    i_d = np.array([-1e-12, -1e-6, -5e-7])
    assert math.isclose(on_off_ratio(i_d), 1e6, rel_tol=1e-9)


def test_on_off_ignores_zeros():
    i_d = np.array([0.0, -1e-12, -1e-6])
    assert math.isclose(on_off_ratio(i_d), 1e6, rel_tol=1e-9)


def test_subthreshold_swing_recovers_synthetic_slope():
    v_g, i_d = _ideal_transfer(ss_mv=200.0)
    ss = subthreshold_swing(v_g, i_d)
    assert ss is not None
    assert abs(ss - 200.0) < 40.0   # 1 V 간격 측정이라 오차 허용


def test_hysteresis_recovers_shift():
    v_g, i_d = _ideal_transfer(v_th=-12.0)
    v_g_r, i_d_r = _ideal_transfer(v_th=-15.0)
    fwd = pd.DataFrame({"V_G": v_g, "I_G": np.zeros_like(v_g), "I_D": i_d})
    rev = pd.DataFrame({"V_G": v_g_r[::-1], "I_G": np.zeros_like(v_g_r),
                        "I_D": i_d_r[::-1]})
    m = transfer_metrics(TransferCurve(forward=fwd, reverse=rev, v_ds=-60.0, dual=True),
                         PARAMS)
    assert m.dv_th is not None
    assert abs(m.dv_th - (-3.0)) < 0.5   # reverse - forward


def test_manual_fit_range_is_honored():
    v_g, i_d = _ideal_transfer()
    m = transfer_metrics(_curve(v_g, i_d), PARAMS, fit_range=(-55.0, -35.0))
    assert m.fit.v_start <= -35.0 and m.fit.v_end >= -55.0


def test_incomplete_params_give_vth_but_no_mobility():
    v_g, i_d = _ideal_transfer()
    m = transfer_metrics(_curve(v_g, i_d), DeviceParams(w_um=None, l_um=50.0,
                                                        eps_r=3.9, d_nm=300.0))
    assert m.v_th is not None
    assert m.mu_sat is None
    assert any("W" in w or "소자" in w for w in m.warnings)


def test_saturation_condition_warning():
    """|V_DS| < |V_G - V_th| 인 구간이 fit 에 들어가면 경고."""
    v_g, i_d = _ideal_transfer()
    c = _curve(v_g, i_d)
    c.v_ds = -20.0   # fit 구간이 V_G -50 근처라 |V_G - V_th| ~ 38 > 20
    m = transfer_metrics(c, PARAMS)
    assert any("포화" in w for w in m.warnings)


def test_real_example_produces_finite_metrics(example_dir):
    from fet_app.grouping import parse_file
    pf = parse_file((example_dir / "1-3 best.xls").read_bytes(), "1-3 best.xls")
    m = transfer_metrics(pf.latest.transfer, PARAMS)
    assert m.v_th is not None and np.isfinite(m.v_th)
    assert m.mu_sat is not None and m.mu_sat > 0
    assert m.on_off is not None and m.on_off > 1
    assert m.fit.r2 > 0.9
