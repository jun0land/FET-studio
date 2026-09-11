import copy

import numpy as np
import pandas as pd

from fet_app.constants import DEFAULTS, FIT_BAND_SHAPE_NAME, RIGHT_AXIS_TITLE_NAME
from fet_app.curves import TransferCurve
from fet_app.figure_transfer import transfer_figure
from fet_app.metrics import transfer_metrics
from fet_app.params import DeviceParams

PARAMS = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)


def _settings(**over):
    s = {
        "geom": copy.deepcopy(DEFAULTS["transfer_geom"]),
        "style": copy.deepcopy(DEFAULTS["style"]),
        "axes": copy.deepcopy(DEFAULTS["transfer_axes"]),
        "trace": copy.deepcopy(DEFAULTS["transfer_style"]),
        "insets": copy.deepcopy(DEFAULTS["insets"]),
    }
    s.update(over)
    return s


def _curve(dual=True):
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = -np.maximum(2e-8 * (v_g + 12.0) ** 2 * (v_g < -12.0), 1e-12)
    fwd = pd.DataFrame({"V_G": v_g, "I_G": np.full_like(v_g, 1e-11), "I_D": i_d})
    rev = fwd.iloc[::-1].reset_index(drop=True) if dual else None
    return TransferCurve(forward=fwd, reverse=rev, v_ds=-60.0, dual=dual)


def _right_title(fig):
    return next(a for a in fig.layout.annotations if a.name == RIGHT_AXIS_TITLE_NAME)


def test_left_axis_title_uses_absolute_value_symbol():
    """FET 에서는 절댓값 기호를 쓴다 (스펙 §5.2 — photodetector 규약을 뒤집은 항목).

    기본 제목은 인라인 마크업(`_{...}`/`^{...}`)으로 정의되어 있고, axis_layout 이
    apply_markup 을 거쳐 Plotly HTML(<sub>/<sup>)로 렌더한다 (FIX 1). 우축 제목은
    270도로 돌리느라 annotation 으로 그린다 (아래 테스트)."""
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    assert fig.layout.yaxis.title.text == "|I<sub>D</sub>| (A)"
    assert _right_title(fig).text == "√|I<sub>D</sub>| (A<sup>0.5</sup>)"
    assert fig.layout.xaxis.title.text == "V<sub>G</sub> (V)"


def test_right_axis_title_reads_top_to_bottom():
    """우축 제목은 좌축(아래->위, 90도)과 마주 보게 위->아래(Origin 270도)로.
    Plotly 축 제목은 각도를 못 바꾸므로 축 제목을 비우고 annotation 으로 돌린다."""
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    assert fig.layout.yaxis2.title.text in (None, "")
    ann = _right_title(fig)
    assert ann.textangle == 90                     # Plotly 시계 방향 90 = Origin 270
    assert ann.xref == "paper" and ann.yref == "paper"
    # 플롯 오른쪽 여백 안, 세로로는 플롯 가운데
    x_dom, y_dom = fig.layout.xaxis.domain, fig.layout.yaxis.domain
    assert x_dom[1] < ann.x <= 1.0
    assert abs(ann.y - (y_dom[0] + y_dom[1]) / 2) < 1e-6
    # 글꼴·색은 축 제목 설정을 그대로 따른다
    assert ann.font.size == fig.layout.yaxis.title.font.size
    assert ann.font.color == fig.layout.yaxis2.tickfont.color


def test_right_axis_title_follows_the_right_axis_color():
    c = _curve()
    s = _settings()
    s["trace"]["axis_color_right"] = "#FF0000"
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    assert _right_title(fig).font.color == "#FF0000"


def test_second_axis_overlays_on_right():
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    assert fig.layout.yaxis2.side == "right"
    assert fig.layout.yaxis2.overlaying == "y"
    assert fig.layout.yaxis.type == "log"
    assert fig.layout.yaxis2.type == "linear"


def test_dash_marks_the_axis_not_the_sweep_direction():
    """dual sweep 은 선 종류로 구분하지 않는다 — 논문 관례대로 주 곡선 |I_D| 가
    실선, fit 을 얹는 √|I_D| 가 점선이고 forward/reverse 는 같은 선 종류다.
    방향은 화살표가 알려준다."""
    c = _curve(dual=True)
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    named = {t.name: t for t in fig.data}
    assert named["forward |I_D|"].line.dash == "solid"
    assert named["reverse |I_D|"].line.dash == "solid"
    assert named["forward √|I_D|"].line.dash == "dot"
    assert named["reverse √|I_D|"].line.dash == "dot"
    assert named["forward |I_D|"].line.color == named["reverse |I_D|"].line.color


def test_gate_current_keeps_a_dash_of_its_own():
    """|I_G| 는 좌축이라 |I_D| 와 색이 같다 — 실선은 |I_D|, 점선은 √|I_D| 가
    가져갔으므로 파선으로 구분해야 겹쳐 보이지 않는다."""
    c = _curve()
    s = _settings()
    s["trace"]["show_gate_current"] = True
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    assert next(t for t in fig.data if t.name == "|I_G|").line.dash == "dash"


def _arrow_shapes(fig):
    return [sh for sh in fig.layout.shapes if sh.type == "path"]


def test_sweep_direction_arrows_are_drawn_inside_the_plot():
    """반환점 쪽에 가는 방향·오는 방향 화살표 두 개. 몸통은 커브를 따라가는
    path, 화살촉은 접선 방향 annotation 이다."""
    c = _curve(dual=True)
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    arrows = _arrow_shapes(fig)
    assert len(arrows) == 2
    heads = [a for a in fig.layout.annotations if a.showarrow]
    assert len(heads) == 2
    for sh in arrows:
        coords = [p.split(",") for p in sh.path.replace("M ", "").split(" L ")]
        for x, y in coords:
            assert 0.0 <= float(x) <= 1.0
            assert 0.0 <= float(y) <= 1.0
    for a in heads:
        assert 0.0 <= a.x <= 1.0 and 0.0 <= a.y <= 1.0


def test_sweep_arrows_point_in_opposite_directions():
    """forward 는 반환점을 향해, reverse 는 반환점에서 나오는 방향이어야 한다."""
    c = _curve(dual=True)
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    ax = [a.ax for a in fig.layout.annotations if a.showarrow]
    assert len(ax) == 2
    assert ax[0] * ax[1] < 0


def test_sweep_arrows_absent_without_reverse_or_when_toggled_off():
    single = _curve(dual=False)
    fig = transfer_figure(single, transfer_metrics(single, PARAMS), _settings())
    assert not _arrow_shapes(fig)

    c = _curve(dual=True)
    s = _settings()
    s["trace"]["show_sweep_arrows"] = False
    assert not _arrow_shapes(transfer_figure(c, transfer_metrics(c, PARAMS), s))

    s2 = _settings()
    s2["trace"]["show_reverse"] = False
    assert not _arrow_shapes(transfer_figure(c, transfer_metrics(c, PARAMS), s2))


def test_fit_band_is_named_so_export_can_drop_it():
    """fit 구간 음영은 화면 전용이다 — 내보내기가 골라낼 수 있게 이름을 단다."""
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    bands = [sh for sh in fig.layout.shapes if sh.name == FIT_BAND_SHAPE_NAME]
    assert len(bands) == 1
    assert bands[0].type == "rect"


def test_plot_area_shrinks_to_make_room_for_the_y_axis_titles():
    """FIX: 우Y 제목이 눈금 숫자('0.012')와 겹쳤다. 눈금 글자 폭 + standoff +
    제목 폭을 재서 플롯 영역(x domain)을 그만큼 안쪽으로 민다."""
    c = _curve()
    s = _settings()
    s["geom"]["graph_left_pct"] = 5.0     # 일부러 여백을 좁게 준다
    s["geom"]["graph_width_pct"] = 90.0
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    left, right = fig.layout.xaxis.domain
    page_w = fig.layout.width
    assert left * page_w > 100      # 좌축 '1E-11' + 제목이 들어갈 만큼
    assert (1 - right) * page_w > 100
    # 여백이 넉넉하면 사용자가 정한 domain 을 그대로 존중한다.
    wide = _settings()
    wide["geom"]["graph_left_pct"] = 30.0
    wide["geom"]["graph_width_pct"] = 40.0
    fig2 = transfer_figure(c, transfer_metrics(c, PARAMS), wide)
    assert fig2.layout.xaxis.domain == (0.3, 0.7)


def test_reverse_hidden_when_toggled_off():
    c = _curve(dual=True)
    s = _settings()
    s["trace"]["show_reverse"] = False
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    assert not any("reverse" in (t.name or "") for t in fig.data)


def test_log_axis_plots_absolute_current():
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    trace = next(t for t in fig.data if t.name == "forward |I_D|")
    assert np.all(np.asarray(trace.y) > 0)


def test_fit_line_and_vth_marker_present():
    c = _curve()
    m = transfer_metrics(c, PARAMS)
    fig = transfer_figure(c, m, _settings())
    names = [t.name for t in fig.data]
    assert "fit" in names
    assert "V_th" in names
    fit_trace = next(t for t in fig.data if t.name == "fit")
    assert fit_trace.yaxis == "y2"


def test_fit_hidden_when_toggled_off():
    c = _curve()
    s = _settings()
    s["trace"]["show_fit"] = False
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    assert "fit" not in [t.name for t in fig.data]


def test_gate_current_optional():
    c = _curve()
    s = _settings()
    assert "|I_G|" not in [t.name for t in transfer_figure(c, transfer_metrics(c, PARAMS), s).data]
    s["trace"]["show_gate_current"] = True
    assert "|I_G|" in [t.name for t in transfer_figure(c, transfer_metrics(c, PARAMS), s).data]


def test_left_and_right_axes_take_independent_colors():
    """좌축(log|I_D|, |I_G|)과 우축(√|I_D|)은 각각 자기 색을 쓴다."""
    c = _curve()
    s = _settings()
    s["trace"].update(axis_color_left="#0000FF", line_color_left="#0000FF",
                      axis_color_right="#FF0000", line_color_right="#FF0000")
    s["trace"]["show_gate_current"] = True
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    named = {t.name: t for t in fig.data}
    assert named["forward |I_D|"].line.color == "#0000FF"
    assert named["|I_G|"].line.color == "#0000FF"
    assert named["forward √|I_D|"].line.color == "#FF0000"
    assert fig.layout.yaxis.linecolor == "#0000FF"
    assert fig.layout.yaxis.title.font.color == "#0000FF"
    assert fig.layout.yaxis2.linecolor == "#FF0000"
    assert _right_title(fig).font.color == "#FF0000"
    # x 축은 좌/우 어느 쪽에도 속하지 않으므로 검정을 유지한다.
    assert fig.layout.xaxis.linecolor == "#000000"


def test_axis_color_and_line_color_are_separate_settings():
    """축(선·눈금·제목) 색과 커브 선 색은 서로 독립이다 — 검은 축에 색깔 커브
    같은 조합이 나와야 한다. |I_G| 는 좌축 커브이므로 line_color_left 를 따른다."""
    c = _curve()
    s = _settings()
    s["trace"].update(axis_color_left="#111111", line_color_left="#0000FF",
                      axis_color_right="#222222", line_color_right="#00FF00",
                      show_gate_current=True)
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    named = {t.name: t for t in fig.data}
    assert named["forward |I_D|"].line.color == "#0000FF"
    assert named["|I_G|"].line.color == "#0000FF"
    assert named["forward √|I_D|"].line.color == "#00FF00"
    # 축은 트레이스 색이 아니라 축 색을 따라간다.
    assert fig.layout.yaxis.linecolor == "#111111"
    assert fig.layout.yaxis.tickfont.color == "#111111"
    assert fig.layout.yaxis.title.font.color == "#111111"
    assert fig.layout.yaxis2.linecolor == "#222222"
    assert fig.layout.yaxis2.tickfont.color == "#222222"
    assert _right_title(fig).font.color == "#222222"


def test_default_transfer_colors_are_all_black():
    """4색으로 나눠도 기본 외관은 그대로(전부 검정)여야 한다."""
    assert DEFAULTS["transfer_style"]["axis_color_left"] == "#000000"
    assert DEFAULTS["transfer_style"]["axis_color_right"] == "#000000"
    assert DEFAULTS["transfer_style"]["line_color_left"] == "#000000"
    assert DEFAULTS["transfer_style"]["line_color_right"] == "#000000"
    assert "color_left" not in DEFAULTS["transfer_style"]
    assert "color_right" not in DEFAULTS["transfer_style"]


def test_fit_accent_color_is_independent_of_trace_colors():
    """fit/V_th 의 빨강은 raw 커브와 구분하기 위한 고정 강조색이다."""
    c = _curve()
    s = _settings()
    s["trace"].update(axis_color_left="#0000FF", line_color_left="#0000FF",
                      axis_color_right="#00FF00", line_color_right="#00FF00")
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    named = {t.name: t for t in fig.data}
    assert named["fit"].line.color == "#d62728"
    assert named["V_th"].marker.color == "#d62728"


def test_no_plotly_legend():
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    assert fig.layout.showlegend is False


def test_custom_axis_title_markup_expands_to_html():
    """사용자가 축 제목에 마크업을 쓰면 실제로 <sub>/<sup>/<b>로 확장돼야 한다 (FIX 1)."""
    c = _curve()
    s = _settings()
    s["axes"]["x"]["title"] = "**V**_{DS} (^{n}V)"
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    assert fig.layout.xaxis.title.text == "<b>V</b><sub>DS</sub> (<sup>n</sup>V)"


def test_right_axis_ticks_share_one_decimal_count():
    """FIX: √|I_D| 축이 '0.002 … 0.008, 0.01' 처럼 마지막만 자릿수가 잘려 나왔다.
    linear 축은 간격을 직접 정하고 그 자릿수로 tickformat 을 걸어 논문 스타일
    (한 축의 모든 눈금이 같은 소수 자릿수)을 맞춘다."""
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    y2 = fig.layout.yaxis2
    assert y2.dtick is not None
    step = float(y2.dtick)
    assert 0 < step <= (y2.range[1] - y2.range[0])
    assert y2.tickformat == f".{max(0, -int(np.floor(np.log10(step))))}f"
    # 로그축은 이 로직에 걸리면 안 된다 (dtick 이 'decade 수' 라 의미가 다르다)
    assert fig.layout.yaxis.dtick == 1
    assert fig.layout.yaxis.tickformat is None
    # 사용자가 지정한 x 축 dtick(20 V)은 그대로 존중된다
    assert fig.layout.xaxis.dtick == 20.0
    assert fig.layout.xaxis.tickformat == ".0f"


def test_axis_titles_keep_a_standoff_from_the_tick_labels():
    """FIX: 축 제목이 눈금 숫자에 붙어 보이던 문제. 기본 standoff 20 px 가
    figure 까지 전달되고 k 로 함께 줄어들어야 한다."""
    c = _curve()
    m = transfer_metrics(c, PARAMS)
    fig = transfer_figure(c, m, _settings(), k=1.0)
    assert fig.layout.yaxis.title.standoff == 20.0
    assert fig.layout.yaxis2.title.standoff == 20.0
    half = transfer_figure(c, m, _settings(), k=0.5)
    assert half.layout.yaxis2.title.standoff == 10.0


def test_scale_shrinks_figure_and_fonts():
    c = _curve()
    m = transfer_metrics(c, PARAMS)
    full = transfer_figure(c, m, _settings(), k=1.0)
    half = transfer_figure(c, m, _settings(), k=0.5)
    assert half.layout.width == full.layout.width // 2
    assert half.layout.xaxis.title.font.size == full.layout.xaxis.title.font.size // 2
