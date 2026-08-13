"""Output 그래프 — 단색 순차 그라데이션 (스펙 §5.3).

명도를 단조 감소시켜 흑백 인쇄·색약 조건에서도 V_G 순서가 유지되게 한다.
"""

from __future__ import annotations

import colorsys

import numpy as np
import plotly.graph_objects as go

from fet_app.figure_common import axis_layout, domains, new_figure


def _hex_to_rgb01(hex_color: str) -> tuple[float, float, float]:
    h = str(hex_color).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _rgb01_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02X}" for c in rgb)


def _fmt_vg(v_g: float) -> str:
    """-0.0 이 '-0' 으로 표기되는 것을 막는다 (부동소수점 음의 0)."""
    return f"{0.0 if v_g == 0 else v_g:g}"


def relative_luminance(hex_color: str) -> float:
    """WCAG 상대 휘도. 흑백 변환 시 순서 검증에 쓴다."""
    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (_lin(c) for c in _hex_to_rgb01(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def gradient_colors(base_hex: str, n: int,
                    l_min: float = 0.18, l_max: float = 0.82) -> list[str]:
    """base 색의 색상·채도를 유지한 채 명도만 l_max -> l_min 으로 단조 감소."""
    if n <= 0:
        return []
    if n == 1:
        return [base_hex]
    r, g, b = _hex_to_rgb01(base_hex)
    h, _l, s = colorsys.rgb_to_hls(r, g, b)
    out = []
    for i in range(n):
        li = l_max - (l_max - l_min) * (i / (n - 1))
        out.append(_rgb01_to_hex(colorsys.hls_to_rgb(h, li, s)))
    return out


def output_figure(curve, settings: dict, k: float = 1.0) -> go.Figure:
    geom, style = settings["geom"], settings["style"]
    axes, trace_cfg, insets = settings["axes"], settings["trace"], settings["insets"]

    fig = new_figure(geom, k)
    x_dom, y_dom = domains(geom)
    lw = max(0.25, float(style["line_width"]) * k)

    blocks = list(curve.blocks) if curve is not None else []
    colors = gradient_colors(trace_cfg.get("base_color", "#ed542b"), len(blocks),
                             float(trace_cfg.get("lightness_min", 0.18)),
                             float(trace_cfg.get("lightness_max", 0.82)))
    manual = trace_cfg.get("manual_colors", {}) or {}

    all_x, all_y, legend_lines = [], [], []
    for idx, b in enumerate(blocks):
        vg_str = _fmt_vg(b.v_g)
        color = manual.get(vg_str, colors[idx] if idx < len(colors) else "#000000")
        label = f"V_G = {vg_str} V"
        legend_lines.append(label)

        pairs = [("forward", b.forward, "solid")]
        if trace_cfg.get("show_reverse", True) and b.reverse is not None:
            pairs.append(("reverse", b.reverse, "dash"))
        for branch, df, dash in pairs:
            x = df["V_D"].to_numpy(dtype=float)
            y = df["I_D"].to_numpy(dtype=float)
            all_x.append(x)
            all_y.append(y)
            fig.add_trace(go.Scatter(
                x=x, y=y, name=f"{label} {branch}", mode="lines",
                line=dict(color=color, width=lw, dash=dash), hoverinfo="skip",
            ))

    x_cat = np.concatenate(all_x) if all_x else np.array([0.0, 1.0])
    y_cat = np.concatenate(all_y) if all_y else np.array([0.0, 1.0])
    y_lo, y_hi = float(np.min(y_cat)), float(np.max(y_cat))
    pad = (y_hi - y_lo) * 0.05 or 1e-12

    fig.update_layout(
        xaxis=axis_layout(axes["x"], style, k,
                          data_min=float(np.min(x_cat)), data_max=float(np.max(x_cat)),
                          domain=x_dom),
        yaxis=axis_layout(axes["y"], style, k,
                          data_min=y_lo - pad, data_max=y_hi + pad, domain=y_dom),
    )

    # 인셋 레전드 — V_G 목록
    inset = insets["legend"]
    fig.add_annotation(
        text="<br>".join(legend_lines),
        xref="x domain", yref="y domain",
        x=float(inset["x"]), y=float(inset["y"]),
        xanchor=inset.get("xanchor", "right"), yanchor=inset.get("yanchor", "top"),
        showarrow=False, align="left",
        font=dict(family=style["font_family"],
                  size=max(1, round(float(inset.get("font_size", 30)) * k)),
                  color="#000000"),
        bgcolor="rgba(255,255,255,0)",
        borderwidth=1 if inset.get("border") else 0,
        bordercolor="#000000" if inset.get("border") else None,
    )
    sample = insets["sample"]
    if sample.get("text"):
        fig.add_annotation(
            text=sample["text"], xref="x domain", yref="y domain",
            x=float(sample["x"]), y=float(sample["y"]),
            xanchor=sample.get("xanchor", "left"), yanchor=sample.get("yanchor", "bottom"),
            showarrow=False,
            font=dict(family=style["font_family"],
                      size=max(1, round(float(sample.get("font_size", 30)) * k)),
                      color="#000000"),
        )
    return fig
