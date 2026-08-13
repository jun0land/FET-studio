import numpy as np
import pandas as pd

from fet_app.curves import OutputBlock, OutputCurve
from fet_app.metrics import output_diagnostics


def _block(v_g, i_d, i_g=None, v_d=None):
    v_d = v_d if v_d is not None else np.arange(0, -61, -1, dtype=float)
    i_g = i_g if i_g is not None else np.full_like(v_d, 1e-12)
    return OutputBlock(v_g=v_g,
                       forward=pd.DataFrame({"V_D": v_d, "I_D": i_d, "I_G": i_g}),
                       reverse=None)


def _ideal(v_d, i_sat=-1e-5, v_knee=-20.0):
    """원점에서 출발해 knee 이후 포화하는 이상적 출력 곡선."""
    return i_sat * np.tanh(v_d / v_knee)


def test_ideal_curve_passes_all_checks():
    v_d = np.arange(0, -61, -1, dtype=float)
    curve = OutputCurve(blocks=[_block(-60.0, _ideal(v_d))])
    d = output_diagnostics(curve)
    b = d.blocks[0]
    assert b.zero_offset < 0.01
    assert b.linearity_r2 > 0.99
    assert b.saturation_ratio < 0.1
    assert b.gate_leak < 0.01
    assert b.flags == []
    assert d.flags == []


def test_zero_offset_detected():
    v_d = np.arange(0, -61, -1, dtype=float)
    i_d = _ideal(v_d) - 1e-6      # 전 구간을 들어올려 0 V 에서 안 떨어지게
    curve = OutputCurve(blocks=[_block(-60.0, i_d)])
    d = output_diagnostics(curve)
    assert d.blocks[0].zero_offset > 0.01
    assert any("0 V" in f for f in d.blocks[0].flags)


def test_nonlinear_origin_detected():
    """S 자 개형(컨택트 저항) 은 원점 선형성 R^2 를 떨어뜨린다."""
    v_d = np.arange(0, -61, -1, dtype=float)
    i_d = -1e-5 * (np.abs(v_d) / 60.0) ** 3
    curve = OutputCurve(blocks=[_block(-60.0, i_d)])
    d = output_diagnostics(curve)
    assert d.blocks[0].linearity_r2 < 0.99
    assert any("선형" in f for f in d.blocks[0].flags)


def test_unsaturated_detected():
    v_d = np.arange(0, -61, -1, dtype=float)
    i_d = -1e-7 * np.abs(v_d)     # 끝까지 직선 = 미포화
    curve = OutputCurve(blocks=[_block(-60.0, i_d)])
    d = output_diagnostics(curve)
    assert d.blocks[0].saturation_ratio > 0.1
    assert any("포화" in f for f in d.blocks[0].flags)


def test_gate_leak_detected():
    v_d = np.arange(0, -61, -1, dtype=float)
    i_d = _ideal(v_d)
    i_g = np.full_like(v_d, -1e-6)   # |I_D| 최대 1e-5 대비 10 %
    curve = OutputCurve(blocks=[_block(-60.0, i_d, i_g=i_g)])
    d = output_diagnostics(curve)
    assert d.blocks[0].gate_leak > 0.01
    assert any("누설" in f for f in d.blocks[0].flags)


def test_worst_aggregates_across_blocks():
    v_d = np.arange(0, -61, -1, dtype=float)
    good = _block(0.0, _ideal(v_d, i_sat=-1e-9))
    bad = _block(-60.0, _ideal(v_d) - 1e-6)
    d = output_diagnostics(OutputCurve(blocks=[good, bad]))
    assert d.worst["zero_offset"] == max(b.zero_offset for b in d.blocks)
    assert d.worst["linearity_r2"] == min(b.linearity_r2 for b in d.blocks)
    assert d.flags


def test_custom_thresholds_are_used():
    v_d = np.arange(0, -61, -1, dtype=float)
    curve = OutputCurve(blocks=[_block(-60.0, _ideal(v_d))])
    d = output_diagnostics(curve, thresholds={"zero_offset": 0.0,
                                              "linearity_r2": 1.1,
                                              "saturation": 0.0,
                                              "gate_leak": 0.0})
    assert len(d.blocks[0].flags) == 4


def test_real_example_runs(example_dir):
    from fet_app.grouping import parse_file
    pf = parse_file((example_dir / "1-1 out.xls").read_bytes(), "1-1 out.xls")
    d = output_diagnostics(pf.latest.output)
    assert len(d.blocks) == 4
    for b in d.blocks:
        assert b.zero_offset is not None
        assert b.gate_leak is not None
