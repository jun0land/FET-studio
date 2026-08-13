import numpy as np
import pandas as pd

from fet_app.curves import TransferCurve
from fet_app.grouping import DeviceGroup, MeasurementRun
from fet_app.params import DeviceParams
from fet_app.parsing import TRANSFER
from fet_app.state import AppState
from fet_app.ui.summary import compute, format_metric


def test_format_metric_handles_none():
    assert format_metric(None, "volt") == "—"
    assert format_metric(None, "mobility") == "—"


def test_format_metric_units():
    assert format_metric(-12.4123, "volt") == "-12.41 V"
    assert format_metric(0.0312, "mobility") == "3.12E-02"
    assert format_metric(3.2e5, "ratio") == "3.2E+05"
    assert format_metric(2100.0, "ss") == "2100 mV/dec"
    assert format_metric(0.0034, "percent") == "0.34 %"


def test_compute_returns_none_for_missing_curves():
    app = AppState()
    g = DeviceGroup(name="x")
    tm, od = compute(app, g)
    assert tm is None and od is None


def test_compute_uses_effective_params():
    app = AppState()
    app.global_params = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = -np.maximum(2e-8 * (v_g + 12.0) ** 2 * (v_g < -12.0), 1e-12)
    df = pd.DataFrame({"V_G": v_g, "I_G": np.full_like(v_g, 1e-11), "I_D": i_d})
    curve = TransferCurve(forward=df, v_ds=-60.0)
    run = MeasurementRun(sheet="Data", label="Data", is_latest=True,
                         kind=TRANSFER, reason="test", transfer=curve)
    g = DeviceGroup(name="x", transfer_runs=[run])
    tm, od = compute(app, g)
    assert tm is not None and tm.mu_sat is not None
    assert od is None
