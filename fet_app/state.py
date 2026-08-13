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


def _merge_kind_sources(old: DeviceGroup, g: DeviceGroup, sources_attr: str,
                        file_attr: str, label: str) -> None:
    """새로 파싱된 ``g`` 의 한 커브 종류(sources_attr)를 기존 소자 ``old`` 에 합친다.

    ``g`` 는 이번에 새로 올라온 파일들만으로 조립된 그룹이라, 같은 배치 안의
    중복(=두 번째 파일)은 group_files 가 이미 g.warnings 에 경고를 남기고
    비활성으로 만들어 뒀다. 여기서는 g 안에서 이긴 파일(g 의 활성 파일)이
    old 의 기존 활성 파일과 부딪히는 경우만 새로 판정하면 된다 — old 에 아직
    활성 파일이 없으면 그 자리를 차지하고, 이미 있으면 후보로만 추가하고
    경고한다. g 안에서 이미 졌던 파일은 조용히 후보로만 추가한다(중복 경고
    방지). extra_files 는 파생 프로퍼티라 별도로 손댈 것이 없다."""
    old_sources: dict = getattr(old, sources_attr)
    new_sources: dict = getattr(g, sources_attr)
    if not new_sources:
        return
    g_active = getattr(g, file_attr)
    ordered = sorted(new_sources, key=lambda n: n != g_active)  # g_active 먼저
    for name in ordered:
        if name in old_sources:
            continue
        old_sources[name] = new_sources[name]
        if getattr(old, file_attr) is None:
            setattr(old, file_attr, name)
        elif name == g_active:
            old.warnings.append(
                f"'{name}' 은 {label} 가 이미 있어 사용하지 않았습니다. "
                "소자 패널에서 교체할 수 있습니다."
            )
        # else: g 안에서 이미 진 파일 — group_files 가 이미 경고했다.


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
        _merge_kind_sources(old, g, "transfer_sources", "transfer_file", "transfer")
        _merge_kind_sources(old, g, "output_sources", "output_file", "output")
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
