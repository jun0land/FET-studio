from fet_app import presets
from fet_app.state import default_settings
from fet_app.ui.panel_insets import ANCHOR_PRESETS, active_anchor


def test_active_anchor_matches_default_legend_bottom_right():
    s = default_settings()
    # DEFAULTS: legend x=0.99,y=0.01,xanchor=right,yanchor=bottom -> bottom-right
    assert active_anchor(s["insets"]["legend"]) == "bottom-right"


def test_active_anchor_matches_default_sample_top_left():
    s = default_settings()
    assert active_anchor(s["insets"]["sample"]) == "top-left"


def test_active_anchor_none_when_no_preset_matches():
    # 9개 프리셋은 {left,center,right} x {top,middle,bottom} 전 조합을 덮으므로,
    # 그 집합 밖의 값(예: xanchor 미지정)일 때만 일치하는 프리셋이 없다.
    assert active_anchor({"xanchor": None, "yanchor": "bottom",
                          "x": 0.3, "y": 0.3}) is None


def test_all_nine_presets_present_and_distinct():
    assert len(ANCHOR_PRESETS) == 9
    combos = {(p["xanchor"], p["yanchor"]) for p in ANCHOR_PRESETS.values()}
    assert len(combos) == 9


def test_anchor_preset_lookup_center():
    assert ANCHOR_PRESETS["center"] == {
        "x": 0.50, "y": 0.50, "xanchor": "center", "yanchor": "middle"}


def test_edited_inset_config_roundtrips_through_presets():
    s = default_settings()
    s["insets"]["legend"].update(ANCHOR_PRESETS["top-left"])
    s["insets"]["legend"]["font_size"] = 22
    s["insets"]["sample"]["text"] = "Device **A**"

    p = presets.extract(s)
    back_json = presets.from_json(presets.to_json(p))
    fresh = presets.apply(default_settings(), back_json)

    assert active_anchor(fresh["insets"]["legend"]) == "top-left"
    assert fresh["insets"]["legend"]["font_size"] == 22
    assert fresh["insets"]["sample"]["text"] == "Device **A**"
