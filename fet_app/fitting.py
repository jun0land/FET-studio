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


def _prefix(a: np.ndarray) -> np.ndarray:
    """누적합. p[i] = sum(a[:i]) 이라 구간합이 p[j] - p[i] 로 O(1)."""
    p = np.zeros(a.size + 1, dtype=float)
    if a.size:
        np.cumsum(a, out=p[1:])
    return p


def _best_window_by_r2(x: np.ndarray, y: np.ndarray,
                       w_min: int, w_max: int) -> tuple[int, int] | None:
    """[0, n) 안에서 R^2 최대 창 (start, width) 을 찾는다.

    창마다 np.polyfit 을 다시 돌리는 대신 누적합으로 구간합(Sx, Sy, Sxy, Sxx,
    Syy)을 O(1) 에 얻어 R^2 를 닫힌 식으로 구한다 -> 창당 O(1). R^2 는 창을
    "고르는 데만" 쓰고, 최종 slope/intercept/r2 는 호출부가 fit_window 로 다시
    계산한다. 그래서 선택만 같으면 결과는 기존 경로와 비트 단위로 같다.

    수치 안정성: 큰 누적합끼리 빼면 자리수가 날아갈 수 있으므로(catastrophic
    cancellation) x, y 를 평균만큼 옮긴 뒤 누적한다. R^2 도 1 - SS_res/SS_tot
    대신 상관계수 제곱 형태(Sxy_c^2 / (Sxx_c x Syy_c))로 계산한다 — 수학적으로
    같지만 뺄셈이 한 단계 적다.
    """
    n = x.size
    xc = x - x.mean()
    yc = y - y.mean()
    p_x, p_y = _prefix(xc), _prefix(yc)
    p_xx, p_yy, p_xy = _prefix(xc * xc), _prefix(yc * yc), _prefix(xc * yc)
    # x 가 상수인 창 판정. linear_fit 의 np.ptp(x) == 0 과 정확히 같은 조건을
    # 누적합으로 옮긴 것 (창 안에 0 이 아닌 diff 가 하나라도 있으면 비상수).
    p_nz = _prefix((np.diff(x) != 0).astype(float))

    best: tuple[int, int] | None = None
    best_r2 = 0.0
    best_n = 0
    for w in range(w_min, w_max + 1):
        m = n - w + 1
        if m <= 0:
            break
        i0 = np.arange(m)
        i1 = i0 + w
        s_x = p_x[i1] - p_x[i0]
        s_y = p_y[i1] - p_y[i0]
        s_xx = p_xx[i1] - p_xx[i0]
        s_yy = p_yy[i1] - p_yy[i0]
        s_xy = p_xy[i1] - p_xy[i0]
        d_xx = s_xx - s_x * s_x / w
        d_yy = s_yy - s_y * s_y / w
        num = s_xy - s_x * s_y / w
        # d_xx <= 0 (x 상수) 또는 d_yy <= 0 (y 상수) 이면 linear_fit 규약대로 0.
        ok = (d_xx > 0) & (d_yy > 0) & ((p_nz[i1 - 1] - p_nz[i0]) > 0)
        r2 = np.zeros(m, dtype=float)
        np.divide(num * num, d_xx * d_yy, out=r2, where=ok)

        # 순차 비교 규칙은 기존 이중 루프와 동일한 순서(w 오름차순, s 오름차순).
        for s, r in enumerate(r2.tolist()):
            if best is None:
                best, best_r2, best_n = (s, w), r, w
            elif r > best_r2 + FIT_TIE_TOLERANCE:
                best, best_r2, best_n = (s, w), r, w
            elif abs(r - best_r2) <= FIT_TIE_TOLERANCE and w > best_n:
                best, best_r2, best_n = (s, w), r, w
            elif w == best_n and r > best_r2:
                best, best_r2, best_n = (s, w), r, w
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

    # I_off = min|I_D| 이지만 정확히 0 인 점은 제외해야 한다. 계측 분해능 클램프
    # 등으로 |I_D| 가 정확히 0 인 점이 하나라도 있으면 I_off 가 0 이 되고, 임계값
    # FIT_ON_REGION_FACTOR x I_off 도 0 이 되어 on-영역 필터가 사실상 무력화된다
    # (mask 가 a > 0 으로 퇴화해 노이즈 바닥까지 후보 구간에 들어온다).
    positive = a[a > 0]
    if positive.size == 0:
        return None
    i_off = float(np.min(positive))

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

    # 후보 영역만 잘라서 창 탐색 (누적합의 크기를 줄여 자리수 손실도 함께 줄인다).
    # 비교 규칙(동점 tolerance, 긴 창 우선, 같은 길이면 R^2 높은 쪽)은 _best_window_by_r2
    # 안에 기존 이중 루프와 같은 순서로 그대로 옮겨져 있다.
    pick = _best_window_by_r2(v_g[lo:hi], y[lo:hi], FIT_MIN_POINTS, max_w)
    if pick is None:
        return None
    s, w = pick
    return fit_window(v_g, y, lo + s, lo + s + w)


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
