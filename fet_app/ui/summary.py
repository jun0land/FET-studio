"""그래프 뷰와 지표 패널 (스펙 §6.1).

그래프 두 개는 좌우, 지표/진단은 각 그래프 바로 아래에 열을 맞춰 놓는다.
커브가 하나뿐이면 늘리지 않고 10:8 비율을 유지한 채 중앙에 둔다.
"""

from __future__ import annotations

import dataclasses

import streamlit as st

from fet_app.export import summary_dataframe, summary_row
from fet_app.figure_output import output_figure
from fet_app.figure_transfer import transfer_figure
from fet_app.metrics import output_diagnostics, transfer_metrics
from fet_app.ui.panel_fit import fit_range_for

# theme.RESPONSIVE_CSS 가 :has() 로 찾는 마커. layout.SHELL_ANCHOR 와 같은 패턴으로
# 그래프 2열 블록의 첫 컬럼에 심어 900px 미만에서 세로 스택되도록 한다.
GRAPHS_ANCHOR = "<div class='fet-graphs-anchor'></div>"


def format_metric(value, kind: str) -> str:
    if value is None:
        return "—"
    if kind == "volt":
        return f"{value:.2f} V"
    if kind == "mobility":
        return f"{value:.2E}"
    if kind == "ratio":
        return f"{value:.1E}"
    if kind == "ss":
        return f"{value:.0f} mV/dec"
    if kind == "percent":
        return f"{value * 100:.2f} %"
    return f"{value:.4g}"


def _has_transfer_data(curve) -> bool:
    return curve is not None and not curve.forward.empty


def _has_output_data(curve) -> bool:
    if curve is None or not curve.blocks:
        return False
    return any(b.forward is not None and not b.forward.empty for b in curve.blocks)


def compute(app, g):
    """(TransferMetrics | None, OutputDiagnostics | None)."""
    tm = od = None
    if g.transfer is not None:
        tm = transfer_metrics(g.transfer, app.effective_params(g),
                              fit_range_for(app, g.name))
    if g.output is not None:
        od = output_diagnostics(g.output, app.thresholds)
    return tm, od


def effective_group(app, g):
    """params 를 전역값과 합친 사본. DeviceGroup.transfer/.output 은 읽기 전용
    프로퍼티(런 인덱스로 계산)라 __dict__ 를 그대로 재조립하는 방식은 쓸 수
    없다 — dataclasses.replace 로 params 필드만 바꾼 사본을 만든다."""
    return dataclasses.replace(g, params=app.effective_params(g))


def _transfer_settings(app):
    s = app.settings
    return {"geom": s["geom"], "style": s["style"], "axes": s["transfer_axes"],
            "trace": s["transfer_style"], "insets": s["insets"]}


def _output_settings(app):
    s = app.settings
    return {"geom": s["geom"], "style": s["style"], "axes": s["output_axes"],
            "trace": s["output_style"], "insets": s["insets"]}


def _metric_card(tm) -> None:
    st.markdown("**Transfer 지표**")
    if tm is None:
        st.caption("transfer 데이터 없음")
        return
    rows = [
        ("V_th", format_metric(tm.v_th, "volt")),
        ("μ_sat (cm²/Vs)", format_metric(tm.mu_sat, "mobility")),
        ("I_on/I_off", format_metric(tm.on_off, "ratio")),
        ("SS", format_metric(tm.ss_mv_dec, "ss")),
        ("ΔV_th", format_metric(tm.dv_th, "volt")),
        ("Fit R²", format_metric(tm.fit.r2 if tm.fit else None, "plain")),
    ]
    st.table({"항목": [r[0] for r in rows], "값": [r[1] for r in rows]})
    for w in tm.warnings:
        st.warning(w, icon="⚠")


def _diagnostic_card(od) -> None:
    st.markdown("**Output 진단**")
    if od is None:
        st.caption("output 데이터 없음")
        return
    w = od.worst
    rows = [
        ("0 V 오프셋", format_metric(w.get("zero_offset"), "percent")),
        ("원점 선형성 R²", format_metric(w.get("linearity_r2"), "plain")),
        ("포화 기울기비", format_metric(w.get("saturation_ratio"), "plain")),
        ("게이트 누설", format_metric(w.get("gate_leak"), "percent")),
    ]
    st.table({"항목": [r[0] for r in rows], "값": [r[1] for r in rows]})

    if od.blocks:
        with st.expander(f"블록별 진단 ({len(od.blocks)}개)", expanded=False):
            block_rows = {
                "V_G (V)": [], "상태": [], "0V 오프셋": [],
                "원점 선형성 R²": [], "포화 기울기비": [], "게이트 누설": [],
            }
            for b in od.blocks:
                block_rows["V_G (V)"].append(f"{b.v_g:g}")
                block_rows["상태"].append("on" if b.is_on else "off (진단 생략)")
                block_rows["0V 오프셋"].append(format_metric(b.zero_offset, "percent"))
                if b.is_on:
                    block_rows["원점 선형성 R²"].append(format_metric(b.linearity_r2, "plain"))
                    block_rows["포화 기울기비"].append(format_metric(b.saturation_ratio, "plain"))
                else:
                    block_rows["원점 선형성 R²"].append("off (진단 생략)")
                    block_rows["포화 기울기비"].append("off (진단 생략)")
                block_rows["게이트 누설"].append(format_metric(b.gate_leak, "percent"))
            st.table(block_rows)

    for f in od.flags:
        st.warning(f, icon="⚠")


def render_device_view(app, k: float) -> None:
    g = app.device(app.selected)
    if g is None:
        return
    tm, od = compute(app, g)

    # "커브가 있다" 는 None 이 아닌 것만으로는 부족하다. 측정이 중단된 파일은
    # 빈 프레임을 만들어 내고, 그걸 그리려 하면 축 계산에서 터진다.
    has_t = _has_transfer_data(g.transfer)
    has_o = _has_output_data(g.output)
    if has_t and has_o:
        cols = st.columns(2, gap="medium")
        with cols[0]:
            # 이 마커가 있어야 RESPONSIVE_CSS 가 이 그래프 2열 블록을 찾아
            # 900px 미만에서 세로로 쌓는다.
            st.markdown(GRAPHS_ANCHOR, unsafe_allow_html=True)
            st.plotly_chart(transfer_figure(g.transfer, tm, _transfer_settings(app), k),
                            use_container_width=False, key=f"tf_{g.name}")
            _metric_card(tm)
        with cols[1]:
            st.plotly_chart(output_figure(g.output, _output_settings(app), k),
                            use_container_width=False, key=f"of_{g.name}")
            _diagnostic_card(od)
    elif has_t or has_o:
        # 커브가 하나뿐이면 늘리지 않고 10:8 비율 그대로, 가운데에 둔다.
        left, mid, right = st.columns([1, 2, 1], gap="medium")
        with mid:
            if has_t:
                st.plotly_chart(transfer_figure(g.transfer, tm, _transfer_settings(app), k),
                                use_container_width=False, key=f"tf_{g.name}")
                _metric_card(tm)
            else:
                st.plotly_chart(output_figure(g.output, _output_settings(app), k),
                                use_container_width=False, key=f"of_{g.name}")
                _diagnostic_card(od)
    else:
        st.info("이 소자에는 표시할 커브가 없습니다.")


def _st_version_tuple() -> tuple[int, int, int]:
    nums = []
    for p in str(st.__version__).split(".")[:3]:
        digits = "".join(ch for ch in p if ch.isdigit())
        nums.append(int(digits) if digits else 0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def _supports_row_select() -> bool:
    """st.dataframe(on_select=...) 는 Streamlit >= 1.35 부터. 그보다 낮으면
    selectbox 로 대신 소자를 고른다 — 크래시보다 낫다."""
    return _st_version_tuple() >= (1, 35, 0)


def render_summary_table(app) -> None:
    st.markdown("### 전체 요약")
    if st.button("← 소자 보기로"):
        app.show_summary = False
        st.rerun()

    rows = []
    for g in app.devices:
        tm, od = compute(app, g)
        rows.append(summary_row(effective_group(app, g), tm, od))
    df = summary_dataframe(rows)

    if _supports_row_select():
        event = st.dataframe(df, use_container_width=True, hide_index=True,
                             on_select="rerun", selection_mode="single-row",
                             key="summary_table")
        picked = event.selection.rows if hasattr(event, "selection") else []
        if picked:
            app.selected = df.iloc[picked[0]]["Device"]
            app.show_summary = False
            st.rerun()
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        if len(df):
            choice = st.selectbox("소자로 이동", df["Device"].tolist(), key="summary_jump")
            if st.button("이동", key="summary_jump_go"):
                app.selected = choice
                app.show_summary = False
                st.rerun()

