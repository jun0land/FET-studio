"""전역 테마: CSS 임베드 (스펙 §6). 폰트를 base64 로 인라인하고, 리퀴드 글래스
패널/버튼/입력 스타일을 적용한다. 반응형 3열 레이아웃은 ``RESPONSIVE_CSS`` 가
맡는다 — ``fet_app.ui.layout`` 이 만드는 3열 블록을 ``:has(.fet-shell-anchor)``
로 찾아 폭을 건다 (스펙 §6.2, §6.1).

포팅 출처: ``photodetector-app/pd_app/theme.py``. 그 앱의 제목·매뉴얼 문구,
배경/로고 이미지, zoom 및 ResizeObserver 뷰포트 바인딩 JS, 팔레트 피커 전용
셀렉터(``st-key-pd_*``)는 이식하지 않았다 — 이 앱 전용 UI(Task 17/18)가 아직
없고, §6.2 는 CSS 미디어 쿼리만으로 4단계 반응형을 처리하므로 JS 관측 루프가
필요 없다. 남긴 것은 폰트 ``@font-face``, 리퀴드 글래스 패널 스타일, 버튼/입력
스타일 — 이 앱들이 공유하는 하우스 룩이다.
"""

from __future__ import annotations

import base64
from pathlib import Path

from fet_app.constants import ACCENT

_ROOT = Path(__file__).resolve().parent.parent
_FONTS_DIR = _ROOT / "static" / "fonts"

# Myriad Pro: 표준 너비(standard width) 정체·이탤릭 5굵기.
# (weight, style, 파일, local() 이름)
_MYRIAD_FACES = [
    (300, "normal", "MyriadPro-Light.otf", "Myriad Pro Light"),
    (400, "normal", "MyriadPro-Regular.otf", "Myriad Pro"),
    (600, "normal", "MyriadPro-Semibold.otf", "Myriad Pro Semibold"),
    (700, "normal", "MyriadPro-Bold.otf", "Myriad Pro Bold"),
    (900, "normal", "MyriadPro-Black.otf", "Myriad Pro Black"),
    (300, "italic", "MyriadPro-LightIt.otf", "Myriad Pro Light Italic"),
    (400, "italic", "MyriadPro-It.otf", "Myriad Pro Italic"),
    (600, "italic", "MyriadPro-SemiboldIt.otf", "Myriad Pro Semibold Italic"),
    (700, "italic", "MyriadPro-BoldIt.otf", "Myriad Pro Bold Italic"),
    (900, "italic", "MyriadPro-BlackIt.otf", "Myriad Pro Black Italic"),
]
_PRETENDARD_WEIGHTS = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _font_face_css() -> str:
    """Myriad Pro(otf) + Pretendard(woff2) 를 base64 로 인라인한 @font-face 모음.

    ``static/fonts/`` 에 파일이 없으면 해당 굵기만 조용히 생략한다 -> 브라우저가
    font-family 스택의 다음 폰트로 자연 폴백한다 (하드 실패 없음).
    """
    faces: list[str] = []
    for weight, style, filename, local_name in _MYRIAD_FACES:
        path = _FONTS_DIR / filename
        if not path.is_file():
            continue
        data = _b64(path)
        faces.append(
            f"@font-face{{font-family:'Myriad Pro';font-weight:{weight};"
            f"font-style:{style};font-display:swap;"
            f"src:local('{local_name}'),url(data:font/otf;base64,{data}) format('opentype');}}"
        )
    for weight, name in _PRETENDARD_WEIGHTS.items():
        path = _FONTS_DIR / f"Pretendard-{name}.woff2"
        if not path.is_file():
            continue
        data = _b64(path)
        faces.append(
            f"@font-face{{font-family:'Pretendard';font-weight:{weight};font-display:swap;"
            f"src:local('Pretendard {name}'),url(data:font/woff2;base64,{data}) format('woff2');}}"
        )
    return "<style>\n" + "\n".join(faces) + "\n</style>"


def _app_css() -> str:
    """리퀴드 글래스 패널 + 버튼/입력 스타일 (하우스 룩).

    photodetector-app 의 제목/로고/배경 이미지·매뉴얼 드로어·팔레트 피커 전용
    셀렉터는 이 앱에 해당 UI 가 없으므로 제외했다.
    """
    return f"""
<style>
html, body, [class*="css"], .stApp, button, input, textarea, select {{
    font-family: 'Myriad Pro', 'Pretendard', 'Nanum Gothic', -apple-system, sans-serif !important;
}}

/* 배경 이미지 에셋(liquid_bg.jpg)은 이 저장소에 없으므로 그라데이션으로 대체 */
.stApp {{
    background: linear-gradient(135deg, #fdf0ec 0%, #f7f7fb 100%);
    background-attachment: fixed;
    color: #1c1c1e;
}}

/* 컨테이너 투명화 */
[data-testid="stHeader"], [data-testid="stToolbar"] {{ background: transparent !important; }}
[data-testid="stAppViewContainer"], .main .block-container {{ background: transparent !important; }}

/* 밀도: 기본 상단 여백이 과해서 한 화면 정보량을 깎는다 */
.main .block-container, [data-testid="stAppViewContainer"] .block-container {{
    padding-top: 2rem !important;
    padding-bottom: 0.6rem !important;
    padding-left: 1.6rem !important;
    padding-right: 1.6rem !important;
    max-width: 100% !important;
}}

/* Glassmorphism — 폼/익스팬더/팝오버를 리퀴드 글래스 패널로 */
[data-testid="stForm"],
[data-testid="stExpander"],
[data-testid="stPopoverBody"] {{
    background: rgba(255,255,255,0.15);
    backdrop-filter: blur(48px) saturate(150%);
    -webkit-backdrop-filter: blur(48px) saturate(150%);
    border: 1px solid rgba(255,255,255,0.35);
    border-radius: 20px;
    box-shadow: 0 12px 32px rgba(0,0,0,0.05);
    padding: 20px 22px;
}}

/* 세로 간격 압축 */
[data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"] {{ gap: 0.5rem !important; }}

/* 파일 업로더 드롭존 */
[data-testid="stFileUploader"] section {{
    background: rgba(255,255,255,0.25);
    border: 2px dashed {ACCENT};
    border-radius: 16px;
}}

/* ---------------- 입력/버튼 ---------------- */
[data-baseweb="select"] > div, .stNumberInput input, .stTextInput input {{
    background: rgba(255,255,255,0.35) !important;
    border-radius: 10px !important;
}}
.stButton > button, .stDownloadButton > button {{
    background: rgba(255,255,255,0.35);
    border: 1px solid rgba(255,255,255,0.5);
    border-radius: 12px; font-weight: 600; color: #1c1c1e;
    transition: all 0.18s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
    transform: translateY(-2px);
    border-color: {ACCENT}; color: {ACCENT};
    box-shadow: 0 6px 18px rgba(237,84,43,0.18);
}}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {ACCENT}, #f68b21);
    color: white; border: none;
}}
.stButton > button[kind="primary"]:hover {{ color: white; opacity: 0.94; }}

h1, h2, h3, h4, p, label, span {{ text-shadow: none; }}
</style>
"""


# 스펙 §6.2 — CSS 미디어 쿼리만으로 4단계. JS 불필요.
# 3열 컬럼은 layout.py 가 st.columns 로 만들고, 여기서 폭을 덮어쓴다.
RESPONSIVE_CSS = """
<style>
/* 본문 최대 폭: 27" QHD 에서 약 3/4 만 쓰게 해 좌우 시선 이동을 억제한다 */
@media (min-width: 1500px) {
  section.main > div.block-container { max-width: 1760px; margin: 0 auto; }
}
@media (max-width: 1499px) {
  section.main > div.block-container { max-width: 100%; }
}

/* 3열: 편집 패널 / 그래프(신축) / 소자 리스트.
   Streamlit 은 st.columns 에 클래스를 붙일 수 없으므로, 첫 컬럼에 심어둔
   마커 <div class="fet-shell-anchor"> 를 :has() 로 찾아 그 부모를 잡는다. */
div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(1) {
  flex: 0 0 clamp(260px, 20vw, 340px);
  min-width: 260px;
}
div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(2) {
  flex: 1 1 auto;
  min-width: 0;
}
div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(3) {
  flex: 0 0 clamp(180px, 13vw, 230px);
  min-width: 180px;
}

/* 900~1150px: 소자 리스트 열을 접는다 (layout.py 가 같은 폭에서 사이드바로 옮겨 렌더한다) */
@media (max-width: 1149px) {
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(3) {
    display: none;
  }
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(1) {
    flex: 0 0 280px; min-width: 280px;
  }
}

/* 900px 미만: 전부 세로 스택 */
@media (max-width: 899px) {
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) { flex-direction: column; }
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"] {
    flex: 1 1 100% !important; min-width: 0 !important; width: 100% !important;
  }
  div[data-testid="stHorizontalBlock"]:has(.fet-graphs-anchor) { flex-direction: column; }
}

/* 소자 리스트는 독립 스크롤 */
.fet-device-list { max-height: 62vh; overflow-y: auto; overflow-x: hidden; }
</style>
"""


def base_css() -> str:
    """폰트 임베드 + 앱 스타일 + 반응형."""
    return _font_face_css() + _app_css() + RESPONSIVE_CSS


def inject() -> None:
    import streamlit as st

    st.markdown(base_css(), unsafe_allow_html=True)
