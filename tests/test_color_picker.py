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


def test_sized_swatch_css_pins_a_true_square():
    """width/height 만으로는 Streamlit 버튼 기본 min-* 와 인라인 display 에
    져서 정사각형이 깨진다 — min-width/min-height/display:block 이 필수다."""
    css = cp._swatch_css("cp_trig_demo", "#FF8000", size="32px")
    for decl in ("width: 32px", "height: 32px",
                 "min-width: 32px", "min-height: 32px", "display: block"):
        assert decl in css, decl


def test_unsized_swatch_css_leaves_the_box_alone():
    css = cp._swatch_css("cp_trig_demo", "#FF8000")
    assert "min-width" not in css and "display: block" not in css


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


def test_trigger_button_is_a_blank_fixed_size_square():
    """트리거는 색만 보여주는 1:1 스와치다 — 색 이름/hex 를 글자로 적지 않고
    폭도 컬럼에 맞춰 늘리지 않는다(요구사항: 1:1 유지, 색값 표기 안 함)."""
    body = inspect.getsource(cp.color_picker).split('"""')[-1]
    assert 'st.button(" "' in body
    assert "color_caption(current), key=" not in body      # 라벨로 쓰지 않는다
    assert "use_container_width=False" in body
    assert "use_container_width=True" not in body
    assert f"size={cp.SWATCH_SIZE}" in body or "size=SWATCH_SIZE" in body


def test_trigger_keeps_its_label_caption_and_tooltip():
    """라벨(캡션)은 남기고, 색 이름은 툴팁으로만 전달한다."""
    body = inspect.getsource(cp.color_picker).split('"""')[-1]
    assert "st.caption(label)" in body
    assert "help=" in body and "color_caption(current)" in body


def test_grid_and_trigger_share_one_swatch_size():
    assert cp.SWATCH_SIZE.endswith("px")
    dialog = inspect.getsource(cp._palette_dialog)
    assert "size=SWATCH_SIZE" in dialog


# ---------------- 커스텀 색: st.color_picker 를 쓰면 다이얼로그가 닫힌다 ----------------

def test_dialog_never_uses_st_color_picker():
    """네이티브 색 팝업이 st.dialog 의 '바깥 클릭' 판정에 걸려 모달을 닫아버린다.
    그래서 커스텀 색은 iframe 안 <input type="color"> + hex 텍스트 인풋으로만
    받는다(photodetector-app 이 같은 버그를 이렇게 우회했다)."""
    # 호출(괄호 포함)만 잡는다 — 왜 안 쓰는지 설명하는 독스트링은 남아 있어야 한다.
    assert "st.color_picker(" not in inspect.getsource(cp)


def test_dialog_reads_custom_color_from_a_hex_text_input():
    dialog = inspect.getsource(cp._palette_dialog)
    assert "st.text_input" in dialog
    assert "custom_key(" in dialog
    assert "components.html" in dialog
    # 적용 버튼을 눌러야만 반영된다 — 매 렌더마다 위젯 값을 그대로 쓰면
    # 팔레트로 고른 색을 스스로 덮어쓴다.
    assert "st.button(" in dialog and "target[field] = normalize_hex(typed" in dialog


def test_native_color_input_drives_that_pickers_own_hex_field():
    """여러 피커가 한 페이지에 있어도 JS 셀렉터가 섞이면 안 된다."""
    hex_key = cp.custom_key("t_axis_l")
    html = cp._native_color_input_html("#FF8000", hex_key)
    assert 'type="color"' in html
    assert 'value="#FF8000"' in html
    assert f".st-key-{hex_key} input" in html
    # React 관리 인풋이라 value setter 우회 + input 이벤트 dispatch 가 필수
    assert "getOwnPropertyDescriptor" in html
    assert "nativeSetter.call" in html
    assert "dispatchEvent" in html
    assert "window.parent.document" in html


def test_native_color_input_normalizes_its_initial_value():
    assert 'value="#FF8800"' in cp._native_color_input_html("#f80", cp.custom_key("k"))
    assert 'value="#000000"' in cp._native_color_input_html("junk", cp.custom_key("k"))


def test_component_does_not_nest_columns_in_the_trigger():
    """호출자가 이미 st.columns 안에 있으므로(서식 탭 2열) 트리거는 컬럼을
    만들면 안 된다 — Streamlit 은 컬럼 중첩을 한 단계까지만 허용한다."""
    parts = inspect.getsource(cp.color_picker).split('"""')
    body = parts[-1]                       # 독스트링 뒤의 실제 코드만
    assert "st.columns" not in body
