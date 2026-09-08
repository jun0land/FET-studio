import copy
import math

import numpy as np
import plotly.graph_objects as go
import pytest

from fet_app.constants import DEFAULTS
from fet_app.figure_common import (DPI, add_curved_arrow, apply_inset_text,
                                   axis_layout, curve_arrow_points, domains,
                                   fit_y_margins, new_figure, nice_dtick,
                                   plot_px_size, px_size, tick_decimals,
                                   tick_label_texts, y_axis_space_px)


def test_px_size_uses_96_dpi():
    """Transfer/Output 은 배경 크기를 따로 갖는다 — 기본값은 8x10 / 10x8."""
    assert px_size(DEFAULTS["output_geom"], 1.0) == (int(10 * DPI), int(8 * DPI)) == (960, 768)
    assert px_size(DEFAULTS["transfer_geom"], 1.0) == (int(8 * DPI), int(10 * DPI)) == (768, 960)


def test_px_size_scales():
    assert px_size(DEFAULTS["output_geom"], 0.5) == (480, 384)
    assert px_size(DEFAULTS["transfer_geom"], 0.5) == (384, 480)


def test_domains_from_percentages():
    geom = {"graph_left_pct": 20.0, "graph_top_pct": 10.0,
            "graph_width_pct": 60.0, "graph_height_pct": 70.0}
    x_dom, y_dom = domains(geom)
    assert x_dom == [0.2, 0.8]
    # Top 은 위에서부터이므로 y_domain = [1-(T+H), 1-T]
    assert y_dom == [0.2, 0.9]


def test_axis_layout_paper_conventions():
    cfg = copy.deepcopy(DEFAULTS["transfer_axes"]["y"])
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0)
    assert lay["type"] == "log"
    assert lay["mirror"] is True          # 4면 박스
    assert lay["ticks"] == "inside"
    assert lay["showgrid"] is False
    assert lay["exponentformat"] == "E"   # 1E-11 형식
    assert lay["showexponent"] == "all"
    assert lay["zeroline"] is False


def test_axis_layout_scales_fonts():
    lay = axis_layout(DEFAULTS["transfer_axes"]["x"], DEFAULTS["style"], k=0.5)
    assert lay["title"]["font"]["size"] == 15   # 30 * 0.5
    assert lay["tickfont"]["size"] == 15


def test_axis_layout_auto_range_has_no_padding():
    cfg = dict(DEFAULTS["transfer_axes"]["x"])
    cfg["auto"] = True
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0, data_min=-60.0, data_max=20.0)
    assert lay["range"] == [-60.0, 20.0]
    assert lay["autorange"] is False


def test_axis_layout_manual_range_wins():
    cfg = dict(DEFAULTS["transfer_axes"]["x"])
    cfg.update({"auto": False, "min": -50.0, "max": 10.0})
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0, data_min=-60.0, data_max=20.0)
    assert lay["range"] == [-50.0, 10.0]


def test_axis_layout_defaults_to_black():
    """axis_color 를 안 넘기는 기존 호출부는 동작이 바뀌지 않아야 한다."""
    lay = axis_layout(DEFAULTS["output_axes"]["y"], DEFAULTS["style"], k=1.0)
    assert lay["linecolor"] == "#000000"
    assert lay["tickcolor"] == "#000000"
    assert lay["title"]["font"]["color"] == "#000000"
    assert lay["tickfont"]["color"] == "#000000"


def test_axis_layout_axis_color_applies_to_line_ticks_and_fonts():
    cfg = copy.deepcopy(DEFAULTS["transfer_axes"]["y"])   # minor_dtick 이 있는 축
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0, axis_color="#FF0000")
    assert lay["linecolor"] == "#FF0000"
    assert lay["tickcolor"] == "#FF0000"
    assert lay["title"]["font"]["color"] == "#FF0000"
    assert lay["tickfont"]["color"] == "#FF0000"
    assert lay["minor"]["tickcolor"] == "#FF0000"


def test_new_figure_is_white_and_unmargined():
    fig = new_figure(DEFAULTS["output_geom"], k=1.0)
    assert fig.layout.paper_bgcolor == "#FFFFFF"
    assert fig.layout.plot_bgcolor == "#FFFFFF"
    assert fig.layout.margin.l == 0
    assert fig.layout.showlegend is False


def test_axis_layout_title_runs_through_markup():
    """FIX 1 — 축 제목 마크업(`_{...}`/`^{...}`)이 Plotly HTML 로 확장돼야 한다."""
    cfg = dict(DEFAULTS["transfer_axes"]["x"])
    cfg["title"] = "V_{G} (V)"
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0)
    assert lay["title"]["text"] == "V<sub>G</sub> (V)"


def test_apply_inset_text_runs_through_markup():
    fig = go.Figure()
    inset = dict(DEFAULTS["insets"]["sample"])
    apply_inset_text(fig, "**Sample**-1_{a}", inset, DEFAULTS["style"], k=1.0)
    assert fig.layout.annotations[0].text == "<b>Sample</b>-1<sub>a</sub>"


def test_apply_inset_text_skips_empty_text():
    fig = go.Figure()
    inset = dict(DEFAULTS["insets"]["sample"])
    apply_inset_text(fig, "", inset, DEFAULTS["style"], k=1.0)
    assert fig.layout.annotations == ()


def test_plot_px_size_matches_domain_fraction_of_page():
    geom = DEFAULTS["output_geom"]
    w, h = px_size(geom, 1.0)
    x_dom, y_dom = domains(geom)
    plot_w, plot_h = plot_px_size(geom, 1.0)
    assert plot_w == w * (x_dom[1] - x_dom[0])
    assert plot_h == h * (y_dom[1] - y_dom[0])


def test_plot_px_size_scales_with_k():
    geom = DEFAULTS["output_geom"]
    full = plot_px_size(geom, 1.0)
    half = plot_px_size(geom, 0.5)
    assert half[0] == full[0] / 2
    assert half[1] == full[1] / 2


# ---------------- 눈금 간격 · 소수 자릿수 (FIX: 축 눈금 자릿수 불일치) ----------------
# 배경: √|I_D| 축이 "0.002 … 0.008, 0.01" 처럼 마지막 눈금만 트레일링 zero 가 잘려
# 나왔다. Plotly 가 자동으로 고른 간격을 우리가 몰라서 tickformat 을 못 걸었기
# 때문이다. 이제 linear 축은 간격을 직접 정하고(1-2-5) 그 자릿수로 포맷을 건다.

def test_nice_dtick_is_from_the_1_2_5_family():
    for lo, hi in [(0.0, 0.01), (0.0, 0.0121727), (-60.0, 20.0), (0.0, 7.3),
                   (-1.5e-3, 4.2e-3), (0.0, 3300.0)]:
        d = nice_dtick(lo, hi)
        mantissa = d / 10 ** math.floor(math.log10(d))
        assert round(mantissa, 6) in (1.0, 2.0, 5.0, 10.0), (lo, hi, d)
        # 눈금이 3~12 칸이면 '익숙한' 밀도다
        assert 3 <= (hi - lo) / d <= 12, (lo, hi, d)


def test_nice_dtick_matches_plotly_choice_on_example_range():
    """Example/ 1-1 의 √|I_D| 축 범위. Plotly 가 고르던 0.002 와 같아야 눈금 위치가
    안 바뀐다 (자릿수만 0.01 -> 0.010 으로 고쳐지는 것이 목적)."""
    assert nice_dtick(0.0, 0.012172713847556214) == 0.002
    assert nice_dtick(0.0, 0.01) == 0.002
    assert nice_dtick(0.0, 0.009582030119060723) == 0.002


def test_nice_dtick_needs_a_positive_span():
    assert nice_dtick(1.0, 1.0) is None
    assert nice_dtick(2.0, 1.0) is None


def test_tick_decimals_follows_the_spacing():
    assert tick_decimals(0.002) == 3
    assert tick_decimals(0.001) == 3
    assert tick_decimals(0.01) == 2
    assert tick_decimals(0.1) == 1
    assert tick_decimals(1.0) == 0
    assert tick_decimals(20.0) == 0
    assert tick_decimals(0.0002) == 4


def test_linear_auto_axis_gets_explicit_dtick_and_matching_tickformat():
    cfg = copy.deepcopy(DEFAULTS["transfer_axes"]["y2"])   # dtick=None (자동)
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0,
                      data_min=0.0, data_max=0.012172713847556214)
    assert lay["dtick"] == 0.002
    assert lay["tickformat"] == ".3f"     # 0.000 0.002 … 0.010 0.012


def test_explicit_dtick_is_respected_and_only_the_format_is_derived():
    """사용자가/기본값이 넣은 dtick 은 절대 덮어쓰지 않는다."""
    cfg = copy.deepcopy(DEFAULTS["transfer_axes"]["x"])    # dtick=20.0
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0, data_min=-60.0, data_max=20.0)
    assert lay["dtick"] == 20.0
    assert lay["tickformat"] == ".0f"


def test_log_axis_is_untouched():
    """log 축의 dtick 은 '몇 decade 마다' 라는 다른 의미다. nice-number 를 적용하면
    안 되고, 지수 표기는 exponentformat="E" 가 이미 맡고 있다."""
    cfg = copy.deepcopy(DEFAULTS["transfer_axes"]["y"])    # type=log, dtick=1
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0, data_min=-9.0, data_max=-3.0)
    assert lay["dtick"] == 1
    assert "tickformat" not in lay
    assert lay["exponentformat"] == "E"


def test_exponent_range_axis_keeps_plotly_defaults():
    """Output 의 I_D 축(~1E-5 A)에 소수 포맷을 씌우면 '-0.00007' 이 되어 오히려
    못 읽는다. 지수 표기 구간에서는 dtick 도 계산하지 않고 그대로 둔다."""
    cfg = copy.deepcopy(DEFAULTS["output_axes"]["y"])
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0,
                      data_min=-7.712e-05, data_max=4.068e-06)
    assert "dtick" not in lay
    assert "tickformat" not in lay


def test_large_value_axis_keeps_plotly_defaults():
    """눈금 최댓값이 1E4 이상이면 Plotly 가 지수 표기로 넘어간다 — 건드리지 않는다."""
    cfg = copy.deepcopy(DEFAULTS["output_axes"]["y"])
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0, data_min=0.0, data_max=5e5)
    assert "dtick" not in lay
    assert "tickformat" not in lay


def test_no_range_means_no_computed_dtick():
    """범위를 모르면 간격을 정할 수 없다 (빈 커브 방어)."""
    cfg = copy.deepcopy(DEFAULTS["transfer_axes"]["y2"])
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0)
    assert "dtick" not in lay
    assert "tickformat" not in lay


def test_title_standoff_defaults_are_set_and_scale_with_k():
    """FIX: 축 제목이 눈금 숫자에 바짝 붙던 문제 — 기본값을 None(=Plotly 기본
    15 px 상당)에서 20 px 로 올렸다."""
    assert DEFAULTS["transfer_axes"]["y"]["title_standoff"] == 20.0
    assert DEFAULTS["transfer_axes"]["y2"]["title_standoff"] == 20.0
    assert DEFAULTS["output_axes"]["y"]["title_standoff"] == 20.0
    lay = axis_layout(DEFAULTS["transfer_axes"]["y2"], DEFAULTS["style"], k=0.5)
    assert lay["title"]["standoff"] == 10.0


# ---------------- Y축 제목 여백 자동 조절 ----------------

def test_tick_label_texts_matches_the_axis_formatting_rules():
    """폭 추정은 실제로 찍힐 라벨 문자열을 재구성해서 한다."""
    assert tick_label_texts({"type": "log", "range": [-12.0, -10.0]}) ==         ["1E-12", "1E-11", "1E-10"]
    assert tick_label_texts({"type": "linear", "range": [0, 0.006],
                             "dtick": 0.002, "tickformat": ".3f"}) ==         ["0.000", "0.002", "0.004", "0.006"]
    # tickformat 이 없는 지수 표기 구간
    assert tick_label_texts({"type": "linear", "range": [-8e-5, -4e-5],
                             "dtick": 2e-5}) == ["-8E-5", "-6E-5", "-4E-5"]
    assert tick_label_texts({"type": "linear"}) == []


def test_y_axis_space_grows_with_font_size_and_label_length():
    style = dict(DEFAULTS["style"])
    lay = axis_layout(DEFAULTS["transfer_axes"]["y"], style, k=1.0,
                      data_min=-12.0, data_max=-3.0)
    need = y_axis_space_px(lay, style, k=1.0)
    assert need > style["tick_font_size"] + style["title_font_size"]
    # k 를 절반으로 줄이면 필요한 폭도 절반 근처로 줄어든다.
    half_lay = axis_layout(DEFAULTS["transfer_axes"]["y"], style, k=0.5,
                           data_min=-12.0, data_max=-3.0)
    assert y_axis_space_px(half_lay, style, k=0.5) == pytest.approx(need / 2, rel=0.05)


def test_fit_y_margins_only_shrinks_when_the_titles_would_not_fit():
    style = DEFAULTS["style"]
    geom = copy.deepcopy(DEFAULTS["transfer_geom"])
    lay = axis_layout(DEFAULTS["transfer_axes"]["y"], style, k=1.0,
                      data_min=-12.0, data_max=-3.0)
    tight = fit_y_margins(geom, [0.02, 0.98], style, 1.0, left_lay=lay, right_lay=lay)
    assert tight[0] > 0.02 and tight[1] < 0.98
    roomy = fit_y_margins(geom, [0.35, 0.65], style, 1.0, left_lay=lay, right_lay=lay)
    assert roomy == [0.35, 0.65]


def test_fit_y_margins_never_collapses_the_plot_area():
    """폰트가 터무니없이 커도 플롯이 사라지면 안 된다 — 최소 폭을 지킨다."""
    style = dict(DEFAULTS["style"], tick_font_size=50, title_font_size=50)
    geom = {"page_w_in": 2.0, "page_h_in": 2.0, "graph_left_pct": 10.0,
            "graph_top_pct": 10.0, "graph_width_pct": 80.0, "graph_height_pct": 80.0}
    lay = axis_layout(DEFAULTS["transfer_axes"]["y"], style, k=1.0,
                      data_min=-12.0, data_max=-3.0)
    left, right = fit_y_margins(geom, [0.1, 0.9], style, 1.0,
                                left_lay=lay, right_lay=lay)
    assert right - left == pytest.approx(0.30, abs=1e-6)
    assert 0 < left < right < 1


# ---------------- 굽은 화살표 ----------------

def test_curve_arrow_points_start_from_the_turning_point_and_stay_short():
    """반환점 기준으로 skip 만큼 안쪽에서 시작해 length 만큼만 따라간다."""
    fx = np.linspace(0.0, 1.0, 200)
    fy = np.full_like(fx, 0.5)
    pts = curve_arrow_points(fx, fy, 400.0, 400.0, skip=0.05, length=0.15,
                             offset=0.0, from_start=True)
    xs = [p[0] for p in pts]
    assert 0.04 < min(xs) < 0.06        # skip
    assert 0.19 < max(xs) < 0.21        # skip + length
    assert xs == sorted(xs)             # 진행 방향 = 화살촉 쪽


def test_curve_arrow_points_reverses_so_the_head_is_at_the_turning_point():
    fx = np.linspace(0.0, 1.0, 200)
    fy = np.full_like(fx, 0.5)
    pts = curve_arrow_points(fx, fy, 400.0, 400.0, skip=0.05, length=0.15,
                             offset=0.0, from_start=False)
    xs = [p[0] for p in pts]
    # from_start=False 는 '마지막 점(=반환점 x=1.0)으로 들어오는' 쪽이다. 거리는
    # 반환점에서부터 재고(0.05~0.20 안쪽), 마지막 점 = 화살촉이 반환점에 가장 가깝다.
    assert xs == sorted(xs)
    assert 0.79 < min(xs) < 0.81
    assert 0.94 < xs[-1] < 0.96


def test_curve_arrow_offset_pushes_the_arrow_off_the_curve():
    fx = np.linspace(0.0, 1.0, 200)
    fy = np.full_like(fx, 0.5)
    up = curve_arrow_points(fx, fy, 400.0, 400.0, 0.05, 0.15, 0.03, True)
    down = curve_arrow_points(fx, fy, 400.0, 400.0, 0.05, 0.15, -0.03, True)
    assert up[0][1] > 0.5 > down[0][1]


def test_add_curved_arrow_clamps_inside_the_plot_and_points_along_the_tangent():
    fig = new_figure(DEFAULTS["output_geom"], 1.0)
    add_curved_arrow(fig, [(-0.5, 0.5), (0.2, 0.5), (0.4, 0.5)],
                     400.0, 400.0, "#000000", 2.0, 1.0)
    path = fig.layout.shapes[0].path
    assert path.startswith("M ")
    assert all(0.0 <= float(p.split(",")[0]) <= 1.0
               for p in path.replace("M ", "").split(" L "))
    ann = fig.layout.annotations[0]
    assert ann.ax < 0 and ann.ay == 0      # +x 방향으로 진행 -> 꼬리는 왼쪽
    assert ann.showarrow is True


def test_add_curved_arrow_ignores_degenerate_input():
    fig = new_figure(DEFAULTS["output_geom"], 1.0)
    add_curved_arrow(fig, [(0.5, 0.5)], 400.0, 400.0, "#000000", 2.0, 1.0)
    assert not fig.layout.shapes
