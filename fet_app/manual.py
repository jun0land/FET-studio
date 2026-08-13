"""문서 로더. 저장소 루트의 마크다운을 앱이 그대로 읽어 렌더한다 (스펙 §8).

문서와 앱이 같은 파일을 보므로 두 벌이 어긋날 수 없다.
"""

from __future__ import annotations

from pathlib import Path

# 탭 이름 -> 파일명. Task 18 의 st.tabs 가 이 순서를 그대로 쓴다.
DOCS = {
    "이용 방법": "MANUAL.md",
    "분석 방법": "METHODS.md",
}

_ROOT = Path(__file__).resolve().parent.parent


def doc_path(file_name: str) -> Path:
    return _ROOT / file_name


def load_doc(file_name: str) -> str:
    path = doc_path(file_name)
    if not path.is_file():
        return f"# 문서 없음\n\n`{file_name}` 를 찾지 못했습니다."
    return path.read_text(encoding="utf-8")


def load_manual() -> str:
    return load_doc("MANUAL.md")


def load_methods() -> str:
    return load_doc("METHODS.md")
