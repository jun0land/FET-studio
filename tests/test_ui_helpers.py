from fet_app.grouping import DeviceGroup
from fet_app.state import AppState
from fet_app.ui.device_list import device_flags, filter_devices
from fet_app.ui.viewport import FALLBACK_SCALE, preview_scale, scale_for_width


def test_filter_is_case_insensitive_substring():
    devs = [DeviceGroup(name="1-1"), DeviceGroup(name="1-10"), DeviceGroup(name="A-2")]
    assert [g.name for g in filter_devices(devs, "1-1")] == ["1-1", "1-10"]
    assert [g.name for g in filter_devices(devs, "a")] == ["A-2"]
    assert len(filter_devices(devs, "")) == 3


def test_device_flags_warn_on_missing_curve():
    app = AppState()
    g = DeviceGroup(name="x")           # transfer/output 모두 없음
    assert "no-data" in device_flags(app, g)


def test_device_flags_warn_on_group_warnings():
    app = AppState()
    g = DeviceGroup(name="x", warnings=["뭔가 이상"])
    assert "warning" in device_flags(app, g)


def test_scale_for_width_clamped():
    assert scale_for_width(0) == FALLBACK_SCALE
    assert scale_for_width(100) == 0.25
    assert scale_for_width(9600) == 1.0
    assert abs(scale_for_width(480) - 0.5) < 1e-9


def test_manual_scale_overrides_auto():
    app = AppState()
    app.preview_scale = 0.42
    assert preview_scale(app) == 0.42
