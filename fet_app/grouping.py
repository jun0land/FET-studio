"""파일 -> ParsedFile -> DeviceGroup 조립 (스펙 §4.1)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from fet_app.curves import OutputCurve, TransferCurve, build_output, build_transfer
from fet_app.params import DeviceParams
from fet_app.parsing import (
    OUTPUT, TRANSFER, SettingsInfo, classify_curve, data_sheet, data_sheet_names,
    load_sheets, parse_settings, settings_frame,
)

# 파일명 끝에서 떼어낼 접미 토큰. 여기 없는 토큰은 stem 의 일부로 남긴다.
STRIP_TOKENS = {"out", "output", "transfer", "tr", "best"}
_SPLIT_RE = re.compile(r"[\s_]+")


@dataclass
class MeasurementRun:
    """파일 안의 측정 한 번. 재측정 파일은 Data 와 Append1 이 각각 하나씩이다."""

    sheet: str                      # "Data" / "Append1"
    label: str                      # UI 표시용 — "Latest Run" / "Run 1"
    is_latest: bool
    kind: str
    reason: str
    settings: SettingsInfo | None = None
    transfer: TransferCurve | None = None
    output: OutputCurve | None = None


@dataclass
class ParsedFile:
    name: str
    runs: list[MeasurementRun] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def latest(self) -> MeasurementRun | None:
        return self.runs[0] if self.runs else None

    @property
    def kind(self) -> str:
        return self.runs[0].kind if self.runs else ""


def parse_file(file_bytes: bytes, file_name: str) -> ParsedFile:
    """파일의 모든 측정 런을 읽는다. 반환 리스트는 Latest Run 이 맨 앞."""
    sheets, engine = load_sheets(file_bytes)
    run_settings = parse_settings(settings_frame(file_bytes, sheets, engine))
    sheet_names = data_sheet_names(sheets)
    if not sheet_names:
        raise ValueError("데이터 시트를 찾지 못했습니다.")

    warns: list[str] = []
    if len(run_settings) and len(run_settings) != len(sheet_names):
        warns.append(
            f"Settings 블록 {len(run_settings)}개와 데이터 시트 {len(sheet_names)}개가 "
            "맞지 않습니다. 시트 이름으로 최선을 다해 짝지었습니다."
        )

    runs: list[MeasurementRun] = []
    for sheet in sheet_names:
        data = data_sheet(sheets, sheet)
        info = run_settings.block(sheet)
        kind, reason = classify_curve(data, info, file_name)
        if reason == "name":
            warns.append(
                f"'{sheet}' 의 커브 종류를 Settings·열 구조로 가리지 못해 파일명으로 "
                "판정했습니다. 소자 패널의 판정 근거 표시에서 확인하세요."
            )

        transfer = output = None
        if kind == TRANSFER:
            transfer = build_transfer(data, info)
            if transfer.v_ds is None:
                warns.append(
                    f"'{sheet}' 의 Settings 에서 V_DS 를 읽지 못했습니다. "
                    "μ_sat 의 포화 조건 검사를 건너뜁니다."
                )
        else:
            output = build_output(data, info)
            if not output.blocks:
                warns.append(f"'{sheet}' 에서 output 블록을 하나도 만들지 못했습니다.")

        is_latest = (run_settings.latest == sheet) if len(run_settings) else (sheet == sheet_names[0])
        runs.append(MeasurementRun(
            sheet=sheet, label="", is_latest=is_latest, kind=kind, reason=reason,
            settings=info, transfer=transfer, output=output,
        ))

    # Latest 를 맨 앞으로. 나머지는 시트 순서 유지.
    runs.sort(key=lambda r: (not r.is_latest,))
    single = len(runs) == 1
    for i, r in enumerate(runs):
        if single:
            r.label = r.sheet
        else:
            r.label = f"{r.sheet} (Latest)" if r.is_latest else r.sheet

    return ParsedFile(name=file_name, runs=runs, warnings=warns)


def stem_of(file_name: str) -> str:
    """확장자와 알려진 접미 토큰을 떼어낸 나머지가 소자 이름."""
    stem = Path(str(file_name)).stem.strip()
    parts = [p for p in _SPLIT_RE.split(stem) if p]
    while len(parts) > 1 and parts[-1].lower() in STRIP_TOKENS:
        parts.pop()
    return " ".join(parts) if parts else stem


@dataclass
class DeviceGroup:
    """소자 하나.

    커브 종류(transfer/output)마다 **후보 파일**이 여럿일 수 있다 — 같은 종류의
    파일이 두 개 이상 오면 첫 번째가 활성 파일이 되고 나머지는 후보로 남는다.
    ``*_sources`` 는 파일명 -> 그 파일의 측정 런 목록(재측정이면 여러 개)이고,
    ``*_file`` 이 그중 활성 파일명이다. ``transfer``/``output`` 프로퍼티는 활성
    파일의 런들에서 ``*_run_idx`` 로 하나를 골라 낸다.
    """

    name: str
    transfer_sources: dict[str, list[MeasurementRun]] = field(default_factory=dict)
    output_sources: dict[str, list[MeasurementRun]] = field(default_factory=dict)
    transfer_run_idx: int = 0
    output_run_idx: int = 0
    transfer_file: str | None = None
    output_file: str | None = None
    params: DeviceParams = field(default_factory=DeviceParams)
    warnings: list[str] = field(default_factory=list)

    @staticmethod
    def _pick(runs: list[MeasurementRun], idx: int, attr: str):
        if not runs:
            return None
        i = idx if 0 <= idx < len(runs) else 0
        return getattr(runs[i], attr)

    @property
    def transfer_runs(self) -> list[MeasurementRun]:
        """활성 transfer 파일의 측정 런들."""
        if self.transfer_file is None:
            return []
        return self.transfer_sources.get(self.transfer_file, [])

    @property
    def output_runs(self) -> list[MeasurementRun]:
        """활성 output 파일의 측정 런들."""
        if self.output_file is None:
            return []
        return self.output_sources.get(self.output_file, [])

    @property
    def transfer(self) -> TransferCurve | None:
        return self._pick(self.transfer_runs, self.transfer_run_idx, "transfer")

    @property
    def output(self) -> OutputCurve | None:
        return self._pick(self.output_runs, self.output_run_idx, "output")

    @property
    def extra_files(self) -> list[str]:
        """활성 파일이 아닌 후보 파일 이름들 — 소자 패널에서 교체 대상."""
        active = {self.transfer_file, self.output_file}
        seen: list[str] = []
        for sources in (self.transfer_sources, self.output_sources):
            for name in sources:
                if name not in active and name not in seen:
                    seen.append(name)
        return seen

    def select_transfer_file(self, name: str) -> None:
        """Transfer 활성 파일을 바꾼다. 런 인덱스는 새 파일 기준으로 0(Latest)."""
        if name in self.transfer_sources and name != self.transfer_file:
            self.transfer_file = name
            self.transfer_run_idx = 0

    def select_output_file(self, name: str) -> None:
        """Output 활성 파일을 바꾼다. 런 인덱스는 새 파일 기준으로 0(Latest)."""
        if name in self.output_sources and name != self.output_file:
            self.output_file = name
            self.output_run_idx = 0

    @property
    def badges(self) -> str:
        marks = []
        if self.transfer is not None:
            marks.append("T")
        if self.output is not None:
            marks.append("O")
        return "·".join(marks) if marks else "—"


def group_files(parsed: list[ParsedFile]) -> list[DeviceGroup]:
    """파일명 stem 으로 묶는다.

    한 파일의 여러 측정 런은 모두 보존한다(재측정 파일). 같은 종류의 파일이
    두 개 이상 오면 먼저 들어온 파일이 활성이 되고, 나머지는 후보로 남는다
    (버리지 않는다 — 소자 패널에서 활성 파일을 바꿀 수 있다).
    """
    groups: dict[str, DeviceGroup] = {}
    order: list[str] = []

    for pf in parsed:
        key = stem_of(pf.name)
        if key not in groups:
            groups[key] = DeviceGroup(name=key)
            order.append(key)
        g = groups[key]
        g.warnings.extend(pf.warnings)

        t_runs = [r for r in pf.runs if r.kind == TRANSFER]
        o_runs = [r for r in pf.runs if r.kind == OUTPUT]

        if t_runs:
            is_first = not g.transfer_sources
            g.transfer_sources[pf.name] = t_runs
            if is_first:
                g.transfer_file = pf.name
            else:
                g.warnings.append(
                    f"'{pf.name}' 은 transfer 가 이미 있어 사용하지 않았습니다. "
                    "소자 패널에서 교체할 수 있습니다."
                )
        if o_runs:
            is_first = not g.output_sources
            g.output_sources[pf.name] = o_runs
            if is_first:
                g.output_file = pf.name
            else:
                g.warnings.append(
                    f"'{pf.name}' 은 output 이 이미 있어 사용하지 않았습니다. "
                    "소자 패널에서 교체할 수 있습니다."
                )

    return [groups[k] for k in order]
