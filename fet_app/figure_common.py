"""그래프 공통 규약 (스펙 §5.1).

논문용 흰 배경, 4면 mirror ticks, ticks inside, 그리드 없음, 1E-11 지수 표기.
크기는 Origin 방식 2단계: background inch x DPI, graph 는 % of background.
표시 배율 k 는 크기와 폰트·선두께에 동시에 곱해 화면에서만 축소한다 (스펙 §5.4).
"""

from __future__ import annotations

import plotly.graph_objects as go

DPI = 96


def px_size(geom: dict, k: float = 1.0) -> tuple[int, int]:
    return (int(round(float(geom["page_w_in"]) * DPI * k)),
            int(round(float(geom["page_h_in"]) * DPI * k)))


def domains(geom: dict) -> tuple[list[float], list[float]]:
    """graph 의 %(좌/상/폭/높이) -> plotly domain. Top 은 위에서부터 잰다."""
    left = float(geom["graph_left_pct"]) / 100.0
    top = float(geom["graph_top_pct"]) / 100.0
    width = float(geom["graph_width_pct"]) / 100.0
    height = float(geom["graph_height_pct"]) / 100.0
    x_dom = [round(left, 6), round(left + width, 6)]
    y_dom = [round(1.0 - (top + height), 6), round(1.0 - top, 6)]
    return x_dom, y_dom


def axis_layout(cfg: dict, style: dict, k: float = 1.0,
                data_min: float | None = None, data_max: float | None = None,
                side: str | None = None, overlaying: str | None = None,
                domain: list[float] | None = None) -> dict:
    """축 하나의 layout dict. 규약 위반이 없도록 여기서만 만든다."""
    title_size = max(1, round(float(style["title_font_size"]) * k))
    tick_size = max(1, round(float(style["tick_font_size"]) * k))
    family = style["font_family"]

    lay: dict = {
        "type": cfg.get("type", "linear"),
        "title": {"text": cfg.get("title", ""),
                  "font": {"family": family, "size": title_size, "color": "#000000"}},
        "tickfont": {"family": family, "size": tick_size, "color": "#000000"},
        "showline": True,
        "linecolor": "#000000",
        "linewidth": max(0.5, 1.5 * k),
        "mirror": True,
        "ticks": "inside",
        "ticklen": max(2, round(8 * k)),
        "tickwidth": max(0.5, 1.5 * k),
        "tickcolor": "#000000",
        "showgrid": bool(style.get("show_grid", False)),
        "zeroline": False,
        "exponentformat": "E",
        "showexponent": "all",
        "automargin": False,
    }
    if cfg.get("title_standoff") is not None:
        lay["title"]["standoff"] = float(cfg["title_standoff"]) * k
    if cfg.get("dtick") is not None:
        lay["dtick"] = cfg["dtick"]
    if cfg.get("minor_dtick") is not None:
        lay["minor"] = {"dtick": cfg["minor_dtick"], "ticks": "inside",
                        "ticklen": max(1, round(4 * k)),
                        "tickwidth": max(0.5, 1.0 * k), "tickcolor": "#000000"}

    # 범위: auto 여도 데이터 min/max 를 명시해 plotly 자동 패딩을 없앤다 (스펙 §5.1)
    lo = cfg.get("min") if not cfg.get("auto", True) else data_min
    hi = cfg.get("max") if not cfg.get("auto", True) else data_max
    if lo is not None and hi is not None:
        lay["range"] = [lo, hi]
        lay["autorange"] = False

    if side:
        lay["side"] = side
    if overlaying:
        lay["overlaying"] = overlaying
    if domain:
        lay["domain"] = domain
    return lay


def new_figure(geom: dict, k: float = 1.0) -> go.Figure:
    w, h = px_size(geom, k)
    fig = go.Figure()
    fig.update_layout(
        width=w, height=h,
        margin=dict(l=0, r=0, t=0, b=0, pad=0),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        showlegend=False,
    )
    return fig


def apply_inset_text(fig: go.Figure, text: str, inset: dict,
                     style: dict, k: float = 1.0) -> None:
    """인셋 텍스트를 플롯 영역 기준(domain)으로 배치한다."""
    if not text:
        return
    fig.add_annotation(
        text=text,
        xref="x domain", yref="y domain",
        x=float(inset["x"]), y=float(inset["y"]),
        xanchor=inset.get("xanchor", "left"), yanchor=inset.get("yanchor", "bottom"),
        showarrow=False, align="left",
        font=dict(family=style["font_family"],
                  size=max(1, round(float(inset.get("font_size", 30)) * k)),
                  color="#000000"),
        bgcolor="rgba(255,255,255,0)" if not inset.get("bg_opacity") else "#FFFFFF",
        bordercolor="#000000" if inset.get("border") else None,
        borderwidth=1 if inset.get("border") else 0,
    )
