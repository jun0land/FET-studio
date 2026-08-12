import pytest

from fet_app.parsing import (
    RunSettings, data_sheet_names, load_sheets, parse_settings, settings_frame,
)


def _runs(path):
    b = path.read_bytes()
    sheets, engine = load_sheets(b)
    return sheets, parse_settings(settings_frame(b, sheets, engine))


def test_single_run_files_have_one_block(example_dir):
    _sheets, rs = _runs(example_dir / "1-1.xls")
    assert isinstance(rs, RunSettings)
    assert rs.order == ["Data"]
    assert rs.latest == "Data"
    assert len(rs) == 1


def test_single_run_block_still_readable(example_dir):
    _sheets, rs = _runs(example_dir / "1-1.xls")
    info = rs.block("Data")
    assert info.test_name == "p_transfer#1@3"
    assert info.get("Forcing Function", "Gate") == "Voltage Sweep"
    assert info.bias_level("Drain") == -60.0
    assert info.n_points("Gate") == 162


def test_two_run_file_splits_into_two_blocks(example_dir):
    _sheets, rs = _runs(example_dir / "1-3 best.xls")
    assert rs.order == ["Append1", "Data"]
    assert rs.latest == "Append1"
    assert len(rs) == 2


def test_each_block_keeps_its_own_timestamp(example_dir):
    """블록이 섞이지 않았는지 — 두 런의 Last Executed 가 서로 달라야 한다."""
    _sheets, rs = _runs(example_dir / "1-3 best.xls")
    t_new = rs.block("Append1").rows["Last Executed"][0]
    t_old = rs.block("Data").rows["Last Executed"][0]
    assert t_new != t_old
    assert t_new > t_old   # 문자열 비교로도 15:35:10 > 15:34:54


def test_block_returns_empty_info_for_unknown_name(example_dir):
    _sheets, rs = _runs(example_dir / "1-1.xls")
    info = rs.block("Append7")
    assert info.test_name == ""
    assert info.get("Forcing Function", "Gate") == ""


def test_data_sheet_names_orders_data_first(example_dir):
    sheets, _rs = _runs(example_dir / "1-3 best.xls")
    assert data_sheet_names(sheets) == ["Data", "Append1"]


def test_data_sheet_names_single(example_dir):
    sheets, _rs = _runs(example_dir / "1-1.xls")
    assert data_sheet_names(sheets) == ["Data"]


def test_data_sheet_names_sorts_append_numerically():
    import pandas as pd
    frame = pd.DataFrame({"GateV": [0.0], "GateI": [0.0], "DrainI": [0.0]})
    sheets = {"Append10": frame, "Calc": pd.DataFrame(),
              "Append2": frame, "Data": frame, "Settings": pd.DataFrame()}
    assert data_sheet_names(sheets) == ["Data", "Append2", "Append10"]


def test_every_example_has_a_latest_block(all_example_files):
    for p in all_example_files:
        _sheets, rs = _runs(p)
        assert rs.latest is not None, p.name
        assert rs.latest in rs.order, p.name


def test_run_count_matches_data_sheet_count(all_example_files):
    """Settings 블록 수와 데이터 시트 수가 어긋나면 런 선택 UI 가 깨진다."""
    for p in all_example_files:
        sheets, rs = _runs(p)
        assert len(rs) == len(data_sheet_names(sheets)), p.name
