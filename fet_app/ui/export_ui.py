"""내보내기 UI (스펙 §7).

아코디언으로 감싸지 않는다 — 내보내기는 세션마다 여러 번 쓰는 기능이라
매번 펼쳐야 하는 아코디언은 방해가 된다. 크기·배율/프리셋(panel_style 에서
옮겨옴)만 부차적인 설정이라 작은 접이식으로 둔다.

이미지 렌더가 실패하면 HTML 로 조용히 바꿔치기하지 않는다 — 사용자가
PNG/JPG 를 받았다고 착각할 수 있다. 실패는 실패로 보여준다.

개별 이미지 다운로드는 st.download_button 의 **지연(deferred) 데이터** 기능을
쓴다: data 에 인자 없는 callable 을 넘기면 Streamlit 이 버튼을 그릴 때가 아니라
사용자가 누른 뒤에(별도 스레드에서) 그 callable 을 호출해 결과를 그대로
내려보낸다. 덕분에 '생성 버튼을 누르고 → 나타난 다운로드 버튼을 또 누르는'
2단계가 클릭 한 번으로 줄었고, 누르지 않은 rerun 에서는 kaleido 를 아예 부르지
않는다(1장당 약 3.3초, 실측 — 미리 만들어 두는 방식은 감당할 수 없다).

지연 callable 은 스크립트 스레드 밖에서 돈다. 그 안에서 st.* 을 건드리면 안
된다 — st.session_state 는 예외도 없이 빈 dict 로 읽혀 fit 구간 같은 설정이
조용히 사라진다. 그래서 세션에 의존하는 값은 전부 렌더 시점에 미리 읽어
클로저에 담고, callable 안에서는 순수 계산만 한다. 서식 dict 는 위젯이 제자리
에서 뒤엎으므로 사본을 뜬다 — 버튼이 그려질 때의 설정으로 내보내야 한다.
"""

from __future__ import annotations

import copy

import streamlit as st

from fet_app import export
from fet_app.figure_output import output_figure
from fet_app.figure_transfer import transfer_figure
from fet_app.metrics import transfer_metrics
from fet_app.ui import panel_style
from fet_app.ui.panel_fit import fit_range_for
from fet_app.ui.summary import (
    _has_output_data, _has_transfer_data, _output_settings, _transfer_settings,
    cache_key, compute, curve_fingerprint, effective_group,
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


def device_image_plan(app, g, kind: str, fmt: str, scale: int):
    """(캐시 키, 인자 없는 렌더 함수) 한 쌍을 만든다.

    세션·앱 상태를 읽는 일은 **전부 여기서** 끝낸다. 반환된 렌더 함수는
    지연 다운로드 스레드에서 불릴 수 있어 st.* 을 쓰면 안 되기 때문이다.

    캐시 키에는 그림을 바꾸는 값이 빠짐없이 들어가야 한다. 예전 키는
    f"{소자}_{kind}_{fmt}_{scale}" 뿐이라, 이미지를 한 번 만든 뒤 색·축·크기를
    바꿔도 키가 그대로여서 **설정이 반영 안 된 예전 이미지가 그대로 내려가는**
    버그가 있었다. 이제 서식 dict 와 커브 지문까지 키에 넣는다.
    """
    if kind == "transfer":
        curve = g.transfer
        params = app.effective_params(g)
        fit_range = fit_range_for(app, g.name)
        settings = copy.deepcopy(_transfer_settings(app))
        key = cache_key({
            "kind": "transfer", "fmt": fmt, "scale": int(scale),
            "curve": curve_fingerprint(curve),
            "params": [params.w_um, params.l_um, params.eps_r, params.d_nm],
            "fit_range": list(fit_range) if fit_range else None,
            "settings": settings,
        })

        def _render() -> bytes:
            tm = transfer_metrics(curve, params, fit_range)
            return export.figure_bytes(transfer_figure(curve, tm, settings, 1.0), fmt, scale)
    else:
        curve = g.output
        settings = copy.deepcopy(_output_settings(app))
        key = cache_key({
            "kind": "output", "fmt": fmt, "scale": int(scale),
            "curve": curve_fingerprint(curve),
            "settings": settings,
        })

        def _render() -> bytes:
            return export.figure_bytes(output_figure(curve, settings, 1.0), fmt, scale)

    return key, _render


# _render 는 언더스코어 인자라 해싱되지 않는다 — 캐시 동일성은 key 문자열이
# 전부 책임진다. 같은 설정으로 다시 누르면 kaleido 를 건너뛰고 즉시 내려간다.
# max_entries 를 작게 잡는 이유: 배율 4x PNG 는 한 장에 수 MB 라 넉넉히 잡으면
# 서버 메모리를 갉아먹는다. 노리는 건 '방금 받은 걸 다시 누르는' 경우뿐이다.
@st.cache_data(show_spinner=False, max_entries=8)
def _cached_image_bytes(_render, key: str) -> bytes:
    return _render()


def _device_kind_download(app, g, kind: str, fmt: str, scale: int) -> None:
    """클릭 한 번으로 바로 받아진다. 라벨은 'Transfer'/'Output' 만 쓴다."""
    key, render = device_image_plan(app, g, kind, fmt, scale)
    st.download_button(
        _KIND_LABEL[kind], data=lambda: _cached_image_bytes(render, key),
        file_name=_device_filename(g.name, kind, fmt),
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

    # 직렬화도 지연시킨다. 내보내기 탭은 화면에 안 보여도 매 rerun 마다
    # 실행되므로, 예전처럼 data= 에 바로 넘기면 아무도 안 받는 XLSX 를 매번
    # 새로 만든다(실측 약 47 ms/rerun). 클릭 수는 그대로 한 번이다.
    st.download_button("요약표 (XLSX)", data=lambda: export.summary_xlsx_bytes(df),
                       file_name="fet_summary.xlsx", use_container_width=True,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.download_button("요약표 (CSV)", data=lambda: export.summary_csv_bytes(df),
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
