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
DIAG_ON_BLOCK_FRACTION = 0.01  # on-block 판정: 블록 max|I_D| >= 1 % of I_drive

DEFAULT_THRESHOLDS = {
    "zero_offset": 0.01,       # |I_D(0)| / I_drive 가 1 % 초과면 경고
    "linearity_r2": 0.99,      # 원점 구간 선형 fit R^2 가 0.99 미만이면 경고
    "saturation": 0.1,         # 말단/원점 기울기비가 0.1 초과면 미포화 경고
    "gate_leak": 0.01,         # max|I_G| / I_drive 가 1 % 초과면 경고
}

# ---------------- transfer fit 품질 (스펙 §3.2) ----------------
FIT_R2_WARN = 0.99             # transfer fit R^2 가 이 미만이면 사용자에게 경고

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

# 인셋 레전드 스와치 기하 (x/y domain 비율. plot 영역 픽셀 크기로 나눠 얻으므로
# k 배율은 분자·분모에서 함께 상쇄되어 자동으로 반영된다 — photodetector-app 참고)
INSET_PAD_X = 0.014      # 스와치 좌측 안쪽 여백 (x domain 비율)
INSET_SWATCH_W = 0.05    # 선 스와치 길이 (x domain 비율)
INSET_GAP = 0.014        # 스와치 <-> 텍스트 간격 (x domain 비율)
INSET_PAD_PX = 4         # 항목 위/아래 안쪽 여백 (px, k 배율 적용 후 domain 비율로 환산)
# 레전드 줄 높이 = 폰트 크기 x 이 값. 첨자가 있어도 늘리지 않는다 — 항목마다 주석을
# 따로 배치하므로 여분의 행간이 필요 없고, 늘리면 항목 사이가 눈에 띄게 벌어진다.
INSET_LINE_HEIGHT = 1.30
# 글자 폭 추정 계수 (폰트 크기 대비). Plotly 로는 실제 폭을 잴 수 없어 추정한다.
# 오른쪽 정렬 인셋에서 텍스트는 앵커로 붙이고 스와치를 이 추정값만큼 왼쪽에 두므로,
# 과대추정하면 스와치와 글자 사이가 벌어진다. 'V_G = -20 V' 를 30 px 로 렌더한
# 실측이 글자당 약 0.35 배라 약간의 여유만 둔다.
INSET_CHAR_W = 0.40

# 눈금 숫자 폭 추정 계수 (폰트 크기 대비). 축 제목이 눈금 숫자와 겹치지 않도록
# 필요한 여백을 계산할 때 쓴다 — Plotly 로는 실제 텍스트 폭을 잴 수 없다.
# 숫자·'E'·부호는 인셋 라벨(공백 포함 0.40)보다 폭이 커서 넉넉히 잡는다.
TICK_CHAR_W = 0.55
# 눈금 숫자와 축선 사이 기본 간격 + 제목 뒤 여유 (px, k 배율 적용 전).
AXIS_TITLE_PAD = 9.0

# fit 구간 음영 shape 의 이름. 내보내기에서 이 이름의 shape 만 걷어낸다
# (화면에서는 fit 구간을 보여주되, 논문에 넣을 그림에는 배경색을 남기지 않는다).
FIT_BAND_SHAPE_NAME = "fit_band"

# 커브 비교 뷰에서 소자마다 돌려 쓰는 색 (Okabe-Ito 색약 친화 팔레트).
# 흰 배경에서 가장 안 읽히는 노랑을 맨 뒤로 뺐고, 소자가 더 많으면 순환한다.
COMPARE_PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7",
                   "#E69F00", "#56B4E9", "#000000", "#F0E442"]

# ---------------- 스윕 방향 화살표 (Transfer) ----------------
# 전부 '플롯 영역의 짧은 변' 대비 비율. k 배율은 픽셀 크기와 함께 상쇄된다.
SWEEP_ARROW_SKIP = 0.03     # 반환점에서 이만큼 안쪽에서 화살표를 시작한다
SWEEP_ARROW_LEN = 0.14      # 화살표 호의 길이
SWEEP_ARROW_OFFSET = 0.028  # 커브에서 수직으로 띄우는 거리 (forward/reverse 반대편)
SWEEP_ARROW_HEAD_PX = 10.0  # 화살촉 꼬리 길이 (px, k 적용 전)
SWEEP_ARROW_MARGIN = 0.015  # 플롯 경계에서 최소 이만큼 안쪽에 둔다


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
    # Transfer/Output 은 각자 독립적인 배경 크기를 갖는다. Transfer 는 이중 Y축이라
    # 세로로 긴 8x10, Output 은 가로로 긴 10x8 이 기본이다.
    # graph_width_pct: Output 은 68.2, Transfer 는 65.0. 원래 Transfer 만 줄인 이유는
    # Plotly 가 축 제목을 종이(paper) 안쪽으로 클램프해서 68.2 에서 우Y(y2) 제목이
    # 눈금 숫자와 겹쳤기 때문인데(title_standoff 를 올려도 안 밀린다), 지금은
    # figure_common.fit_y_margins 가 눈금 라벨 폭을 재서 플롯 영역을 자동으로 안쪽에
    # 민다. 그래서 이 값은 '여유가 있을 때의 상한'일 뿐이고, 모자라면 자동으로 더
    # 좁아진다 (기본값에서는 실제 domain 이 0.188~0.812 로 잡힌다).
    "transfer_geom": {"page_w_in": 8.0, "page_h_in": 10.0, "graph_left_pct": 17.9,
                      "graph_top_pct": 11.58, "graph_width_pct": 65.0,
                      "graph_height_pct": 71.77},
    "output_geom": {"page_w_in": 10.0, "page_h_in": 8.0, "graph_left_pct": 17.9,
                    "graph_top_pct": 11.58, "graph_width_pct": 68.2,
                    "graph_height_pct": 71.77},
    "style": {"font_family": "Myriad Pro", "title_font_size": 30,
              "tick_font_size": 30, "line_width": 2.0, "show_grid": False},
    "transfer_axes": {
        "x": {"type": "linear", "auto": True, "min": None, "max": None,
              "dtick": 20.0, "minor_dtick": None,
              "title": "V_{G} (V)", "title_standoff": None},
        # 좌 Y: 절댓값 기호를 쓴다 (스펙 §5.2 — photodetector-app 규약 A2 를 뒤집음)
        # title_standoff: Plotly 기본값은 15 px 상당이라 30 px 눈금 글자 옆에서는
        # 제목이 숫자에 바짝 붙는다. 20 px 로 올려 여유를 둔다. 단, Plotly 는 축
        # 제목을 종이(paper) 안쪽으로 클램프하므로 여백이 모자란 축에서는 이 값을
        # 올려도 더 밀리지 않는다 (아래 y2 주석 참고).
        "y": {"type": "log", "auto": True, "min": None, "max": None,
              "dtick": 1, "minor_dtick": "D1",
              "title": "|I_{D}| (A)", "title_standoff": 20.0},
        # 우 Y 는 눈금 글자('0.012')가 넓어 여백이 가장 빠듯한 축이다. 예전에는
        # 이 값을 올려도 클램프 때문에 간격이 안 벌어져서 graph_width_pct 를 직접
        # 줄여야 했지만, 이제는 fit_y_margins 가 이 standoff 까지 포함해 필요한
        # 폭을 계산하고 플롯 영역을 그만큼 안쪽으로 민다.
        "y2": {"type": "linear", "auto": True, "min": None, "max": None,
               "dtick": None, "minor_dtick": None,
               "title": "√|I_{D}| (A^{0.5})", "title_standoff": 20.0},
    },
    "output_axes": {
        "x": {"type": "linear", "auto": True, "min": None, "max": None,
              "dtick": 20.0, "minor_dtick": None,
              "title": "V_{D} (V)", "title_standoff": None},
        "y": {"type": "linear", "auto": True, "min": None, "max": None,
              "dtick": None, "minor_dtick": None,
              "title": "I_{D} (A)", "title_standoff": 20.0},
    },
    "transfer_style": {
        # 이중 Y축이라 좌(log|I_D|)/우(√|I_D|) 마다 색을 준다. 축(선·눈금·제목)과
        # 커브(트레이스) 색은 서로 독립이다 — 검은 축에 색깔 커브처럼 논문에서
        # 흔한 조합을 만들 수 있어야 한다. 기본값은 넷 다 검정이라 외관은 그대로.
        # 게이트 전류(|I_G|)는 좌축에 속하므로 line_color_left 를 따른다.
        "axis_color_left": "#000000",
        "axis_color_right": "#000000",
        "line_color_left": "#000000",
        "line_color_right": "#000000",
        "show_reverse": True,
        "show_gate_current": False,
        "show_fit": True,
        # dual sweep 은 선 종류로 구분하지 않는다 — |I_D| 는 forward/reverse 모두
        # 실선, fit 을 얹는 √|I_D| 는 모두 점선이고, 방향은 반환점(스윕이 꺾이는
        # 쪽) 안쪽에 커브 모양을 따라 굽은 작은 화살표로 표시한다.
        "show_sweep_arrows": True,
    },
    "output_style": {
        "base_color": ACCENT,
        # Output 은 V_G 블록마다 커브가 여러 개라 reverse 까지 겹치면 그림이
        # 금세 지저분해진다 — 기본은 forward 만 그린다.
        "show_reverse": False,
        "lightness_min": 0.18,
        "lightness_max": 0.82,
        "manual_colors": {},   # {v_g(str): "#RRGGBB"} — 비어 있으면 그라데이션 사용
    },
    # 커브 비교 뷰 — 여러 소자의 transfer 를 한 그래프에 겹쳐 그린다.
    # colors 는 {소자명: "#RRGGBB"} 로, 비어 있으면 COMPARE_PALETTE 를 순서대로
    # 돌려 쓴다. 선택 자체(어떤 소자를 겹칠지)는 서식이 아니라 그때그때의 작업
    # 상태라 AppState.compare_selected 에 둔다.
    "compare": {
        "mode": "log",           # log = log|I_D| / sqrt = √|I_D|
        "show_reverse": False,   # 여러 커브를 겹치므로 기본은 forward 만
        "colors": {},
        "legend": True,
        # transfer 커브는 좌상 -> 우하로 흐르므로 두 모서리(좌하/우상)가 빈다.
        # Output 레전드(insets["legend"], 우하 기본)와 자리를 따로 갖는 이유다.
        "legend_pos": "bottom-left",
    },
    # 순간미분(포인트별 미분) 그래프. Transfer/Output 본 그래프 아래에 따로 그린다.
    # smooth 는 미분 '전' 원자료에 거는 이동평균 창(점 개수, 홀수)이다 — 포인트별
    # 중앙차분은 측정 노이즈를 그대로 증폭하므로 창을 키워 다듬을 수 있게 둔다.
    "derivative": {
        "show": False,
        "transfer_mode": "mu",   # gm | dsqrt | mu
        "smooth": 1,
        "y_type": "linear",      # linear | log
        "line_color": "#000000",
    },
    # p-type output 곡선은 원점(우상단)에서 좌하단으로 그어지므로, 두 인셋 기본값을
    # 데이터가 비어 있는 반대쪽 두 모서리(우하단/좌상단)로 둔다.
    "insets": {
        "legend": {"x": 0.99, "y": 0.01, "xanchor": "right", "yanchor": "bottom",
                   "font_size": 30, "bg_opacity": 0.0, "border": False},
        "sample": {"x": 0.01, "y": 0.99, "xanchor": "left", "yanchor": "top",
                   "text": "", "font_size": 30},
    },
}
