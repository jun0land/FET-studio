"""좌측 패널 — 축(transfer/output) 범위·눈금·제목.

빈 입력은 0 이 아니라 '미지정'(None, = 자동)으로 해석해야 하므로 panel_device.py 와
같은 방식으로 st.number_input 대신 st.text_input + 파싱을 쓴다.
"""

from __future__ import annotations

import streamlit as st


def parse_optional_float(text) -> float | None:
    """빈 문자열/공백 -> None. 숫자로 못 읽어도 None (설정을 깨뜨리지 않는다)."""
    s = str(text).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_minor_dtick(text, axis_type: str):
    """log 축은 'D1'/'D2' 같은 문자열 그대로, 그 외 축은 숫자(없으면 None)."""
    if axis_type == "log":
        s = str(text).strip()
        return s or None
    return parse_optional_float(text)


def _fmt_num(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return f"{v:g}"
    return str(v)


def _axis_row(cfg: dict, key_prefix: str, label: str) -> None:
    c_label, c_auto, c_min, c_max, c_major, c_minor = st.columns(
        [0.7, 0.7, 1, 1, 1, 1])
    with c_label:
        st.markdown(f"**{label}**")
    with c_auto:
        cfg["auto"] = st.checkbox("auto", value=bool(cfg.get("auto", True)),
                                  key=f"{key_prefix}_auto")
    is_auto = bool(cfg["auto"])
    with c_min:
        min_txt = st.text_input("min", value=_fmt_num(cfg.get("min")),
                                key=f"{key_prefix}_min", disabled=is_auto,
                                label_visibility="collapsed", placeholder="min")
    with c_max:
        max_txt = st.text_input("max", value=_fmt_num(cfg.get("max")),
                                key=f"{key_prefix}_max", disabled=is_auto,
                                label_visibility="collapsed", placeholder="max")
    with c_major:
        major_txt = st.text_input("major", value=_fmt_num(cfg.get("dtick")),
                                  key=f"{key_prefix}_major",
                                  label_visibility="collapsed", placeholder="major")
    with c_minor:
        minor_txt = st.text_input("minor", value=_fmt_num(cfg.get("minor_dtick")),
                                  key=f"{key_prefix}_minor",
                                  label_visibility="collapsed", placeholder="minor(D1/D2)")

    cfg["min"] = parse_optional_float(min_txt)
    cfg["max"] = parse_optional_float(max_txt)
    cfg["dtick"] = parse_optional_float(major_txt)
    cfg["minor_dtick"] = parse_minor_dtick(minor_txt, cfg.get("type", "linear"))


def _axis_tab(axes: dict, key_prefix: str, rows: list[tuple[str, str]]) -> None:
    header = st.columns([0.7, 0.7, 1, 1, 1, 1])
    for col, text in zip(header, ["축", "auto", "min", "max", "major", "minor"]):
        col.caption(text)
    for axis_key, label in rows:
        _axis_row(axes[axis_key], f"{key_prefix}_{axis_key}", label)

    st.caption("제목 마크업: _{아래첨자}  ^{윗첨자}  **굵게**  *기울임*  {#RRGGBB|색}")
    for axis_key, label in rows:
        axes[axis_key]["title"] = st.text_input(
            f"{label} 제목", value=axes[axis_key].get("title", ""),
            key=f"{key_prefix}_{axis_key}_title")


def render(app) -> None:
    """아코디언으로 감싸지 않는다 — 이미 panel_edit 의
    st.tabs(["정보","축","인셋","서식"]) 안 '축' 탭 내용이라, 탭 안에 또
    아코디언을 두면 클릭이 한 번 더 든다."""
    s = app.settings
    tabs = st.tabs(["Transfer", "Output"])
    with tabs[0]:
        _axis_tab(s["transfer_axes"], "ax_t",
                 [("x", "X"), ("y", "좌Y"), ("y2", "우Y")])
    with tabs[1]:
        _axis_tab(s["output_axes"], "ax_o",
                 [("x", "X"), ("y", "Y")])
