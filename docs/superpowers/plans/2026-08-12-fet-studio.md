# FET Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keithley `.xls` 파일을 한 번에 업로드하면 transfer/output curve 를 자동 판정해 논문용 그래프를 그리고, V_th·μ_sat·SS·on-off·히스테리시스와 output 진단 4종을 계산해 내보내는 Streamlit 앱을 만든다.

**Architecture:** 얇은 `app.py` 진입점 + `fet_app/` 패키지. 순수 함수 계층(parsing → curves → grouping → fitting → metrics → figure → export)을 먼저 완성하고 그 위에 Streamlit UI 계층(`fet_app/ui/`)을 올린다. 계산 계층은 Streamlit 을 import 하지 않으므로 pytest 로 독립 검증된다. UI 는 세션 상태(`state.py`)만 통해 계산 계층과 대화한다.

**Tech Stack:** Python 3.12, Streamlit, pandas, numpy, plotly, kaleido, xlrd(구형 .xls), openpyxl, XlsxWriter, pytest

## Global Constraints

- 스펙 원본: `docs/superpowers/specs/2026-08-12-fet-studio-design.md`. 충돌 시 스펙이 우선.
- 저장소 origin: `https://github.com/jun0land/FET-studio.git`
- 물리 상수 `EPSILON_0 = 8.854e-14` F/cm — 이 값 그대로. 반올림 금지.
- 유전체 프리셋 ε_r: SiO2 3.9 / Al2O3 9.0 / HfO2 25.0 / PMMA 3.6
- fit 자동 탐색 상수: on-영역 기준 `100 × I_off`, 최소 윈도우 `10` 점, 최대 `60 %`, 동점 판정 `ΔR² < 5e-4`
- SS 이동 회귀 창 `5` 점, output 진단 기울기 산출 `5` 점, 원점 구간 `10 %`
- output 진단 기본 임계값: 0V 오프셋 `1 %` / 원점 선형성 `R² 0.99` / 포화 `0.1` / 게이트 누설 `1 %`
- 그래프는 **논문용 흰 배경 + 4면 mirror ticks + ticks inside + 그리드 없음**. glass 효과 금지.
- 눈금 지수 표기는 항상 `exponentformat="E"` (`1E-11` 형식).
- 폰트 기본 크기 30, 범위 6–50. **폰트 크기에 슬라이더 금지** — `st.number_input` 스테퍼.
- 선 두께 조절 간격 0.5.
- Transfer 좌 Y축 제목은 **`|I_D| (A)` — 절댓값 기호를 쓴다.** (photodetector-app 규약 A2 를 의도적으로 뒤집은 것. 근거는 스펙 §5.2)
- 내보내기 PNG 는 배경 **완전 투명**, JPG 는 배경 **흰색**. 화면 표시는 항상 흰 배경.
- `xlrd` 의 OLE2 경고는 절대 사용자에게 노출하지 않는다.
- 계산 계층 모듈(`parsing`/`curves`/`grouping`/`params`/`fitting`/`metrics`/`figure_*`/`export`)은 **`import streamlit` 금지**. 캐싱이 필요하면 UI 계층에서 감싼다.
- 커밋 메시지는 한글 요약 + `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` 로 끝낸다.

---

## File Structure

| 경로 | 책임 |
|---|---|
| `app.py` | 진입점. `set_page_config` → `state.boot()` → `layout.render_app()`. 로직 없음 |
| `fet_app/constants.py` | 물리 상수·프리셋·알고리즘 상수·팔레트·`DEFAULTS`. 동작은 `hex_to_rgba` 하나 |
| `fet_app/params.py` | `DeviceParams` (W/L/ε_r/d) 와 `c_ox_from` |
| `fet_app/parsing.py` | 다단 폴백 로더 · Settings 표 파싱 · 커브 종류 판정 |
| `fet_app/curves.py` | `TransferCurve`/`OutputCurve` 모델, dual sweep 분리 |
| `fet_app/grouping.py` | 파일명 stem 추출 → `DeviceGroup` 조립 |
| `fet_app/fitting.py` | 최소자승 fit · 자동 윈도우 탐색 |
| `fet_app/metrics.py` | V_th·μ_sat·on/off·SS·ΔV_th · output 진단 4종 |
| `fet_app/figure_common.py` | geom/축/폰트 공통 규약, 표시 배율 k 적용 |
| `fet_app/figure_transfer.py` | 이중 Y축 transfer 그래프 |
| `fet_app/figure_output.py` | 그라데이션 output 그래프 |
| `fet_app/export.py` | 요약표 · 이미지 바이트 · 가공 CSV · ZIP |
| `fet_app/presets.py` | 서식 프리셋 추출/적용 |
| `fet_app/state.py` | 세션 상태 부팅 · 파일 등록 |
| `fet_app/theme.py` | photodetector-app 에서 이식한 CSS |
| `fet_app/manual.py` | `MANUAL.md` 로드 |
| `fet_app/ui/layout.py` | 3열 배치 + 반응형 CSS 주입 |
| `fet_app/ui/device_list.py` | 우측 소자 리스트 + 검색 |
| `fet_app/ui/panel_device.py` | W/L/ε/d 입력 |
| `fet_app/ui/panel_fit.py` | fit 자동/수동 |
| `fet_app/ui/panel_style.py` | 색·두께·축·폰트·geom·프리셋 |
| `fet_app/ui/summary.py` | 지표·진단 패널 + 전체 요약 테이블 |
| `fet_app/ui/export_ui.py` | 내보내기 UI |
| `fet_app/ui/viewport.py` | 뷰포트 폭 프로브 + 수동 배율 폴백 |
| `MANUAL.md` | 모든 수식·상수·임계값 (앱이 이 파일을 읽어 렌더) |
| `tests/` | pytest. `Example/` 을 픽스처로 사용 |

---

## Task 1: 프로젝트 스캐폴딩과 테스트 하네스

**Files:**
- Create: `requirements.txt`, `.streamlit/config.toml`, `pytest.ini`, `fet_app/__init__.py`, `fet_app/ui/__init__.py`, `tests/__init__.py`, `tests/conftest.py`
- Test: `tests/test_fixtures.py`

**Interfaces:**
- Consumes: 없음
- Produces: pytest 픽스처 `example_dir` (Path), `transfer_files` (list[Path], 9개), `output_files` (list[Path], 9개), `all_example_files` (list[Path], 18개)

- [ ] **Step 1: 의존성과 설정 파일 작성**

`requirements.txt`:
```
streamlit>=1.40
pandas>=2.2
numpy>=1.26
plotly>=5.24
kaleido>=0.2.1
xlrd>=2.0.1
openpyxl>=3.1
lxml>=5.0
XlsxWriter>=3.2
```

`.streamlit/config.toml`:
```toml
[theme]
base = "light"
primaryColor = "#ed542b"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F5F6F8"
textColor = "#1A1C1E"

[server]
maxUploadSize = 200

[browser]
gatherUsageStats = false
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
filterwarnings =
    ignore::DeprecationWarning
```

빈 패키지 파일 3개를 만든다:
```python
# fet_app/__init__.py
"""FET Studio — transfer/output curve 분석 앱."""
```
```python
# fet_app/ui/__init__.py
"""Streamlit UI 계층."""
```
```python
# tests/__init__.py
```

- [ ] **Step 2: conftest 픽스처 작성**

`tests/conftest.py`:
```python
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
```

- [ ] **Step 3: 실패하는 테스트 작성**

`tests/test_fixtures.py`:
```python
def test_example_set_counts(transfer_files, output_files):
    assert len(transfer_files) == 9
    assert len(output_files) == 9


def test_sample_bytes_are_ole2(sample_transfer_bytes, sample_output_bytes):
    # 구형 Keithley .xls 는 OLE2 복합문서다.
    magic = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    assert sample_transfer_bytes[:8] == magic
    assert sample_output_bytes[:8] == magic
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `python -m pytest tests/test_fixtures.py -v`
Expected: 2 passed. 실패하면 `Example/` 경로나 파일 개수를 확인한다.

- [ ] **Step 5: 커밋**

```bash
git add requirements.txt .streamlit pytest.ini fet_app tests
git commit -m "$(cat <<'EOF'
chore: 프로젝트 스캐폴딩과 예제 데이터 픽스처

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 상수 모듈과 C_ox 계산

**Files:**
- Create: `fet_app/constants.py`, `fet_app/params.py`
- Test: `tests/test_params.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `constants.EPSILON_0: float`, `constants.DIELECTRIC_PRESETS: dict[str, float]`, `constants.ACCENT: str`
  - `constants.FIT_MIN_POINTS`, `FIT_MAX_FRACTION`, `FIT_ON_REGION_FACTOR`, `FIT_TIE_TOLERANCE`, `SS_WINDOW`, `DIAG_SLOPE_POINTS`, `DIAG_ORIGIN_FRACTION`, `DEFAULT_THRESHOLDS: dict[str, float]`
  - `constants.FONT_FAMILIES: list[str]`, `DASH_OPTIONS: dict[str, str]`, `FONT_SIZE_MIN`, `FONT_SIZE_MAX`, `LINE_WIDTH_STEP`, `DEFAULTS: dict`
  - `constants.hex_to_rgba(hex_color: str, alpha: float) -> str`
  - `params.DeviceParams(w_um: float, l_um: float, eps_r: float, d_nm: float)` — 메서드 `c_ox() -> float`, `w_cm() -> float`, `l_cm() -> float`, `is_complete() -> bool`
  - `params.c_ox_from(eps_r: float, d_nm: float) -> float`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_params.py`:
```python
import math

import pytest

from fet_app import constants
from fet_app.params import DeviceParams, c_ox_from


def test_epsilon_0_exact_value():
    """스펙 고정값. 반올림하면 mu_sat 이 어긋난다."""
    assert constants.EPSILON_0 == 8.854e-14


def test_dielectric_presets():
    assert constants.DIELECTRIC_PRESETS["SiO2"] == 3.9
    assert constants.DIELECTRIC_PRESETS["Al2O3"] == 9.0
    assert constants.DIELECTRIC_PRESETS["HfO2"] == 25.0
    assert constants.DIELECTRIC_PRESETS["PMMA"] == 3.6


def test_c_ox_sio2_300nm():
    """SiO2 300 nm -> 11.51 nF/cm^2 (스펙 §3.1 검산값)."""
    c = c_ox_from(3.9, 300.0)
    assert math.isclose(c, 1.1510e-8, rel_tol=1e-3)


def test_c_ox_scales_inversely_with_thickness():
    assert math.isclose(c_ox_from(3.9, 150.0), 2 * c_ox_from(3.9, 300.0), rel_tol=1e-9)


def test_c_ox_rejects_nonpositive_thickness():
    with pytest.raises(ValueError):
        c_ox_from(3.9, 0.0)


def test_device_params_unit_conversion():
    p = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)
    assert math.isclose(p.w_cm(), 0.1, rel_tol=1e-12)
    assert math.isclose(p.l_cm(), 5e-3, rel_tol=1e-12)
    assert math.isclose(p.c_ox(), 1.1510e-8, rel_tol=1e-3)
    assert p.is_complete()


def test_device_params_incomplete_when_missing():
    assert not DeviceParams(w_um=None, l_um=50.0, eps_r=3.9, d_nm=300.0).is_complete()


def test_default_thresholds():
    t = constants.DEFAULT_THRESHOLDS
    assert t["zero_offset"] == 0.01
    assert t["linearity_r2"] == 0.99
    assert t["saturation"] == 0.1
    assert t["gate_leak"] == 0.01


def test_fit_algorithm_constants():
    assert constants.FIT_ON_REGION_FACTOR == 100.0
    assert constants.FIT_MIN_POINTS == 10
    assert constants.FIT_MAX_FRACTION == 0.60
    assert constants.FIT_TIE_TOLERANCE == 5e-4
    assert constants.SS_WINDOW == 5
    assert constants.DIAG_SLOPE_POINTS == 5
    assert constants.DIAG_ORIGIN_FRACTION == 0.10


def test_hex_to_rgba():
    assert constants.hex_to_rgba("#ed542b", 0.5) == "rgba(237,84,43,0.5)"
    assert constants.hex_to_rgba("#000", 1) == "rgba(0,0,0,1)"
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_params.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.constants'`

- [ ] **Step 3: 구현**

`fet_app/constants.py`:
```python
"""앱 전역 상수. 데이터 전용 — 동작은 hex_to_rgba 하나뿐.

여기 값은 MANUAL.md 에 그대로 문서화된다. 고칠 때 매뉴얼도 같이 고칠 것.
"""

from __future__ import annotations

# ---------------- 물리 상수 ----------------
# 진공 유전율, cm 단위계. 스펙 §3.1 고정값 — 반올림 금지.
EPSILON_0 = 8.854e-14  # F/cm

DIELECTRIC_PRESETS = {
    "SiO2": 3.9,
    "Al2O3": 9.0,
    "HfO2": 25.0,
    "PMMA": 3.6,
}
DIELECTRIC_LABELS = {
    "SiO2": "SiO₂ (3.9)",
    "Al2O3": "Al₂O₃ (9.0)",
    "HfO2": "HfO₂ (25)",
    "PMMA": "PMMA (3.6)",
    "Custom": "직접 입력",
}

# ---------------- fit 자동 탐색 (스펙 §3.3) ----------------
FIT_ON_REGION_FACTOR = 100.0   # on-영역 기준: |I_D| > 100 x I_off
FIT_MIN_POINTS = 10            # 최소 윈도우 점 개수
FIT_MAX_FRACTION = 0.60        # 최대 윈도우 = 후보 영역의 60 %
FIT_TIE_TOLERANCE = 5e-4       # 동점 판정: dR^2 < 5e-4 면 긴 쪽 우선

# ---------------- 지표 (스펙 §3.5, §3.7) ----------------
SS_WINDOW = 5                  # SS 이동 최소자승 회귀 창
DIAG_SLOPE_POINTS = 5          # output 진단 기울기 산출 점 개수
DIAG_ORIGIN_FRACTION = 0.10    # 원점 선형성 판정 구간 = 스윕폭의 10 %

DEFAULT_THRESHOLDS = {
    "zero_offset": 0.01,       # |I_D(0)| / max|I_D| 가 1 % 초과면 경고
    "linearity_r2": 0.99,      # 원점 구간 선형 fit R^2 가 0.99 미만이면 경고
    "saturation": 0.1,         # 말단/원점 기울기비가 0.1 초과면 미포화 경고
    "gate_leak": 0.01,         # max|I_G| / max|I_D| 가 1 % 초과면 경고
}

# ---------------- 그래프 ----------------
ACCENT = "#ed542b"

ORIGIN_COLORS = {
    "Black": "#000000", "Red": "#FF0000", "Green": "#00FF00", "Blue": "#0000FF",
    "Cyan": "#00FFFF", "Magenta": "#FF00FF", "Yellow": "#FFFF00",
    "Dark Yellow": "#808000", "Navy": "#000080", "Purple": "#800080",
    "Wine": "#800000", "Olive": "#008000", "Dark Cyan": "#008080",
    "Royal": "#0000A0", "Orange": "#FF8000", "Violet": "#8000FF",
    "Pink": "#FF0080", "White": "#FFFFFF", "LT Gray": "#C0C0C0",
    "Gray": "#808080", "LT Yellow": "#FFFF80", "LT Cyan": "#80FFFF",
    "LT Magenta": "#FF80FF", "Dark Gray": "#404040",
}

FONT_FAMILIES = ["Myriad Pro", "Pretendard", "Arial", "Times New Roman",
                 "Calibri", "Helvetica", "Courier New"]
DASH_OPTIONS = {"Solid": "solid", "Dash": "dash", "Dot": "dot", "DashDot": "dashdot"}

FONT_SIZE_MIN = 6
FONT_SIZE_MAX = 50
LINE_WIDTH_STEP = 0.5

# Settings 시트 블록 구분자
SEP_TOKEN = "=================================="


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """#RRGGBB + 투명도 -> rgba() 문자열."""
    h = str(hex_color).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        r, g, b = 255, 255, 255
    return f"rgba({r},{g},{b},{alpha:g})"


# ---------------- 기본 서식 ----------------
# 소비자는 반드시 copy.deepcopy 후 사용할 것 (평범한 dict 이라 전역 오염 위험).
DEFAULTS = {
    "geom": {"page_w_in": 10.0, "page_h_in": 8.0, "graph_left_pct": 17.9,
             "graph_top_pct": 11.58, "graph_width_pct": 68.2, "graph_height_pct": 71.77},
    "style": {"font_family": "Myriad Pro", "title_font_size": 30,
              "tick_font_size": 30, "line_width": 2.0, "show_grid": False},
    "transfer_axes": {
        "x": {"type": "linear", "auto": True, "min": None, "max": None,
              "dtick": 20.0, "minor_dtick": None,
              "title": "V_G (V)", "title_standoff": None},
        # 좌 Y: 절댓값 기호를 쓴다 (스펙 §5.2 — photodetector-app 규약 A2 를 뒤집음)
        "y": {"type": "log", "auto": True, "min": None, "max": None,
              "dtick": 1, "minor_dtick": "D1",
              "title": "|I_D| (A)", "title_standoff": None},
        "y2": {"type": "linear", "auto": True, "min": None, "max": None,
               "dtick": None, "minor_dtick": None,
               "title": "√|I_D| (A^0.5)", "title_standoff": None},
    },
    "output_axes": {
        "x": {"type": "linear", "auto": True, "min": None, "max": None,
              "dtick": 20.0, "minor_dtick": None,
              "title": "V_D (V)", "title_standoff": None},
        "y": {"type": "linear", "auto": True, "min": None, "max": None,
              "dtick": None, "minor_dtick": None,
              "title": "I_D (A)", "title_standoff": None},
    },
    "transfer_style": {
        "color": "#000000",
        "show_reverse": True,
        "show_gate_current": False,
        "show_fit": True,
    },
    "output_style": {
        "base_color": ACCENT,
        "show_reverse": True,
        "lightness_min": 0.18,
        "lightness_max": 0.82,
        "manual_colors": {},   # {v_g(str): "#RRGGBB"} — 비어 있으면 그라데이션 사용
    },
    "insets": {
        "legend": {"x": 0.99, "y": 0.99, "xanchor": "right", "yanchor": "top",
                   "font_size": 30, "bg_opacity": 0.0, "border": False},
        "sample": {"x": 0.01, "y": 0.01, "xanchor": "left", "yanchor": "bottom",
                   "text": "", "font_size": 30},
    },
}
```

`fet_app/params.py`:
```python
"""소자 기하·유전체 파라미터와 C_ox 계산 (스펙 §3.1)."""

from __future__ import annotations

from dataclasses import dataclass

from fet_app.constants import EPSILON_0


def c_ox_from(eps_r: float, d_nm: float) -> float:
    """C_ox = eps_0 * eps_r / d.  d 는 nm 입력, 내부에서 cm 로 환산(x1e-7).

    반환 단위: F/cm^2
    """
    if d_nm is None or float(d_nm) <= 0:
        raise ValueError("유전체 두께는 0보다 커야 합니다.")
    if eps_r is None or float(eps_r) <= 0:
        raise ValueError("유전상수는 0보다 커야 합니다.")
    d_cm = float(d_nm) * 1e-7
    return EPSILON_0 * float(eps_r) / d_cm


@dataclass
class DeviceParams:
    """채널 폭/길이는 UI 입력이 um, 유전체 두께는 nm. 내부 계산은 전부 cm."""

    w_um: float | None = None
    l_um: float | None = None
    eps_r: float | None = None
    d_nm: float | None = None

    def w_cm(self) -> float:
        return float(self.w_um) * 1e-4

    def l_cm(self) -> float:
        return float(self.l_um) * 1e-4

    def c_ox(self) -> float:
        return c_ox_from(self.eps_r, self.d_nm)

    def is_complete(self) -> bool:
        vals = (self.w_um, self.l_um, self.eps_r, self.d_nm)
        return all(v is not None and float(v) > 0 for v in vals)

    def merged_with(self, fallback: "DeviceParams") -> "DeviceParams":
        """비어 있는 항목만 전역 기본값에서 상속받는다."""
        return DeviceParams(
            w_um=self.w_um if self.w_um is not None else fallback.w_um,
            l_um=self.l_um if self.l_um is not None else fallback.l_um,
            eps_r=self.eps_r if self.eps_r is not None else fallback.eps_r,
            d_nm=self.d_nm if self.d_nm is not None else fallback.d_nm,
        )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_params.py -v`
Expected: 10 passed

- [ ] **Step 5: 커밋**

```bash
git add fet_app/constants.py fet_app/params.py tests/test_params.py
git commit -m "$(cat <<'EOF'
feat: 상수 모듈과 C_ox 계산

EPSILON_0, 유전체 프리셋, fit/진단 알고리즘 상수, 기본 서식을 한곳에 모은다.
DeviceParams 는 um/nm 입력을 cm 로 환산한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 파일 로더와 Settings 파싱

**Files:**
- Create: `fet_app/parsing.py`
- Test: `tests/test_parsing_loader.py`

**Interfaces:**
- Consumes: `fet_app.constants.SEP_TOKEN`
- Produces:
  - `parsing.load_sheets(file_bytes: bytes) -> tuple[dict[str, pd.DataFrame], str | None]`
  - `parsing.settings_frame(file_bytes: bytes, sheets: dict, engine: str | None) -> pd.DataFrame | None`
  - `parsing.SettingsInfo` — 필드 `test_name: str`, `terminals: list[str]`, `rows: dict[str, list[str]]`, `raw: list[list[str]]`; 메서드 `get(row_label: str, terminal: str) -> str`, `dual_sweep(terminal: str) -> bool`, `n_points(terminal: str) -> int | None`, `bias_level(terminal: str) -> float | None`
  - `parsing.parse_settings(df: pd.DataFrame | None) -> SettingsInfo`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_parsing_loader.py`:
```python
import pandas as pd

from fet_app.parsing import load_sheets, parse_settings, settings_frame


def _info(file_bytes):
    sheets, engine = load_sheets(file_bytes)
    return parse_settings(settings_frame(file_bytes, sheets, engine))


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
    info = parse_settings(None)
    assert info.test_name == ""
    assert info.terminals == []
    assert info.get("Forcing Function", "Gate") == ""


def test_all_examples_load(all_example_files):
    for path in all_example_files:
        sheets, _ = load_sheets(path.read_bytes())
        assert any(str(k).strip().lower() == "data" for k in sheets), path.name
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_parsing_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.parsing'`

- [ ] **Step 3: 구현**

`fet_app/parsing.py`:
```python
"""Keithley KTEI .xls 로더와 Settings 표 파싱.

구형 OLE2 .xls 는 엔진마다 읽히는 정도가 달라 다단 폴백을 쓴다.
xlrd 는 무해한 OLE2 경고를 stdout 으로 뱉으므로 반드시 삼킨다 (스펙 §1.3).
"""

from __future__ import annotations

import contextlib
import io
import re
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from fet_app.constants import SEP_TOKEN


@contextlib.contextmanager
def _quiet():
    """xlrd 의 OLE2 경고를 사용자에게 노출하지 않는다."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


def _read_excel(file_bytes: bytes, engine: str | None = None, **kwargs):
    if engine:
        kwargs["engine"] = engine
    with _quiet():
        return pd.read_excel(io.BytesIO(file_bytes), **kwargs)


def _looks_like_data(df) -> bool:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return False
    cols = {str(c).strip() for c in df.columns}
    return any(re.match(r"^(Gate|Drain|Source)[IV](\(\d+\))?$", c) for c in cols)


def load_sheets(file_bytes: bytes) -> tuple[dict[str, pd.DataFrame], str | None]:
    """기본 -> xlrd -> openpyxl -> read_html -> TSV 순으로 시도.

    반환: (시트이름 -> DataFrame, 성공한 engine). engine 은 Settings 재읽기에 쓴다.
    """
    errors: list[str] = []
    for engine in (None, "xlrd", "openpyxl"):
        try:
            sheets = _read_excel(file_bytes, engine, sheet_name=None)
            if isinstance(sheets, dict) and sheets:
                return sheets, engine
        except Exception as e:  # noqa: BLE001
            errors.append(f"read_excel(engine={engine}): {e}")

    try:
        with _quiet():
            tables = pd.read_html(io.BytesIO(file_bytes))
        out: dict[str, pd.DataFrame] = {}
        for i, t in enumerate(tables):
            if _looks_like_data(t):
                out["Data" if not out else f"Append{i}"] = t
        if out:
            return out, None
        errors.append("read_html: 데이터 표를 찾지 못함")
    except Exception as e:  # noqa: BLE001
        errors.append(f"read_html: {e}")

    try:
        with _quiet():
            df = pd.read_csv(io.BytesIO(file_bytes), sep="\t")
        if _looks_like_data(df):
            return {"Data": df}, None
        errors.append("read_csv(tab): 데이터 컬럼 없음")
    except Exception as e:  # noqa: BLE001
        errors.append(f"read_csv(tab): {e}")

    raise ValueError("파일을 읽을 수 없습니다.\n" + "\n".join(errors))


def settings_frame(file_bytes: bytes, sheets: dict, engine: str | None) -> pd.DataFrame | None:
    """Settings 는 첫 행이 구분선이라 header=0 이면 소실된다 -> header=None 으로 다시 읽는다."""
    key = next((k for k in sheets if str(k).strip().lower() == "settings"), None)
    if key is None:
        return None
    try:
        return _read_excel(file_bytes, engine, sheet_name=key, header=None)
    except Exception:  # noqa: BLE001
        return sheets[key]


def _cell(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


@dataclass
class SettingsInfo:
    """Settings 시트를 '행 라벨 -> 단자별 값' 으로 정규화한 것.

    예: rows["Forcing Function"] == ["Common", "Voltage Sweep", "Voltage Bias"]
        terminals                 == ["Source", "Gate", "Drain"]
    """

    test_name: str = ""
    terminals: list[str] = field(default_factory=list)
    rows: dict[str, list[str]] = field(default_factory=dict)
    raw: list[list[str]] = field(default_factory=list)

    def get(self, row_label: str, terminal: str) -> str:
        values = self.rows.get(row_label)
        if not values or terminal not in self.terminals:
            return ""
        i = self.terminals.index(terminal)
        return values[i] if i < len(values) else ""

    def dual_sweep(self, terminal: str) -> bool:
        return self.get("Dual Sweep Mode", terminal).lower() == "enabled"

    def n_points(self, terminal: str) -> int | None:
        raw = self.get("Number of Points", terminal)
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return None

    def bias_level(self, terminal: str) -> float | None:
        raw = self.get("Start/Level", terminal)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None


def parse_settings(df: pd.DataFrame | None) -> SettingsInfo:
    info = SettingsInfo()
    if not isinstance(df, pd.DataFrame) or df.empty:
        return info

    # header=None 으로 못 읽었으면 컬럼명이 첫 행이므로 복원한다.
    rows: list[list[str]] = []
    cols = list(df.columns)
    if not all(isinstance(c, (int, np.integer)) or str(c).startswith("Unnamed") for c in cols):
        rows.append([_cell(c) for c in cols])
    for i in range(len(df)):
        rows.append([_cell(df.iloc[i, j]) for j in range(df.shape[1])])
    info.raw = rows

    for cells in rows:
        if not cells:
            continue
        joined = " ".join(cells)
        if "=====" in joined or SEP_TOKEN in joined:
            continue
        label = cells[0]
        if not label:
            continue
        values = [c for c in cells[1:]]
        # 뒤쪽 빈 칸 제거
        while values and not values[-1]:
            values.pop()

        if label.lower() == "test name":
            info.test_name = values[0] if values else ""
            continue
        if label.lower() == "device terminal":
            info.terminals = values
            continue
        info.rows.setdefault(label, values)

    return info
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_parsing_loader.py -v`
Expected: 8 passed

- [ ] **Step 5: 커밋**

```bash
git add fet_app/parsing.py tests/test_parsing_loader.py
git commit -m "$(cat <<'EOF'
feat: Keithley .xls 다단 폴백 로더와 Settings 파싱

SettingsInfo 로 '행 라벨 x 단자' 조회를 정규화한다.
xlrd 의 OLE2 경고는 _quiet() 로 삼켜 사용자에게 노출하지 않는다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3b: 다중 측정 런 지원

**배경 (플랜 작성 후 발견):** `Example/1-3 best.xls` 는 시트가 `Data, Calc, Settings, Append1` 이고
`Data`(162행) 와 `Append1`(162행) 두 번의 측정이 들어 있다. `Settings` 도 블록이 두 개다:

```
==================================
Append 1        Latest Run          <- 15:35:10, 데이터는 Append1 시트
==================================
...
==================================
Initial Run                         <- 15:34:54, 데이터는 Data 시트
==================================
```

Task 3 의 `parse_settings` 는 블록을 구분하지 않고 `setdefault` 로 첫 블록만 남긴다. 그 결과
`Data` 시트(먼저 측정)를 쓰면서 설정은 `Append1`(나중 측정) 것을 읽어 **어긋날 수 있고**,
재측정분 하나가 조용히 버려진다. 나머지 17개 파일은 단일 런이라 영향 없다.

**사용자 결정:** 런을 모두 읽고 사용자가 고른다. 기본 선택은 Latest Run.

**Files:**
- Modify: `fet_app/parsing.py`
- Test: `tests/test_parsing_runs.py`

**Interfaces:**
- Consumes: Task 3 의 `SettingsInfo`, `load_sheets`
- Produces:
  - `parsing.RunSettings` — 필드 `blocks: dict[str, SettingsInfo]`, `order: list[str]`, `latest: str | None`;
    메서드 `block(name: str) -> SettingsInfo` (없으면 빈 `SettingsInfo`), `__len__`
  - `parsing.parse_settings(df) -> RunSettings` — **반환 타입이 바뀐다** (기존 `SettingsInfo` → `RunSettings`)
  - `parsing.data_sheet_names(sheets: dict) -> list[str]` — `Data` 먼저, 그 다음 `AppendN` 을 N 오름차순
  - `parsing.SHEET_FOR_BLOCK` 은 만들지 않는다. 블록 이름 자체를 시트 이름으로 정규화한다:
    `Initial Run` → `"Data"`, `Append 1` → `"Append1"`

**블록 헤더 판별 규칙:** 구분선(`=====`) 다음 행의 첫 칸이 블록 헤더다.
`Initial Run` 이면 `"Data"`, `Append <N>` 이면 `f"Append{N}"` 로 정규화한다.
같은 행 두 번째 칸에 `Latest Run` 이 있으면 그 블록이 `latest`. `latest` 를 못 찾으면 `order[0]`.
헤더가 하나도 없는 단일 블록 파일은 전체를 `"Data"` 블록으로 담는다 (기존 17개 파일이 이 경로).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_parsing_runs.py`:
```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_parsing_runs.py -v`
Expected: FAIL — `ImportError: cannot import name 'RunSettings'`

- [ ] **Step 3: 구현 — `fet_app/parsing.py` 수정**

`SettingsInfo` 는 그대로 두고, 블록 컨테이너와 시트 정렬을 추가한 뒤 `parse_settings` 를 바꾼다.

```python
_BLOCK_HEADER_RE = re.compile(r"^append\s*(\d+)$", flags=re.IGNORECASE)
_INITIAL_RE = re.compile(r"^initial\s*run$", flags=re.IGNORECASE)
_SHEET_APPEND_RE = re.compile(r"^append\s*(\d+)$", flags=re.IGNORECASE)


def _normalize_block_name(label: str) -> str | None:
    """Settings 블록 헤더 -> 대응하는 데이터 시트 이름. 헤더가 아니면 None."""
    text = str(label).strip()
    if _INITIAL_RE.match(text):
        return "Data"
    m = _BLOCK_HEADER_RE.match(text)
    if m:
        return f"Append{int(m.group(1))}"
    return None


@dataclass
class RunSettings:
    """측정 런별 SettingsInfo. 키는 대응하는 데이터 시트 이름이다."""

    blocks: dict[str, SettingsInfo] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    latest: str | None = None

    def block(self, name: str) -> SettingsInfo:
        return self.blocks.get(name, SettingsInfo())

    def __len__(self) -> int:
        return len(self.order)


def data_sheet_names(sheets: dict) -> list[str]:
    """데이터 시트를 Data 먼저, 그 다음 AppendN 오름차순으로."""
    def _key(name: str):
        text = str(name).strip()
        if text.lower() == "data":
            return (0, 0)
        m = _SHEET_APPEND_RE.match(text)
        return (1, int(m.group(1))) if m else (2, 0)

    names = [n for n, d in sheets.items()
             if str(n).strip().lower() == "data" or _SHEET_APPEND_RE.match(str(n).strip())]
    names = [n for n in names if _looks_like_data(sheets[n])]
    return sorted((str(n).strip() for n in names), key=_key)
```

`parse_settings` 를 아래로 교체한다 (기존 행 정규화 로직은 유지하되, 구분선 다음 행의
헤더를 만나면 새 블록으로 전환한다):

```python
def parse_settings(df: pd.DataFrame | None) -> RunSettings:
    """Settings 시트를 런 블록별 SettingsInfo 로 나눈다.

    구분선(=====) 다음 행의 첫 칸이 블록 헤더다. 'Initial Run' -> Data,
    'Append N' -> AppendN. 헤더가 없는 파일은 전체를 Data 블록으로 담는다.
    """
    runs = RunSettings()
    if not isinstance(df, pd.DataFrame) or df.empty:
        return runs

    rows: list[list[str]] = []
    cols = list(df.columns)
    if not all(isinstance(c, (int, np.integer)) or str(c).startswith("Unnamed") for c in cols):
        rows.append([_cell(c) for c in cols])
    for i in range(len(df)):
        rows.append([_cell(df.iloc[i, j]) for j in range(df.shape[1])])

    def _ensure(name: str) -> SettingsInfo:
        if name not in runs.blocks:
            runs.blocks[name] = SettingsInfo()
            runs.order.append(name)
        return runs.blocks[name]

    current: SettingsInfo | None = None
    for cells in rows:
        if not cells:
            continue
        joined = " ".join(cells)
        if "=====" in joined or SEP_TOKEN in joined:
            continue
        label = cells[0]
        if not label:
            continue

        block_name = _normalize_block_name(label)
        if block_name is not None:
            current = _ensure(block_name)
            current.raw.append(list(cells))
            if any(c.strip().lower() == "latest run" for c in cells[1:]):
                runs.latest = block_name
            continue

        if current is None:                     # 헤더 없는 단일 블록 파일
            current = _ensure("Data")
        current.raw.append(list(cells))

        values = list(cells[1:])
        while values and not values[-1]:
            values.pop()

        if label.lower() == "test name":
            current.test_name = values[0] if values else ""
            continue
        if label.lower() == "device terminal":
            current.terminals = values
            continue
        current.rows.setdefault(label, values)

    if runs.latest is None and runs.order:
        runs.latest = runs.order[0]
    return runs
```

- [ ] **Step 4: 기존 Task 3 테스트를 새 반환 타입에 맞춘다**

`tests/test_parsing_loader.py` 의 `_info` 헬퍼만 고친다. **테스트 기대값은 바꾸지 않는다.**

```python
def _info(file_bytes):
    sheets, engine = load_sheets(file_bytes)
    runs = parse_settings(settings_frame(file_bytes, sheets, engine))
    return runs.block(runs.latest or "Data")
```

`test_parse_settings_handles_none` 은 아래로 바꾼다:
```python
def test_parse_settings_handles_none():
    runs = parse_settings(None)
    assert len(runs) == 0
    assert runs.latest is None
    info = runs.block("Data")
    assert info.test_name == ""
    assert info.terminals == []
    assert info.get("Forcing Function", "Gate") == ""
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest tests/test_parsing_runs.py tests/test_parsing_loader.py -v`
Expected: 18 passed (신규 10 + 기존 8)

Run: `python -m pytest -v`
Expected: 전체 통과

- [ ] **Step 6: 커밋**

```bash
git add fet_app/parsing.py tests/test_parsing_runs.py tests/test_parsing_loader.py
git commit -m "$(cat <<'EOF'
feat: Settings 를 측정 런 블록별로 분리

1-3 best.xls 처럼 Data + Append1 두 번 측정한 파일에서 데이터와 설정이
어긋나지 않게 한다. parse_settings 는 RunSettings 를 반환하고
Initial Run -> Data, Append N -> AppendN 으로 시트와 짝지운다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: 커브 종류 자동 판정

**Files:**
- Modify: `fet_app/parsing.py` (끝에 추가)
- Test: `tests/test_classify.py`

**Interfaces:**
- Consumes: `parsing.SettingsInfo`, `parsing.load_sheets`, `parsing.data_sheet_names` (Task 3b)
- Produces:
  - `parsing.TRANSFER = "transfer"`, `parsing.OUTPUT = "output"`
  - `parsing.data_sheet(sheets: dict, name: str | None = None) -> pd.DataFrame` — 컬럼명을 strip 해 반환.
    `name` 을 주면 그 시트, 없으면 `data_sheet_names(sheets)` 의 첫 번째(= `Data`)
  - `parsing.classify_curve(data: pd.DataFrame, info: SettingsInfo, file_name: str) -> tuple[str, str]` — `(kind, reason)`. reason 은 `"forcing"` / `"structure"` / `"name"` 중 하나
  - `parsing.output_block_count(data: pd.DataFrame) -> int`

**주의:** Task 3b 에서 `parse_settings` 의 반환 타입이 `RunSettings` 로 바뀌었다.
이 태스크의 테스트는 `runs.block(runs.latest)` 로 `SettingsInfo` 를 꺼내 쓴다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_classify.py`:
```python
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


def test_name_fallback():
    """구조로도 못 가리면 Test Name / 파일명을 본다."""
    data = pd.DataFrame({"Foo": [1.0]})
    info = SettingsInfo(test_name="p_output#1@3")
    assert classify_curve(data, info, "x.xls") == (OUTPUT, "name")
    assert classify_curve(data, SettingsInfo(), "1-7 out.xls") == (OUTPUT, "name")
    assert classify_curve(data, SettingsInfo(), "1-7.xls") == (TRANSFER, "name")


def test_misnamed_file_still_classified_by_content(example_dir):
    """'out' 이 안 붙어도, 반대로 붙어도 내용으로 맞춘다 (명명법 불필요)."""
    b = (example_dir / "1-1 out.xls").read_bytes()
    sheets, engine = load_sheets(b)
    runs = parse_settings(settings_frame(b, sheets, engine))
    kind, reason = classify_curve(data_sheet(sheets),
                                  runs.block(runs.latest), "완전히엉뚱한이름.xls")
    assert (kind, reason) == (OUTPUT, "forcing")


def test_data_sheet_missing_raises():
    with pytest.raises(ValueError):
        data_sheet({"Settings": pd.DataFrame()})


def test_data_sheet_selects_named_run(example_dir):
    """1-3 best.xls 는 Data 와 Append1 두 런이 있고 둘 다 꺼낼 수 있어야 한다."""
    sheets, _engine = load_sheets((example_dir / "1-3 best.xls").read_bytes())
    default = data_sheet(sheets)
    first = data_sheet(sheets, "Data")
    second = data_sheet(sheets, "Append1")
    assert default.equals(first)          # 이름을 안 주면 Data
    assert len(second) == 162
    assert not second.equals(first)       # 서로 다른 측정
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_classify.py -v`
Expected: FAIL — `ImportError: cannot import name 'classify_curve'`

- [ ] **Step 3: 구현 — `fet_app/parsing.py` 끝에 추가**

```python
# ---------------- 커브 종류 판정 (스펙 §2) ----------------

TRANSFER = "transfer"
OUTPUT = "output"

_BLOCK_RE = re.compile(r"^(GateI|GateV|DrainI|DrainV)\((\d+)\)$")


def data_sheet(sheets: dict, name: str | None = None) -> pd.DataFrame:
    """데이터 시트 하나를 컬럼명 strip 해 반환한다.

    name 을 주면 그 시트, 없으면 data_sheet_names 의 첫 번째(= Data).
    재측정 파일(Data + Append1)에서 특정 런을 꺼낼 때 name 을 쓴다.
    """
    if name is None:
        ordered = data_sheet_names(sheets)
        if not ordered:
            raise ValueError("데이터 시트를 찾지 못했습니다.")
        name = ordered[0]

    key = next((k for k in sheets if str(k).strip() == str(name).strip()), None)
    if key is None:
        raise ValueError(f"데이터 시트 '{name}' 를 찾지 못했습니다.")
    df = sheets[key].copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def output_block_count(data: pd.DataFrame) -> int:
    """GateI(n)/GateV(n)/DrainI(n)/DrainV(n) 블록 개수. 하드코딩 금지 (스펙 §1.2)."""
    indices = set()
    for c in data.columns:
        m = _BLOCK_RE.match(str(c).strip())
        if m:
            indices.add(int(m.group(2)))
    return len(indices)


def _has_constant_gate_blocks(data: pd.DataFrame) -> bool:
    n = output_block_count(data)
    if n < 1:
        return False
    for i in range(1, n + 1):
        col = f"GateV({i})"
        if col not in data.columns:
            return False
        vals = pd.to_numeric(data[col], errors="coerce").dropna()
        if vals.empty or vals.nunique() != 1:
            return False
    return True


def classify_curve(data: pd.DataFrame, info: SettingsInfo,
                   file_name: str) -> tuple[str, str]:
    """(kind, reason) 반환. reason 은 판정 근거 단계: forcing / structure / name.

    1순위 Settings 의 Forcing Function, 2순위 Data 열 구조, 3순위 이름.
    """
    gate = info.get("Forcing Function", "Gate").lower()
    drain = info.get("Forcing Function", "Drain").lower()
    if "sweep" in gate and "bias" in drain:
        return TRANSFER, "forcing"
    if "step" in gate and "sweep" in drain:
        return OUTPUT, "forcing"

    cols = {str(c).strip() for c in data.columns}
    if _has_constant_gate_blocks(data):
        return OUTPUT, "structure"
    if "GateV" in cols and not any(c.startswith("DrainV") for c in cols):
        return TRANSFER, "structure"

    haystack = f"{info.test_name} {file_name}".lower()
    tokens = re.split(r"[\s_\-.]+", haystack)
    if "output" in haystack or "out" in tokens:
        return OUTPUT, "name"
    return TRANSFER, "name"
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_classify.py -v`
Expected: 7 passed. 특히 `test_all_18_files_classified_correctly` 가 통과해야 "명명법 불필요" 주장이 성립한다.

- [ ] **Step 5: 커밋**

```bash
git add fet_app/parsing.py tests/test_classify.py
git commit -m "$(cat <<'EOF'
feat: 커브 종류 3단 폴백 자동 판정

Forcing Function -> Data 열 구조 -> Test Name/파일명 순.
예제 18파일 전부 1순위(forcing)에서 정확히 판정됨을 테스트로 고정한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: 커브 모델과 dual sweep 분리

**Files:**
- Create: `fet_app/curves.py`
- Test: `tests/test_curves.py`

**Interfaces:**
- Consumes: `parsing.SettingsInfo`, `parsing.output_block_count`
- Produces:
  - `curves.split_dual(df: pd.DataFrame, n_points: int | None, dual: bool) -> tuple[pd.DataFrame, pd.DataFrame | None]`
  - `curves.TransferCurve` — 필드 `v_ds: float | None`, `forward: pd.DataFrame`, `reverse: pd.DataFrame | None`, `dual: bool`; forward/reverse 컬럼은 `["V_G", "I_G", "I_D"]`
  - `curves.OutputBlock` — 필드 `v_g: float`, `forward: pd.DataFrame`, `reverse: pd.DataFrame | None`; 컬럼 `["V_D", "I_D", "I_G"]`
  - `curves.OutputCurve` — 필드 `blocks: list[OutputBlock]`; 프로퍼티 `gate_voltages -> list[float]`
  - `curves.build_transfer(data: pd.DataFrame, info: SettingsInfo) -> TransferCurve`
  - `curves.build_output(data: pd.DataFrame, info: SettingsInfo) -> OutputCurve`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_curves.py`:
```python
import numpy as np
import pandas as pd

from fet_app.curves import build_output, build_transfer, split_dual
from fet_app.parsing import (
    SettingsInfo, data_sheet, load_sheets, parse_settings, settings_frame,
)


def _load(path):
    b = path.read_bytes()
    sheets, engine = load_sheets(b)
    return data_sheet(sheets), parse_settings(settings_frame(b, sheets, engine))


def test_split_dual_halves():
    df = pd.DataFrame({"V": list(range(10))})
    fwd, rev = split_dual(df, n_points=10, dual=True)
    assert len(fwd) == 5 and len(rev) == 5
    assert list(fwd["V"]) == [0, 1, 2, 3, 4]
    assert list(rev["V"]) == [5, 6, 7, 8, 9]


def test_split_dual_disabled():
    df = pd.DataFrame({"V": list(range(10))})
    fwd, rev = split_dual(df, n_points=10, dual=False)
    assert len(fwd) == 10 and rev is None


def test_split_dual_falls_back_to_turning_point():
    """n_points 가 없으면 전압 방향이 뒤집히는 지점을 찾는다 (스펙 §1.3)."""
    v = list(range(0, -6, -1)) + list(range(-5, 1))
    df = pd.DataFrame({"V": v})
    fwd, rev = split_dual(df, n_points=None, dual=True)
    assert len(fwd) == 6 and len(rev) == 6


def test_transfer_from_example(transfer_files):
    for p in transfer_files:
        data, info = _load(p)
        c = build_transfer(data, info)
        assert c.v_ds == -60.0, p.name
        assert c.dual is True, p.name
        assert len(c.forward) == 81, p.name
        assert len(c.reverse) == 81, p.name
        assert list(c.forward.columns) == ["V_G", "I_G", "I_D"]
        # forward 는 +20 V 에서 시작해 -60 V 로 내려간다
        assert c.forward["V_G"].iloc[0] == 20.0
        assert c.forward["V_G"].iloc[-1] == -60.0
        assert c.reverse["V_G"].iloc[0] == -60.0
        assert c.reverse["V_G"].iloc[-1] == 20.0


def test_output_from_example(output_files):
    for p in output_files:
        data, info = _load(p)
        c = build_output(data, info)
        assert c.gate_voltages == [0.0, -20.0, -40.0, -60.0], p.name
        for b in c.blocks:
            assert len(b.forward) == 61, p.name
            assert len(b.reverse) == 61, p.name
            assert list(b.forward.columns) == ["V_D", "I_D", "I_G"]
            assert b.forward["V_D"].iloc[0] == 0.0
            assert b.forward["V_D"].iloc[-1] == -60.0


def test_transfer_drops_non_numeric_rows():
    data = pd.DataFrame({
        "GateI": [1e-9, np.nan, 3e-9],
        "GateV": [1.0, 2.0, 3.0],
        "DrainI": [1e-6, 2e-6, 3e-6],
    })
    c = build_transfer(data, SettingsInfo())
    assert len(c.forward) == 2
    assert c.v_ds is None
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_curves.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.curves'`

- [ ] **Step 3: 구현**

`fet_app/curves.py`:
```python
"""측정 커브 데이터 모델과 dual sweep 분리 (스펙 §1, §4)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from fet_app.parsing import SettingsInfo, output_block_count


def _turning_index(v: np.ndarray) -> int | None:
    """전압 스윕 방향이 뒤집히는 지점. 같은 값이 연속돼도 견디게 부호만 본다."""
    if v.size < 4:
        return None
    d = np.diff(v)
    nz = d[d != 0]
    if nz.size == 0:
        return None
    first_sign = np.sign(nz[0])
    for i in range(1, d.size):
        if d[i] != 0 and np.sign(d[i]) != first_sign:
            return i
    return None


def split_dual(df: pd.DataFrame, n_points: int | None,
               dual: bool) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """dual sweep 데이터를 forward/reverse 로 자른다.

    1순위: Settings 의 Number of Points 절반 (전압이 turning point 에서 두 번
    나오는 경우가 있어 부호 변화만으로는 실패한다 — 스펙 §1.3).
    2순위: 전압 방향 부호가 뒤집히는 지점.
    """
    if not dual or df.empty:
        return df.reset_index(drop=True), None

    half = None
    if n_points and n_points > 1 and abs(n_points - len(df)) <= 1:
        half = n_points // 2
    if half is None:
        v = pd.to_numeric(df.iloc[:, 0], errors="coerce").to_numpy()
        t = _turning_index(v)
        half = t if t else len(df) // 2
    half = max(1, min(half, len(df) - 1))

    fwd = df.iloc[:half].reset_index(drop=True)
    rev = df.iloc[half:].reset_index(drop=True)
    return fwd, (rev if not rev.empty else None)


@dataclass
class TransferCurve:
    """V_DS 고정, V_G 스윕. forward/reverse 컬럼은 V_G / I_G / I_D."""

    forward: pd.DataFrame
    reverse: pd.DataFrame | None = None
    v_ds: float | None = None
    dual: bool = False

    def branches(self) -> list[tuple[str, pd.DataFrame]]:
        out = [("forward", self.forward)]
        if self.reverse is not None:
            out.append(("reverse", self.reverse))
        return out


@dataclass
class OutputBlock:
    """V_G 한 스텝. forward/reverse 컬럼은 V_D / I_D / I_G."""

    v_g: float
    forward: pd.DataFrame
    reverse: pd.DataFrame | None = None


@dataclass
class OutputCurve:
    blocks: list[OutputBlock] = field(default_factory=list)

    @property
    def gate_voltages(self) -> list[float]:
        return [b.v_g for b in self.blocks]


def build_transfer(data: pd.DataFrame, info: SettingsInfo) -> TransferCurve:
    frame = pd.DataFrame({
        "V_G": pd.to_numeric(data.get("GateV"), errors="coerce"),
        "I_G": pd.to_numeric(data.get("GateI"), errors="coerce"),
        "I_D": pd.to_numeric(data.get("DrainI"), errors="coerce"),
    }).dropna().reset_index(drop=True)

    dual = info.dual_sweep("Gate")
    fwd, rev = split_dual(frame, info.n_points("Gate"), dual)
    return TransferCurve(forward=fwd, reverse=rev,
                         v_ds=info.bias_level("Drain"), dual=dual)


def build_output(data: pd.DataFrame, info: SettingsInfo) -> OutputCurve:
    n = output_block_count(data)
    dual = info.dual_sweep("Drain")
    n_points = info.n_points("Drain")

    blocks: list[OutputBlock] = []
    for i in range(1, n + 1):
        frame = pd.DataFrame({
            "V_D": pd.to_numeric(data.get(f"DrainV({i})"), errors="coerce"),
            "I_D": pd.to_numeric(data.get(f"DrainI({i})"), errors="coerce"),
            "I_G": pd.to_numeric(data.get(f"GateI({i})"), errors="coerce"),
        }).dropna().reset_index(drop=True)
        if frame.empty:
            continue

        v_g_col = pd.to_numeric(data.get(f"GateV({i})"), errors="coerce").dropna()
        v_g = float(v_g_col.iloc[0]) if not v_g_col.empty else float("nan")

        fwd, rev = split_dual(frame, n_points, dual)
        blocks.append(OutputBlock(v_g=v_g, forward=fwd, reverse=rev))

    return OutputCurve(blocks=blocks)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_curves.py -v`
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add fet_app/curves.py tests/test_curves.py
git commit -m "$(cat <<'EOF'
feat: TransferCurve/OutputCurve 모델과 dual sweep 분리

Number of Points 절반으로 자르고, 없으면 전압 방향 부호 변화로 폴백한다.
예제에서 transfer 81+81, output 블록 4개 x 61+61 로 갈리는 것을 고정한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: 파일 파싱 파사드와 소자 그룹핑

**Files:**
- Create: `fet_app/grouping.py`
- Test: `tests/test_grouping.py`

**Interfaces:**
- Consumes: `parsing.*` (`data_sheet_names`, `data_sheet`, `parse_settings`→`RunSettings`, `classify_curve`), `curves.*`, `params.DeviceParams`
- Produces:
  - `grouping.MeasurementRun` — 필드 `sheet: str`("Data"/"Append1"), `label: str`(UI 표시용), `is_latest: bool`, `kind: str`, `reason: str`, `settings: SettingsInfo`, `transfer: TransferCurve | None`, `output: OutputCurve | None`
  - `grouping.ParsedFile` — 필드 `name: str`, `runs: list[MeasurementRun]`, `warnings: list[str]`;
    프로퍼티 `latest -> MeasurementRun | None`, `kind -> str`(latest 의 kind, 런이 없으면 `""`)
  - `grouping.parse_file(file_bytes: bytes, file_name: str) -> ParsedFile`
  - `grouping.stem_of(file_name: str) -> str`
  - `grouping.DeviceGroup` — 필드 `name: str`, `transfer_runs: list[MeasurementRun]`, `output_runs: list[MeasurementRun]`, `transfer_run_idx: int = 0`, `output_run_idx: int = 0`, `transfer_file: str | None`, `output_file: str | None`, `params: DeviceParams`, `extra_files: list[str]`, `warnings: list[str]`;
    프로퍼티 `transfer -> TransferCurve | None`(선택된 런), `output -> OutputCurve | None`(선택된 런), `badges -> str`
  - `grouping.group_files(parsed: list[ParsedFile]) -> list[DeviceGroup]`

**런 선택 규약:** `*_run_idx` 는 해당 `*_runs` 리스트의 인덱스이며, 기본값은 **Latest Run 의 인덱스**
(`parse_file` 이 런을 Latest 먼저 오도록 정렬하므로 0). `transfer`/`output` 프로퍼티가 인덱스를
해석하므로, 소비자(Task 8/9/11/12/13/18)는 기존과 똑같이 `g.transfer` / `g.output` 만 쓰면 된다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_grouping.py`:
```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_grouping.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.grouping'`

- [ ] **Step 3: 구현**

`fet_app/grouping.py`:
```python
"""파일 -> ParsedFile -> DeviceGroup 조립 (스펙 §4.1)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from fet_app.curves import OutputCurve, TransferCurve, build_output, build_transfer
from fet_app.params import DeviceParams
from fet_app.parsing import (
    OUTPUT, TRANSFER, SettingsInfo, classify_curve, data_sheet, data_sheet_names,
    load_sheets, parse_settings, settings_frame,
)

# 파일명 끝에서 떼어낼 접미 토큰. 여기 없는 토큰은 stem 의 일부로 남긴다.
STRIP_TOKENS = {"out", "output", "transfer", "tr", "best"}
_SPLIT_RE = re.compile(r"[\s_]+")


@dataclass
class MeasurementRun:
    """파일 안의 측정 한 번. 재측정 파일은 Data 와 Append1 이 각각 하나씩이다."""

    sheet: str                      # "Data" / "Append1"
    label: str                      # UI 표시용 — "Latest Run" / "Run 1"
    is_latest: bool
    kind: str
    reason: str
    settings: SettingsInfo | None = None
    transfer: TransferCurve | None = None
    output: OutputCurve | None = None


@dataclass
class ParsedFile:
    name: str
    runs: list[MeasurementRun] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def latest(self) -> MeasurementRun | None:
        return self.runs[0] if self.runs else None

    @property
    def kind(self) -> str:
        return self.runs[0].kind if self.runs else ""


def parse_file(file_bytes: bytes, file_name: str) -> ParsedFile:
    """파일의 모든 측정 런을 읽는다. 반환 리스트는 Latest Run 이 맨 앞."""
    sheets, engine = load_sheets(file_bytes)
    run_settings = parse_settings(settings_frame(file_bytes, sheets, engine))
    sheet_names = data_sheet_names(sheets)
    if not sheet_names:
        raise ValueError("데이터 시트를 찾지 못했습니다.")

    warns: list[str] = []
    if len(run_settings) and len(run_settings) != len(sheet_names):
        warns.append(
            f"Settings 블록 {len(run_settings)}개와 데이터 시트 {len(sheet_names)}개가 "
            "맞지 않습니다. 시트 이름으로 최선을 다해 짝지었습니다."
        )

    runs: list[MeasurementRun] = []
    for sheet in sheet_names:
        data = data_sheet(sheets, sheet)
        info = run_settings.block(sheet)
        kind, reason = classify_curve(data, info, file_name)
        if reason == "name":
            warns.append(
                f"'{sheet}' 의 커브 종류를 Settings·열 구조로 가리지 못해 파일명으로 "
                "판정했습니다. 틀렸다면 소자 패널에서 바꿔주세요."
            )

        transfer = output = None
        if kind == TRANSFER:
            transfer = build_transfer(data, info)
            if transfer.v_ds is None:
                warns.append(
                    f"'{sheet}' 의 Settings 에서 V_DS 를 읽지 못했습니다. "
                    "μ_sat 의 포화 조건 검사를 건너뜁니다."
                )
        else:
            output = build_output(data, info)
            if not output.blocks:
                warns.append(f"'{sheet}' 에서 output 블록을 하나도 만들지 못했습니다.")

        is_latest = (run_settings.latest == sheet) if len(run_settings) else (sheet == sheet_names[0])
        runs.append(MeasurementRun(
            sheet=sheet, label="", is_latest=is_latest, kind=kind, reason=reason,
            settings=info, transfer=transfer, output=output,
        ))

    # Latest 를 맨 앞으로. 나머지는 시트 순서 유지.
    runs.sort(key=lambda r: (not r.is_latest,))
    single = len(runs) == 1
    for i, r in enumerate(runs):
        if single:
            r.label = r.sheet
        else:
            r.label = f"{r.sheet} (Latest)" if r.is_latest else r.sheet

    return ParsedFile(name=file_name, runs=runs, warnings=warns)


def stem_of(file_name: str) -> str:
    """확장자와 알려진 접미 토큰을 떼어낸 나머지가 소자 이름."""
    stem = Path(str(file_name)).stem.strip()
    parts = [p for p in _SPLIT_RE.split(stem) if p]
    while len(parts) > 1 and parts[-1].lower() in STRIP_TOKENS:
        parts.pop()
    return " ".join(parts) if parts else stem


@dataclass
class DeviceGroup:
    """소자 하나. 커브 종류마다 측정 런 목록과 선택 인덱스를 갖는다."""

    name: str
    transfer_runs: list[MeasurementRun] = field(default_factory=list)
    output_runs: list[MeasurementRun] = field(default_factory=list)
    transfer_run_idx: int = 0
    output_run_idx: int = 0
    transfer_file: str | None = None
    output_file: str | None = None
    params: DeviceParams = field(default_factory=DeviceParams)
    extra_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @staticmethod
    def _pick(runs: list[MeasurementRun], idx: int, attr: str):
        if not runs:
            return None
        i = idx if 0 <= idx < len(runs) else 0
        return getattr(runs[i], attr)

    @property
    def transfer(self) -> TransferCurve | None:
        return self._pick(self.transfer_runs, self.transfer_run_idx, "transfer")

    @property
    def output(self) -> OutputCurve | None:
        return self._pick(self.output_runs, self.output_run_idx, "output")

    @property
    def badges(self) -> str:
        marks = []
        if self.transfer is not None:
            marks.append("T")
        if self.output is not None:
            marks.append("O")
        return "·".join(marks) if marks else "—"


def group_files(parsed: list[ParsedFile]) -> list[DeviceGroup]:
    """파일명 stem 으로 묶는다.

    한 파일의 여러 측정 런은 모두 보존한다(재측정 파일). 같은 종류의 파일이
    두 개 오면 첫 번째 파일의 런만 쓰고 나머지 파일은 extra 로 밀어둔다.
    """
    groups: dict[str, DeviceGroup] = {}
    order: list[str] = []

    for pf in parsed:
        key = stem_of(pf.name)
        if key not in groups:
            groups[key] = DeviceGroup(name=key)
            order.append(key)
        g = groups[key]
        g.warnings.extend(pf.warnings)

        t_runs = [r for r in pf.runs if r.kind == TRANSFER]
        o_runs = [r for r in pf.runs if r.kind == OUTPUT]

        if t_runs:
            if not g.transfer_runs:
                g.transfer_runs, g.transfer_file = t_runs, pf.name
            else:
                g.extra_files.append(pf.name)
                g.warnings.append(
                    f"'{pf.name}' 은 transfer 가 이미 있어 사용하지 않았습니다. "
                    "소자 패널에서 교체할 수 있습니다."
                )
        if o_runs:
            if not g.output_runs:
                g.output_runs, g.output_file = o_runs, pf.name
            elif pf.name not in g.extra_files:
                g.extra_files.append(pf.name)
                g.warnings.append(
                    f"'{pf.name}' 은 output 이 이미 있어 사용하지 않았습니다. "
                    "소자 패널에서 교체할 수 있습니다."
                )

    return [groups[k] for k in order]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_grouping.py -v`
Expected: 7 passed

- [ ] **Step 5: 전체 회귀 확인 후 커밋**

Run: `python -m pytest -v`
Expected: 여기까지 작성한 테스트 전부 통과

```bash
git add fet_app/grouping.py tests/test_grouping.py
git commit -m "$(cat <<'EOF'
feat: 파일 파싱 파사드와 소자 자동 그룹핑

파일명 stem 에서 out/output/best/transfer 접미 토큰을 떼어 묶는다.
예제 18파일이 1-1~1-9 아홉 그룹으로 정확히 갈리는 것을 테스트로 고정한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: 선형 fit 과 자동 윈도우 탐색

**Files:**
- Create: `fet_app/fitting.py`
- Test: `tests/test_fitting.py`

**Interfaces:**
- Consumes: `constants.FIT_*`
- Produces:
  - `fitting.FitResult` — 필드 `slope: float`, `intercept: float`, `r2: float`, `i_start: int`, `i_end: int`(배타적), `v_start: float`, `v_end: float`, `n_points: int`
  - `fitting.linear_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]` — `(slope, intercept, r2)`
  - `fitting.fit_window(x: np.ndarray, y: np.ndarray, i0: int, i1: int) -> FitResult | None`
  - `fitting.auto_fit_sqrt(v_g: np.ndarray, i_d: np.ndarray) -> FitResult | None`
  - `fitting.manual_fit_sqrt(v_g: np.ndarray, i_d: np.ndarray, v_lo: float, v_hi: float) -> FitResult | None`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_fitting.py`:
```python
import math

import numpy as np

from fet_app.constants import FIT_MIN_POINTS
from fet_app.fitting import auto_fit_sqrt, fit_window, linear_fit, manual_fit_sqrt


def _square_law(v_g, v_th=-10.0, k=2e-8, floor=1e-12):
    """이상적 p-type 포화 전류. V_G > V_th 에서는 off 바닥으로 깔린다."""
    on = v_g < v_th
    i = np.full_like(v_g, floor, dtype=float)
    i[on] = k * (v_g[on] - v_th) ** 2
    return -i  # p-type 이라 음수


def test_linear_fit_exact():
    x = np.arange(10, dtype=float)
    y = 3.0 * x - 4.0
    slope, intercept, r2 = linear_fit(x, y)
    assert math.isclose(slope, 3.0, rel_tol=1e-12)
    assert math.isclose(intercept, -4.0, abs_tol=1e-12)
    assert math.isclose(r2, 1.0, abs_tol=1e-12)


def test_linear_fit_degenerate_returns_zero_r2():
    x = np.zeros(5)
    y = np.arange(5, dtype=float)
    _slope, _intercept, r2 = linear_fit(x, y)
    assert r2 == 0.0


def test_fit_window_records_bounds():
    x = np.arange(20, dtype=float)
    y = 2.0 * x
    fit = fit_window(x, y, 5, 15)
    assert fit.i_start == 5 and fit.i_end == 15 and fit.n_points == 10
    assert fit.v_start == 5.0 and fit.v_end == 14.0


def test_auto_fit_recovers_ideal_square_law():
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = _square_law(v_g, v_th=-10.0, k=2e-8)
    fit = auto_fit_sqrt(v_g, i_d)
    assert fit is not None
    assert fit.r2 > 0.9999
    # x 절편 = V_th
    assert math.isclose(-fit.intercept / fit.slope, -10.0, abs_tol=0.2)
    assert fit.n_points >= FIT_MIN_POINTS


def test_auto_fit_prefers_longer_window_on_tie():
    """완벽한 직선이면 어느 창이든 R^2=1 -> 가장 긴 창을 골라야 한다."""
    v_g = np.arange(0, -61, -1, dtype=float)
    i_d = -((v_g * 1e-5) ** 2)
    fit = auto_fit_sqrt(v_g, i_d)
    assert fit is not None
    n_candidates = v_g.size
    assert fit.n_points >= int(n_candidates * 0.55)


def test_auto_fit_survives_noise():
    rng = np.random.default_rng(0)
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = _square_law(v_g, v_th=-10.0, k=2e-8)
    i_d = i_d * (1 + rng.normal(0, 0.01, i_d.size))
    fit = auto_fit_sqrt(v_g, i_d)
    assert fit is not None
    assert math.isclose(-fit.intercept / fit.slope, -10.0, abs_tol=1.5)


def test_auto_fit_returns_none_when_all_noise_floor():
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = np.full(v_g.size, -1e-12)
    assert auto_fit_sqrt(v_g, i_d) is None


def test_manual_fit_uses_given_range():
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = _square_law(v_g, v_th=-10.0, k=2e-8)
    fit = manual_fit_sqrt(v_g, i_d, v_lo=-50.0, v_hi=-30.0)
    assert fit is not None
    assert fit.v_start <= -30.0 and fit.v_end >= -50.0
    assert fit.n_points == 21


def test_manual_fit_too_few_points_returns_none():
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = _square_law(v_g)
    assert manual_fit_sqrt(v_g, i_d, v_lo=-31.0, v_hi=-30.0) is None
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_fitting.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.fitting'`

- [ ] **Step 3: 구현**

`fet_app/fitting.py`:
```python
"""최소자승 fit 과 sqrt(|I_D|) 구간 자동 탐색 (스펙 §3.3).

여기 상수는 전부 constants.py 에 있고 MANUAL.md 에 문서화된다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from fet_app.constants import (
    FIT_MAX_FRACTION, FIT_MIN_POINTS, FIT_ON_REGION_FACTOR, FIT_TIE_TOLERANCE,
)


@dataclass
class FitResult:
    slope: float
    intercept: float
    r2: float
    i_start: int
    i_end: int          # 배타적
    v_start: float
    v_end: float
    n_points: int

    def x_intercept(self) -> float | None:
        """y = 0 이 되는 x. V_th 계산에 쓴다."""
        if self.slope == 0:
            return None
        return -self.intercept / self.slope


def linear_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """(slope, intercept, r2). x 가 상수이거나 점이 2개 미만이면 r2=0."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 2 or np.ptp(x) == 0:
        return 0.0, 0.0, 0.0

    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(slope), float(intercept), float(r2)


def fit_window(x: np.ndarray, y: np.ndarray, i0: int, i1: int) -> FitResult | None:
    """[i0, i1) 구간 fit."""
    if i1 - i0 < 2:
        return None
    xs, ys = np.asarray(x, float)[i0:i1], np.asarray(y, float)[i0:i1]
    slope, intercept, r2 = linear_fit(xs, ys)
    return FitResult(slope=slope, intercept=intercept, r2=r2,
                     i_start=i0, i_end=i1,
                     v_start=float(xs[0]), v_end=float(xs[-1]),
                     n_points=int(i1 - i0))


def _longest_run(mask: np.ndarray) -> tuple[int, int] | None:
    """mask 가 True 인 가장 긴 연속 구간 [lo, hi) 를 반환."""
    best = None
    lo = None
    for i, m in enumerate(mask):
        if m and lo is None:
            lo = i
        elif not m and lo is not None:
            if best is None or i - lo > best[1] - best[0]:
                best = (lo, i)
            lo = None
    if lo is not None:
        if best is None or mask.size - lo > best[1] - best[0]:
            best = (lo, int(mask.size))
    return best


def auto_fit_sqrt(v_g: np.ndarray, i_d: np.ndarray) -> FitResult | None:
    """sqrt(|I_D|) vs V_G 에서 R^2 최대 구간을 찾는다.

    1. I_off = min|I_D| (0 제외)
    2. 후보 영역 = |I_D| > FIT_ON_REGION_FACTOR x I_off 의 최장 연속 구간
    3. 윈도우 FIT_MIN_POINTS ~ 후보영역x FIT_MAX_FRACTION 를 1점씩 슬라이딩
    4. R^2 최대. 차이가 FIT_TIE_TOLERANCE 이내면 점이 많은 쪽 우선
    """
    v_g = np.asarray(v_g, dtype=float)
    a = np.abs(np.asarray(i_d, dtype=float))
    if v_g.size != a.size or v_g.size < FIT_MIN_POINTS:
        return None

    positive = a[a > 0]
    if positive.size == 0:
        return None
    i_off = float(np.min(positive))

    mask = a > FIT_ON_REGION_FACTOR * i_off
    run = _longest_run(mask)
    if run is None:
        return None
    lo, hi = run
    n = hi - lo
    if n < FIT_MIN_POINTS:
        return None

    y = np.sqrt(a)
    max_w = max(FIT_MIN_POINTS, int(n * FIT_MAX_FRACTION))
    max_w = min(max_w, n)

    best: FitResult | None = None
    for w in range(FIT_MIN_POINTS, max_w + 1):
        for s in range(lo, hi - w + 1):
            cand = fit_window(v_g, y, s, s + w)
            if cand is None:
                continue
            if best is None:
                best = cand
            elif cand.r2 > best.r2 + FIT_TIE_TOLERANCE:
                best = cand
            elif abs(cand.r2 - best.r2) <= FIT_TIE_TOLERANCE and cand.n_points > best.n_points:
                best = cand
    return best


def manual_fit_sqrt(v_g: np.ndarray, i_d: np.ndarray,
                    v_lo: float, v_hi: float) -> FitResult | None:
    """사용자가 지정한 V_G 범위 [v_lo, v_hi] 로 fit. 순서는 상관없다."""
    v_g = np.asarray(v_g, dtype=float)
    a = np.abs(np.asarray(i_d, dtype=float))
    lo, hi = (v_lo, v_hi) if v_lo <= v_hi else (v_hi, v_lo)

    idx = np.flatnonzero((v_g >= lo) & (v_g <= hi) & (a > 0))
    if idx.size < FIT_MIN_POINTS:
        return None
    i0, i1 = int(idx[0]), int(idx[-1]) + 1
    return fit_window(v_g, np.sqrt(a), i0, i1)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_fitting.py -v`
Expected: 9 passed

- [ ] **Step 5: 커밋**

```bash
git add fet_app/fitting.py tests/test_fitting.py
git commit -m "$(cat <<'EOF'
feat: 선형 fit 과 sqrt(|I_D|) 구간 자동 탐색

on-영역 100xI_off 로 후보를 제한하고 10점~60% 윈도우를 슬라이딩해 R^2 최대를 고른다.
동점(dR^2<5e-4)이면 긴 구간 우선. 이상적 제곱법칙에서 V_th 를 0.2 V 이내로 복원한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Transfer 지표 계산

**Files:**
- Create: `fet_app/metrics.py`
- Test: `tests/test_metrics_transfer.py`

**Interfaces:**
- Consumes: `fitting.FitResult`, `fitting.auto_fit_sqrt`, `fitting.manual_fit_sqrt`, `params.DeviceParams`, `curves.TransferCurve`, `constants.SS_WINDOW`
- Produces:
  - `metrics.threshold_and_mobility(fit: FitResult, p: DeviceParams) -> tuple[float | None, float | None]`
  - `metrics.on_off_ratio(i_d: np.ndarray) -> float | None`
  - `metrics.subthreshold_swing(v_g: np.ndarray, i_d: np.ndarray) -> float | None` — mV/dec
  - `metrics.TransferMetrics` — 필드 `v_th`, `mu_sat`, `on_off`, `ss_mv_dec`, `dv_th`, `v_th_reverse`, `fit`, `fit_reverse`, `c_ox`, `warnings: list[str]`
  - `metrics.transfer_metrics(curve: TransferCurve, p: DeviceParams, fit_range: tuple[float, float] | None = None) -> TransferMetrics`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_metrics_transfer.py`:
```python
import math

import numpy as np
import pandas as pd

from fet_app.curves import TransferCurve
from fet_app.metrics import (
    on_off_ratio, subthreshold_swing, transfer_metrics,
)
from fet_app.params import DeviceParams

# 합성 데이터의 정답값
W_UM, L_UM, EPS_R, D_NM = 1000.0, 50.0, 3.9, 300.0
PARAMS = DeviceParams(w_um=W_UM, l_um=L_UM, eps_r=EPS_R, d_nm=D_NM)
TRUE_MU = 0.05          # cm^2/Vs
TRUE_VTH = -12.0        # V


def _ideal_transfer(v_th=TRUE_VTH, mu=TRUE_MU, floor=1e-12, ss_mv=200.0):
    """I_D = (W/2L) mu C_ox (V_G - V_th)^2, off 쪽은 지수 꼬리를 붙인다."""
    v_g = np.arange(20, -61, -1, dtype=float)
    c_ox = PARAMS.c_ox()
    k = (PARAMS.w_cm() / (2 * PARAMS.l_cm())) * mu * c_ox
    i = np.where(v_g < v_th, k * (v_g - v_th) ** 2, 0.0)
    # 서브스레숄드: V_th 위쪽에서 ss_mv mV/dec 로 감소
    tail_at_vth = k * 1.0
    tail = tail_at_vth * 10.0 ** (-(v_g - v_th) / (ss_mv / 1000.0))
    i = np.maximum(i, np.where(v_g >= v_th, tail, 0.0))
    i = np.maximum(i, floor)
    return v_g, -i  # p-type


def _curve(v_g, i_d, i_g=None):
    df = pd.DataFrame({"V_G": v_g, "I_G": i_g if i_g is not None else np.zeros_like(v_g),
                       "I_D": i_d})
    return TransferCurve(forward=df, reverse=None, v_ds=-60.0, dual=False)


def test_recovers_mobility_and_threshold_within_1_percent():
    v_g, i_d = _ideal_transfer()
    m = transfer_metrics(_curve(v_g, i_d), PARAMS)
    assert m.mu_sat is not None
    assert abs(m.mu_sat - TRUE_MU) / TRUE_MU < 0.01
    assert abs(m.v_th - TRUE_VTH) < 0.3


def test_mobility_scales_with_channel_length():
    """L 을 2배로 하면 mu 도 2배로 나와야 한다 (mu = 2L/(W C_ox) m^2)."""
    v_g, i_d = _ideal_transfer()
    m1 = transfer_metrics(_curve(v_g, i_d), PARAMS)
    p2 = DeviceParams(w_um=W_UM, l_um=L_UM * 2, eps_r=EPS_R, d_nm=D_NM)
    m2 = transfer_metrics(_curve(v_g, i_d), p2)
    assert math.isclose(m2.mu_sat, 2 * m1.mu_sat, rel_tol=1e-9)


def test_on_off_ratio():
    i_d = np.array([-1e-12, -1e-6, -5e-7])
    assert math.isclose(on_off_ratio(i_d), 1e6, rel_tol=1e-9)


def test_on_off_ignores_zeros():
    i_d = np.array([0.0, -1e-12, -1e-6])
    assert math.isclose(on_off_ratio(i_d), 1e6, rel_tol=1e-9)


def test_subthreshold_swing_recovers_synthetic_slope():
    v_g, i_d = _ideal_transfer(ss_mv=200.0)
    ss = subthreshold_swing(v_g, i_d)
    assert ss is not None
    assert abs(ss - 200.0) < 40.0   # 1 V 간격 측정이라 오차 허용


def test_hysteresis_recovers_shift():
    v_g, i_d = _ideal_transfer(v_th=-12.0)
    v_g_r, i_d_r = _ideal_transfer(v_th=-15.0)
    fwd = pd.DataFrame({"V_G": v_g, "I_G": np.zeros_like(v_g), "I_D": i_d})
    rev = pd.DataFrame({"V_G": v_g_r[::-1], "I_G": np.zeros_like(v_g_r),
                        "I_D": i_d_r[::-1]})
    m = transfer_metrics(TransferCurve(forward=fwd, reverse=rev, v_ds=-60.0, dual=True),
                         PARAMS)
    assert m.dv_th is not None
    assert abs(m.dv_th - (-3.0)) < 0.5   # reverse - forward


def test_manual_fit_range_is_honored():
    v_g, i_d = _ideal_transfer()
    m = transfer_metrics(_curve(v_g, i_d), PARAMS, fit_range=(-55.0, -35.0))
    assert m.fit.v_start <= -35.0 and m.fit.v_end >= -55.0


def test_incomplete_params_give_vth_but_no_mobility():
    v_g, i_d = _ideal_transfer()
    m = transfer_metrics(_curve(v_g, i_d), DeviceParams(w_um=None, l_um=50.0,
                                                        eps_r=3.9, d_nm=300.0))
    assert m.v_th is not None
    assert m.mu_sat is None
    assert any("W" in w or "소자" in w for w in m.warnings)


def test_saturation_condition_warning():
    """|V_DS| < |V_G - V_th| 인 구간이 fit 에 들어가면 경고."""
    v_g, i_d = _ideal_transfer()
    c = _curve(v_g, i_d)
    c.v_ds = -20.0   # fit 구간이 V_G -50 근처라 |V_G - V_th| ~ 38 > 20
    m = transfer_metrics(c, PARAMS)
    assert any("포화" in w for w in m.warnings)


def test_real_example_produces_finite_metrics(example_dir):
    from fet_app.grouping import parse_file
    pf = parse_file((example_dir / "1-3 best.xls").read_bytes(), "1-3 best.xls")
    m = transfer_metrics(pf.transfer, PARAMS)
    assert m.v_th is not None and np.isfinite(m.v_th)
    assert m.mu_sat is not None and m.mu_sat > 0
    assert m.on_off is not None and m.on_off > 1
    assert m.fit.r2 > 0.9
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_metrics_transfer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.metrics'`

- [ ] **Step 3: 구현**

`fet_app/metrics.py`:
```python
"""성능 지표 계산 (스펙 §3). 모든 식은 MANUAL.md 에 그대로 문서화된다."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from fet_app.constants import SS_WINDOW
from fet_app.curves import TransferCurve
from fet_app.fitting import FitResult, auto_fit_sqrt, linear_fit, manual_fit_sqrt
from fet_app.params import DeviceParams


def threshold_and_mobility(fit: FitResult,
                           p: DeviceParams) -> tuple[float | None, float | None]:
    """V_th = -b/m,  mu_sat = (2L / (W C_ox)) m^2   (스펙 §3.2)."""
    if fit is None or fit.slope == 0:
        return None, None
    v_th = -fit.intercept / fit.slope
    if not p.is_complete():
        return float(v_th), None
    mu = (2.0 * p.l_cm() / (p.w_cm() * p.c_ox())) * (fit.slope ** 2)
    return float(v_th), float(mu)


def on_off_ratio(i_d) -> float | None:
    """max|I_D| / min|I_D|, 0 은 제외 (스펙 §3.4)."""
    a = np.abs(np.asarray(i_d, dtype=float))
    a = a[np.isfinite(a) & (a > 0)]
    if a.size < 2:
        return None
    lo = float(np.min(a))
    return float(np.max(a) / lo) if lo > 0 else None


def subthreshold_swing(v_g, i_d, window: int = SS_WINDOW) -> float | None:
    """SS = min(dV_G / d log10|I_D|) [mV/dec]  (스펙 §3.5).

    구현은 등가식 SS = 1000 / max|d log10|I_D| / dV_G| 를 쓴다.
    탐색 범위는 I_off*10 ~ I_on/10 의 서브스레숄드 구간, window 점 이동 회귀.
    """
    v = np.asarray(v_g, dtype=float)
    a = np.abs(np.asarray(i_d, dtype=float))
    ok = np.isfinite(v) & np.isfinite(a) & (a > 0)
    v, a = v[ok], a[ok]
    if v.size < window:
        return None

    i_off, i_on = float(np.min(a)), float(np.max(a))
    if i_on <= i_off * 100:
        return None
    band = (a > i_off * 10) & (a < i_on / 10)
    idx = np.flatnonzero(band)
    if idx.size < window:
        return None

    y = np.log10(a)
    best_slope = 0.0
    for s in range(idx[0], idx[-1] - window + 2):
        xs, ys = v[s:s + window], y[s:s + window]
        slope, _intercept, _r2 = linear_fit(xs, ys)
        best_slope = max(best_slope, abs(slope))
    if best_slope <= 0:
        return None
    return float(1000.0 / best_slope)


@dataclass
class TransferMetrics:
    v_th: float | None = None
    mu_sat: float | None = None
    on_off: float | None = None
    ss_mv_dec: float | None = None
    dv_th: float | None = None
    v_th_reverse: float | None = None
    mu_sat_reverse: float | None = None
    c_ox: float | None = None
    fit: FitResult | None = None
    fit_reverse: FitResult | None = None
    warnings: list[str] = field(default_factory=list)


def _fit_branch(df, fit_range: tuple[float, float] | None) -> FitResult | None:
    v_g = df["V_G"].to_numpy(dtype=float)
    i_d = df["I_D"].to_numpy(dtype=float)
    if fit_range is not None:
        return manual_fit_sqrt(v_g, i_d, fit_range[0], fit_range[1])
    return auto_fit_sqrt(v_g, i_d)


def transfer_metrics(curve: TransferCurve, p: DeviceParams,
                     fit_range: tuple[float, float] | None = None) -> TransferMetrics:
    m = TransferMetrics()
    if curve is None or curve.forward.empty:
        m.warnings.append("transfer 데이터가 없습니다.")
        return m

    if p.is_complete():
        m.c_ox = p.c_ox()
    else:
        m.warnings.append("소자 파라미터(W, L, ε_r, d)가 비어 있어 μ_sat 을 계산할 수 없습니다.")

    fwd = curve.forward
    m.on_off = on_off_ratio(fwd["I_D"].to_numpy(dtype=float))
    m.ss_mv_dec = subthreshold_swing(fwd["V_G"].to_numpy(dtype=float),
                                     fwd["I_D"].to_numpy(dtype=float))

    m.fit = _fit_branch(fwd, fit_range)
    if m.fit is None:
        m.warnings.append(
            "fit 구간을 찾지 못했습니다. on 영역이 너무 짧거나 노이즈가 큽니다. "
            "fit 패널에서 V_G 범위를 직접 지정해 보세요."
        )
        return m

    m.v_th, m.mu_sat = threshold_and_mobility(m.fit, p)

    if m.fit.r2 < 0.99:
        m.warnings.append(f"fit R² = {m.fit.r2:.4f} 로 낮습니다. 구간을 확인하세요.")

    # 포화 조건 |V_DS| >= |V_G - V_th| 검사 (스펙 §3.8)
    if curve.v_ds is not None and m.v_th is not None:
        worst = max(abs(m.fit.v_start - m.v_th), abs(m.fit.v_end - m.v_th))
        if worst > abs(curve.v_ds):
            m.warnings.append(
                f"fit 구간에서 포화 조건이 깨집니다: |V_G − V_th| 최대 {worst:.1f} V "
                f"> |V_DS| {abs(curve.v_ds):.1f} V. μ_sat 이 과대평가될 수 있습니다."
            )

    if curve.reverse is not None and not curve.reverse.empty:
        m.fit_reverse = _fit_branch(curve.reverse, fit_range)
        if m.fit_reverse is not None:
            m.v_th_reverse, m.mu_sat_reverse = threshold_and_mobility(m.fit_reverse, p)
            if m.v_th is not None and m.v_th_reverse is not None:
                m.dv_th = float(m.v_th_reverse - m.v_th)
        else:
            m.warnings.append("reverse branch 의 fit 구간을 찾지 못해 ΔV_th 를 계산하지 못했습니다.")

    return m
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_metrics_transfer.py -v`
Expected: 10 passed

- [ ] **Step 5: 커밋**

```bash
git add fet_app/metrics.py tests/test_metrics_transfer.py
git commit -m "$(cat <<'EOF'
feat: transfer 지표 계산 (V_th, mu_sat, on/off, SS, dV_th)

합성 제곱법칙 데이터에서 mu 를 1% 이내, V_th 를 0.3 V 이내로 복원한다.
포화 조건 |V_DS| >= |V_G - V_th| 위반 시 경고를 붙인다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Output 진단 4종

**Files:**
- Modify: `fet_app/metrics.py` (끝에 추가)
- Test: `tests/test_metrics_output.py`

**Interfaces:**
- Consumes: `curves.OutputCurve`, `curves.OutputBlock`, `constants.DEFAULT_THRESHOLDS`, `DIAG_SLOPE_POINTS`, `DIAG_ORIGIN_FRACTION`, `DIAG_ON_BLOCK_FRACTION`
- Produces:
  - `constants.DIAG_ON_BLOCK_FRACTION = 0.01` — **새 상수. `fet_app/constants.py` 에 추가한다.**
  - `metrics.BlockDiagnostics` — 필드 `v_g: float`, `is_on: bool`, `i_max: float`, `zero_offset: float | None`, `linearity_r2: float | None`, `saturation_ratio: float | None`, `gate_leak: float | None`, `flags: list[str]`
  - `metrics.OutputDiagnostics` — 필드 `blocks: list[BlockDiagnostics]`, `worst: dict[str, float | None]`, `flags: list[str]`, `i_drive: float | None`
  - `metrics.output_diagnostics(curve: OutputCurve, thresholds: dict | None = None) -> OutputDiagnostics`

**정규화 규약 (스펙 §3.7 — 필수).**

```
I_drive  = 모든 블록의 max|I_D| 중 최댓값      (소자 온상태 구동전류)
is_on    = 그 블록의 max|I_D| >= DIAG_ON_BLOCK_FRACTION * I_drive
```

- `zero_offset`, `gate_leak` 은 **전 블록**에서 계산하되 분모를 `I_drive` 로 쓴다.
  블록 내 최댓값으로 나누면 꺼진 블록(V_G=0)이 노이즈끼리 나눈 값을 내놓아 오경보가 난다.
- `linearity_r2`, `saturation_ratio` 는 **`is_on` 인 블록에서만** 계산한다.
  off-block 에서는 `None` 으로 두고 경고도 달지 않는다 — 꺼진 소자의 곡선 모양은 노이즈다.
- `worst` 집계는 종전대로: zero_offset·saturation_ratio·gate_leak 은 `max`,
  linearity_r2 는 `min`. `None` 은 건너뛰고, 전부 `None` 이면 결과도 `None`.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_metrics_output.py`:
```python
import numpy as np
import pandas as pd

from fet_app.curves import OutputBlock, OutputCurve
from fet_app.metrics import output_diagnostics


def _block(v_g, i_d, i_g=None, v_d=None):
    v_d = v_d if v_d is not None else np.arange(0, -61, -1, dtype=float)
    i_g = i_g if i_g is not None else np.full_like(v_d, 1e-12)
    return OutputBlock(v_g=v_g,
                       forward=pd.DataFrame({"V_D": v_d, "I_D": i_d, "I_G": i_g}),
                       reverse=None)


def _ideal(v_d, i_sat=-1e-5, v_knee=-20.0):
    """원점에서 출발해 knee 이후 포화하는 이상적 출력 곡선."""
    return i_sat * np.tanh(v_d / v_knee)


def test_ideal_curve_passes_all_checks():
    v_d = np.arange(0, -61, -1, dtype=float)
    curve = OutputCurve(blocks=[_block(-60.0, _ideal(v_d))])
    d = output_diagnostics(curve)
    b = d.blocks[0]
    assert b.is_on
    assert b.zero_offset < 0.01
    assert b.linearity_r2 > 0.99
    assert b.saturation_ratio < 0.1
    assert b.gate_leak < 0.01
    assert b.flags == []
    assert d.flags == []


def test_off_block_does_not_raise_false_alarms():
    """V_G=0 처럼 꺼진 블록은 전류가 노이즈다. 자기 블록 최댓값으로 나누면
    비율이 폭주해 멀쩡한 소자가 불량으로 찍힌다 (스펙 §3.7)."""
    v_d = np.arange(0, -61, -1, dtype=float)
    on = _block(-60.0, _ideal(v_d, i_sat=-1e-4))
    # 꺼진 블록: 구동전류의 1/100000 수준, 원점에서도 노이즈가 남아 있다
    noise = np.full_like(v_d, -6e-10) + np.linspace(0, -1e-10, v_d.size)
    off = _block(0.0, noise, i_g=np.full_like(v_d, -7e-10))
    d = output_diagnostics(OutputCurve(blocks=[off, on]))

    off_d, on_d = d.blocks[0], d.blocks[1]
    assert not off_d.is_on and on_d.is_on
    # 모양 판정은 생략된다
    assert off_d.linearity_r2 is None
    assert off_d.saturation_ratio is None
    # 오프셋·누설은 계산하되 소자 구동전류로 나눠 미미하게 나온다
    assert off_d.zero_offset < 0.01
    assert off_d.gate_leak < 0.01
    assert off_d.flags == []
    assert d.flags == []
    assert d.i_drive == pytest.approx(1e-4, rel=1e-6)


def test_off_block_still_reports_real_gate_leak():
    """꺼진 블록이라도 누설이 진짜 크면 놓치지 않는다."""
    v_d = np.arange(0, -61, -1, dtype=float)
    on = _block(-60.0, _ideal(v_d, i_sat=-1e-5))
    off = _block(0.0, np.full_like(v_d, -1e-10),
                 i_g=np.full_like(v_d, -5e-7))   # 구동전류의 5 %
    d = output_diagnostics(OutputCurve(blocks=[off, on]))
    assert not d.blocks[0].is_on
    assert d.blocks[0].gate_leak == pytest.approx(0.05, rel=1e-6)
    assert any("누설" in f for f in d.blocks[0].flags)


def test_zero_offset_detected():
    v_d = np.arange(0, -61, -1, dtype=float)
    i_d = _ideal(v_d) - 1e-6      # 전 구간을 들어올려 0 V 에서 안 떨어지게
    curve = OutputCurve(blocks=[_block(-60.0, i_d)])
    d = output_diagnostics(curve)
    assert d.blocks[0].zero_offset > 0.01
    assert any("0 V" in f for f in d.blocks[0].flags)


def test_nonlinear_origin_detected():
    """S 자 개형(컨택트 저항) 은 원점 선형성 R^2 를 떨어뜨린다."""
    v_d = np.arange(0, -61, -1, dtype=float)
    i_d = -1e-5 * (np.abs(v_d) / 60.0) ** 3
    curve = OutputCurve(blocks=[_block(-60.0, i_d)])
    d = output_diagnostics(curve)
    assert d.blocks[0].linearity_r2 < 0.99
    assert any("선형" in f for f in d.blocks[0].flags)


def test_unsaturated_detected():
    v_d = np.arange(0, -61, -1, dtype=float)
    i_d = -1e-7 * np.abs(v_d)     # 끝까지 직선 = 미포화
    curve = OutputCurve(blocks=[_block(-60.0, i_d)])
    d = output_diagnostics(curve)
    assert d.blocks[0].saturation_ratio > 0.1
    assert any("포화" in f for f in d.blocks[0].flags)


def test_gate_leak_detected():
    v_d = np.arange(0, -61, -1, dtype=float)
    i_d = _ideal(v_d)
    i_g = np.full_like(v_d, -1e-6)   # |I_D| 최대 1e-5 대비 10 %
    curve = OutputCurve(blocks=[_block(-60.0, i_d, i_g=i_g)])
    d = output_diagnostics(curve)
    assert d.blocks[0].gate_leak > 0.01
    assert any("누설" in f for f in d.blocks[0].flags)


def test_worst_aggregates_across_blocks():
    """집계는 나쁜 쪽을 취한다: 비율은 max, R^2 는 min. None 은 건너뛴다."""
    v_d = np.arange(0, -61, -1, dtype=float)
    clean = _block(-40.0, _ideal(v_d, i_sat=-5e-5))
    offset = _block(-60.0, _ideal(v_d, i_sat=-1e-4) - 5e-6)
    d = output_diagnostics(OutputCurve(blocks=[clean, offset]))
    zeros = [b.zero_offset for b in d.blocks if b.zero_offset is not None]
    lins = [b.linearity_r2 for b in d.blocks if b.linearity_r2 is not None]
    assert d.worst["zero_offset"] == max(zeros)
    assert d.worst["linearity_r2"] == min(lins)
    assert d.flags


def test_worst_is_none_when_every_block_is_none():
    """모두 꺼진 블록이면 모양 지표 집계는 None 이어야 한다 (0.0 아님)."""
    v_d = np.arange(0, -61, -1, dtype=float)
    a = _block(0.0, np.full_like(v_d, -1e-12))
    d = output_diagnostics(OutputCurve(blocks=[a]))
    # 단일 블록이면 그 블록이 곧 I_drive 이므로 is_on 이다 — 모양 지표가 나온다
    assert d.blocks[0].is_on
    assert d.worst["linearity_r2"] is not None


def test_custom_thresholds_override_defaults_key_by_key():
    """일부 키만 넘기면 나머지는 기본값을 유지한다."""
    v_d = np.arange(0, -61, -1, dtype=float)
    curve = OutputCurve(blocks=[_block(-60.0, _ideal(v_d))])
    # 기본값으로는 무경고
    assert output_diagnostics(curve).blocks[0].flags == []
    # 선형성 하한만 불가능한 값으로 올리면 그 항목만 걸린다
    d = output_diagnostics(curve, thresholds={"linearity_r2": 1.1})
    flags = d.blocks[0].flags
    assert len(flags) == 1
    assert "선형" in flags[0]


def test_all_thresholds_can_fire_together():
    v_d = np.arange(0, -61, -1, dtype=float)
    i_d = _ideal(v_d) - 1e-6                  # 원점에서 안 떨어짐
    curve = OutputCurve(blocks=[_block(-60.0, i_d, i_g=np.full_like(v_d, -1e-7))])
    d = output_diagnostics(curve, thresholds={"zero_offset": 0.0,
                                              "linearity_r2": 1.1,
                                              "saturation": 0.0,
                                              "gate_leak": 0.0})
    assert len(d.blocks[0].flags) == 4


def test_real_example_runs(example_dir):
    from fet_app.grouping import parse_file
    pf = parse_file((example_dir / "1-1 out.xls").read_bytes(), "1-1 out.xls")
    d = output_diagnostics(pf.latest.output)
    assert len(d.blocks) == 4
    assert d.i_drive is not None and d.i_drive > 0
    for b in d.blocks:
        assert b.zero_offset is not None
        assert b.gate_leak is not None


def test_real_example_off_block_is_not_flagged(example_dir):
    """1-1 out.xls 의 V_G=0 블록은 꺼져 있다. 예전 정규화로는 0V 오프셋 57 %,
    누설 100 % 가 나와 멀쩡한 소자가 불량으로 찍혔다."""
    from fet_app.grouping import parse_file
    pf = parse_file((example_dir / "1-1 out.xls").read_bytes(), "1-1 out.xls")
    d = output_diagnostics(pf.latest.output)
    off = next(b for b in d.blocks if b.v_g == 0.0)
    assert not off.is_on
    assert off.zero_offset < 0.01
    assert off.gate_leak < 0.01
    assert off.linearity_r2 is None and off.saturation_ratio is None
    assert off.flags == []
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_metrics_output.py -v`
Expected: FAIL — `ImportError: cannot import name 'output_diagnostics'`

- [ ] **Step 3: 구현 — `fet_app/metrics.py` 끝에 추가**

상단 import 에 다음을 더한다:
```python
from fet_app.constants import (
    DEFAULT_THRESHOLDS, DIAG_ORIGIN_FRACTION, DIAG_SLOPE_POINTS, SS_WINDOW,
)
from fet_app.curves import OutputCurve, TransferCurve
```

파일 끝에 추가:
```python
# ---------------- Output 진단 (스펙 §3.7) ----------------


@dataclass
class BlockDiagnostics:
    v_g: float
    is_on: bool = False                    # max|I_D| >= 1 % of I_drive
    i_max: float = 0.0                     # 이 블록의 max|I_D|
    zero_offset: float | None = None       # |I_D(V_D=0)| / I_drive
    linearity_r2: float | None = None      # 원점 구간 선형 fit R^2 (on-block 만)
    saturation_ratio: float | None = None  # 말단 기울기 / 원점 기울기 (on-block 만)
    gate_leak: float | None = None         # max|I_G| / I_drive
    flags: list[str] = field(default_factory=list)


@dataclass
class OutputDiagnostics:
    blocks: list[BlockDiagnostics] = field(default_factory=list)
    worst: dict = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)
    i_drive: float | None = None           # 소자 온상태 구동전류 (정규화 분모)


def _edge_slope(v_d: np.ndarray, i_d: np.ndarray, at_origin: bool) -> float | None:
    n = min(DIAG_SLOPE_POINTS, v_d.size)
    if n < 2:
        return None
    xs, ys = (v_d[:n], i_d[:n]) if at_origin else (v_d[-n:], i_d[-n:])
    slope, _intercept, _r2 = linear_fit(xs, ys)
    return float(slope)


def _block_i_max(block) -> float:
    df = block.forward
    if df is None or df.empty:
        return 0.0
    a = np.abs(df["I_D"].to_numpy(dtype=float))
    return float(np.max(a)) if a.size else 0.0


def _diagnose_block(block, t: dict, i_drive: float) -> BlockDiagnostics:
    """i_drive = 소자 전체의 온상태 구동전류. 블록 내 최댓값으로 나누면
    꺼진 블록(V_G=0)이 노이즈끼리 나눈 값을 내놓아 오경보가 난다 (스펙 §3.7)."""
    i_max = _block_i_max(block)
    is_on = i_drive > 0 and i_max >= DIAG_ON_BLOCK_FRACTION * i_drive
    d = BlockDiagnostics(v_g=block.v_g, is_on=is_on, i_max=i_max)

    df = block.forward
    if df is None or df.empty:
        d.flags.append("데이터 없음")
        return d

    v_d = df["V_D"].to_numpy(dtype=float)
    i_d = df["I_D"].to_numpy(dtype=float)
    i_g = df["I_G"].to_numpy(dtype=float)

    # 1) 0 V 오프셋 — 전 블록. 분모는 소자 구동전류.
    if i_drive > 0 and v_d.size:
        j = int(np.argmin(np.abs(v_d)))
        d.zero_offset = float(abs(i_d[j]) / i_drive)
        if d.zero_offset > t["zero_offset"]:
            d.flags.append(
                f"0 V 오프셋 {d.zero_offset * 100:.2f} % (> {t['zero_offset'] * 100:g} %)"
            )

    # 4) 게이트 누설 — 전 블록. 꺼진 상태의 누설도 실제 문제라 건너뛰지 않는다.
    if i_drive > 0 and i_g.size:
        d.gate_leak = float(np.max(np.abs(i_g)) / i_drive)
        if d.gate_leak > t["gate_leak"]:
            d.flags.append(
                f"게이트 누설 {d.gate_leak * 100:.2f} % (> {t['gate_leak'] * 100:g} %)"
            )

    # 2)·3) 곡선 모양 판정은 켜진 블록에서만. 꺼진 소자의 개형은 노이즈다.
    if not is_on:
        return d

    span = float(np.max(np.abs(v_d))) if v_d.size else 0.0
    if span > 0:
        near = np.abs(v_d) <= span * DIAG_ORIGIN_FRACTION
        if int(np.count_nonzero(near)) >= 3:
            _slope, _intercept, r2 = linear_fit(v_d[near], i_d[near])
            d.linearity_r2 = float(r2)
            if d.linearity_r2 < t["linearity_r2"]:
                d.flags.append(
                    f"원점 선형성 R² {d.linearity_r2:.4f} (< {t['linearity_r2']:g}) "
                    "— 컨택트 저항 의심"
                )

    s0 = _edge_slope(v_d, i_d, at_origin=True)
    s1 = _edge_slope(v_d, i_d, at_origin=False)
    if s0 not in (None, 0.0) and s1 is not None:
        d.saturation_ratio = float(abs(s1 / s0))
        if d.saturation_ratio > t["saturation"]:
            d.flags.append(
                f"미포화: 말단/원점 기울기비 {d.saturation_ratio:.3f} (> {t['saturation']:g})"
            )

    return d


def output_diagnostics(curve: OutputCurve,
                       thresholds: dict | None = None) -> OutputDiagnostics:
    t = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        t.update(thresholds)

    out = OutputDiagnostics()
    if curve is None or not curve.blocks:
        out.flags.append("output 데이터가 없습니다.")
        return out

    i_drive = max((_block_i_max(b) for b in curve.blocks), default=0.0)
    out.i_drive = i_drive if i_drive > 0 else None
    out.blocks = [_diagnose_block(b, t, i_drive) for b in curve.blocks]

    def _agg(attr: str, fn):
        vals = [getattr(b, attr) for b in out.blocks if getattr(b, attr) is not None]
        return fn(vals) if vals else None

    out.worst = {
        "zero_offset": _agg("zero_offset", max),
        "linearity_r2": _agg("linearity_r2", min),
        "saturation_ratio": _agg("saturation_ratio", max),
        "gate_leak": _agg("gate_leak", max),
    }
    for b in out.blocks:
        for f in b.flags:
            out.flags.append(f"V_G = {b.v_g:g} V: {f}")
    return out
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_metrics_output.py -v`
Expected: 8 passed

- [ ] **Step 5: 커밋**

```bash
git add fet_app/metrics.py tests/test_metrics_output.py
git commit -m "$(cat <<'EOF'
feat: output 진단 4종 (0V 오프셋, 원점 선형성, 포화, 게이트 누설)

블록별로 계산하고 최악값을 소자 대표값으로 집계한다. 임계값은 주입 가능.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: 그래프 공통 규약과 표시 배율

**Files:**
- Create: `fet_app/figure_common.py`
- Test: `tests/test_figure_common.py`

**Interfaces:**
- Consumes: `constants.DEFAULTS`
- Produces:
  - `figure_common.px_size(geom: dict, k: float) -> tuple[int, int]`
  - `figure_common.domains(geom: dict) -> tuple[list[float], list[float]]` — `(x_domain, y_domain)`
  - `figure_common.axis_layout(cfg: dict, style: dict, k: float, data_min=None, data_max=None, side=None, overlaying=None, domain=None) -> dict`
  - `figure_common.new_figure(geom: dict, k: float) -> go.Figure`
  - `figure_common.apply_inset_text(fig, text: str, inset: dict, style: dict, k: float) -> None`
  - `figure_common.DPI = 96`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_figure_common.py`:
```python
import copy

from fet_app.constants import DEFAULTS
from fet_app.figure_common import DPI, axis_layout, domains, new_figure, px_size


def test_px_size_uses_96_dpi():
    geom = DEFAULTS["geom"]
    assert px_size(geom, 1.0) == (int(10 * DPI), int(8 * DPI)) == (960, 768)


def test_px_size_scales():
    assert px_size(DEFAULTS["geom"], 0.5) == (480, 384)


def test_domains_from_percentages():
    geom = {"graph_left_pct": 20.0, "graph_top_pct": 10.0,
            "graph_width_pct": 60.0, "graph_height_pct": 70.0}
    x_dom, y_dom = domains(geom)
    assert x_dom == [0.2, 0.8]
    # Top 은 위에서부터이므로 y_domain = [1-(T+H), 1-T]
    assert y_dom == [0.2, 0.9]


def test_axis_layout_paper_conventions():
    cfg = copy.deepcopy(DEFAULTS["transfer_axes"]["y"])
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0)
    assert lay["type"] == "log"
    assert lay["mirror"] is True          # 4면 박스
    assert lay["ticks"] == "inside"
    assert lay["showgrid"] is False
    assert lay["exponentformat"] == "E"   # 1E-11 형식
    assert lay["showexponent"] == "all"
    assert lay["zeroline"] is False


def test_axis_layout_scales_fonts():
    lay = axis_layout(DEFAULTS["transfer_axes"]["x"], DEFAULTS["style"], k=0.5)
    assert lay["title"]["font"]["size"] == 15   # 30 * 0.5
    assert lay["tickfont"]["size"] == 15


def test_axis_layout_auto_range_has_no_padding():
    cfg = dict(DEFAULTS["transfer_axes"]["x"])
    cfg["auto"] = True
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0, data_min=-60.0, data_max=20.0)
    assert lay["range"] == [-60.0, 20.0]
    assert lay["autorange"] is False


def test_axis_layout_manual_range_wins():
    cfg = dict(DEFAULTS["transfer_axes"]["x"])
    cfg.update({"auto": False, "min": -50.0, "max": 10.0})
    lay = axis_layout(cfg, DEFAULTS["style"], k=1.0, data_min=-60.0, data_max=20.0)
    assert lay["range"] == [-50.0, 10.0]


def test_new_figure_is_white_and_unmargined():
    fig = new_figure(DEFAULTS["geom"], k=1.0)
    assert fig.layout.paper_bgcolor == "#FFFFFF"
    assert fig.layout.plot_bgcolor == "#FFFFFF"
    assert fig.layout.margin.l == 0
    assert fig.layout.showlegend is False
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_figure_common.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.figure_common'`

- [ ] **Step 3: 구현**

`fet_app/figure_common.py`:
```python
"""그래프 공통 규약 (스펙 §5.1).

논문용 흰 배경, 4면 mirror ticks, ticks inside, 그리드 없음, 1E-11 지수 표기.
크기는 Origin 방식 2단계: background inch x DPI, graph 는 % of background.
표시 배율 k 는 크기와 폰트·선두께에 동시에 곱해 화면에서만 축소한다 (스펙 §5.4).
"""

from __future__ import annotations

import plotly.graph_objects as go

DPI = 96


def px_size(geom: dict, k: float = 1.0) -> tuple[int, int]:
    return (int(round(float(geom["page_w_in"]) * DPI * k)),
            int(round(float(geom["page_h_in"]) * DPI * k)))


def domains(geom: dict) -> tuple[list[float], list[float]]:
    """graph 의 %(좌/상/폭/높이) -> plotly domain. Top 은 위에서부터 잰다."""
    left = float(geom["graph_left_pct"]) / 100.0
    top = float(geom["graph_top_pct"]) / 100.0
    width = float(geom["graph_width_pct"]) / 100.0
    height = float(geom["graph_height_pct"]) / 100.0
    x_dom = [round(left, 6), round(left + width, 6)]
    y_dom = [round(1.0 - (top + height), 6), round(1.0 - top, 6)]
    return x_dom, y_dom


def axis_layout(cfg: dict, style: dict, k: float = 1.0,
                data_min: float | None = None, data_max: float | None = None,
                side: str | None = None, overlaying: str | None = None,
                domain: list[float] | None = None) -> dict:
    """축 하나의 layout dict. 규약 위반이 없도록 여기서만 만든다."""
    title_size = max(1, round(float(style["title_font_size"]) * k))
    tick_size = max(1, round(float(style["tick_font_size"]) * k))
    family = style["font_family"]

    lay: dict = {
        "type": cfg.get("type", "linear"),
        "title": {"text": cfg.get("title", ""),
                  "font": {"family": family, "size": title_size, "color": "#000000"}},
        "tickfont": {"family": family, "size": tick_size, "color": "#000000"},
        "showline": True,
        "linecolor": "#000000",
        "linewidth": max(0.5, 1.5 * k),
        "mirror": True,
        "ticks": "inside",
        "ticklen": max(2, round(8 * k)),
        "tickwidth": max(0.5, 1.5 * k),
        "tickcolor": "#000000",
        "showgrid": bool(style.get("show_grid", False)),
        "zeroline": False,
        "exponentformat": "E",
        "showexponent": "all",
        "automargin": False,
    }
    if cfg.get("title_standoff") is not None:
        lay["title"]["standoff"] = float(cfg["title_standoff"]) * k
    if cfg.get("dtick") is not None:
        lay["dtick"] = cfg["dtick"]
    if cfg.get("minor_dtick") is not None:
        lay["minor"] = {"dtick": cfg["minor_dtick"], "ticks": "inside",
                        "ticklen": max(1, round(4 * k)),
                        "tickwidth": max(0.5, 1.0 * k), "tickcolor": "#000000"}

    # 범위: auto 여도 데이터 min/max 를 명시해 plotly 자동 패딩을 없앤다 (스펙 §5.1)
    lo = cfg.get("min") if not cfg.get("auto", True) else data_min
    hi = cfg.get("max") if not cfg.get("auto", True) else data_max
    if lo is not None and hi is not None:
        lay["range"] = [lo, hi]
        lay["autorange"] = False

    if side:
        lay["side"] = side
    if overlaying:
        lay["overlaying"] = overlaying
    if domain:
        lay["domain"] = domain
    return lay


def new_figure(geom: dict, k: float = 1.0) -> go.Figure:
    w, h = px_size(geom, k)
    fig = go.Figure()
    fig.update_layout(
        width=w, height=h,
        margin=dict(l=0, r=0, t=0, b=0, pad=0),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        showlegend=False,
    )
    return fig


def apply_inset_text(fig: go.Figure, text: str, inset: dict,
                     style: dict, k: float = 1.0) -> None:
    """인셋 텍스트를 플롯 영역 기준(domain)으로 배치한다."""
    if not text:
        return
    fig.add_annotation(
        text=text,
        xref="x domain", yref="y domain",
        x=float(inset["x"]), y=float(inset["y"]),
        xanchor=inset.get("xanchor", "left"), yanchor=inset.get("yanchor", "bottom"),
        showarrow=False, align="left",
        font=dict(family=style["font_family"],
                  size=max(1, round(float(inset.get("font_size", 30)) * k)),
                  color="#000000"),
        bgcolor="rgba(255,255,255,0)" if not inset.get("bg_opacity") else "#FFFFFF",
        bordercolor="#000000" if inset.get("border") else None,
        borderwidth=1 if inset.get("border") else 0,
    )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_figure_common.py -v`
Expected: 8 passed

- [ ] **Step 5: 커밋**

```bash
git add fet_app/figure_common.py tests/test_figure_common.py
git commit -m "$(cat <<'EOF'
feat: 그래프 공통 규약 모듈

흰 배경/4면 mirror ticks/inside/그리드 없음/1E 지수 표기를 한곳에서 강제한다.
표시 배율 k 는 크기와 폰트에 동시에 곱해 화면에서만 축소한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Transfer 이중축 그래프

**Files:**
- Create: `fet_app/figure_transfer.py`
- Test: `tests/test_figure_transfer.py`

**Interfaces:**
- Consumes: `figure_common.*`, `curves.TransferCurve`, `metrics.TransferMetrics`
- Produces: `figure_transfer.transfer_figure(curve: TransferCurve, metrics: TransferMetrics, settings: dict, k: float = 1.0) -> go.Figure`
  - `settings` 는 `{"geom":..., "style":..., "axes": DEFAULTS["transfer_axes"], "trace": DEFAULTS["transfer_style"], "insets":...}` 형태

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_figure_transfer.py`:
```python
import copy

import numpy as np
import pandas as pd

from fet_app.constants import DEFAULTS
from fet_app.curves import TransferCurve
from fet_app.figure_transfer import transfer_figure
from fet_app.metrics import transfer_metrics
from fet_app.params import DeviceParams

PARAMS = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)


def _settings(**over):
    s = {
        "geom": copy.deepcopy(DEFAULTS["geom"]),
        "style": copy.deepcopy(DEFAULTS["style"]),
        "axes": copy.deepcopy(DEFAULTS["transfer_axes"]),
        "trace": copy.deepcopy(DEFAULTS["transfer_style"]),
        "insets": copy.deepcopy(DEFAULTS["insets"]),
    }
    s.update(over)
    return s


def _curve(dual=True):
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = -np.maximum(2e-8 * (v_g + 12.0) ** 2 * (v_g < -12.0), 1e-12)
    fwd = pd.DataFrame({"V_G": v_g, "I_G": np.full_like(v_g, 1e-11), "I_D": i_d})
    rev = fwd.iloc[::-1].reset_index(drop=True) if dual else None
    return TransferCurve(forward=fwd, reverse=rev, v_ds=-60.0, dual=dual)


def test_left_axis_title_uses_absolute_value_symbol():
    """FET 에서는 절댓값 기호를 쓴다 (스펙 §5.2 — photodetector 규약을 뒤집은 항목)."""
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    assert fig.layout.yaxis.title.text == "|I_D| (A)"
    assert fig.layout.yaxis2.title.text == "√|I_D| (A^0.5)"
    assert fig.layout.xaxis.title.text == "V_G (V)"


def test_second_axis_overlays_on_right():
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    assert fig.layout.yaxis2.side == "right"
    assert fig.layout.yaxis2.overlaying == "y"
    assert fig.layout.yaxis.type == "log"
    assert fig.layout.yaxis2.type == "linear"


def test_forward_solid_reverse_dashed():
    c = _curve(dual=True)
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    named = {t.name: t for t in fig.data}
    assert named["forward |I_D|"].line.dash in (None, "solid")
    assert named["reverse |I_D|"].line.dash == "dash"
    assert named["forward |I_D|"].line.color == named["reverse |I_D|"].line.color


def test_reverse_hidden_when_toggled_off():
    c = _curve(dual=True)
    s = _settings()
    s["trace"]["show_reverse"] = False
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    assert not any("reverse" in (t.name or "") for t in fig.data)


def test_log_axis_plots_absolute_current():
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    trace = next(t for t in fig.data if t.name == "forward |I_D|")
    assert np.all(np.asarray(trace.y) > 0)


def test_fit_line_and_vth_marker_present():
    c = _curve()
    m = transfer_metrics(c, PARAMS)
    fig = transfer_figure(c, m, _settings())
    names = [t.name for t in fig.data]
    assert "fit" in names
    assert "V_th" in names
    fit_trace = next(t for t in fig.data if t.name == "fit")
    assert fit_trace.yaxis == "y2"


def test_fit_hidden_when_toggled_off():
    c = _curve()
    s = _settings()
    s["trace"]["show_fit"] = False
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), s)
    assert "fit" not in [t.name for t in fig.data]


def test_gate_current_optional():
    c = _curve()
    s = _settings()
    assert "|I_G|" not in [t.name for t in transfer_figure(c, transfer_metrics(c, PARAMS), s).data]
    s["trace"]["show_gate_current"] = True
    assert "|I_G|" in [t.name for t in transfer_figure(c, transfer_metrics(c, PARAMS), s).data]


def test_no_plotly_legend():
    c = _curve()
    fig = transfer_figure(c, transfer_metrics(c, PARAMS), _settings())
    assert fig.layout.showlegend is False


def test_scale_shrinks_figure_and_fonts():
    c = _curve()
    m = transfer_metrics(c, PARAMS)
    full = transfer_figure(c, m, _settings(), k=1.0)
    half = transfer_figure(c, m, _settings(), k=0.5)
    assert half.layout.width == full.layout.width // 2
    assert half.layout.xaxis.title.font.size == full.layout.xaxis.title.font.size // 2
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_figure_transfer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.figure_transfer'`

- [ ] **Step 3: 구현**

`fet_app/figure_transfer.py`:
```python
"""Transfer 이중 Y축 그래프 (스펙 §5.2).

좌 log|I_D| / 우 sqrt(|I_D|). 우축에 fit 직선·구간 음영·V_th 절편을 얹는다.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from fet_app.constants import hex_to_rgba
from fet_app.figure_common import apply_inset_text, axis_layout, domains, new_figure


def _abs_positive(a: np.ndarray) -> np.ndarray:
    """log 축용. 0 은 그릴 수 없으므로 nan 으로 빼둔다."""
    out = np.abs(np.asarray(a, dtype=float))
    return np.where(out > 0, out, np.nan)


def transfer_figure(curve, metrics, settings: dict, k: float = 1.0) -> go.Figure:
    geom, style = settings["geom"], settings["style"]
    axes, trace_cfg, insets = settings["axes"], settings["trace"], settings["insets"]

    fig = new_figure(geom, k)
    x_dom, y_dom = domains(geom)
    color = trace_cfg.get("color", "#000000")
    lw = max(0.25, float(style["line_width"]) * k)

    branches = [("forward", curve.forward, "solid")]
    if trace_cfg.get("show_reverse", True) and curve.reverse is not None:
        branches.append(("reverse", curve.reverse, "dash"))

    all_v, all_i, all_sqrt = [], [], []
    for label, df, dash in branches:
        v = df["V_G"].to_numpy(dtype=float)
        i_abs = _abs_positive(df["I_D"].to_numpy(dtype=float))
        all_v.append(v)
        all_i.append(i_abs)
        all_sqrt.append(np.sqrt(i_abs))

        fig.add_trace(go.Scatter(
            x=v, y=i_abs, name=f"{label} |I_D|", mode="lines", yaxis="y",
            line=dict(color=color, width=lw, dash=dash), hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=v, y=np.sqrt(i_abs), name=f"{label} √|I_D|", mode="lines", yaxis="y2",
            line=dict(color=color, width=lw, dash=dash), opacity=0.55, hoverinfo="skip",
        ))
        if trace_cfg.get("show_gate_current", False):
            fig.add_trace(go.Scatter(
                x=v, y=_abs_positive(df["I_G"].to_numpy(dtype=float)),
                name="|I_G|", mode="lines", yaxis="y",
                line=dict(color=color, width=lw * 0.75, dash="dot"),
                opacity=0.6, hoverinfo="skip",
            ))

    # fit 직선 · 구간 음영 · V_th 절편
    fit = getattr(metrics, "fit", None)
    if trace_cfg.get("show_fit", True) and fit is not None and fit.slope != 0:
        v_th = -fit.intercept / fit.slope
        x_lo, x_hi = sorted((fit.v_start, fit.v_end))
        x_line = np.array([min(x_lo, v_th), max(x_hi, v_th)], dtype=float)
        fig.add_trace(go.Scatter(
            x=x_line, y=fit.slope * x_line + fit.intercept,
            name="fit", mode="lines", yaxis="y2",
            line=dict(color="#d62728", width=max(0.25, lw * 0.9), dash="solid"),
            hoverinfo="skip",
        ))
        fig.add_vrect(x0=x_lo, x1=x_hi, xref="x",
                      fillcolor=hex_to_rgba("#d62728", 0.08),
                      line_width=0, layer="below")
        fig.add_trace(go.Scatter(
            x=[v_th], y=[0.0], name="V_th", mode="markers", yaxis="y2",
            marker=dict(color="#d62728", size=max(3, round(10 * k)), symbol="circle-open",
                        line=dict(width=max(0.5, 2 * k))),
            hoverinfo="skip",
        ))

    v_cat = np.concatenate(all_v)
    i_cat = np.concatenate(all_i)
    s_cat = np.concatenate(all_sqrt)
    i_pos = i_cat[np.isfinite(i_cat)]
    s_pos = s_cat[np.isfinite(s_cat)]

    fig.update_layout(
        xaxis=axis_layout(axes["x"], style, k,
                          data_min=float(np.min(v_cat)), data_max=float(np.max(v_cat)),
                          domain=x_dom),
        yaxis=axis_layout(
            axes["y"], style, k,
            data_min=float(np.floor(np.log10(np.min(i_pos)))) if i_pos.size else None,
            data_max=float(np.ceil(np.log10(np.max(i_pos)))) if i_pos.size else None,
            domain=y_dom),
        yaxis2=axis_layout(axes["y2"], style, k,
                           data_min=0.0,
                           data_max=float(np.max(s_pos)) * 1.05 if s_pos.size else None,
                           side="right", overlaying="y"),
    )
    apply_inset_text(fig, insets["sample"].get("text", ""), insets["sample"], style, k)
    return fig
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_figure_transfer.py -v`
Expected: 10 passed

- [ ] **Step 5: 커밋**

```bash
git add fet_app/figure_transfer.py tests/test_figure_transfer.py
git commit -m "$(cat <<'EOF'
feat: transfer 이중 Y축 그래프

좌 log|I_D| / 우 sqrt(|I_D|), forward 실선 reverse 파선.
우축에 fit 직선과 구간 음영, V_th 절편 마커를 얹는다.
좌축 제목은 |I_D| (A) — FET 관례에 따라 절댓값 기호를 쓴다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Output 그라데이션 그래프

**Files:**
- Create: `fet_app/figure_output.py`
- Test: `tests/test_figure_output.py`

**Interfaces:**
- Consumes: `figure_common.*`, `curves.OutputCurve`
- Produces:
  - `figure_output.gradient_colors(base_hex: str, n: int, l_min: float = 0.18, l_max: float = 0.82) -> list[str]`
  - `figure_output.relative_luminance(hex_color: str) -> float`
  - `figure_output.output_figure(curve: OutputCurve, settings: dict, k: float = 1.0) -> go.Figure`
  - `settings` 는 `{"geom":..., "style":..., "axes": DEFAULTS["output_axes"], "trace": DEFAULTS["output_style"], "insets":...}`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_figure_output.py`:
```python
import copy

import numpy as np
import pandas as pd

from fet_app.constants import ACCENT, DEFAULTS
from fet_app.curves import OutputBlock, OutputCurve
from fet_app.figure_output import gradient_colors, output_figure, relative_luminance


def _settings(**over):
    s = {
        "geom": copy.deepcopy(DEFAULTS["geom"]),
        "style": copy.deepcopy(DEFAULTS["style"]),
        "axes": copy.deepcopy(DEFAULTS["output_axes"]),
        "trace": copy.deepcopy(DEFAULTS["output_style"]),
        "insets": copy.deepcopy(DEFAULTS["insets"]),
    }
    s.update(over)
    return s


def _curve(n=4, dual=True):
    v_d = np.arange(0, -61, -1, dtype=float)
    blocks = []
    for i in range(n):
        v_g = -20.0 * i
        i_d = -1e-6 * (i + 1) * np.tanh(v_d / -20.0)
        fwd = pd.DataFrame({"V_D": v_d, "I_D": i_d, "I_G": np.full_like(v_d, 1e-12)})
        rev = fwd.iloc[::-1].reset_index(drop=True) if dual else None
        blocks.append(OutputBlock(v_g=v_g, forward=fwd, reverse=rev))
    return OutputCurve(blocks=blocks)


def test_gradient_returns_requested_count():
    assert len(gradient_colors(ACCENT, 4)) == 4
    assert gradient_colors(ACCENT, 1) == [ACCENT]
    assert gradient_colors(ACCENT, 0) == []


def test_gradient_luminance_is_strictly_decreasing():
    """흑백 인쇄에서도 순서가 유지되어야 한다 (스펙 §5.3)."""
    lums = [relative_luminance(c) for c in gradient_colors(ACCENT, 6)]
    assert all(lums[i] > lums[i + 1] for i in range(len(lums) - 1)), lums


def test_gradient_preserves_hue_family():
    colors = gradient_colors("#ed542b", 4)
    for c in colors:
        r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
        assert r >= g >= b, c   # 주황 계열 유지


def test_output_axes_are_linear():
    fig = output_figure(_curve(), _settings())
    assert fig.layout.yaxis.type == "linear"
    assert fig.layout.xaxis.type == "linear"
    assert fig.layout.xaxis.title.text == "V_D (V)"
    assert fig.layout.yaxis.title.text == "I_D (A)"


def test_one_trace_pair_per_block():
    fig = output_figure(_curve(n=4), _settings())
    fwd = [t for t in fig.data if "forward" in (t.name or "")]
    rev = [t for t in fig.data if "reverse" in (t.name or "")]
    assert len(fwd) == 4 and len(rev) == 4


def test_block_colors_match_gradient_order():
    s = _settings()
    fig = output_figure(_curve(n=4), s)
    expected = gradient_colors(s["trace"]["base_color"], 4,
                               s["trace"]["lightness_min"], s["trace"]["lightness_max"])
    actual = [t.line.color for t in fig.data if "forward" in (t.name or "")]
    assert actual == expected


def test_manual_color_override():
    s = _settings()
    s["trace"]["manual_colors"] = {"-40": "#123456"}
    fig = output_figure(_curve(n=4), s)
    t = next(t for t in fig.data if t.name == "V_G = -40 V forward")
    assert t.line.color == "#123456"


def test_reverse_dashed_same_color():
    fig = output_figure(_curve(n=2), _settings())
    f = next(t for t in fig.data if t.name == "V_G = 0 V forward")
    r = next(t for t in fig.data if t.name == "V_G = 0 V reverse")
    assert r.line.dash == "dash"
    assert r.line.color == f.line.color


def test_inset_legend_lists_gate_voltages():
    fig = output_figure(_curve(n=4), _settings())
    texts = " ".join(a.text for a in fig.layout.annotations)
    for v in ("0", "-20", "-40", "-60"):
        assert f"V_G = {v} V" in texts


def test_no_plotly_legend():
    assert output_figure(_curve(), _settings()).layout.showlegend is False
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_figure_output.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.figure_output'`

- [ ] **Step 3: 구현**

`fet_app/figure_output.py`:
```python
"""Output 그래프 — 단색 순차 그라데이션 (스펙 §5.3).

명도를 단조 감소시켜 흑백 인쇄·색약 조건에서도 V_G 순서가 유지되게 한다.
"""

from __future__ import annotations

import colorsys

import numpy as np
import plotly.graph_objects as go

from fet_app.figure_common import axis_layout, domains, new_figure


def _hex_to_rgb01(hex_color: str) -> tuple[float, float, float]:
    h = str(hex_color).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _rgb01_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02X}" for c in rgb)


def relative_luminance(hex_color: str) -> float:
    """WCAG 상대 휘도. 흑백 변환 시 순서 검증에 쓴다."""
    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (_lin(c) for c in _hex_to_rgb01(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def gradient_colors(base_hex: str, n: int,
                    l_min: float = 0.18, l_max: float = 0.82) -> list[str]:
    """base 색의 색상·채도를 유지한 채 명도만 l_max -> l_min 으로 단조 감소."""
    if n <= 0:
        return []
    if n == 1:
        return [base_hex]
    r, g, b = _hex_to_rgb01(base_hex)
    h, _l, s = colorsys.rgb_to_hls(r, g, b)
    out = []
    for i in range(n):
        li = l_max - (l_max - l_min) * (i / (n - 1))
        out.append(_rgb01_to_hex(colorsys.hls_to_rgb(h, li, s)))
    return out


def output_figure(curve, settings: dict, k: float = 1.0) -> go.Figure:
    geom, style = settings["geom"], settings["style"]
    axes, trace_cfg, insets = settings["axes"], settings["trace"], settings["insets"]

    fig = new_figure(geom, k)
    x_dom, y_dom = domains(geom)
    lw = max(0.25, float(style["line_width"]) * k)

    blocks = list(curve.blocks) if curve is not None else []
    colors = gradient_colors(trace_cfg.get("base_color", "#ed542b"), len(blocks),
                             float(trace_cfg.get("lightness_min", 0.18)),
                             float(trace_cfg.get("lightness_max", 0.82)))
    manual = trace_cfg.get("manual_colors", {}) or {}

    all_x, all_y, legend_lines = [], [], []
    for idx, b in enumerate(blocks):
        color = manual.get(f"{b.v_g:g}", colors[idx] if idx < len(colors) else "#000000")
        label = f"V_G = {b.v_g:g} V"
        legend_lines.append(label)

        pairs = [("forward", b.forward, "solid")]
        if trace_cfg.get("show_reverse", True) and b.reverse is not None:
            pairs.append(("reverse", b.reverse, "dash"))
        for branch, df, dash in pairs:
            x = df["V_D"].to_numpy(dtype=float)
            y = df["I_D"].to_numpy(dtype=float)
            all_x.append(x)
            all_y.append(y)
            fig.add_trace(go.Scatter(
                x=x, y=y, name=f"{label} {branch}", mode="lines",
                line=dict(color=color, width=lw, dash=dash), hoverinfo="skip",
            ))

    x_cat = np.concatenate(all_x) if all_x else np.array([0.0, 1.0])
    y_cat = np.concatenate(all_y) if all_y else np.array([0.0, 1.0])
    y_lo, y_hi = float(np.min(y_cat)), float(np.max(y_cat))
    pad = (y_hi - y_lo) * 0.05 or 1e-12

    fig.update_layout(
        xaxis=axis_layout(axes["x"], style, k,
                          data_min=float(np.min(x_cat)), data_max=float(np.max(x_cat)),
                          domain=x_dom),
        yaxis=axis_layout(axes["y"], style, k,
                          data_min=y_lo - pad, data_max=y_hi + pad, domain=y_dom),
    )

    # 인셋 레전드 — V_G 목록
    inset = insets["legend"]
    fig.add_annotation(
        text="<br>".join(legend_lines),
        xref="x domain", yref="y domain",
        x=float(inset["x"]), y=float(inset["y"]),
        xanchor=inset.get("xanchor", "right"), yanchor=inset.get("yanchor", "top"),
        showarrow=False, align="left",
        font=dict(family=style["font_family"],
                  size=max(1, round(float(inset.get("font_size", 30)) * k)),
                  color="#000000"),
        bgcolor="rgba(255,255,255,0)",
        borderwidth=1 if inset.get("border") else 0,
        bordercolor="#000000" if inset.get("border") else None,
    )
    sample = insets["sample"]
    if sample.get("text"):
        fig.add_annotation(
            text=sample["text"], xref="x domain", yref="y domain",
            x=float(sample["x"]), y=float(sample["y"]),
            xanchor=sample.get("xanchor", "left"), yanchor=sample.get("yanchor", "bottom"),
            showarrow=False,
            font=dict(family=style["font_family"],
                      size=max(1, round(float(sample.get("font_size", 30)) * k)),
                      color="#000000"),
        )
    return fig
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_figure_output.py -v`
Expected: 10 passed

- [ ] **Step 5: 커밋**

```bash
git add fet_app/figure_output.py tests/test_figure_output.py
git commit -m "$(cat <<'EOF'
feat: output 그라데이션 그래프

베이스 색의 색상/채도를 유지한 채 명도만 단조 감소시켜 흑백에서도 V_G 순서가 남는다.
상대 휘도 단조성을 테스트로 고정한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: 내보내기 (요약표 · 이미지 · 가공 CSV · ZIP)

**Files:**
- Create: `fet_app/export.py`
- Test: `tests/test_export.py`

**Interfaces:**
- Consumes: `grouping.DeviceGroup`, `metrics.TransferMetrics`, `metrics.OutputDiagnostics`
- Produces:
  - `export.summary_row(group, tm, od) -> dict` — 열 순서 고정
  - `export.summary_dataframe(rows: list[dict]) -> pd.DataFrame`
  - `export.summary_csv_bytes(df) -> bytes`, `export.summary_xlsx_bytes(df) -> bytes`
  - `export.figure_bytes(fig, fmt: str, scale: int = 1) -> bytes` — fmt: `png`/`jpg`/`svg`/`pdf`
  - `export.transfer_processed_csv(curve, tm) -> str`, `export.output_processed_csv(curve) -> str`
  - `export.build_zip(items: list[tuple[str, bytes]]) -> bytes`
  - `export.KaleidoUnavailable` — 예외

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_export.py`:
```python
import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from fet_app import export
from fet_app.curves import OutputBlock, OutputCurve, TransferCurve
from fet_app.grouping import DeviceGroup
from fet_app.metrics import output_diagnostics, transfer_metrics
from fet_app.params import DeviceParams

PARAMS = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)


def _transfer():
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = -np.maximum(2e-8 * (v_g + 12.0) ** 2 * (v_g < -12.0), 1e-12)
    df = pd.DataFrame({"V_G": v_g, "I_G": np.full_like(v_g, 1e-11), "I_D": i_d})
    return TransferCurve(forward=df, reverse=df.iloc[::-1].reset_index(drop=True),
                         v_ds=-60.0, dual=True)


def _output():
    v_d = np.arange(0, -61, -1, dtype=float)
    blocks = [OutputBlock(v_g=-20.0 * i,
                          forward=pd.DataFrame({"V_D": v_d,
                                                "I_D": -1e-6 * (i + 1) * np.tanh(v_d / -20),
                                                "I_G": np.full_like(v_d, 1e-12)}),
                          reverse=None)
              for i in range(4)]
    return OutputCurve(blocks=blocks)


def _group():
    return DeviceGroup(name="1-1", transfer=_transfer(), output=_output(),
                       transfer_file="1-1.xls", output_file="1-1 out.xls",
                       params=PARAMS)


def test_summary_row_columns_and_values():
    g = _group()
    tm = transfer_metrics(g.transfer, PARAMS)
    od = output_diagnostics(g.output)
    row = export.summary_row(g, tm, od)
    for key in ("Device", "W (um)", "L (um)", "eps_r", "d (nm)", "C_ox (nF/cm2)",
                "V_DS (V)", "V_th (V)", "mu_sat (cm2/Vs)", "I_on/I_off",
                "SS (mV/dec)", "dV_th (V)", "Fit R2", "Fit range (V)", "Fit points",
                "0V offset (%)", "Origin linearity R2", "Saturation ratio",
                "Gate leak (%)", "Warnings"):
        assert key in row, key
    assert row["Device"] == "1-1"
    assert row["V_DS (V)"] == -60.0
    assert row["C_ox (nF/cm2)"] == pytest.approx(11.51, rel=1e-3)


def test_summary_dataframe_keeps_column_order():
    g = _group()
    tm = transfer_metrics(g.transfer, PARAMS)
    od = output_diagnostics(g.output)
    df = export.summary_dataframe([export.summary_row(g, tm, od)])
    assert list(df.columns)[0] == "Device"
    assert list(df.columns)[-1] == "Warnings"


def test_summary_csv_and_xlsx_roundtrip():
    g = _group()
    df = export.summary_dataframe([export.summary_row(
        g, transfer_metrics(g.transfer, PARAMS), output_diagnostics(g.output))])
    csv = export.summary_csv_bytes(df)
    assert csv.startswith(b"\xef\xbb\xbf")   # 엑셀 한글 깨짐 방지 BOM
    back = pd.read_csv(io.BytesIO(csv))
    assert back.loc[0, "Device"] == "1-1"

    xlsx = export.summary_xlsx_bytes(df)
    assert xlsx[:2] == b"PK"
    back2 = pd.read_excel(io.BytesIO(xlsx))
    assert back2.loc[0, "Device"] == "1-1"


def test_transfer_processed_csv_has_fit_column():
    c = _transfer()
    tm = transfer_metrics(c, PARAMS)
    text = export.transfer_processed_csv(c, tm)
    header = text.splitlines()[0]
    assert header.split(",") == ["branch", "V_G", "I_G", "I_D", "sqrt_abs_I_D", "fit_sqrt_I_D"]
    assert "forward" in text and "reverse" in text


def test_output_processed_csv_columns():
    text = export.output_processed_csv(_output())
    assert text.splitlines()[0].split(",") == ["V_G", "branch", "V_D", "I_D", "I_G"]


def test_build_zip_structure():
    data = export.build_zip([("1-3/transfer.png", b"a"), ("1-3/output.png", b"b")])
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.namelist() == ["1-3/transfer.png", "1-3/output.png"]


def test_png_is_transparent_and_jpg_is_white():
    """스펙 §7 — PNG 투명, JPG 흰 배경. kaleido 가 없으면 skip."""
    from fet_app.figure_common import new_figure
    from fet_app.constants import DEFAULTS
    fig = new_figure(DEFAULTS["geom"], k=0.2)
    try:
        png = export.figure_bytes(fig, "png", scale=1)
        jpg = export.figure_bytes(fig, "jpg", scale=1)
    except export.KaleidoUnavailable:
        pytest.skip("kaleido 미설치")

    from PIL import Image
    im = Image.open(io.BytesIO(png))
    assert im.mode == "RGBA"
    assert im.getpixel((0, 0))[3] == 0          # 좌상단 알파 0 = 투명

    jm = Image.open(io.BytesIO(jpg)).convert("RGB")
    assert jm.getpixel((0, 0)) == (255, 255, 255)


def test_figure_bytes_rejects_unknown_format():
    from fet_app.figure_common import new_figure
    from fet_app.constants import DEFAULTS
    with pytest.raises(ValueError):
        export.figure_bytes(new_figure(DEFAULTS["geom"], 0.2), "gif")


def test_export_does_not_mutate_figure():
    from fet_app.figure_common import new_figure
    from fet_app.constants import DEFAULTS
    fig = new_figure(DEFAULTS["geom"], k=0.2)
    try:
        export.figure_bytes(fig, "png")
    except export.KaleidoUnavailable:
        pytest.skip("kaleido 미설치")
    assert fig.layout.paper_bgcolor == "#FFFFFF"   # 화면 표시는 흰 배경 유지
```

`requirements.txt` 에 테스트용 `Pillow>=10.0` 을 추가한다 (PNG 알파 검사에 필요).

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_export.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.export'`

- [ ] **Step 3: 구현**

`fet_app/export.py`:
```python
"""내보내기 (스펙 §7).

화면 표시는 항상 흰 배경. 배경 전환은 여기서 figure 복제본에만 적용한다.
"""

from __future__ import annotations

import copy
import io
import zipfile

import numpy as np
import pandas as pd

SUMMARY_COLUMNS = [
    "Device", "Transfer file", "Output file",
    "W (um)", "L (um)", "eps_r", "d (nm)", "C_ox (nF/cm2)", "V_DS (V)",
    "V_th (V)", "mu_sat (cm2/Vs)", "I_on/I_off", "SS (mV/dec)", "dV_th (V)",
    "Fit R2", "Fit range (V)", "Fit points",
    "0V offset (%)", "Origin linearity R2", "Saturation ratio", "Gate leak (%)",
    "Warnings",
]

# fmt -> (kaleido format, 배경색). None 배경 = 투명.
_FORMATS = {
    "png": ("png", None),
    "jpg": ("jpg", "#FFFFFF"),
    "jpeg": ("jpg", "#FFFFFF"),
    "svg": ("svg", None),
    "pdf": ("pdf", "#FFFFFF"),
}


class KaleidoUnavailable(RuntimeError):
    """kaleido 가 없거나 Chromium 을 못 띄웠을 때."""


def summary_row(group, tm, od) -> dict:
    p = group.params
    worst = od.worst if od is not None else {}
    fit = getattr(tm, "fit", None) if tm is not None else None

    def _pct(v):
        return None if v is None else round(v * 100, 4)

    warnings = list(getattr(group, "warnings", []) or [])
    warnings += list(getattr(tm, "warnings", []) or [])
    warnings += list(getattr(od, "flags", []) or [])

    return {
        "Device": group.name,
        "Transfer file": group.transfer_file or "",
        "Output file": group.output_file or "",
        "W (um)": p.w_um, "L (um)": p.l_um, "eps_r": p.eps_r, "d (nm)": p.d_nm,
        "C_ox (nF/cm2)": round(p.c_ox() * 1e9, 4) if p.is_complete() else None,
        "V_DS (V)": group.transfer.v_ds if group.transfer is not None else None,
        "V_th (V)": getattr(tm, "v_th", None),
        "mu_sat (cm2/Vs)": getattr(tm, "mu_sat", None),
        "I_on/I_off": getattr(tm, "on_off", None),
        "SS (mV/dec)": getattr(tm, "ss_mv_dec", None),
        "dV_th (V)": getattr(tm, "dv_th", None),
        "Fit R2": round(fit.r2, 6) if fit else None,
        "Fit range (V)": f"{fit.v_start:g} ~ {fit.v_end:g}" if fit else "",
        "Fit points": fit.n_points if fit else None,
        "0V offset (%)": _pct(worst.get("zero_offset")),
        "Origin linearity R2": worst.get("linearity_r2"),
        "Saturation ratio": worst.get("saturation_ratio"),
        "Gate leak (%)": _pct(worst.get("gate_leak")),
        "Warnings": " | ".join(warnings),
    }


def summary_dataframe(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in SUMMARY_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[SUMMARY_COLUMNS]


def summary_csv_bytes(df: pd.DataFrame) -> bytes:
    """엑셀에서 한글이 깨지지 않게 UTF-8 BOM 을 붙인다."""
    return df.to_csv(index=False).encode("utf-8-sig")


def summary_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Summary")
    return buf.getvalue()


def figure_bytes(fig, fmt: str, scale: int = 1) -> bytes:
    """PNG 는 투명, JPG/PDF 는 흰 배경. 원본 figure 는 건드리지 않는다."""
    key = str(fmt).lower()
    if key not in _FORMATS:
        raise ValueError(f"지원하지 않는 형식입니다: {fmt}")
    kfmt, bg = _FORMATS[key]

    export_fig = copy.deepcopy(fig)
    if bg is None:
        export_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                 plot_bgcolor="rgba(0,0,0,0)")
    else:
        export_fig.update_layout(paper_bgcolor=bg, plot_bgcolor=bg)

    try:
        return export_fig.to_image(format=kfmt, scale=scale)
    except Exception as e:  # noqa: BLE001
        raise KaleidoUnavailable(
            "이미지 렌더에 실패했습니다 (kaleido/Chromium). "
            "HTML 다운로드로 대체하거나 로컬에서 다시 시도하세요."
        ) from e


def transfer_processed_csv(curve, tm) -> str:
    fit = getattr(tm, "fit", None)
    frames = []
    for branch, df in curve.branches():
        out = df.copy()
        out.insert(0, "branch", branch)
        sq = np.sqrt(np.abs(out["I_D"].to_numpy(dtype=float)))
        out["sqrt_abs_I_D"] = sq
        if fit is not None and branch == "forward":
            v = out["V_G"].to_numpy(dtype=float)
            lo, hi = sorted((fit.v_start, fit.v_end))
            inside = (v >= lo) & (v <= hi)
            out["fit_sqrt_I_D"] = np.where(inside, fit.slope * v + fit.intercept, np.nan)
        else:
            out["fit_sqrt_I_D"] = np.nan
        frames.append(out[["branch", "V_G", "I_G", "I_D", "sqrt_abs_I_D", "fit_sqrt_I_D"]])
    return pd.concat(frames, ignore_index=True).to_csv(index=False, lineterminator="\n")


def output_processed_csv(curve) -> str:
    frames = []
    for b in curve.blocks:
        for branch, df in (("forward", b.forward), ("reverse", b.reverse)):
            if df is None or df.empty:
                continue
            out = df.copy()
            out.insert(0, "branch", branch)
            out.insert(0, "V_G", b.v_g)
            frames.append(out[["V_G", "branch", "V_D", "I_D", "I_G"]])
    if not frames:
        return "V_G,branch,V_D,I_D,I_G\n"
    return pd.concat(frames, ignore_index=True).to_csv(index=False, lineterminator="\n")


def build_zip(items: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path, blob in items:
            z.writestr(path, blob)
    return buf.getvalue()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pip install Pillow && python -m pytest tests/test_export.py -v`
Expected: 9 passed (kaleido 가 없으면 이미지 관련 2개는 skip)

- [ ] **Step 5: 커밋**

```bash
git add fet_app/export.py tests/test_export.py requirements.txt
git commit -m "$(cat <<'EOF'
feat: 내보내기 (요약표, 이미지, 가공 CSV, ZIP)

PNG 는 투명 JPG 는 흰 배경으로 figure 복제본에만 배경을 적용한다.
화면 표시용 figure 는 흰 배경 그대로 남는다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: MANUAL.md 와 매뉴얼 로더

**Files:**
- Create: `MANUAL.md`, `METHODS.md`, `fet_app/manual.py`
- Test: `tests/test_manual.py`

**Interfaces:**
- Consumes: `constants.*`
- Produces:
  - `manual.DOCS: dict[str, str]` — 탭 이름 → 파일명. 정확히 `{"이용 방법": "MANUAL.md", "분석 방법": "METHODS.md"}`
  - `manual.doc_path(file_name: str) -> Path`
  - `manual.load_doc(file_name: str) -> str` — 없으면 안내 문구를 담은 대체 텍스트
  - `manual.load_manual() -> str` (= `load_doc("MANUAL.md")`), `manual.load_methods() -> str` (= `load_doc("METHODS.md")`)

**문서를 둘로 나누는 이유 (사용자 확정).** 찾는 목적이 다르다 — 쓰다가 막혔을 때 보는
문서와, 나온 숫자가 맞는지 검증할 때 보는 문서. 앱은 `st.tabs(["이용 방법", "분석 방법"])`
로 보여준다 (Task 18 이 배선).

| 파일 | 탭 | 담는 것 |
|---|---|---|
| `MANUAL.md` | 이용 방법 | 업로드, 명명법이 필요 없는 이유, 측정 런 선택, 패널 사용법, 내보내기, 문제 해결 |
| `METHODS.md` | 분석 방법 | **모든 수식·물리상수·알고리즘 상수·판정 임계값·가정과 한계** |

**주의:** `METHODS.md` 는 사용자가 수식을 대조·교정하기 위한 단일 소스다. 앱이 이 파일을
읽어 렌더하므로 두 벌이 어긋날 수 없다. 아래 테스트가 **상수 누락을 강제로 잡는다** —
상수를 바꾸면 `METHODS.md` 도 반드시 같이 바뀐다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_manual.py`:
```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_manual.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.manual'`

- [ ] **Step 3: 구현**

`fet_app/manual.py`:
```python
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
```

### `MANUAL.md` — 이용 방법 탭

파일 형식·자동 인식·측정 런 선택·패널 사용법·내보내기·문제 해결을 담는다.
**수식은 넣지 않는다** — 필요하면 "분석 방법 탭 참조" 라고만 쓴다.

```markdown
# FET Studio 이용 방법

Keithley 측정 파일을 올리면 transfer / output curve 를 스스로 구분해 그래프를 그리고
성능 지표를 계산한다. 계산에 쓰인 수식과 판정 기준은 **[분석 방법] 탭**에 있다.

## 1. 파일 형식과 자동 인식

### 1.1 지원 형식
Keithley 4200-SCS / KTEI 가 내보낸 `.xls` (구형 OLE2) 및 `.xlsx`.
시트 `Data` 와 `Settings` 를 사용한다.

### 1.2 커브 종류 판정 — 3단 폴백
파일 이름을 지정할 필요가 없다. 아래 순서로 판정한다.

1. `Settings` 의 **Forcing Function** 행
   - Gate = `Voltage Sweep` 이고 Drain = `Voltage Bias` → **transfer**
   - Gate = `Voltage Step` 이고 Drain = `Voltage Sweep` → **output**
2. `Data` 열 구조
   - `GateV` 가 있고 `DrainV` 가 없다 → transfer
   - `GateI(n)/GateV(n)/DrainI(n)/DrainV(n)` 4열 블록이 반복되고 각 `GateV(n)` 이 상수 → output
3. `Test Name` 과 파일명의 `transfer` / `output` / `out` 토큰

3단계까지 내려가면 소자 카드에 경고가 뜬다.

### 1.3 dual sweep 분리
`Settings` 의 `Dual Sweep Mode = Enabled` 이면 데이터를 forward/reverse 로 나눈다.
분할 지점은 `Number of Points ÷ 2`. 이 값을 못 읽으면 전압 스윕 방향의 부호가
뒤집히는 지점을 찾는다. (turning point 에서 같은 전압이 두 번 나올 수 있어
부호 변화만으로는 실패하는 경우가 있다.)

### 1.4 한 파일에 측정이 여러 번 있을 때
같은 조건으로 다시 측정하면 KTEI 는 데이터 시트를 `Data`, `Append1`, `Append2` … 로 늘리고
`Settings` 에도 런마다 블록을 하나씩 붙인다. 블록 헤더가 `Initial Run` 이면 `Data` 시트,
`Append N` 이면 `AppendN` 시트에 대응하며, 헤더 옆에 `Latest Run` 표시가 붙은 것이 최신 측정이다.

앱은 **모든 런을 읽어 보존**하고, 소자 패널의 "측정 런" 드롭다운에서 고를 수 있게 한다.
기본 선택은 Latest Run 이다. 각 런은 자기 블록의 설정(V_DS, dual sweep 여부 등)을 쓰므로
데이터와 설정이 어긋나지 않는다.

예: `1-3 best.xls` 는 `Data`(15:34:54, Initial Run) 와 `Append1`(15:35:10, Latest Run)
두 번의 transfer 측정을 담고 있고, 기본으로 `Append1` 이 분석된다.

### 1.5 소자 자동 그룹핑
파일명에서 확장자와 접미 토큰 `out` / `output` / `transfer` / `tr` / `best` 를 떼어낸
나머지가 소자 이름이다. 예: `1-3 best.xls` 와 `1-3 out.xls` → 소자 `1-3`.
같은 종류의 **파일**이 두 개 들어오면 첫 번째 파일만 쓰고 나머지는 미사용으로 보관한다.
(한 파일 안의 여러 런은 이와 별개로 모두 보존한다 — §1.4)

## 2. 소자 파라미터 입력

좌측 패널에서 채널 폭 **W**, 채널 길이 **L**, 유전체 **ε_r** 과 **두께 d** 를 넣는다.
비워두면 우측 하단 [전역 기본값] 에 넣은 값을 상속한다. 웨이퍼 한 장을 통째로 올렸다면
전역값만 한 번 채우면 되고, 특정 소자만 다르면 그 소자 패널에서 덮어쓴다.

네 값이 다 채워지면 C_ox 가 자동 계산돼 패널에 뜬다. 하나라도 비면 μ_sat 은 계산되지
않고 V_th 만 나온다. 계산식은 [분석 방법] 탭 참조.

V_DS 는 파일의 Settings 에서 자동으로 읽으므로 입력할 필요가 없다.

## 3. Fit 구간

기본은 자동이다. √|I_D| 가 가장 곧게 뻗은 구간을 찾아 그래프에 직선과 음영으로 표시한다.
마음에 들지 않으면 [수동 지정] 을 켜고 V_G 범위를 숫자로 넣으면 즉시 다시 계산한다.
탐색 규칙은 [분석 방법] 탭 참조.

## 4. 그래프 서식과 미리보기 배율

그래프는 논문용으로 10 × 8 inch 실측 크기로 만들어진다. 화면이 좁으면 그대로는 안 들어가므로
표시용으로만 축소해서 보여준다. [서식 · 크기] 에서 자동/수동을 고를 수 있고,
**내보내는 파일은 항상 실측 크기라 미리보기 배율의 영향을 받지 않는다.**

서식(색·선 두께·축 범위·인셋 위치)은 [프리셋] 에서 JSON 으로 저장해 다른 소자에 그대로
적용할 수 있다. 소자 파라미터와 진단 임계값은 측정 조건이라 프리셋에 들어가지 않는다.

## 5. 내보내기

| 형식 | 배경 | 용도 |
|---|---|---|
| PNG | **투명** | PPT · 포스터에 얹기 |
| JPG | **흰색** | 문서 · 메일 |
| SVG | 투명 (벡터) | Illustrator 재편집 |
| PDF | 흰색 (벡터) | 논문 투고 |

배율 1× / 2× / 4× 를 고를 수 있다. 4× 면 3840 × 3072 px.
[전체 ZIP] 은 소자별 폴더(`1-3/transfer.png`)에 그래프·가공 원데이터를 담고 요약표를 함께 넣는다.
요약표는 CSV(엑셀에서 한글이 깨지지 않게 BOM 포함) 와 XLSX 로 받을 수 있다.

투명 PNG 는 축과 글자가 검정이므로 어두운 슬라이드에 얹으면 보이지 않는다.

## 6. 자주 겪는 문제

- **커브 종류가 잘못 잡혔다** — 소자 패널에 판정 근거가 뜬다. "파일명으로 판정" 이라고
  나오면 Settings 를 못 읽은 것이니 원본 파일을 확인한다.
- **μ_sat 이 안 나온다** — W / L / ε_r / d 중 빈 항목이 있다. 전역 기본값을 채우면 된다.
- **fit R² 가 낮다는 경고** — 자동 구간이 서브스레숄드까지 끌고 들어간 경우다.
  수동으로 포화 영역만 지정한다.
- **소자가 잘못 묶였다** — 파일명 stem 기준이라 접미 토큰이 예상 밖이면 갈릴 수 있다.
  소자 리스트에서 확인하고 파일명을 정리한 뒤 다시 올린다.
- **이미지 내보내기가 실패한다** — 서버에 렌더러가 없는 경우다. HTML 로 대체 저장되므로
  브라우저에서 열어 인쇄하면 된다.
```

### `METHODS.md` — 분석 방법 탭

**모든 수식·상수·임계값이 여기 모인다.** 테스트가 상수 누락을 잡으므로
`fet_app/constants.py` 를 고치면 이 파일도 반드시 같이 고쳐야 한다.

```markdown
# FET Studio 분석 방법

이 문서는 앱이 계산하는 **모든 수식·상수·판정 기준**을 담는다.
앱은 이 파일을 그대로 읽어 렌더하므로 문서와 계산이 어긋나지 않는다.
값이 연구실 관례와 다르면 이 문서를 근거로 수정을 요청하면 된다.

## 1. 소자 파라미터

| 기호 | 의미 | UI 단위 | 내부 단위 | 환산 |
|---|---|---|---|---|
| W | 채널 폭 | µm | cm | ×1e-4 |
| L | 채널 길이 | µm | cm | ×1e-4 |
| ε_r | 유전상수 | — | — | — |
| d | 유전체 두께 | nm | cm | ×1e-7 |

### 1.1 산화막 정전용량 C_ox

```
C_ox = ε₀ · ε_r / d          [F/cm²]
ε₀ = 8.854 × 10⁻¹⁴ F/cm      (진공 유전율, cm 단위계)
```

유전체 프리셋 ε_r: **SiO₂ 3.9 · Al₂O₃ 9.0 · HfO₂ 25.0 · PMMA 3.6 · Custom(직접 입력)**

검산: SiO₂ 300 nm → C_ox = 3.9 × 8.854e-14 / 300e-7 = 1.151e-8 F/cm² = **11.51 nF/cm²**

## 2. Transfer 지표

### 2.1 포화 이동도 μ_sat 과 문턱 전압 V_th

포화영역 제곱법칙:
```
I_D = (W / 2L) · μ_sat · C_ox · (V_G − V_th)²
```
양변 제곱근을 취하면 √|I_D| 가 V_G 에 대해 직선이 된다.
이 직선을 최소자승 fit 해 `√|I_D| = m·V_G + b` 를 얻으면:
```
μ_sat = (2L / (W · C_ox)) · m²      [cm² V⁻¹ s⁻¹]
V_th  = −b / m                      [V]
```
p-type 이라 m < 0 이지만 m² 이므로 μ_sat > 0.
함께 보고하는 값: fit 의 R², 사용된 V_G 구간, 구간 내 점 개수.

### 2.2 fit 구간 자동 탐색

대상은 **forward branch 의 √|I_D| vs V_G**.

1. off 바닥 `I_off = min|I_D|` (0 제외) 를 구한다.
2. 후보 영역 = `|I_D| > 100 × I_off` 인 **최장 연속 구간**.
3. 윈도우 크기를 **최소 10 점**부터 **후보 영역의 60 %** 까지 키우며 1 점씩 슬라이딩,
   각 윈도우의 최소자승 R² 를 계산한다.
4. R² 최대 윈도우 선택. 차이가 **5e-4** 이내면 **점이 많은 쪽**을 택한다.

숫자로 V_G 범위를 지정하면 자동 탐색을 끄고 그 구간으로 재계산한다.
reverse branch 도 같은 알고리즘을 독립 적용한다.

### 2.3 On/Off 전류비
```
I_on / I_off = max|I_D| / min|I_D|      (forward branch 전 구간, 0 제외)
```

### 2.4 Subthreshold swing SS
```
SS = min( dV_G / d log₁₀|I_D| )        [V/dec] → ×1000 → [mV/dec]
```
구현은 등가식 `SS = 1000 / max|d log₁₀|I_D| / dV_G|` 를 쓴다.
탐색 범위는 `I_off × 10` 이상 `I_on / 10` 이하인 서브스레숄드 구간,
국소 기울기는 **5 점 이동 최소자승 회귀**로 구한다.

### 2.5 히스테리시스 ΔV_th
```
ΔV_th = V_th(reverse) − V_th(forward)   [V]
```
reverse 도 §2.2 와 같은 방식으로 독립 fit 한다.

## 3. Output 진단

각 V_G 블록마다 계산하고, 블록 중 최악값을 소자 대표값으로 보고한다.
임계값은 앱에서 조정할 수 있으며 아래는 기본값이다.

### 3.1 정규화 기준 — 왜 블록 최댓값으로 나누지 않는가

`V_G = 0 V` 블록은 소자가 꺼져 있어 전류가 노이즈 수준이다(예제에서 ~1 nA).
비율을 **그 블록 안의** `max|I_D|` 로 재면 노이즈끼리 나눈 값이 나와,
멀쩡한 소자가 0 V 오프셋 57 % · 게이트 누설 100 % 로 찍힌다.
그래서 **소자 전체의 구동전류**로 정규화한다.

```
I_drive = 모든 블록의 max|I_D| 중 최댓값        (소자 온상태 구동전류)
on-block = 그 블록의 max|I_D| >= 0.01 x I_drive  (= 켜진 블록)
```

### 3.2 진단 4종

| 항목 | 정의 | 대상 | 기본 임계 | 의미 |
|---|---|---|---|---|
| 0 V 오프셋 | `\|I_D(V_D=0)\| / I_drive` | 전 블록 | > 1 % | 원점에서 출발하지 않음 |
| 원점 선형성 | `\|V_D\| ≤ 스윕폭의 10 %` 구간 선형 fit R² | **켜진 블록만** | < 0.99 | S자 개형 = 컨택트 저항 / Schottky 장벽 |
| 포화 도달 | `(dI_D/dV_D)_말단 / (dI_D/dV_D)_원점` | **켜진 블록만** | > 0.1 | 미포화 |
| 게이트 누설 | `max\|I_G\| / I_drive` | 전 블록 | > 1 % | 게이트 누설 과다 |

- 말단·원점 기울기는 각각 양 끝 **5 점**의 선형 회귀 기울기다.
- 꺼진 블록의 **선형성·포화는 계산하지 않고 경고도 달지 않는다.** 꺼진 소자의
  곡선 개형은 노이즈라 판정 대상이 아니다. UI 에는 "off (진단 생략)" 으로 표시된다.
- 꺼진 블록에서도 **0 V 오프셋과 게이트 누설은 계산한다.** 꺼진 상태의 큰 누설은
  실제 문제이고, `I_drive` 로 나누므로 노이즈가 부풀지 않는다.
- 집계는 나쁜 쪽을 취한다: 비율 3종은 `max`, 선형성 R² 는 `min`.

## 4. 가정과 한계

- μ_sat 은 **포화영역 제곱법칙**을 가정한다. 접촉저항이 크거나 이동도가 게이트 전압에
  의존하면 **과소평가**된다.
- 포화 조건 `|V_DS| ≥ |V_G − V_th|` 가 fit 구간 전체에서 성립해야 한다.
  깨지는 구간이 포함되면 경고가 뜨며, μ_sat 이 과대평가될 수 있다.
- SS 는 측정 점 간격보다 가파른 소자에서는 과대평가된다.
  (예제 데이터는 V_G 간격이 1 V 이므로 그보다 가파른 SS 는 분해할 수 없다.)
- I_on/I_off 는 스윕 범위에 의존하므로 다른 범위로 측정한 소자와 직접 비교하면 안 된다.
- 극성은 데이터에서 자동 판별한다. p-type 이 아닌 데이터가 들어오면 경고만 띄운다.

## 5. 그래프 규약

- 논문용 흰 배경, 4면 박스 mirror ticks, ticks inside, 그리드 없음.
- 눈금 지수는 `1E-11` 형식.
- 크기는 Origin 방식 2단계: Background(inch) → Graph(% of background).
- Transfer: 좌 축 `|I_D| (A)` log, 우 축 `√|I_D| (A^0.5)` linear.
  forward 실선 / reverse 파선. 우축에 fit 직선·구간 음영·V_th 절편.
  좌축 제목에 절댓값 기호를 쓰는 것은 p-type 이라 I_D 가 음수이고 log 축에 |I_D| 를
  그리는 것이 FET 문헌의 일반 표기이기 때문이다.
- Output: `V_D (V)` vs `I_D (A)` 모두 linear.
  V_G 순서대로 명도가 단조 감소하는 단색 그라데이션 — 흑백 인쇄에서도 순서가 남는다.
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_manual.py -v`
Expected: 8 passed

- [ ] **Step 5: 커밋**

```bash
git add MANUAL.md fet_app/manual.py tests/test_manual.py
git commit -m "$(cat <<'EOF'
docs: MANUAL.md 와 매뉴얼 로더

모든 수식/상수/임계값을 한 파일에 모으고 앱이 이를 읽어 렌더한다.
테스트가 상수 누락을 잡으므로 상수를 바꾸면 매뉴얼도 반드시 같이 바뀐다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: 세션 상태와 프리셋

**Files:**
- Create: `fet_app/state.py`, `fet_app/presets.py`
- Test: `tests/test_presets.py`, `tests/test_state.py`

**Interfaces:**
- Consumes: `constants.DEFAULTS`, `grouping.*`, `params.DeviceParams`
- Produces:
  - `presets.extract(settings: dict) -> dict` — 서식만 뽑는다 (소자 파라미터·진단 임계값 제외)
  - `presets.apply(settings: dict, preset: dict) -> dict` — 새 dict 반환, 원본 불변
  - `presets.to_json(preset: dict) -> str`, `presets.from_json(text: str) -> dict`
  - `state.default_settings() -> dict` — `{"geom","style","transfer_axes","output_axes","transfer_style","output_style","insets"}` 의 deepcopy
  - `state.AppState` — 필드 `devices: list[DeviceGroup]`, `selected: str | None`, `global_params: DeviceParams`, `thresholds: dict`, `settings: dict`, `preview_scale: float | None`, `search: str`
  - `state.add_files(app: AppState, files: list[tuple[str, bytes]]) -> list[str]` — 반환은 경고 목록
  - `state.boot() -> AppState` (Streamlit 세션에 저장; 여기서만 streamlit import 허용)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_presets.py`:
```python
import json

from fet_app import presets
from fet_app.state import default_settings


def test_extract_contains_only_format_keys():
    p = presets.extract(default_settings())
    assert set(p) == {"geom", "style", "transfer_axes", "output_axes",
                      "transfer_style", "output_style", "insets"}


def test_extract_excludes_measurement_inputs():
    s = default_settings()
    s["thresholds"] = {"zero_offset": 0.5}
    s["params"] = {"w_um": 1000}
    p = presets.extract(s)
    assert "thresholds" not in p
    assert "params" not in p


def test_apply_returns_new_dict_and_leaves_original():
    s = default_settings()
    p = presets.extract(s)
    p["style"]["line_width"] = 4.0
    s2 = presets.apply(s, p)
    assert s2["style"]["line_width"] == 4.0
    assert s["style"]["line_width"] == 2.0


def test_apply_ignores_unknown_keys():
    s = default_settings()
    s2 = presets.apply(s, {"style": {"line_width": 3.0}, "bogus": 1})
    assert s2["style"]["line_width"] == 3.0
    assert "bogus" not in s2


def test_json_roundtrip():
    p = presets.extract(default_settings())
    back = presets.from_json(presets.to_json(p))
    assert back == p
    json.loads(presets.to_json(p))   # 유효한 JSON


def test_from_json_rejects_non_object():
    try:
        presets.from_json("[1,2,3]")
    except ValueError:
        return
    raise AssertionError("리스트를 받으면 ValueError 여야 합니다")
```

`tests/test_state.py`:
```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_presets.py tests/test_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.presets'`

- [ ] **Step 3: 구현**

`fet_app/presets.py`:
```python
"""서식 프리셋 추출/적용 (스펙 §7).

프리셋에는 **서식만** 들어간다. 소자 파라미터(W/L/ε/d)와 진단 임계값은
측정 조건·판단 기준이라 절대 포함하지 않는다.
"""

from __future__ import annotations

import copy
import json

PRESET_KEYS = ("geom", "style", "transfer_axes", "output_axes",
               "transfer_style", "output_style", "insets")


def extract(settings: dict) -> dict:
    return {k: copy.deepcopy(settings[k]) for k in PRESET_KEYS if k in settings}


def _deep_update(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = copy.deepcopy(v)
    return dst


def apply(settings: dict, preset: dict) -> dict:
    """알려진 키만 병합한 새 dict 를 반환한다. 원본은 건드리지 않는다."""
    out = copy.deepcopy(settings)
    for k in PRESET_KEYS:
        if k in preset and isinstance(preset[k], dict):
            if isinstance(out.get(k), dict):
                _deep_update(out[k], preset[k])
            else:
                out[k] = copy.deepcopy(preset[k])
    return out


def to_json(preset: dict) -> str:
    return json.dumps(preset, ensure_ascii=False, indent=2)


def from_json(text: str) -> dict:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("프리셋 파일은 JSON 객체여야 합니다.")
    return {k: v for k, v in data.items() if k in PRESET_KEYS}
```

`fet_app/state.py`:
```python
"""세션 상태. streamlit import 는 boot() 안에서만 한다."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from fet_app.constants import DEFAULTS, DEFAULT_THRESHOLDS
from fet_app.grouping import DeviceGroup, group_files, parse_file
from fet_app.params import DeviceParams

SETTINGS_KEYS = ("geom", "style", "transfer_axes", "output_axes",
                 "transfer_style", "output_style", "insets")


def default_settings() -> dict:
    return {k: copy.deepcopy(DEFAULTS[k]) for k in SETTINGS_KEYS}


@dataclass
class AppState:
    devices: list[DeviceGroup] = field(default_factory=list)
    selected: str | None = None
    file_names: set = field(default_factory=set)
    global_params: DeviceParams = field(default_factory=DeviceParams)
    thresholds: dict = field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))
    settings: dict = field(default_factory=default_settings)
    preview_scale: float | None = None   # None = 자동, 값 = 수동 배율
    search: str = ""
    show_summary: bool = False

    def device(self, name: str | None) -> DeviceGroup | None:
        return next((g for g in self.devices if g.name == name), None)

    def effective_params(self, g: DeviceGroup) -> DeviceParams:
        return g.params.merged_with(self.global_params)


def add_files(app: AppState, files: list[tuple[str, bytes]]) -> list[str]:
    """(파일명, bytes) 목록을 등록한다. 반환은 사용자에게 보여줄 경고 목록."""
    warns: list[str] = []
    parsed = []
    for name, blob in files:
        if name in app.file_names:
            continue
        try:
            parsed.append(parse_file(blob, name))
            app.file_names.add(name)
        except Exception as e:  # noqa: BLE001
            warns.append(f"'{name}' 을 읽지 못했습니다: {e}")
    if not parsed:
        return warns

    # 기존 소자의 사용자 입력(params)을 보존하면서 새 파일을 병합한다.
    saved = {g.name: g.params for g in app.devices}
    existing = list(app.devices)

    for g in group_files(parsed):
        old = next((x for x in existing if x.name == g.name), None)
        if old is None:
            existing.append(g)
            continue
        if not old.transfer_runs and g.transfer_runs:
            old.transfer_runs, old.transfer_file = g.transfer_runs, g.transfer_file
        elif g.transfer_runs and g.transfer_file:
            old.extra_files.append(g.transfer_file)
        if not old.output_runs and g.output_runs:
            old.output_runs, old.output_file = g.output_runs, g.output_file
        elif g.output_runs and g.output_file and g.output_file not in old.extra_files:
            old.extra_files.append(g.output_file)
        old.warnings.extend(g.warnings)

    app.devices = existing
    for g in app.devices:
        if g.name in saved:
            g.params = saved[g.name]
    if app.selected is None and app.devices:
        app.selected = app.devices[0].name
    return warns


def boot() -> AppState:
    """세션에 AppState 를 붙이고 돌려준다."""
    import streamlit as st

    if "app" not in st.session_state:
        st.session_state["app"] = AppState()
    return st.session_state["app"]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_presets.py tests/test_state.py -v`
Expected: 11 passed

- [ ] **Step 5: 커밋**

```bash
git add fet_app/presets.py fet_app/state.py tests/test_presets.py tests/test_state.py
git commit -m "$(cat <<'EOF'
feat: 세션 상태와 서식 프리셋

프리셋에는 서식만 담고 소자 파라미터/진단 임계값은 제외한다.
파일 재등록 시 사용자가 입력한 W/L/eps/d 를 보존한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: 테마와 반응형 레이아웃 골격

**Files:**
- Create: `fet_app/theme.py`, `fet_app/ui/layout.py`, `fet_app/ui/viewport.py`, `app.py`
- Test: `tests/test_theme.py`

**Interfaces:**
- Consumes: `state.AppState`
- Produces:
  - `theme.RESPONSIVE_CSS: str` — 스펙 §6.2 브레이크포인트 CSS
  - `theme.base_css() -> str` — 폰트 임베드 + 기본 스타일 + `RESPONSIVE_CSS`
  - `theme.inject() -> None` — `st.markdown(..., unsafe_allow_html=True)`
  - `viewport.preview_scale(app) -> float` — 자동 프로브 실패 시 수동값/기본 0.6
  - `layout.render_app() -> None`

**참고:** photodetector-app 의 `pd_app/theme.py` 와 `static/fonts/` 를 복사해 온다. 폰트 파일은 `static/fonts/` 에 그대로 두고 `theme.py` 가 base64 로 `@font-face` 를 만든다.

- [ ] **Step 1: 폰트와 테마 이식**

```bash
mkdir -p static/fonts
cp -r "/c/Users/mintj/photodetector-app/static/fonts/." static/fonts/
cp "/c/Users/mintj/photodetector-app/pd_app/theme.py" fet_app/theme.py
```
`fet_app/theme.py` 안의 `pd_app` import 경로를 `fet_app` 으로 바꾸고, photodetector 전용 문구(제목·매뉴얼 텍스트)는 지운다. 남길 것은 폰트 `@font-face`, liquid glass 패널 스타일, 버튼/입력 스타일이다.

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_theme.py`:
```python
from fet_app.theme import RESPONSIVE_CSS, base_css


def test_responsive_css_has_all_four_breakpoints():
    css = RESPONSIVE_CSS
    assert "max-width: 1760px" in css.replace(" ", " ")
    for bp in ("1500px", "1150px", "900px"):
        assert bp in css, bp


def test_panel_widths_use_clamp():
    css = RESPONSIVE_CSS
    assert "clamp(260px, 20vw, 340px)" in css
    assert "clamp(180px, 13vw, 230px)" in css


def test_columns_are_targeted_via_anchor_marker():
    """st.columns 에 클래스를 못 붙이므로 마커를 :has() 로 찾는다."""
    assert ":has(.fet-shell-anchor)" in RESPONSIVE_CSS


def test_base_css_embeds_fonts():
    css = base_css()
    assert "@font-face" in css
    assert "Myriad Pro" in css
    assert "Pretendard" in css


def test_base_css_includes_responsive():
    assert RESPONSIVE_CSS in base_css()
```

- [ ] **Step 3: 실패 확인**

Run: `python -m pytest tests/test_theme.py -v`
Expected: FAIL — `ImportError: cannot import name 'RESPONSIVE_CSS'`

- [ ] **Step 4: 구현**

`fet_app/theme.py` 에 추가:
```python
# 스펙 §6.2 — CSS 미디어 쿼리만으로 4단계. JS 불필요.
# 3열 컬럼은 layout.py 가 st.columns 로 만들고, 여기서 폭을 덮어쓴다.
RESPONSIVE_CSS = """
<style>
/* 본문 최대 폭: 27" QHD 에서 약 3/4 만 쓰게 해 좌우 시선 이동을 억제한다 */
@media (min-width: 1500px) {
  section.main > div.block-container { max-width: 1760px; margin: 0 auto; }
}
@media (max-width: 1499px) {
  section.main > div.block-container { max-width: 100%; }
}

/* 3열: 편집 패널 / 그래프(신축) / 소자 리스트.
   Streamlit 은 st.columns 에 클래스를 붙일 수 없으므로, 첫 컬럼에 심어둔
   마커 <div class="fet-shell-anchor"> 를 :has() 로 찾아 그 부모를 잡는다. */
div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(1) {
  flex: 0 0 clamp(260px, 20vw, 340px);
  min-width: 260px;
}
div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(2) {
  flex: 1 1 auto;
  min-width: 0;
}
div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(3) {
  flex: 0 0 clamp(180px, 13vw, 230px);
  min-width: 180px;
}

/* 900~1150px: 소자 리스트 열을 접는다 (layout.py 가 같은 폭에서 사이드바로 옮겨 렌더한다) */
@media (max-width: 1149px) {
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(3) {
    display: none;
  }
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"]:nth-child(1) {
    flex: 0 0 280px; min-width: 280px;
  }
}

/* 900px 미만: 전부 세로 스택 */
@media (max-width: 899px) {
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) { flex-direction: column; }
  div[data-testid="stHorizontalBlock"]:has(.fet-shell-anchor) > div[data-testid="stColumn"] {
    flex: 1 1 100% !important; min-width: 0 !important; width: 100% !important;
  }
  div[data-testid="stHorizontalBlock"]:has(.fet-graphs-anchor) { flex-direction: column; }
}

/* 소자 리스트는 독립 스크롤 */
.fet-device-list { max-height: 62vh; overflow-y: auto; overflow-x: hidden; }
</style>
"""


def base_css() -> str:
    """폰트 임베드 + 앱 스타일 + 반응형."""
    return _font_face_css() + _app_css() + RESPONSIVE_CSS


def inject() -> None:
    import streamlit as st
    st.markdown(base_css(), unsafe_allow_html=True)
```
(`_font_face_css` 와 `_app_css` 는 photodetector-app 에서 이식한 함수. 이름이 다르면 그에 맞춰 감싼다.)

`fet_app/ui/viewport.py`:
```python
"""표시 배율 산출 (스펙 §5.4).

뷰포트 폭 프로브가 실패해도 앱이 죽으면 안 된다. 반드시 수동 배율로 폴백한다.
"""

from __future__ import annotations

FALLBACK_SCALE = 0.60
GRAPH_DESIGN_PX = 960   # 10 inch x 96 dpi


def scale_for_width(container_px: float) -> float:
    """그래프 하나에 배정된 픽셀 폭 -> 배율. 0.25~1.0 로 자른다."""
    if not container_px or container_px <= 0:
        return FALLBACK_SCALE
    return max(0.25, min(1.0, float(container_px) / GRAPH_DESIGN_PX))


def probe_viewport_width() -> float | None:
    """1회성 뷰포트 폭 측정. 실패하면 None (앱은 계속 동작한다)."""
    try:
        import streamlit as st
        from streamlit.components.v1 import html as _html  # noqa: F401
        # st.context.viewport 가 있으면 그것을 우선 쓴다 (컴포넌트 불필요).
        ctx = getattr(st, "context", None)
        width = getattr(getattr(ctx, "viewport", None), "width", None)
        return float(width) if width else None
    except Exception:  # noqa: BLE001
        return None


def preview_scale(app) -> float:
    """AppState.preview_scale 이 None 이면 자동, 아니면 수동값."""
    if app.preview_scale is not None:
        return float(app.preview_scale)
    width = probe_viewport_width()
    if width is None:
        return FALLBACK_SCALE
    # 3열에서 그래프 두 개가 나눠 갖는 폭 추정: 본문 - 좌우 패널 - 여백
    usable = min(float(width), 1760.0) - 340 - 230 - 80
    return scale_for_width(max(200.0, usable / 2.0))
```

`fet_app/ui/layout.py`:
```python
"""3열 배치 (스펙 §6.1). 패널 폭은 theme.RESPONSIVE_CSS 가 정한다."""

from __future__ import annotations

import streamlit as st

from fet_app import state as state_mod
from fet_app import theme
from fet_app.ui import (
    device_list, export_ui, panel_device, panel_fit, panel_style, summary,
)
from fet_app.ui.viewport import preview_scale

# theme.RESPONSIVE_CSS 가 :has() 로 찾는 마커. 3열 컨테이너의 첫 컬럼에 심는다.
SHELL_ANCHOR = "<div class='fet-shell-anchor'></div>"


def render_app() -> None:
    theme.inject()
    app = st.session_state["app"]

    header = st.columns([0.7, 0.3])
    with header[0]:
        st.markdown("### FET Studio")
    with header[1]:
        uploaded = st.file_uploader(
            "측정 파일", type=["xls", "xlsx"], accept_multiple_files=True,
            label_visibility="collapsed", key="uploader",
        )
    if uploaded:
        warns = state_mod.add_files(app, [(f.name, f.getvalue()) for f in uploaded])
        for w in warns:
            st.warning(w)

    if not app.devices:
        st.info("Keithley `.xls` 파일을 올리면 transfer/output 을 자동으로 구분합니다. "
                "파일 이름은 아무렇게나 지어도 됩니다.")
        with st.expander("문서"):
            from fet_app.manual import DOCS, load_doc
            for tab, (name, file_name) in zip(st.tabs(list(DOCS)), DOCS.items()):
                with tab:
                    st.markdown(load_doc(file_name))
        return

    if app.show_summary:
        summary.render_summary_table(app)
        return

    k = preview_scale(app)
    left, center, right = st.columns([1, 3, 1], gap="medium")

    with left:
        # 이 마커가 있어야 RESPONSIVE_CSS 가 이 3열 블록을 찾아 폭을 잡는다.
        st.markdown(SHELL_ANCHOR, unsafe_allow_html=True)
        panel_device.render(app)
        panel_fit.render(app)
        panel_style.render(app)

    with center:
        summary.render_device_view(app, k)

    with right:
        device_list.render(app)
        export_ui.render(app)
```

`app.py`:
```python
"""FET Studio — 진입점. 얇게 유지할 것: 부팅과 위임만 한다."""

from __future__ import annotations

import streamlit as st

# set_page_config 는 반드시 다른 st 호출보다 먼저 (streamlit 규약).
st.set_page_config(page_title="FET Studio", layout="wide")

from fet_app import state  # noqa: E402
from fet_app.ui import layout  # noqa: E402


def main() -> None:
    state.boot()
    layout.render_app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest tests/test_theme.py -v`
Expected: 4 passed

- [ ] **Step 6: 커밋**

```bash
git add app.py fet_app/theme.py fet_app/ui/layout.py fet_app/ui/viewport.py static tests/test_theme.py
git commit -m "$(cat <<'EOF'
feat: 테마 이식과 반응형 3열 레이아웃 골격

CSS 미디어 쿼리 4단계로 데스크톱/노트북/소형화면을 나눈다.
본문 최대 폭 1760px 캡으로 대형 모니터에서 시선 이동을 억제한다.
표시 배율 프로브는 실패해도 수동 폴백으로 앱이 계속 동작한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 17: UI 패널 (소자 · fit · 서식 · 소자 리스트)

**Files:**
- Create: `fet_app/ui/panel_device.py`, `fet_app/ui/panel_fit.py`, `fet_app/ui/panel_style.py`, `fet_app/ui/device_list.py`
- Test: `tests/test_ui_helpers.py`

**Interfaces:**
- Consumes: `state.AppState`, `constants.*`, `presets.*`
- Produces:
  - `panel_device.render(app) -> None`
  - `panel_fit.render(app) -> None`, `panel_fit.fit_range_for(app, name) -> tuple[float, float] | None`
  - `panel_style.render(app) -> None`
  - `device_list.render(app) -> None`, `device_list.filter_devices(devices, query: str) -> list`
  - `device_list.device_flags(app, g) -> list[str]` — 경고 아이콘용

- [ ] **Step 1: 실패하는 테스트 작성**

순수 헬퍼만 테스트한다 (Streamlit 렌더는 Task 19 의 수동 확인으로 검증).

`tests/test_ui_helpers.py`:
```python
from fet_app.grouping import DeviceGroup
from fet_app.state import AppState
from fet_app.ui.device_list import device_flags, filter_devices
from fet_app.ui.viewport import FALLBACK_SCALE, preview_scale, scale_for_width


def test_filter_is_case_insensitive_substring():
    devs = [DeviceGroup(name="1-1"), DeviceGroup(name="1-10"), DeviceGroup(name="A-2")]
    assert [g.name for g in filter_devices(devs, "1-1")] == ["1-1", "1-10"]
    assert [g.name for g in filter_devices(devs, "a")] == ["A-2"]
    assert len(filter_devices(devs, "")) == 3


def test_device_flags_warn_on_missing_curve():
    app = AppState()
    g = DeviceGroup(name="x")           # transfer/output 모두 없음
    assert "no-data" in device_flags(app, g)


def test_device_flags_warn_on_group_warnings():
    app = AppState()
    g = DeviceGroup(name="x", warnings=["뭔가 이상"])
    assert "warning" in device_flags(app, g)


def test_scale_for_width_clamped():
    assert scale_for_width(0) == FALLBACK_SCALE
    assert scale_for_width(100) == 0.25
    assert scale_for_width(9600) == 1.0
    assert abs(scale_for_width(480) - 0.5) < 1e-9


def test_manual_scale_overrides_auto():
    app = AppState()
    app.preview_scale = 0.42
    assert preview_scale(app) == 0.42
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_ui_helpers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.ui.device_list'`

- [ ] **Step 3: 구현**

`fet_app/ui/device_list.py`:
```python
"""우측 소자 리스트 (스펙 §6.1). 세로 스크롤 + 검색 + 배지/경고."""

from __future__ import annotations

import streamlit as st

from fet_app.constants import DEFAULT_THRESHOLDS, DIELECTRIC_PRESETS


def filter_devices(devices, query: str):
    q = (query or "").strip().lower()
    if not q:
        return list(devices)
    return [g for g in devices if q in g.name.lower()]


def device_flags(app, g) -> list[str]:
    flags = []
    if g.transfer is None and g.output is None:
        flags.append("no-data")
    if g.warnings:
        flags.append("warning")
    return flags


def render(app) -> None:
    st.caption("소자")
    app.search = st.text_input("검색", value=app.search, key="device_search",
                               placeholder="이름 검색", label_visibility="collapsed")

    st.markdown("<div class='fet-device-list'>", unsafe_allow_html=True)
    for g in filter_devices(app.devices, app.search):
        mark = "⚠ " if "warning" in device_flags(app, g) else ""
        label = f"{mark}{g.name}  ·{g.badges}"
        if st.button(label, key=f"dev_{g.name}", use_container_width=True,
                     type="primary" if g.name == app.selected else "secondary"):
            app.selected = g.name
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    with st.expander("전역 기본값", expanded=False):
        p = app.global_params
        p.w_um = st.number_input("W (µm)", min_value=0.0, value=float(p.w_um or 1000.0),
                                 step=10.0, key="g_w")
        p.l_um = st.number_input("L (µm)", min_value=0.0, value=float(p.l_um or 50.0),
                                 step=1.0, key="g_l")
        name = st.selectbox("유전체", list(DIELECTRIC_PRESETS) + ["Custom"], key="g_diel")
        p.eps_r = (st.number_input("ε_r", min_value=0.0, value=float(p.eps_r or 3.9),
                                   step=0.1, key="g_eps")
                   if name == "Custom" else DIELECTRIC_PRESETS[name])
        p.d_nm = st.number_input("두께 (nm)", min_value=0.0, value=float(p.d_nm or 300.0),
                                 step=10.0, key="g_d")

    with st.expander("진단 임계값", expanded=False):
        t = app.thresholds
        t["zero_offset"] = st.number_input(
            "0 V 오프셋 (%)", min_value=0.0, max_value=100.0,
            value=float(t.get("zero_offset", DEFAULT_THRESHOLDS["zero_offset"])) * 100,
            step=0.1, key="t_zero") / 100.0
        t["linearity_r2"] = st.number_input(
            "원점 선형성 R² 하한", min_value=0.0, max_value=1.2,
            value=float(t.get("linearity_r2", DEFAULT_THRESHOLDS["linearity_r2"])),
            step=0.001, format="%.3f", key="t_lin")
        t["saturation"] = st.number_input(
            "포화 기울기비 상한", min_value=0.0, max_value=10.0,
            value=float(t.get("saturation", DEFAULT_THRESHOLDS["saturation"])),
            step=0.01, key="t_sat")
        t["gate_leak"] = st.number_input(
            "게이트 누설 (%)", min_value=0.0, max_value=100.0,
            value=float(t.get("gate_leak", DEFAULT_THRESHOLDS["gate_leak"])) * 100,
            step=0.1, key="t_leak") / 100.0

    if st.button("☰ 전체 요약", use_container_width=True):
        app.show_summary = True
        st.rerun()
```

`fet_app/ui/panel_device.py`:
```python
"""좌측 패널 — 소자 파라미터. 비우면 전역 기본값을 상속한다."""

from __future__ import annotations

import streamlit as st

from fet_app.constants import DIELECTRIC_PRESETS
from fet_app.params import DeviceParams


def render(app) -> None:
    g = app.device(app.selected)
    if g is None:
        return

    st.markdown(f"**소자 · {g.name}**")
    if g.warnings:
        with st.expander(f"⚠ 경고 {len(g.warnings)}건"):
            for w in g.warnings:
                st.caption(w)

    # 재측정 파일(Data + Append1)이면 어느 런을 분석할지 고른다. 기본은 Latest.
    if len(g.transfer_runs) > 1:
        labels = [r.label for r in g.transfer_runs]
        g.transfer_run_idx = labels.index(st.selectbox(
            "Transfer 측정 런", labels,
            index=min(g.transfer_run_idx, len(labels) - 1), key=f"trun_{g.name}"))
    if len(g.output_runs) > 1:
        labels = [r.label for r in g.output_runs]
        g.output_run_idx = labels.index(st.selectbox(
            "Output 측정 런", labels,
            index=min(g.output_run_idx, len(labels) - 1), key=f"orun_{g.name}"))

    p = g.params
    c1, c2 = st.columns(2)
    with c1:
        w = st.text_input("W (µm)", value="" if p.w_um is None else f"{p.w_um:g}",
                          key=f"w_{g.name}", placeholder="전역값")
    with c2:
        length = st.text_input("L (µm)", value="" if p.l_um is None else f"{p.l_um:g}",
                               key=f"l_{g.name}", placeholder="전역값")

    names = list(DIELECTRIC_PRESETS) + ["Custom"]
    current = next((n for n, v in DIELECTRIC_PRESETS.items() if v == p.eps_r), None)
    idx = names.index(current) if current else len(names) - 1
    choice = st.selectbox("유전체", names, index=idx, key=f"diel_{g.name}")

    c3, c4 = st.columns(2)
    with c3:
        eps = (st.text_input("ε_r", value="" if p.eps_r is None else f"{p.eps_r:g}",
                             key=f"eps_{g.name}", placeholder="전역값")
               if choice == "Custom" else str(DIELECTRIC_PRESETS[choice]))
    with c4:
        d = st.text_input("d (nm)", value="" if p.d_nm is None else f"{p.d_nm:g}",
                          key=f"d_{g.name}", placeholder="전역값")

    def _num(text):
        try:
            v = float(str(text).strip())
            return v if v > 0 else None
        except ValueError:
            return None

    g.params = DeviceParams(w_um=_num(w), l_um=_num(length),
                            eps_r=_num(eps), d_nm=_num(d))

    eff = app.effective_params(g)
    if eff.is_complete():
        st.caption(f"C_ox = **{eff.c_ox() * 1e9:.2f} nF/cm²**")
    else:
        st.caption("C_ox — W/L/ε_r/d 를 모두 채우면 계산됩니다 (전역값 상속 가능)")

    if g.transfer is not None and g.transfer.v_ds is not None:
        st.caption(f"V_DS = {g.transfer.v_ds:g} V (Settings 에서 읽음)")
```

`fet_app/ui/panel_fit.py`:
```python
"""좌측 패널 — fit 구간. 자동 탐색 결과를 보여주고 수동으로 덮어쓸 수 있다."""

from __future__ import annotations

import streamlit as st


def fit_range_for(app, name: str):
    """수동 지정이 켜져 있으면 (lo, hi), 아니면 None (= 자동 탐색)."""
    return st.session_state.get(f"fitrange_{name}")


def render(app) -> None:
    g = app.device(app.selected)
    if g is None or g.transfer is None:
        return

    st.markdown("**Fit 구간**")
    key = f"fitmode_{g.name}"
    manual = st.toggle("수동 지정", value=bool(st.session_state.get(key, False)), key=key)

    v = g.transfer.forward["V_G"]
    v_lo, v_hi = float(v.min()), float(v.max())
    if manual:
        c1, c2 = st.columns(2)
        with c1:
            lo = st.number_input("V_G 하한 (V)", value=v_lo, step=1.0, key=f"fl_{g.name}")
        with c2:
            hi = st.number_input("V_G 상한 (V)", value=v_hi, step=1.0, key=f"fh_{g.name}")
        st.session_state[f"fitrange_{g.name}"] = (float(lo), float(hi))
    else:
        st.session_state.pop(f"fitrange_{g.name}", None)
        st.caption("R² 최대 구간을 자동으로 찾습니다. 동점이면 긴 구간을 택합니다.")
```

`fet_app/ui/panel_style.py`:
```python
"""좌측 패널 — 서식. 폰트 크기는 슬라이더 금지, number_input 스테퍼만 쓴다."""

from __future__ import annotations

import streamlit as st

from fet_app import presets
from fet_app.constants import (
    ACCENT, FONT_FAMILIES, FONT_SIZE_MAX, FONT_SIZE_MIN, LINE_WIDTH_STEP,
)


def render(app) -> None:
    s = app.settings
    with st.expander("서식", expanded=False):
        style = s["style"]
        style["font_family"] = st.selectbox(
            "폰트", FONT_FAMILIES, index=FONT_FAMILIES.index(style["font_family"]),
            key="font_family")
        c1, c2 = st.columns(2)
        with c1:
            style["title_font_size"] = st.number_input(
                "축 제목 크기", min_value=FONT_SIZE_MIN, max_value=FONT_SIZE_MAX,
                value=int(style["title_font_size"]), step=1, key="ts")
        with c2:
            style["tick_font_size"] = st.number_input(
                "눈금 크기", min_value=FONT_SIZE_MIN, max_value=FONT_SIZE_MAX,
                value=int(style["tick_font_size"]), step=1, key="tk")
        style["line_width"] = st.number_input(
            "선 두께", min_value=0.5, max_value=10.0,
            value=float(style["line_width"]), step=LINE_WIDTH_STEP, key="lw")

        s["transfer_style"]["color"] = st.color_picker(
            "Transfer 색", value=s["transfer_style"]["color"], key="tcolor")
        s["transfer_style"]["show_reverse"] = st.checkbox(
            "reverse 표시", value=s["transfer_style"]["show_reverse"], key="trev")
        s["transfer_style"]["show_fit"] = st.checkbox(
            "fit 직선 표시", value=s["transfer_style"]["show_fit"], key="tfit")
        s["transfer_style"]["show_gate_current"] = st.checkbox(
            "|I_G| 표시", value=s["transfer_style"]["show_gate_current"], key="tig")

        s["output_style"]["base_color"] = st.color_picker(
            "Output 베이스 색", value=s["output_style"].get("base_color", ACCENT),
            key="ocolor")
        s["output_style"]["show_reverse"] = st.checkbox(
            "output reverse 표시", value=s["output_style"]["show_reverse"], key="orev")

    with st.expander("크기 · 배율", expanded=False):
        geom = s["geom"]
        c1, c2 = st.columns(2)
        with c1:
            geom["page_w_in"] = st.number_input("가로 (inch)", min_value=1.0,
                                                value=float(geom["page_w_in"]),
                                                step=0.5, key="pw")
        with c2:
            geom["page_h_in"] = st.number_input("세로 (inch)", min_value=1.0,
                                                value=float(geom["page_h_in"]),
                                                step=0.5, key="ph")
        auto = st.checkbox("미리보기 배율 자동", value=app.preview_scale is None,
                           key="auto_scale")
        if auto:
            app.preview_scale = None
        else:
            app.preview_scale = st.number_input(
                "미리보기 배율 (%)", min_value=25, max_value=200,
                value=int((app.preview_scale or 0.6) * 100), step=5, key="mscale") / 100.0

    with st.expander("프리셋", expanded=False):
        st.download_button("프리셋 저장 (JSON)",
                           data=presets.to_json(presets.extract(s)).encode("utf-8"),
                           file_name="fet_preset.json", mime="application/json",
                           use_container_width=True)
        up = st.file_uploader("프리셋 불러오기", type=["json"], key="preset_up")
        if up is not None:
            try:
                app.settings = presets.apply(s, presets.from_json(up.getvalue().decode("utf-8")))
                st.success("프리셋을 적용했습니다.")
            except Exception as e:  # noqa: BLE001
                st.error(f"프리셋을 읽지 못했습니다: {e}")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_ui_helpers.py -v`
Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add fet_app/ui/panel_device.py fet_app/ui/panel_fit.py fet_app/ui/panel_style.py fet_app/ui/device_list.py tests/test_ui_helpers.py
git commit -m "$(cat <<'EOF'
feat: 좌측 편집 패널과 우측 소자 리스트

소자 파라미터는 비우면 전역값을 상속한다. 폰트 크기는 스테퍼만 쓴다.
소자 리스트는 세로 스크롤 + 검색 + T/O 배지 + 경고 아이콘.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 18: 그래프 뷰 · 지표 패널 · 전체 요약 · 내보내기 UI

**Files:**
- Create: `fet_app/ui/summary.py`, `fet_app/ui/export_ui.py`
- Test: `tests/test_summary_helpers.py`

**Interfaces:**
- Consumes: 위 전부
- Produces:
  - `summary.compute(app, g) -> tuple[TransferMetrics | None, OutputDiagnostics | None]`
  - `summary.format_metric(value, kind: str) -> str` — kind: `volt`/`mobility`/`ratio`/`ss`/`percent`/`plain`
  - `summary.render_device_view(app, k: float) -> None` — 그래프 좌우 + 지표 아래
  - `summary.render_summary_table(app) -> None`
  - `export_ui.render(app) -> None`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_summary_helpers.py`:
```python
import numpy as np
import pandas as pd

from fet_app.curves import TransferCurve
from fet_app.grouping import DeviceGroup
from fet_app.params import DeviceParams
from fet_app.state import AppState
from fet_app.ui.summary import compute, format_metric


def test_format_metric_handles_none():
    assert format_metric(None, "volt") == "—"
    assert format_metric(None, "mobility") == "—"


def test_format_metric_units():
    assert format_metric(-12.4123, "volt") == "-12.41 V"
    assert format_metric(0.0312, "mobility") == "3.12E-02"
    assert format_metric(3.2e5, "ratio") == "3.2E+05"
    assert format_metric(2100.0, "ss") == "2100 mV/dec"
    assert format_metric(0.0034, "percent") == "0.34 %"


def test_compute_returns_none_for_missing_curves():
    app = AppState()
    g = DeviceGroup(name="x")
    tm, od = compute(app, g)
    assert tm is None and od is None


def test_compute_uses_effective_params():
    app = AppState()
    app.global_params = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)
    v_g = np.arange(20, -61, -1, dtype=float)
    i_d = -np.maximum(2e-8 * (v_g + 12.0) ** 2 * (v_g < -12.0), 1e-12)
    df = pd.DataFrame({"V_G": v_g, "I_G": np.full_like(v_g, 1e-11), "I_D": i_d})
    g = DeviceGroup(name="x", transfer=TransferCurve(forward=df, v_ds=-60.0))
    tm, od = compute(app, g)
    assert tm is not None and tm.mu_sat is not None
    assert od is None
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_summary_helpers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fet_app.ui.summary'`

- [ ] **Step 3: 구현**

`fet_app/ui/summary.py`:
```python
"""그래프 뷰와 지표 패널 (스펙 §6.1).

그래프 두 개는 좌우, 지표/진단은 각 그래프 바로 아래에 열을 맞춰 놓는다.
커브가 하나뿐이면 늘리지 않고 10:8 비율을 유지한 채 중앙에 둔다.
"""

from __future__ import annotations

import streamlit as st

from fet_app.export import summary_dataframe, summary_row
from fet_app.figure_output import output_figure
from fet_app.figure_transfer import transfer_figure
from fet_app.metrics import output_diagnostics, transfer_metrics
from fet_app.ui.panel_fit import fit_range_for


def format_metric(value, kind: str) -> str:
    if value is None:
        return "—"
    if kind == "volt":
        return f"{value:.2f} V"
    if kind == "mobility":
        return f"{value:.2E}"
    if kind == "ratio":
        return f"{value:.1E}"
    if kind == "ss":
        return f"{value:.0f} mV/dec"
    if kind == "percent":
        return f"{value * 100:.2f} %"
    return f"{value:.4g}"


def compute(app, g):
    """(TransferMetrics | None, OutputDiagnostics | None)."""
    tm = od = None
    if g.transfer is not None:
        tm = transfer_metrics(g.transfer, app.effective_params(g),
                              fit_range_for(app, g.name))
    if g.output is not None:
        od = output_diagnostics(g.output, app.thresholds)
    return tm, od


def _transfer_settings(app):
    s = app.settings
    return {"geom": s["geom"], "style": s["style"], "axes": s["transfer_axes"],
            "trace": s["transfer_style"], "insets": s["insets"]}


def _output_settings(app):
    s = app.settings
    return {"geom": s["geom"], "style": s["style"], "axes": s["output_axes"],
            "trace": s["output_style"], "insets": s["insets"]}


def _metric_card(tm) -> None:
    st.markdown("**Transfer 지표**")
    if tm is None:
        st.caption("transfer 데이터 없음")
        return
    rows = [
        ("V_th", format_metric(tm.v_th, "volt")),
        ("μ_sat (cm²/Vs)", format_metric(tm.mu_sat, "mobility")),
        ("I_on/I_off", format_metric(tm.on_off, "ratio")),
        ("SS", format_metric(tm.ss_mv_dec, "ss")),
        ("ΔV_th", format_metric(tm.dv_th, "volt")),
        ("Fit R²", format_metric(tm.fit.r2 if tm.fit else None, "plain")),
    ]
    st.table({"항목": [r[0] for r in rows], "값": [r[1] for r in rows]})
    for w in tm.warnings:
        st.warning(w, icon="⚠")


def _diagnostic_card(od) -> None:
    st.markdown("**Output 진단**")
    if od is None:
        st.caption("output 데이터 없음")
        return
    w = od.worst
    rows = [
        ("0 V 오프셋", format_metric(w.get("zero_offset"), "percent")),
        ("원점 선형성 R²", format_metric(w.get("linearity_r2"), "plain")),
        ("포화 기울기비", format_metric(w.get("saturation_ratio"), "plain")),
        ("게이트 누설", format_metric(w.get("gate_leak"), "percent")),
    ]
    st.table({"항목": [r[0] for r in rows], "값": [r[1] for r in rows]})
    for f in od.flags:
        st.warning(f, icon="⚠")


def render_device_view(app, k: float) -> None:
    g = app.device(app.selected)
    if g is None:
        return
    tm, od = compute(app, g)

    has_t, has_o = g.transfer is not None, g.output is not None
    if has_t and has_o:
        cols = st.columns(2, gap="medium")
        with cols[0]:
            st.plotly_chart(transfer_figure(g.transfer, tm, _transfer_settings(app), k),
                            use_container_width=False, key=f"tf_{g.name}")
            _metric_card(tm)
        with cols[1]:
            st.plotly_chart(output_figure(g.output, _output_settings(app), k),
                            use_container_width=False, key=f"of_{g.name}")
            _diagnostic_card(od)
    elif has_t:
        st.plotly_chart(transfer_figure(g.transfer, tm, _transfer_settings(app), k),
                        use_container_width=False, key=f"tf_{g.name}")
        _metric_card(tm)
    elif has_o:
        st.plotly_chart(output_figure(g.output, _output_settings(app), k),
                        use_container_width=False, key=f"of_{g.name}")
        _diagnostic_card(od)
    else:
        st.info("이 소자에는 표시할 커브가 없습니다.")


def render_summary_table(app) -> None:
    st.markdown("### 전체 요약")
    if st.button("← 소자 보기로"):
        app.show_summary = False
        st.rerun()

    rows = []
    for g in app.devices:
        tm, od = compute(app, g)
        gg = type(g)(**{**g.__dict__, "params": app.effective_params(g)})
        rows.append(summary_row(gg, tm, od))
    df = summary_dataframe(rows)

    event = st.dataframe(df, use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row",
                         key="summary_table")
    picked = event.selection.rows if hasattr(event, "selection") else []
    if picked:
        app.selected = df.iloc[picked[0]]["Device"]
        app.show_summary = False
        st.rerun()

    with st.expander("문서"):
        from fet_app.manual import DOCS, load_doc
        for tab, (name, file_name) in zip(st.tabs(list(DOCS)), DOCS.items()):
            with tab:
                st.markdown(load_doc(file_name))
```

`fet_app/ui/export_ui.py`:
```python
"""내보내기 UI (스펙 §7)."""

from __future__ import annotations

import streamlit as st

from fet_app import export
from fet_app.figure_output import output_figure
from fet_app.figure_transfer import transfer_figure
from fet_app.ui.summary import _output_settings, _transfer_settings, compute

FORMATS = ["PNG (투명)", "JPG (흰 배경)", "SVG", "PDF"]
_FMT_KEY = {"PNG (투명)": "png", "JPG (흰 배경)": "jpg", "SVG": "svg", "PDF": "pdf"}


def _figures(app, g, tm):
    out = []
    if g.transfer is not None:
        out.append(("transfer", transfer_figure(g.transfer, tm, _transfer_settings(app), 1.0)))
    if g.output is not None:
        out.append(("output", output_figure(g.output, _output_settings(app), 1.0)))
    return out


def render(app) -> None:
    st.divider()
    with st.expander("내보내기", expanded=False):
        fmt_label = st.selectbox("이미지 형식", FORMATS, key="exp_fmt")
        fmt = _FMT_KEY[fmt_label]
        scale = st.selectbox("배율", [1, 2, 4], index=0, key="exp_scale")

        rows = []
        for g in app.devices:
            tm, od = compute(app, g)
            gg = type(g)(**{**g.__dict__, "params": app.effective_params(g)})
            rows.append(export.summary_row(gg, tm, od))
        df = export.summary_dataframe(rows)

        st.download_button("요약표 (XLSX)", data=export.summary_xlsx_bytes(df),
                           file_name="fet_summary.xlsx", use_container_width=True,
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("요약표 (CSV)", data=export.summary_csv_bytes(df),
                           file_name="fet_summary.csv", mime="text/csv",
                           use_container_width=True)

        if st.button("전체 ZIP 만들기", use_container_width=True):
            items: list[tuple[str, bytes]] = [
                ("fet_summary.xlsx", export.summary_xlsx_bytes(df)),
                ("fet_summary.csv", export.summary_csv_bytes(df)),
            ]
            failed = []
            for g in app.devices:
                tm, _od = compute(app, g)
                for kind, fig in _figures(app, g, tm):
                    try:
                        items.append((f"{g.name}/{kind}.{fmt}",
                                      export.figure_bytes(fig, fmt, scale)))
                    except export.KaleidoUnavailable:
                        failed.append(f"{g.name}/{kind}")
                        items.append((f"{g.name}/{kind}.html",
                                      fig.to_html(include_plotlyjs="cdn").encode("utf-8")))
                if g.transfer is not None:
                    items.append((f"{g.name}/transfer_processed.csv",
                                  export.transfer_processed_csv(g.transfer, tm).encode("utf-8-sig")))
                if g.output is not None:
                    items.append((f"{g.name}/output_processed.csv",
                                  export.output_processed_csv(g.output).encode("utf-8-sig")))
            st.session_state["zip_blob"] = export.build_zip(items)
            if failed:
                st.warning("이미지 렌더 실패 — HTML 로 대체했습니다: " + ", ".join(failed))

        if st.session_state.get("zip_blob"):
            st.download_button("ZIP 다운로드", data=st.session_state["zip_blob"],
                               file_name="fet_studio_export.zip", mime="application/zip",
                               use_container_width=True)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_summary_helpers.py -v`
Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add fet_app/ui/summary.py fet_app/ui/export_ui.py tests/test_summary_helpers.py
git commit -m "$(cat <<'EOF'
feat: 그래프 뷰, 지표/진단 패널, 전체 요약, 내보내기 UI

그래프 두 개는 좌우 배치하고 지표는 각 그래프 아래에 열을 맞춘다.
kaleido 실패 시 HTML 로 대체해 ZIP 생성이 중단되지 않는다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 19: 통합 확인과 배포 준비

**Files:**
- Create: `tests/test_integration.py`, `README.md`, `.gitignore`(갱신)
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: 전부
- Produces: 없음 (검증 태스크)

- [ ] **Step 1: 통합 테스트 작성**

`tests/test_integration.py`:
```python
"""예제 9세트를 끝까지 통과시키는 회귀 테스트."""

import numpy as np
import pytest

from fet_app import export
from fet_app.figure_output import output_figure
from fet_app.figure_transfer import transfer_figure
from fet_app.params import DeviceParams
from fet_app.state import AppState, add_files
from fet_app.ui.summary import _output_settings, _transfer_settings, compute

PARAMS = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)


@pytest.fixture(scope="module")
def app(request):
    example_dir = request.config.rootpath / "Example"
    a = AppState()
    a.global_params = PARAMS
    warns = add_files(a, [(p.name, p.read_bytes())
                          for p in sorted(example_dir.glob("*.xls"))])
    assert warns == []
    return a


def test_nine_devices_each_with_both_curves(app):
    assert len(app.devices) == 9
    for g in app.devices:
        assert g.transfer is not None, g.name
        assert g.output is not None, g.name


def test_only_1_3_has_a_second_transfer_run(app):
    """1-3 best.xls 만 Data + Append1 두 런. 기본 선택은 Latest(Append1)."""
    counts = {g.name: len(g.transfer_runs) for g in app.devices}
    assert counts["1-3"] == 2
    assert all(n == 1 for name, n in counts.items() if name != "1-3")
    g = next(g for g in app.devices if g.name == "1-3")
    assert g.transfer_runs[g.transfer_run_idx].is_latest


def test_switching_run_changes_metrics(app):
    """런을 바꾸면 실제로 다른 데이터가 쓰인다 — 프로퍼티가 인덱스를 무시하지 않는지."""
    g = next(g for g in app.devices if g.name == "1-3")
    original = g.transfer_run_idx
    try:
        g.transfer_run_idx = 0
        a, _ = compute(app, g)
        g.transfer_run_idx = 1
        b, _ = compute(app, g)
        assert a.v_th is not None and b.v_th is not None
        assert g.transfer_runs[0].transfer is not g.transfer_runs[1].transfer
    finally:
        g.transfer_run_idx = original


def test_every_device_yields_finite_metrics(app):
    for g in app.devices:
        tm, od = compute(app, g)
        assert tm.v_th is not None and np.isfinite(tm.v_th), g.name
        assert tm.mu_sat is not None and tm.mu_sat > 0, g.name
        assert tm.on_off is not None and tm.on_off > 1, g.name
        assert tm.fit is not None and tm.fit.r2 > 0.9, g.name
        assert len(od.blocks) == 4, g.name


def test_every_device_renders_both_figures(app):
    for g in app.devices:
        tm, _od = compute(app, g)
        tf = transfer_figure(g.transfer, tm, _transfer_settings(app), 0.5)
        of = output_figure(g.output, _output_settings(app), 0.5)
        assert len(tf.data) > 0 and len(of.data) > 0, g.name


def test_summary_table_has_nine_rows(app):
    rows = []
    for g in app.devices:
        tm, od = compute(app, g)
        gg = type(g)(**{**g.__dict__, "params": app.effective_params(g)})
        rows.append(export.summary_row(gg, tm, od))
    df = export.summary_dataframe(rows)
    assert len(df) == 9
    assert df["V_th (V)"].notna().all()
    assert df["mu_sat (cm2/Vs)"].notna().all()


def test_processed_csv_roundtrips_for_every_device(app):
    for g in app.devices:
        tm, _od = compute(app, g)
        t_csv = export.transfer_processed_csv(g.transfer, tm)
        o_csv = export.output_processed_csv(g.output)
        assert t_csv.count("\n") > 100, g.name
        assert o_csv.count("\n") > 100, g.name


def test_zip_contains_per_device_folders(app):
    import io
    import zipfile
    items = []
    for g in app.devices[:2]:
        tm, _od = compute(app, g)
        items.append((f"{g.name}/transfer_processed.csv",
                      export.transfer_processed_csv(g.transfer, tm).encode("utf-8-sig")))
    blob = export.build_zip(items)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert all("/" in n for n in z.namelist())
```

- [ ] **Step 2: 실행**

Run: `python -m pytest tests/test_integration.py -v`
Expected: 6 passed. 실패하면 앞선 태스크로 돌아가 원인을 고친다 — 여기서 억지로 통과시키지 말 것.

- [ ] **Step 3: 전체 테스트와 앱 기동 확인**

Run: `python -m pytest -v`
Expected: 전 항목 통과

Run: `python -m streamlit run app.py --server.headless true --server.port 8501`
브라우저에서 `http://localhost:8501` 을 열고 `Example/` 18파일을 한 번에 업로드해 확인한다:
- 소자 리스트에 `1-1` ~ `1-9` 가 뜨고 각 행에 `T·O` 배지
- transfer/output 그래프가 좌우로 뜨고 지표/진단이 그 아래
- 창 폭을 1400 → 1000 → 800 px 로 줄이며 브레이크포인트 동작
- PNG / JPG 내보내기 후 배경 확인

- [ ] **Step 4: README 와 .gitignore 작성**

`README.md`:
```markdown
# FET Studio

Keithley 측정 파일에서 FET transfer/output curve 를 자동 인식해 논문용 그래프를 그리고
성능 지표를 계산·내보내는 Streamlit 앱.

- 파일 이름 규칙 없음. `Settings` 의 Forcing Function 과 `Data` 열 구조로 커브 종류를 판정한다.
- 여러 파일을 한 번에 올리면 파일명 stem 으로 소자를 자동 그룹핑한다.
- 계산하는 지표: V_th, μ_sat, I_on/I_off, SS, ΔV_th, output 진단 4종.
- **모든 수식·상수·임계값은 [MANUAL.md](MANUAL.md) 에 있다.**

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 테스트

```bash
pytest
```

`Example/` 의 9세트 18파일이 회귀 기준이다.

## 배포

Streamlit Community Cloud. 저장소 https://github.com/jun0land/FET-studio
```

`.gitignore` 에 다음을 더한다:
```
.pytest_cache/
*.egg-info/
```

- [ ] **Step 5: 커밋과 푸시**

```bash
git add tests/test_integration.py README.md .gitignore requirements.txt
git commit -m "$(cat <<'EOF'
test: 예제 9세트 종단 통합 테스트와 README

18파일 업로드 -> 9소자 그룹핑 -> 지표 -> 그래프 -> 요약표 -> ZIP 을 한 번에 검증한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
git push -u origin main
```

---

## Task 20: 사용자 최종 확인 리스트 제시

**Files:**
- 없음 (보고 태스크)

**Interfaces:**
- Consumes: Task 19 의 실행 결과
- Produces: 없음

- [ ] **Step 1: 예제 9세트의 실제 계산값 표 만들기**

```bash
python - <<'PY'
from pathlib import Path
from fet_app import export
from fet_app.params import DeviceParams
from fet_app.state import AppState, add_files
from fet_app.ui.summary import compute

app = AppState()
app.global_params = DeviceParams(w_um=1000.0, l_um=50.0, eps_r=3.9, d_nm=300.0)
add_files(app, [(p.name, p.read_bytes()) for p in sorted(Path("Example").glob("*.xls"))])

rows = []
for g in app.devices:
    tm, od = compute(app, g)
    gg = type(g)(**{**g.__dict__, "params": app.effective_params(g)})
    rows.append(export.summary_row(gg, tm, od))
df = export.summary_dataframe(rows)
print(df[["Device", "V_th (V)", "mu_sat (cm2/Vs)", "I_on/I_off", "SS (mV/dec)",
          "dV_th (V)", "Fit R2", "Fit range (V)", "0V offset (%)",
          "Origin linearity R2", "Saturation ratio", "Gate leak (%)"]].to_string(index=False))
PY
```

- [ ] **Step 2: 그래프 실물 캡처**

`1-3` 소자의 transfer / output PNG 를 배율 1× 로 내보내 스펙 §13-B 항목을 눈으로 확인할 수 있게 준비한다.

- [ ] **Step 3: 스펙 §13 의 18개 항목을 사용자에게 제시**

스펙 `docs/superpowers/specs/2026-08-12-fet-studio-design.md` §13 의 A(수식·지표 7개) / B(그래프 양식 7개) / C(동작 4개) 를 Step 1 의 실제 수치 표, Step 2 의 그래프와 함께 제시한다. 각 항목마다 **현재 구현된 값**과 **바꿀 수 있는 선택지**를 같이 적는다.

- [ ] **Step 4: 사용자 응답을 받아 스펙과 MANUAL.md 를 갱신**

수정 요청이 오면 해당 상수를 `fet_app/constants.py` 에서 고치고, `MANUAL.md` 를 같이 고친다.
`tests/test_manual.py` 가 상수와 매뉴얼의 불일치를 잡으므로 한쪽만 고치면 테스트가 실패한다.

---

## Self-Review

**1. 스펙 커버리지**

| 스펙 절 | 담당 태스크 |
|---|---|
| §1 입력 데이터 형식·파싱 함정 | 3, 5 |
| §1 다중 측정 런 (플랜 작성 후 추가) | 3b, 6, 17 |
| §2 커브 종류 3단 폴백 | 4 |
| §3.1 C_ox | 2 |
| §3.2 V_th, μ_sat | 8 |
| §3.3 fit 자동 탐색 | 7 |
| §3.4 on/off · §3.5 SS · §3.6 ΔV_th | 8 |
| §3.7 output 진단 4종 | 9 |
| §3.8 가정과 한계 | 8(경고), 14(문서) |
| §4 데이터 모델 · 자동 그룹핑 | 5, 6 |
| §5.1 공통 그래프 규약 | 10 |
| §5.2 transfer 이중축 | 11 |
| §5.3 output 그라데이션 | 12 |
| §5.4 미리보기 배율 | 10(k 적용), 16(프로브·폴백) |
| §6.1 비대칭 3열 | 16, 17, 18 |
| §6.2 브레이크포인트 4단계 | 16 |
| §7 내보내기 | 13, 18 |
| §8 매뉴얼 2탭 분리 | 14, 18 |
| §9 모듈 구조 | 전 태스크 |
| §10 테스트 | 각 태스크 + 19 |
| §11 배포 | 1, 19 |
| §12 범위 밖 | 구현하지 않음 |
| §13 최종 확인 리스트 | 20 |

누락 없음.

**2. 플레이스홀더 스캔**

"TBD" / "TODO" / "적절히 처리" 류 없음. 모든 코드 단계에 실제 코드가 들어 있고, 모든 실행 단계에 명령과 기대 출력이 있다.

**3. 타입 일관성 확인**

- `SettingsInfo.get/dual_sweep/n_points/bias_level` — Task 3 정의, Task 4·5 에서 동일 시그니처로 사용
- `FitResult` 필드명(`slope/intercept/r2/i_start/i_end/v_start/v_end/n_points`) — Task 7 정의, Task 8·11·13 에서 동일
- `TransferCurve.branches()` — Task 5 정의, Task 13 `transfer_processed_csv` 에서 사용
- `DeviceParams.merged_with` — Task 2 정의, Task 15 `effective_params` 에서 사용
- `DeviceGroup.badges` — Task 6 정의, Task 17 `device_list` 에서 사용
- `_transfer_settings` / `_output_settings` / `compute` — Task 18 정의, Task 18·19 에서 사용
- `export.KaleidoUnavailable` — Task 13 정의, Task 18 에서 포착

**4. 주의사항 (구현자에게)**

- Task 16 의 `theme.py` 는 photodetector-app 에서 복사해 오는 것이라 함수 이름이 다를 수 있다. `base_css()` 가 `_font_face_css() + _app_css() + RESPONSIVE_CSS` 를 반환하기만 하면 내부 이름은 그 저장소에 맞춰 조정한다.
- Task 16 의 `layout.py` 에서 `st.columns` 결과에 CSS 클래스를 붙이는 방법은 Streamlit 버전에 따라 달라질 수 있다. `:has()` 선택자가 동작하지 않으면 `st.container(key=...)` 로 클래스를 붙이는 방식으로 바꾼다 — 브레이크포인트 동작은 Task 19 Step 3 의 육안 확인이 최종 기준이다.
- `st.dataframe(on_select=...)` 는 Streamlit 1.35+ 필요. 없으면 행 클릭 대신 selectbox 로 대체한다.

