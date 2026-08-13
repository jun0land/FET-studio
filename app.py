"""FET Studio — 진입점. 얇게 유지할 것: 부팅과 위임만 한다."""

from __future__ import annotations

import streamlit as st

# set_page_config 는 반드시 다른 st 호출보다 먼저 (streamlit 규약).
st.set_page_config(page_title="FET Studio", layout="wide")

from fet_app import state  # noqa: E402
from fet_app.ui import layout  # noqa: E402


def main() -> None:
    state.boot()
    layout.render_app()


if __name__ == "__main__":
    main()
