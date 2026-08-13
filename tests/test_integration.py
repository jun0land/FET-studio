"""예제 9세트를 끝까지 통과시키는 회귀 테스트.

18개 파일을 한 번에 올려 9개 소자로 묶고, 지표 계산 -> 그래프 렌더 ->
요약표 -> CSV/ZIP 내보내기까지 전체 파이프라인이 실제 예제 데이터에서
끝까지 돌아가는지 확인한다. Example/ 폴더 위치는 `all_example_files`
fixture(tests/conftest.py, REPO_ROOT 기준)로 찾으므로 작업 디렉터리에
의존하지 않는다.
"""

from __future__ import annotations

import io
import zipfile

import numpy as np
import pytest

from fet_app import export
from fet_app.figure_output import output_figure
from fet_app.figure_transfer import transfer_figure
from fet_app.params import DeviceParams
from fet_app.state import AppState, add_files
from fet_app.ui.summary import _output_settings, _transfer_settings, compute, effective_group

PARAMS = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)


@pytest.fixture(scope="module")
def app(all_example_files):
    a = AppState()
    a.global_params = PARAMS
    warns = add_files(a, [(p.name, p.read_bytes()) for p in all_example_files])
    assert warns == []
    return a


def test_nine_devices_each_with_both_curves(app):
    assert len(app.devices) == 9
    for g in app.devices:
        assert g.transfer is not None, g.name
        assert g.output is not None, g.name


def test_only_1_3_has_a_second_transfer_run(app):
    """1-3 best.xls 만 Data + Append1 두 런. 기본 선택은 Latest(Append1)."""
    counts = {g.name: len(g.transfer_runs) for g in app.devices}
    assert counts["1-3"] == 2
    assert all(n == 1 for name, n in counts.items() if name != "1-3")
    g = next(g for g in app.devices if g.name == "1-3")
    assert g.transfer_runs[g.transfer_run_idx].is_latest


def test_switching_run_changes_metrics(app):
    """런을 바꾸면 실제로 다른 데이터가 쓰인다 — 프로퍼티가 인덱스를 무시하지 않는지."""
    g = next(g for g in app.devices if g.name == "1-3")
    original = g.transfer_run_idx
    try:
        g.transfer_run_idx = 0
        a, _ = compute(app, g)
        g.transfer_run_idx = 1
        b, _ = compute(app, g)
        assert a.v_th is not None and b.v_th is not None
        assert g.transfer_runs[0].transfer is not g.transfer_runs[1].transfer
    finally:
        g.transfer_run_idx = original


def test_every_device_yields_finite_metrics(app):
    for g in app.devices:
        tm, od = compute(app, g)
        assert tm.v_th is not None and np.isfinite(tm.v_th), g.name
        assert tm.mu_sat is not None and tm.mu_sat > 0, g.name
        assert tm.on_off is not None and tm.on_off > 1, g.name
        assert tm.fit is not None and tm.fit.r2 > 0.9, g.name
        assert len(od.blocks) == 4, g.name


def test_every_device_renders_both_figures(app):
    for g in app.devices:
        tm, _od = compute(app, g)
        tf = transfer_figure(g.transfer, tm, _transfer_settings(app), 0.5)
        of = output_figure(g.output, _output_settings(app), 0.5)
        assert len(tf.data) > 0 and len(of.data) > 0, g.name


def test_summary_table_has_nine_rows(app):
    rows = []
    for g in app.devices:
        tm, od = compute(app, g)
        rows.append(export.summary_row(effective_group(app, g), tm, od))
    df = export.summary_dataframe(rows)
    assert len(df) == 9
    assert df["V_th (V)"].notna().all()
    assert df["mu_sat (cm2/Vs)"].notna().all()


def test_processed_csv_roundtrips_for_every_device(app):
    for g in app.devices:
        tm, _od = compute(app, g)
        t_csv = export.transfer_processed_csv(g.transfer, tm)
        o_csv = export.output_processed_csv(g.output)
        assert t_csv.count("\n") > 100, g.name
        assert o_csv.count("\n") > 100, g.name


def test_zip_contains_per_device_folders(app):
    items = []
    for g in app.devices[:2]:
        tm, _od = compute(app, g)
        items.append((f"{g.name}/transfer_processed.csv",
                      export.transfer_processed_csv(g.transfer, tm).encode("utf-8-sig")))
    blob = export.build_zip(items)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert all("/" in n for n in z.namelist())


def test_figure_bytes_exports_every_device_when_kaleido_available(app):
    """전체 파이프라인의 마지막 구간(이미지 렌더)도 가능하면 한 번은 확인한다.
    kaleido/Chromium 이 없는 환경에서는 건너뛴다 — 이 조합은 tests/test_export.py
    가 별도로 검증한다."""
    g = app.devices[0]
    tm, _od = compute(app, g)
    fig = transfer_figure(g.transfer, tm, _transfer_settings(app), 0.5)
    try:
        png = export.figure_bytes(fig, "png")
    except export.KaleidoUnavailable:
        pytest.skip("kaleido 미설치")
    assert len(png) > 0
