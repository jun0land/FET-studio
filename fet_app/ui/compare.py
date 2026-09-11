"""Transfer 비교 — 두 단계.

1. **소자 선택**: transfer 미리보기 격자에서 겹칠 소자를 고른다. 여기서는 고르기만
   한다 — 색·이름 같은 편집은 다음 화면 몫이다.
2. **멀티 커브 편집**: 고른 커브를 한 그래프에 겹치고, 커브마다 색·레전드 이름·
   fit 구간을 만지며, 그 fit 에서 나온 성능 지표(V_th, μ_sat, I_on/I_off, SS,
   ΔV_th, R²)를 표로 함께 본다. √|I_D| 모드에서는 소자별 fit 직선과 V_th 마커가
   그래프 위에 같은 색으로 얹힌다.

둘 다 전체 요약 표(summary.render_summary_table)처럼 화면 전체를 쓰는 '다른 창'
이고, [← 소자 보기로] 로 돌아간다.

선택은 서식이 아니라 그때그때의 작업 상태라 AppState.compare_selected 에 두고,
색·이름·표시 옵션만 settings["compare"] 에 둔다. 색은 **고른 순서**대로 팔레트에서
배정한다 — 소자 목록 순서로 배정하면 선택을 바꿀 때마다 남아 있는 커브의 색까지
따라 바뀌어서, 같은 그림을 다시 만들기가 어려워진다.

fit 구간은 정보 탭(panel_fit)과 **같은 세션 값**을 쓴다. 어느 화면에서 바꿔도
같은 fit 이고, 지표도 summary.compute 의 캐시를 그대로 탄다.
"""

from __future__ import annotations

import copy

import pandas as pd
import streamlit as st

from fet_app import export
from fet_app.figure_compare import (
    LEGEND_POS_LABELS, MODE_LABELS, assign_colors, compare_figure,
)
from fet_app.metrics import transfer_metrics
from fet_app.ui import color_picker, panel_axes, panel_fit, panel_insets, panel_style
from fet_app.ui.export_ui import _FMT_KEY, _MIME, FORMATS, _cached_image_bytes
from fet_app.ui.panel_fit import fit_range_for
from fet_app.ui.summary import (
    _has_transfer_data, cache_key, compute, curve_fingerprint, effective_group,
    format_metric,
)
from fet_app.ui.viewport import preview_scale

# 미리보기 카드 한 줄에 몇 개를 놓을지.
PREVIEW_COLS = 4
# 썸네일 전용 배경 크기(inch)와 글자 크기(px). 본 그래프를 k 로 줄이면 폰트까지
# 같이 줄어 눈금이 뭉개지므로, 썸네일은 자기 크기·자기 폰트로 따로 그린다.
#
# 크기는 **가장 좁을 때 카드에 들어가는 폭**으로 잡아야 한다. Plotly 차트가
# 컨테이너보다 넓으면 폭만 컨테이너에 맞춰 찌그러지고 높이는 그대로 남아
# 종횡비가 깨진다 (viewport.py 에 같은 현상이 기록돼 있다).
#   theme.apply_ui_zoom 은 zoom = clamp(창폭/1440, 0.85, 1.0) 이므로 CSS 폭은
#   창이 좁아도 창폭/0.85 까지만 줄어든다 — 1000px 창이면 약 1176 CSS px,
#   좁게 잡아 1000 CSS px 로 봐도 본문은 좌우 패딩 1.6rem(약 51px)을 빼고 949px,
#   4열은 열 간격 1rem x 3(48px)을 더 빼서 카드가 약 225px 다.
# 그래서 썸네일 폭을 2.2 inch(211px)로 두면 그 폭에서도 눌리지 않는다.
THUMB_W_IN, THUMB_H_IN = 2.2, 1.8
THUMB_TICK_PX = 10
UNSELECTED_COLOR = "#9E9E9E"
# 편집 화면 배치. 그래프는 하나로 겹쳐져 폭이 고정(기본 배율에서 약 500px)이라,
# 화면을 [커브 카드 | 그래프 | 서식 패널] 평평한 3열로 나누고 그래프 오른쪽에
# 표시 옵션·다운로드·축·서식·인셋·크기 편집을 탭으로 세운다. 지표 표는 그 아래
# 그래프+서식 패널 폭을 쓴다.
#
# 3열을 평평하게 두는 이유: 서식 패널 안의 편집칸(min|max, major|minor 등)이
# 2열이라 패널 자체가 1단계 컬럼이어야 한다 — Streamlit 은 컬럼 중첩을 한
# 단계까지만 허용한다.
# 가장 좁을 때(1000 CSS px, 본문 949px): 열 간격 2 x 16px 을 빼면 917px 이고
# 그래프 칸은 917 * 2.8 / 5.1 = 503px 로 그래프(499px)보다 넓어야 종횡비가 산다.
# 그때 서식 패널은 약 234px — 2열 입력칸이 100px 남짓으로 숫자 몇 자는 들어간다.
EDIT_COLS = [1, 2.8, 1.3]
# 편집 화면에서 같이 보여주는 지표 표의 열 (summary_row 의 열 이름 그대로).
METRIC_COLUMNS = ["V_th (V)", "mu_sat (cm2/Vs)", "I_on/I_off", "SS (mV/dec)",
                  "dV_th (V)", "Fit R2", "Fit range (V)", "Fit points"]


def compare_devices(app) -> list:
    """transfer 커브가 실제로 있는 소자만. 빈 프레임(중단된 측정)은 뺀다."""
    return [g for g in app.devices if _has_transfer_data(g.transfer)]


def sync_selection(app, names: list[str], checked: set[str]) -> list[str]:
    """체크 상태 -> AppState.compare_selected. 이미 고른 것의 순서는 지킨다.

    체크박스는 매 rerun 마다 bool 만 돌려주므로 '언제 골랐는지'는 우리가
    기억해야 한다. 기존 순서를 앞에 두고 새로 체크된 것만 뒤에 붙이면, 색이
    배정된 소자는 계속 같은 색을 유지한다.
    """
    kept = [n for n in app.compare_selected if n in checked]
    added = [n for n in names if n in checked and n not in kept]
    app.compare_selected = kept + added
    return app.compare_selected


def _compare_settings(app) -> dict:
    s = app.settings
    return {"geom": s["transfer_geom"], "style": s["style"], "axes": s["transfer_axes"],
            "compare": s["compare"], "insets": s["insets"], "trace": s["transfer_style"]}


def _thumb_settings(app) -> dict:
    """썸네일용 settings 사본 — 작은 배경, 축 제목·레전드·fit 없음."""
    base = copy.deepcopy(_compare_settings(app))
    base["geom"].update(page_w_in=THUMB_W_IN, page_h_in=THUMB_H_IN,
                        graph_left_pct=20.0, graph_top_pct=6.0,
                        graph_width_pct=74.0, graph_height_pct=86.0)
    base["style"].update(tick_font_size=THUMB_TICK_PX, title_font_size=THUMB_TICK_PX,
                         line_width=1.5)
    for axis in ("x", "y", "y2"):
        base["axes"][axis]["title"] = ""
    # 썸네일은 '어느 커브인지' 알아보는 용도라 가장 낯익은 log|I_D| 하나만 그린다.
    base["compare"]["mode"] = "log"
    base["compare"]["show_reverse"] = False
    base["compare"]["legend"] = False
    base["compare"]["show_fit"] = False
    base["insets"] = copy.deepcopy(base["insets"])
    base["insets"]["sample"]["text"] = ""
    return base


def device_label(app, name: str) -> str:
    """레전드에 쓸 이름. 지정이 없거나 비어 있으면 소자 이름을 그대로 쓴다."""
    labels = app.settings["compare"].get("labels") or {}
    return str(labels.get(name, "")).strip() or name


def selected_groups(app) -> list:
    """고른 순서대로의 DeviceGroup 목록. 사라졌거나 비어 있는 소자는 뺀다."""
    out = []
    for name in app.compare_selected:
        g = app.device(name)
        if g is not None and _has_transfer_data(g.transfer):
            out.append(g)
    return out


def selected_items(app, with_fit: bool = False) -> list[tuple]:
    """[(레전드 이름, TransferCurve, 색[, FitResult])] — 고른 순서 그대로.

    ``with_fit`` 이면 소자마다 지표를 계산해(캐시) fit 을 함께 넣는다 — 편집
    화면의 그래프용. 썸네일·선택 화면은 fit 이 필요 없으니 계산하지 않는다.
    """
    colors = assign_colors(app.compare_selected, app.settings["compare"].get("colors"))
    out = []
    for g in selected_groups(app):
        item = [device_label(app, g.name), g.transfer, colors[g.name]]
        if with_fit:
            tm, _od = compute(app, g)
            item.append(getattr(tm, "fit", None))
        out.append(tuple(item))
    return out


def compare_image_plan(app, fmt: str, scale: int):
    """(캐시 키, 인자 없는 렌더 함수). export_ui.device_image_plan 과 같은 규칙 —
    세션·앱 상태는 여기서 다 읽고, 반환된 함수는 순수 계산만 한다. fit 은 그
    함수 안에서 다시 계산한다(캐시된 지표 객체를 클로저에 넣어도 되지만,
    파라미터·fit 구간까지 키에 넣어야 하는 건 마찬가지라 계산 재현이 더 단순하다).
    """
    settings = copy.deepcopy(_compare_settings(app))
    colors = assign_colors(app.compare_selected, settings["compare"].get("colors"))
    plan = []
    for g in selected_groups(app):
        params = app.effective_params(g)
        plan.append((device_label(app, g.name), g.transfer, colors[g.name],
                     params, fit_range_for(app, g.name)))
    key = cache_key({
        "kind": "compare", "fmt": fmt, "scale": int(scale), "settings": settings,
        "items": [(label, curve_fingerprint(curve), color,
                   [p.w_um, p.l_um, p.eps_r, p.d_nm], list(fr) if fr else None)
                  for label, curve, color, p, fr in plan],
    })

    def _render() -> bytes:
        items = [(label, curve, color, transfer_metrics(curve, params, fr).fit)
                 for label, curve, color, params, fr in plan]
        return export.figure_bytes(compare_figure(items, settings, 1.0), fmt, scale)

    return key, _render


# ---------------- 1단계: 소자 선택 ----------------

def _render_select(app, devices) -> None:
    names = [g.name for g in devices]
    # 버튼 셋은 내용 폭으로 왼쪽에 모으고, 안내 문구가 남는 폭을 갖는다.
    c1, c2, c3, c4 = st.columns([1, 1, 1.4, 4], vertical_alignment="center")
    with c1:
        if st.button("전체 선택", key="cmp_all"):
            app.compare_selected = list(names)
            st.rerun()
    with c2:
        if st.button("선택 해제", key="cmp_none"):
            app.compare_selected = []
            st.rerun()
    with c3:
        if st.button("멀티 커브 편집 →", type="primary", key="cmp_go_edit",
                     disabled=not app.compare_selected):
            app.compare_stage = "edit"
            st.rerun()
    with c4:
        st.caption(f"{len(app.compare_selected)}개 선택 · 고른 순서대로 색이 배정됩니다")

    thumb = _thumb_settings(app)
    colors = assign_colors(app.compare_selected, app.settings["compare"].get("colors"))
    checked = set()
    for row_start in range(0, len(devices), PREVIEW_COLS):
        row = devices[row_start:row_start + PREVIEW_COLS]
        cols = st.columns(PREVIEW_COLS)
        for col, g in zip(cols, row):
            with col:
                on = st.checkbox(g.name, value=g.name in app.compare_selected,
                                 key=f"cmp_sel_{g.name}")
                if on:
                    checked.add(g.name)
                # 고른 소자는 배정된 색으로, 아닌 것은 회색으로 — 썸네일 자체가
                # '이 커브가 어떤 색으로 겹쳐질지' 를 미리 보여준다.
                color = colors.get(g.name, UNSELECTED_COLOR) if on else UNSELECTED_COLOR
                st.plotly_chart(
                    compare_figure([(g.name, g.transfer, color)], thumb, 1.0),
                    use_container_width=False, key=f"cmp_thumb_{g.name}")
    sync_selection(app, names, checked)


# ---------------- 2단계: 멀티 커브 편집 ----------------

def _render_edit_controls(app) -> None:
    cfg = app.settings["compare"]
    modes = list(MODE_LABELS)
    current_mode = cfg.get("mode", "dual")
    cfg["mode"] = st.selectbox("값", modes,
                               index=modes.index(current_mode) if current_mode in modes else 0,
                               format_func=lambda m: MODE_LABELS[m], key="cmp_mode")
    positions = list(LEGEND_POS_LABELS)
    current = cfg.get("legend_pos", "bottom-left")
    cfg["legend_pos"] = st.selectbox(
        "레전드 위치", positions,
        index=positions.index(current) if current in positions else 0,
        format_func=lambda p: LEGEND_POS_LABELS[p], key="cmp_legend_pos",
        disabled=not cfg.get("legend", True))
    # 옆 패널은 좁다(가장 좁을 때 약 170px) — 체크박스를 세로로 쌓는다.
    cfg["legend"] = st.checkbox("레전드", value=bool(cfg.get("legend", True)),
                                key="cmp_legend")
    cfg["show_reverse"] = st.checkbox("reverse", value=bool(cfg.get("show_reverse", True)),
                                      key="cmp_rev")
    cfg["show_sweep_arrows"] = st.checkbox(
        "스윕 방향 화살표", value=bool(cfg.get("show_sweep_arrows", True)),
        key="cmp_arrows", disabled=not cfg["show_reverse"])
    cfg["show_fit"] = st.checkbox("fit 직선", value=bool(cfg.get("show_fit", True)),
                                  key="cmp_fit")
    if cfg["show_fit"] and cfg["mode"] == "log":
        st.caption("fit 직선·V_th 마커는 √|I_D| 축이 있는 모드에서 그려집니다 "
                   "(fit 은 √|I_D| 위의 직선이라서요).")


def _metric_line(tm) -> str:
    """카드 안 한 줄 요약. 표는 오른쪽에 따로 있으니 핵심 셋만."""
    if tm is None:
        return "지표 없음"
    return (f"V_th {format_metric(tm.v_th, 'volt')} · "
            f"μ_sat {format_metric(tm.mu_sat, 'mobility')} · "
            f"R² {format_metric(tm.fit.r2 if tm.fit else None, 'plain')}")


def _render_curve_card(app, g, color: str) -> None:
    """커브 하나의 편집 카드: [스와치][레전드 이름] / fit 구간 / 지표 한 줄.

    카드는 이미 왼쪽 컬럼 안이라 여기서 여는 st.columns 가 중첩 한 단계째다
    (Streamlit 이 허용하는 마지막 단계). color_picker 와 panel_fit.render_device
    는 그 안에서 컬럼을 더 만들지 않도록 짜여 있다 — render_device 의 하한/상한
    2열은 카드 바로 아래(형제)라 괜찮다.
    """
    with st.container(border=True):
        swatch, name_col = st.columns([1, 3], vertical_alignment="bottom")
        with swatch:
            color_picker.color_picker("색", app.settings["compare"]["colors"], g.name,
                                      key=f"cmp_color_{g.name}", default=color)
        with name_col:
            labels = app.settings["compare"].setdefault("labels", {})
            labels[g.name] = st.text_input(
                f"레전드 이름 — {g.name}", value=labels.get(g.name, ""),
                placeholder=g.name, key=f"cmp_label_{g.name}",
                help="비워 두면 소자 이름. 마크업 가능: "
                     "_{아래첨자} ^{윗첨자} **굵게** *기울임*")
        panel_fit.render_device(g, compact=True)
        tm, _od = compute(app, g)
        st.caption(_metric_line(tm))
        for w in getattr(tm, "warnings", []) or []:
            st.caption(f"⚠ {w}")


def metrics_table(app, groups) -> pd.DataFrame:
    """고른 소자들의 성능 지표 — 전체 요약 표와 같은 계산(export.summary_row)을
    같은 열 이름으로 잘라 쓴다. 숫자는 가공하지 않는다(CSV 용)."""
    rows = []
    for g in groups:
        tm, od = compute(app, g)
        row = export.summary_row(effective_group(app, g), tm, od)
        rows.append({"Device": g.name, "Label": device_label(app, g.name),
                     **{c: row.get(c) for c in METRIC_COLUMNS}})
    return pd.DataFrame(rows, columns=["Device", "Label", *METRIC_COLUMNS])


def _formatted_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """화면용 — 지표 카드와 같은 자릿수로 문자열화한다."""
    kinds = {"V_th (V)": "volt", "mu_sat (cm2/Vs)": "mobility", "I_on/I_off": "ratio",
             "SS (mV/dec)": "ss", "dV_th (V)": "volt", "Fit R2": "plain"}
    out = df.copy()
    for col, kind in kinds.items():
        out[col] = [format_metric(None if v is None or v != v else v, kind)
                    for v in out[col]]
    return out


def _render_exports(app, df: pd.DataFrame) -> None:
    """내보내기 한 줄 — 그래프 이미지(형식·배율·받기)와 지표 CSV.

    작업 끝에 한 번 쓰는 것이라 화면 맨 아래(지표 표 아래)에 둔다. 편집 중에는
    눈에 안 띄어야 하고, 편집 칸들은 그래프 옆에서 스크롤 없이 닿아야 한다.
    """
    c1, c2, c3, c4, _ = st.columns([1, 0.7, 1.4, 1, 3], vertical_alignment="bottom")
    with c1:
        fmt = _FMT_KEY[st.selectbox("이미지 형식", FORMATS, key="cmp_fmt")]
    with c2:
        scale = st.selectbox("배율", [1, 2, 4], index=0, key="cmp_scale")
    key, render = compare_image_plan(app, fmt, scale)
    with c3:
        st.download_button("비교 그래프 다운로드",
                           data=lambda: _cached_image_bytes(render, key),
                           file_name=f"fet_transfer_compare.{fmt}",
                           mime=_MIME.get(fmt, "application/octet-stream"),
                           key="cmp_dl")
    with c4:
        st.download_button("지표 CSV", data=lambda: export.summary_csv_bytes(df),
                           file_name="fet_transfer_compare_metrics.csv", mime="text/csv",
                           key="cmp_metrics_csv")


def _render_edit(app) -> None:
    groups = selected_groups(app)
    if not groups:
        st.info("고른 소자가 없습니다. [← 소자 선택] 에서 먼저 골라 주세요.")
        return
    colors = assign_colors(app.compare_selected, app.settings["compare"].get("colors"))

    left, graph_col, side = st.columns(EDIT_COLS, gap="medium")
    with left:
        st.markdown("**커브**")
        for g in groups:
            _render_curve_card(app, g, colors[g.name])
    with graph_col:
        st.plotly_chart(
            compare_figure(selected_items(app, with_fit=True), _compare_settings(app),
                           preview_scale(app)),
            use_container_width=False, key="cmp_main")
    with side:
        _render_side_panel(app)

    # 지표 표는 그래프 + 서식 패널 폭 (왼쪽 카드 열과 같은 비율로 비운다).
    _, table_col = st.columns([EDIT_COLS[0], EDIT_COLS[1] + EDIT_COLS[2]], gap="medium")
    with table_col:
        st.markdown("**성능 지표**")
        df = metrics_table(app, groups)
        st.table(_formatted_metrics(df).drop(columns=["Device"]))
        st.markdown("**내보내기**")
        _render_exports(app, df)


def _render_side_panel(app) -> None:
    """그래프 오른쪽 서식 패널 — 탭 하나가 단일 그래프 편집 패널의 탭 하나에 대응한다.

    비교 그래프는 Transfer 그래프의 서식(transfer_axes·style·transfer_geom·insets)을
    그대로 물려받으므로 새 설정을 만들 게 없다 — 같은 dict 를 편집하는 같은 패널을
    여기서도 보여주면 된다. 위젯 key 도 같지만 좌측 패널은 이 화면에서 그려지지
    않으므로 충돌하지 않는다. 패널이 좁아 축 편집칸은 2열 x 2행 버전을 쓴다.
    Transfer 의 선 색은 소자별 색이 대신하므로 뺀다.
    """
    tabs = st.tabs(["표시", "축", "서식", "인셋", "크기"])
    with tabs[0]:
        _render_edit_controls(app)
    with tabs[1]:
        panel_axes.render_transfer_axes_compact(app)
    with tabs[2]:
        panel_style.render_typography(app)
        panel_style.render_transfer_colors(app, axes_only=True)
    with tabs[3]:
        panel_insets.render_for_compare(app)
    with tabs[4]:
        panel_style.render_page_and_presets(app)


# ---------------- 진입 ----------------

def render(app) -> None:
    editing = app.compare_stage == "edit"
    st.markdown("### Transfer 비교 — " + ("멀티 커브 편집" if editing else "소자 선택"))
    # 이동 버튼은 내용 폭으로 왼쪽에 모은다 — 화면 폭에 맞춰 늘리면 배너처럼 길어진다.
    c1, c2, _ = st.columns([1, 1, 6])
    with c1:
        if st.button("← 소자 보기로", key="cmp_back"):
            app.show_compare = False
            app.compare_stage = "select"
            st.rerun()
    with c2:
        if editing and st.button("← 소자 선택", key="cmp_back_select"):
            app.compare_stage = "select"
            st.rerun()

    devices = compare_devices(app)
    if not devices:
        st.info("Transfer 커브가 있는 소자가 없습니다.")
        return

    if editing:
        _render_edit(app)
    else:
        _render_select(app, devices)
