"""우측 소자 리스트 (스펙 §6.1). 세로 스크롤 + 검색 + 배지/경고."""

from __future__ import annotations

import streamlit as st

from fet_app.constants import DEFAULT_THRESHOLDS


def filter_devices(devices, query: str):
    q = (query or "").strip().lower()
    if not q:
        return list(devices)
    return [g for g in devices if q in g.name.lower()]


def device_flags(app, g) -> list[str]:
    flags = []
    if g.transfer is None and g.output is None:
        flags.append("no-data")
    if g.warnings:
        flags.append("warning")
    return flags


DEVICE_LIST_HEIGHT = 460  # px — 아래 컨테이너의 높이. 정수 px 만 받는다 (vh 불가)


def render(app) -> None:
    st.caption("소자")
    # 검색창은 컨테이너 밖에 둬야 리스트가 스크롤돼도 고정된 채 남는다.
    app.search = st.text_input("검색", value=app.search, key="device_search",
                               placeholder="이름 검색", label_visibility="collapsed")

    # st.markdown 으로 연 <div> 는 각자 독립 컨테이너에 렌더되어 바로 다음
    # st.markdown 이 닫아버린다 — 그 사이의 st.button 들은 자식이 아니라
    # 형제로 끝나서 CSS max-height/overflow 를 건 래퍼가 실제로는 아무것도
    # 감싸지 못했다. 아래 컨테이너는 실제로 스크롤되는 영역을 만든다.
    with st.container(height=DEVICE_LIST_HEIGHT, border=False):
        for g in filter_devices(app.devices, app.search):
            mark = "⚠ " if "warning" in device_flags(app, g) else ""
            label = f"{mark}{g.name}  ·{g.badges}"
            if st.button(label, key=f"dev_{g.name}", use_container_width=True,
                         type="primary" if g.name == app.selected else "secondary"):
                app.selected = g.name
                st.rerun()

    st.divider()
    # 전역 기본값(W/L/유전체/d)은 좌측 편집 패널 최상단으로 옮겼다 — 같은
    # 값을 편집하는 창이 두 군데 있을 이유가 없었다.
    with st.expander("진단 임계값", expanded=False):
        t = app.thresholds
        t["zero_offset"] = st.number_input(
            "0 V 오프셋 (%)", min_value=0.0, max_value=100.0,
            value=float(t.get("zero_offset", DEFAULT_THRESHOLDS["zero_offset"])) * 100,
            step=0.1, key="t_zero") / 100.0
        t["linearity_r2"] = st.number_input(
            "원점 선형성 R² 하한", min_value=0.0, max_value=1.2,
            value=float(t.get("linearity_r2", DEFAULT_THRESHOLDS["linearity_r2"])),
            step=0.001, format="%.3f", key="t_lin")
        t["saturation"] = st.number_input(
            "포화 기울기비 상한", min_value=0.0, max_value=10.0,
            value=float(t.get("saturation", DEFAULT_THRESHOLDS["saturation"])),
            step=0.01, key="t_sat")
        t["gate_leak"] = st.number_input(
            "게이트 누설 (%)", min_value=0.0, max_value=100.0,
            value=float(t.get("gate_leak", DEFAULT_THRESHOLDS["gate_leak"])) * 100,
            step=0.1, key="t_leak") / 100.0

    if st.button("☰ 전체 요약", use_container_width=True):
        app.show_summary = True
        st.rerun()
