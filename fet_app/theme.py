"""전역 테마: CSS 임베드 (스펙 §6). 폰트를 base64 로 인라인하고, 리퀴드 글래스
패널/버튼/입력 스타일을 적용한다. 반응형 3열 레이아웃은 ``RESPONSIVE_CSS`` 가
맡는다 — ``fet_app.ui.layout`` 이 만드는 3열 블록을 ``:has(.fet-shell-anchor)``
로, ``fet_app.ui.summary`` 가 만드는 그래프 2열 블록을
``:has(.fet-graphs-anchor)`` 로 찾아 폭/스택 방향을 건다 (스펙 §6.2, §6.1).

포팅 출처: ``photodetector-app/pd_app/theme.py``. 폰트 ``@font-face``, 리퀴드
글래스 패널 스타일, 버튼/입력 스타일, 배경/로고 이미지는 이식했다 — 이 앱들이
공유하는 하우스 룩이다. 그 앱의 매뉴얼 드로어 JS, ResizeObserver 뷰포트 바인딩
JS, 팔레트 피커 전용 셀렉터(``st-key-pd_*``)는 이식하지 않았다 — 이 앱에는
해당 UI 가 없고, §6.2 는 CSS 미디어 쿼리만으로 4단계 반응형을 처리하므로 JS
관측 루프가 필요 없다.
"""

from __future__ import annotations

from pathlib import Path

from fet_app.constants import ACCENT

_ROOT = Path(__file__).resolve().parent.parent
_FONTS_DIR = _ROOT / "static" / "fonts"

_STATIC_DIR = _ROOT / "static"
_BG_PATH = _STATIC_DIR / "liquid_bg.jpg"
_LOGO_PATH = _STATIC_DIR / "logo.png"
_HAS_BG = _BG_PATH.is_file()
_HAS_LOGO = _LOGO_PATH.is_file()
_BG_URL = "app/static/liquid_bg.jpg"
_LOGO_URL = "app/static/logo.png"

_BG_LAYER = (
    f"linear-gradient(rgba(255,255,255,0.72), rgba(255,255,255,0.82)), url('{_BG_URL}')"
    if _HAS_BG else
    "linear-gradient(135deg, #fdf0ec 0%, #f7f7fb 100%)"
)


def logo_url() -> str | None:
    """헤더 로고 URL. 에셋이 없으면 None (레이아웃이 로고를 생략한다)."""
    return _LOGO_URL if _HAS_LOGO else None

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

    photodetector-app 의 매뉴얼 드로어·팔레트 피커 전용 셀렉터는 이 앱에
    해당 UI 가 없으므로 제외했다. 제목/로고/배경 이미지는 이식했다.
    """
    return f"""
<style>
html, body, [class*="css"], .stApp, button, input, textarea, select {{
    font-family: 'Myriad Pro', 'Pretendard', 'Nanum Gothic', -apple-system, sans-serif !important;
}}

.stApp {{
    background: {_BG_LAYER};
    background-size: cover;
    background-attachment: fixed;
    background-position: center;
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

/* 헤더 문서 버튼 — NBEDL Exp Assistant 의 사용설명서(주황)/분석방법(청록) 배색을 그대로 옮겼다 */
.st-key-doc_manual_btn button {{
    background: linear-gradient(135deg, #ed542b, #f68b21) !important;
    color: white !important;
    border: none !important;
}}
.st-key-doc_manual_btn button:hover {{ opacity: 0.9; }}

.st-key-doc_methods_btn button {{
    background: linear-gradient(135deg, #0c8599, #20c997) !important;
    color: white !important;
    border: none !important;
}}
.st-key-doc_methods_btn button:hover {{ opacity: 0.9; }}

/* 제목 줄. h3 기본 마진이 남아 있으면 vertical_alignment="center" 를 걸어도
   버튼들과 눈으로 봤을 때 높이가 안 맞는다 — margin:0 으로 제거한다.
   photodetector-app 의 .pd-title-glass(로고+제목을 flex 로 가운데 정렬,
   img{{height}}, h2{{margin:0}}) 와 같은 패턴이다. */
.fet-title {{
    display: flex; align-items: center; gap: 10px; margin: 0;
}}
.fet-title img {{ height: 32px; width: auto; flex-shrink: 0; }}
.fet-title h3 {{
    margin: 0; padding: 0; white-space: nowrap;
}}

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
/* 편집 패널은 이제 탭 4개(정보/축/인셋/서식)를 담는다 — 축 탭의 행 하나가
   label/auto/min/max/major/minor 6컬럼이라 340px 상한으로는 비좁았다. */
div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(1) {
  flex: 0 0 clamp(340px, 30vw, 480px);
  min-width: 340px;
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
  /* 편집 패널이 탭 4개를 담으므로 기본 최소폭(340px)과 일관되게 유지한다. */
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(1) {
    flex: 0 0 340px; min-width: 340px;
  }
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(3) {
    flex: 1 1 100%; min-width: 0;
  }
}

/* 헤더 행: 제목·문서 버튼 두 개는 내용 크기로 왼쪽에 붙고, 업로더(4번째 칸)가
   남는 폭을 전부 가져간다(파일을 자주 올리니 널찍하게). 넷 다 같은
   st.columns() 의 형제라 gap 이 전부 동일해서 "일정 간격"이 자연히 맞는다.

   이전 버전은 문서 버튼 두 개를 header[1] 안에 st.columns(2) 로 중첩해
   넣고, 그 안쪽 블록에만 마커를 심어 :has(.fet-doc-buttons-anchor) 로 잡았다.
   :has(SELECTOR) 는 SELECTOR 가 '어느 깊이의 자손이든' 있으면 매치하므로
   (직계 자식으로 한정되지 않는다), 마커를 감싼 바깥쪽 헤더 행까지 같이
   매치돼 flex:0 0 auto 가 제목·업로더 칸에도 걸렸다 — 제목이 오른쪽으로
   끌려가고 업로더 폭이 줄어드는 회귀였다. 지금은 중첩 자체를 없애 제목·
   버튼 두 개·업로더를 하나의 st.columns() 로 평평하게 뒀으므로, 마커를
   담는 stHorizontalBlock 이 이 행 하나뿐이라 :has() 가 잘못된 조상을 잡을
   여지가 없다(3열 셸에 쓰는 fet-shell-anchor 와 같은, 검증된 패턴). */
div[data-testid="stHorizontalBlock"]:has(.fet-header-row-anchor) {
  align-items: center;
}
div[data-testid="stHorizontalBlock"]:has(.fet-header-row-anchor) > div[data-testid="stColumn"]:nth-child(1),
div[data-testid="stHorizontalBlock"]:has(.fet-header-row-anchor) > div[data-testid="stColumn"]:nth-child(2),
div[data-testid="stHorizontalBlock"]:has(.fet-header-row-anchor) > div[data-testid="stColumn"]:nth-child(3) {
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
}
div[data-testid="stHorizontalBlock"]:has(.fet-header-row-anchor) > div[data-testid="stColumn"]:nth-child(4) {
  flex: 1 1 auto !important;
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


def apply_ui_zoom() -> None:
    """화면 폭에 따라 전체 UI 를 CSS zoom 으로 축소한다.

    그래프 하나만 줄이는 것으로는 부족했다 — 좌우 패널 폭·폰트·여백은 그대로라
    노트북 화면(1280~1440px)에서 우측 소자 리스트가 화면 밖으로 밀려났다.
    NBEDL Exp Assistant(C:\\Users\\mintj\\NBEDL Exp Assistant\\app.py,
    apply_ui_zoom())에서 검증된 같은 기법을 그대로 옮겼다: 기준 폭(DESIGN)보다
    좁으면 축소하고, 넓으면 확대하지 않고 1.0 으로 고정한다.

    body 전체에 zoom 을 걸면 Streamlit 내부의 100vh 기반 레이아웃과 충돌해
    화면이 위로 밀린다(NBEDL 에서 이미 겪은 문제) — 그래서 vh 의존이 없는
    .stMainBlockContainer 에만 건다.

    st.components.v1.html 은 Streamlit 이 한때 폐기 예정으로 표시했던 API 지만,
    이 글을 쓰는 시점 설치된 1.61.1 에서 여전히 동작하고, 같은 기법을 쓰는
    NBEDL Exp Assistant 도 실제로 배포되어 동작 중이다.
    """
    import streamlit.components.v1 as components

    components.html("""
<script>
(function() {
  try {
    var win = window.parent, doc = win.document;
    var DESIGN = 1440, MIN = 0.85, MAX = 1.0;
    var ID = 'fet-zoom-style';
    var styleEl = doc.getElementById(ID);
    if (!styleEl) { styleEl = doc.createElement('style'); styleEl.id = ID; doc.head.appendChild(styleEl); }
    win.__fetApplyZoom = function() {
      var z = win.innerWidth / DESIGN;
      z = Math.max(MIN, Math.min(MAX, z));
      styleEl.textContent = '[data-testid="stMain"] .stMainBlockContainer { zoom: ' + z + '; }';
    };
    win.__fetApplyZoom();
    if (!win.__fetZoomBound) {
      win.__fetZoomBound = true;
      win.addEventListener('resize', function() { win.__fetApplyZoom(); });
    }
  } catch (err) { /* 무시 */ }
})();
</script>
""", height=0)
