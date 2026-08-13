"""Output 그래프 — 단색 순차 그라데이션 (스펙 §5.3).

명도를 단조 감소시켜 흑백 인쇄·색약 조건에서도 V_G 순서가 유지되게 한다.
"""

from __future__ import annotations

import colorsys
import re

import numpy as np
import plotly.graph_objects as go

from fet_app.constants import INSET_GAP, INSET_PAD_X, INSET_SWATCH_W, hex_to_rgba
from fet_app.figure_common import apply_inset_text, axis_layout, domains, new_figure, plot_px_size
from fet_app.markup import apply_markup


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


def _plain_len(html: str) -> int:
    """스와치 옆 라벨 폭 추정용 — 태그를 걷어낸 대략적 글자 수."""
    out = html
    for tag in ("<b>", "</b>", "<i>", "</i>", "<sup>", "</sup>", "<sub>", "</sub>"):
        out = out.replace(tag, "")
    return len(re.sub(r"<span[^>]*>|</span>", "", out))


def _add_legend_swatches(fig: go.Figure, rows: list[tuple[str, str]], inset: dict,
                         geom: dict, style: dict, k: float) -> None:
    """레전드 항목마다 곡선 색의 선 스와치 + 라벨을 세로로 쌓아 그린다 (스펙 §5.3 보완).

    x domain/y domain 좌표계에서 픽셀 단위 폰트 크기를 plot 영역 픽셀 크기(k 반영)로
    나눠 domain 비율로 환산하므로, k 가 달라져도 스와치·간격이 폰트에 비례해 맞는다.
    """
    if not rows:
        return
    plot_w_px, plot_h_px = plot_px_size(geom, k)
    if plot_h_px <= 0:
        return
    fs_px = max(1, round(float(inset.get("font_size", 30)) * k))
    row_h_px = [fs_px * (1.75 if ("<sup>" in html or "<sub>" in html) else 1.5)
               for _color, html in rows]
    total_h = sum(row_h_px) / plot_h_px

    x, y = float(inset["x"]), float(inset["y"])
    xanchor = inset.get("xanchor", "right")
    yanchor = inset.get("yanchor", "top")
    top = y if yanchor == "top" else (y + total_h / 2 if yanchor == "middle" else y + total_h)

    max_chars = max((_plain_len(html) for _color, html in rows), default=0)
    text_w = (max_chars * fs_px * 0.55 / plot_w_px) if plot_w_px > 0 else 0.0
    block_w = 2 * INSET_PAD_X + INSET_SWATCH_W + INSET_GAP + text_w
    left = x if xanchor == "left" else (x - block_w / 2 if xanchor == "center" else x - block_w)

    if inset.get("border") or inset.get("bg_opacity"):
        fig.add_shape(
            type="rect", xref="x domain", yref="y domain", layer="below",
            x0=left, x1=left + block_w, y0=top - total_h, y1=top,
            fillcolor=hex_to_rgba("#FFFFFF", float(inset.get("bg_opacity") or 0.0)),
            line=dict(color="#000000" if inset.get("border") else "rgba(0,0,0,0)",
                      width=max(0.5, 1.0 * k) if inset.get("border") else 0),
        )

    cursor = top
    for (color, html), h_px in zip(rows, row_h_px):
        h_dom = h_px / plot_h_px
        cy = cursor - h_dom / 2
        x0 = left + INSET_PAD_X
        x1 = x0 + INSET_SWATCH_W
        fig.add_shape(
            type="line", xref="x domain", yref="y domain", layer="above",
            x0=x0, x1=x1, y0=cy, y1=cy,
            line=dict(color=color, width=max(0.5, float(style["line_width"]) * k)),
        )
        fig.add_annotation(
            x=x1 + INSET_GAP, y=cy, xref="x domain", yref="y domain",
            xanchor="left", yanchor="middle", text=html,
            showarrow=False, align="left",
            font=dict(family=style["font_family"], size=fs_px, color="#000000"),
        )
        cursor -= h_dom


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

    all_x, all_y, legend_rows = [], [], []
    for idx, b in enumerate(blocks):
        vg_str = _fmt_vg(b.v_g)
        # 주의: manual_colors 조회 키는 항상 순수 숫자 문자열이어야 한다 — 마크업이
        # 적용된 라벨을 키로 쓰면 조회가 깨진다. label 은 트레이스 name(내부 식별자)
        # 이라 마크업을 적용하지 않고, 레전드 표시용 문구만 따로 마크업을 적용한다.
        color = manual.get(vg_str, colors[idx] if idx < len(colors) else "#000000")
        label = f"V_G = {vg_str} V"
        legend_rows.append((color, apply_markup(f"V_{{G}} = {vg_str} V")))

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

    # 인셋 레전드 — V_G 목록 (색 스와치 + 라벨, 세로로 쌓기)
    _add_legend_swatches(fig, legend_rows, insets["legend"], geom, style, k)
    apply_inset_text(fig, insets["sample"].get("text", ""), insets["sample"], style, k)
    return fig
