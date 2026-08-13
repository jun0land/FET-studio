"""측정 커브 데이터 모델과 dual sweep 분리 (스펙 §1, §4)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from fet_app.parsing import SettingsInfo, output_block_indices


def _turning_index(v: np.ndarray) -> int | None:
    """전압 스윕 방향이 뒤집히는 지점. 같은 값이 연속돼도 견디게 부호만 본다."""
    if v.size < 4:
        return None
    d = np.diff(v)
    nz = d[d != 0]
    if nz.size == 0:
        return None
    first_sign = np.sign(nz[0])
    for i in range(1, d.size):
        if d[i] != 0 and np.sign(d[i]) != first_sign:
            return i
    return None


def split_dual(df: pd.DataFrame, n_points: int | None,
               dual: bool) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """dual sweep 데이터를 forward/reverse 로 자른다.

    1순위: Settings 의 Number of Points 절반 (전압이 turning point 에서 두 번
    나오는 경우가 있어 부호 변화만으로는 실패한다 — 스펙 §1.3).
    2순위: 전압 방향 부호가 뒤집히는 지점.
    """
    if not dual or df.empty:
        return df.reset_index(drop=True), None

    half = None
    if n_points and n_points > 1 and abs(n_points - len(df)) <= 1:
        half = n_points // 2
    if half is None:
        v = pd.to_numeric(df.iloc[:, 0], errors="coerce").to_numpy()
        t = _turning_index(v)
        half = t if t else len(df) // 2
    half = max(1, min(half, len(df) - 1))

    fwd = df.iloc[:half].reset_index(drop=True)
    rev = df.iloc[half:].reset_index(drop=True)
    return fwd, (rev if not rev.empty else None)


@dataclass
class TransferCurve:
    """V_DS 고정, V_G 스윕. forward/reverse 컬럼은 V_G / I_G / I_D."""

    forward: pd.DataFrame
    reverse: pd.DataFrame | None = None
    v_ds: float | None = None
    dual: bool = False

    def branches(self) -> list[tuple[str, pd.DataFrame]]:
        out = [("forward", self.forward)]
        if self.reverse is not None:
            out.append(("reverse", self.reverse))
        return out


@dataclass
class OutputBlock:
    """V_G 한 스텝. forward/reverse 컬럼은 V_D / I_D / I_G."""

    v_g: float
    forward: pd.DataFrame
    reverse: pd.DataFrame | None = None


@dataclass
class OutputCurve:
    blocks: list[OutputBlock] = field(default_factory=list)

    @property
    def gate_voltages(self) -> list[float]:
        return [b.v_g for b in self.blocks]


def _require_columns(data: pd.DataFrame, needed: list[str], what: str) -> None:
    """없는 열을 pandas 가 스칼라 nan 으로 broadcast 하기 전에 잡는다.

    그냥 두면 'If using all scalar values, you must pass an index' 라는
    쓸모없는 메시지가 사용자에게 그대로 노출되고, 열이 하나만 빠졌을 때는
    조용히 빈 프레임이 만들어져 그래프 단계에서 뒤늦게 터진다.
    """
    missing = [c for c in needed if c not in data.columns]
    if missing:
        raise ValueError(
            f"{what} 에 필요한 열이 없습니다: {', '.join(missing)}. "
            "측정이 중단된 파일이거나 형식이 다를 수 있습니다."
        )


def build_transfer(data: pd.DataFrame, info: SettingsInfo) -> TransferCurve:
    _require_columns(data, ["GateV", "GateI", "DrainI"], "transfer curve")
    frame = pd.DataFrame({
        "V_G": pd.to_numeric(data["GateV"], errors="coerce"),
        "I_G": pd.to_numeric(data["GateI"], errors="coerce"),
        "I_D": pd.to_numeric(data["DrainI"], errors="coerce"),
    }).dropna().reset_index(drop=True)

    if frame.empty:
        raise ValueError(
            "transfer curve 에 쓸 수 있는 숫자 데이터가 없습니다. "
            "측정이 중단된 파일일 수 있습니다."
        )

    dual = info.dual_sweep("Gate")
    fwd, rev = split_dual(frame, info.n_points("Gate"), dual)
    return TransferCurve(forward=fwd, reverse=rev,
                         v_ds=info.bias_level("Drain"), dual=dual)


def build_output(data: pd.DataFrame, info: SettingsInfo) -> OutputCurve:
    dual = info.dual_sweep("Drain")
    n_points = info.n_points("Drain")

    # 실제로 있는 블록 번호만 돈다. 1..n 로 이어진다고 가정하면 1,2,4 처럼
    # 비어 있는 파일에서 없는 열을 읽는다.
    indices = output_block_indices(data)

    blocks: list[OutputBlock] = []
    for i in indices:
        _require_columns(
            data, [f"DrainV({i})", f"DrainI({i})", f"GateI({i})", f"GateV({i})"],
            f"output curve 블록 {i}",
        )
        frame = pd.DataFrame({
            "V_D": pd.to_numeric(data[f"DrainV({i})"], errors="coerce"),
            "I_D": pd.to_numeric(data[f"DrainI({i})"], errors="coerce"),
            "I_G": pd.to_numeric(data[f"GateI({i})"], errors="coerce"),
        }).dropna().reset_index(drop=True)
        if frame.empty:
            continue

        v_g_col = pd.to_numeric(data[f"GateV({i})"], errors="coerce").dropna()
        v_g = float(v_g_col.iloc[0]) if not v_g_col.empty else float("nan")

        fwd, rev = split_dual(frame, n_points, dual)
        blocks.append(OutputBlock(v_g=v_g, forward=fwd, reverse=rev))

    return OutputCurve(blocks=blocks)
