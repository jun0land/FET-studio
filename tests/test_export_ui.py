"""소자별 개별 다운로드 (스펙 §7 / MANUAL.md §5, export_ui.py).

이 저장소에는 Streamlit AppTest 인프라가 없다(tests/test_ui_helpers.py 처럼
순수 헬퍼 함수와 소스 텍스트 확인으로 UI 로직을 검증하는 관례를 따른다).
export_ui.render() 자체는 st.button/session_state 상호작용이라 단위 테스트로
직접 구동하기 어려우므로, 실제 판단 로직을 순수 함수로 뽑아 테스트한다.
"""

from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from fet_app import export
from fet_app.constants import DEFAULTS
from fet_app.curves import OutputBlock, OutputCurve, TransferCurve
from fet_app.figure_common import new_figure
from fet_app.grouping import DeviceGroup, MeasurementRun
from fet_app.params import DeviceParams
from fet_app.ui import export_ui

PARAMS = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)


def _transfer():
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = -np.maximum(2e-8 * (v_g + 12.0) ** 2 * (v_g < -12.0), 1e-12)
    df = pd.DataFrame({"V_G": v_g, "I_G": np.full_like(v_g, 1e-11), "I_D": i_d})
    return TransferCurve(forward=df, reverse=df.iloc[::-1].reset_index(drop=True),
                         v_ds=-60.0, dual=True)


def _output():
    v_d = np.arange(0, -61, -1, dtype=float)
    block = OutputBlock(v_g=-20.0, forward=pd.DataFrame({
        "V_D": v_d, "I_D": -1e-6 * np.tanh(v_d / -20), "I_G": np.full_like(v_d, 1e-12),
    }), reverse=None)
    return OutputCurve(blocks=[block])


def _group(name="1-1", with_transfer=True, with_output=True):
    transfer_runs, output_runs = [], []
    if with_transfer:
        transfer_runs = [MeasurementRun(sheet="Data", label="Data", is_latest=True,
                                        kind="transfer", reason="settings",
                                        transfer=_transfer())]
    if with_output:
        output_runs = [MeasurementRun(sheet="Data", label="Data", is_latest=True,
                                      kind="output", reason="settings",
                                      output=_output())]
    return DeviceGroup(name=name, transfer_runs=transfer_runs, output_runs=output_runs,
                       transfer_file=f"{name}.xls" if with_transfer else None,
                       output_file=f"{name} out.xls" if with_output else None,
                       params=PARAMS)


# ---------------- _available_kinds: 커브 종류별 버튼 가드 ----------------

def test_available_kinds_both_present():
    assert export_ui._available_kinds(_group()) == ["transfer", "output"]


def test_available_kinds_transfer_only_device_has_no_output_button():
    """MAIN FIX 요구사항: 소자가 가진 커브에만 버튼을 보여준다."""
    g = _group(with_output=False)
    assert export_ui._available_kinds(g) == ["transfer"]


def test_available_kinds_output_only_device_has_no_transfer_button():
    g = _group(with_transfer=False)
    assert export_ui._available_kinds(g) == ["output"]


def test_available_kinds_empty_device_gets_no_buttons():
    assert export_ui._available_kinds(DeviceGroup(name="empty")) == []


def test_available_kinds_excludes_interrupted_measurement_with_empty_frame():
    """측정이 중단된 파일은 빈 DataFrame 을 만든다 — transfer_runs 가 있어도
    forward 가 비어 있으면 그리다가 터지므로 버튼을 보이면 안 된다
    (summary._has_transfer_data 와 같은 규칙을 재사용해야 하는 이유)."""
    empty = TransferCurve(forward=pd.DataFrame({"V_G": [], "I_G": [], "I_D": []}))
    g = DeviceGroup(name="x", transfer_file="x.xls",
                    transfer_runs=[MeasurementRun(sheet="Data", label="Data", is_latest=True,
                                                  kind="transfer", reason="settings",
                                                  transfer=empty)])
    assert export_ui._available_kinds(g) == []


def test_export_ui_reuses_summary_curve_presence_helpers():
    """중복 판정 로직을 새로 만들지 않고 summary._has_transfer_data /
    _has_output_data 를 그대로 쓴다는 요구사항을 소스 레벨로도 못박는다."""
    src = inspect.getsource(export_ui)
    assert "_has_transfer_data" in src
    assert "_has_output_data" in src
    assert "from fet_app.ui.summary import" in src


# ---------------- 파일명 규약 ----------------

def test_device_filename_matches_naming_convention():
    assert export_ui._device_filename("1-3", "transfer", "png") == "1-3_transfer.png"
    assert export_ui._device_filename("1-3", "output", "html") == "1-3_output.html"


# ---------------- KaleidoUnavailable -> HTML 폴백 (ZIP 경로와 동일 정책) ----------------

def test_render_or_fallback_returns_html_on_kaleido_unavailable(monkeypatch):
    def _boom(*_a, **_k):
        raise export.KaleidoUnavailable("no chromium")
    monkeypatch.setattr(export, "figure_bytes", _boom)

    fig = new_figure(DEFAULTS["geom"], k=0.2)
    data, ext, ok = export_ui._render_or_fallback(fig, "png", 1)
    assert ok is False
    assert ext == "html"
    assert b"plotly" in data.lower()


def test_render_or_fallback_returns_native_bytes_when_kaleido_available():
    fig = new_figure(DEFAULTS["geom"], k=0.2)
    try:
        data, ext, ok = export_ui._render_or_fallback(fig, "png", 1)
    except export.KaleidoUnavailable:
        pytest.skip("kaleido 미설치")
    assert ok is True
    assert ext == "png"
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
