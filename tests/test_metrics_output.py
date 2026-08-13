import numpy as np
import pandas as pd
import pytest

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
    assert b.is_on
    assert b.zero_offset < 0.01
    assert b.linearity_r2 > 0.99
    assert b.saturation_ratio < 0.1
    assert b.gate_leak < 0.01
    assert b.flags == []
    assert d.flags == []


def test_off_block_does_not_raise_false_alarms():
    """V_G=0 처럼 꺼진 블록은 전류가 노이즈다. 자기 블록 최댓값으로 나누면
    비율이 폭주해 멀쩡한 소자가 불량으로 찍힌다 (스펙 §3.7)."""
    v_d = np.arange(0, -61, -1, dtype=float)
    on = _block(-60.0, _ideal(v_d, i_sat=-1e-4))
    # 꺼진 블록: 구동전류의 1/100000 수준, 원점에서도 노이즈가 남아 있다
    noise = np.full_like(v_d, -6e-10) + np.linspace(0, -1e-10, v_d.size)
    off = _block(0.0, noise, i_g=np.full_like(v_d, -7e-10))
    d = output_diagnostics(OutputCurve(blocks=[off, on]))

    off_d, on_d = d.blocks[0], d.blocks[1]
    assert not off_d.is_on and on_d.is_on
    # 모양 판정은 생략된다
    assert off_d.linearity_r2 is None
    assert off_d.saturation_ratio is None
    # 오프셋·누설은 계산하되 소자 구동전류로 나눠 미미하게 나온다
    assert off_d.zero_offset < 0.01
    assert off_d.gate_leak < 0.01
    assert off_d.flags == []
    assert d.flags == []
    # tanh(-60/-20) = 0.995 이므로 곡선이 i_sat 에 완전히 도달하지는 않는다.
    # 여기서 볼 것은 "I_drive 가 켜진 블록에서 온다"는 것이지 소수점 정밀도가 아니다.
    assert d.i_drive == pytest.approx(1e-4, rel=1e-2)


def test_off_block_still_reports_real_gate_leak():
    """꺼진 블록이라도 누설이 진짜 크면 놓치지 않는다."""
    v_d = np.arange(0, -61, -1, dtype=float)
    on = _block(-60.0, _ideal(v_d, i_sat=-1e-5))
    off = _block(0.0, np.full_like(v_d, -1e-10),
                 i_g=np.full_like(v_d, -5e-7))   # 구동전류의 5 %
    d = output_diagnostics(OutputCurve(blocks=[off, on]))
    assert not d.blocks[0].is_on
    # 분모가 I_drive(1e-5 x tanh(3)) 이라 5e-7/1e-5 = 5 % 에서 0.5 % 만큼 어긋난다.
    # 블록 자기 최댓값(1e-10)으로 나눴다면 5000배 어긋났을 것이다 — 그걸 가르는 검사다.
    assert d.blocks[0].gate_leak == pytest.approx(0.05, rel=1e-2)
    assert any("누설" in f for f in d.blocks[0].flags)


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
    """집계는 나쁜 쪽을 취한다: 비율은 max, R^2 는 min. None 은 건너뛴다."""
    v_d = np.arange(0, -61, -1, dtype=float)
    clean = _block(-40.0, _ideal(v_d, i_sat=-5e-5))
    offset = _block(-60.0, _ideal(v_d, i_sat=-1e-4) - 5e-6)
    d = output_diagnostics(OutputCurve(blocks=[clean, offset]))
    zeros = [b.zero_offset for b in d.blocks if b.zero_offset is not None]
    lins = [b.linearity_r2 for b in d.blocks if b.linearity_r2 is not None]
    assert d.worst["zero_offset"] == max(zeros)
    assert d.worst["linearity_r2"] == min(lins)
    assert d.flags


def test_worst_is_none_when_every_block_is_none():
    """모두 꺼진 블록이면 모양 지표 집계는 None 이어야 한다 (0.0 아님)."""
    v_d = np.arange(0, -61, -1, dtype=float)
    a = _block(0.0, np.full_like(v_d, -1e-12))
    d = output_diagnostics(OutputCurve(blocks=[a]))
    # 단일 블록이면 그 블록이 곧 I_drive 이므로 is_on 이다 — 모양 지표가 나온다
    assert d.blocks[0].is_on
    assert d.worst["linearity_r2"] is not None


def test_custom_thresholds_override_defaults_key_by_key():
    """일부 키만 넘기면 나머지는 기본값을 유지한다."""
    v_d = np.arange(0, -61, -1, dtype=float)
    curve = OutputCurve(blocks=[_block(-60.0, _ideal(v_d))])
    # 기본값으로는 무경고
    assert output_diagnostics(curve).blocks[0].flags == []
    # 선형성 하한만 불가능한 값으로 올리면 그 항목만 걸린다
    d = output_diagnostics(curve, thresholds={"linearity_r2": 1.1})
    flags = d.blocks[0].flags
    assert len(flags) == 1
    assert "선형" in flags[0]


def test_all_thresholds_can_fire_together():
    v_d = np.arange(0, -61, -1, dtype=float)
    i_d = _ideal(v_d) - 1e-6                  # 원점에서 안 떨어짐
    curve = OutputCurve(blocks=[_block(-60.0, i_d, i_g=np.full_like(v_d, -1e-7))])
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
    assert d.i_drive is not None and d.i_drive > 0
    for b in d.blocks:
        assert b.zero_offset is not None
        assert b.gate_leak is not None


def test_real_example_off_block_is_not_flagged(example_dir):
    """1-1 out.xls 의 V_G=0 블록은 꺼져 있다. 예전 정규화로는 0V 오프셋 57 %,
    누설 100 % 가 나와 멀쩡한 소자가 불량으로 찍혔다."""
    from fet_app.grouping import parse_file
    pf = parse_file((example_dir / "1-1 out.xls").read_bytes(), "1-1 out.xls")
    d = output_diagnostics(pf.latest.output)
    off = next(b for b in d.blocks if b.v_g == 0.0)
    assert not off.is_on
    assert off.zero_offset < 0.01
    assert off.gate_leak < 0.01
    assert off.linearity_r2 is None and off.saturation_ratio is None
    assert off.flags == []
