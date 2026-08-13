"""성능 지표 계산 (스펙 §3). 모든 식은 MANUAL.md 에 그대로 문서화된다."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from fet_app.constants import (
    DEFAULT_THRESHOLDS, DIAG_ORIGIN_FRACTION, DIAG_SLOPE_POINTS, SS_WINDOW,
)
from fet_app.curves import OutputCurve, TransferCurve
from fet_app.fitting import FitResult, auto_fit_sqrt, linear_fit, manual_fit_sqrt
from fet_app.params import DeviceParams


def threshold_and_mobility(fit: FitResult,
                           p: DeviceParams) -> tuple[float | None, float | None]:
    """V_th = -b/m,  mu_sat = (2L / (W C_ox)) m^2   (스펙 §3.2)."""
    if fit is None or fit.slope == 0:
        return None, None
    v_th = -fit.intercept / fit.slope
    if not p.is_complete():
        return float(v_th), None
    mu = (2.0 * p.l_cm() / (p.w_cm() * p.c_ox())) * (fit.slope ** 2)
    return float(v_th), float(mu)


def on_off_ratio(i_d) -> float | None:
    """max|I_D| / min|I_D|, 0 은 제외 (스펙 §3.4)."""
    a = np.abs(np.asarray(i_d, dtype=float))
    a = a[np.isfinite(a) & (a > 0)]
    if a.size < 2:
        return None
    lo = float(np.min(a))
    return float(np.max(a) / lo) if lo > 0 else None


def subthreshold_swing(v_g, i_d, window: int = SS_WINDOW) -> float | None:
    """SS = min(dV_G / d log10|I_D|) [mV/dec]  (스펙 §3.5).

    구현은 등가식 SS = 1000 / max|d log10|I_D| / dV_G| 를 쓴다.
    탐색 범위는 I_off*10 ~ I_on/10 의 서브스레숄드 구간, window 점 이동 회귀.
    """
    v = np.asarray(v_g, dtype=float)
    a = np.abs(np.asarray(i_d, dtype=float))
    ok = np.isfinite(v) & np.isfinite(a) & (a > 0)
    v, a = v[ok], a[ok]
    if v.size < window:
        return None

    i_off, i_on = float(np.min(a)), float(np.max(a))
    if i_on <= i_off * 100:
        return None
    band = (a > i_off * 10) & (a < i_on / 10)
    idx = np.flatnonzero(band)
    if idx.size < window:
        return None

    y = np.log10(a)
    best_slope = 0.0
    for s in range(idx[0], idx[-1] - window + 2):
        xs, ys = v[s:s + window], y[s:s + window]
        slope, _intercept, _r2 = linear_fit(xs, ys)
        best_slope = max(best_slope, abs(slope))
    if best_slope <= 0:
        return None
    return float(1000.0 / best_slope)


@dataclass
class TransferMetrics:
    v_th: float | None = None
    mu_sat: float | None = None
    on_off: float | None = None
    ss_mv_dec: float | None = None
    dv_th: float | None = None
    v_th_reverse: float | None = None
    mu_sat_reverse: float | None = None
    c_ox: float | None = None
    fit: FitResult | None = None
    fit_reverse: FitResult | None = None
    warnings: list[str] = field(default_factory=list)


def _fit_branch(df, fit_range: tuple[float, float] | None) -> FitResult | None:
    v_g = df["V_G"].to_numpy(dtype=float)
    i_d = df["I_D"].to_numpy(dtype=float)
    if fit_range is not None:
        return manual_fit_sqrt(v_g, i_d, fit_range[0], fit_range[1])
    return auto_fit_sqrt(v_g, i_d)


def transfer_metrics(curve: TransferCurve, p: DeviceParams,
                     fit_range: tuple[float, float] | None = None) -> TransferMetrics:
    m = TransferMetrics()
    if curve is None or curve.forward.empty:
        m.warnings.append("transfer 데이터가 없습니다.")
        return m

    if p.is_complete():
        m.c_ox = p.c_ox()
    else:
        m.warnings.append("소자 파라미터(W, L, ε_r, d)가 비어 있어 μ_sat 을 계산할 수 없습니다.")

    fwd = curve.forward
    m.on_off = on_off_ratio(fwd["I_D"].to_numpy(dtype=float))
    m.ss_mv_dec = subthreshold_swing(fwd["V_G"].to_numpy(dtype=float),
                                     fwd["I_D"].to_numpy(dtype=float))

    m.fit = _fit_branch(fwd, fit_range)
    if m.fit is None:
        m.warnings.append(
            "fit 구간을 찾지 못했습니다. on 영역이 너무 짧거나 노이즈가 큽니다. "
            "fit 패널에서 V_G 범위를 직접 지정해 보세요."
        )
        return m

    m.v_th, m.mu_sat = threshold_and_mobility(m.fit, p)

    if m.fit.r2 < 0.99:
        m.warnings.append(f"fit R² = {m.fit.r2:.4f} 로 낮습니다. 구간을 확인하세요.")

    # 포화 조건 |V_DS| >= |V_G - V_th| 검사 (스펙 §3.8)
    if curve.v_ds is not None and m.v_th is not None:
        worst = max(abs(m.fit.v_start - m.v_th), abs(m.fit.v_end - m.v_th))
        if worst > abs(curve.v_ds):
            m.warnings.append(
                f"fit 구간에서 포화 조건이 깨집니다: |V_G − V_th| 최대 {worst:.1f} V "
                f"> |V_DS| {abs(curve.v_ds):.1f} V. μ_sat 이 과대평가될 수 있습니다."
            )

    if curve.reverse is not None and not curve.reverse.empty:
        m.fit_reverse = _fit_branch(curve.reverse, fit_range)
        if m.fit_reverse is not None:
            m.v_th_reverse, m.mu_sat_reverse = threshold_and_mobility(m.fit_reverse, p)
            if m.v_th is not None and m.v_th_reverse is not None:
                m.dv_th = float(m.v_th_reverse - m.v_th)
        else:
            m.warnings.append("reverse branch 의 fit 구간을 찾지 못해 ΔV_th 를 계산하지 못했습니다.")

    return m


# ---------------- Output 진단 (스펙 §3.7) ----------------


@dataclass
class BlockDiagnostics:
    v_g: float
    zero_offset: float | None = None       # |I_D(V_D=0)| / max|I_D|
    linearity_r2: float | None = None      # 원점 구간 선형 fit R^2
    saturation_ratio: float | None = None  # 말단 기울기 / 원점 기울기
    gate_leak: float | None = None         # max|I_G| / max|I_D|
    flags: list[str] = field(default_factory=list)


@dataclass
class OutputDiagnostics:
    blocks: list[BlockDiagnostics] = field(default_factory=list)
    worst: dict = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)


def _edge_slope(v_d: np.ndarray, i_d: np.ndarray, at_origin: bool) -> float | None:
    n = min(DIAG_SLOPE_POINTS, v_d.size)
    if n < 2:
        return None
    xs, ys = (v_d[:n], i_d[:n]) if at_origin else (v_d[-n:], i_d[-n:])
    slope, _intercept, _r2 = linear_fit(xs, ys)
    return float(slope)


def _diagnose_block(block, t: dict) -> BlockDiagnostics:
    d = BlockDiagnostics(v_g=block.v_g)
    df = block.forward
    if df is None or df.empty:
        d.flags.append("데이터 없음")
        return d

    v_d = df["V_D"].to_numpy(dtype=float)
    i_d = df["I_D"].to_numpy(dtype=float)
    i_g = df["I_G"].to_numpy(dtype=float)
    i_max = float(np.max(np.abs(i_d))) if i_d.size else 0.0

    # 1) 0 V 오프셋
    if i_max > 0:
        j = int(np.argmin(np.abs(v_d)))
        d.zero_offset = float(abs(i_d[j]) / i_max)
        if d.zero_offset > t["zero_offset"]:
            d.flags.append(
                f"0 V 오프셋 {d.zero_offset * 100:.2f} % (> {t['zero_offset'] * 100:g} %)"
            )

    # 2) 원점 근처 선형성
    span = float(np.max(np.abs(v_d))) if v_d.size else 0.0
    if span > 0:
        near = np.abs(v_d) <= span * DIAG_ORIGIN_FRACTION
        if int(np.count_nonzero(near)) >= 3:
            _slope, _intercept, r2 = linear_fit(v_d[near], i_d[near])
            d.linearity_r2 = float(r2)
            if d.linearity_r2 < t["linearity_r2"]:
                d.flags.append(
                    f"원점 선형성 R² {d.linearity_r2:.4f} (< {t['linearity_r2']:g}) "
                    "— 컨택트 저항 의심"
                )

    # 3) 포화 도달
    s0 = _edge_slope(v_d, i_d, at_origin=True)
    s1 = _edge_slope(v_d, i_d, at_origin=False)
    if s0 not in (None, 0.0) and s1 is not None:
        d.saturation_ratio = float(abs(s1 / s0))
        if d.saturation_ratio > t["saturation"]:
            d.flags.append(
                f"미포화: 말단/원점 기울기비 {d.saturation_ratio:.3f} (> {t['saturation']:g})"
            )

    # 4) 게이트 누설
    if i_max > 0 and i_g.size:
        d.gate_leak = float(np.max(np.abs(i_g)) / i_max)
        if d.gate_leak > t["gate_leak"]:
            d.flags.append(
                f"게이트 누설 {d.gate_leak * 100:.2f} % (> {t['gate_leak'] * 100:g} %)"
            )

    return d


def output_diagnostics(curve: OutputCurve,
                       thresholds: dict | None = None) -> OutputDiagnostics:
    t = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        t.update(thresholds)

    out = OutputDiagnostics()
    if curve is None or not curve.blocks:
        out.flags.append("output 데이터가 없습니다.")
        return out

    out.blocks = [_diagnose_block(b, t) for b in curve.blocks]

    def _agg(attr: str, fn):
        vals = [getattr(b, attr) for b in out.blocks if getattr(b, attr) is not None]
        return fn(vals) if vals else None

    out.worst = {
        "zero_offset": _agg("zero_offset", max),
        "linearity_r2": _agg("linearity_r2", min),
        "saturation_ratio": _agg("saturation_ratio", max),
        "gate_leak": _agg("gate_leak", max),
    }
    for b in out.blocks:
        for f in b.flags:
            out.flags.append(f"V_G = {b.v_g:g} V: {f}")
    return out
