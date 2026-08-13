"""최소자승 fit 과 sqrt(|I_D|) 구간 자동 탐색 (스펙 §3.3).

여기 상수는 전부 constants.py 에 있고 MANUAL.md 에 문서화된다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from fet_app.constants import (
    FIT_MAX_FRACTION, FIT_MIN_POINTS, FIT_ON_REGION_FACTOR, FIT_TIE_TOLERANCE,
)


@dataclass
class FitResult:
    slope: float
    intercept: float
    r2: float
    i_start: int
    i_end: int          # 배타적
    v_start: float
    v_end: float
    n_points: int

    def x_intercept(self) -> float | None:
        """y = 0 이 되는 x. V_th 계산에 쓴다."""
        if self.slope == 0:
            return None
        return -self.intercept / self.slope


def linear_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """(slope, intercept, r2). x 가 상수이거나 점이 2개 미만이면 r2=0."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 2 or np.ptp(x) == 0:
        return 0.0, 0.0, 0.0

    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(slope), float(intercept), float(r2)


def fit_window(x: np.ndarray, y: np.ndarray, i0: int, i1: int) -> FitResult | None:
    """[i0, i1) 구간 fit."""
    if i1 - i0 < 2:
        return None
    xs, ys = np.asarray(x, float)[i0:i1], np.asarray(y, float)[i0:i1]
    slope, intercept, r2 = linear_fit(xs, ys)
    return FitResult(slope=slope, intercept=intercept, r2=r2,
                     i_start=i0, i_end=i1,
                     v_start=float(xs[0]), v_end=float(xs[-1]),
                     n_points=int(i1 - i0))


def _longest_run(mask: np.ndarray) -> tuple[int, int] | None:
    """mask 가 True 인 가장 긴 연속 구간 [lo, hi) 를 반환."""
    best = None
    lo = None
    for i, m in enumerate(mask):
        if m and lo is None:
            lo = i
        elif not m and lo is not None:
            if best is None or i - lo > best[1] - best[0]:
                best = (lo, i)
            lo = None
    if lo is not None:
        if best is None or mask.size - lo > best[1] - best[0]:
            best = (lo, int(mask.size))
    return best


def auto_fit_sqrt(v_g: np.ndarray, i_d: np.ndarray) -> FitResult | None:
    """sqrt(|I_D|) vs V_G 에서 R^2 최대 구간을 찾는다.

    1. I_off = min|I_D|
    2. 후보 영역 = |I_D| > FIT_ON_REGION_FACTOR x I_off 의 최장 연속 구간
    3. 윈도우 FIT_MIN_POINTS ~ 후보영역x FIT_MAX_FRACTION 를 1점씩 슬라이딩
    4. R^2 최대. 차이가 FIT_TIE_TOLERANCE 이내면 점이 많은 쪽 우선
    """
    v_g = np.asarray(v_g, dtype=float)
    a = np.abs(np.asarray(i_d, dtype=float))
    if v_g.size != a.size or v_g.size < FIT_MIN_POINTS:
        return None

    # 스펙 §3.3 그대로 I_off = min|I_D|. tie-break 테스트(경계점에서 정확히 I_D=0 이
    # 되는 이상적 커브)는 "0 을 뺀 최솟값"을 쓰면 실패한다: 그 최솟값이 0 에 극도로
    # 가까운 값이 되어 임계값이 지나치게 엄격해지고 on-후보 구간이 필요한 폭보다
    # 줄어든다. min|I_D| 를 그대로 쓰면 정확히 0 인 점만 자연스럽게 걸러지고
    # 후보 구간은 최대로 유지된다.
    i_off = float(np.min(a))

    mask = a > FIT_ON_REGION_FACTOR * i_off
    run = _longest_run(mask)
    if run is None:
        return None
    lo, hi = run
    n = hi - lo
    if n < FIT_MIN_POINTS:
        return None

    y = np.sqrt(a)
    max_w = max(FIT_MIN_POINTS, int(n * FIT_MAX_FRACTION))
    max_w = min(max_w, n)

    best: FitResult | None = None
    for w in range(FIT_MIN_POINTS, max_w + 1):
        for s in range(lo, hi - w + 1):
            cand = fit_window(v_g, y, s, s + w)
            if cand is None:
                continue
            if best is None:
                best = cand
            elif cand.r2 > best.r2 + FIT_TIE_TOLERANCE:
                best = cand
            elif abs(cand.r2 - best.r2) <= FIT_TIE_TOLERANCE and cand.n_points > best.n_points:
                best = cand
    return best


def manual_fit_sqrt(v_g: np.ndarray, i_d: np.ndarray,
                    v_lo: float, v_hi: float) -> FitResult | None:
    """사용자가 지정한 V_G 범위 [v_lo, v_hi] 로 fit. 순서는 상관없다."""
    v_g = np.asarray(v_g, dtype=float)
    a = np.abs(np.asarray(i_d, dtype=float))
    lo, hi = (v_lo, v_hi) if v_lo <= v_hi else (v_hi, v_lo)

    idx = np.flatnonzero((v_g >= lo) & (v_g <= hi) & (a > 0))
    if idx.size < FIT_MIN_POINTS:
        return None
    i0, i1 = int(idx[0]), int(idx[-1]) + 1
    return fit_window(v_g, np.sqrt(a), i0, i1)
