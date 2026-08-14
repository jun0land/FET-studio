"""그래프 뷰와 지표 패널 (스펙 §6.1).

그래프 두 개는 좌우, 지표/진단은 각 그래프 바로 아래에 열을 맞춰 놓는다.
커브가 하나뿐이면 늘리지 않고 10:8 비율을 유지한 채 중앙에 둔다.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json

import numpy as np
import pandas as pd
import streamlit as st

from fet_app.export import summary_dataframe, summary_row
from fet_app.figure_common import px_size
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


def _frame_digest(h, df) -> None:
    """숫자 프레임은 numpy 버퍼를 그대로 먹인다 — pandas 해시보다 15배 빠르다
    (예제 18커브 기준 44 ms -> 2.9 ms, 실측). 숫자로 못 바꾸는 프레임만
    pandas 해시로 되돌아간다."""
    if df is None or len(df) == 0:
        h.update(b"|empty|")
        return
    h.update("|".join(map(str, df.columns)).encode("utf-8"))
    try:
        h.update(np.ascontiguousarray(df.to_numpy(dtype=float)).tobytes())
    except (TypeError, ValueError):
        h.update(pd.util.hash_pandas_object(df, index=False).to_numpy().tobytes())


def curve_fingerprint(curve) -> str:
    """커브 데이터 내용의 지문.

    캐시 키를 소자 이름·파일명으로만 만들면 안 된다. st.cache_data 는 기본이
    전역(global) 스코프라 세션이 달라도 캐시를 공유하는데, 서로 다른 사용자가
    같은 이름('1-1.xls')으로 다른 데이터를 올리면 남의 결과를 받아 간다.
    내용 자체를 키에 넣어 그 충돌을 원천 차단한다. 같은 이유로 소자 패널에서
    활성 파일·측정 런을 바꾸면 지문이 달라져 자동으로 다시 계산된다.
    """
    if curve is None:
        return "none"
    h = hashlib.blake2b(digest_size=16)
    blocks = getattr(curve, "blocks", None)
    if blocks is not None:                                    # OutputCurve
        for b in blocks:
            h.update(f"|vg={b.v_g!r}|".encode())
            _frame_digest(h, b.forward)
            _frame_digest(h, b.reverse)
    else:                                                     # TransferCurve
        h.update(f"|vds={curve.v_ds!r}|dual={curve.dual!r}|".encode())
        _frame_digest(h, curve.forward)
        _frame_digest(h, curve.reverse)
    return h.hexdigest()


def cache_key(payload: dict) -> str:
    """캐시 키 문자열. default=str 은 numpy 스칼라처럼 JSON 이 모르는 값이
    섞여 들어와도 키 생성이 터지지 않게 하는 안전망이다."""
    return json.dumps(payload, sort_keys=True, default=str)


# _ 로 시작하는 인자는 st.cache_data 가 해싱하지 않는다. TransferCurve/
# DeviceParams 같은 커스텀 객체를 해싱시키지 않으면서, 캐시 동일성은 전적으로
# key 문자열이 책임진다(위 curve_fingerprint 가 그 핵심).
@st.cache_data(show_spinner=False, max_entries=256)
def _transfer_metrics_cached(_curve, _params, _fit_range, key: str):
    return transfer_metrics(_curve, _params, _fit_range)


@st.cache_data(show_spinner=False, max_entries=256)
def _output_diagnostics_cached(_curve, _thresholds, key: str):
    return output_diagnostics(_curve, _thresholds)


def compute(app, g):
    """(TransferMetrics | None, OutputDiagnostics | None).

    지표 계산은 순수 함수라 캐시한다. 이 함수는 소자 뷰(선택된 1개)와 내보내기
    탭의 요약표(전 소자)에서 각각 호출되는데, st.tabs 는 **화면에 안 보이는
    탭의 본문도 매 rerun 마다 실행**하므로 캐시가 없으면 아무 위젯이나 건드릴
    때마다 전 소자 지표가 다시 계산된다 — 예제 9소자 기준 rerun 당 약 1.4초가
    여기서만 소모됐다(실측). 캐시 이후에는 지문 계산 약 3 ms 만 남는다.
    """
    tm = od = None
    if g.transfer is not None:
        p = app.effective_params(g)
        fr = fit_range_for(app, g.name)
        tm = _transfer_metrics_cached(g.transfer, p, fr, cache_key({
            "curve": curve_fingerprint(g.transfer),
            "params": [p.w_um, p.l_um, p.eps_r, p.d_nm],
            "fit_range": list(fr) if fr else None,
        }))
    if g.output is not None:
        od = _output_diagnostics_cached(g.output, app.thresholds, cache_key({
            "curve": curve_fingerprint(g.output),
            "thresholds": app.thresholds,
        }))
    return tm, od


def effective_group(app, g):
    """params 를 전역값과 합친 사본. DeviceGroup.transfer/.output 은 읽기 전용
    프로퍼티(런 인덱스로 계산)라 __dict__ 를 그대로 재조립하는 방식은 쓸 수
    없다 — dataclasses.replace 로 params 필드만 바꾼 사본을 만든다."""
    return dataclasses.replace(g, params=app.effective_params(g))


def _transfer_settings(app):
    s = app.settings
    return {"geom": s["transfer_geom"], "style": s["style"], "axes": s["transfer_axes"],
            "trace": s["transfer_style"], "insets": s["insets"]}


def _output_settings(app):
    s = app.settings
    return {"geom": s["output_geom"], "style": s["style"], "axes": s["output_axes"],
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
        # Transfer 기본값(8x10)과 Output 기본값(10x8)은 세로 길이가 달라 나란히
        # 놓으면 높이가 어긋난다. 화면에서만 Transfer 를 Output 의 렌더링 높이에
        # 맞춰 비율 그대로 더 줄인다 — 내보내기는 k=1.0 이라 영향을 받지 않는다.
        transfer_geom = app.settings["transfer_geom"]
        output_geom = app.settings["output_geom"]
        k_transfer = k * (float(output_geom["page_h_in"]) / float(transfer_geom["page_h_in"]))
        with cols[0]:
            # 이 마커가 있어야 RESPONSIVE_CSS 가 이 그래프 2열 블록을 찾아
            # 900px 미만에서 세로로 쌓는다.
            st.markdown(GRAPHS_ANCHOR, unsafe_allow_html=True)
            st.plotly_chart(transfer_figure(g.transfer, tm, _transfer_settings(app), k_transfer),
                            use_container_width=False, key=f"tf_{g.name}")
            # 지표 테이블도 축소된 그래프 폭에 맞춰 좁힌다. st.container(key=...) 가
            # .st-key-<key> 클래스를 붙여주므로 그 클래스에 max-width 를 건다.
            t_w_px, _t_h_px = px_size(transfer_geom, k_transfer)
            st.markdown(
                f"<style>.st-key-transfer_metric_{g.name} {{ max-width: {t_w_px}px; }}</style>",
                unsafe_allow_html=True,
            )
            with st.container(key=f"transfer_metric_{g.name}"):
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

