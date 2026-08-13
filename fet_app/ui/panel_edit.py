"""좌측 편집 패널 — 탭 5개(정보/축/인셋/서식/내보내기).

아코디언 대신 탭을 쓴다: 자주 오가며 조정하는데, 아코디언은 매번 열고
닫아야 해서 손이 많이 간다. 탭은 클릭 한 번으로 전환된다.

전역 기본값은 '정보' 탭 안에 있다 — 예전엔 탭 밖에 항상 떠 있는 별도
섹션이었는데, 다른 탭(축/인셋/서식/내보내기)을 열 때도 화면 위쪽을
차지하고 있어서 정보 탭 안으로 접었다.

내보내기도 여기 마지막 탭으로 옮겼다 — 예전엔 우측 소자 리스트 아래에
있었는데, 그러면 소자 리스트가 스크롤 영역과 내보내기 UI 를 동시에
좁은 우측 컬럼 하나에 욱여넣게 된다.
"""

from __future__ import annotations

import streamlit as st

from fet_app.ui import (
    export_ui, panel_axes, panel_device, panel_fit, panel_insets, panel_style,
)


def render(app) -> None:
    tabs = st.tabs(["정보", "축", "인셋", "서식", "내보내기"])
    with tabs[0]:
        panel_device.render_global(app)
        st.divider()
        panel_device.render(app)
        panel_fit.render(app)
    with tabs[1]:
        panel_axes.render(app)
    with tabs[2]:
        panel_insets.render(app)
    with tabs[3]:
        panel_style.render(app)
    with tabs[4]:
        export_ui.render(app)
