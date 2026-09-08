"""순간미분 그래프 — Transfer/Output 본 그래프와 같은 규약으로 그린다.

본 그래프의 배경 크기(geom)·서식(style)·X축 설정을 그대로 물려받고, Y축만
미분 종류에 맞춰 그때그때 만든다. 미분값은 종류에 따라 자릿수가 크게 달라져서
축 제목을 설정에 저장해 두면 오히려 어긋나기 때문이다.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from fet_app.derivative import (
    OUTPUT_MODE_TITLE, TRANSFER_MODES, output_series, transfer_series,
)
from fet_app.figure_common import (
    axis_layout, domains, fit_y_margins, new_figure,
)
from fet_app.figure_output import _add_legend_swatches, _fmt_vg, gradient_colors
from fet_app.markup import apply_markup


def _y_cfg(title: str, y_type: str) -> dict:
    return {"type": y_type, "auto": True, "min": None, "max": None,
            "dtick": 1 if y_type == "log" else None,
            "minor_dtick": "D1" if y_type == "log" else None,
            "title": title, "title_standoff": 20.0}


def _y_range(values: list[np.ndarray], y_type: str):
    """(data_min, data_max). log 축은 지수 단위, linear 축은 0 을 바닥으로 쓴다."""
    cat = np.concatenate(values) if values else np.array([np.nan])
    finite = cat[np.isfinite(cat)]
    if y_type == "log":
        pos = finite[finite > 0]
        if not pos.size:
            return None, None
        return (float(np.floor(np.log10(pos.min()))),
                float(np.ceil(np.log10(pos.max()))))
    if not finite.size:
        return None, None
    lo, hi = float(finite.min()), float(finite.max())
    pad = (hi - lo) * 0.05 or 1e-15
    return (0.0 if lo >= 0 else lo - pad), hi + pad


def _finish(fig: go.Figure, geom: dict, style: dict, x_cfg: dict, y_cfg: dict,
            k: float, x_vals: list[np.ndarray], y_vals: list[np.ndarray],
            y_type: str) -> list[float]:
    x_dom, y_dom = domains(geom)
    x_cat = np.concatenate(x_vals) if x_vals else np.array([0.0, 1.0])
    y_lo, y_hi = _y_range(y_vals, y_type)
    y_lay = axis_layout(y_cfg, style, k, data_min=y_lo, data_max=y_hi, domain=y_dom)
    x_dom = fit_y_margins(geom, x_dom, style, k, left_lay=y_lay)
    fig.update_layout(
        xaxis=axis_layout(x_cfg, style, k,
                          data_min=float(np.min(x_cat)), data_max=float(np.max(x_cat)),
                          domain=x_dom),
        yaxis=y_lay,
    )
    return x_dom


def transfer_derivative_figure(curve, params, settings: dict,
                               k: float = 1.0) -> go.Figure:
    """V_G 에 대한 포인트별 미분. mode 는 derivative.TRANSFER_MODES 참고."""
    geom, style = settings["geom"], settings["style"]
    axes, trace_cfg, deriv = settings["axes"], settings["trace"], settings["deriv"]

    mode = deriv.get("transfer_mode", "mu")
    smooth = int(deriv.get("smooth", 1) or 1)
    y_type = deriv.get("y_type", "linear")
    color = deriv.get("line_color", "#000000")
    lw = max(0.25, float(style["line_width"]) * k)

    fig = new_figure(geom, k)
    branches = [("forward", curve.forward, "solid")]
    if trace_cfg.get("show_reverse", True) and curve.reverse is not None:
        # 미분 그래프는 논문 그림이 아니라 진단용이라 방향을 선 종류로 구분한다
        # (본 그래프는 화살표로 구분한다 — figure_transfer 참고).
        branches.append(("reverse", curve.reverse, "dash"))

    x_vals, y_vals = [], []
    for label, df, dash in branches:
        series = transfer_series(df, mode, params, smooth)
        if series is None:
            continue
        x, y = series
        x_vals.append(x)
        y_vals.append(y)
        fig.add_trace(go.Scatter(
            x=x, y=y, name=f"{label} d", mode="lines",
            line=dict(color=color, width=lw, dash=dash), hoverinfo="skip",
        ))

    title = TRANSFER_MODES.get(mode, ("", False))[0]
    _finish(fig, geom, style, axes["x"], _y_cfg(title, y_type), k,
            x_vals, y_vals, y_type)
    return fig


def output_derivative_figure(curve, settings: dict, k: float = 1.0) -> go.Figure:
    """V_D 에 대한 포인트별 미분(출력 컨덕턴스). 색·레전드는 Output 그래프와 동일."""
    geom, style = settings["geom"], settings["style"]
    axes, trace_cfg = settings["axes"], settings["trace"]
    deriv, insets = settings["deriv"], settings["insets"]

    smooth = int(deriv.get("smooth", 1) or 1)
    y_type = deriv.get("y_type", "linear")
    lw = max(0.25, float(style["line_width"]) * k)

    fig = new_figure(geom, k)
    blocks = list(curve.blocks) if curve is not None else []
    colors = gradient_colors(trace_cfg.get("base_color", "#ed542b"), len(blocks),
                             float(trace_cfg.get("lightness_min", 0.18)),
                             float(trace_cfg.get("lightness_max", 0.82)))
    manual = trace_cfg.get("manual_colors", {}) or {}

    x_vals, y_vals, legend_rows = [], [], []
    for idx, b in enumerate(blocks):
        vg_str = _fmt_vg(b.v_g)
        color = manual.get(vg_str, colors[idx] if idx < len(colors) else "#000000")
        legend_rows.append((color, apply_markup(f"V_{{G}} = {vg_str} V")))
        pairs = [("forward", b.forward, "solid")]
        if trace_cfg.get("show_reverse", True) and b.reverse is not None:
            pairs.append(("reverse", b.reverse, "dash"))
        for branch, df, dash in pairs:
            series = output_series(df, smooth)
            if series is None:
                continue
            x, y = series
            x_vals.append(x)
            y_vals.append(y)
            fig.add_trace(go.Scatter(
                x=x, y=y, name=f"V_G = {vg_str} V {branch}", mode="lines",
                line=dict(color=color, width=lw, dash=dash), hoverinfo="skip",
            ))

    x_dom = _finish(fig, geom, style, axes["x"], _y_cfg(OUTPUT_MODE_TITLE, y_type), k,
                    x_vals, y_vals, y_type)
    _add_legend_swatches(fig, legend_rows, insets["legend"], geom, style, k, x_dom)
    return fig
