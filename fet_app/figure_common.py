"""그래프 공통 규약 (스펙 §5.1).

논문용 흰 배경, 4면 mirror ticks, ticks inside, 그리드 없음, 1E-11 지수 표기.
크기는 Origin 방식 2단계: background inch x DPI, graph 는 % of background.
표시 배율 k 는 크기와 폰트·선두께에 동시에 곱해 화면에서만 축소한다 (스펙 §5.4).
"""

from __future__ import annotations

import math

import numpy as np
import plotly.graph_objects as go

from fet_app.constants import (
    AXIS_TITLE_PAD, RIGHT_AXIS_TITLE_ANGLE, RIGHT_AXIS_TITLE_NAME, SWEEP_ARROW_HEAD_PX,
    SWEEP_ARROW_MARGIN, TICK_CHAR_W,
)
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


def tick_label_texts(lay: dict) -> list[str]:
    """축 layout 이 실제로 찍을 눈금 라벨(추정). 폭 계산에만 쓴다.

    Plotly 는 텍스트 폭을 우리에게 알려주지 않으므로 라벨 문자열을 우리가 직접
    재구성한다. tickformat 이 있으면(=평문 소수 구간) 그 자릿수로, 없으면
    지수 표기('2E-4')로 만든다 — _apply_tick_spacing 이 정하는 규칙 그대로다.
    """
    rng = lay.get("range")
    if not rng:
        return []
    lo, hi = float(min(rng)), float(max(rng))
    if lay.get("type") == "log":
        # 로그축은 range 가 지수(decade)다. 라벨은 '1E-11' 꼴.
        return [f"1E{e:+d}" for e in range(math.floor(lo), math.ceil(hi) + 1)]

    dtick = lay.get("dtick") or nice_dtick(lo, hi)
    try:
        step = abs(float(dtick))
    except (TypeError, ValueError):
        step = 0.0
    if step <= 0 or not math.isfinite(step):
        return [f"{lo:g}", f"{hi:g}"]

    fmt = lay.get("tickformat")
    decimals = None
    if isinstance(fmt, str) and fmt.startswith(".") and fmt.endswith("f"):
        try:
            decimals = int(fmt[1:-1])
        except ValueError:
            decimals = None

    out = []
    n = min(int((hi - lo) / step) + 2, 200)   # 눈금이 비정상적으로 촘촘해도 상한을 둔다
    for i in range(n):
        v = math.ceil(lo / step) * step + i * step
        if v > hi + step * 1e-6:
            break
        if decimals is not None:
            out.append(f"{v:.{decimals}f}")
        else:
            mant, exp = f"{v:.0E}".split("E")
            out.append(f"{mant}E{int(exp):+d}")
    return out or [f"{lo:g}", f"{hi:g}"]


def y_axis_space_px(lay: dict, style: dict, k: float = 1.0) -> float:
    """Y축 하나가 플롯 바깥에 필요로 하는 폭(px): 눈금 숫자 + standoff + 제목.

    Plotly 는 축 제목을 종이(paper) 안쪽으로 클램프하기 때문에, 여백이 모자라면
    standoff 를 아무리 키워도 제목이 눈금 숫자 위로 겹쳐 올라간다. 그래서
    '얼마나 필요한지'를 먼저 재고 fit_y_margins 가 플롯 영역을 그만큼 안쪽으로
    민다.
    """
    tick_px = max(1.0, float(style["tick_font_size"]) * k)
    title_px = max(1.0, float(style["title_font_size"]) * k)
    chars = max((len(t) for t in tick_label_texts(lay)), default=0)
    standoff = float(lay.get("title", {}).get("standoff", 0.0) or 0.0)
    has_title = bool(lay.get("title", {}).get("text"))
    need = chars * tick_px * TICK_CHAR_W + AXIS_TITLE_PAD * k
    if has_title:
        need += standoff + title_px + AXIS_TITLE_PAD * k
    return need


def rotate_right_axis_title(fig: go.Figure, lay: dict, style: dict, k: float,
                            geom: dict, x_dom, y_dom) -> None:
    """우측 Y축 제목을 270도(위에서 아래로 읽힘)로 돌린다. Origin 의 우축 기본값.

    Plotly 축 제목은 각도를 바꿀 수 없다 — 우축도 좌축과 똑같이 90도(아래에서
    위로)로만 그려진다. 그래서 제목을 축 layout 에서 떼어 내고(빈 문자열) 같은
    글꼴·색의 annotation 으로 다시 그린다. ``textangle=90`` 은 Plotly 기준 시계
    방향 90도 = Origin 의 270도다.

    자리는 fit_y_margins 가 '눈금 라벨 폭 + standoff + 제목 폭' 으로 이미 확보해
    둔 여백 안이다: 축선에서 라벨 폭과 standoff 만큼 떨어진 곳에 제목 높이의
    절반을 더한 지점을 회전 중심으로 잡는다. 반드시 fit_y_margins **다음에**
    불러야 한다 — 이 함수가 제목을 비우면 그 뒤로는 여백 계산에 제목이 빠진다.
    """
    text = (lay.get("title") or {}).get("text") or ""
    if not text:
        return
    page_w = float(px_size(geom, k)[0])
    if page_w <= 0:
        return
    tick_px = max(1.0, float(style["tick_font_size"]) * k)
    title_px = max(1.0, float(style["title_font_size"]) * k)
    chars = max((len(t) for t in tick_label_texts(lay)), default=0)
    standoff = float(lay["title"].get("standoff", 0.0) or 0.0)
    x_px = (float(x_dom[1]) * page_w + chars * tick_px * TICK_CHAR_W
            + AXIS_TITLE_PAD * k + standoff + title_px / 2)
    fig.add_annotation(
        x=min(1.0, x_px / page_w), y=(float(y_dom[0]) + float(y_dom[1])) / 2,
        xref="paper", yref="paper", xanchor="center", yanchor="middle",
        text=text, textangle=RIGHT_AXIS_TITLE_ANGLE, showarrow=False,
        font=dict(lay["title"].get("font", {})),
        name=RIGHT_AXIS_TITLE_NAME,
    )
    lay["title"]["text"] = ""


def fit_y_margins(geom: dict, x_dom: list[float], style: dict, k: float = 1.0,
                  left_lay: dict | None = None, right_lay: dict | None = None,
                  min_width: float = 0.30) -> list[float]:
    """Y축 제목이 눈금 숫자와 겹치지 않도록 x domain 을 안쪽으로 민 값.

    사용자가 정한 여백(geom 의 graph_left_pct/width)이 이미 넉넉하면 그대로
    돌려준다 — 좁을 때만 줄인다. 플롯이 지나치게 납작해지지 않도록 폭은
    ``min_width`` 아래로 내려가지 않게 하고, 그 경우 좌/우가 필요로 하는 양의
    비율대로 남은 여백을 나눈다.
    """
    page_w = float(px_size(geom, k)[0])
    if page_w <= 0:
        return list(x_dom)
    need_l = (y_axis_space_px(left_lay, style, k) / page_w) if left_lay else 0.0
    need_r = (y_axis_space_px(right_lay, style, k) / page_w) if right_lay else 0.0

    left = max(float(x_dom[0]), need_l)
    right = min(float(x_dom[1]), 1.0 - need_r)
    if right - left < min_width:
        total = need_l + need_r
        slack = max(0.0, 1.0 - min_width)
        if total > 0:
            left = slack * need_l / total
            right = 1.0 - slack * need_r / total
        else:
            left, right = (1.0 - min_width) / 2, (1.0 + min_width) / 2
    return [round(left, 6), round(right, 6)]


def plot_px_size(geom: dict, k: float = 1.0,
                 x_dom: list[float] | None = None,
                 y_dom: list[float] | None = None) -> tuple[float, float]:
    """플롯 영역(그래프 domain)의 픽셀 크기. 인셋 스와치 기하 계산에 쓴다.

    domain 비율은 k 와 무관하지만, 이 함수가 반환하는 픽셀 크기에는 k 가
    반영되어 있으므로 "픽셀 단위로 정한 크기(폰트 등)를 domain 비율로 환산"할 때
    분모로 쓰면 k 배율이 자동으로 맞아떨어진다.

    ``x_dom``/``y_dom`` 을 넘기면 geom 대신 그 domain 을 쓴다 — fit_y_margins 가
    축 제목 자리를 만드느라 domain 을 안쪽으로 민 경우, 인셋도 그 실제 플롯
    영역을 기준으로 놓아야 하기 때문이다.
    """
    w, h = px_size(geom, k)
    gx, gy = domains(geom)
    x_dom = gx if x_dom is None else x_dom
    y_dom = gy if y_dom is None else y_dom
    return w * (x_dom[1] - x_dom[0]), h * (y_dom[1] - y_dom[0])


def _clamp_frac(v: float) -> float:
    """화살표가 플롯 경계(축선) 밖으로 삐져나가지 않게 domain 안쪽으로 자른다."""
    return float(min(1.0 - SWEEP_ARROW_MARGIN, max(SWEEP_ARROW_MARGIN, v)))


def add_curved_arrow(fig: go.Figure, pts, plot_w_px: float, plot_h_px: float,
                     color: str, width: float, k: float = 1.0) -> None:
    """domain 비율 폴리라인(마지막 점이 화살촉 끝)을 굽은 화살표로 그린다.

    Plotly 에는 '굽은 화살표'가 없다. 그래서 몸통은 path shape 으로 커브 모양을
    그대로 따라 그리고, 화살촉만 마지막 구간의 접선 방향으로 짧은 annotation
    화살표를 얹어 만든다. 좌표는 전부 x/y domain 비율이라 축 종류(log/linear)와
    무관하고, 화살촉 꼬리 길이만 픽셀이라 k 배율을 곱해 준다.
    """
    pts = [(_clamp_frac(x), _clamp_frac(y)) for x, y in pts
           if math.isfinite(x) and math.isfinite(y)]
    if len(pts) < 2:
        return
    path = "M " + " L ".join(f"{x:.5f},{y:.5f}" for x, y in pts)
    fig.add_shape(type="path", path=path, xref="x domain", yref="y domain",
                  layer="above", line=dict(color=color, width=width))

    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    dx, dy = (x1 - x0) * plot_w_px, (y1 - y0) * plot_h_px   # px, y 는 위쪽이 +
    norm = math.hypot(dx, dy)
    if norm <= 0:
        return
    tail = SWEEP_ARROW_HEAD_PX * k
    # ax/ay 는 화살촉 기준 꼬리의 화면 픽셀 오프셋 — 화면 y 는 아래쪽이 +라
    # 부호가 뒤집힌다.
    fig.add_annotation(
        x=x1, y=y1, xref="x domain", yref="y domain",
        axref="pixel", ayref="pixel", ax=-dx / norm * tail, ay=dy / norm * tail,
        text="", showarrow=True, arrowhead=2, arrowsize=1.2,
        arrowwidth=width, arrowcolor=color,
    )


def curve_arrow_points(fx, fy, plot_w_px: float, plot_h_px: float,
                       skip: float, length: float, offset: float,
                       from_start: bool, n_out: int = 12):
    """커브를 따라가는 화살표 몸통 좌표(domain 비율)를 뽑는다.

    ``from_start`` 가 True 면 커브의 첫 점(=반환점에서 출발하는 reverse)에서
    시작해 진행 방향으로, False 면 마지막 점(=반환점으로 들어오는 forward)을
    향해 나아가는 순서로 돌려준다. 어느 쪽이든 **마지막 점이 화살촉**이다.

    거리는 플롯 영역의 짧은 변 대비 비율이다 — x/y 데이터 단위가 서로 완전히
    다르므로(V 와 A) 화면 픽셀 공간에서 재야 눈에 보이는 길이가 맞는다.
    ``offset`` 은 커브에서 수직으로 띄우는 거리로, forward/reverse 를 서로 반대
    부호로 주면 두 화살표가 커브 양옆에 나란히 놓인다.
    """
    fx = np.asarray(fx, dtype=float)
    fy = np.asarray(fy, dtype=float)
    ok = np.isfinite(fx) & np.isfinite(fy)
    fx, fy = fx[ok], fy[ok]
    if fx.size < 3:
        return []
    if not from_start:                      # 반환점을 향해 가는 쪽
        fx, fy = fx[::-1], fy[::-1]         # 항상 '반환점에서 바깥으로' 로 맞춘다

    unit = min(plot_w_px, plot_h_px)
    px, py = fx * plot_w_px, fy * plot_h_px
    seg = np.hypot(np.diff(px), np.diff(py))
    dist = np.concatenate(([0.0], np.cumsum(seg))) / max(unit, 1e-9)

    lo, hi = skip, skip + length
    sel = np.flatnonzero((dist >= lo) & (dist <= hi))
    if sel.size < 3:
        # 커브가 짧아 구간이 안 잡히면 앞쪽 일부라도 쓴다.
        sel = np.arange(min(fx.size, 5))
    idx = np.unique(np.linspace(sel[0], sel[-1], min(n_out, sel.size)).round().astype(int))
    if idx.size < 2:
        return []

    ox, oy = fx[idx], fy[idx]
    # 수직 오프셋: 각 점의 접선을 픽셀 공간에서 구해 법선 방향으로 민다.
    tx = np.gradient(ox * plot_w_px)
    ty = np.gradient(oy * plot_h_px)
    tn = np.hypot(tx, ty)
    tn[tn == 0] = 1.0
    nx, ny = -ty / tn, tx / tn
    ox = ox + nx * offset * unit / plot_w_px
    oy = oy + ny * offset * unit / plot_h_px

    pts = list(zip(ox.tolist(), oy.tolist()))
    if not from_start:
        pts.reverse()          # forward 는 반환점 쪽이 화살촉이 되도록 되돌린다
    return pts


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
