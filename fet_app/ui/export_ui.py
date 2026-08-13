"""내보내기 UI (스펙 §7)."""

from __future__ import annotations

import streamlit as st

from fet_app import export
from fet_app.figure_output import output_figure
from fet_app.figure_transfer import transfer_figure
from fet_app.ui.summary import _output_settings, _transfer_settings, compute, effective_group

FORMATS = ["PNG (투명)", "JPG (흰 배경)", "SVG", "PDF"]
_FMT_KEY = {"PNG (투명)": "png", "JPG (흰 배경)": "jpg", "SVG": "svg", "PDF": "pdf"}


def _figures(app, g, tm):
    out = []
    if g.transfer is not None:
        out.append(("transfer", transfer_figure(g.transfer, tm, _transfer_settings(app), 1.0)))
    if g.output is not None:
        out.append(("output", output_figure(g.output, _output_settings(app), 1.0)))
    return out


def render(app) -> None:
    st.divider()
    with st.expander("내보내기", expanded=False):
        fmt_label = st.selectbox("이미지 형식", FORMATS, key="exp_fmt")
        fmt = _FMT_KEY[fmt_label]
        scale = st.selectbox("배율", [1, 2, 4], index=0, key="exp_scale")

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
                        items.append((f"{g.name}/{kind}.html",
                                      fig.to_html(include_plotlyjs="cdn").encode("utf-8")))
                if g.transfer is not None:
                    items.append((f"{g.name}/transfer_processed.csv",
                                  export.transfer_processed_csv(g.transfer, tm).encode("utf-8-sig")))
                if g.output is not None:
                    items.append((f"{g.name}/output_processed.csv",
                                  export.output_processed_csv(g.output).encode("utf-8-sig")))
            st.session_state["zip_blob"] = export.build_zip(items)
            if failed:
                st.warning("이미지 렌더 실패 — HTML 로 대체했습니다: " + ", ".join(failed))

        if st.session_state.get("zip_blob"):
            st.download_button("ZIP 다운로드", data=st.session_state["zip_blob"],
                               file_name="fet_studio_export.zip", mime="application/zip",
                               use_container_width=True)
