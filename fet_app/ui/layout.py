"""3열 배치 (스펙 §6.1). 패널 폭은 theme.RESPONSIVE_CSS 가 정한다."""

from __future__ import annotations

import streamlit as st

from fet_app import state as state_mod
from fet_app import theme
from fet_app.manual import DOCS, load_doc
from fet_app.ui import (
    device_list, export_ui, panel_axes, panel_device, panel_fit, panel_insets,
    panel_style, summary,
)
from fet_app.ui.viewport import preview_scale

# theme.RESPONSIVE_CSS 가 :has() 로 찾는 마커. 3열 컨테이너의 첫 컬럼에 심는다.
SHELL_ANCHOR = "<div class='fet-shell-anchor'></div>"


def render_app() -> None:
    theme.inject()
    app = st.session_state["app"]

    header = st.columns([0.7, 0.3])
    with header[0]:
        st.markdown("### FET Studio")
    with header[1]:
        uploaded = st.file_uploader(
            "측정 파일", type=["xls", "xlsx"], accept_multiple_files=True,
            label_visibility="collapsed", key="uploader",
        )
    if uploaded:
        warns = state_mod.add_files(app, [(f.name, f.getvalue()) for f in uploaded])
        for w in warns:
            st.warning(w)

    if not app.devices:
        st.info("Keithley `.xls` 파일을 올리면 transfer/output 을 자동으로 구분합니다. "
                 "파일 이름은 아무렇게나 지어도 됩니다.")
        with st.expander("문서"):
            for tab, (name, file_name) in zip(st.tabs(list(DOCS)), DOCS.items()):
                with tab:
                    st.markdown(load_doc(file_name))
        return

    if app.show_summary:
        summary.render_summary_table(app)
        return

    k = preview_scale(app)
    left, center, right = st.columns([1, 3, 1], gap="medium")

    with left:
        # 이 마커가 있어야 RESPONSIVE_CSS 가 이 3열 블록을 찾아 폭을 잡는다.
        st.markdown(SHELL_ANCHOR, unsafe_allow_html=True)
        panel_device.render(app)
        panel_fit.render(app)
        panel_axes.render(app)
        panel_insets.render(app)
        panel_style.render(app)

    with center:
        summary.render_device_view(app, k)

    with right:
        device_list.render(app)
        export_ui.render(app)
