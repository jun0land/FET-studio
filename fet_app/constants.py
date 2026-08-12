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
