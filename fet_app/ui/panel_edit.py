"""좌측 편집 패널 — 전역 기본값(항상 보임) + 탭 4개(정보/축/인셋/서식).

아코디언 대신 탭을 쓴다: 축·인셋·서식을 자주 오가며 조정하는데, 아코디언은
매번 열고 닫아야 해서 손이 많이 간다. 탭은 클릭 한 번으로 전환된다.
"""

from __future__ import annotations

import streamlit as st

from fet_app.ui import panel_axes, panel_device, panel_fit, panel_insets, panel_style


def render(app) -> None:
    panel_device.render_global(app)
    st.divider()
    tabs = st.tabs(["정보", "축", "인셋", "서식"])
    with tabs[0]:
        panel_device.render(app)
        panel_fit.render(app)
    with tabs[1]:
        panel_axes.render(app)
    with tabs[2]:
        panel_insets.render(app)
    with tabs[3]:
        panel_style.render(app)
