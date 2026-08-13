from pathlib import Path

from fet_app.grouping import DeviceGroup
from fet_app.state import AppState
from fet_app.ui.device_list import DEVICE_LIST_HEIGHT, device_flags, filter_devices
from fet_app.ui.viewport import FALLBACK_SCALE, preview_scale, scale_for_width

_DEVICE_LIST_SRC = Path(__file__).resolve().parent.parent / "fet_app" / "ui" / "device_list.py"


def test_filter_is_case_insensitive_substring():
    devs = [DeviceGroup(name="1-1"), DeviceGroup(name="1-10"), DeviceGroup(name="A-2")]
    assert [g.name for g in filter_devices(devs, "1-1")] == ["1-1", "1-10"]
    assert [g.name for g in filter_devices(devs, "a")] == ["A-2"]
    assert len(filter_devices(devs, "")) == 3


def test_device_flags_warn_on_missing_curve():
    app = AppState()
    g = DeviceGroup(name="x")           # transfer/output 모두 없음
    assert "no-data" in device_flags(app, g)


def test_device_flags_warn_on_group_warnings():
    app = AppState()
    g = DeviceGroup(name="x", warnings=["뭔가 이상"])
    assert "warning" in device_flags(app, g)


def test_scale_for_width_clamped():
    assert scale_for_width(0) == FALLBACK_SCALE
    assert scale_for_width(100) == 0.25
    assert scale_for_width(9600) == 1.0
    assert abs(scale_for_width(480) - 0.5) < 1e-9


def test_manual_scale_overrides_auto():
    app = AppState()
    app.preview_scale = 0.42
    assert preview_scale(app) == 0.42


def test_device_list_height_is_a_positive_pixel_int():
    """st.container(height=...) 는 정수 px 만 받는다 (vh 문자열 불가)."""
    assert isinstance(DEVICE_LIST_HEIGHT, int)
    assert DEVICE_LIST_HEIGHT > 0


def test_device_list_uses_real_scroll_container_not_fake_markdown_div():
    """I6: st.markdown 으로 연 <div> 는 st.button 들과 별개 컨테이너에 렌더돼
    바로 다음 st.markdown 이 즉시 닫아버린다 — 버튼들은 자식이 아니라 형제로
    끝나서 max-height/overflow-y 가 걸릴 대상이 없었다. st.container(height=)
    는 실제로 스크롤되는 DOM 컨테이너를 만든다."""
    src = _DEVICE_LIST_SRC.read_text(encoding="utf-8")
    assert "with st.container(height=" in src
    assert "fet-device-list" not in src


def test_device_list_search_box_stays_outside_scroll_container():
    """검색창은 리스트가 스크롤돼도 고정돼야 하므로 st.container(height=...)
    호출보다 소스상 앞에 나와야 한다 (검색창이 컨테이너 밖에 있다는 뜻)."""
    src = _DEVICE_LIST_SRC.read_text(encoding="utf-8")
    search_idx = src.index('st.text_input("검색"')
    container_idx = src.index("with st.container(height=")
    assert search_idx < container_idx
