import copy

import plotly.graph_objects as go

from fet_app.constants import DEFAULTS
from fet_app.figure_common import (DPI, apply_inset_text, axis_layout, domains,
                                   new_figure, plot_px_size, px_size)


def test_px_size_uses_96_dpi():
    geom = DEFAULTS["geom"]
    assert px_size(geom, 1.0) == (int(10 * DPI), int(8 * DPI)) == (960, 768)


def test_px_size_scales():
    assert px_size(DEFAULTS["geom"], 0.5) == (480, 384)


def test_domains_from_percentages():
    geom = {"graph_left_pct": 20.0, "graph_top_pct": 10.0,
            "graph_width_pct": 60.0, "graph_height_pct": 70.0}
    x_dom, y_dom = domains(geom)
    assert x_dom == [0.2, 0.8]
    # Top 은 위에서부터이므로 y_domain = [1-(T+H), 1-T]
    assert y_dom == [0.2, 0.9]


def test_axis_layout_paper_conventions():
    cfg = copy.deepcopy(DEFAULTS["transfer_axes"]["y"])
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0)
    assert lay["type"] == "log"
    assert lay["mirror"] is True          # 4면 박스
    assert lay["ticks"] == "inside"
    assert lay["showgrid"] is False
    assert lay["exponentformat"] == "E"   # 1E-11 형식
    assert lay["showexponent"] == "all"
    assert lay["zeroline"] is False


def test_axis_layout_scales_fonts():
    lay = axis_layout(DEFAULTS["transfer_axes"]["x"], DEFAULTS["style"], k=0.5)
    assert lay["title"]["font"]["size"] == 15   # 30 * 0.5
    assert lay["tickfont"]["size"] == 15


def test_axis_layout_auto_range_has_no_padding():
    cfg = dict(DEFAULTS["transfer_axes"]["x"])
    cfg["auto"] = True
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0, data_min=-60.0, data_max=20.0)
    assert lay["range"] == [-60.0, 20.0]
    assert lay["autorange"] is False


def test_axis_layout_manual_range_wins():
    cfg = dict(DEFAULTS["transfer_axes"]["x"])
    cfg.update({"auto": False, "min": -50.0, "max": 10.0})
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0, data_min=-60.0, data_max=20.0)
    assert lay["range"] == [-50.0, 10.0]


def test_new_figure_is_white_and_unmargined():
    fig = new_figure(DEFAULTS["geom"], k=1.0)
    assert fig.layout.paper_bgcolor == "#FFFFFF"
    assert fig.layout.plot_bgcolor == "#FFFFFF"
    assert fig.layout.margin.l == 0
    assert fig.layout.showlegend is False


def test_axis_layout_title_runs_through_markup():
    """FIX 1 — 축 제목 마크업(`_{...}`/`^{...}`)이 Plotly HTML 로 확장돼야 한다."""
    cfg = dict(DEFAULTS["transfer_axes"]["x"])
    cfg["title"] = "V_{G} (V)"
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0)
    assert lay["title"]["text"] == "V<sub>G</sub> (V)"


def test_apply_inset_text_runs_through_markup():
    fig = go.Figure()
    inset = dict(DEFAULTS["insets"]["sample"])
    apply_inset_text(fig, "**Sample**-1_{a}", inset, DEFAULTS["style"], k=1.0)
    assert fig.layout.annotations[0].text == "<b>Sample</b>-1<sub>a</sub>"


def test_apply_inset_text_skips_empty_text():
    fig = go.Figure()
    inset = dict(DEFAULTS["insets"]["sample"])
    apply_inset_text(fig, "", inset, DEFAULTS["style"], k=1.0)
    assert fig.layout.annotations == ()


def test_plot_px_size_matches_domain_fraction_of_page():
    geom = DEFAULTS["geom"]
    w, h = px_size(geom, 1.0)
    x_dom, y_dom = domains(geom)
    plot_w, plot_h = plot_px_size(geom, 1.0)
    assert plot_w == w * (x_dom[1] - x_dom[0])
    assert plot_h == h * (y_dom[1] - y_dom[0])


def test_plot_px_size_scales_with_k():
    geom = DEFAULTS["geom"]
    full = plot_px_size(geom, 1.0)
    half = plot_px_size(geom, 0.5)
    assert half[0] == full[0] / 2
    assert half[1] == full[1] / 2
