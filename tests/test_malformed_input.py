"""중단된/깨진 측정 파일이 앱을 죽이지 않는지 (최종 리뷰 C1, I1).

`GateV`/`GateI` 는 있고 `DrainI` 가 없는 파일은 _looks_like_data 를 통과하고
열 구조로 transfer 로 분류된다. 예전에는 경고 없이 소자 목록에 뜬 뒤,
선택하는 순간 축 계산이 zero-size 배열에서 터져 페이지 전체가 트레이스백이 됐다.
"""

from __future__ import annotations

import copy
import io

import numpy as np
import pandas as pd
import pytest

from fet_app.constants import DEFAULTS
from fet_app.curves import OutputBlock, OutputCurve, TransferCurve, build_output, build_transfer
from fet_app.figure_transfer import transfer_figure
from fet_app.metrics import TransferMetrics
from fet_app.parsing import SettingsInfo, output_block_indices
from fet_app.state import AppState, add_files
from fet_app.ui.summary import _has_output_data, _has_transfer_data


def _xlsx(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return buf.getvalue()


def _aborted_transfer_bytes() -> bytes:
    """게이트는 쓸었지만 드레인 전류를 못 받은 파일."""
    v = np.arange(20, -61, -1, dtype=float)
    return _xlsx({
        "Data": pd.DataFrame({"GateV": v, "GateI": np.full_like(v, 1e-12)}),
        "Settings": pd.DataFrame({0: ["Test Name"], 1: ["p_transfer#1@3"]}),
    })


def test_build_transfer_names_the_missing_column():
    data = pd.DataFrame({"GateV": [1.0, 2.0], "GateI": [1e-12, 1e-12]})
    with pytest.raises(ValueError) as e:
        build_transfer(data, SettingsInfo())
    assert "DrainI" in str(e.value)
    assert "scalar" not in str(e.value)


def test_build_transfer_rejects_all_non_numeric():
    data = pd.DataFrame({"GateV": ["a", "b"], "GateI": ["a", "b"], "DrainI": ["a", "b"]})
    with pytest.raises(ValueError):
        build_transfer(data, SettingsInfo())


def test_build_output_names_the_missing_column():
    data = pd.DataFrame({"GateV(1)": [0.0], "GateI(1)": [1e-12], "DrainV(1)": [0.0]})
    with pytest.raises(ValueError) as e:
        build_output(data, SettingsInfo())
    assert "DrainI(1)" in str(e.value)


def test_output_block_indices_tolerates_gaps():
    """블록 번호가 1,2,4 로 비어 있어도 없는 열을 읽지 않는다."""
    cols = {}
    for i in (1, 2, 4):
        cols[f"GateV({i})"] = [float(-20 * i)]
        cols[f"GateI({i})"] = [1e-12]
        cols[f"DrainV({i})"] = [0.0]
        cols[f"DrainI({i})"] = [-1e-9]
    data = pd.DataFrame(cols)
    assert output_block_indices(data) == [1, 2, 4]
    curve = build_output(data, SettingsInfo())
    assert [b.v_g for b in curve.blocks] == [-20.0, -40.0, -80.0]


def test_add_files_warns_instead_of_crashing():
    app = AppState()
    warns = add_files(app, [("중단된측정.xlsx", _aborted_transfer_bytes())])
    assert warns, "경고 없이 조용히 통과하면 안 된다"
    assert "중단된측정.xlsx" in warns[0]
    assert "DrainI" in warns[0]
    assert app.devices == []
    assert app.selected is None


def test_empty_curve_still_produces_a_figure():
    """방어가 없으면 np.min 이 zero-size 배열에서 터진다."""
    empty = TransferCurve(forward=pd.DataFrame(columns=["V_G", "I_G", "I_D"]))
    settings = {
        "geom": copy.deepcopy(DEFAULTS["geom"]),
        "style": copy.deepcopy(DEFAULTS["style"]),
        "axes": copy.deepcopy(DEFAULTS["transfer_axes"]),
        "trace": copy.deepcopy(DEFAULTS["transfer_style"]),
        "insets": copy.deepcopy(DEFAULTS["insets"]),
    }
    fig = transfer_figure(empty, TransferMetrics(), settings, k=0.5)
    assert fig.layout.width > 0


def test_curve_presence_helpers_reject_empty():
    empty_df = pd.DataFrame(columns=["V_G", "I_G", "I_D"])
    assert not _has_transfer_data(None)
    assert not _has_transfer_data(TransferCurve(forward=empty_df))
    assert _has_transfer_data(TransferCurve(
        forward=pd.DataFrame({"V_G": [0.0], "I_G": [0.0], "I_D": [-1e-9]})))

    assert not _has_output_data(None)
    assert not _has_output_data(OutputCurve(blocks=[]))
    assert not _has_output_data(OutputCurve(blocks=[
        OutputBlock(v_g=0.0, forward=pd.DataFrame(columns=["V_D", "I_D", "I_G"]))]))
    assert _has_output_data(OutputCurve(blocks=[
        OutputBlock(v_g=0.0,
                    forward=pd.DataFrame({"V_D": [0.0], "I_D": [-1e-9], "I_G": [1e-12]}))]))


def test_real_example_files_unaffected(all_example_files):
    """방어를 넣었다고 정상 파일이 달라지면 안 된다."""
    app = AppState()
    warns = add_files(app, [(p.name, p.read_bytes()) for p in all_example_files])
    assert warns == []
    assert len(app.devices) == 9
    for g in app.devices:
        assert _has_transfer_data(g.transfer), g.name
        assert _has_output_data(g.output), g.name
