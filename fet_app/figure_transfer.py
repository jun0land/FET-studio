"""Transfer 이중 Y축 그래프 (스펙 §5.2).

좌 log|I_D| / 우 sqrt(|I_D|). 우축에 fit 직선·구간 음영·V_th 절편을 얹는다.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from fet_app.constants import (
    FIT_BAND_SHAPE_NAME, SWEEP_ARROW_LEN, SWEEP_ARROW_OFFSET, SWEEP_ARROW_SKIP,
    hex_to_rgba,
)
from fet_app.figure_common import (
    add_curved_arrow, apply_inset_text, axis_layout, curve_arrow_points, domains,
    fit_y_margins, new_figure, plot_px_size,
)


def _abs_positive(a: np.ndarray) -> np.ndarray:
    """log 축용. 0 은 그릴 수 없으므로 nan 으로 빼둔다."""
    out = np.abs(np.asarray(a, dtype=float))
    return np.where(out > 0, out, np.nan)


def _fractions(v: np.ndarray, i_abs: np.ndarray,
               x_rng, y_rng) -> tuple[np.ndarray, np.ndarray] | None:
    """데이터 좌표 -> 플롯 영역 안의 domain 비율 (좌축은 log 라 지수로 잰다)."""
    if not x_rng or not y_rng:
        return None
    x0, x1 = float(x_rng[0]), float(x_rng[1])
    y0, y1 = float(y_rng[0]), float(y_rng[1])
    if x1 == x0 or y1 == y0:
        return None
    with np.errstate(divide="ignore", invalid="ignore"):
        log_i = np.log10(i_abs)
    return (v - x0) / (x1 - x0), (log_i - y0) / (y1 - y0)


def _add_sweep_arrows(fig: go.Figure, curve, x_lay: dict, y_lay: dict,
                      geom: dict, x_dom, y_dom, color: str, width: float,
                      k: float) -> None:
    """반환점(스윕이 꺾이는 쪽) 안쪽에 가는 방향·오는 방향 화살표를 얹는다.

    dual sweep 을 선 종류(실선/파선)로 구분하는 대신 쓰는 표시다 — |I_D| 는
    forward/reverse 가 모두 점선이라 선만 봐서는 방향을 알 수 없기 때문이다.
    forward 는 반환점을 '향해' 가고 reverse 는 반환점에서 '나오'므로, 두 화살표를
    커브 양옆(수직 오프셋 부호를 반대로)에 놓아 겹치지 않게 한다.
    """
    plot_w, plot_h = plot_px_size(geom, k, x_dom, y_dom)
    if plot_w <= 0 or plot_h <= 0:
        return
    x_rng, y_rng = x_lay.get("range"), y_lay.get("range")
    for df, from_start, sign in ((curve.forward, False, 1.0),
                                 (curve.reverse, True, -1.0)):
        if df is None or df.empty:
            continue
        fr = _fractions(df["V_G"].to_numpy(dtype=float),
                        _abs_positive(df["I_D"].to_numpy(dtype=float)), x_rng, y_rng)
        if fr is None:
            continue
        pts = curve_arrow_points(fr[0], fr[1], plot_w, plot_h,
                                 SWEEP_ARROW_SKIP, SWEEP_ARROW_LEN,
                                 sign * SWEEP_ARROW_OFFSET, from_start)
        add_curved_arrow(fig, pts, plot_w, plot_h, color, width, k)


def transfer_figure(curve, metrics, settings: dict, k: float = 1.0) -> go.Figure:
    geom, style = settings["geom"], settings["style"]
    axes, trace_cfg, insets = settings["axes"], settings["trace"], settings["insets"]

    fig = new_figure(geom, k)
    x_dom, y_dom = domains(geom)
    # 좌축(log|I_D|, |I_G|)과 우축(√|I_D|)은 각각 자기 색을 쓰고, 축(선·눈금·제목)
    # 색과 커브(트레이스) 선 색은 서로 독립이다. fit/V_th 의 빨강(#d62728)은 raw
    # 커브와 구분하기 위한 고정 강조색이라 여기 영향을 받지 않는다.
    axis_color_left = trace_cfg.get("axis_color_left", "#000000")
    axis_color_right = trace_cfg.get("axis_color_right", "#000000")
    line_color_left = trace_cfg.get("line_color_left", "#000000")
    line_color_right = trace_cfg.get("line_color_right", "#000000")
    lw = max(0.25, float(style["line_width"]) * k)

    show_reverse = bool(trace_cfg.get("show_reverse", True)) and curve.reverse is not None
    branches = [("forward", curve.forward)]
    if show_reverse:
        branches.append(("reverse", curve.reverse))

    all_v, all_i, all_sqrt = [], [], []
    for label, df in branches:
        v = df["V_G"].to_numpy(dtype=float)
        i_abs = _abs_positive(df["I_D"].to_numpy(dtype=float))
        all_v.append(v)
        all_i.append(i_abs)
        all_sqrt.append(np.sqrt(i_abs))

        # dual sweep 을 선 종류로 구분하지 않는다 — 축으로 구분한다. 논문
        # 관례대로 주 곡선인 |I_D| 가 실선(좌축), fit 을 얹는 √|I_D| 가 점선
        # (우축)이고, forward/reverse 는 둘 다 같은 선 종류다. 스윕 방향은
        # 반환점 옆 화살표(_add_sweep_arrows)가 알려준다.
        fig.add_trace(go.Scatter(
            x=v, y=i_abs, name=f"{label} |I_D|", mode="lines", yaxis="y",
            line=dict(color=line_color_left, width=lw, dash="solid"), hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=v, y=np.sqrt(i_abs), name=f"{label} √|I_D|", mode="lines", yaxis="y2",
            line=dict(color=line_color_right, width=lw, dash="dot"), opacity=0.55,
            hoverinfo="skip",
        ))
        if trace_cfg.get("show_gate_current", False):
            # |I_G| 도 좌축이라 |I_D| 와 색이 같다. 실선은 |I_D|, 점선은 √|I_D| 가
            # 가져갔으므로 파선으로 구분한다.
            fig.add_trace(go.Scatter(
                x=v, y=_abs_positive(df["I_G"].to_numpy(dtype=float)),
                name="|I_G|", mode="lines", yaxis="y",
                line=dict(color=line_color_left, width=lw * 0.75, dash="dash"),
                opacity=0.6, hoverinfo="skip",
            ))

    # fit 직선 · 구간 음영 · V_th 절편
    fit = getattr(metrics, "fit", None)
    if trace_cfg.get("show_fit", True) and fit is not None and fit.slope != 0:
        v_th = -fit.intercept / fit.slope
        x_lo, x_hi = sorted((fit.v_start, fit.v_end))
        x_line = np.array([min(x_lo, v_th), max(x_hi, v_th)], dtype=float)
        fig.add_trace(go.Scatter(
            x=x_line, y=fit.slope * x_line + fit.intercept,
            name="fit", mode="lines", yaxis="y2",
            line=dict(color="#d62728", width=max(0.25, lw * 0.9), dash="solid"),
            hoverinfo="skip",
        ))
        # 이름을 붙여 두면 내보내기(export._prepared_figure)가 이 음영만 골라
        # 걷어낸다 — 화면에서는 fit 구간을 보여주되 그림 파일에는 남기지 않는다.
        fig.add_vrect(x0=x_lo, x1=x_hi, xref="x", name=FIT_BAND_SHAPE_NAME,
                      fillcolor=hex_to_rgba("#d62728", 0.08),
                      line_width=0, layer="below")
        fig.add_trace(go.Scatter(
            x=[v_th], y=[0.0], name="V_th", mode="markers", yaxis="y2",
            marker=dict(color="#d62728", size=max(3, round(10 * k)), symbol="circle-open",
                        line=dict(width=max(0.5, 2 * k))),
            hoverinfo="skip",
        ))

    # 빈 커브(측정 중단 파일)여도 축이 만들어져야 한다. 방어가 없으면
    # np.min 이 zero-size 배열에서 터져 페이지 전체가 트레이스백이 된다.
    # figure_output 도 같은 방식으로 막고 있다.
    v_cat = np.concatenate(all_v) if all_v else np.array([0.0, 1.0])
    i_cat = np.concatenate(all_i) if all_i else np.array([np.nan])
    s_cat = np.concatenate(all_sqrt) if all_sqrt else np.array([np.nan])
    if v_cat.size == 0:
        v_cat = np.array([0.0, 1.0])
    i_pos = i_cat[np.isfinite(i_cat)]
    s_pos = s_cat[np.isfinite(s_cat)]

    # Y축 둘을 먼저 만들고, 그 눈금 숫자·제목이 실제로 먹는 폭을 재서 플롯
    # 영역(x domain)을 안쪽으로 민다 — Plotly 는 축 제목을 종이 안쪽으로
    # 클램프하므로 여백이 모자라면 standoff 를 올려도 제목이 숫자에 겹친다.
    y_lay = axis_layout(
        axes["y"], style, k,
        data_min=float(np.floor(np.log10(np.min(i_pos)))) if i_pos.size else None,
        data_max=float(np.ceil(np.log10(np.max(i_pos)))) if i_pos.size else None,
        domain=y_dom, axis_color=axis_color_left)
    y2_lay = axis_layout(axes["y2"], style, k,
                         data_min=0.0,
                         data_max=float(np.max(s_pos)) * 1.05 if s_pos.size else None,
                         side="right", overlaying="y", axis_color=axis_color_right)
    x_dom = fit_y_margins(geom, x_dom, style, k, left_lay=y_lay, right_lay=y2_lay)
    x_lay = axis_layout(axes["x"], style, k,
                        data_min=float(np.min(v_cat)), data_max=float(np.max(v_cat)),
                        domain=x_dom)

    fig.update_layout(xaxis=x_lay, yaxis=y_lay, yaxis2=y2_lay)

    if show_reverse and trace_cfg.get("show_sweep_arrows", True):
        _add_sweep_arrows(fig, curve, x_lay, y_lay, geom, x_dom, y_dom,
                          line_color_left, max(0.4, lw * 0.9), k)

    apply_inset_text(fig, insets["sample"].get("text", ""), insets["sample"], style, k)
    return fig
