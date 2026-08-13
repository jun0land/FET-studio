import copy

import numpy as np
import pandas as pd

from fet_app.constants import DEFAULTS
from fet_app.curves import TransferCurve
from fet_app.figure_transfer import transfer_figure
from fet_app.metrics import transfer_metrics
from fet_app.params import DeviceParams

PARAMS = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)


def _settings(**over):
    s = {
        "geom": copy.deepcopy(DEFAULTS["geom"]),
        "style": copy.deepcopy(DEFAULTS["style"]),
        "axes": copy.deepcopy(DEFAULTS["transfer_axes"]),
        "trace": copy.deepcopy(DEFAULTS["transfer_style"]),
        "insets": copy.deepcopy(DEFAULTS["insets"]),
    }
    s.update(over)
    return s


def _curve(dual=True):
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = -np.maximum(2e-8 * (v_g + 12.0) ** 2 * (v_g < -12.0), 1e-12)
    fwd = pd.DataFrame({"V_G": v_g, "I_G": np.full_like(v_g, 1e-11), "I_D": i_d})
    rev = fwd.iloc[::-1].reset_index(drop=True) if dual else None
    return TransferCurve(forward=fwd, reverse=rev, v_ds=-60.0, dual=dual)


def test_left_axis_title_uses_absolute_value_symbol():
    """FET 에서는 절댓값 기호를 쓴다 (스펙 §5.2 — photodetector 규약을 뒤집은 항목).

    기본 제목은 인라인 마크업(`_{...}`/`^{...}`)으로 정의되어 있고, axis_layout 이
    apply_markup 을 거쳐 Plotly HTML(<sub>/<sup>)로 렌더한다 (FIX 1)."""
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    assert fig.layout.yaxis.title.text == "|I<sub>D</sub>| (A)"
    assert fig.layout.yaxis2.title.text == "√|I<sub>D</sub>| (A<sup>0.5</sup>)"
    assert fig.layout.xaxis.title.text == "V<sub>G</sub> (V)"


def test_second_axis_overlays_on_right():
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    assert fig.layout.yaxis2.side == "right"
    assert fig.layout.yaxis2.overlaying == "y"
    assert fig.layout.yaxis.type == "log"
    assert fig.layout.yaxis2.type == "linear"


def test_forward_solid_reverse_dashed():
    c = _curve(dual=True)
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    named = {t.name: t for t in fig.data}
    assert named["forward |I_D|"].line.dash in (None, "solid")
    assert named["reverse |I_D|"].line.dash == "dash"
    assert named["forward |I_D|"].line.color == named["reverse |I_D|"].line.color


def test_reverse_hidden_when_toggled_off():
    c = _curve(dual=True)
    s = _settings()
    s["trace"]["show_reverse"] = False
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    assert not any("reverse" in (t.name or "") for t in fig.data)


def test_log_axis_plots_absolute_current():
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    trace = next(t for t in fig.data if t.name == "forward |I_D|")
    assert np.all(np.asarray(trace.y) > 0)


def test_fit_line_and_vth_marker_present():
    c = _curve()
    m = transfer_metrics(c, PARAMS)
    fig = transfer_figure(c, m, _settings())
    names = [t.name for t in fig.data]
    assert "fit" in names
    assert "V_th" in names
    fit_trace = next(t for t in fig.data if t.name == "fit")
    assert fit_trace.yaxis == "y2"


def test_fit_hidden_when_toggled_off():
    c = _curve()
    s = _settings()
    s["trace"]["show_fit"] = False
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    assert "fit" not in [t.name for t in fig.data]


def test_gate_current_optional():
    c = _curve()
    s = _settings()
    assert "|I_G|" not in [t.name for t in transfer_figure(c, transfer_metrics(c, PARAMS), s).data]
    s["trace"]["show_gate_current"] = True
    assert "|I_G|" in [t.name for t in transfer_figure(c, transfer_metrics(c, PARAMS), s).data]


def test_no_plotly_legend():
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    assert fig.layout.showlegend is False


def test_custom_axis_title_markup_expands_to_html():
    """사용자가 축 제목에 마크업을 쓰면 실제로 <sub>/<sup>/<b>로 확장돼야 한다 (FIX 1)."""
    c = _curve()
    s = _settings()
    s["axes"]["x"]["title"] = "**V**_{DS} (^{n}V)"
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    assert fig.layout.xaxis.title.text == "<b>V</b><sub>DS</sub> (<sup>n</sup>V)"


def test_scale_shrinks_figure_and_fonts():
    c = _curve()
    m = transfer_metrics(c, PARAMS)
    full = transfer_figure(c, m, _settings(), k=1.0)
    half = transfer_figure(c, m, _settings(), k=0.5)
    assert half.layout.width == full.layout.width // 2
    assert half.layout.xaxis.title.font.size == full.layout.xaxis.title.font.size // 2
