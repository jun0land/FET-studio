"""좌측 패널 — 소자 파라미터. 비우면 전역 기본값을 상속한다."""

from __future__ import annotations

import streamlit as st

from fet_app.constants import DIELECTRIC_PRESETS
from fet_app.params import DeviceParams


def render(app) -> None:
    g = app.device(app.selected)
    if g is None:
        return

    st.markdown(f"**소자 · {g.name}**")
    if g.warnings:
        with st.expander(f"⚠ 경고 {len(g.warnings)}건"):
            for w in g.warnings:
                st.caption(w)

    # 재측정 파일(Data + Append1)이면 어느 런을 분석할지 고른다. 기본은 Latest.
    if len(g.transfer_runs) > 1:
        labels = [r.label for r in g.transfer_runs]
        g.transfer_run_idx = labels.index(st.selectbox(
            "Transfer 측정 런", labels,
            index=min(g.transfer_run_idx, len(labels) - 1), key=f"trun_{g.name}"))
    if len(g.output_runs) > 1:
        labels = [r.label for r in g.output_runs]
        g.output_run_idx = labels.index(st.selectbox(
            "Output 측정 런", labels,
            index=min(g.output_run_idx, len(labels) - 1), key=f"orun_{g.name}"))

    p = g.params
    c1, c2 = st.columns(2)
    with c1:
        w = st.text_input("W (µm)", value="" if p.w_um is None else f"{p.w_um:g}",
                          key=f"w_{g.name}", placeholder="전역값")
    with c2:
        length = st.text_input("L (µm)", value="" if p.l_um is None else f"{p.l_um:g}",
                               key=f"l_{g.name}", placeholder="전역값")

    names = list(DIELECTRIC_PRESETS) + ["Custom"]
    current = next((n for n, v in DIELECTRIC_PRESETS.items() if v == p.eps_r), None)
    idx = names.index(current) if current else len(names) - 1
    choice = st.selectbox("유전체", names, index=idx, key=f"diel_{g.name}")

    c3, c4 = st.columns(2)
    with c3:
        eps = (st.text_input("ε_r", value="" if p.eps_r is None else f"{p.eps_r:g}",
                             key=f"eps_{g.name}", placeholder="전역값")
               if choice == "Custom" else str(DIELECTRIC_PRESETS[choice]))
    with c4:
        d = st.text_input("d (nm)", value="" if p.d_nm is None else f"{p.d_nm:g}",
                          key=f"d_{g.name}", placeholder="전역값")

    def _num(text):
        try:
            v = float(str(text).strip())
            return v if v > 0 else None
        except ValueError:
            return None

    g.params = DeviceParams(w_um=_num(w), l_um=_num(length),
                            eps_r=_num(eps), d_nm=_num(d))

    eff = app.effective_params(g)
    if eff.is_complete():
        st.caption(f"C_ox = **{eff.c_ox() * 1e9:.2f} nF/cm²**")
    else:
        st.caption("C_ox — W/L/ε_r/d 를 모두 채우면 계산됩니다 (전역값 상속 가능)")

    if g.transfer is not None and g.transfer.v_ds is not None:
        st.caption(f"V_DS = {g.transfer.v_ds:g} V (Settings 에서 읽음)")
