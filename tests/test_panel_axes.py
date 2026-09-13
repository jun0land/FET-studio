from fet_app import presets
from fet_app.state import default_settings
from fet_app.ui.panel_axes import parse_dtick, parse_minor_dtick, parse_optional_float


def test_parse_optional_float_empty_is_none():
    assert parse_optional_float("") is None
    assert parse_optional_float("   ") is None


def test_parse_optional_float_reads_number():
    assert parse_optional_float("20") == 20.0
    assert parse_optional_float(" -3.5 ") == -3.5


def test_parse_optional_float_garbage_is_none():
    assert parse_optional_float("abc") is None


def test_parse_minor_dtick_log_axis_keeps_string():
    assert parse_minor_dtick("D1", "log") == "D1"
    assert parse_minor_dtick(" D2 ", "log") == "D2"
    assert parse_minor_dtick("", "log") is None


def test_parse_minor_dtick_linear_axis_parses_number():
    assert parse_minor_dtick("5", "linear") == 5.0
    assert parse_minor_dtick("", "linear") is None
    assert parse_minor_dtick("nope", "linear") is None


def test_edited_axis_config_roundtrips_through_presets():
    s = default_settings()
    s["transfer_axes"]["x"]["auto"] = False
    s["transfer_axes"]["x"]["min"] = -20.0
    s["transfer_axes"]["x"]["max"] = 20.0
    s["transfer_axes"]["x"]["dtick"] = 5.0
    s["transfer_axes"]["y"]["minor_dtick"] = "D2"
    s["output_axes"]["y"]["title"] = "I_{D} custom (A)"

    p = presets.extract(s)
    back_json = presets.from_json(presets.to_json(p))
    fresh = presets.apply(default_settings(), back_json)

    assert fresh["transfer_axes"]["x"]["auto"] is False
    assert fresh["transfer_axes"]["x"]["min"] == -20.0
    assert fresh["transfer_axes"]["x"]["max"] == 20.0
    assert fresh["transfer_axes"]["x"]["dtick"] == 5.0
    assert fresh["transfer_axes"]["y"]["minor_dtick"] == "D2"
    assert fresh["output_axes"]["y"]["title"] == "I_{D} custom (A)"


def test_parse_dtick_rejects_zero_and_negative():
    """0·음수 간격은 Plotly 가 눈금을 못 만든다 — 입력 단계에서 '미지정'으로."""
    assert parse_dtick("20") == 20.0
    assert parse_dtick("0") is None
    assert parse_dtick("-20") is None
    assert parse_dtick("") is None


def test_parse_minor_dtick_only_accepts_what_plotly_understands():
    assert parse_minor_dtick("D1", "log") == "D1"
    assert parse_minor_dtick("d2", "log") == "D2"
    assert parse_minor_dtick("아무거나", "log") is None
    assert parse_minor_dtick("2", "log") == 2.0
    assert parse_minor_dtick("D1", "linear") is None
    assert parse_minor_dtick("0", "linear") is None
    assert parse_minor_dtick("5", "linear") == 5.0
