import pandas as pd
import pytest

from fet_app.parsing import (
    OUTPUT,
    TRANSFER,
    SettingsInfo,
    classify_curve,
    data_sheet,
    load_sheets,
    output_block_count,
    parse_settings,
    settings_frame,
)


def _classify(path):
    b = path.read_bytes()
    sheets, engine = load_sheets(b)
    runs = parse_settings(settings_frame(b, sheets, engine))
    data = data_sheet(sheets)
    return classify_curve(data, runs.block(runs.latest or "Data"), path.name)


def test_all_18_files_classified_correctly(transfer_files, output_files):
    for p in transfer_files:
        kind, reason = _classify(p)
        assert kind == TRANSFER, f"{p.name} -> {kind}"
        assert reason == "forcing"
    for p in output_files:
        kind, reason = _classify(p)
        assert kind == OUTPUT, f"{p.name} -> {kind}"
        assert reason == "forcing"


def test_output_block_count_is_four(output_files):
    for p in output_files:
        sheets, _ = load_sheets(p.read_bytes())
        assert output_block_count(data_sheet(sheets)) == 4, p.name


def test_transfer_files_have_no_blocks(transfer_files):
    for p in transfer_files:
        sheets, _ = load_sheets(p.read_bytes())
        assert output_block_count(data_sheet(sheets)) == 0, p.name


def test_structure_fallback_transfer():
    """Settings 가 비었을 때 열 구조만으로 transfer 를 판정한다."""
    data = pd.DataFrame({"GateI": [1.0], "GateV": [0.0], "DrainI": [1.0]})
    kind, reason = classify_curve(data, SettingsInfo(), "무관한이름.xls")
    assert (kind, reason) == (TRANSFER, "structure")


def test_structure_fallback_output():
    data = pd.DataFrame({
        "GateI(1)": [1.0, 1.0], "GateV(1)": [0.0, 0.0],
        "DrainI(1)": [1.0, 2.0], "DrainV(1)": [0.0, -1.0],
        "GateI(2)": [1.0, 1.0], "GateV(2)": [-20.0, -20.0],
        "DrainI(2)": [1.0, 2.0], "DrainV(2)": [0.0, -1.0],
    })
    kind, reason = classify_curve(data, SettingsInfo(), "무관한이름.xls")
    assert (kind, reason) == (OUTPUT, "structure")


def test_structure_does_not_call_varying_gate_blocks_output():
    """GateV(n) 이 상수가 아니면 output 블록이 아니다 — 이름 단계로 넘어가야 한다."""
    data = pd.DataFrame({
        "GateI(1)": [1.0, 1.0], "GateV(1)": [0.0, -5.0],
        "DrainI(1)": [1.0, 2.0], "DrainV(1)": [0.0, -1.0],
    })
    _kind, reason = classify_curve(data, SettingsInfo(), "무관한이름.xls")
    assert reason == "name"


def test_name_fallback():
    """구조로도 못 가리면 Test Name / 파일명을 본다."""
    data = pd.DataFrame({"Foo": [1.0]})
    info = SettingsInfo(test_name="p_output#1@3")
    assert classify_curve(data, info, "x.xls") == (OUTPUT, "name")
    assert classify_curve(data, SettingsInfo(), "1-7 out.xls") == (OUTPUT, "name")
    assert classify_curve(data, SettingsInfo(), "1-7.xls") == (TRANSFER, "name")


def test_name_fallback_does_not_match_out_inside_word():
    """'output' 은 잡되 'routine' 같은 단어 속 out 은 잡지 않는다."""
    data = pd.DataFrame({"Foo": [1.0]})
    assert classify_curve(data, SettingsInfo(), "routine.xls") == (TRANSFER, "name")


def test_misnamed_file_still_classified_by_content(example_dir):
    """'out' 이 안 붙어도, 반대로 붙어도 내용으로 맞춘다 (명명법 불필요)."""
    b = (example_dir / "1-1 out.xls").read_bytes()
    sheets, engine = load_sheets(b)
    runs = parse_settings(settings_frame(b, sheets, engine))
    kind, reason = classify_curve(data_sheet(sheets),
                                  runs.block(runs.latest), "완전히엉뚱한이름.xls")
    assert (kind, reason) == (OUTPUT, "forcing")


def test_transfer_misnamed_as_out_still_transfer(example_dir):
    b = (example_dir / "1-1.xls").read_bytes()
    sheets, engine = load_sheets(b)
    runs = parse_settings(settings_frame(b, sheets, engine))
    kind, reason = classify_curve(data_sheet(sheets),
                                  runs.block(runs.latest), "1-1 out.xls")
    assert (kind, reason) == (TRANSFER, "forcing")


def test_data_sheet_missing_raises():
    with pytest.raises(ValueError):
        data_sheet({"Settings": pd.DataFrame()})


def test_data_sheet_unknown_name_raises(example_dir):
    sheets, _engine = load_sheets((example_dir / "1-1.xls").read_bytes())
    with pytest.raises(ValueError):
        data_sheet(sheets, "Append9")


def test_data_sheet_selects_named_run(example_dir):
    """1-3 best.xls 는 Data 와 Append1 두 런이 있고 둘 다 꺼낼 수 있어야 한다."""
    sheets, _engine = load_sheets((example_dir / "1-3 best.xls").read_bytes())
    default = data_sheet(sheets)
    first = data_sheet(sheets, "Data")
    second = data_sheet(sheets, "Append1")
    assert default.equals(first)          # 이름을 안 주면 Data
    assert len(second) == 162
    assert not second.equals(first)       # 서로 다른 측정


def test_data_sheet_strips_column_names(example_dir):
    sheets, _engine = load_sheets((example_dir / "1-1.xls").read_bytes())
    cols = list(data_sheet(sheets).columns)
    assert cols == ["GateI", "GateV", "DrainI"]
    assert all(c == c.strip() for c in cols)
