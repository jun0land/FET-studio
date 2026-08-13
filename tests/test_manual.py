import re

from fet_app import constants
from fet_app.manual import DOCS, doc_path, load_doc, load_manual, load_methods


def test_both_docs_exist():
    assert DOCS == {"이용 방법": "MANUAL.md", "분석 방법": "METHODS.md"}
    for file_name in DOCS.values():
        assert doc_path(file_name).is_file(), file_name


def test_load_doc_matches_named_loaders():
    assert load_doc("MANUAL.md") == load_manual()
    assert load_doc("METHODS.md") == load_methods()


def test_missing_doc_returns_placeholder_not_crash():
    text = load_doc("NOPE.md")
    assert "NOPE.md" in text


def test_methods_contains_every_algorithm_constant():
    """상수를 바꾸면 METHODS.md 도 같이 바뀌게 강제한다 (스펙 §8)."""
    text = load_methods()
    required = [
        "8.854",                                   # EPSILON_0
        str(constants.FIT_ON_REGION_FACTOR).rstrip("0").rstrip("."),  # 100
        str(constants.FIT_MIN_POINTS),             # 10
        "60",                                      # FIT_MAX_FRACTION
        "5e-4",                                    # FIT_TIE_TOLERANCE
        str(constants.SS_WINDOW),                  # 5
        str(constants.DIAG_SLOPE_POINTS),          # 5
    ]
    for token in required:
        assert token in text, f"METHODS.md 에 '{token}' 이 없습니다"


def test_methods_contains_dielectric_presets():
    text = load_methods()
    for name, eps in constants.DIELECTRIC_PRESETS.items():
        assert str(eps) in text, f"{name} 의 eps_r {eps} 가 METHODS.md 에 없습니다"


def test_methods_contains_thresholds():
    text = load_methods()
    assert "1 %" in text or "1%" in text
    assert "0.99" in text
    assert "0.1" in text


def test_methods_contains_all_formulas():
    text = load_methods()
    for key in ["C_ox", "mu_sat", "V_th", "I_on", "SS", "ΔV_th"]:
        assert key in text, key


def test_methods_documents_output_normalization():
    """진단 정규화 기준 — 오경보 수정의 근거라 반드시 문서화한다 (스펙 §3.7)."""
    text = load_methods()
    assert "I_drive" in text
    assert "on-block" in text or "켜진 블록" in text
    assert "1 %" in text or "0.01" in text


def test_methods_documents_assumptions():
    text = load_methods()
    assert "가정과 한계" in text
    assert "과소평가" in text


def test_manual_documents_classification_and_grouping():
    text = load_manual()
    assert "Forcing Function" in text
    assert "dual sweep" in text.lower()
    assert "그룹" in text


def test_manual_documents_multi_run_handling():
    """재측정 파일 처리 규칙 — 사용자가 대조할 수 있어야 한다."""
    text = load_manual()
    assert "Append1" in text
    assert "Latest Run" in text
    assert "Initial Run" in text


def test_manual_documents_export_backgrounds():
    text = load_manual()
    assert "투명" in text
    assert "PNG" in text and "JPG" in text


def test_no_placeholders_in_either_doc():
    for file_name in DOCS.values():
        text = load_doc(file_name)
        assert not re.search(r"\bTBD\b|\bTODO\b", text), file_name
