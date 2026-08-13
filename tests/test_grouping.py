from fet_app.grouping import DeviceGroup, group_files, parse_file, stem_of


def test_stem_strips_known_tokens():
    assert stem_of("1-1.xls") == "1-1"
    assert stem_of("1-1 out.xls") == "1-1"
    assert stem_of("1-3 best.xls") == "1-3"
    assert stem_of("1-3 out.xls") == "1-3"
    assert stem_of("1-5_output.xls") == "1-5"
    assert stem_of("sample-A transfer.xls") == "sample-A"


def test_stem_keeps_unknown_suffix():
    assert stem_of("1-9 anneal.xls") == "1-9 anneal"


def test_parse_file_transfer(example_dir):
    p = example_dir / "1-2.xls"
    pf = parse_file(p.read_bytes(), p.name)
    assert pf.kind == "transfer"
    assert len(pf.runs) == 1
    run = pf.latest
    assert run.transfer is not None and run.output is None
    assert run.transfer.v_ds == -60.0
    assert run.is_latest


def test_parse_file_output(example_dir):
    p = example_dir / "1-2 out.xls"
    pf = parse_file(p.read_bytes(), p.name)
    assert pf.kind == "output"
    assert len(pf.runs) == 1
    assert pf.latest.output is not None and pf.latest.transfer is None
    assert len(pf.latest.output.blocks) == 4


def test_parse_file_multi_run(example_dir):
    """1-3 best.xls 는 Data + Append1 두 런. Latest(Append1) 가 먼저 온다."""
    p = example_dir / "1-3 best.xls"
    pf = parse_file(p.read_bytes(), p.name)
    assert len(pf.runs) == 2
    assert [r.sheet for r in pf.runs] == ["Append1", "Data"]
    assert pf.runs[0].is_latest and not pf.runs[1].is_latest
    assert pf.latest.sheet == "Append1"
    for r in pf.runs:
        assert r.kind == "transfer"
        assert r.transfer is not None
        assert len(r.transfer.forward) == 81


def test_multi_run_group_defaults_to_latest_and_can_switch(example_dir):
    p = example_dir / "1-3 best.xls"
    groups = group_files([parse_file(p.read_bytes(), p.name)])
    g = groups[0]
    assert g.name == "1-3"
    assert len(g.transfer_runs) == 2
    assert g.transfer_run_idx == 0
    assert g.transfer is g.transfer_runs[0].transfer
    g.transfer_run_idx = 1
    assert g.transfer is g.transfer_runs[1].transfer


def test_group_transfer_property_none_when_no_runs():
    g = DeviceGroup(name="x")
    assert g.transfer is None and g.output is None


def test_group_all_examples(all_example_files):
    parsed = [parse_file(p.read_bytes(), p.name) for p in all_example_files]
    groups = group_files(parsed)
    assert [g.name for g in groups] == [f"1-{i}" for i in range(1, 10)]
    for g in groups:
        assert g.transfer is not None, g.name
        assert g.output is not None, g.name
        assert g.badges == "T·O"
        assert g.extra_files == []
    # 1-3 만 transfer 런이 2개
    by_name = {g.name: g for g in groups}
    assert len(by_name["1-3"].transfer_runs) == 2
    assert len(by_name["1-1"].transfer_runs) == 1


def test_group_records_extra_when_duplicate_kind(example_dir):
    a = example_dir / "1-1.xls"
    b = example_dir / "1-5 best.xls"
    parsed = [parse_file(a.read_bytes(), "dev.xls"),
              parse_file(b.read_bytes(), "dev copy.xls")]
    groups = group_files(parsed)
    # stem 이 'dev' 와 'dev copy' 로 달라 그룹 2개
    assert len(groups) == 2
    # 같은 stem 으로 강제하면 두 번째가 extra 로 밀린다
    parsed[1].name = "dev.xls"
    groups = group_files(parsed)
    assert len(groups) == 1
    assert groups[0].extra_files == ["dev.xls"]
    assert groups[0].warnings


def test_badges_reflect_available_curves():
    from fet_app.grouping import MeasurementRun
    t_run = MeasurementRun(sheet="Data", label="Run", is_latest=True,
                           kind="transfer", reason="forcing", settings=None,
                           transfer=object(), output=None)
    o_run = MeasurementRun(sheet="Data", label="Run", is_latest=True,
                           kind="output", reason="forcing", settings=None,
                           transfer=None, output=object())
    assert DeviceGroup(name="x", transfer_runs=[t_run]).badges == "T"
    assert DeviceGroup(name="x", output_runs=[o_run]).badges == "O"
    assert DeviceGroup(name="x").badges == "—"
