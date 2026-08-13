from fet_app.markup import apply_markup


def test_empty_text_returns_empty_string():
    assert apply_markup("") == ""
    assert apply_markup(None) == ""


def test_bold():
    assert apply_markup("**V**") == "<b>V</b>"


def test_italic():
    assert apply_markup("*V*") == "<i>V</i>"


def test_superscript_requires_braces():
    assert apply_markup("V^{0.5}") == "V<sup>0.5</sup>"
    assert apply_markup("V^0.5") == "V^0.5"   # 중괄호 없으면 리터럴


def test_subscript_requires_braces():
    assert apply_markup("V_{G}") == "V<sub>G</sub>"
    assert apply_markup("V_G") == "V_G"       # 중괄호 없으면 리터럴


def test_color_span():
    assert apply_markup("{#FF0000|hot}") == '<span style="color:#FF0000">hot</span>'


def test_escape_next_char():
    assert apply_markup(r"\*\*V\*\*") == "**V**"
    assert apply_markup(r"V\_{G}") == "V_{G}"


def test_html_escaped_before_expansion_so_user_text_cant_break_plotly():
    assert apply_markup("<script>&</script>") == "&lt;script&gt;&amp;&lt;/script&gt;"


def test_combined_transfer_axis_titles():
    assert apply_markup("V_{G} (V)") == "V<sub>G</sub> (V)"
    assert apply_markup("|I_{D}| (A)") == "|I<sub>D</sub>| (A)"
    assert apply_markup("√|I_{D}| (A^{0.5})") == "√|I<sub>D</sub>| (A<sup>0.5</sup>)"


def test_unmatched_bold_marker_is_literal():
    assert apply_markup("**V") == "**V"
