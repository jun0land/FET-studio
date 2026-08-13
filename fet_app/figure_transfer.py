"""Transfer 이중 Y축 그래프 (스펙 §5.2).

좌 log|I_D| / 우 sqrt(|I_D|). 우축에 fit 직선·구간 음영·V_th 절편을 얹는다.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from fet_app.constants import hex_to_rgba
from fet_app.figure_common import apply_inset_text, axis_layout, domains, new_figure


def _abs_positive(a: np.ndarray) -> np.ndarray:
    """log 축용. 0 은 그릴 수 없으므로 nan 으로 빼둔다."""
    out = np.abs(np.asarray(a, dtype=float))
    return np.where(out > 0, out, np.nan)


def transfer_figure(curve, metrics, settings: dict, k: float = 1.0) -> go.Figure:
    geom, style = settings["geom"], settings["style"]
    axes, trace_cfg, insets = settings["axes"], settings["trace"], settings["insets"]

    fig = new_figure(geom, k)
    x_dom, y_dom = domains(geom)
    color = trace_cfg.get("color", "#000000")
    lw = max(0.25, float(style["line_width"]) * k)

    branches = [("forward", curve.forward, "solid")]
    if trace_cfg.get("show_reverse", True) and curve.reverse is not None:
        branches.append(("reverse", curve.reverse, "dash"))

    all_v, all_i, all_sqrt = [], [], []
    for label, df, dash in branches:
        v = df["V_G"].to_numpy(dtype=float)
        i_abs = _abs_positive(df["I_D"].to_numpy(dtype=float))
        all_v.append(v)
        all_i.append(i_abs)
        all_sqrt.append(np.sqrt(i_abs))

        fig.add_trace(go.Scatter(
            x=v, y=i_abs, name=f"{label} |I_D|", mode="lines", yaxis="y",
            line=dict(color=color, width=lw, dash=dash), hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=v, y=np.sqrt(i_abs), name=f"{label} √|I_D|", mode="lines", yaxis="y2",
            line=dict(color=color, width=lw, dash=dash), opacity=0.55, hoverinfo="skip",
        ))
        if trace_cfg.get("show_gate_current", False):
            fig.add_trace(go.Scatter(
                x=v, y=_abs_positive(df["I_G"].to_numpy(dtype=float)),
                name="|I_G|", mode="lines", yaxis="y",
                line=dict(color=color, width=lw * 0.75, dash="dot"),
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
        fig.add_vrect(x0=x_lo, x1=x_hi, xref="x",
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

    fig.update_layout(
        xaxis=axis_layout(axes["x"], style, k,
                          data_min=float(np.min(v_cat)), data_max=float(np.max(v_cat)),
                          domain=x_dom),
        yaxis=axis_layout(
            axes["y"], style, k,
            data_min=float(np.floor(np.log10(np.min(i_pos)))) if i_pos.size else None,
            data_max=float(np.ceil(np.log10(np.max(i_pos)))) if i_pos.size else None,
            domain=y_dom),
        yaxis2=axis_layout(axes["y2"], style, k,
                           data_min=0.0,
                           data_max=float(np.max(s_pos)) * 1.05 if s_pos.size else None,
                           side="right", overlaying="y"),
    )
    apply_inset_text(fig, insets["sample"].get("text", ""), insets["sample"], style, k)
    return fig
