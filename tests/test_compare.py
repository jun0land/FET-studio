"""커브 비교 — 그래프(figure_compare.py)와 선택/색 배정(ui/compare.py).

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
from fet_app.state import AppState
from fet_app.ui import compare


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


def test_selected_items_drops_devices_that_disappeared():
    app = _app()
    app.compare_selected = ["1-1", "사라진소자"]
    assert [n for n, _c, _color in compare.selected_items(app)] == ["1-1"]


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
