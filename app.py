"""FETs Studio — 진입점. 얇게 유지할 것: 부팅과 위임만 한다."""

from __future__ import annotations

import streamlit as st

# set_page_config 는 반드시 다른 st 호출보다 먼저 (streamlit 규약).
st.set_page_config(page_title="FETs Studio", layout="wide")

from fet_app import fonts_setup, state  # noqa: E402
from fet_app.ui import layout  # noqa: E402


def main() -> None:
    # 내보내기(kaleido -> 시스템 Chromium)는 앱의 @font-face 가 아니라 OS 폰트
    # 시스템에서 'Myriad Pro' 를 찾는다. 첫 내보내기 전에 등록해 둔다.
    # 두 번째 호출부터는 캐시된 결과를 즉시 돌려주므로 rerun 비용이 없다.
    fonts_setup.ensure_installed()
    state.boot()
    layout.render_app()


if __name__ == "__main__":
    main()
