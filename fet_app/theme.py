"""전역 테마: CSS 임베드 (스펙 §6). 폰트를 base64 로 인라인하고, 리퀴드 글래스
패널/버튼/입력 스타일을 적용한다. 반응형 3열 레이아웃은 ``RESPONSIVE_CSS`` 가
맡는다 — ``fet_app.ui.layout`` 이 만드는 3열 블록을 ``:has(.fet-shell-anchor)``
로, ``fet_app.ui.summary`` 가 만드는 그래프 2열 블록을
``:has(.fet-graphs-anchor)`` 로 찾아 폭/스택 방향을 건다 (스펙 §6.2, §6.1).

포팅 출처: ``photodetector-app/pd_app/theme.py``. 그 앱의 제목·매뉴얼 문구,
배경/로고 이미지, zoom 및 ResizeObserver 뷰포트 바인딩 JS, 팔레트 피커 전용
셀렉터(``st-key-pd_*``)는 이식하지 않았다 — 이 앱 전용 UI(Task 17/18)가 아직
없고, §6.2 는 CSS 미디어 쿼리만으로 4단계 반응형을 처리하므로 JS 관측 루프가
필요 없다. 남긴 것은 폰트 ``@font-face``, 리퀴드 글래스 패널 스타일, 버튼/입력
스타일 — 이 앱들이 공유하는 하우스 룩이다.
"""

from __future__ import annotations

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


# Streamlit 정적 서빙 경로. .streamlit/config.toml 의 enableStaticServing = true 가
# 저장소 루트의 static/ 를 여기로 노출한다.
_STATIC_URL = "app/static/fonts"


def _font_face_css() -> str:
    """Myriad Pro(otf) + Pretendard(woff2) @font-face 모음.

    폰트는 base64 로 인라인하지 않고 ``app/static/fonts/`` 에서 받아간다.
    인라인하면 CSS 가 5 MB 를 넘고, Streamlit 은 위젯을 건드릴 때마다 스크립트를
    다시 돌리므로 그 5 MB 가 매번 웹소켓으로 나가 앱이 느려진다.
    브라우저는 폰트를 캐시하므로 URL 방식은 최초 1회만 받는다.

    ``static/fonts/`` 에 파일이 없으면 해당 굵기만 조용히 생략한다 -> 브라우저가
    font-family 스택의 다음 폰트로 자연 폴백한다 (하드 실패 없음).
    """
    faces: list[str] = []
    for weight, style, filename, local_name in _MYRIAD_FACES:
        if not (_FONTS_DIR / filename).is_file():
            continue
        faces.append(
            f"@font-face{{font-family:'Myriad Pro';font-weight:{weight};"
            f"font-style:{style};font-display:swap;"
            f"src:local('{local_name}'),"
            f"url('{_STATIC_URL}/{filename}') format('opentype');}}"
        )
    for weight, name in _PRETENDARD_WEIGHTS.items():
        filename = f"Pretendard-{name}.woff2"
        if not (_FONTS_DIR / filename).is_file():
            continue
        faces.append(
            f"@font-face{{font-family:'Pretendard';font-weight:{weight};font-display:swap;"
            f"src:local('Pretendard {name}'),"
            f"url('{_STATIC_URL}/{filename}') format('woff2');}}"
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
/* 본문 최대 폭: 27" QHD 에서 약 3/4 만 쓰게 해 좌우 시선 이동을 억제한다.
   실제 Streamlit 1.61 DOM 은 <section class="stMain" data-testid="stMain">
   안에 <div class="stMainBlockContainer block-container"> 이다. 구버전
   셀렉터는 이 클래스가 아닌 다른(존재한 적 없는) main 클래스를 직계 자식
   결합자로 찾고 있었다 — 아무 것도 매치하지 못해 이 캡이 어떤 화면에서도
   적용된 적이 없었다. */
@media (min-width: 1500px) {
  [data-testid="stMain"] .stMainBlockContainer { max-width: 1760px; margin: 0 auto; }
}
@media (max-width: 1499px) {
  [data-testid="stMain"] .stMainBlockContainer { max-width: 100%; }
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

/* 1150px 미만: 3열을 유지하기엔 좁다. 소자 리스트(3번째 컬럼)를 숨기던
   이전 규칙은 layout.py 가 같은 폭에서 사이드바로 옮겨 그린다고 주장했지만
   그런 코드는 없다 (fet_app/ 어디에도 sidebar 렌더링이 없다) — 그래서 소자
   전환/검색/전역 W·L·ε_r·d/진단 임계값/전체 요약 버튼/내보내기 패널 전체가
   이 폭 아래에서 통째로 사라졌다. 숨기는 대신 flex-wrap 으로 3번째 컬럼만
   다음 줄로 떨어뜨려 세로로 쌓는다: 스크롤해서 도달하는 편이 아예 닿지 않는
   것보다 낫다. 편집 패널(1열)은 여전히 그래프(2열)와 한 줄을 공유하므로
   고정 폭 오버라이드가 계속 의미가 있어 남긴다. */
@media (max-width: 1149px) {
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) {
    flex-wrap: wrap;
  }
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(1) {
    flex: 0 0 280px; min-width: 280px;
  }
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(3) {
    flex: 1 1 100%; min-width: 0;
  }
}

/* 900px 미만: 전부 세로 스택 */
@media (max-width: 899px) {
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) { flex-direction: column; }
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"] {
    flex: 1 1 100% !important; min-width: 0 !important; width: 100% !important;
  }
  div[data-testid="stHorizontalBlock"]:has(.fet-graphs-anchor) { flex-direction: column; }
  div[data-testid="stHorizontalBlock"]:has(.fet-graphs-anchor) > div[data-testid="stColumn"] {
    flex: 1 1 100% !important; min-width: 0 !important; width: 100% !important;
  }
}
</style>
"""


def base_css() -> str:
    """폰트 임베드 + 앱 스타일 + 반응형."""
    return _font_face_css() + _app_css() + RESPONSIVE_CSS


def inject() -> None:
    import streamlit as st

    st.markdown(base_css(), unsafe_allow_html=True)
