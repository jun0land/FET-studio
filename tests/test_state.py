from fet_app.params import DeviceParams
from fet_app.state import AppState, add_files, default_settings


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
