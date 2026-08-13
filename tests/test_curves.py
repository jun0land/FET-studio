import numpy as np
import pandas as pd

from fet_app.curves import build_output, build_transfer, split_dual
from fet_app.parsing import (
    SettingsInfo, data_sheet, load_sheets, parse_settings, settings_frame,
)


def _load(path):
    b = path.read_bytes()
    sheets, engine = load_sheets(b)
    runs = parse_settings(settings_frame(b, sheets, engine))
    return data_sheet(sheets), runs.block(runs.latest or "Data")


def test_split_dual_halves():
    df = pd.DataFrame({"V": list(range(10))})
    fwd, rev = split_dual(df, n_points=10, dual=True)
    assert len(fwd) == 5 and len(rev) == 5
    assert list(fwd["V"]) == [0, 1, 2, 3, 4]
    assert list(rev["V"]) == [5, 6, 7, 8, 9]


def test_split_dual_disabled():
    df = pd.DataFrame({"V": list(range(10))})
    fwd, rev = split_dual(df, n_points=10, dual=False)
    assert len(fwd) == 10 and rev is None


def test_split_dual_reindexes_both_branches():
    """인덱스가 0부터 다시 시작하지 않으면 이후 위치 기반 접근이 어긋난다."""
    df = pd.DataFrame({"V": list(range(10))})
    fwd, rev = split_dual(df, n_points=10, dual=True)
    assert list(fwd.index) == list(range(5))
    assert list(rev.index) == list(range(5))


def test_split_dual_falls_back_to_turning_point():
    """n_points 가 없으면 전압 방향이 뒤집히는 지점을 찾는다."""
    v = list(range(0, -6, -1)) + list(range(-5, 1))
    df = pd.DataFrame({"V": v})
    fwd, rev = split_dual(df, n_points=None, dual=True)
    assert len(fwd) == 6 and len(rev) == 6


def test_split_dual_ignores_mismatched_n_points():
    """Settings 의 점 개수가 실제 행 수와 다르면 신뢰하지 않는다."""
    v = list(range(0, -6, -1)) + list(range(-5, 1))
    df = pd.DataFrame({"V": v})
    fwd, rev = split_dual(df, n_points=999, dual=True)
    assert len(fwd) == 6 and len(rev) == 6


def test_split_dual_empty_frame():
    fwd, rev = split_dual(pd.DataFrame({"V": []}), n_points=None, dual=True)
    assert fwd.empty and rev is None


def test_transfer_from_example(transfer_files):
    for p in transfer_files:
        data, info = _load(p)
        c = build_transfer(data, info)
        assert c.v_ds == -60.0, p.name
        assert c.dual is True, p.name
        assert len(c.forward) == 81, p.name
        assert len(c.reverse) == 81, p.name
        assert list(c.forward.columns) == ["V_G", "I_G", "I_D"]
        assert c.forward["V_G"].iloc[0] == 20.0
        assert c.forward["V_G"].iloc[-1] == -60.0
        assert c.reverse["V_G"].iloc[0] == -60.0
        assert c.reverse["V_G"].iloc[-1] == 20.0


def test_transfer_branches_helper(transfer_files):
    data, info = _load(transfer_files[0])
    c = build_transfer(data, info)
    labels = [name for name, _df in c.branches()]
    assert labels == ["forward", "reverse"]


def test_output_from_example(output_files):
    for p in output_files:
        data, info = _load(p)
        c = build_output(data, info)
        assert c.gate_voltages == [0.0, -20.0, -40.0, -60.0], p.name
        for b in c.blocks:
            assert len(b.forward) == 61, p.name
            assert len(b.reverse) == 61, p.name
            assert list(b.forward.columns) == ["V_D", "I_D", "I_G"]
            assert b.forward["V_D"].iloc[0] == 0.0
            assert b.forward["V_D"].iloc[-1] == -60.0


def test_output_blocks_carry_distinct_currents(output_files):
    """블록마다 같은 열을 잘못 읽으면 전부 동일해진다 — 실제로 다른지 본다."""
    data, info = _load(output_files[0])
    c = build_output(data, info)
    peaks = [float(b.forward["I_D"].abs().max()) for b in c.blocks]
    assert len(set(peaks)) == len(peaks)
    assert peaks == sorted(peaks)


def test_transfer_drops_non_numeric_rows():
    data = pd.DataFrame({
        "GateI": [1e-9, np.nan, 3e-9],
        "GateV": [1.0, 2.0, 3.0],
        "DrainI": [1e-6, 2e-6, 3e-6],
    })
    c = build_transfer(data, SettingsInfo())
    assert len(c.forward) == 2
    assert c.v_ds is None
    assert c.dual is False
    assert c.reverse is None


def test_output_skips_empty_blocks():
    data = pd.DataFrame({
        "GateI(1)": [1e-12], "GateV(1)": [0.0],
        "DrainI(1)": [-1e-9], "DrainV(1)": [0.0],
        "GateI(2)": [np.nan], "GateV(2)": [np.nan],
        "DrainI(2)": [np.nan], "DrainV(2)": [np.nan],
    })
    c = build_output(data, SettingsInfo())
    assert len(c.blocks) == 1
    assert c.gate_voltages == [0.0]
