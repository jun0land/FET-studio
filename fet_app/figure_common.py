"""그래프 공통 규약 (스펙 §5.1).

논문용 흰 배경, 4면 mirror ticks, ticks inside, 그리드 없음, 1E-11 지수 표기.
크기는 Origin 방식 2단계: background inch x DPI, graph 는 % of background.
표시 배율 k 는 크기와 폰트·선두께에 동시에 곱해 화면에서만 축소한다 (스펙 §5.4).
"""

from __future__ import annotations

import math

import plotly.graph_objects as go

from fet_app.markup import apply_markup

DPI = 96

# Plotly 가 지수 표기(exponentformat="E") 대신 평범한 소수로 눈금을 찍는 구간.
# plotly 6.x 실측: 눈금 간격이 1E-4 이상이고 눈금 최댓값이 1E4 미만이면 평문이다
# (dtick 2E-4 -> "0.0002" / dtick 2E-5 -> "0.2E-4", 최댓값 5E3 -> "5000" / 1E4 -> "1E+4").
# tickformat 은 exponentformat 을 무시하고 이기므로, 이 구간 밖에서 소수 포맷을
# 씌우면 Output 의 I_D 축(1E-5 A)이 "-0.00007" 처럼 되어 오히려 읽기 어려워진다.
# 그래서 표기 방식은 그대로 두고 트레일링 zero 만 맞추도록 구간 안에서만 적용한다.
PLAIN_TICK_MIN_DTICK = 1e-4
PLAIN_TICK_MAX_VALUE = 1e4


def nice_dtick(data_min: float, data_max: float, target_ticks: int = 6) -> float | None:
    """축 범위에 맞는 1-2-5 계열의 '깔끔한' 눈금 간격. 범위가 없으면 None.

    Plotly 자동 선택에 맡기면 우리가 간격을 모르는 채로 눈금이 찍혀 소수
    자릿수를 맞출 수 없다 (0.008 다음이 0.01 로 나오는 문제). 그래서 직접 고른다.
    ``target_ticks`` 기본값 6 은 Example/ 실측에서 Plotly 의 기존 자동 선택과
    같은 간격(√|I_D| 축 0.002)이 나오도록 맞춘 값이다.
    """
    span = float(data_max) - float(data_min)
    if not math.isfinite(span) or span <= 0:
        return None
    raw_step = span / max(1, int(target_ticks))
    magnitude = 10.0 ** math.floor(math.log10(raw_step))
    residual = raw_step / magnitude
    if residual < 1.5:
        nice = 1
    elif residual < 3:
        nice = 2
    elif residual < 7:
        nice = 5
    else:
        nice = 10
    # 10 ** floor(...) 에서 생기는 부동소수점 찌꺼기를 턴다
    # (9.999999999999999e-06 같은 값이 dtick 으로 들어가면 눈금 라벨이 흔들린다).
    return float(f"{nice * magnitude:.6e}")


def tick_decimals(dtick: float) -> int:
    """눈금 간격에 맞춘 소수 자릿수. dtick >= 1 이면 0.

    1e-9 는 부동소수점 오차 방어용이다 (0.001 의 log10 이 -2.9999... 로 나올 때
    자릿수가 한 칸 밀리는 것을 막는다).
    """
    d = abs(float(dtick))
    if d <= 0 or not math.isfinite(d):
        return 0
    return max(0, -math.floor(math.log10(d) + 1e-9))


def _apply_tick_spacing(lay: dict, cfg: dict, lo, hi) -> None:
    """major dtick 과 그 간격에 맞춘 tickformat 을 정한다 (논문 스타일: 한 축의
    모든 눈금이 같은 소수 자릿수).

    log 축은 dtick 이 '몇 decade 마다' 라는 다른 의미이고 이미 exponentformat="E"
    로 지수 표기를 하므로 여기서 전혀 손대지 않는다. 사용자가(또는 기본값이)
    dtick 을 명시했으면 그 값을 그대로 존중하고 자릿수만 맞춘다.

    지수 표기 구간(PLAIN_TICK_* 밖)에서는 dtick 도 계산하지 않고 Plotly 자동
    선택에 그대로 맡긴다 — 자릿수를 고칠 수 없는 축의 눈금 위치를 굳이 바꿔
    기존 그림을 흔들 이유가 없다.
    """
    explicit = cfg.get("dtick")
    if explicit is not None:
        lay["dtick"] = explicit
    if cfg.get("type", "linear") != "linear" or lo is None or hi is None:
        return
    if max(abs(float(lo)), abs(float(hi))) >= PLAIN_TICK_MAX_VALUE:
        return

    dtick = explicit if explicit is not None else nice_dtick(float(lo), float(hi))
    try:
        d = abs(float(dtick))
    except (TypeError, ValueError):
        return
    if d < PLAIN_TICK_MIN_DTICK:
        return
    if explicit is None:
        lay["dtick"] = dtick
    lay["tickformat"] = f".{tick_decimals(d)}f"


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
                domain: list[float] | None = None,
                axis_color: str = "#000000") -> dict:
    """축 하나의 layout dict. 규약 위반이 없도록 여기서만 만든다.

    ``axis_color`` 는 축선·눈금·제목·눈금 글자에 함께 쓰인다. Transfer 의 이중
    Y축처럼 축마다 트레이스 색이 다를 때 축을 그 색에 맞추기 위한 것이고,
    기본값이 검정이라 넘기지 않는 호출부는 기존 동작 그대로다.
    """
    title_size = max(1, round(float(style["title_font_size"]) * k))
    tick_size = max(1, round(float(style["tick_font_size"]) * k))
    family = style["font_family"]

    lay: dict = {
        "type": cfg.get("type", "linear"),
        "title": {"text": apply_markup(cfg.get("title", "")),
                  "font": {"family": family, "size": title_size, "color": axis_color}},
        "tickfont": {"family": family, "size": tick_size, "color": axis_color},
        "showline": True,
        "linecolor": axis_color,
        "linewidth": max(0.5, 1.5 * k),
        "mirror": True,
        "ticks": "inside",
        "ticklen": max(2, round(8 * k)),
        "tickwidth": max(0.5, 1.5 * k),
        "tickcolor": axis_color,
        "showgrid": bool(style.get("show_grid", False)),
        "zeroline": False,
        "exponentformat": "E",
        "showexponent": "all",
        "automargin": False,
    }
    if cfg.get("title_standoff") is not None:
        lay["title"]["standoff"] = float(cfg["title_standoff"]) * k
    if cfg.get("minor_dtick") is not None:
        lay["minor"] = {"dtick": cfg["minor_dtick"], "ticks": "inside",
                        "ticklen": max(1, round(4 * k)),
                        "tickwidth": max(0.5, 1.0 * k), "tickcolor": axis_color}

    # 범위: auto 여도 데이터 min/max 를 명시해 plotly 자동 패딩을 없앤다 (스펙 §5.1)
    lo = cfg.get("min") if not cfg.get("auto", True) else data_min
    hi = cfg.get("max") if not cfg.get("auto", True) else data_max
    if lo is not None and hi is not None:
        lay["range"] = [lo, hi]
        lay["autorange"] = False

    # 눈금 간격/자릿수는 실제로 쓰이는 범위(lo/hi)를 알아야 정할 수 있으므로
    # 범위를 확정한 다음에 계산한다.
    _apply_tick_spacing(lay, cfg, lo, hi)

    if side:
        lay["side"] = side
    if overlaying:
        lay["overlaying"] = overlaying
    if domain:
        lay["domain"] = domain
    return lay


def plot_px_size(geom: dict, k: float = 1.0) -> tuple[float, float]:
    """플롯 영역(그래프 domain)의 픽셀 크기. 인셋 스와치 기하 계산에 쓴다.

    domain 비율은 k 와 무관하지만, 이 함수가 반환하는 픽셀 크기에는 k 가
    반영되어 있으므로 "픽셀 단위로 정한 크기(폰트 등)를 domain 비율로 환산"할 때
    분모로 쓰면 k 배율이 자동으로 맞아떨어진다.
    """
    w, h = px_size(geom, k)
    x_dom, y_dom = domains(geom)
    return w * (x_dom[1] - x_dom[0]), h * (y_dom[1] - y_dom[0])


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
        text=apply_markup(text),
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
