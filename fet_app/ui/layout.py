"""3열 배치 (스펙 §6.1). 패널 폭은 theme.RESPONSIVE_CSS 가 정한다."""

from __future__ import annotations

import streamlit as st

from fet_app import state as state_mod
from fet_app import theme
from fet_app.manual import load_doc
from fet_app.ui import device_list, export_ui, panel_edit, summary
from fet_app.ui.viewport import preview_scale

# theme.RESPONSIVE_CSS 가 :has() 로 찾는 마커. 3열 컨테이너의 첫 컬럼에 심는다.
SHELL_ANCHOR = "<div class='fet-shell-anchor'></div>"


def _render_doc_buttons() -> None:
    """이용 방법/분석 방법 문서 버튼.

    예전엔 [전체 요약] 화면에 들어가야만 보이는 '문서' 아코디언에 있었다 —
    자주 참고할 문서인데 거기까지 가야 해서 옮겼다. 우측에 고정 배너로 달면
    그래프·패널과 공간을 다투므로, 제목 옆 버튼 + 팝오버(눌렀을 때만 뜨는
    말풍선)로 바꿨다. 색은 NBEDL Exp Assistant 의 사용 설명서(주황)/분석
    방법(청록) 배너 색을 그대로 따왔다 — CSS 는 theme.py 의
    .st-key-doc_manual_btn / .st-key-doc_methods_btn 규칙을 본다.
    """
    c1, c2 = st.columns(2)
    with c1:
        with st.popover("📖 이용 방법", use_container_width=True, key="doc_manual_btn"):
            st.markdown(load_doc("MANUAL.md"))
    with c2:
        with st.popover("📊 분석 방법", use_container_width=True, key="doc_methods_btn"):
            st.markdown(load_doc("METHODS.md"))


def render_app() -> None:
    theme.inject()
    app = st.session_state["app"]

    header = st.columns([0.38, 0.34, 0.28])
    with header[0]:
        st.markdown("### FET Studio")
    with header[1]:
        _render_doc_buttons()
    with header[2]:
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
                 "파일 이름은 아무렇게나 지어도 됩니다. 사용법은 위 [이용 방법] 버튼을 참고하세요.")
        return

    if app.show_summary:
        summary.render_summary_table(app)
        return

    k = preview_scale(app)
    left, center, right = st.columns([1, 3, 1], gap="medium")

    with left:
        # 이 마커가 있어야 RESPONSIVE_CSS 가 이 3열 블록을 찾아 폭을 잡는다.
        st.markdown(SHELL_ANCHOR, unsafe_allow_html=True)
        panel_edit.render(app)

    with center:
        summary.render_device_view(app, k)

    with right:
        device_list.render(app)
        export_ui.render(app)
