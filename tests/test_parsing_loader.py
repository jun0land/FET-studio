import pandas as pd

from fet_app.parsing import load_sheets, parse_settings, settings_frame


def _info(file_bytes):
    sheets, engine = load_sheets(file_bytes)
    runs = parse_settings(settings_frame(file_bytes, sheets, engine))
    return runs.block(runs.latest or "Data")


def test_load_sheets_returns_three_sheets(sample_transfer_bytes):
    sheets, _engine = load_sheets(sample_transfer_bytes)
    names = {str(k).strip().lower() for k in sheets}
    assert {"data", "settings"} <= names


def test_transfer_data_columns(sample_transfer_bytes):
    sheets, _ = load_sheets(sample_transfer_bytes)
    data = next(v for k, v in sheets.items() if str(k).strip().lower() == "data")
    assert [str(c).strip() for c in data.columns] == ["GateI", "GateV", "DrainI"]
    assert len(data) == 162


def test_output_data_columns(sample_output_bytes):
    sheets, _ = load_sheets(sample_output_bytes)
    data = next(v for k, v in sheets.items() if str(k).strip().lower() == "data")
    cols = [str(c).strip() for c in data.columns]
    assert cols[:4] == ["GateI(1)", "GateV(1)", "DrainI(1)", "DrainV(1)"]
    assert len(cols) == 16
    assert len(data) == 122


def test_loader_is_silent(sample_transfer_bytes, capsys):
    """xlrd 의 OLE2 경고가 stdout 으로 새면 안 된다 (스펙 §1.3)."""
    load_sheets(sample_transfer_bytes)
    captured = capsys.readouterr()
    assert "OLE2" not in captured.out
    assert "WARNING" not in captured.out


def test_settings_transfer(sample_transfer_bytes):
    info = _info(sample_transfer_bytes)
    assert info.test_name == "p_transfer#1@3"
    assert info.terminals == ["Source", "Gate", "Drain"]
    assert info.get("Forcing Function", "Gate") == "Voltage Sweep"
    assert info.get("Forcing Function", "Drain") == "Voltage Bias"
    assert info.bias_level("Drain") == -60.0
    assert info.n_points("Gate") == 162
    assert info.dual_sweep("Gate") is True


def test_settings_output(sample_output_bytes):
    info = _info(sample_output_bytes)
    assert info.test_name == "p_output#1@3"
    assert info.get("Forcing Function", "Gate") == "Voltage Step"
    assert info.get("Forcing Function", "Drain") == "Voltage Sweep"
    assert info.n_points("Drain") == 122
    assert info.n_points("Gate") == 4
    assert info.dual_sweep("Drain") is True


def test_parse_settings_handles_none():
    runs = parse_settings(None)
    assert len(runs) == 0
    assert runs.latest is None
    info = runs.block("Data")
    assert info.test_name == ""
    assert info.terminals == []
    assert info.get("Forcing Function", "Gate") == ""


def test_all_examples_load(all_example_files):
    for path in all_example_files:
        sheets, _ = load_sheets(path.read_bytes())
        assert any(str(k).strip().lower() == "data" for k in sheets), path.name
