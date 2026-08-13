"""좌측 패널 — fit 구간. 자동 탐색 결과를 보여주고 수동으로 덮어쓸 수 있다."""

from __future__ import annotations

import streamlit as st


def fit_range_for(app, name: str):
    """수동 지정이 켜져 있으면 (lo, hi), 아니면 None (= 자동 탐색)."""
    return st.session_state.get(f"fitrange_{name}")


def render(app) -> None:
    g = app.device(app.selected)
    if g is None or g.transfer is None:
        return

    st.markdown("**Fit 구간**")
    key = f"fitmode_{g.name}"
    manual = st.toggle("수동 지정", value=bool(st.session_state.get(key, False)), key=key)

    v = g.transfer.forward["V_G"]
    v_lo, v_hi = float(v.min()), float(v.max())
    if manual:
        c1, c2 = st.columns(2)
        with c1:
            lo = st.number_input("V_G 하한 (V)", value=v_lo, step=1.0, key=f"fl_{g.name}")
        with c2:
            hi = st.number_input("V_G 상한 (V)", value=v_hi, step=1.0, key=f"fh_{g.name}")
        st.session_state[f"fitrange_{g.name}"] = (float(lo), float(hi))
    else:
        st.session_state.pop(f"fitrange_{g.name}", None)
        st.caption("R² 최대 구간을 자동으로 찾습니다. 동점이면 긴 구간을 택합니다.")
