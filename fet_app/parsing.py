"""Keithley KTEI .xls 로더와 Settings 표 파싱.

구형 OLE2 .xls 는 엔진마다 읽히는 정도가 달라 다단 폴백을 쓴다.
xlrd 는 무해한 OLE2 경고를 stdout 으로 뱉으므로 반드시 삼킨다 (스펙 §1.3).
"""

from __future__ import annotations

import contextlib
import io
import re
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from fet_app.constants import SEP_TOKEN

# Settings 의 블록 구분선. 파일마다 '=' 개수가 조금씩 달라 앞 몇 글자만 본다.
_SEP_PREFIX = SEP_TOKEN[:5]


@contextlib.contextmanager
def _quiet():
    """xlrd 의 OLE2 경고를 사용자에게 노출하지 않는다."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


def _read_excel(file_bytes: bytes, engine: str | None = None, **kwargs):
    if engine:
        kwargs["engine"] = engine
    with _quiet():
        return pd.read_excel(io.BytesIO(file_bytes), **kwargs)


def _looks_like_data(df) -> bool:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return False
    cols = {str(c).strip() for c in df.columns}
    return any(re.match(r"^(Gate|Drain|Source)[IV](\(\d+\))?$", c) for c in cols)


def load_sheets(file_bytes: bytes) -> tuple[dict[str, pd.DataFrame], str | None]:
    """기본 -> xlrd -> openpyxl -> read_html -> TSV 순으로 시도.

    반환: (시트이름 -> DataFrame, 성공한 engine). engine 은 Settings 재읽기에 쓴다.
    """
    errors: list[str] = []
    for engine in (None, "xlrd", "openpyxl"):
        try:
            sheets = _read_excel(file_bytes, engine, sheet_name=None)
            if isinstance(sheets, dict) and sheets:
                return sheets, engine
        except Exception as e:  # noqa: BLE001
            errors.append(f"read_excel(engine={engine}): {e}")

    try:
        with _quiet():
            tables = pd.read_html(io.BytesIO(file_bytes))
        out: dict[str, pd.DataFrame] = {}
        for i, t in enumerate(tables):
            if _looks_like_data(t):
                out["Data" if not out else f"Append{i}"] = t
        if out:
            return out, None
        errors.append("read_html: 데이터 표를 찾지 못함")
    except Exception as e:  # noqa: BLE001
        errors.append(f"read_html: {e}")

    try:
        with _quiet():
            df = pd.read_csv(io.BytesIO(file_bytes), sep="\t")
        if _looks_like_data(df):
            return {"Data": df}, None
        errors.append("read_csv(tab): 데이터 컬럼 없음")
    except Exception as e:  # noqa: BLE001
        errors.append(f"read_csv(tab): {e}")

    raise ValueError("파일을 읽을 수 없습니다.\n" + "\n".join(errors))


def settings_frame(file_bytes: bytes, sheets: dict, engine: str | None) -> pd.DataFrame | None:
    """Settings 는 첫 행이 구분선이라 header=0 이면 소실된다 -> header=None 으로 다시 읽는다."""
    key = next((k for k in sheets if str(k).strip().lower() == "settings"), None)
    if key is None:
        return None
    try:
        return _read_excel(file_bytes, engine, sheet_name=key, header=None)
    except Exception:  # noqa: BLE001
        return sheets[key]


def _cell(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


@dataclass
class SettingsInfo:
    """Settings 시트를 '행 라벨 -> 단자별 값' 으로 정규화한 것.

    예: rows["Forcing Function"] == ["Common", "Voltage Sweep", "Voltage Bias"]
        terminals                 == ["Source", "Gate", "Drain"]
    """

    test_name: str = ""
    terminals: list[str] = field(default_factory=list)
    rows: dict[str, list[str]] = field(default_factory=dict)
    raw: list[list[str]] = field(default_factory=list)

    def get(self, row_label: str, terminal: str) -> str:
        values = self.rows.get(row_label)
        if not values or terminal not in self.terminals:
            return ""
        i = self.terminals.index(terminal)
        return values[i] if i < len(values) else ""

    def dual_sweep(self, terminal: str) -> bool:
        return self.get("Dual Sweep Mode", terminal).lower() == "enabled"

    def n_points(self, terminal: str) -> int | None:
        raw = self.get("Number of Points", terminal)
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return None

    def bias_level(self, terminal: str) -> float | None:
        raw = self.get("Start/Level", terminal)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None


_BLOCK_HEADER_RE = re.compile(r"^append\s*(\d+)$", flags=re.IGNORECASE)
_INITIAL_RE = re.compile(r"^initial\s*run$", flags=re.IGNORECASE)
_SHEET_APPEND_RE = re.compile(r"^append\s*(\d+)$", flags=re.IGNORECASE)


def _normalize_block_name(label: str) -> str | None:
    """Settings 블록 헤더 -> 대응하는 데이터 시트 이름. 헤더가 아니면 None."""
    text = str(label).strip()
    if _INITIAL_RE.match(text):
        return "Data"
    m = _BLOCK_HEADER_RE.match(text)
    if m:
        return f"Append{int(m.group(1))}"
    return None


@dataclass
class RunSettings:
    """측정 런별 SettingsInfo. 키는 대응하는 데이터 시트 이름이다."""

    blocks: dict[str, SettingsInfo] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    latest: str | None = None

    def block(self, name: str) -> SettingsInfo:
        return self.blocks.get(name, SettingsInfo())

    def __len__(self) -> int:
        return len(self.order)


def data_sheet_names(sheets: dict) -> list[str]:
    """데이터 시트를 Data 먼저, 그 다음 AppendN 오름차순으로."""
    def _key(name: str):
        text = str(name).strip()
        if text.lower() == "data":
            return (0, 0)
        m = _SHEET_APPEND_RE.match(text)
        return (1, int(m.group(1))) if m else (2, 0)

    names = [n for n, d in sheets.items()
             if str(n).strip().lower() == "data" or _SHEET_APPEND_RE.match(str(n).strip())]
    names = [n for n in names if _looks_like_data(sheets[n])]
    return sorted((str(n).strip() for n in names), key=_key)


def parse_settings(df: pd.DataFrame | None) -> RunSettings:
    """Settings 시트를 런 블록별 SettingsInfo 로 나눈다.

    구분선(=====) 다음 행의 첫 칸이 블록 헤더다. 'Initial Run' -> Data,
    'Append N' -> AppendN. 헤더가 없는 파일은 전체를 Data 블록으로 담는다.
    """
    runs = RunSettings()
    if not isinstance(df, pd.DataFrame) or df.empty:
        return runs

    rows: list[list[str]] = []
    cols = list(df.columns)
    if not all(isinstance(c, (int, np.integer)) or str(c).startswith("Unnamed") for c in cols):
        rows.append([_cell(c) for c in cols])
    for i in range(len(df)):
        rows.append([_cell(df.iloc[i, j]) for j in range(df.shape[1])])

    def _ensure(name: str) -> SettingsInfo:
        if name not in runs.blocks:
            runs.blocks[name] = SettingsInfo()
            runs.order.append(name)
        return runs.blocks[name]

    current: SettingsInfo | None = None
    for cells in rows:
        if not cells:
            continue
        joined = " ".join(cells)
        if _SEP_PREFIX in joined:
            continue
        label = cells[0]
        if not label:
            continue

        block_name = _normalize_block_name(label)
        if block_name is not None:
            current = _ensure(block_name)
            current.raw.append(list(cells))
            if any(c.strip().lower() == "latest run" for c in cells[1:]):
                runs.latest = block_name
            continue

        if current is None:                     # 헤더 없는 단일 블록 파일
            current = _ensure("Data")
        current.raw.append(list(cells))

        values = list(cells[1:])
        while values and not values[-1]:
            values.pop()

        if label.lower() == "test name":
            current.test_name = values[0] if values else ""
            continue
        if label.lower() == "device terminal":
            current.terminals = values
            continue
        current.rows.setdefault(label, values)

    if runs.latest is None and runs.order:
        runs.latest = runs.order[0]
    return runs


# ---------------- 커브 종류 판정 (스펙 §2) ----------------

TRANSFER = "transfer"
OUTPUT = "output"

_BLOCK_RE = re.compile(r"^(GateI|GateV|DrainI|DrainV)\((\d+)\)$")


def data_sheet(sheets: dict, name: str | None = None) -> pd.DataFrame:
    """데이터 시트 하나를 컬럼명 strip 해 반환한다.

    name 을 주면 그 시트, 없으면 data_sheet_names 의 첫 번째(= Data).
    재측정 파일(Data + Append1)에서 특정 런을 꺼낼 때 name 을 쓴다.
    """
    if name is None:
        ordered = data_sheet_names(sheets)
        if not ordered:
            raise ValueError("데이터 시트를 찾지 못했습니다.")
        name = ordered[0]

    key = next((k for k in sheets if str(k).strip() == str(name).strip()), None)
    if key is None:
        raise ValueError(f"데이터 시트 '{name}' 를 찾지 못했습니다.")
    df = sheets[key].copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def output_block_count(data: pd.DataFrame) -> int:
    """GateI(n)/GateV(n)/DrainI(n)/DrainV(n) 블록 개수. 하드코딩 금지 (스펙 §1.2)."""
    indices = set()
    for c in data.columns:
        m = _BLOCK_RE.match(str(c).strip())
        if m:
            indices.add(int(m.group(2)))
    return len(indices)


def _has_constant_gate_blocks(data: pd.DataFrame) -> bool:
    """output 은 블록마다 GateV(n) 이 상수다. 하나라도 변하면 output 이 아니다."""
    n = output_block_count(data)
    if n < 1:
        return False
    for i in range(1, n + 1):
        col = f"GateV({i})"
        if col not in data.columns:
            return False
        vals = pd.to_numeric(data[col], errors="coerce").dropna()
        if vals.empty or vals.nunique() != 1:
            return False
    return True


def classify_curve(data: pd.DataFrame, info: SettingsInfo,
                   file_name: str) -> tuple[str, str]:
    """(kind, reason) 반환. reason 은 판정 근거 단계: forcing / structure / name.

    1순위 Settings 의 Forcing Function, 2순위 Data 열 구조, 3순위 이름.
    파일 이름 규칙을 요구하지 않기 위한 3단 폴백이다.
    """
    gate = info.get("Forcing Function", "Gate").lower()
    drain = info.get("Forcing Function", "Drain").lower()
    if "sweep" in gate and "bias" in drain:
        return TRANSFER, "forcing"
    if "step" in gate and "sweep" in drain:
        return OUTPUT, "forcing"

    cols = {str(c).strip() for c in data.columns}
    if _has_constant_gate_blocks(data):
        return OUTPUT, "structure"
    if "GateV" in cols and not any(c.startswith("DrainV") for c in cols):
        return TRANSFER, "structure"

    # 영숫자가 아닌 모든 문자로 자른다. Test Name 이 'p_output#1@3' 처럼
    # 기호를 섞어 쓰므로 공백/밑줄만으로 자르면 'output' 이 안 잡힌다.
    # 부분문자열이 아닌 토큰으로 봐야 'routine' 의 'out' 을 오인하지 않는다.
    tokens = set(re.split(r"[^a-z0-9]+", f"{info.test_name} {file_name}".lower()))
    if tokens & {"out", "output"}:
        return OUTPUT, "name"
    return TRANSFER, "name"
