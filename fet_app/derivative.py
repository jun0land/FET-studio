"""포인트별(순간) 미분.

fit 은 구간 하나를 직선으로 요약한다. 그래서 '어디가 정말 직선인지', '이동도가
V_G 에 따라 어떻게 변하는지'는 fit 값만 봐서는 알 수 없다. 여기서는 각 측정
포인트마다 중앙차분으로 기울기를 구해 그 자체를 곡선으로 만든다.

중앙차분은 측정 노이즈를 그대로 증폭하므로(간격이 촘촘할수록 심하다), 미분
'전' 원자료에 이동평균을 걸 수 있게 열어 둔다 — 미분 결과를 다듬는 것보다
원자료를 다듬는 쪽이 봉우리 위치를 덜 흔든다.
"""

from __future__ import annotations

import numpy as np

# mode -> (Y축 제목 마크업, 소자 파라미터 필요 여부)
TRANSFER_MODES = {
    "gm": ("|g_{m}| (S)", False),
    "dsqrt": ("|d√|I_{D}|/dV_{G}| (A^{0.5}/V)", False),
    "mu": ("μ (cm^{2}/Vs)", True),
}
TRANSFER_MODE_LABELS = {
    "gm": "g_m = d|I_D|/dV_G",
    "dsqrt": "d√|I_D|/dV_G",
    "mu": "포인트별 μ",
}
OUTPUT_MODE_TITLE = "|g_{d}| (S)"


def moving_average(y, window: int) -> np.ndarray:
    """양 끝에서 기울기를 왜곡하지 않는 이동평균. window <= 1 이면 원본 그대로.

    가장자리 처리를 어떻게 하느냐가 전부다. 이 결과를 곧바로 미분하기 때문에,
    끝에서 값이 조금만 눌려도 그 구간의 기울기가 통째로 틀어진다.

      - ``np.convolve(mode="same")`` 는 창 밖에서 0 을 끌어와 끝값을 0 쪽으로
        끌어내린다.
      - 유효 표본 수로 나눠 정규화하면(잘린 창의 평균) 값은 안 눌리지만
        평균의 '중심'이 안쪽으로 밀려서, 직선 구간에서도 끝 h 개 점의 기울기가
        절반으로 나온다 (실측: 기울기 1E-6 데이터에서 끝점이 5E-7).

    그래서 끝점 기준 **점대칭(odd/antisymmetric) 패딩**을 쓴다: 2*y[0] - y[h..1]
    을 앞에 붙이면 직선을 그대로 이어 붙인 셈이라 1차 추세가 완전히 보존되고,
    창 전체가 항상 채워져 중심도 밀리지 않는다.
    """
    a = np.asarray(y, dtype=float)
    w = int(window or 1)
    if w <= 1 or a.size < 3:
        return a
    w = min(w if w % 2 else w + 1, a.size if a.size % 2 else a.size - 1)
    if w <= 1:
        return a
    h = w // 2
    padded = np.concatenate((2 * a[0] - a[h:0:-1], a, 2 * a[-1] - a[-2:-h - 2:-1]))

    kernel = np.ones(w)
    valid = np.isfinite(padded)
    total = np.convolve(np.where(valid, padded, 0.0), kernel, mode="valid")
    count = np.convolve(valid.astype(float), kernel, mode="valid")
    with np.errstate(invalid="ignore", divide="ignore"):
        out = total / count
    return np.where(count > 0, out, np.nan)


def pointwise(x, y) -> np.ndarray:
    """dy/dx 를 포인트마다 (중앙차분, 양 끝은 전진/후진 차분).

    같은 x 가 연달아 나오면(측정기가 반환점에서 같은 전압을 두 번 찍는다)
    0 으로 나누게 되므로 그 점은 미리 빼고 계산한 뒤 nan 으로 되돌린다.
    """
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    out = np.full(xa.shape, np.nan)
    ok = np.isfinite(xa) & np.isfinite(ya)
    if ok.sum() >= 2:
        idx = np.flatnonzero(ok)
        xs, ys = xa[idx], ya[idx]
        keep = np.concatenate(([True], np.diff(xs) != 0))
        idx, xs, ys = idx[keep], xs[keep], ys[keep]
        if xs.size >= 2:
            out[idx] = np.gradient(ys, xs)
    return out


def transfer_series(df, mode: str, params, smooth: int = 1):
    """(V_G, 미분값) — 그릴 수 없으면 None.

    ``mu`` 는 포화영역 이동도식의 포인트별 판이다:
    μ(V_G) = (2L / (W C_ox)) * (d√|I_D| / dV_G)^2  (스펙 §3.2 와 같은 식).
    """
    if df is None or df.empty or mode not in TRANSFER_MODES:
        return None
    v = df["V_G"].to_numpy(dtype=float)
    i_abs = np.abs(df["I_D"].to_numpy(dtype=float))

    if mode == "gm":
        return v, np.abs(pointwise(v, moving_average(i_abs, smooth)))

    d_sqrt = pointwise(v, moving_average(np.sqrt(i_abs), smooth))
    if mode == "dsqrt":
        return v, np.abs(d_sqrt)

    if params is None or not params.is_complete():
        return None
    factor = 2.0 * params.l_cm() / (params.w_cm() * params.c_ox())
    return v, factor * d_sqrt ** 2


def output_series(df, smooth: int = 1):
    """(V_D, |dI_D/dV_D|) — output 곡선의 포인트별 출력 컨덕턴스."""
    if df is None or df.empty:
        return None
    v = df["V_D"].to_numpy(dtype=float)
    i_abs = np.abs(df["I_D"].to_numpy(dtype=float))
    return v, np.abs(pointwise(v, moving_average(i_abs, smooth)))
