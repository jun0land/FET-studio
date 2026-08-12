def test_example_set_counts(transfer_files, output_files):
    assert len(transfer_files) == 9
    assert len(output_files) == 9


def test_sample_bytes_are_ole2(sample_transfer_bytes, sample_output_bytes):
    # 구형 Keithley .xls 는 OLE2 복합문서다.
    magic = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    assert sample_transfer_bytes[:8] == magic
    assert sample_output_bytes[:8] == magic
