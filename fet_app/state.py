"""세션 상태. streamlit import 는 boot() 안에서만 한다."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from fet_app.constants import DEFAULTS, DEFAULT_THRESHOLDS
from fet_app.grouping import DeviceGroup, group_files, parse_file
from fet_app.params import DeviceParams

SETTINGS_KEYS = ("geom", "style", "transfer_axes", "output_axes",
                 "transfer_style", "output_style", "insets")


def default_settings() -> dict:
    return {k: copy.deepcopy(DEFAULTS[k]) for k in SETTINGS_KEYS}


@dataclass
class AppState:
    devices: list[DeviceGroup] = field(default_factory=list)
    selected: str | None = None
    file_names: set = field(default_factory=set)
    global_params: DeviceParams = field(default_factory=DeviceParams)
    thresholds: dict = field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))
    settings: dict = field(default_factory=default_settings)
    preview_scale: float | None = None   # None = 자동, 값 = 수동 배율
    search: str = ""
    show_summary: bool = False

    def device(self, name: str | None) -> DeviceGroup | None:
        return next((g for g in self.devices if g.name == name), None)

    def effective_params(self, g: DeviceGroup) -> DeviceParams:
        return g.params.merged_with(self.global_params)


def add_files(app: AppState, files: list[tuple[str, bytes]]) -> list[str]:
    """(파일명, bytes) 목록을 등록한다. 반환은 사용자에게 보여줄 경고 목록."""
    warns: list[str] = []
    parsed = []
    for name, blob in files:
        if name in app.file_names:
            continue
        try:
            parsed.append(parse_file(blob, name))
            app.file_names.add(name)
        except Exception as e:  # noqa: BLE001
            warns.append(f"'{name}' 을 읽지 못했습니다: {e}")
    if not parsed:
        return warns

    # 기존 소자는 app.devices 의 같은 객체를 그대로 이어 쓴다(existing 은 리스트만
    # 복사) — 아래에서 old.* 를 직접 mutate 하므로 old.params 도 이미 보존된다.
    existing = list(app.devices)

    for g in group_files(parsed):
        old = next((x for x in existing if x.name == g.name), None)
        if old is None:
            existing.append(g)
            continue
        if not old.transfer_runs and g.transfer_runs:
            old.transfer_runs, old.transfer_file = g.transfer_runs, g.transfer_file
        elif g.transfer_runs and g.transfer_file and g.transfer_file not in old.extra_files:
            old.extra_files.append(g.transfer_file)
        if not old.output_runs and g.output_runs:
            old.output_runs, old.output_file = g.output_runs, g.output_file
        elif g.output_runs and g.output_file and g.output_file not in old.extra_files:
            old.extra_files.append(g.output_file)
        old.warnings.extend(g.warnings)

    app.devices = existing
    if app.selected is None and app.devices:
        app.selected = app.devices[0].name
    return warns


def boot() -> AppState:
    """세션에 AppState 를 붙이고 돌려준다."""
    import streamlit as st

    if "app" not in st.session_state:
        st.session_state["app"] = AppState()
    return st.session_state["app"]
