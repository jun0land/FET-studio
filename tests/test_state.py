from pathlib import Path

from fet_app.grouping import DeviceGroup, MeasurementRun
from fet_app.params import DeviceParams
from fet_app.state import AppState, add_files, default_settings

_STATE_SRC = Path(__file__).resolve().parent.parent / "fet_app" / "state.py"


def test_default_settings_are_independent_copies():
    a, b = default_settings(), default_settings()
    a["style"]["line_width"] = 9.0
    assert b["style"]["line_width"] == 2.0


def test_add_files_groups_examples(all_example_files):
    app = AppState()
    warns = add_files(app, [(p.name, p.read_bytes()) for p in all_example_files])
    assert [g.name for g in app.devices] == [f"1-{i}" for i in range(1, 10)]
    assert app.selected == "1-1"
    assert warns == []


def test_add_files_is_idempotent_on_same_name(all_example_files):
    app = AppState()
    pair = [(p.name, p.read_bytes()) for p in all_example_files[:2]]
    add_files(app, pair)
    add_files(app, pair)
    # 같은 파일명은 다시 넣지 않는다
    assert sum(len(g.extra_files) for g in app.devices) == 0


def test_add_files_reports_unreadable():
    app = AppState()
    warns = add_files(app, [("깨진파일.xls", b"not an excel file")])
    assert warns and "깨진파일.xls" in warns[0]
    assert app.devices == []


def test_effective_params_inherit_global(all_example_files):
    app = AppState()
    add_files(app, [(p.name, p.read_bytes()) for p in all_example_files[:2]])
    app.global_params = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)
    g = app.devices[0]
    g.params = DeviceParams(l_um=25.0)
    eff = g.params.merged_with(app.global_params)
    assert eff.w_um == 1000.0 and eff.l_um == 25.0


def test_add_files_preserves_custom_params_when_merging_second_file(all_example_files):
    """existing 소자에 두 번째 파일(짝 파일)을 병합해도 사용자가 입력한 params
    는 유지돼야 한다 (M11) — saved/restore 없이 object identity 만으로 성립함을
    확인한다: existing 은 app.devices 와 같은 DeviceGroup 객체를 담고, 병합
    루프는 old.* 를 제자리에서 mutate 할 뿐 old 자체를 새로 만들지 않는다."""
    app = AppState()
    first = next(p for p in all_example_files if p.name == "1-1 out.xls")
    second = next(p for p in all_example_files if p.name == "1-1.xls")
    add_files(app, [(first.name, first.read_bytes())])
    g = app.device("1-1")
    g.params = DeviceParams(w_um=123.0, l_um=45.0, eps_r=3.9, d_nm=300.0)
    add_files(app, [(second.name, second.read_bytes())])
    g2 = app.device("1-1")
    assert g2 is g                       # 같은 객체 — 새로 만들어지지 않았다
    assert g2.params.w_um == 123.0
    assert g2.transfer is not None and g2.output is not None


def test_add_files_transfer_extra_dedupe_guard_matches_output_sibling():
    """M11: transfer_file 쪽 elif 도 output_file 쪽처럼 `not in old.extra_files`
    가드를 써야 한다. 현재 두 if/elif 블록의 실행 순서(transfer 먼저) 덕에 이
    가드가 없어도 동일 파일명의 중복 append 는 우연히 막히지만, 두 블록의
    순서가 바뀌면 바로 깨지는 취약한 상태였다. 소스에서 대칭성을 직접
    확인한다 — 가드를 지우면 이 테스트가 실패한다."""
    src = _STATE_SRC.read_text(encoding="utf-8")
    assert "elif g.transfer_runs and g.transfer_file and g.transfer_file not in old.extra_files:" in src
    assert "elif g.output_runs and g.output_file and g.output_file not in old.extra_files:" in src


def test_add_files_dual_kind_file_not_appended_twice_to_extra_files():
    """M11 이 지키는 실제 계약: 하나의 소자가 transfer/output 둘 다 이미 있는
    상태에서, 두 커브 종류를 동시에 담은 파일(같은 파일명이 transfer_file 이자
    output_file)을 추가로 올려도 extra_files 에는 그 파일명이 한 번만 남는다."""
    existing = DeviceGroup(
        name="1-1",
        transfer_runs=[MeasurementRun(sheet="Data", label="Data", is_latest=True,
                                      kind="transfer", reason="settings")],
        output_runs=[MeasurementRun(sheet="Data", label="Data", is_latest=True,
                                    kind="output", reason="settings")],
        transfer_file="orig_t.xls", output_file="orig_o.xls",
    )
    app = AppState(devices=[existing], file_names={"orig_t.xls", "orig_o.xls"})

    dual_group = DeviceGroup(
        name="1-1",
        transfer_runs=[MeasurementRun(sheet="Data", label="Data", is_latest=True,
                                      kind="transfer", reason="settings")],
        output_runs=[MeasurementRun(sheet="Append1", label="Append1", is_latest=False,
                                    kind="output", reason="settings")],
        transfer_file="dual.xls", output_file="dual.xls",
    )

    import fet_app.state as state_mod
    original_group_files = state_mod.group_files
    original_parse_file = state_mod.parse_file
    state_mod.group_files = lambda parsed: [dual_group]
    state_mod.parse_file = lambda blob, name: object()
    try:
        add_files(app, [("dual.xls", b"fake")])
    finally:
        state_mod.group_files = original_group_files
        state_mod.parse_file = original_parse_file

    assert app.devices[0].extra_files == ["dual.xls"]
