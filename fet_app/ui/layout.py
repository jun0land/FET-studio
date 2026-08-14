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

# theme.RESPONSIVE_CSS 가 :has() 로 찾는 마커. 헤더 행(제목/문서버튼 2개/업로더,
# 중첩 없는 단일 st.columns 4열)의 첫 컬럼에 심는다 — 제목·버튼 두 개는 내용
# 크기로, 업로더는 남는 폭을 다 갖게 한다.
#
# 처음엔 문서 버튼 둘을 header[1] 안에 st.columns(2) 로 중첩해서 넣고 그
# 안쪽 블록에 마커를 심었었다. :has(SELECTOR) 는 SELECTOR 가 '어느 깊이의
# 자손이든' 있으면 매치하므로(직계 자식으로 한정되지 않는다), 그 마커를
# 감싸는 바깥쪽 헤더 행까지 같이 매치돼 flex:0 0 auto 가 제목·업로더 칸에도
# 걸려버렸다 — 제목이 오른쪽으로 끌려가고 업로더 폭이 줄어드는 회귀였다.
# 중첩을 아예 없애고 제목·버튼 두 개·업로더를 하나의 st.columns() 로 평평하게
# 두면, 마커를 담는 블록이 이 행 하나뿐이라 :has() 가 잘못된 조상을 잡을
# 여지가 없다(3열 셸에 쓰는 fet-shell-anchor 와 같은, 검증된 패턴).
HEADER_ROW_ANCHOR = "<div class='fet-header-row-anchor'></div>"


@st.dialog("이용 방법", width="large")
def _manual_dialog() -> None:
    # unsafe_allow_html: 문서 프로즈의 V_th 같은 변수를 <sub>th</sub> 로 실제
    # 아래첨자 렌더링하기 위해 필요하다(표준 마크다운엔 첨자 문법이 없다).
    st.markdown(load_doc("MANUAL.md"), unsafe_allow_html=True)


@st.dialog("분석 방법", width="large")
def _methods_dialog() -> None:
    st.markdown(load_doc("METHODS.md"), unsafe_allow_html=True)


def render_app() -> None:
    theme.inject()
    theme.apply_ui_zoom()
    theme.warn_before_unload()
    app = st.session_state["app"]

    # Streamlit 은 페이지 맨 위쪽에 클릭이 잘 안 먹는 구간이 있는 것으로
    # 알려져 있다(고정 헤더/툴바가 위에 얹혀서 생기는 문제). 제목·문서
    # 버튼·업로더 높이가 서로 달라 상단 정렬이면 버튼이 그 죽은 영역에
    # 걸치기 쉬우므로 세로 중앙 정렬로 맞춘다.
    #
    # 제목은 왼쪽에 내용 크기만큼만, 문서 버튼 두 개는 그 옆에 일정 간격으로
    # 붙고, 업로더는 남는 공간을 전부 차지한다(파일을 자주 올리니 널찍하게).
    # 네 칸 모두 같은 st.columns() 의 형제라 간격(gap)이 전부 동일하다.
    # 비율([0.14, 0.11, 0.11, 0.64])은 CSS 가 로드되기 전 잠깐 보일 초기값일
    # 뿐이고, RESPONSIVE_CSS 의 fet-header-row-anchor 규칙이 실제 폭(제목·
    # 버튼=내용 크기, 업로더=flex-grow)을 정한다.
    header = st.columns([0.14, 0.11, 0.11, 0.64], vertical_alignment="center")
    with header[0]:
        # 마커와 제목을 st.markdown() 한 번으로 합친다. 따로 두 번 호출하면
        # Streamlit 이 stElementContainer 를 두 개 만들고 그 사이에 기본
        # 세로 gap 이 생겨, 실제로 보이는 제목(.fet-title)이 아래로 밀려나면서
        # header[1]/[2]/[3](호출이 하나뿐) 대비 세로 중심이 처지는 회귀가 난다.
        logo = theme.logo_url()
        img_tag = f"<img src='{logo}' alt='FETs Studio logo'/>" if logo else ""
        st.markdown(
            f"{HEADER_ROW_ANCHOR}<div class='fet-title'>{img_tag}<h3>FETs Studio</h3></div>",
            unsafe_allow_html=True,
        )
    with header[1]:
        if st.button("📖 이용 방법", key="doc_manual_btn"):
            _manual_dialog()
    with header[2]:
        if st.button("📊 분석 방법", key="doc_methods_btn"):
            _methods_dialog()
    with header[3]:
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
