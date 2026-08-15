"""Origin 팔레트 색 피커 컴포넌트 — 순수 함수 부분 (fet_app/ui/color_picker.py).

Streamlit 위젯 자체는 여기서 못 돌리므로, hex 정규화·이름 역조회·대비 글자색·
key 파생처럼 다이얼로그 밖에서 결정되는 로직만 검증한다. 위젯 동작(다중 피커
독립성 등)은 Playwright 로 따로 확인했다.
"""

import inspect

from fet_app.constants import ORIGIN_COLORS
from fet_app.ui import color_picker as cp


# ---------------- hex 정규화 ----------------

def test_normalize_accepts_common_hex_spellings():
    assert cp.normalize_hex("#ff8000") == "#FF8000"
    assert cp.normalize_hex("ff8000") == "#FF8000"
    assert cp.normalize_hex("#f80") == "#FF8800"
    assert cp.normalize_hex("  #FF8000 ") == "#FF8000"


def test_normalize_falls_back_on_garbage():
    assert cp.normalize_hex("not-a-color") == "#000000"
    assert cp.normalize_hex(None, default="#ED542B") == "#ED542B"
    assert cp.normalize_hex("#12345", default="#ED542B") == "#ED542B"
    assert cp.normalize_hex("#GGGGGG") == "#000000"


# ---------------- hex -> 팔레트 이름 역조회 ----------------

def test_every_palette_color_round_trips_to_its_name():
    for name, hexv in ORIGIN_COLORS.items():
        assert cp.color_name_of(hexv) == name


def test_reverse_lookup_is_case_insensitive():
    assert cp.color_name_of("#ff0000") == "Red"
    assert cp.color_name_of("#FF0000") == "Red"


def test_unknown_color_is_custom():
    assert cp.color_name_of("#123456") == cp.CUSTOM
    assert cp.color_name_of("nonsense") == cp.CUSTOM


def test_caption_shows_name_for_palette_and_hex_for_custom():
    """버튼에 팔레트 색은 이름을, 그 외에는 hex 를 보여준다."""
    assert cp.color_caption("#FF8000") == "Orange"
    assert cp.color_caption("#000000") == "Black"
    assert cp.color_caption("#123456") == "#123456"
    assert cp.color_caption("123456") == "#123456"


# ---------------- 스와치 위 글자색 ----------------

def test_contrast_text_flips_on_light_backgrounds():
    assert cp.contrast_text_color("#FFFFFF") == "#000000"
    assert cp.contrast_text_color("#FFFF00") == "#000000"
    assert cp.contrast_text_color("#000000") == "#FFFFFF"
    assert cp.contrast_text_color("#000080") == "#FFFFFF"


def test_every_palette_color_gets_a_legible_text_color():
    for hexv in ORIGIN_COLORS.values():
        assert cp.contrast_text_color(hexv) in ("#000000", "#FFFFFF")


# ---------------- key 파생: 피커끼리 절대 겹치면 안 된다 ----------------

def test_widget_keys_are_unique_per_picker_key():
    keys = ["t_axis_l", "t_line_l", "t_axis_r", "t_line_r", "o_base"]
    trig = [cp.trigger_key(k) for k in keys]
    cust = [cp.custom_key(k) for k in keys]
    assert len(set(trig)) == len(keys)
    assert len(set(cust)) == len(keys)
    assert not set(trig) & set(cust)


def test_widget_keys_are_css_class_safe():
    """`.st-key-<key>` 셀렉터에 그대로 박히므로 영숫자/밑줄만 남아야 한다."""
    for raw in ("좌축 색", "a.b-c", "x y", "t_axis_l"):
        for k in (cp.trigger_key(raw), cp.custom_key(raw)):
            assert k.replace("_", "").isalnum(), k


def test_swatch_css_targets_only_that_widget():
    css = cp._swatch_css("cp_trig_demo", "#FF8000")
    assert ".st-key-cp_trig_demo button" in css
    assert "#FF8000" in css
    # 흰 글자가 주황 위에 얹히지 않도록 대비색이 같이 들어간다
    assert cp.contrast_text_color("#FF8000") in css


# ---------------- 컴포넌트 계약 ----------------

def test_color_picker_is_generic_over_dict_and_field():
    """특정 설정 dict/필드에 종속되지 않는 범용 시그니처여야 한다."""
    sig = inspect.signature(cp.color_picker)
    assert list(sig.parameters) == ["label", "target", "field", "key", "default"]
    assert sig.parameters["key"].kind is inspect.Parameter.KEYWORD_ONLY


def test_palette_grid_covers_all_24_colors_in_8_columns():
    assert len(ORIGIN_COLORS) == 24
    assert cp.GRID_COLS == 8
    assert len(ORIGIN_COLORS) % cp.GRID_COLS == 0    # 8 x 3 로 딱 떨어진다


def test_component_does_not_nest_columns_in_the_trigger():
    """호출자가 이미 st.columns 안에 있으므로(서식 탭 2열) 트리거는 컬럼을
    만들면 안 된다 — Streamlit 은 컬럼 중첩을 한 단계까지만 허용한다."""
    parts = inspect.getsource(cp.color_picker).split('"""')
    body = parts[-1]                       # 독스트링 뒤의 실제 코드만
    assert "st.columns" not in body
