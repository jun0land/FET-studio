"""Transfer 비교 그래프 — 여러 소자의 transfer 를 한 장에 겹쳐 그린다.

소자별 비교는 논문 그림에서 '조건 A/B/C' 를 나란히 보여주는 그 그림이다.
그래서 Transfer 그래프(figure_transfer)와 같은 규약·같은 배경 크기를 쓰되,
축은 **하나만** 둔다 — 이중 Y축에 여러 소자를 얹으면 어느 곡선이 어느 축인지
읽을 수 없기 때문이다. 어느 쪽을 볼지는 mode 로 고른다(log|I_D| 또는 √|I_D|).
구분은 색으로 하고, 소자 이름은 인셋 레전드에 스와치와 함께 적는다.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from fet_app.constants import COMPARE_PALETTE
from fet_app.figure_common import (
    apply_inset_text, axis_layout, domains, fit_y_margins, new_figure,
)
from fet_app.figure_output import _add_legend_swatches
from fet_app.figure_transfer import _abs_positive
from fet_app.markup import apply_markup

MODE_LABELS = {"log": "|I_D| (log)", "sqrt": "√|I_D|"}

# 레전드를 놓을 모서리 -> (x, y, xanchor, yanchor). transfer 커브는 좌상에서
# 우하로 흐르므로 좌하가 기본이다 (우상도 대개 비어 있다).
LEGEND_POSITIONS = {
    "bottom-left": (0.01, 0.01, "left", "bottom"),
    "bottom-right": (0.99, 0.01, "right", "bottom"),
    "top-left": (0.01, 0.99, "left", "top"),
    "top-right": (0.99, 0.99, "right", "top"),
}
LEGEND_POS_LABELS = {"bottom-left": "좌하", "bottom-right": "우하",
                     "top-left": "좌상", "top-right": "우상"}


def palette_color(index: int) -> str:
    """소자 순서 -> 기본 색. 팔레트보다 소자가 많으면 순환한다."""
    return COMPARE_PALETTE[int(index) % len(COMPARE_PALETTE)]


def assign_colors(names, manual: dict | None = None) -> dict[str, str]:
    """{소자명: 색}. 수동 지정이 있으면 그것이 이기고, 나머지는 팔레트 순서대로.

    수동 색이 팔레트 자리를 '먹지' 않게 한다 — 예를 들어 두 번째 소자만 빨강으로
    바꿨다고 세 번째 소자의 색까지 밀려서 바뀌면, 고르지도 않은 커브 색이 계속
    흔들려 보인다. 그래서 자동 배정은 자기 인덱스를 그대로 쓴다.
    """
    manual = manual or {}
    return {name: manual.get(name) or palette_color(i)
            for i, name in enumerate(names)}


def _unpack(item):
    """(라벨, 커브, 색[, fit]) — fit 은 선택이라 3-튜플도 그대로 받는다."""
    label, curve, color, *rest = item
    return label, curve, color, (rest[0] if rest else None)


def _add_fit(fig: go.Figure, label: str, fit, color: str, lw: float, k: float) -> None:
    """√|I_D| 위에 그 소자의 fit 직선과 V_th 절편 마커를 같은 색으로 얹는다.

    Transfer 그래프는 fit 을 고정 빨강으로 그리지만, 여기서는 소자마다 색이
    다르므로 커브 색을 따라가야 어느 fit 이 어느 커브의 것인지 읽힌다. 커브가
    실선이라 fit 은 점선으로 구분한다(reverse 는 파선). fit 구간 음영은 여러
    소자가 겹치면 뭉개지므로 그리지 않는다.
    """
    if fit is None or fit.slope == 0:
        return
    v_th = -fit.intercept / fit.slope
    x_lo, x_hi = sorted((fit.v_start, fit.v_end))
    x_line = np.array([min(x_lo, v_th), max(x_hi, v_th)], dtype=float)
    fig.add_trace(go.Scatter(
        x=x_line, y=fit.slope * x_line + fit.intercept, name=f"{label} fit",
        mode="lines", line=dict(color=color, width=max(0.25, lw * 0.9), dash="dot"),
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=[v_th], y=[0.0], name=f"{label} V_th", mode="markers",
        marker=dict(color=color, size=max(3, round(10 * k)), symbol="circle-open",
                    line=dict(width=max(0.5, 2 * k))),
        hoverinfo="skip",
    ))


def compare_figure(items, settings: dict, k: float = 1.0) -> go.Figure:
    """``items`` = [(라벨, TransferCurve, 색[, FitResult])] 을 한 축에 겹쳐 그린다.

    fit 은 √|I_D| 위의 직선이라 mode 가 ``sqrt`` 일 때만 그린다 — log 축에
    옮겨 그리면 곡선이 되어 논문 관례와 어긋난다.
    """
    geom, style = settings["geom"], settings["style"]
    axes, cfg, insets = settings["axes"], settings["compare"], settings["insets"]

    mode = cfg.get("mode", "log")
    show_reverse = bool(cfg.get("show_reverse", False))
    show_fit = bool(cfg.get("show_fit", True)) and mode == "sqrt"
    lw = max(0.25, float(style["line_width"]) * k)

    fig = new_figure(geom, k)
    x_dom, y_dom = domains(geom)

    all_v, all_y, legend_rows = [], [], []
    for item in items:
        label, curve, color, fit = _unpack(item)
        if curve is None:
            continue
        legend_rows.append((color, apply_markup(str(label))))
        branches = [("forward", curve.forward, "solid")]
        if show_reverse and curve.reverse is not None:
            # 소자마다 색이 다르므로 방향은 선 종류로 구분해도 헷갈리지 않는다.
            branches.append(("reverse", curve.reverse, "dash"))
        for branch, df, dash in branches:
            if df is None or df.empty:
                continue
            v = df["V_G"].to_numpy(dtype=float)
            i_abs = _abs_positive(df["I_D"].to_numpy(dtype=float))
            y = i_abs if mode == "log" else np.sqrt(i_abs)
            all_v.append(v)
            all_y.append(y)
            fig.add_trace(go.Scatter(
                x=v, y=y, name=f"{label} {branch}", mode="lines",
                line=dict(color=color, width=lw, dash=dash), hoverinfo="skip",
            ))
        if show_fit:
            _add_fit(fig, label, fit, color, lw, k)

    # 빈 선택(또는 전부 빈 커브)이어도 축은 나와야 한다 — figure_transfer 와 같은 방어.
    v_cat = np.concatenate(all_v) if all_v else np.array([0.0, 1.0])
    y_cat = np.concatenate(all_y) if all_y else np.array([np.nan])
    if v_cat.size == 0:
        v_cat = np.array([0.0, 1.0])
    y_pos = y_cat[np.isfinite(y_cat)]

    if mode == "log":
        y_cfg = axes["y"]
        y_lo = float(np.floor(np.log10(np.min(y_pos)))) if y_pos.size else None
        y_hi = float(np.ceil(np.log10(np.max(y_pos)))) if y_pos.size else None
    else:
        # y2 는 Transfer 에서 오른쪽 축이지만 여기서는 축이 하나뿐이라 왼쪽에
        # 그린다 (side 를 넘기지 않으면 기본이 왼쪽이다). 제목·눈금 설정은
        # 그대로 물려받아 두 화면의 √|I_D| 축이 같아 보이게 한다.
        y_cfg = axes["y2"]
        y_lo = 0.0
        y_hi = float(np.max(y_pos)) * 1.05 if y_pos.size else None

    y_lay = axis_layout(y_cfg, style, k, data_min=y_lo, data_max=y_hi, domain=y_dom)
    x_dom = fit_y_margins(geom, x_dom, style, k, left_lay=y_lay)
    fig.update_layout(
        xaxis=axis_layout(axes["x"], style, k,
                          data_min=float(np.min(v_cat)), data_max=float(np.max(v_cat)),
                          domain=x_dom),
        yaxis=y_lay,
    )

    if cfg.get("legend", True):
        # 글꼴·배경 같은 모양은 인셋 레전드 설정을 그대로 쓰고, 자리만 비교 뷰가
        # 따로 정한다 (Output 레전드와 비어 있는 모서리가 다르다).
        pos = LEGEND_POSITIONS.get(cfg.get("legend_pos"),
                                   LEGEND_POSITIONS["bottom-left"])
        inset = dict(insets["legend"])
        inset.update(x=pos[0], y=pos[1], xanchor=pos[2], yanchor=pos[3])
        _add_legend_swatches(fig, legend_rows, inset, geom, style, k, x_dom)
    apply_inset_text(fig, insets["sample"].get("text", ""), insets["sample"], style, k)
    return fig
