"""서식 탭 + 크기·배율/프리셋(내보내기 패널에서 호출). 폰트 크기는 슬라이더
금지, number_input 스테퍼만 쓴다."""

from __future__ import annotations

import streamlit as st

from fet_app import presets
from fet_app.constants import (
    ACCENT, FONT_FAMILIES, FONT_SIZE_MAX, FONT_SIZE_MIN, LINE_WIDTH_STEP,
)
from fet_app.ui.viewport import FALLBACK_SCALE


def render(app) -> None:
    """'서식' 탭 내용 — 폰트/색/두께/토글만. 크기·배율과 프리셋은 내보내기
    패널(우측)로 옮겼다. render_page_and_presets() 를 보라."""
    s = app.settings
    style = s["style"]
    style["font_family"] = st.selectbox(
        "폰트", FONT_FAMILIES, index=FONT_FAMILIES.index(style["font_family"]),
        key="font_family")
    c1, c2 = st.columns(2)
    with c1:
        style["title_font_size"] = st.number_input(
            "축 제목 크기", min_value=FONT_SIZE_MIN, max_value=FONT_SIZE_MAX,
            value=int(style["title_font_size"]), step=1, key="ts")
    with c2:
        style["tick_font_size"] = st.number_input(
            "눈금 크기", min_value=FONT_SIZE_MIN, max_value=FONT_SIZE_MAX,
            value=int(style["tick_font_size"]), step=1, key="tk")
    style["line_width"] = st.number_input(
        "선 두께", min_value=0.5, max_value=10.0,
        value=float(style["line_width"]), step=LINE_WIDTH_STEP, key="lw")

    s["transfer_style"]["color"] = st.color_picker(
        "Transfer 색", value=s["transfer_style"]["color"], key="tcolor")
    s["transfer_style"]["show_reverse"] = st.checkbox(
        "reverse 표시", value=s["transfer_style"]["show_reverse"], key="trev")
    s["transfer_style"]["show_fit"] = st.checkbox(
        "fit 직선 표시", value=s["transfer_style"]["show_fit"], key="tfit")
    s["transfer_style"]["show_gate_current"] = st.checkbox(
        "|I_G| 표시", value=s["transfer_style"]["show_gate_current"], key="tig")

    s["output_style"]["base_color"] = st.color_picker(
        "Output 베이스 색", value=s["output_style"].get("base_color", ACCENT),
        key="ocolor")
    s["output_style"]["show_reverse"] = st.checkbox(
        "output reverse 표시", value=s["output_style"]["show_reverse"], key="orev")


def render_page_and_presets(app) -> None:
    """크기·배율 + 프리셋 — 내보내기 패널(우측)에서 호출한다.

    그래프 크기/배율/프리셋은 '그래프를 어떤 모습으로 뽑을지'라는 점에서
    내보내기와 같은 맥락이라 좌측 편집 패널에서 우측 내보내기 옆으로 옮겼다.
    """
    s = app.settings
    with st.expander("크기 · 배율", expanded=False):
        geom = s["geom"]
        c1, c2 = st.columns(2)
        with c1:
            geom["page_w_in"] = st.number_input("가로 (inch)", min_value=1.0,
                                                value=float(geom["page_w_in"]),
                                                step=0.5, key="pw")
        with c2:
            geom["page_h_in"] = st.number_input("세로 (inch)", min_value=1.0,
                                                value=float(geom["page_h_in"]),
                                                step=0.5, key="ph")
        auto = st.checkbox("미리보기 배율 자동", value=app.preview_scale is None,
                           key="auto_scale")
        if auto:
            app.preview_scale = None
        else:
            app.preview_scale = st.number_input(
                "미리보기 배율 (%)", min_value=25, max_value=200,
                value=int((app.preview_scale or FALLBACK_SCALE) * 100), step=5, key="mscale") / 100.0

    with st.expander("프리셋", expanded=False):
        st.download_button("프리셋 저장 (JSON)",
                           data=presets.to_json(presets.extract(s)).encode("utf-8"),
                           file_name="fet_preset.json", mime="application/json",
                           use_container_width=True)
        up = st.file_uploader("프리셋 불러오기", type=["json"], key="preset_up")
        if up is not None:
            try:
                app.settings = presets.apply(s, presets.from_json(up.getvalue().decode("utf-8")))
                st.success("프리셋을 적용했습니다.")
            except Exception as e:  # noqa: BLE001
                st.error(f"프리셋을 읽지 못했습니다: {e}")
