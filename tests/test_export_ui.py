"""소자별 개별 다운로드 (스펙 §7 / MANUAL.md §5, export_ui.py).

이 저장소에는 Streamlit AppTest 인프라가 없다(tests/test_ui_helpers.py 처럼
순수 헬퍼 함수와 소스 텍스트 확인으로 UI 로직을 검증하는 관례를 따른다).
export_ui.render() 자체는 st.button/session_state 상호작용이라 단위 테스트로
직접 구동하기 어려우므로, 실제 판단 로직을 순수 함수로 뽑아 테스트한다.
"""

from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from fet_app import export
from fet_app.curves import OutputBlock, OutputCurve, TransferCurve
from fet_app.grouping import DeviceGroup, MeasurementRun
from fet_app.params import DeviceParams
from fet_app.state import AppState
from fet_app.ui import export_ui

PARAMS = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)


def _transfer():
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = -np.maximum(2e-8 * (v_g + 12.0) ** 2 * (v_g < -12.0), 1e-12)
    df = pd.DataFrame({"V_G": v_g, "I_G": np.full_like(v_g, 1e-11), "I_D": i_d})
    return TransferCurve(forward=df, reverse=df.iloc[::-1].reset_index(drop=True),
                         v_ds=-60.0, dual=True)


def _output():
    v_d = np.arange(0, -61, -1, dtype=float)
    block = OutputBlock(v_g=-20.0, forward=pd.DataFrame({
        "V_D": v_d, "I_D": -1e-6 * np.tanh(v_d / -20), "I_G": np.full_like(v_d, 1e-12),
    }), reverse=None)
    return OutputCurve(blocks=[block])


def _group(name="1-1", with_transfer=True, with_output=True):
    transfer_sources, output_sources = {}, {}
    transfer_file = output_file = None
    if with_transfer:
        transfer_file = f"{name}.xls"
        transfer_sources[transfer_file] = [MeasurementRun(
            sheet="Data", label="Data", is_latest=True,
            kind="transfer", reason="settings", transfer=_transfer())]
    if with_output:
        output_file = f"{name} out.xls"
        output_sources[output_file] = [MeasurementRun(
            sheet="Data", label="Data", is_latest=True,
            kind="output", reason="settings", output=_output())]
    return DeviceGroup(name=name, transfer_sources=transfer_sources, output_sources=output_sources,
                       transfer_file=transfer_file, output_file=output_file,
                       params=PARAMS)


# ---------------- _available_kinds: 커브 종류별 버튼 가드 ----------------

def test_available_kinds_both_present():
    assert export_ui._available_kinds(_group()) == ["transfer", "output"]


def test_available_kinds_transfer_only_device_has_no_output_button():
    """MAIN FIX 요구사항: 소자가 가진 커브에만 버튼을 보여준다."""
    g = _group(with_output=False)
    assert export_ui._available_kinds(g) == ["transfer"]


def test_available_kinds_output_only_device_has_no_transfer_button():
    g = _group(with_transfer=False)
    assert export_ui._available_kinds(g) == ["output"]


def test_available_kinds_empty_device_gets_no_buttons():
    assert export_ui._available_kinds(DeviceGroup(name="empty")) == []


def test_available_kinds_excludes_interrupted_measurement_with_empty_frame():
    """측정이 중단된 파일은 빈 DataFrame 을 만든다 — transfer_runs 가 있어도
    forward 가 비어 있으면 그리다가 터지므로 버튼을 보이면 안 된다
    (summary._has_transfer_data 와 같은 규칙을 재사용해야 하는 이유)."""
    empty = TransferCurve(forward=pd.DataFrame({"V_G": [], "I_G": [], "I_D": []}))
    g = DeviceGroup(name="x", transfer_file="x.xls",
                    transfer_sources={"x.xls": [MeasurementRun(
                        sheet="Data", label="Data", is_latest=True,
                        kind="transfer", reason="settings", transfer=empty)]})
    assert export_ui._available_kinds(g) == []


def test_export_ui_reuses_summary_curve_presence_helpers():
    """중복 판정 로직을 새로 만들지 않고 summary._has_transfer_data /
    _has_output_data 를 그대로 쓴다는 요구사항을 소스 레벨로도 못박는다."""
    src = inspect.getsource(export_ui)
    assert "_has_transfer_data" in src
    assert "_has_output_data" in src
    assert "from fet_app.ui.summary import" in src


# ---------------- 파일명 규약 ----------------

def test_device_filename_matches_naming_convention():
    assert export_ui._device_filename("1-3", "transfer", "png") == "1-3_transfer.png"
    assert export_ui._device_filename("1-3", "output", "svg") == "1-3_output.svg"


# ---------------- HTML 폴백 제거 확인 ----------------

def test_export_ui_never_falls_back_to_html():
    """이미지 렌더 실패 시 HTML 로 대체하지 않는다 — 사용자가 PNG/JPG 를
    받았다고 착각할 수 있어서 제거했다. 실패는 실패로 보여준다.

    ZIP 경로는 이제 export.figure_bytes_batch() 를 쓴다 — 이 함수는 예외 대신
    실패한 항목만 None 을 돌려주므로(항목별 부분 실패를 허용하기 위해),
    KaleidoUnavailable 을 잡는 대신 blob is None 을 확인해 failed 목록에 담고
    st.error 로 보여준다. 동작(실패는 실패로 보여준다)은 그대로다."""
    src = inspect.getsource(export_ui)
    assert "to_html" not in src
    assert '"html"' not in src
    assert "figure_bytes_batch" in src
    assert "blob is None" in src
    assert "failed.append" in src
    assert "st.error" in src


# ---------------- 개별 다운로드: 클릭 한 번 ----------------

def _app(g) -> AppState:
    a = AppState()
    a.global_params = PARAMS
    a.devices = [g]
    a.selected = g.name
    return a


def test_device_download_is_one_click_not_two():
    """예전엔 '생성' 버튼을 눌러 session_state 에 bytes 를 담고 rerun 한 뒤,
    나타난 st.download_button 을 **또** 눌러야 실제로 받아졌다. 이제는
    download_button 하나만 그리고 data 에 지연 callable 을 넘겨 클릭 한 번으로
    끝낸다 — 중간 단계가 되살아나지 않게 소스로 못박는다."""
    src = inspect.getsource(export_ui._device_kind_download)
    assert "st.download_button" in src
    assert "st.button" not in src        # '생성' 버튼 단계가 없다
    assert "st.rerun" not in src         # 그 클릭을 소화하려던 rerun 도 없다
    assert "session_state" not in src    # 수동 blob 캐시도 없다
    assert "data=lambda" in src          # 렌더 시점이 아니라 클릭 시점에 만든다


def test_deferred_render_closure_reads_no_streamlit_state():
    """지연 callable 은 스크립트 스레드 밖에서 실행된다. 그 안에서
    st.session_state 를 읽으면 예외도 없이 빈 dict 로 읽혀 fit 구간이 조용히
    사라진다 — 세션·설정 값은 반드시 plan 을 만들 때(렌더 스레드에서) 읽어
    클로저에 담아야 한다."""
    src = inspect.getsource(export_ui.device_image_plan)
    body = src.replace(export_ui.device_image_plan.__doc__, "")  # 독스트링 제외
    assert "st." not in body
    assert "fit_range_for" in body     # fit 구간을 미리 읽어 담는다
    assert "deepcopy" in body          # 서식 dict 는 사본으로 고정한다


def test_device_image_plan_returns_key_and_zero_arg_callable():
    app = _app(_group())
    key, render = export_ui.device_image_plan(app, app.devices[0], "transfer", "png", 1)
    assert isinstance(key, str) and key
    assert callable(render)
    assert inspect.signature(render).parameters == {}


# ---------------- 스테일 캐시 버그: 설정이 캐시 키에 들어간다 ----------------

def _key(app, kind="transfer", fmt="png", scale=1) -> str:
    return export_ui.device_image_plan(app, app.devices[0], kind, fmt, scale)[0]


def test_cache_key_is_stable_when_nothing_changes():
    app = _app(_group())
    assert _key(app) == _key(app)


@pytest.mark.parametrize("mutate", [
    pytest.param(lambda s: s["transfer_style"].update(line_color_left="#123456"), id="색"),
    pytest.param(lambda s: s["style"].update(line_width=9.0), id="선두께"),
    pytest.param(lambda s: s["style"].update(tick_font_size=42), id="폰트"),
    pytest.param(lambda s: s["transfer_geom"].update(page_w_in=12.0), id="크기"),
    pytest.param(lambda s: s["transfer_axes"]["x"].update(auto=False, min=-99.0), id="축범위"),
    pytest.param(lambda s: s["transfer_style"].update(show_reverse=False), id="reverse토글"),
    pytest.param(lambda s: s["insets"]["legend"].update(font_size=11), id="인셋"),
])
def test_cache_key_changes_when_graph_settings_change(mutate):
    """예전 캐시 키는 f"{소자}_{kind}_{fmt}_{scale}" 뿐이라, 이미지를 한 번
    만든 뒤 색·축·크기를 바꿔도 키가 그대로여서 **설정이 반영 안 된 예전
    이미지가 그대로 내려가는** 버그가 있었다. 서식이 바뀌면 키도 바뀌어야 한다."""
    app = _app(_group())
    before = _key(app)
    mutate(app.settings)
    assert _key(app) != before


def test_cache_key_changes_with_format_and_scale():
    app = _app(_group())
    base = _key(app)
    assert _key(app, fmt="svg") != base
    assert _key(app, scale=4) != base


def test_cache_key_changes_with_device_params():
    """W/L/ε/d 는 fit -> V_th -> fit 직선을 바꾸므로 그림도 바뀐다."""
    app = _app(_group())
    before = _key(app)
    app.devices[0].params = DeviceParams(w_um=2000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)
    assert _key(app) != before


def test_cache_key_changes_when_underlying_curve_changes():
    """소자 패널에서 활성 파일·측정 런을 바꾸면 데이터가 달라진다. 소자
    이름만으로 키를 만들면 남의(또는 이전 런의) 이미지를 그대로 돌려준다."""
    g = _group()
    other = _transfer()
    other.forward = other.forward.assign(I_D=other.forward["I_D"] * 3.0)
    g.transfer_sources[g.transfer_file].append(MeasurementRun(
        sheet="Append1", label="Append1", is_latest=False,
        kind="transfer", reason="settings", transfer=other))
    app = _app(g)
    before = _key(app)
    g.transfer_run_idx = 1
    assert _key(app) != before


def test_transfer_and_output_keys_never_collide():
    app = _app(_group())
    assert _key(app, kind="transfer") != _key(app, kind="output")


# ---------------- 실제 bytes 로 증명 ----------------

def test_changed_settings_download_new_bytes_not_the_stale_image():
    """스테일 캐시 버그의 최종 증명. 같은 소자/kind/fmt/scale 로 다시 받아도
    설정이 바뀌었으면 다른 bytes 가 나와야 한다. 덤으로, 먼저 만들어 둔 렌더
    함수는 나중에 app.settings 가 뒤바뀌어도 자기가 그려질 때의 설정을 그대로
    유지해야 한다(지연 실행 시점과 렌더 시점이 다르기 때문)."""
    app = _app(_group())
    app.settings["transfer_style"]["line_color_left"] = "#FF0000"
    key_red, render_red = export_ui.device_image_plan(app, app.devices[0], "transfer", "png", 1)
    try:
        red = render_red()
    except export.KaleidoUnavailable:
        pytest.skip("kaleido 미설치")

    app.settings["transfer_style"]["line_color_left"] = "#0000FF"
    key_blue, render_blue = export_ui.device_image_plan(app, app.devices[0], "transfer", "png", 1)
    blue = render_blue()

    assert key_red != key_blue
    assert red != blue, "설정을 바꿨는데 같은 이미지가 나왔다 (스테일 캐시)"
    # 먼저 만든 함수는 나중 설정에 오염되지 않는다.
    assert render_red() == red


def test_same_key_repeat_download_is_served_from_cache():
    """같은 설정으로 다시 누르면 kaleido 를 건너뛴다 — 한 번 클릭이 매번
    3초씩 걸리면 안 된다."""
    app = _app(_group())
    app.settings["transfer_style"]["line_color_left"] = "#00AA00"
    key, render = export_ui.device_image_plan(app, app.devices[0], "transfer", "png", 1)
    calls = {"n": 0}

    def counting():
        calls["n"] += 1
        return render()

    try:
        first = export_ui._cached_image_bytes(counting, key)
    except export.KaleidoUnavailable:
        pytest.skip("kaleido 미설치")
    second = export_ui._cached_image_bytes(counting, key)
    assert first == second
    assert calls["n"] == 1


# ---------------- 요약표 직렬화도 클릭 시점으로 미룬다 ----------------

def test_summary_downloads_are_deferred():
    """내보내기 탭은 화면에 안 보여도 매 rerun 마다 실행된다. XLSX 직렬화를
    data= 에 바로 넘기면 아무도 안 받는 파일을 매 rerun 마다 새로 만든다."""
    src = inspect.getsource(export_ui.render)
    assert "data=lambda: export.summary_xlsx_bytes(df)" in src
    assert "data=lambda: export.summary_csv_bytes(df)" in src
