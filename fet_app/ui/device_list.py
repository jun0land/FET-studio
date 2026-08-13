"""우측 소자 리스트 (스펙 §6.1). 세로 스크롤 + 검색 + 배지/경고."""

from __future__ import annotations

import streamlit as st

from fet_app.constants import DEFAULT_THRESHOLDS, DIELECTRIC_PRESETS


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


def render(app) -> None:
    st.caption("소자")
    app.search = st.text_input("검색", value=app.search, key="device_search",
                               placeholder="이름 검색", label_visibility="collapsed")

    st.markdown("<div class='fet-device-list'>", unsafe_allow_html=True)
    for g in filter_devices(app.devices, app.search):
        mark = "⚠ " if "warning" in device_flags(app, g) else ""
        label = f"{mark}{g.name}  ·{g.badges}"
        if st.button(label, key=f"dev_{g.name}", use_container_width=True,
                     type="primary" if g.name == app.selected else "secondary"):
            app.selected = g.name
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    with st.expander("전역 기본값", expanded=False):
        p = app.global_params
        p.w_um = st.number_input("W (µm)", min_value=0.0, value=float(p.w_um or 1000.0),
                                 step=10.0, key="g_w")
        p.l_um = st.number_input("L (µm)", min_value=0.0, value=float(p.l_um or 50.0),
                                 step=1.0, key="g_l")
        name = st.selectbox("유전체", list(DIELECTRIC_PRESETS) + ["Custom"], key="g_diel")
        p.eps_r = (st.number_input("ε_r", min_value=0.0, value=float(p.eps_r or 3.9),
                                   step=0.1, key="g_eps")
                   if name == "Custom" else DIELECTRIC_PRESETS[name])
        p.d_nm = st.number_input("두께 (nm)", min_value=0.0, value=float(p.d_nm or 300.0),
                                 step=10.0, key="g_d")

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
