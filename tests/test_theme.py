from pathlib import Path

from fet_app.theme import RESPONSIVE_CSS, base_css

_ROOT = Path(__file__).resolve().parent.parent


def test_max_width_cap_targets_real_streamlit_dom():
    """1760px 캡은 실제 Streamlit 1.61 DOM 을 잡아야 한다:
    <section class="stMain" data-testid="stMain"> 안의
    <div class="stMainBlockContainer block-container">.
    ``section.main > div.block-container`` 는 이 번들에 존재한 적이 없는
    셀렉터라 조용히 아무것도 매치하지 못했다 (I5)."""
    css = RESPONSIVE_CSS
    assert "max-width: 1760px" in css
    assert '[data-testid="stMain"] .stMainBlockContainer' in css


def test_section_main_selector_is_gone():
    """section.main 은 실제 DOM 에 없다 — 이 셀렉터가 남아 있으면 다시 no-op."""
    assert "section.main" not in RESPONSIVE_CSS


def test_responsive_css_has_all_four_breakpoints():
    css = RESPONSIVE_CSS
    for bp in ("1500px", "1150px", "900px"):
        assert bp in css, bp


def test_panel_widths_use_clamp():
    css = RESPONSIVE_CSS
    assert "clamp(340px, 30vw, 480px)" in css
    assert "clamp(180px, 13vw, 230px)" in css


def test_columns_are_targeted_via_anchor_marker():
    """st.columns 에 클래스를 못 붙이므로 마커를 :has() 로 찾는다."""
    assert ":has(.fet-shell-anchor)" in RESPONSIVE_CSS


def test_no_column_is_ever_hidden_with_display_none():
    """C2: 1150px 미만에서 3번째 컬럼(소자 리스트+내보내기)을 display:none 으로
    숨기던 규칙은 그 폭에서 콘텐츠 전체를 접근 불가로 만들었다. 어떤 컬럼도
    어떤 브레이크포인트에서도 display:none 이 되어서는 안 된다."""
    assert "display: none" not in RESPONSIVE_CSS
    assert "display:none" not in RESPONSIVE_CSS


def test_graphs_anchor_referenced_in_css_and_emitted_by_summary():
    """I7: .fet-graphs-anchor 가 CSS 에서 쓰이려면 summary.py 가 실제로
    그 마커를 그래프 2열 블록의 첫 컬럼에 심어야 한다."""
    assert ":has(.fet-graphs-anchor)" in RESPONSIVE_CSS
    summary_src = (_ROOT / "fet_app" / "ui" / "summary.py").read_text(encoding="utf-8")
    assert "fet-graphs-anchor" in summary_src


def test_shell_anchor_emitted_by_layout():
    layout_src = (_ROOT / "fet_app" / "ui" / "layout.py").read_text(encoding="utf-8")
    assert "fet-shell-anchor" in layout_src


def test_base_css_embeds_fonts():
    css = base_css()
    assert "@font-face" in css
    assert "Myriad Pro" in css
    assert "Pretendard" in css


def test_base_css_includes_responsive():
    assert RESPONSIVE_CSS in base_css()
