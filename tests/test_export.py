import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from fet_app import export
from fet_app.curves import OutputBlock, OutputCurve, TransferCurve
from fet_app.grouping import DeviceGroup, MeasurementRun
from fet_app.metrics import output_diagnostics, transfer_metrics
from fet_app.params import DeviceParams

PARAMS = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)


def _transfer():
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = -np.maximum(2e-8 * (v_g + 12.0) ** 2 * (v_g < -12.0), 1e-12)
    df = pd.DataFrame({"V_G": v_g, "I_G": np.full_like(v_g, 1e-11), "I_D": i_d})
    return TransferCurve(forward=df, reverse=df.iloc[::-1].reset_index(drop=True),
                         v_ds=-60.0, dual=True)


def _output():
    v_d = np.arange(0, -61, -1, dtype=float)
    blocks = [OutputBlock(v_g=-20.0 * i,
                          forward=pd.DataFrame({"V_D": v_d,
                                                "I_D": -1e-6 * (i + 1) * np.tanh(v_d / -20),
                                                "I_G": np.full_like(v_d, 1e-12)}),
                          reverse=None)
              for i in range(4)]
    return OutputCurve(blocks=blocks)


def _group():
    # DeviceGroup.transfer / .output are read-only properties resolving a run
    # index, not constructor fields — wrap the curves in MeasurementRun lists.
    transfer_run = MeasurementRun(sheet="Data", label="Data", is_latest=True,
                                  kind="transfer", reason="settings",
                                  transfer=_transfer())
    output_run = MeasurementRun(sheet="Data", label="Data", is_latest=True,
                                kind="output", reason="settings",
                                output=_output())
    return DeviceGroup(name="1-1",
                       transfer_sources={"1-1.xls": [transfer_run]},
                       output_sources={"1-1 out.xls": [output_run]},
                       transfer_file="1-1.xls", output_file="1-1 out.xls",
                       params=PARAMS)


def test_summary_row_columns_and_values():
    g = _group()
    tm = transfer_metrics(g.transfer, PARAMS)
    od = output_diagnostics(g.output)
    row = export.summary_row(g, tm, od)
    for key in ("Device", "W (um)", "L (um)", "eps_r", "d (nm)", "C_ox (nF/cm2)",
                "V_DS (V)", "V_th (V)", "mu_sat (cm2/Vs)", "I_on/I_off",
                "SS (mV/dec)", "dV_th (V)", "Fit R2", "Fit range (V)", "Fit points",
                "0V offset (%)", "Origin linearity R2", "Saturation ratio",
                "Gate leak (%)", "Warnings"):
        assert key in row, key
    assert row["Device"] == "1-1"
    assert row["V_DS (V)"] == -60.0
    assert row["C_ox (nF/cm2)"] == pytest.approx(11.51, rel=1e-3)


def test_summary_dataframe_keeps_column_order():
    g = _group()
    tm = transfer_metrics(g.transfer, PARAMS)
    od = output_diagnostics(g.output)
    df = export.summary_dataframe([export.summary_row(g, tm, od)])
    assert list(df.columns)[0] == "Device"
    assert list(df.columns)[-1] == "Warnings"


def test_summary_csv_and_xlsx_roundtrip():
    g = _group()
    df = export.summary_dataframe([export.summary_row(
        g, transfer_metrics(g.transfer, PARAMS), output_diagnostics(g.output))])
    csv = export.summary_csv_bytes(df)
    assert csv.startswith(b"\xef\xbb\xbf")   # 엑셀 한글 깨짐 방지 BOM
    back = pd.read_csv(io.BytesIO(csv))
    assert back.loc[0, "Device"] == "1-1"

    xlsx = export.summary_xlsx_bytes(df)
    assert xlsx[:2] == b"PK"
    back2 = pd.read_excel(io.BytesIO(xlsx))
    assert back2.loc[0, "Device"] == "1-1"


def test_transfer_processed_csv_has_fit_column():
    c = _transfer()
    tm = transfer_metrics(c, PARAMS)
    text = export.transfer_processed_csv(c, tm)
    header = text.splitlines()[0]
    assert header.split(",") == ["branch", "V_G", "I_G", "I_D", "sqrt_abs_I_D", "fit_sqrt_I_D"]
    assert "forward" in text and "reverse" in text


def test_output_processed_csv_columns():
    text = export.output_processed_csv(_output())
    assert text.splitlines()[0].split(",") == ["V_G", "branch", "V_D", "I_D", "I_G"]


def test_build_zip_structure():
    data = export.build_zip([("1-3/transfer.png", b"a"), ("1-3/output.png", b"b")])
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.namelist() == ["1-3/transfer.png", "1-3/output.png"]


def test_png_is_transparent_and_jpg_is_white():
    """스펙 §7 — PNG 투명, JPG 흰 배경. kaleido 가 없으면 skip."""
    from fet_app.figure_common import new_figure
    from fet_app.constants import DEFAULTS
    fig = new_figure(DEFAULTS["output_geom"], k=0.2)
    try:
        png = export.figure_bytes(fig, "png", scale=1)
        jpg = export.figure_bytes(fig, "jpg", scale=1)
    except export.KaleidoUnavailable:
        pytest.skip("kaleido 미설치")

    from PIL import Image
    im = Image.open(io.BytesIO(png))
    assert im.mode == "RGBA"
    assert im.getpixel((0, 0))[3] == 0          # 좌상단 알파 0 = 투명

    jm = Image.open(io.BytesIO(jpg)).convert("RGB")
    assert jm.getpixel((0, 0)) == (255, 255, 255)


def test_figure_bytes_rejects_unknown_format():
    from fet_app.figure_common import new_figure
    from fet_app.constants import DEFAULTS
    with pytest.raises(ValueError):
        export.figure_bytes(new_figure(DEFAULTS["output_geom"], 0.2), "gif")


def test_export_does_not_mutate_figure():
    from fet_app.figure_common import new_figure
    from fet_app.constants import DEFAULTS
    fig = new_figure(DEFAULTS["output_geom"], k=0.2)
    try:
        export.figure_bytes(fig, "png")
    except export.KaleidoUnavailable:
        pytest.skip("kaleido 미설치")
    assert fig.layout.paper_bgcolor == "#FFFFFF"   # 화면 표시는 흰 배경 유지
