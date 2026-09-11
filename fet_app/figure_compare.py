"""Transfer 비교 그래프 — 여러 소자의 transfer 를 한 장에 겹쳐 그린다.

소자별 비교는 논문 그림에서 '조건 A/B/C' 를 나란히 보여주는 그 그림이다.
Transfer 그래프(figure_transfer)와 같은 규약·같은 배경 크기를 쓰고, mode 로
세 가지 중 하나를 고른다.

  dual  좌축 log|I_D| (실선) + 우축 √|I_D| (점선) — 논문에서 소자 몇 개를 한
        패널에 비교할 때 흔한 형식. 축은 선 종류로, 소자는 색으로 구분한다.
        선 종류 규약은 Transfer 그래프와 같다(|I_D| 실선, √|I_D| 점선).
  log   좌축 log|I_D| 만.   sqrt  √|I_D| 만 (fit 직선을 크게 보고 싶을 때).

소자가 많으면 dual 은 선이 두 배라 어수선해진다 — 그때는 log/sqrt 로 나눠
두 패널을 만드는 쪽이 논문에서도 일반적이다. 소자 이름은 인셋 레전드에
스와치와 함께 적는다.
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

MODE_LABELS = {"dual": "|I_D| (log) + √|I_D|", "log": "|I_D| (log)", "sqrt": "√|I_D|"}
# 우축 √|I_D| 의 불투명도. Transfer 그래프(0.55, 검정을 회색으로 보이게)보다
# 조금 진하게 — 색깔 점선은 너무 연하면 소자 색을 못 알아본다.
DUAL_SQRT_OPACITY = 0.7

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


def _add_fit(fig: go.Figure, label: str, fit, color: str, lw: float, k: float,
             yaxis: str, dash: str) -> None:
    """√|I_D| 위에 그 소자의 fit 직선과 V_th 절편 마커를 같은 색으로 얹는다.

    Transfer 그래프는 fit 을 고정 빨강으로 그리지만, 여기서는 소자마다 색이
    다르므로 커브 색을 따라가야 어느 fit 이 어느 커브의 것인지 읽힌다. 선 종류는
    호출부가 정한다 — √|I_D| 커브가 실선(sqrt 모드)이면 fit 은 점선, 커브가
    점선(dual 모드)이면 fit 은 파선. fit 구간 음영은 여러 소자가 겹치면
    뭉개지므로 그리지 않는다.
    """
    if fit is None or fit.slope == 0:
        return
    v_th = -fit.intercept / fit.slope
    x_lo, x_hi = sorted((fit.v_start, fit.v_end))
    x_line = np.array([min(x_lo, v_th), max(x_hi, v_th)], dtype=float)
    fig.add_trace(go.Scatter(
        x=x_line, y=fit.slope * x_line + fit.intercept, name=f"{label} fit",
        mode="lines", yaxis=yaxis,
        line=dict(color=color, width=max(0.25, lw * 0.9), dash=dash),
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=[v_th], y=[0.0], name=f"{label} V_th", mode="markers", yaxis=yaxis,
        marker=dict(color=color, size=max(3, round(10 * k)), symbol="circle-open",
                    line=dict(width=max(0.5, 2 * k))),
        hoverinfo="skip",
    ))


def compare_figure(items, settings: dict, k: float = 1.0) -> go.Figure:
    """``items`` = [(라벨, TransferCurve, 색[, FitResult])] 을 겹쳐 그린다.

    fit 은 √|I_D| 위의 직선이라 √ 축이 있는 모드(dual/sqrt)에서만 그린다 —
    log 축에 옮겨 그리면 곡선이 되어 논문 관례와 어긋난다.
    """
    geom, style = settings["geom"], settings["style"]
    axes, cfg, insets = settings["axes"], settings["compare"], settings["insets"]
    trace_cfg = settings.get("trace", {})

    mode = cfg.get("mode", "dual")
    if mode not in MODE_LABELS:
        mode = "dual"
    dual = mode == "dual"
    show_reverse = bool(cfg.get("show_reverse", False))
    show_fit = bool(cfg.get("show_fit", True)) and mode != "log"
    lw = max(0.25, float(style["line_width"]) * k)

    # 선 종류. dual 은 Transfer 그래프와 같은 규약(|I_D| 실선 / √|I_D| 점선 / fit 파선,
    # forward·reverse 는 같은 선). 단일 축 모드는 커브가 실선 하나뿐이라 reverse 를
    # 파선으로, fit 을 점선으로 구분한다.
    if dual:
        log_dash, sqrt_dash, rev_dash, fit_dash = "solid", "dot", None, "dash"
        sqrt_axis = fit_axis = "y2"
    else:
        log_dash = sqrt_dash = "solid"
        rev_dash, fit_dash = "dash", "dot"
        sqrt_axis = fit_axis = "y"

    fig = new_figure(geom, k)
    x_dom, y_dom = domains(geom)

    all_v, all_i, all_sqrt, legend_rows = [], [], [], []
    for item in items:
        label, curve, color, fit = _unpack(item)
        if curve is None:
            continue
        legend_rows.append((color, apply_markup(str(label))))
        branches = [("forward", curve.forward, False)]
        if show_reverse and curve.reverse is not None:
            branches.append(("reverse", curve.reverse, True))
        for branch, df, is_rev in branches:
            if df is None or df.empty:
                continue
            v = df["V_G"].to_numpy(dtype=float)
            i_abs = _abs_positive(df["I_D"].to_numpy(dtype=float))
            all_v.append(v)
            if mode in ("dual", "log"):
                all_i.append(i_abs)
                fig.add_trace(go.Scatter(
                    x=v, y=i_abs, name=f"{label} {branch} |I_D|", mode="lines", yaxis="y",
                    line=dict(color=color, width=lw,
                              dash=(rev_dash if is_rev and rev_dash else log_dash)),
                    hoverinfo="skip",
                ))
            if mode in ("dual", "sqrt"):
                sq = np.sqrt(i_abs)
                all_sqrt.append(sq)
                fig.add_trace(go.Scatter(
                    x=v, y=sq, name=f"{label} {branch} √|I_D|", mode="lines",
                    yaxis=sqrt_axis,
                    line=dict(color=color, width=lw,
                              dash=(rev_dash if is_rev and rev_dash else sqrt_dash)),
                    opacity=DUAL_SQRT_OPACITY if dual else 1.0, hoverinfo="skip",
                ))
        if show_fit:
            _add_fit(fig, label, fit, color, lw, k, fit_axis, fit_dash)

    # 빈 선택(또는 전부 빈 커브)이어도 축은 나와야 한다 — figure_transfer 와 같은 방어.
    v_cat = np.concatenate(all_v) if all_v else np.array([0.0, 1.0])
    if v_cat.size == 0:
        v_cat = np.array([0.0, 1.0])
    i_cat = np.concatenate(all_i) if all_i else np.array([np.nan])
    s_cat = np.concatenate(all_sqrt) if all_sqrt else np.array([np.nan])
    i_pos = i_cat[np.isfinite(i_cat)]
    s_pos = s_cat[np.isfinite(s_cat)]

    log_lay = axis_layout(
        axes["y"], style, k,
        data_min=float(np.floor(np.log10(np.min(i_pos)))) if i_pos.size else None,
        data_max=float(np.ceil(np.log10(np.max(i_pos)))) if i_pos.size else None,
        domain=y_dom, axis_color=trace_cfg.get("axis_color_left", "#000000"))
    sqrt_hi = float(np.max(s_pos)) * 1.05 if s_pos.size else None

    if dual:
        # Transfer 그래프와 같은 이중 Y축. 축 색도 그쪽 설정을 따른다.
        y_lay = log_lay
        y2_lay = axis_layout(axes["y2"], style, k, data_min=0.0, data_max=sqrt_hi,
                             side="right", overlaying="y",
                             axis_color=trace_cfg.get("axis_color_right", "#000000"))
        x_dom = fit_y_margins(geom, x_dom, style, k, left_lay=y_lay, right_lay=y2_lay)
    elif mode == "log":
        y_lay, y2_lay = log_lay, None
        x_dom = fit_y_margins(geom, x_dom, style, k, left_lay=y_lay)
    else:
        # y2 는 Transfer 에서 오른쪽 축이지만 여기서는 축이 하나뿐이라 왼쪽에
        # 그린다 (side 를 넘기지 않으면 기본이 왼쪽이다). 제목·눈금 설정은
        # 그대로 물려받아 두 화면의 √|I_D| 축이 같아 보이게 한다.
        y_lay = axis_layout(axes["y2"], style, k, data_min=0.0, data_max=sqrt_hi,
                            domain=y_dom)
        y2_lay = None
        x_dom = fit_y_margins(geom, x_dom, style, k, left_lay=y_lay)

    layout = dict(
        xaxis=axis_layout(axes["x"], style, k,
                          data_min=float(np.min(v_cat)), data_max=float(np.max(v_cat)),
                          domain=x_dom),
        yaxis=y_lay,
    )
    if y2_lay is not None:
        layout["yaxis2"] = y2_lay
    fig.update_layout(**layout)

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
