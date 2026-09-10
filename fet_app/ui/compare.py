"""커브 비교 뷰 — transfer 미리보기에서 여러 소자를 골라 한 그래프에 겹친다.

전체 요약 표(summary.render_summary_table)와 같은 자리에 서는 '다른 창'이다:
좌/우 패널을 접고 화면 전체를 쓰며, [← 소자 보기로] 로 돌아간다.

선택은 서식이 아니라 그때그때의 작업 상태라 AppState.compare_selected 에 두고,
색·표시 옵션만 settings["compare"] 에 둔다. 색은 **고른 순서**대로 팔레트에서
배정한다 — 소자 목록 순서로 배정하면 선택을 바꿀 때마다 남아 있는 커브의 색까지
따라 바뀌어서, 같은 그림을 다시 만들기가 어려워진다.
"""

from __future__ import annotations

import copy

import streamlit as st

from fet_app import export
from fet_app.figure_compare import (
    LEGEND_POS_LABELS, MODE_LABELS, assign_colors, compare_figure,
)
from fet_app.ui import color_picker
from fet_app.ui.export_ui import _FMT_KEY, _MIME, FORMATS, _cached_image_bytes
from fet_app.ui.summary import _has_transfer_data, cache_key, curve_fingerprint
from fet_app.ui.viewport import preview_scale

# 미리보기 카드 한 줄에 몇 개를 놓을지. 4열이면 1440px 기준 카드 폭이 약 330px 로,
# 3.2 inch 썸네일(307px)이 잘리지 않고 들어간다.
PREVIEW_COLS = 4
# 썸네일 전용 배경 크기(inch)와 글자 크기(px). 본 그래프를 k 로 줄이면 폰트까지
# 같이 줄어 눈금이 뭉개지므로, 썸네일은 자기 크기·자기 폰트로 따로 그린다.
THUMB_W_IN, THUMB_H_IN = 3.2, 2.6
THUMB_TICK_PX = 11
UNSELECTED_COLOR = "#9E9E9E"


def compare_devices(app) -> list:
    """transfer 커브가 실제로 있는 소자만. 빈 프레임(중단된 측정)은 뺀다."""
    return [g for g in app.devices if _has_transfer_data(g.transfer)]


def sync_selection(app, names: list[str], checked: set[str]) -> list[str]:
    """체크 상태 -> AppState.compare_selected. 이미 고른 것의 순서는 지킨다.

    체크박스는 매 rerun 마다 bool 만 돌려주므로 '언제 골랐는지'는 우리가
    기억해야 한다. 기존 순서를 앞에 두고 새로 체크된 것만 뒤에 붙이면, 색이
    배정된 소자는 계속 같은 색을 유지한다.
    """
    kept = [n for n in app.compare_selected if n in checked]
    added = [n for n in names if n in checked and n not in kept]
    app.compare_selected = kept + added
    return app.compare_selected


def _compare_settings(app) -> dict:
    s = app.settings
    return {"geom": s["transfer_geom"], "style": s["style"], "axes": s["transfer_axes"],
            "compare": s["compare"], "insets": s["insets"]}


def _thumb_settings(app) -> dict:
    """썸네일용 settings 사본 — 작은 배경, 축 제목 없음, 레전드 없음."""
    base = copy.deepcopy(_compare_settings(app))
    base["geom"].update(page_w_in=THUMB_W_IN, page_h_in=THUMB_H_IN,
                        graph_left_pct=20.0, graph_top_pct=6.0,
                        graph_width_pct=74.0, graph_height_pct=86.0)
    base["style"].update(tick_font_size=THUMB_TICK_PX, title_font_size=THUMB_TICK_PX,
                         line_width=1.5)
    for axis in ("x", "y", "y2"):
        base["axes"][axis]["title"] = ""
    base["compare"]["legend"] = False
    base["insets"] = copy.deepcopy(base["insets"])
    base["insets"]["sample"]["text"] = ""
    return base


def device_label(app, name: str) -> str:
    """레전드에 쓸 이름. 지정이 없거나 비어 있으면 소자 이름을 그대로 쓴다."""
    labels = app.settings["compare"].get("labels") or {}
    return str(labels.get(name, "")).strip() or name


def selected_items(app) -> list[tuple[str, object, str]]:
    """[(레전드 이름, TransferCurve, 색)] — 고른 순서 그대로."""
    colors = assign_colors(app.compare_selected, app.settings["compare"].get("colors"))
    out = []
    for name in app.compare_selected:
        g = app.device(name)
        if g is not None and _has_transfer_data(g.transfer):
            out.append((device_label(app, name), g.transfer, colors[name]))
    return out


def compare_image_plan(app, fmt: str, scale: int):
    """(캐시 키, 인자 없는 렌더 함수). export_ui.device_image_plan 과 같은 규칙 —
    세션·앱 상태는 여기서 다 읽고, 반환된 함수는 순수 계산만 한다."""
    items = selected_items(app)
    settings = copy.deepcopy(_compare_settings(app))
    key = cache_key({
        "kind": "compare", "fmt": fmt, "scale": int(scale), "settings": settings,
        "items": [(name, curve_fingerprint(curve), color)
                  for name, curve, color in items],
    })

    def _render() -> bytes:
        return export.figure_bytes(compare_figure(items, settings, 1.0), fmt, scale)

    return key, _render


def _render_controls(app, names: list[str]) -> None:
    cfg = app.settings["compare"]
    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1], vertical_alignment="bottom")
    with c1:
        modes = list(MODE_LABELS)
        cfg["mode"] = st.selectbox("값", modes,
                                   index=modes.index(cfg.get("mode", "log")),
                                   format_func=lambda m: MODE_LABELS[m], key="cmp_mode")
    with c2:
        positions = list(LEGEND_POS_LABELS)
        current = cfg.get("legend_pos", "bottom-left")
        cfg["legend_pos"] = st.selectbox(
            "레전드 위치", positions,
            index=positions.index(current) if current in positions else 0,
            format_func=lambda p: LEGEND_POS_LABELS[p], key="cmp_legend_pos",
            disabled=not cfg.get("legend", True))
        cfg["show_reverse"] = st.checkbox("reverse 표시",
                                          value=bool(cfg.get("show_reverse", False)),
                                          key="cmp_rev")
        cfg["legend"] = st.checkbox("레전드", value=bool(cfg.get("legend", True)),
                                    key="cmp_legend")
    with c3:
        if st.button("전체 선택", use_container_width=True, key="cmp_all"):
            app.compare_selected = list(names)
            st.rerun()
    with c4:
        if st.button("선택 해제", use_container_width=True, key="cmp_none"):
            app.compare_selected = []
            st.rerun()


def _render_previews(app, devices) -> None:
    """소자마다 [체크박스 + 썸네일 + (선택 시) 색 스와치] 카드를 격자로 놓는다."""
    thumb = _thumb_settings(app)
    colors = assign_colors(app.compare_selected, app.settings["compare"].get("colors"))
    names = [g.name for g in devices]
    checked = set()

    for row_start in range(0, len(devices), PREVIEW_COLS):
        row = devices[row_start:row_start + PREVIEW_COLS]
        cols = st.columns(PREVIEW_COLS)
        for col, g in zip(cols, row):
            with col:
                on = st.checkbox(g.name, value=g.name in app.compare_selected,
                                 key=f"cmp_sel_{g.name}")
                if on:
                    checked.add(g.name)
                color = colors.get(g.name, UNSELECTED_COLOR) if on else UNSELECTED_COLOR
                st.plotly_chart(
                    compare_figure([(g.name, g.transfer, color)], thumb, 1.0),
                    use_container_width=False, key=f"cmp_thumb_{g.name}")
                if on:
                    color_picker.color_picker(
                        "색", app.settings["compare"]["colors"], g.name,
                        key=f"cmp_color_{g.name}", default=color)
                    # 레전드 이름. 비워 두면 소자 이름을 그대로 쓴다 —
                    # placeholder 로 그 기본값을 보여준다.
                    labels = app.settings["compare"].setdefault("labels", {})
                    labels[g.name] = st.text_input(
                        "레전드 이름", value=labels.get(g.name, ""),
                        placeholder=g.name, key=f"cmp_label_{g.name}",
                        help="비워 두면 소자 이름. 마크업 가능: "
                             "_{아래첨자} ^{윗첨자} **굵게** *기울임*")
    sync_selection(app, names, checked)


def _render_downloads(app) -> None:
    c1, c2 = st.columns(2)
    with c1:
        fmt = _FMT_KEY[st.selectbox("이미지 형식", FORMATS, key="cmp_fmt")]
    with c2:
        scale = st.selectbox("배율", [1, 2, 4], index=0, key="cmp_scale")
    key, render = compare_image_plan(app, fmt, scale)
    st.download_button("비교 그래프 다운로드",
                       data=lambda: _cached_image_bytes(render, key),
                       file_name=f"fet_compare.{fmt}",
                       mime=_MIME.get(fmt, "application/octet-stream"),
                       use_container_width=True, key="cmp_dl")


def render(app) -> None:
    st.markdown("### 커브 비교")
    if st.button("← 소자 보기로", key="cmp_back"):
        app.show_compare = False
        st.rerun()

    devices = compare_devices(app)
    if not devices:
        st.info("transfer 커브가 있는 소자가 없습니다.")
        return

    _render_controls(app, [g.name for g in devices])
    _render_previews(app, devices)
    st.divider()

    items = selected_items(app)
    if not items:
        st.info("위에서 소자를 골라 주세요. 고른 순서대로 색이 배정됩니다.")
        return

    left, mid, right = st.columns([1, 2, 1], gap="medium")
    with mid:
        st.plotly_chart(compare_figure(items, _compare_settings(app), preview_scale(app)),
                        use_container_width=False, key="cmp_main")
        _render_downloads(app)
