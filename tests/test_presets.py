import json

from fet_app import presets
from fet_app.state import default_settings


def test_extract_contains_only_format_keys():
    p = presets.extract(default_settings())
    assert set(p) == {"geom", "style", "transfer_axes", "output_axes",
                      "transfer_style", "output_style", "insets"}


def test_extract_excludes_measurement_inputs():
    s = default_settings()
    s["thresholds"] = {"zero_offset": 0.5}
    s["params"] = {"w_um": 1000}
    p = presets.extract(s)
    assert "thresholds" not in p
    assert "params" not in p


def test_apply_returns_new_dict_and_leaves_original():
    s = default_settings()
    p = presets.extract(s)
    p["style"]["line_width"] = 4.0
    s2 = presets.apply(s, p)
    assert s2["style"]["line_width"] == 4.0
    assert s["style"]["line_width"] == 2.0


def test_apply_ignores_unknown_keys():
    s = default_settings()
    s2 = presets.apply(s, {"style": {"line_width": 3.0}, "bogus": 1})
    assert s2["style"]["line_width"] == 3.0
    assert "bogus" not in s2


def test_json_roundtrip():
    p = presets.extract(default_settings())
    back = presets.from_json(presets.to_json(p))
    assert back == p
    json.loads(presets.to_json(p))   # 유효한 JSON


def test_from_json_rejects_non_object():
    try:
        presets.from_json("[1,2,3]")
    except ValueError:
        return
    raise AssertionError("리스트를 받으면 ValueError 여야 합니다")
