"""내보내기 UI (스펙 §7).

아코디언으로 감싸지 않는다 — 내보내기는 세션마다 여러 번 쓰는 기능이라
매번 펼쳐야 하는 아코디언은 방해가 된다. 크기·배율/프리셋(panel_style 에서
옮겨옴)만 부차적인 설정이라 작은 접이식으로 둔다.

이미지 렌더가 실패하면 HTML 로 조용히 바꿔치기하지 않는다 — 사용자가
PNG/JPG 를 받았다고 착각할 수 있다. 실패는 실패로 보여준다.
"""

from __future__ import annotations

import streamlit as st

from fet_app import export
from fet_app.figure_output import output_figure
from fet_app.figure_transfer import transfer_figure
from fet_app.ui import panel_style
from fet_app.ui.summary import (
    _has_output_data, _has_transfer_data, _output_settings, _transfer_settings,
    compute, effective_group,
)

FORMATS = ["PNG (투명)", "JPG (흰 배경)", "SVG", "PDF"]
_FMT_KEY = {"PNG (투명)": "png", "JPG (흰 배경)": "jpg", "SVG": "svg", "PDF": "pdf"}

_KIND_LABEL = {"transfer": "Transfer", "output": "Output"}
_MIME = {
    "png": "image/png", "jpg": "image/jpeg", "svg": "image/svg+xml",
    "pdf": "application/pdf",
}


def _figures(app, g, tm):
    out = []
    if g.transfer is not None:
        out.append(("transfer", transfer_figure(g.transfer, tm, _transfer_settings(app), 1.0)))
    if g.output is not None:
        out.append(("output", output_figure(g.output, _output_settings(app), 1.0)))
    return out


def _available_kinds(g) -> list[str]:
    """이 소자가 실제로 가진 커브 종류만. summary._has_*_data 재사용 —
    빈 프레임(중단된 측정)을 '있음'으로 잘못 보고하지 않는다."""
    kinds = []
    if _has_transfer_data(g.transfer):
        kinds.append("transfer")
    if _has_output_data(g.output):
        kinds.append("output")
    return kinds


def _device_filename(device: str, kind: str, ext: str) -> str:
    return f"{device}_{kind}.{ext}"


def _build_device_figure(app, g, kind: str):
    if kind == "transfer":
        tm, _od = compute(app, g)
        return transfer_figure(g.transfer, tm, _transfer_settings(app), 1.0)
    return output_figure(g.output, _output_settings(app), 1.0)


def _device_kind_download(app, g, kind: str, fmt: str, scale: int) -> None:
    """버튼 클릭 시에만 이미지를 만든다 — 렌더가 비싸므로 매 rerun 마다 새로
    만들지 않고 session_state 에 결과를 담아 재사용한다. 라벨은 'Transfer'/
    'Output' 만 쓴다. 형식·배율이 바뀌면 캐시 키가 달라져 자동으로 다시
    만들어진다.
    """
    label = _KIND_LABEL[kind]
    blob_key = f"exp_dev_blob_{g.name}_{kind}_{fmt}_{scale}"
    cached = st.session_state.get(blob_key)

    if cached is None:
        if st.button(label, key=f"exp_dev_btn_{g.name}_{kind}", use_container_width=True):
            try:
                fig = _build_device_figure(app, g, kind)
                st.session_state[blob_key] = export.figure_bytes(fig, fmt, scale)
                st.rerun()
            except export.KaleidoUnavailable as e:
                st.error(f"{label} 이미지를 만들지 못했습니다: {e}")
    else:
        st.download_button(
            label, data=cached, file_name=_device_filename(g.name, kind, fmt),
            mime=_MIME.get(fmt, "application/octet-stream"),
            use_container_width=True, key=f"exp_dev_dl_{g.name}_{kind}",
        )


def _render_device_downloads(app, fmt: str, scale: int) -> None:
    g = app.device(app.selected)
    st.markdown(f"**개별 다운로드 — {g.name}**" if g is not None else "**개별 다운로드**")
    if g is None:
        st.caption("소자를 선택하세요.")
        return
    kinds = _available_kinds(g)
    if not kinds:
        st.caption("이 소자에는 표시할 커브가 없습니다.")
        return
    cols = st.columns(len(kinds))
    for col, kind in zip(cols, kinds):
        with col:
            _device_kind_download(app, g, kind, fmt, scale)


def render(app) -> None:
    st.divider()
    st.markdown("**내보내기**")

    panel_style.render_page_and_presets(app)

    fmt_label = st.selectbox("이미지 형식", FORMATS, key="exp_fmt")
    fmt = _FMT_KEY[fmt_label]
    scale = st.selectbox("배율", [1, 2, 4], index=0, key="exp_scale")

    # 그래프 이미지만 담은 ZIP — 요약표 없이. 배율 선택 없이 항상 1x
    # (전체 ZIP/개별 다운로드처럼 세세히 고를 필요 없는, 빠르게 훑어볼 용도).
    if st.button("이미지 ZIP 만들기", use_container_width=True):
        items: list[tuple[str, bytes]] = []
        failed = []
        for g in app.devices:
            tm, _od = compute(app, g)
            for kind, fig in _figures(app, g, tm):
                try:
                    items.append((f"{g.name}/{kind}.{fmt}", export.figure_bytes(fig, fmt, 1)))
                except export.KaleidoUnavailable:
                    failed.append(f"{g.name}/{kind}")
        st.session_state["image_zip_blob"] = export.build_zip(items)
        if failed:
            st.error("다음 이미지를 만들지 못해 ZIP 에서 제외했습니다: " + ", ".join(failed))

    if st.session_state.get("image_zip_blob"):
        st.download_button("이미지 ZIP 다운로드", data=st.session_state["image_zip_blob"],
                           file_name="fet_studio_images.zip", mime="application/zip",
                           use_container_width=True)

    st.divider()

    rows = []
    for g in app.devices:
        tm, od = compute(app, g)
        rows.append(export.summary_row(effective_group(app, g), tm, od))
    df = export.summary_dataframe(rows)

    st.download_button("요약표 (XLSX)", data=export.summary_xlsx_bytes(df),
                       file_name="fet_summary.xlsx", use_container_width=True,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.download_button("요약표 (CSV)", data=export.summary_csv_bytes(df),
                       file_name="fet_summary.csv", mime="text/csv",
                       use_container_width=True)

    if st.button("전체 ZIP 만들기", use_container_width=True):
        items: list[tuple[str, bytes]] = [
            ("fet_summary.xlsx", export.summary_xlsx_bytes(df)),
            ("fet_summary.csv", export.summary_csv_bytes(df)),
        ]
        failed = []
        for g in app.devices:
            tm, _od = compute(app, g)
            for kind, fig in _figures(app, g, tm):
                try:
                    items.append((f"{g.name}/{kind}.{fmt}",
                                  export.figure_bytes(fig, fmt, scale)))
                except export.KaleidoUnavailable:
                    failed.append(f"{g.name}/{kind}")
            if g.transfer is not None:
                items.append((f"{g.name}/transfer_processed.csv",
                              export.transfer_processed_csv(g.transfer, tm).encode("utf-8-sig")))
            if g.output is not None:
                items.append((f"{g.name}/output_processed.csv",
                              export.output_processed_csv(g.output).encode("utf-8-sig")))
        st.session_state["zip_blob"] = export.build_zip(items)
        if failed:
            st.error("다음 이미지를 만들지 못해 ZIP 에서 제외했습니다: " + ", ".join(failed))

    if st.session_state.get("zip_blob"):
        st.download_button("ZIP 다운로드", data=st.session_state["zip_blob"],
                           file_name="fet_studio_export.zip", mime="application/zip",
                           use_container_width=True)

    st.divider()
    _render_device_downloads(app, fmt, scale)
