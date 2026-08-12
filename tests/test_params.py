import math

import pytest

from fet_app import constants
from fet_app.params import DeviceParams, c_ox_from


def test_epsilon_0_exact_value():
    """스펙 고정값. 반올림하면 mu_sat 이 어긋난다."""
    assert constants.EPSILON_0 == 8.854e-14


def test_dielectric_presets():
    assert constants.DIELECTRIC_PRESETS["SiO2"] == 3.9
    assert constants.DIELECTRIC_PRESETS["Al2O3"] == 9.0
    assert constants.DIELECTRIC_PRESETS["HfO2"] == 25.0
    assert constants.DIELECTRIC_PRESETS["PMMA"] == 3.6


def test_c_ox_sio2_300nm():
    """SiO2 300 nm -> 11.51 nF/cm^2 (스펙 §3.1 검산값)."""
    c = c_ox_from(3.9, 300.0)
    assert math.isclose(c, 1.1510e-8, rel_tol=1e-3)


def test_c_ox_scales_inversely_with_thickness():
    assert math.isclose(c_ox_from(3.9, 150.0), 2 * c_ox_from(3.9, 300.0), rel_tol=1e-9)


def test_c_ox_rejects_nonpositive_thickness():
    with pytest.raises(ValueError):
        c_ox_from(3.9, 0.0)


def test_device_params_unit_conversion():
    p = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)
    assert math.isclose(p.w_cm(), 0.1, rel_tol=1e-12)
    assert math.isclose(p.l_cm(), 5e-3, rel_tol=1e-12)
    assert math.isclose(p.c_ox(), 1.1510e-8, rel_tol=1e-3)
    assert p.is_complete()


def test_device_params_incomplete_when_missing():
    assert not DeviceParams(w_um=None, l_um=50.0, eps_r=3.9, d_nm=300.0).is_complete()


def test_default_thresholds():
    t = constants.DEFAULT_THRESHOLDS
    assert t["zero_offset"] == 0.01
    assert t["linearity_r2"] == 0.99
    assert t["saturation"] == 0.1
    assert t["gate_leak"] == 0.01


def test_fit_algorithm_constants():
    assert constants.FIT_ON_REGION_FACTOR == 100.0
    assert constants.FIT_MIN_POINTS == 10
    assert constants.FIT_MAX_FRACTION == 0.60
    assert constants.FIT_TIE_TOLERANCE == 5e-4
    assert constants.SS_WINDOW == 5
    assert constants.DIAG_SLOPE_POINTS == 5
    assert constants.DIAG_ORIGIN_FRACTION == 0.10


def test_hex_to_rgba():
    assert constants.hex_to_rgba("#ed542b", 0.5) == "rgba(237,84,43,0.5)"
    assert constants.hex_to_rgba("#000", 1) == "rgba(0,0,0,1)"
