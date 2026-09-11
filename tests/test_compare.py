"""Transfer 비교 — 그래프(figure_compare.py)와 선택/색 배정(ui/compare.py).

ui.compare.render() 자체는 st 위젯 상호작용이라, 다른 UI 테스트(test_export_ui)
와 같은 관례로 판단 로직을 순수 함수로 뽑아 검증한다.
"""

from __future__ import annotations

import copy
import inspect

import numpy as np
import pandas as pd

from fet_app.constants import COMPARE_PALETTE, DEFAULTS
from fet_app.curves import TransferCurve
from fet_app.figure_compare import (
    LEGEND_POSITIONS, assign_colors, compare_figure, palette_color,
)
from fet_app.grouping import DeviceGroup, MeasurementRun
from fet_app.metrics import transfer_metrics
from fet_app.params import DeviceParams
from fet_app.state import AppState
from fet_app.ui import compare

PARAMS = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)


def _curve(scale=1.0, dual=True):
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = -scale * np.maximum(2e-8 * (v_g + 12.0) ** 2 * (v_g < -12.0), 1e-12)
    fwd = pd.DataFrame({"V_G": v_g, "I_G": np.full_like(v_g, 1e-11), "I_D": i_d})
    rev = fwd.iloc[::-1].reset_index(drop=True) if dual else None
    return TransferCurve(forward=fwd, reverse=rev, v_ds=-60.0, dual=dual)


def _group(name, curve=None):
    curve = _curve() if curve is None else curve
    return DeviceGroup(
        name=name, transfer_file=f"{name}.xls",
        transfer_sources={f"{name}.xls": [MeasurementRun(
            sheet="Data", label="Data", is_latest=True,
            kind="transfer", reason="settings", transfer=curve)]})


def _settings(**cmp_over):
    s = {
        "geom": copy.deepcopy(DEFAULTS["transfer_geom"]),
        "style": copy.deepcopy(DEFAULTS["style"]),
        "axes": copy.deepcopy(DEFAULTS["transfer_axes"]),
        "compare": copy.deepcopy(DEFAULTS["compare"]),
        "insets": copy.deepcopy(DEFAULTS["insets"]),
    }
    s["compare"].update(cmp_over)
    return s


def _app(names=("1-1", "1-2", "1-3")):
    app = AppState(devices=[_group(n) for n in names])
    app.global_params = PARAMS
    return app


# ---------------- 색 배정 ----------------

def test_palette_cycles_when_there_are_more_devices_than_colors():
    assert palette_color(0) == COMPARE_PALETTE[0]
    assert palette_color(len(COMPARE_PALETTE)) == COMPARE_PALETTE[0]
    assert palette_color(len(COMPARE_PALETTE) + 2) == COMPARE_PALETTE[2]


def test_manual_color_wins_without_shifting_the_others():
    """수동 색이 팔레트 자리를 먹으면 고르지도 않은 커브 색이 따라 바뀐다."""
    auto = assign_colors(["a", "b", "c"])
    manual = assign_colors(["a", "b", "c"], {"b": "#FF0000"})
    assert manual["b"] == "#FF0000"
    assert manual["a"] == auto["a"] and manual["c"] == auto["c"]


def test_colors_follow_selection_order():
    assert assign_colors(["x", "y"])["x"] == assign_colors(["x"])["x"]
    assert assign_colors(["y", "x"])["y"] == assign_colors(["x", "y"])["x"]


# ---------------- 그래프 ----------------

def test_each_device_gets_one_trace_in_its_own_color():
    items = [("1-1", _curve(), "#0072B2"), ("1-2", _curve(0.5), "#D55E00")]
    fig = compare_figure(items, _settings())
    assert len(fig.data) == 2
    assert [t.line.color for t in fig.data] == ["#0072B2", "#D55E00"]
    assert [t.line.dash for t in fig.data] == ["solid", "solid"]


def test_reverse_adds_a_dashed_branch_per_device():
    items = [("1-1", _curve(), "#0072B2")]
    fig = compare_figure(items, _settings(show_reverse=True))
    assert [t.line.dash for t in fig.data] == ["solid", "dash"]
    assert {t.line.color for t in fig.data} == {"#0072B2"}


def test_single_axis_follows_the_mode():
    """이중 Y축에 여러 소자를 얹으면 어느 곡선이 어느 축인지 못 읽는다 —
    비교 그래프는 축이 하나뿐이고, 그 축을 mode 로 고른다."""
    items = [("1-1", _curve(), "#0072B2")]
    log_fig = compare_figure(items, _settings(mode="log"))
    assert log_fig.layout.yaxis.type == "log"
    assert log_fig.layout.yaxis.title.text == "|I<sub>D</sub>| (A)"
    # 두 번째 축은 아예 만들지 않는다 (없는 축은 layout 에 속성 자체가 없다)
    assert "yaxis2" not in log_fig.layout

    sqrt_fig = compare_figure(items, _settings(mode="sqrt"))
    assert sqrt_fig.layout.yaxis.type == "linear"
    assert sqrt_fig.layout.yaxis.title.text == "√|I<sub>D</sub>| (A<sup>0.5</sup>)"
    assert sqrt_fig.layout.yaxis.side is None          # 왼쪽에 그린다 (y2 설정 재사용)
    peak = float(np.nanmax(np.sqrt(np.abs(_curve().forward["I_D"].to_numpy()))))
    assert sqrt_fig.layout.yaxis.range[1] >= peak


def test_x_range_covers_every_selected_curve():
    narrow = _curve(dual=False)
    wide = TransferCurve(forward=pd.DataFrame({
        "V_G": np.arange(40, -81, -1, dtype=float),
        "I_G": 1e-11, "I_D": -1e-6}), dual=False)
    fig = compare_figure([("a", narrow, "#000000"), ("b", wide, "#FF0000")], _settings())
    assert fig.layout.xaxis.range == (-80.0, 40.0)


def test_legend_swatches_carry_the_device_names():
    items = [("1-1", _curve(), "#0072B2"), ("1-2", _curve(), "#D55E00")]
    fig = compare_figure(items, _settings())
    labels = [a.text for a in fig.layout.annotations]
    assert labels == ["1-1", "1-2"]
    assert [sh.line.color for sh in fig.layout.shapes if sh.type == "line"] == \
        ["#0072B2", "#D55E00"]


def test_legend_can_be_turned_off_and_moved():
    items = [("1-1", _curve(), "#0072B2")]
    assert not compare_figure(items, _settings(legend=False)).layout.annotations

    bottom = compare_figure(items, _settings(legend_pos="bottom-left"))
    top = compare_figure(items, _settings(legend_pos="top-right"))
    assert bottom.layout.annotations[0].y < top.layout.annotations[0].y
    assert "bottom-left" in LEGEND_POSITIONS


def _fit_traces(fig):
    return [t.name for t in fig.data if t.name.endswith(" fit") or t.name.endswith(" V_th")]


def test_fit_lines_and_vth_markers_are_drawn_in_sqrt_mode_in_the_curve_color():
    """멀티 커브 편집: 소자마다 fit 직선(점선)과 V_th 절편 마커를 커브 색으로 얹는다.
    Transfer 그래프의 고정 빨강은 여기서 쓸 수 없다 — 어느 fit 이 누구 것인지
    색으로 짝지어야 한다."""
    c = _curve(dual=False)
    fit = transfer_metrics(c, PARAMS).fit
    fig = compare_figure([("1-1", c, "#0072B2", fit)], _settings(mode="sqrt"))
    assert _fit_traces(fig) == ["1-1 fit", "1-1 V_th"]
    fit_trace = next(t for t in fig.data if t.name == "1-1 fit")
    assert fit_trace.line.color == "#0072B2" and fit_trace.line.dash == "dot"
    marker = next(t for t in fig.data if t.name == "1-1 V_th")
    assert marker.marker.color == "#0072B2" and marker.y == (0.0,)
    assert abs(marker.x[0] - (-fit.intercept / fit.slope)) < 1e-9


def test_fit_overlay_only_in_sqrt_mode_and_only_when_enabled():
    """fit 은 √|I_D| 위의 직선이라 log 축에는 그리지 않는다."""
    c = _curve(dual=False)
    fit = transfer_metrics(c, PARAMS).fit
    assert not _fit_traces(compare_figure([("a", c, "#000", fit)], _settings(mode="log")))
    assert not _fit_traces(compare_figure([("a", c, "#000", fit)],
                                          _settings(mode="sqrt", show_fit=False)))
    # fit 이 없는(3-튜플) 항목은 그대로 받는다 — 썸네일·선택 화면이 그렇게 부른다.
    assert not _fit_traces(compare_figure([("a", c, "#000")], _settings(mode="sqrt")))
    assert not _fit_traces(compare_figure([("a", c, "#000", None)], _settings(mode="sqrt")))


def test_empty_selection_still_produces_axes():
    """빈 선택으로도 축은 나와야 한다 (figure_transfer 와 같은 방어)."""
    fig = compare_figure([], _settings())
    assert not fig.data
    assert fig.layout.xaxis.range is not None


def test_compare_figure_scales_with_k():
    items = [("1-1", _curve(), "#0072B2")]
    full = compare_figure(items, _settings(), 1.0)
    half = compare_figure(items, _settings(), 0.5)
    assert half.layout.width == full.layout.width // 2
    assert half.layout.yaxis.title.font.size == full.layout.yaxis.title.font.size // 2


# ---------------- 선택 상태 ----------------

def test_compare_devices_skips_devices_without_transfer_data():
    empty = TransferCurve(forward=pd.DataFrame({"V_G": [], "I_G": [], "I_D": []}))
    app = AppState(devices=[_group("ok"), _group("empty", empty), DeviceGroup(name="none")])
    assert [g.name for g in compare.compare_devices(app)] == ["ok"]


def test_sync_selection_keeps_the_order_things_were_picked_in():
    app = _app()
    compare.sync_selection(app, ["1-1", "1-2", "1-3"], {"1-3"})
    compare.sync_selection(app, ["1-1", "1-2", "1-3"], {"1-3", "1-1"})
    assert app.compare_selected == ["1-3", "1-1"]
    # 하나를 빼도 남은 것의 순서(=색)는 그대로다.
    compare.sync_selection(app, ["1-1", "1-2", "1-3"], {"1-1"})
    assert app.compare_selected == ["1-1"]


def test_selected_items_are_in_pick_order_with_stable_colors():
    app = _app()
    compare.sync_selection(app, ["1-1", "1-2", "1-3"], {"1-2"})
    compare.sync_selection(app, ["1-1", "1-2", "1-3"], {"1-2", "1-1"})
    items = compare.selected_items(app)
    assert [name for name, _c, _color in items] == ["1-2", "1-1"]
    assert [color for _n, _c, color in items] == [palette_color(0), palette_color(1)]


def test_legend_name_defaults_to_the_device_name():
    app = _app()
    assert compare.device_label(app, "1-1") == "1-1"
    app.settings["compare"]["labels"]["1-1"] = "   "     # 공백만 넣은 것도 '미지정'
    assert compare.device_label(app, "1-1") == "1-1"


def test_custom_legend_name_reaches_the_figure_with_markup():
    """개별 그래프의 '샘플명' 인셋은 전역 문구 하나라 소자마다 다를 수 없다 —
    겹쳐 그릴 때 쓸 이름은 비교 뷰가 소자별로 따로 갖는다."""
    app = _app()
    app.settings["compare"]["labels"]["1-2"] = "PMMA 20 nm (V_{th} 보정)"
    compare.sync_selection(app, ["1-1", "1-2"], {"1-1", "1-2"})
    items = compare.selected_items(app)
    assert [name for name, _c, _color in items] == ["1-1", "PMMA 20 nm (V_{th} 보정)"]

    fig = compare_figure(items, _settings())
    assert [a.text for a in fig.layout.annotations] ==         ["1-1", "PMMA 20 nm (V<sub>th</sub> 보정)"]


def test_image_plan_key_changes_when_a_legend_name_changes():
    app = _app()
    compare.sync_selection(app, ["1-1"], {"1-1"})
    before, _r = compare.compare_image_plan(app, "png", 1)
    app.settings["compare"]["labels"]["1-1"] = "소자 A"
    after, _r = compare.compare_image_plan(app, "png", 1)
    assert before != after


def test_selected_items_drops_devices_that_disappeared():
    app = _app()
    app.compare_selected = ["1-1", "사라진소자"]
    assert [n for n, _c, _color in compare.selected_items(app)] == ["1-1"]


def test_thumbnail_fits_the_narrowest_card_so_the_aspect_ratio_survives():
    """Plotly 차트는 칸보다 넓으면 폭만 줄고 높이는 그대로라 종횡비가 깨진다
    (viewport.py 에 같은 현상이 적혀 있다). 가장 좁을 때의 카드 폭보다
    썸네일이 작아야 한다."""
    from fet_app.figure_common import DPI

    narrowest_body = 1000 - 51          # CSS 1000px - 좌우 패딩 1.6rem
    card = (narrowest_body - 16 * (compare.PREVIEW_COLS - 1)) / compare.PREVIEW_COLS
    assert compare.THUMB_W_IN * DPI <= card
    # 편집 화면의 겹친 그래프도 같은 이유로 오른쪽 칸보다 좁아야 한다 (기본 배율 0.65).
    from fet_app.constants import DEFAULTS
    from fet_app.ui.viewport import FALLBACK_SCALE

    right = (narrowest_body - 16) * compare.EDIT_COLS[1] / sum(compare.EDIT_COLS)
    assert DEFAULTS["transfer_geom"]["page_w_in"] * DPI * FALLBACK_SCALE <= right


def test_thumbnail_settings_do_not_touch_the_real_settings():
    app = _app()
    thumb = compare._thumb_settings(app)
    assert thumb["axes"]["x"]["title"] == ""
    assert thumb["compare"]["legend"] is False
    assert thumb["geom"]["page_w_in"] == compare.THUMB_W_IN
    # 원본은 그대로 — 썸네일 설정은 사본이어야 한다.
    assert app.settings["transfer_axes"]["x"]["title"] == DEFAULTS["transfer_axes"]["x"]["title"]
    assert app.settings["transfer_geom"]["page_w_in"] == DEFAULTS["transfer_geom"]["page_w_in"]
    assert app.settings["compare"]["legend"] is True


# ---------------- 내보내기 ----------------

def test_selected_items_can_carry_each_devices_fit():
    app = _app()
    compare.sync_selection(app, ["1-1", "1-2"], {"1-1", "1-2"})
    plain = compare.selected_items(app)
    with_fit = compare.selected_items(app, with_fit=True)
    assert all(len(item) == 3 for item in plain)
    assert all(len(item) == 4 and item[3] is not None for item in with_fit)
    assert with_fit[0][3].slope != 0


def test_metrics_table_matches_the_summary_numbers_in_pick_order():
    """편집 화면의 지표 표는 전체 요약 표와 같은 계산(summary_row)을 잘라 쓴다 —
    두 화면의 숫자가 다르면 안 된다."""
    from fet_app.export import summary_row
    from fet_app.ui.summary import compute, effective_group

    app = _app()
    app.settings["compare"]["labels"]["1-3"] = "세 번째"
    compare.sync_selection(app, ["1-1", "1-2", "1-3"], {"1-3"})
    compare.sync_selection(app, ["1-1", "1-2", "1-3"], {"1-3", "1-1"})
    df = compare.metrics_table(app, compare.selected_groups(app))
    assert list(df["Device"]) == ["1-3", "1-1"]
    assert list(df["Label"]) == ["세 번째", "1-1"]
    assert list(df.columns) == ["Device", "Label", *compare.METRIC_COLUMNS]
    g = app.device("1-3")
    tm, od = compute(app, g)
    expected = summary_row(effective_group(app, g), tm, od)
    for col in compare.METRIC_COLUMNS:
        assert df.iloc[0][col] == expected[col]


def test_formatted_metrics_uses_the_metric_card_formatting():
    app = _app()
    compare.sync_selection(app, ["1-1"], {"1-1"})
    df = compare._formatted_metrics(compare.metrics_table(app, compare.selected_groups(app)))
    assert df.iloc[0]["V_th (V)"].endswith(" V")
    assert "E" in df.iloc[0]["mu_sat (cm2/Vs)"]


def test_image_plan_key_changes_with_device_params_and_fit_range(monkeypatch):
    """fit 직선은 파라미터·fit 구간에 따라 달라진다 — 키에 빠지면 예전 그림이 내려간다."""
    app = _app()
    compare.sync_selection(app, ["1-1"], {"1-1"})
    key1, _r = compare.compare_image_plan(app, "png", 1)
    app.global_params = DeviceParams(w_um=500.0, l_um=50.0, eps_r=3.9, d_nm=300.0)
    key2, _r = compare.compare_image_plan(app, "png", 1)
    assert key1 != key2
    monkeypatch.setattr(compare, "fit_range_for", lambda app, name: (-50.0, -20.0))
    key3, _r = compare.compare_image_plan(app, "png", 1)
    assert key3 != key2


def test_image_plan_key_changes_with_settings_and_selection():
    app = _app()
    compare.sync_selection(app, ["1-1", "1-2"], {"1-1"})
    key1, _r = compare.compare_image_plan(app, "png", 1)
    app.settings["compare"]["mode"] = "sqrt"
    key2, _r = compare.compare_image_plan(app, "png", 1)
    assert key1 != key2
    compare.sync_selection(app, ["1-1", "1-2"], {"1-1", "1-2"})
    key3, _r = compare.compare_image_plan(app, "png", 1)
    assert key3 != key2


def test_image_plan_render_closure_reads_no_streamlit_state():
    """지연 다운로드는 스크립트 스레드 밖에서 돈다 — 그 안에서 st.* 을 만지면
    세션 값이 조용히 사라진다 (export_ui.device_image_plan 과 같은 규칙)."""
    src = inspect.getsource(compare.compare_image_plan)
    body = src.split('"""')[-1]        # 독스트링 이후 본문만
    assert "st." not in body
