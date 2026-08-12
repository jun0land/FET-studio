"""예제 데이터 픽스처. Example/ 의 9세트 18파일을 회귀 기준으로 쓴다."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def example_dir() -> Path:
    d = REPO_ROOT / "Example"
    assert d.is_dir(), f"Example 폴더가 없습니다: {d}"
    return d


@pytest.fixture(scope="session")
def all_example_files(example_dir: Path) -> list[Path]:
    files = sorted(example_dir.glob("*.xls"))
    assert len(files) == 18, f"예제 파일이 18개가 아닙니다: {len(files)}"
    return files


@pytest.fixture(scope="session")
def output_files(all_example_files: list[Path]) -> list[Path]:
    """파일명에 'out' 토큰이 있는 것 = output curve (기대값 확인용 정답지)."""
    return [p for p in all_example_files if "out" in p.stem.lower().split()]


@pytest.fixture(scope="session")
def transfer_files(all_example_files: list[Path]) -> list[Path]:
    return [p for p in all_example_files if "out" not in p.stem.lower().split()]


@pytest.fixture(scope="session")
def sample_transfer_bytes(example_dir: Path) -> bytes:
    return (example_dir / "1-1.xls").read_bytes()


@pytest.fixture(scope="session")
def sample_output_bytes(example_dir: Path) -> bytes:
    return (example_dir / "1-1 out.xls").read_bytes()
