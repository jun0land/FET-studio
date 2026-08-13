"""3열 배치 (스펙 §6.1). 패널 폭은 theme.RESPONSIVE_CSS 가 정한다."""

from __future__ import annotations

import streamlit as st

from fet_app import state as state_mod
from fet_app import theme
from fet_app.manual import load_doc
from fet_app.ui import device_list, panel_edit, summary
from fet_app.ui.viewport import preview_scale

# theme.RESPONSIVE_CSS 가 :has() 로 찾는 마커. 3열 컨테이너의 첫 컬럼에 심는다.
SHELL_ANCHOR = "<div class='fet-shell-anchor'></div>"


@st.dialog("이용 방법", width="large")
def _manual_dialog() -> None:
    st.markdown(load_doc("MANUAL.md"))


@st.dialog("분석 방법", width="large")
def _methods_dialog() -> None:
    st.markdown(load_doc("METHODS.md"))


def _render_doc_buttons() -> None:
    """이용 방법/분석 방법 문서 버튼 — 진짜 팝업(모달)으로 띄운다.

    처음엔 st.popover 를 썼는데, 팝오버는 버튼 아래에 내용이 펼쳐지며 레이아웃을
    밀어내는 느낌이 아코디언과 비슷하다는 피드백을 받아 st.dialog(모달)로
    바꿨다 — 화면 전체 위에 뜨고 레이아웃을 밀어내지 않는다.
    색은 NBEDL Exp Assistant 의 사용 설명서(주황)/분석 방법(청록) 배너 색을
    그대로 따왔다 — CSS 는 theme.py 의 .st-key-doc_manual_btn /
    .st-key-doc_methods_btn 규칙을 본다 (버튼 위젯이면 종류에 상관없이 key 로
    같은 클래스가 붙는다).
    """
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📖 이용 방법", key="doc_manual_btn", use_container_width=True):
            _manual_dialog()
    with c2:
        if st.button("📊 분석 방법", key="doc_methods_btn", use_container_width=True):
            _methods_dialog()


def render_app() -> None:
    theme.inject()
    app = st.session_state["app"]

    # Streamlit 은 페이지 맨 위쪽에 클릭이 잘 안 먹는 구간이 있는 것으로
    # 알려져 있다(고정 헤더/툴바가 위에 얹혀서 생기는 문제). 제목·문서
    # 버튼·업로더 높이가 서로 달라 상단 정렬이면 버튼이 그 죽은 영역에
    # 걸치기 쉬우므로 세로 중앙 정렬로 맞춘다.
    header = st.columns([0.38, 0.34, 0.28], vertical_alignment="center")
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
