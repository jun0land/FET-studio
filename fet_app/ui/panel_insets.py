"""좌측 패널 — 인셋(레전드/샘플명) 위치·서식.

3x3 앵커 그리드 버튼으로 아홉 위치 중 하나를 한 번에 지정한다(슬라이더 2개 대신
클릭 1번). 그 아래 x/y 미세조정 입력으로 프리셋 위치에서 살짝 벗어나게 조정한다.
"""

from __future__ import annotations

import streamlit as st

from fet_app.constants import FONT_SIZE_MAX, FONT_SIZE_MIN

# 위치키 -> (x, y, xanchor, yanchor). x/y 는 plot domain 비율, 0.01/0.99 로
# 살짝 안쪽에 붙여 축 테두리에 글자가 겹치지 않게 한다.
ANCHOR_PRESETS = {
    "top-left":     {"x": 0.01, "y": 0.99, "xanchor": "left",   "yanchor": "top"},
    "top":          {"x": 0.50, "y": 0.99, "xanchor": "center", "yanchor": "top"},
    "top-right":    {"x": 0.99, "y": 0.99, "xanchor": "right",  "yanchor": "top"},
    "left":         {"x": 0.01, "y": 0.50, "xanchor": "left",   "yanchor": "middle"},
    "center":       {"x": 0.50, "y": 0.50, "xanchor": "center", "yanchor": "middle"},
    "right":        {"x": 0.99, "y": 0.50, "xanchor": "right",  "yanchor": "middle"},
    "bottom-left":  {"x": 0.01, "y": 0.01, "xanchor": "left",   "yanchor": "bottom"},
    "bottom":       {"x": 0.50, "y": 0.01, "xanchor": "center", "yanchor": "bottom"},
    "bottom-right": {"x": 0.99, "y": 0.01, "xanchor": "right",  "yanchor": "bottom"},
}

# 3x3 그리드 배치 (좌상/상/우상 / 좌/중앙/우 / 좌하/하/우하)
ANCHOR_GRID = [
    [("top-left", "좌상"), ("top", "상"), ("top-right", "우상")],
    [("left", "좌"), ("center", "중앙"), ("right", "우")],
    [("bottom-left", "좌하"), ("bottom", "하"), ("bottom-right", "우하")],
]


def active_anchor(inset: dict) -> str | None:
    """inset 의 xanchor/yanchor 조합이 아홉 프리셋 중 어디와 일치하는지.

    x/y 를 미세조정해도 xanchor/yanchor 는 그대로이므로 이 기준으로 '현재 켜진
    모서리'를 찾는다. 일치하는 프리셋이 없으면(예: 기본값이 아닌 커스텀 상태) None.
    """
    xa, ya = inset.get("xanchor"), inset.get("yanchor")
    for key, preset in ANCHOR_PRESETS.items():
        if preset["xanchor"] == xa and preset["yanchor"] == ya:
            return key
    return None


def _apply_anchor(inset: dict, key_prefix: str, pos_key: str) -> None:
    inset.update(ANCHOR_PRESETS[pos_key])
    # 아래에서 그릴 x/y 미세조정 위젯이 새 값을 즉시 반영하도록, 이전 위젯
    # 상태를 지운다 — 키가 세션에 남아 있으면 number_input 이 value= 인자를
    # 무시하고 그 값을 다시 보여준다.
    st.session_state.pop(f"{key_prefix}_x", None)
    st.session_state.pop(f"{key_prefix}_y", None)


def _anchor_grid(inset: dict, key_prefix: str) -> None:
    active = active_anchor(inset)
    for row in ANCHOR_GRID:
        cols = st.columns(3)
        for col, (pos_key, label) in zip(cols, row):
            with col:
                is_active = pos_key == active
                if st.button(label, key=f"{key_prefix}_anchor_{pos_key}",
                            type="primary" if is_active else "secondary",
                            use_container_width=True):
                    _apply_anchor(inset, key_prefix, pos_key)


def _tab(inset: dict, key_prefix: str, *, with_text: bool) -> None:
    _anchor_grid(inset, key_prefix)

    c1, c2 = st.columns(2)
    with c1:
        inset["x"] = st.number_input(
            "x (미세조정)", min_value=0.0, max_value=1.0,
            value=float(inset.get("x", 0.5)), step=0.01, key=f"{key_prefix}_x")
    with c2:
        inset["y"] = st.number_input(
            "y (미세조정)", min_value=0.0, max_value=1.0,
            value=float(inset.get("y", 0.5)), step=0.01, key=f"{key_prefix}_y")

    inset["font_size"] = st.number_input(
        "글자 크기", min_value=FONT_SIZE_MIN, max_value=FONT_SIZE_MAX,
        value=int(inset.get("font_size", 30)), step=1, key=f"{key_prefix}_fs")

    c3, c4 = st.columns(2)
    with c3:
        inset["border"] = st.checkbox(
            "테두리", value=bool(inset.get("border", False)), key=f"{key_prefix}_border")
    with c4:
        inset["bg_opacity"] = st.number_input(
            "배경 불투명도", min_value=0.0, max_value=1.0,
            value=float(inset.get("bg_opacity") or 0.0), step=0.05,
            key=f"{key_prefix}_bgop")

    if with_text:
        inset["text"] = st.text_input(
            "샘플명 (마크업 가능)", value=inset.get("text", ""), key=f"{key_prefix}_text")


def render(app) -> None:
    s = app.settings
    with st.expander("인셋", expanded=False):
        insets = s["insets"]
        tabs = st.tabs(["레전드", "샘플명"])
        with tabs[0]:
            _tab(insets["legend"], "inset_legend", with_text=False)
        with tabs[1]:
            _tab(insets["sample"], "inset_sample", with_text=True)
