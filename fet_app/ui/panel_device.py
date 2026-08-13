"""소자 파라미터 (좌측 편집 패널의 '정보' 탭). 비우면 전역 기본값을 상속한다."""

from __future__ import annotations

import streamlit as st

from fet_app.constants import DIELECTRIC_PRESETS
from fet_app.params import DeviceParams


def _render_source_picker(g, sources_attr: str, file_attr: str, run_attr: str,
                          select_fn, label: str) -> None:
    """커브 종류 하나(transfer/output)의 활성 파일 선택 + 런 선택."""
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


def render_global(app) -> None:
    """전역 기본값 — 좌측 패널 최상단, 탭보다 위에 항상 보이게 둔다.

    이 입력칸 자체가 곧 기본값이다. 처음 렌더될 때부터 W 1000 / L 50 /
    SiO2 3.9 / d 300 nm 로 미리 채워지므로 별도의 '기본값' 창이 따로
    필요 없다 — 예전엔 여기와 별개로 숨겨진 expander 가 하나 더 있어서
    같은 값을 두 군데서 편집할 수 있었다.
    """
    st.markdown("**전역 기본값**")
    p = app.global_params

    c1, c2 = st.columns(2)
    with c1:
        p.w_um = st.number_input("W (µm)", min_value=0.0, value=float(p.w_um or 1000.0),
                                 step=10.0, key="g_w")
    with c2:
        p.l_um = st.number_input("L (µm)", min_value=0.0, value=float(p.l_um or 50.0),
                                 step=1.0, key="g_l")

    names = list(DIELECTRIC_PRESETS) + ["Custom"]
    current = next((n for n, v in DIELECTRIC_PRESETS.items() if v == p.eps_r), None)
    idx = names.index(current) if current else 0  # 기본 SiO2

    c3, c4 = st.columns(2)
    with c3:
        choice = st.selectbox("유전체", names, index=idx, key="g_diel")
    with c4:
        if choice == "Custom":
            p.eps_r = st.number_input("ε_r", min_value=0.0,
                                      value=float(p.eps_r or 3.9), step=0.1, key="g_eps")
        else:
            # Custom 이 아니어도 선택한 물질의 값을 항상 여기 보여준다(공부용).
            # 값 자체는 프리셋이 정하므로 편집은 막는다.
            p.eps_r = DIELECTRIC_PRESETS[choice]
            st.number_input("ε_r", value=float(p.eps_r), step=0.1,
                            key="g_eps_display", disabled=True)

    p.d_nm = st.number_input("두께 (nm)", min_value=0.0, value=float(p.d_nm or 300.0),
                             step=10.0, key="g_d")


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
