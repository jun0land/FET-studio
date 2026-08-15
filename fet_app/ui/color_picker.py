"""Origin 24색 팔레트 색 피커 (재사용 컴포넌트).

포팅 출처: ``photodetector-app/pd_app/ui/panel_traces.py`` 의 ``_color_dialog``
/ ``_color_control``. 스와치 그리드, 정사각형 트리거 버튼, 그리고 커스텀 색을
HTML5 ``<input type="color">`` + JS 동기화로 다루는 우회법까지 가져왔다.
그 앱의 투명도 설정만 빼놓았다 — 이 앱에는 없는 개념이다.

설계 — 왜 커스텀 색에 ``st.color_picker`` 를 쓰지 않는가:
``st.color_picker`` 를 누르면 브라우저 네이티브 색상 팝업이 뜨는데, 그 클릭이
``st.dialog`` 모달의 "바깥 클릭 시 닫기" 판정에 걸려 **색을 고르려는 순간
다이얼로그가 꺼진다**. 그래서 네이티브 ``<input type="color">`` 를
``components.html`` 이 만드는 iframe 안에 두어 부모 문서의 클릭 감지에서
격리시키고, 그 ``oninput`` 에서 JS 로 옆의 ``st.text_input``(hex 칸) 값을
네이티브 setter 로 갱신 + ``input`` 이벤트를 dispatch 해 Streamlit 에 알린다.
즉 Streamlit 쪽 진실 값은 언제나 hex 텍스트 인풋이고, iframe 은 그 값을
편하게 채워주는 입력 보조 장치일 뿐이다.

설계 — 왜 세션 상태를 거치는가:
``st.dialog`` 은 데코레이터가 평가되는 시점에 제목 문자열이 고정되므로,
다이얼로그 함수는 모듈당 하나만 두고 여러 호출자가 공유해야 한다. 그래서
"지금 어떤 dict 의 어떤 필드를 편집 중인지"를 트리거 버튼이 눌린 순간
``st.session_state[_TARGET]`` 에 담고, 다이얼로그는 그것만 읽어 동작한다.
한 번에 열리는 다이얼로그는 하나뿐이라 이 슬롯은 하나면 충분하고, 피커마다
고유한 ``key`` 에서 파생한 슬러그로 위젯 key 를 만들기 때문에 한 페이지에
여러 피커가 있어도 서로 값이 섞이지 않는다.

편집 대상 dict 는 참조로 들고 있는다(`app.settings[...]` 의 하위 dict 는
세션 내내 같은 객체다) — 스와치를 누르면 그 dict 의 필드가 즉시 갱신된다.
"""

from __future__ import annotations

import re

import streamlit as st
import streamlit.components.v1 as components

from fet_app.constants import ORIGIN_COLORS

CUSTOM = "Custom"          # 팔레트에 없는 색의 이름
GRID_COLS = 8              # 24색을 8열 x 3행으로 (photodetector-app 과 동일)
SWATCH_SIZE = "32px"       # 트리거 버튼과 그리드 스와치가 공유하는 1:1 한 변

_TARGET = "_color_picker_target"   # 세션 상태 슬롯 (열려 있는 다이얼로그의 편집 대상)
_UNSAFE = re.compile(r"\W+")
# 흰 스와치 위의 흰 글자를 막기 위한 밝기 경계 (0~255 의 relative luminance).
_BRIGHT_CUTOFF = 150.0


def normalize_hex(hex_color, default: str = "#000000") -> str:
    """'ff8000' / '#f80' / '#FF8000' -> '#FF8000'. 못 읽으면 default."""
    h = str(hex_color).strip().upper().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6 or any(c not in "0123456789ABCDEF" for c in h):
        return default
    return "#" + h


def color_name_of(hex_color) -> str:
    """hex -> Origin 팔레트 이름 역조회. 팔레트에 없으면 ``"Custom"``."""
    h = normalize_hex(hex_color, default="")
    if not h:
        return CUSTOM
    return next((k for k, v in ORIGIN_COLORS.items()
                 if normalize_hex(v) == h), CUSTOM)


def color_caption(hex_color) -> str:
    """버튼에 쓸 표시 문자열 — 팔레트 색이면 이름을, 아니면 hex 를 보여준다."""
    name = color_name_of(hex_color)
    return normalize_hex(hex_color) if name == CUSTOM else name


def contrast_text_color(hex_color) -> str:
    """스와치 위 글자색. 밝은 배경엔 검정, 어두운 배경엔 흰색."""
    h = normalize_hex(hex_color).lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#000000" if (0.299 * r + 0.587 * g + 0.114 * b) > _BRIGHT_CUTOFF else "#FFFFFF"


def _slug(key: str) -> str:
    """위젯 key 로 쓸 수 있게 CSS 클래스(.st-key-<key>)에 안전한 형태로 만든다."""
    return _UNSAFE.sub("_", str(key))


def trigger_key(key: str) -> str:
    return f"cp_trig_{_slug(key)}"


def custom_key(key: str) -> str:
    """다이얼로그 안 hex 텍스트 인풋의 key. iframe 의 JS 가 이 key 로 만들어진
    ``.st-key-<key> input`` 셀렉터로 값을 밀어 넣으므로 유일해야 한다."""
    return f"cp_custom_{_slug(key)}"


def _swatch_css(class_key: str, hex_color: str, *, size: str | None = None) -> str:
    """``.st-key-<key>`` 컨벤션으로 그 버튼 하나만 색 스와치처럼 칠한다.

    이 클래스는 Streamlit 이 key 있는 위젯 컨테이너에 자동으로 붙여주는 것으로,
    이 저장소의 theme.py / summary.py 에서도 이미 쓰고 있는 검증된 패턴이다.

    ``size`` 를 주면 1:1 정사각형을 강제한다. ``width``/``height`` 만으로는
    부족하다 — Streamlit 버튼의 기본 ``min-width``/``min-height`` 와 인라인
    ``display`` 가 그대로 이기기 때문에, ``min-*`` 와 ``display: block`` 을
    같이 줘야 실제로 정사각형이 된다(photodetector-app 이 같은 결론).
    """
    box = (f"width: {size} !important; height: {size} !important; "
           f"min-width: {size} !important; min-height: {size} !important; "
           f"padding: 0 !important; display: block !important; "
           f"margin: 0 auto !important; ") if size else ""
    return (
        f"<style>"
        f".st-key-{class_key} button {{"
        f" background: {hex_color} !important;"
        f" color: {contrast_text_color(hex_color)} !important;"
        f" border: 1px solid rgba(0,0,0,0.35) !important;"
        f" border-radius: 6px !important; {box}"
        f"}}"
        f".st-key-{class_key} button:hover {{"
        f" border: 2px solid #000 !important;"
        f" color: {contrast_text_color(hex_color)} !important;"
        f"}}"
        f".st-key-{class_key} button p {{"
        f" color: {contrast_text_color(hex_color)} !important;"
        f"}}"
        f"</style>"
    )


def _native_color_input_html(current: str, hex_key: str) -> str:
    """iframe 안에 띄울 HTML5 ``<input type="color">``.

    ``oninput`` 에서 부모 문서의 ``.st-key-<hex_key> input``(= 옆의 hex
    텍스트 인풋)을 찾아 **네이티브 value setter** 로 값을 넣고 ``input``
    이벤트를 dispatch 한다. React 가 관리하는 인풋이라 ``el.value = ...`` 만
    해서는 Streamlit 이 변경을 알아채지 못하기 때문에 setter 우회가 필요하다.
    """
    return (
        f'<div style="display:flex; align-items:center; justify-content:center;">'
        f'<input type="color" value="{normalize_hex(current)}" '
        f'style="width:38px; height:38px; padding:0; border:1px solid #ccc; '
        f'border-radius:6px; cursor:pointer;" '
        f'oninput="'
        f"var hexInput = window.parent.document.querySelector('.st-key-{hex_key} input');"
        f'if (hexInput) {{'
        f"var nativeSetter = Object.getOwnPropertyDescriptor("
        f"window.HTMLInputElement.prototype, 'value').set;"
        f'nativeSetter.call(hexInput, this.value);'
        f"hexInput.dispatchEvent(new Event('input', {{ bubbles: true }}));"
        f'}}">'
        f'</div>'
    )


@st.dialog("🎨 색 선택")
def _palette_dialog() -> None:
    """Origin 24색 그리드 + 커스텀 색 폴백. 편집 대상은 세션 상태에서 읽는다."""
    tgt = st.session_state.get(_TARGET)
    if not tgt:                      # 방어: 대상 없이 열릴 일은 없다
        st.caption("편집할 색 대상을 찾지 못했습니다.")
        return
    target, field = tgt["target"], tgt["field"]
    label, slug = tgt["label"], tgt["slug"]
    current = normalize_hex(target.get(field, "#000000"))

    st.markdown(f"**{label}** · 현재 `{color_caption(current)}`")
    st.caption("Origin 24색 팔레트")

    items = list(ORIGIN_COLORS.items())
    for start in range(0, len(items), GRID_COLS):
        cols = st.columns(GRID_COLS)
        for offset, (name, hexv) in enumerate(items[start:start + GRID_COLS]):
            with cols[offset]:
                btn_key = f"cp_sw_{slug}_{start + offset}"
                st.markdown(_swatch_css(btn_key, hexv, size=SWATCH_SIZE),
                            unsafe_allow_html=True)
                if st.button(" ", key=btn_key, help=name, use_container_width=False):
                    target[field] = hexv
                    st.rerun()       # 다이얼로그를 닫으면서 새 색으로 다시 그린다

    st.divider()
    st.caption("커스텀 색상")
    hex_key = custom_key(tgt["key"])
    c_pick, c_hex, c_apply = st.columns([1, 2, 2], vertical_alignment="bottom")
    with c_pick:
        # iframe 안의 네이티브 컬러 인풋 — 여기서 고른 값을 JS 가 옆 hex 칸에
        # 밀어 넣는다. 부모 문서에서 열리지 않으므로 다이얼로그가 닫히지 않는다.
        components.html(_native_color_input_html(current, hex_key), height=56)
    with c_hex:
        typed = st.text_input("Hex 코드", value=current, key=hex_key,
                              max_chars=7, label_visibility="collapsed")
    with c_apply:
        # 커스텀 색은 '적용' 버튼으로만 반영한다. 위젯 값을 매 렌더마다 그대로
        # 써버리면 팔레트로 고른 색을 스스로 덮어쓸 수 있다.
        if st.button("설정 적용", key=f"cp_apply_{slug}", type="primary",
                     use_container_width=True):
            # 읽을 수 없는 입력이면 현재 색을 유지한다(조용히 무시).
            target[field] = normalize_hex(typed, default=current)
            st.rerun()


def color_picker(label: str, target: dict, field: str, *,
                 key: str, default: str = "#000000") -> str:
    """색 하나를 고르는 트리거 버튼. 고른 색은 ``target[field]`` 에 바로 들어간다.

    특정 설정 dict/필드에 종속되지 않는 범용 위젯이다. ``key`` 는 페이지 안에서
    유일해야 한다(트리거 버튼과 다이얼로그 내부 위젯 key 가 여기서 파생된다).
    반환값은 지금 적용돼 있는 색(#RRGGBB).

    컬럼 중첩을 만들지 않는다 — 호출자가 이미 ``st.columns`` 안에 있을 수 있고,
    Streamlit 은 컬럼 중첩을 한 단계까지만 허용하기 때문이다.
    """
    current = normalize_hex(target.get(field, default), default=default)
    slug = _slug(key)
    btn_key = trigger_key(key)

    # 버튼은 색 자체를 보여주는 1:1 스와치다 — 색 이름/hex 는 글자로 적지 않고
    # 툴팁에만 담는다(작은 정사각형 안에서 어차피 읽히지 않는다).
    st.caption(label)
    st.markdown(_swatch_css(btn_key, current, size=SWATCH_SIZE),
                unsafe_allow_html=True)
    if st.button(" ", key=btn_key, use_container_width=False,
                 help=f"{label} — 현재 {color_caption(current)} · "
                      f"클릭해서 Origin 팔레트에서 고르기"):
        # 커스텀 피커 위젯의 예전 값이 남아 있으면 다시 열었을 때 현재 색이
        # 아닌 옛 값이 보인다. 열 때마다 비워 current 로 초기화되게 한다.
        st.session_state.pop(custom_key(key), None)
        st.session_state[_TARGET] = {"target": target, "field": field,
                                     "label": label, "slug": slug, "key": key}
        _palette_dialog()
    return current
