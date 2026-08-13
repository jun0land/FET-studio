"""3열 배치 (스펙 §6.1). 패널 폭은 theme.RESPONSIVE_CSS 가 정한다.

Task 17/18 이 아직 ``fet_app/ui/panel_device.py`` 등을 만들지 않았으므로, 그
모듈들에 대한 import 는 모듈 스코프가 아니라 ``render_app()`` 안에서 실제로
쓰는 시점에 한다 — 그래야 이 모듈은 지금도 깨지지 않고 import 된다
(``tests/test_theme.py`` 는 이 모듈을 건드리지 않지만, 다른 어떤 것이 이
패키지를 import 할 때도 마찬가지로 안전해야 한다). Task 18 이 실제 배선을
완성한다.
"""

from __future__ import annotations

import streamlit as st

from fet_app import state as state_mod
from fet_app import theme
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
            from fet_app.manual import DOCS, load_doc

            for tab, (name, file_name) in zip(st.tabs(list(DOCS)), DOCS.items()):
                with tab:
                    st.markdown(load_doc(file_name))
        return

    # Task 17/18 이 아직 구현하지 않은 패널 모듈. 실제로 쓰는 시점에만 import 해서
    # 이 모듈 자체는 그 전까지도 항상 import 가 가능하도록 한다.
    from fet_app.ui import device_list, export_ui, panel_device, panel_fit, panel_style, summary

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
        panel_style.render(app)

    with center:
        summary.render_device_view(app, k)

    with right:
        device_list.render(app)
        export_ui.render(app)
