"""좌측 패널 — 소자 파라미터. 비우면 전역 기본값을 상속한다."""

from __future__ import annotations

import streamlit as st

from fet_app.constants import DIELECTRIC_PRESETS
from fet_app.params import DeviceParams

# classify_curve 의 reason("forcing"/"structure"/"name") -> 사람이 읽을 라벨.
# fet_app/parsing.py classify_curve 의 판정 순서(스펙 §2, MANUAL.md §1.2)와 맞춘다.
REASON_LABELS = {
    "forcing": "Settings 의 Forcing Function",
    "structure": "Data 열 구조",
    "name": "파일명",
}


def _render_source_picker(g, sources_attr: str, file_attr: str, run_attr: str,
                          select_fn, label: str) -> None:
    """커브 종류 하나(transfer/output)의 활성 파일 선택 + 런 선택 + 판정 근거."""
    sources: dict = getattr(g, sources_attr)
    active_file = getattr(g, file_attr)

    # 후보 파일이 둘 이상일 때만 고르는 드롭다운을 보여준다 — 파일이 하나뿐인
    # 소자에 쓸모없는 드롭다운을 붙이지 않는다.
    if len(sources) > 1:
        names = list(sources)
        choice = st.selectbox(
            f"{label} 파일", names,
            index=names.index(active_file) if active_file in names else 0,
            key=f"{run_attr}_file_{g.name}")
        if choice != active_file:
            select_fn(choice)
            active_file = choice

    runs = sources.get(active_file, []) if active_file else []

    # 재측정 파일(Data + Append1)이면 어느 런을 분석할지 고른다. 기본은 Latest.
    if len(runs) > 1:
        labels = [r.label for r in runs]
        idx = getattr(g, run_attr)
        idx = labels.index(st.selectbox(
            f"{label} 측정 런", labels,
            index=min(idx, len(labels) - 1), key=f"{run_attr}_{g.name}"))
        setattr(g, run_attr, idx)

    idx = getattr(g, run_attr)
    run = runs[idx] if runs and 0 <= idx < len(runs) else (runs[0] if runs else None)
    if run is not None:
        basis = REASON_LABELS.get(run.reason, run.reason)
        text = f"{label} 판정 근거: {basis} · '{active_file}'"
        if run.reason == "name":
            st.warning(text, icon="⚠")
        else:
            st.caption(text)


def render(app) -> None:
    g = app.device(app.selected)
    if g is None:
        return

    st.markdown(f"**소자 · {g.name}**")
    if g.warnings:
        with st.expander(f"⚠ 경고 {len(g.warnings)}건"):
            for w in g.warnings:
                st.caption(w)

    if g.transfer_sources:
        _render_source_picker(g, "transfer_sources", "transfer_file", "transfer_run_idx",
                              g.select_transfer_file, "Transfer")
    if g.output_sources:
        _render_source_picker(g, "output_sources", "output_file", "output_run_idx",
                              g.select_output_file, "Output")

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
