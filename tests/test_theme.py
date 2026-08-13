from fet_app.theme import RESPONSIVE_CSS, base_css


def test_responsive_css_has_all_four_breakpoints():
    css = RESPONSIVE_CSS
    assert "max-width: 1760px" in css.replace(" ", " ")
    for bp in ("1500px", "1150px", "900px"):
        assert bp in css, bp


def test_panel_widths_use_clamp():
    css = RESPONSIVE_CSS
    assert "clamp(260px, 20vw, 340px)" in css
    assert "clamp(180px, 13vw, 230px)" in css


def test_columns_are_targeted_via_anchor_marker():
    """st.columns 에 클래스를 못 붙이므로 마커를 :has() 로 찾는다."""
    assert ":has(.fet-shell-anchor)" in RESPONSIVE_CSS


def test_base_css_embeds_fonts():
    css = base_css()
    assert "@font-face" in css
    assert "Myriad Pro" in css
    assert "Pretendard" in css


def test_base_css_includes_responsive():
    assert RESPONSIVE_CSS in base_css()
