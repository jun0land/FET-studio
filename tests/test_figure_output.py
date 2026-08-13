import copy

import numpy as np
import pandas as pd

from fet_app.constants import ACCENT, DEFAULTS
from fet_app.curves import OutputBlock, OutputCurve
from fet_app.figure_output import gradient_colors, output_figure, relative_luminance


def _settings(**over):
    s = {
        "geom": copy.deepcopy(DEFAULTS["geom"]),
        "style": copy.deepcopy(DEFAULTS["style"]),
        "axes": copy.deepcopy(DEFAULTS["output_axes"]),
        "trace": copy.deepcopy(DEFAULTS["output_style"]),
        "insets": copy.deepcopy(DEFAULTS["insets"]),
    }
    s.update(over)
    return s


def _curve(n=4, dual=True):
    v_d = np.arange(0, -61, -1, dtype=float)
    blocks = []
    for i in range(n):
        v_g = -20.0 * i
        i_d = -1e-6 * (i + 1) * np.tanh(v_d / -20.0)
        fwd = pd.DataFrame({"V_D": v_d, "I_D": i_d, "I_G": np.full_like(v_d, 1e-12)})
        rev = fwd.iloc[::-1].reset_index(drop=True) if dual else None
        blocks.append(OutputBlock(v_g=v_g, forward=fwd, reverse=rev))
    return OutputCurve(blocks=blocks)


def test_gradient_returns_requested_count():
    assert len(gradient_colors(ACCENT, 4)) == 4
    assert gradient_colors(ACCENT, 1) == [ACCENT]
    assert gradient_colors(ACCENT, 0) == []


def test_gradient_luminance_is_strictly_decreasing():
    """흑백 인쇄에서도 순서가 유지되어야 한다 (스펙 §5.3)."""
    lums = [relative_luminance(c) for c in gradient_colors(ACCENT, 6)]
    assert all(lums[i] > lums[i + 1] for i in range(len(lums) - 1)), lums


def test_gradient_preserves_hue_family():
    colors = gradient_colors("#ed542b", 4)
    for c in colors:
        r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
        assert r >= g >= b, c   # 주황 계열 유지


def test_output_axes_are_linear():
    """기본 제목은 마크업(`V_{D}`/`I_{D}`)이며 axis_layout 이 <sub>로 렌더한다 (FIX 1)."""
    fig = output_figure(_curve(), _settings())
    assert fig.layout.yaxis.type == "linear"
    assert fig.layout.xaxis.type == "linear"
    assert fig.layout.xaxis.title.text == "V<sub>D</sub> (V)"
    assert fig.layout.yaxis.title.text == "I<sub>D</sub> (A)"


def test_one_trace_pair_per_block():
    fig = output_figure(_curve(n=4), _settings())
    fwd = [t for t in fig.data if "forward" in (t.name or "")]
    rev = [t for t in fig.data if "reverse" in (t.name or "")]
    assert len(fwd) == 4 and len(rev) == 4


def test_block_colors_match_gradient_order():
    s = _settings()
    fig = output_figure(_curve(n=4), s)
    expected = gradient_colors(s["trace"]["base_color"], 4,
                               s["trace"]["lightness_min"], s["trace"]["lightness_max"])
    actual = [t.line.color for t in fig.data if "forward" in (t.name or "")]
    assert actual == expected


def test_manual_color_override():
    s = _settings()
    s["trace"]["manual_colors"] = {"-40": "#123456"}
    fig = output_figure(_curve(n=4), s)
    t = next(t for t in fig.data if t.name == "V_G = -40 V forward")
    assert t.line.color == "#123456"


def test_reverse_dashed_same_color():
    fig = output_figure(_curve(n=2), _settings())
    f = next(t for t in fig.data if t.name == "V_G = 0 V forward")
    r = next(t for t in fig.data if t.name == "V_G = 0 V reverse")
    assert r.line.dash == "dash"
    assert r.line.color == f.line.color


def test_inset_legend_lists_gate_voltages():
    fig = output_figure(_curve(n=4), _settings())
    texts = " ".join(a.text for a in fig.layout.annotations)
    for v in ("0", "-20", "-40", "-60"):
        assert f"V_G = {v} V" in texts


def test_no_plotly_legend():
    assert output_figure(_curve(), _settings()).layout.showlegend is False
