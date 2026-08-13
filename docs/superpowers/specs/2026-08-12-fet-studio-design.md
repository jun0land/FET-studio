# FET Studio — 설계 스펙 (2026-08-12 확정)

FET 측정 데이터(transfer / output curve)를 자동 인식해 논문용 그래프를 그리고,
성능 지표를 계산·내보내는 Streamlit 앱.

레퍼런스 앱: `C:\Users\mintj\photodetector-app` (그래프 규약·테마·모듈 구조를 이식)
예제 데이터: `Example/` — 9세트 18파일 (Keithley KTEI V9.1 `.xls`)

---

## 0. 확정된 결정 요약

| 항목 | 결정 |
|---|---|
| 구조 | 새 독립 프로젝트. photodetector-app 의 theme / 로더 / 그래프 규약만 **복사** 이식 |
| 커브 종류 구분 | **파일 내용 기반 자동**. 명명법 불필요 |
| 소자 파라미터 | 전역 기본값 + 소자별 오버라이드 |
| C_ox | 유전체 두께 + 유전상수로 자동 계산 |
| 파일 그룹핑 | 파일명 stem 자동 그룹 + 수동 재지정 |
| Transfer 지표 | V_th, μ_sat, I_on/I_off, SS, ΔV_th |
| Fit 구간 | 자동 탐색 + 수동 재조정 |
| Dual sweep | forward·reverse 둘 다 표시, 기본 지표는 forward |
| Transfer 축 | 이중 Y축 (좌 log\|I_D\|, 우 √\|I_D\|) |
| Output 진단 | 0V 오프셋 · 원점 선형성 · 포화 도달 · 게이트 누설 |
| Output 색상 | 단색 순차 그라데이션 |
| 내보내기 | 지표 요약표 · 그래프 이미지 · 가공 원데이터 · 서식 프리셋 |
| 레이아웃 | 비대칭 3열 (편집 좌 / 그래프 중앙 / 소자 리스트 우측 좁게) |
| 매뉴얼 | `MANUAL.md` + 앱 내 동일 내용. **모든 수식·상수·임계값 수록** |

---

## 1. 입력 데이터 형식 (예제 18파일 전수 확인 완료)

Keithley 4200-SCS / KTEI V9.1 이 내보낸 구형 OLE2 `.xls`.
시트 3개: `Data`, `Calc`(비어 있음), `Settings`.

### 1.1 Transfer 파일 (예: `1-1.xls`)

- `Data` 헤더: `GateI`, `GateV`, `DrainI` — 3열, 162 행
- `Settings` 발췌:
  ```
  Test Name        p_transfer#1@3
  Device Terminal  Source | Gate          | Drain
  Forcing Function Common | Voltage Sweep | Voltage Bias
  Start/Level      N/A    | 20            | -60
  Stop             N/A    | -60           | N/A
  Step             N/A    | -1            | N/A
  Number of Points N/A    | 162           | 0
  Dual Sweep Mode  N/A    | Enabled       | N/A
  ```
- 해석: V_DS = **−60 V** 고정 바이어스, V_G 를 20 → −60 V 로 1 V 씩 스윕(81 점),
  dual sweep 이므로 역방향 81 점이 이어 붙어 총 162 점.
- 극성: V_G, V_DS, I_D 모두 음수 → **p-type**.

### 1.2 Output 파일 (예: `1-1 out.xls`)

- `Data` 헤더: `GateI(n)`, `GateV(n)`, `DrainI(n)`, `DrainV(n)` — n = 1..4, 총 16열, 122 행
- `Settings` 발췌:
  ```
  Test Name        p_output#1@3
  Forcing Function Common | Voltage Step | Voltage Sweep
  Start/Level      N/A    | 0            | 0
  Stop             N/A    | -60          | -60
  Step             N/A    | -20          | -1
  Number of Points N/A    | 4            | 122
  Dual Sweep Mode  N/A    | N/A          | Enabled
  ```
- 해석: V_G 를 0 / −20 / −40 / −60 V 로 4 스텝, 각 스텝마다 V_D 를 0 → −60 V 로
  61 점 스윕 + dual sweep 역방향 61 점 = 122 점.
- 블록 개수(4)는 파일마다 다를 수 있으므로 **하드코딩 금지**. 열 개수 ÷ 4 로 산출.

### 1.3 다중 측정 런 (2026-08-12 추가 — 최초 조사 시 놓친 것)

`Example/1-3 best.xls` 는 시트가 `Data, Calc, Settings, Append1` 이고 **transfer 측정이 두 번**
들어 있다 (`Data` 162행, `Append1` 162행). `Settings` 도 블록이 두 개다:

```
==================================
Append 1        Latest Run          <- 15:35:10, 데이터는 Append1
==================================
...
==================================
Initial Run                         <- 15:34:54, 데이터는 Data
==================================
```

나머지 17개 파일은 단일 런이다.

**결정(사용자 확정): 모든 런을 읽어 보존하고 사용자가 고른다. 기본은 Latest Run.**

- Settings 블록 헤더를 시트 이름으로 정규화한다: `Initial Run` → `Data`, `Append N` → `AppendN`
- 각 런은 **자기 블록의 설정**(V_DS, dual sweep 여부, Number of Points)을 쓴다.
  블록을 합치면 데이터와 설정이 어긋난다.
- 소자 패널에 "측정 런" 드롭다운이 생긴다. 런이 하나뿐이면 표시하지 않는다.
- 이 규칙은 `MANUAL.md` §1.4 에 문서화한다.

### 1.4 알려진 파싱 함정

- `xlrd` 가 stdout 으로 OLE2 경고를 뱉는다 (`SSCS size is 0 but SSAT size is non-zero`,
  `file size not 512 + multiple of sector size`). 전부 무해하므로 **사용자에게 노출하지 않는다**.
  photodetector-app 의 `_quiet()` 컨텍스트 매니저를 그대로 이식.
- Dual sweep 의 turning point 에서 같은 전압이 2회 연속 나올 수 있어, 인접 차분의
  부호 변화만으로 분기점을 찾으면 실패한다. **`Number of Points ÷ 2` 로 분할**하고
  실패 시에만 부호 변화 탐색으로 폴백.

---

## 2. 커브 종류 자동 판정

명명법을 요구하지 않는다. 3단 폴백:

1. **`Settings` → `Forcing Function` 행** (1순위, 가장 신뢰도 높음)
   - Gate = `Voltage Sweep` **AND** Drain = `Voltage Bias` → **transfer**
   - Gate = `Voltage Step` **AND** Drain = `Voltage Sweep` → **output**
2. **`Data` 열 구조** (Settings 를 못 읽었을 때)
   - `GateV` 가 있고 `DrainV` 가 없다 → transfer
   - `GateV(n)`/`DrainV(n)` 형태의 4열 블록이 반복되고 각 블록의 `GateV(n)` 이 상수 → output
3. **`Test Name` / 파일명** (최후)
   - `transfer` / `output` 문자열 포함 여부, 파일명의 `out` 토큰

판정 결과와 근거(어느 단계에서 결정됐는지)를 소자 카드에 표시한다. 3단계까지 내려가면 경고.

---

## 3. 계산 수식 — 전부 `MANUAL.md` 에 그대로 수록할 것

> 이 절의 모든 식·상수·임계값은 매뉴얼에 **빠짐없이** 옮겨 적는다.
> 사용자가 나중에 대조해 수정 요청할 수 있어야 한다는 것이 매뉴얼의 존재 이유다.

### 3.1 산화막 정전용량

```
C_ox = ε₀ · ε_r / d
ε₀ = 8.854 × 10⁻¹⁴ F/cm      (진공 유전율, cm 단위계)
d  : 유전체 두께 [cm]  (UI 입력은 nm, 내부에서 ×1e-7)
```

유전체 프리셋 ε_r: **SiO₂ 3.9 · Al₂O₃ 9.0 · HfO₂ 25 · PMMA 3.6 · Custom(직접 입력)**
검산: SiO₂ 300 nm → C_ox = 3.9 × 8.854e-14 / 300e-7 = **1.151e-8 F/cm² = 11.51 nF/cm²**

### 3.2 포화 이동도와 문턱 전압

포화영역 제곱법칙:

```
I_D = (W / 2L) · μ_sat · C_ox · (V_G − V_th)²
```

양변 제곱근을 취하면 √|I_D| 가 V_G 에 대해 직선이 된다. 이 직선을 최소자승 fit 하여
`√|I_D| = m·V_G + b` 를 얻으면:

```
μ_sat = (2L / (W · C_ox)) · m²        [cm² V⁻¹ s⁻¹]
V_th  = −b / m                        [V]
```

- W, L 은 UI 입력이 µm, 내부에서 cm 로 환산 (×1e-4).
- p-type 이라 m < 0 이지만 m² 이므로 μ_sat > 0.
- 함께 보고할 값: fit 의 **R²**, 사용된 **V_G 구간**, 구간 내 **점 개수**.

### 3.3 Fit 구간 자동 탐색

대상: **forward branch 의 √|I_D| vs V_G**.

1. off 바닥 `I_off = min|I_D|` 를 구한다.
2. 후보 영역을 `|I_D| > 100 × I_off` 인 on-영역으로 제한한다.
3. 윈도우 크기를 **최소 10 점**부터 **후보 영역의 60 %** 까지 키우며 1점씩 슬라이딩,
   각 윈도우에서 최소자승 fit 의 R² 를 계산한다.
4. R² 최대 윈도우를 선택. **ΔR² < 5e-4 이내의 동점**이면 **점 개수가 많은 쪽**을 택한다.
5. 결과를 그래프에 fit 직선 · 구간 음영 · V_th 절편 마커로 표시한다.

사용자가 V_G 범위를 숫자로 덮어쓰면 자동 탐색을 끄고 즉시 재계산한다.
reverse branch 도 동일한 알고리즘을 독립 적용한다 (ΔV_th 용).

### 3.4 On/Off 전류비

```
I_on / I_off = max|I_D| / min|I_D|        (스윕 전 구간, forward branch)
```

### 3.5 Subthreshold swing

```
SS = min( dV_G / d(log₁₀|I_D|) )          [V/dec] → ×1000 → [mV/dec]
```

- 노이즈 억제를 위해 **5 점 이동 최소자승 회귀**로 국소 기울기를 구하고 그 중 최솟값을 취한다.
- 탐색 범위는 `I_off × 10` 이상 `I_on / 10` 이하인 서브스레숄드 구간.

### 3.6 히스테리시스

```
ΔV_th = V_th(reverse) − V_th(forward)     [V]
```

reverse 도 §3.3 과 같은 방식으로 독립 fit 한다.

### 3.7 Output curve 진단 4종

**정규화 기준 (2026-08-13 수정 — 구현 중 발견한 오경보 때문).**
처음에는 각 항목을 **블록 내** `max|I_D|` 로 나눴는데, `V_G = 0 V` 블록은 소자가 꺼져 있어
전류가 노이즈 수준(~1 nA)이다. 노이즈끼리 나누면 비율이 폭주해서 (`1-1 out.xls` 의 V_G=0
블록: 0V 오프셋 57.89 %, 게이트 누설 100.67 %) 멀쩡한 소자가 불량으로 찍혔다.
예제 9개 중 6개가 이 이유로 오경보였다.

**결정(사용자 확정):** 소자 전체의 구동전류로 정규화하고, 모양 판정은 켜진 블록에서만 한다.

```
I_drive = 모든 블록의 max|I_D| 중 최댓값      (소자 온상태 구동전류)
on-block = 그 블록의 max|I_D| >= 0.01 x I_drive
```

| 항목 | 정의 | 대상 | 기본 임계 | 의미 |
|---|---|---|---|---|
| **0 V 오프셋** | `\|I_D(V_D=0)\| / I_drive` | 전 블록 | > 1 % → ⚠ | 원점에서 출발하지 않음 (오프셋·누설) |
| **원점 선형성** | `\|V_D\| ≤ 스윕폭의 10 %` 구간 선형 fit 의 R² | **on-block 만** | R² < 0.99 → ⚠ | S자 개형 = 컨택트 저항 / Schottky 장벽 |
| **포화 도달** | `(dI_D/dV_D)_말단 / (dI_D/dV_D)_원점` | **on-block 만** | > 0.1 → ⚠ | 미포화 |
| **게이트 누설** | `max\|I_G\| / I_drive` | 전 블록 | > 1 % → ⚠ | 게이트 누설 과다 |

- off-block 의 선형성·포화는 `None` 으로 두고 경고하지 않는다. 꺼진 소자의 곡선 모양은
  노이즈라 판정할 대상이 아니다. UI 에는 "off (진단 생략)" 으로 표시한다.
- 0V 오프셋과 게이트 누설은 off-block 에서도 계산한다. 꺼진 상태의 큰 누설은 실제 문제이므로
  놓치면 안 되고, `I_drive` 로 나누므로 노이즈가 부풀지 않는다.
- 새 상수 `DIAG_ON_BLOCK_FRACTION = 0.01`.
- 말단·원점 기울기는 각각 양 끝 5 점의 선형 회귀 기울기.
- 4개 임계값은 모두 UI 에서 조정 가능. 조정값은 프리셋에 저장하지 않는다(측정 판단 기준이므로 전역 설정).
- 예제 데이터에서 V_G = −60 V 블록의 |I_G| 가 µA 급까지 올라가는 것이 관찰되므로
  게이트 누설 항목은 실제로 유효하게 동작해야 한다.

### 3.8 지표의 가정과 한계 (매뉴얼에 반드시 명시)

- μ_sat 은 **포화영역 제곱법칙**을 가정한다. 접촉저항이 크거나 이동도가 게이트 전압에
  의존하면 **과소평가**된다.
- 포화 조건 `|V_DS| ≥ |V_G − V_th|` 가 fit 구간 전체에서 성립하는지 검사하고,
  깨지는 구간이 포함되면 경고를 띄운다. (예제: V_DS = −60 V, V_G 최저 −60 V,
  V_th ≈ −10 V 라면 |V_G − V_th| ≈ 50 < 60 으로 성립)
- SS 는 측정 점 간격(1 V)보다 가파른 소자에서는 과대평가된다.
- I_on/I_off 는 스윕 범위에 의존하므로 다른 범위로 측정한 소자와 직접 비교하면 안 된다.

---

## 4. 데이터 모델

```
DeviceGroup                     # 소자 하나 = 탭 하나
  name: str                     # 파일명 stem, 예 "1-1"
  transfer: TransferCurve | None
  output:   OutputCurve   | None
  params:   DeviceParams        # W, L, ε_r, d (미입력 시 전역값 상속)
  extra_files: list[str]        # 그룹에 들어왔지만 미사용

TransferCurve
  v_ds: float                   # Settings 에서 추출
  forward: DataFrame            # V_G, I_G, I_D
  reverse: DataFrame | None
  dual: bool

OutputCurve
  blocks: list[OutputBlock]
OutputBlock
  v_g: float
  forward: DataFrame            # V_D, I_D, I_G
  reverse: DataFrame | None
```

### 4.1 자동 그룹핑

파일명에서 확장자와 알려진 접미 토큰(`out`, `output`, `best`, `transfer`, 공백/하이픈/언더바
구분)을 제거한 나머지를 stem 으로 삼는다. 예제 기준:

```
1-1.xls, 1-1 out.xls        → "1-1"
1-3 best.xls, 1-3 out.xls   → "1-3"
```

같은 stem 에 transfer 가 2개 이상 들어오면 첫 번째를 사용하고 나머지는 `extra_files` 로
보관, UI 에서 교체 가능. 그룹이 틀렸으면 소자 리스트에서 파일을 다른 그룹으로 옮길 수 있다.

---

## 5. 그래프

### 5.1 공통 규약 (photodetector-app 에서 이식, 변경 금지)

- **논문용 흰 배경**. glass 효과 금지.
- 4면 박스 mirror ticks, ticks **inside**, 그리드 없음.
- 눈금 지수 표기는 항상 `1E-11` 형식 (`exponentformat="E"`).
- 크기는 Origin 방식 2단계 지정:
  1. Background: width / height (**inch**, 기본 10 × 8)
  2. Graph: Left / Top / Width / Height (**% of background**, 기본 17.9 / 11.58 / 68.2 / 71.77)
  - figure px = inch × 96 dpi, `xaxis.domain=[L, L+W]`, `yaxis.domain=[1−(T+H), 1−T]`, margin 0
- Major / Minor tick 간격 개별 조절. log 축 minor 는 `dtick="D1"`.
- 축 범위 auto 일 때도 데이터 min/max 를 명시해 Plotly 자동 패딩 제거.
- 폰트: Myriad Pro(기본) · Pretendard · Arial · Times New Roman · Calibri · Helvetica · Courier New.
  기본 크기 **30**, 범위 6–50, **슬라이더 금지 — `st.number_input` 스테퍼**.
- 선 두께 **0.5 단위**.
- Plotly 기본 레전드 **제거**. 드래그 가능한 **인셋 레전드** + **샘플명 인셋** 사용.
- 트레이스 on/off 는 레전드가 아니라 좌측 편집 패널에서.

> **이식하지 않는 규약 — 축 제목의 절댓값 기호.**
> photodetector-app 규약 A2 는 `|Current|` 표기를 금지하지만 FET 에서는 채택하지 않는다.
> 근거는 §5.2 참조. 나머지 규약은 전부 그대로 따른다.

### 5.2 Transfer 그래프 — 이중 Y축

- X: `V_G (V)`
- 좌 Y: **log**, 제목 `|I_D| (A)` — **절댓값 기호를 쓴다.**
  photodetector-app 은 규약 A2 로 절댓값 기호를 금지했지만, **FET 에서는 p-type 이라
  I_D 가 음수이고 log 축에 |I_D| 를 그리는 것이 일반적인 표기이므로 반대로 간다.**
  두 앱은 서로 다른 데이터를 다루므로 이 항목은 의도적으로 규칙이 다르다.
- 우 Y: **linear**, 제목 `√|I_D| (A^0.5)`
- forward = 실선, reverse = 파선 (같은 색)
- 우축 위에 fit 직선 · fit 구간 음영 · V_th 절편 마커 오버레이
- 게이트 전류 `|I_G|` 표시 토글 (기본 꺼짐, 켜면 좌축에 점선)

### 5.3 Output 그래프 — 단색 순차 그라데이션

- X: `V_D (V)`, Y: `I_D (A)` — **linear** 스케일 (log 아님)
- 베이스 색 하나(기본 ACCENT `#ed542b`)에서 V_G 순서대로 **명도 단조 감소**.
  흑백 인쇄·색약 조건에서도 순서가 유지되어야 한다.
- 베이스 색은 사용자가 변경 가능. 개별 곡선 색 수동 지정도 허용.
- forward = 실선, reverse = 파선
- 인셋 레전드에 각 곡선의 V_G 값 표시

### 5.4 미리보기 배율

그래프는 실측 960 × 768 px 로 생성되지만 좌우 배치 시 화면 배정폭은 500 px 남짓이다.
Plotly 는 컨테이너에 맞춰 늘려도 폰트(30 pt)를 그대로 두므로 글자만 거대해진다.

→ **표시용으로만 figure 전체(크기 · 폰트 크기 · 선 두께)에 배율 k 를 곱한다.**
내보내기는 항상 k = 1 실측 크기이므로 출력물은 영향받지 않는다.

- k 는 뷰포트 폭을 1회 측정하는 초경량 커스텀 컴포넌트로 자동 산출.
- **프로브 실패 시 수동 배율(25–200 %, 기본 60 %)로 폴백.** 컴포넌트가 죽어도 앱은 동작해야 한다.

---

## 6. 레이아웃 / 반응형

### 6.1 비대칭 3열

```
┌─ 편집 패널 ────┬─ 그래프 (신축) ──────────────────┬ 소자 ──┐
│ 소자           │  ┌ Transfer ──┐  ┌ Output ────┐ │ 🔍[   ]│
│  W / L / ε / d │  │            │  │            │ │ 1-1 T·O│
│  → C_ox 표시   │  └────────────┘  └────────────┘ │▶1-3 ⚠  │
│ Fit            │  ┌ 지표 ──────┐  ┌ 진단 ──────┐ │  ...   │
│ 서식           │  └────────────┘  └────────────┘ │[전체요약]│
└───────────────┴─────────────────────────────────┴────────┘
 clamp(260,20vw,340)        flex: 1           clamp(180,13vw,230)
```

- 지표 패널은 각 그래프 **바로 아래에 열을 맞춰** 배치한다.
- 커브가 한 종류뿐인 소자는 그 그래프 하나만 중앙 정렬하고 **10:8 비율을 유지**한다(늘리지 않음).
- 소자 리스트 각 행: 소자명 + 보유 커브 배지(`T`/`O`) + 경고 아이콘.
  검색 필터, `↑`/`↓` 키 이동 지원.
- **[전체 요약]**: 모든 소자를 행으로 놓은 지표 테이블 뷰. 열 정렬 가능, 행 클릭 시 해당 소자로 점프.
- 전역 기본값(W/L/ε/d, 진단 임계값)은 소자 리스트 하단에 배치.

### 6.2 브레이크포인트 (CSS 미디어 쿼리, JS 불필요)

| 폭 | 배치 |
|---|---|
| **≥ 1500 px** | 3열, 그래프 좌우. 본문 `max-width: 1760px` 중앙 정렬 |
| **1150–1500 px** | 3열 유지, max-width 해제해 화면을 꽉 채움. 패널은 하한(260/180)까지 축소 |
| **900–1150 px** | 소자 리스트를 Streamlit 접이식 사이드바로 이동 → 2열, 그래프는 여전히 좌우 |
| **< 900 px** | 전부 세로 스택 (편집 → 그래프 → 지표), 그래프도 상하 |

1760 px 캡의 근거: 27" QHD 에서 화면의 약 3/4 을 사용해 좌우 시선 이동을 억제하고,
그보다 넓은 모니터에서 더 벌어지지 않게 한다. 노트북(FHD 이하)에서는 캡이 걸리지 않아
화면을 최대한 활용한다.

---

## 7. 내보내기

| 형식 | 내용 |
|---|---|
| `fet_summary.xlsx` / `.csv` | 소자별 1행: 이름, W, L, ε_r, d, C_ox, V_DS, V_th, μ_sat, I_on/I_off, SS, ΔV_th, fit R², fit 구간, 점 개수, output 진단 4종, 경고 플래그 |
| `PNG` | 배경 **완전 투명** (`rgba(0,0,0,0)`) — PPT·포스터 합성용 |
| `JPG` | 배경 **흰색** `#FFFFFF` (알파 미지원) — 문서·메일용 |
| `SVG` | 투명, 벡터 — Illustrator 재편집용 |
| `PDF` | 흰색, 벡터 — 논문 투고용 |
| `*_processed.csv` | transfer: V_G, I_G, I_D, √\|I_D\|, branch(fwd/rev), fit 직선값 / output: V_D, I_D, I_G, V_G, branch |
| `preset.json` | 색 · 선 두께 · 축 범위/스케일 · geom · 인셋 위치 · 폰트. 다른 소자에 즉시 적용 |

- 배경 전환은 **내보내기 시점에만** 적용한다. 화면 표시는 항상 흰 배경.
- 배율 1× / 2× / 4× 선택 (4× = 3840 × 3072 px).
- 개별 다운로드 + 전체 ZIP 일괄. ZIP 내부 구조는 소자별 폴더: `1-3/transfer.png`, `1-3/output.png`.
- 렌더는 `kaleido`. `requirements.txt` 에 반드시 포함.

---

## 8. 매뉴얼 — 두 탭으로 분리 (2026-08-13 사용자 확정)

문서를 **성격별로 두 개**로 나누고, 앱에서는 `st.tabs(["이용 방법", "분석 방법"])` 로 보여준다.
찾는 목적이 다르기 때문이다 — 쓰다가 막혔을 때와, 나온 숫자를 검증할 때.

| 파일 | 탭 | 내용 |
|---|---|---|
| `MANUAL.md` | **이용 방법** | 파일 업로드, 명명법이 필요 없는 이유, 측정 런 선택, 각 패널 사용법, 내보내기, 자주 겪는 문제 |
| `METHODS.md` | **분석 방법** | 모든 수식·물리상수·알고리즘 상수·판정 임계값·가정과 한계 |

- 두 파일 모두 저장소 루트에 둔다. 텍스트라 diff 가 되고 수정 요청이 쉽다.
- 앱은 이 파일들을 **읽어서** 렌더하므로 문서와 앱이 어긋날 수 없다.
- 수식은 LaTeX 로 쓴다.
- **판정 기준·수식은 전부 `METHODS.md` 에 둔다.** `MANUAL.md` 에서는 필요할 때 참조만 한다.

### `METHODS.md` 수록 항목 (누락 금지)

- §3 의 모든 수식: C_ox, μ_sat, V_th, I_on/I_off, SS, ΔV_th, output 진단 4종
- 각 기호의 의미와 **단위**, 내부 단위 환산 규칙 (µm→cm, nm→cm)
- 물리 상수: ε₀ = 8.854 × 10⁻¹⁴ F/cm
- 유전체 프리셋 ε_r 전체 값
- fit 자동 탐색 알고리즘의 상수 전부: on-영역 기준 `100 × I_off`, 최소 윈도우 10 점,
  최대 60 %, 동점 판정 `ΔR² < 5e-4`, SS 이동 회귀 창 5 점, 진단 기울기 산출 5 점
- output 진단 기본 임계값: 1 % / R² 0.99 / 0.1 / 1 %
- 커브 종류 판정 3단 폴백 규칙, dual sweep 분리 규칙
- 자동 그룹핑 규칙과 제거되는 접미 토큰 목록
- §3.8 의 **가정과 한계** 전문
- 파일 형식 요구사항, 지원 확장자, 실패 시 대처

---

## 9. 모듈 구조

```
app.py                    얇은 진입점 — 부팅과 위임만. 로직 없음.
fet_app/
  constants.py            팔레트 · 기본값 · 물리 상수 · 진단 임계값. 동작 없음.
  parsing.py              다단 폴백 로더 + Settings 파싱 + 커브 종류 판정
  curves.py               TransferCurve / OutputCurve 모델, dual sweep 분리
  fitting.py              선형 fit, 자동 윈도우 탐색
  metrics.py              V_th, μ_sat, SS, on/off, ΔV_th, output 진단
  grouping.py             파일 → DeviceGroup
  figure_transfer.py      이중축 그래프
  figure_output.py        그라데이션 그래프
  figure_common.py        geom/축/폰트/인셋 공통 규약, 배율 k 적용
  export.py               xlsx / csv / png / jpg / svg / pdf / zip
  presets.py              서식 프리셋 추출·적용
  state.py                세션 상태 부팅
  theme.py                photodetector-app 에서 이식 (liquid glass CSS)
  manual.py               MANUAL.md 로드 후 렌더
  ui/
    layout.py             3열 배치 + 반응형 CSS 주입
    panel_device.py       W / L / ε / d
    panel_fit.py          fit 구간 자동·수동
    panel_style.py        색 · 두께 · 축 · 폰트 · geom
    device_list.py        우측 소자 리스트 + 검색
    summary.py            지표 · 진단 패널 + 전체 요약 테이블
    export_ui.py          내보내기 UI
tests/
docs/superpowers/specs/
Example/                  예제 9세트 (테스트 픽스처 겸용)
MANUAL.md
requirements.txt
.streamlit/config.toml
```

파일이 커지면 책임이 섞였다는 신호다. 각 모듈은 **무엇을 하는지 · 어떻게 쓰는지 ·
무엇에 의존하는지** 세 줄로 답할 수 있어야 한다.

---

## 10. 테스트

`Example/` 9세트를 회귀 픽스처로 사용한다.

**파싱**
- 18개 파일 전부 커브 종류 판정 성공, 오분류 0건
- transfer 9개: V_DS = −60 V 추출, dual sweep 81 + 81 분리
- output 9개: 블록 4개, V_G = {0, −20, −40, −60}, 각 61 + 61 분리
- xlrd 경고가 stdout 으로 새지 않을 것

**지표 (합성 데이터로 정확성 검증)**
- 완벽한 제곱법칙 곡선 `I_D = (W/2L)·μ·C_ox·(V_G−V_th)²` 을 생성해
  넣은 μ, V_th 를 오차 1 % 이내로 복원하는지 확인
- 노이즈를 섞어도 fit 자동 탐색이 정상 구간을 잡는지
- SS · I_on/I_off 는 손계산 값과 대조
- ΔV_th: forward 를 평행이동한 reverse 를 합성해 이동량을 정확히 복원하는지

**Output 진단**
- 원점 오프셋을 인위적으로 넣은 데이터에서 경고가 뜨는지
- 이상적 직선 / S자 곡선에서 선형성 R² 판정이 갈리는지

**내보내기**
- PNG 알파 채널이 실제로 투명한지 (픽셀 검사)
- JPG 배경이 흰색인지
- ZIP 내부 경로 구조

---

## 11. 배포

- 저장소: **https://github.com/jun0land/FET-studio.git** (origin)
- Streamlit Community Cloud.
- `requirements.txt`: streamlit, pandas, numpy, plotly, kaleido, xlrd, openpyxl, lxml, XlsxWriter
- `.streamlit/config.toml`: photodetector-app 설정 이식.
- 폰트(Myriad Pro, Pretendard)는 `static/fonts/` 에 동봉해 서버 폰트에 의존하지 않는다.

### 알려진 리스크

- `st.components.v1.html` 이 "removed after 2026-06-01" 경고 상태다. 뷰포트 폭 프로브가
  여기 의존하므로 **반드시 수동 배율 폴백을 갖추고**, 프로브 실패가 앱 전체를 죽이지 않게 한다.
- `kaleido` 는 Streamlit Cloud 에서 Chromium 을 필요로 한다. 실패 시 사용자에게
  "이미지 내보내기 불가, HTML 다운로드로 대체" 경로를 제공한다.

---

## 12. 범위 밖 (지금 구현하지 말 것)

- 여러 소자를 한 그래프에 겹쳐 그리는 비교 오버레이
- 선형영역 이동도(μ_lin), 계면 트랩 밀도(D_it), 접촉저항 추출(TLM)
- n-type / ambipolar 소자 전용 처리 — 극성 자동 판별만 하고, 예제와 다른 극성이
  들어오면 경고만 띄운다
- 상세 그래프 양식(전체 비율 · 색상 · inset 구성)의 추가 커스터마이즈 — 사용자가
  추후 업데이트 예정

---

## 13. 구현 완료 후 사용자 최종 확인 리스트

구현이 끝나면 아래 항목을 **실제 계산 결과·실제 그래프와 함께** 제시해 확인받는다.
지금 확정한 것들은 전부 문헌 관례에 따른 기본값이므로, 연구실 기준과 다르면 이 시점에 교정한다.

**A. 수식 · 지표 정의** (`MANUAL.md` §수식 과 대조)
1. μ_sat = (2L / W·C_ox)·m² 와 V_th = −b/m — 예제 소자에서 나온 실제 수치가 타당한 범위인지
2. C_ox 계산과 유전체 프리셋 ε_r 값 (SiO₂ 3.9 / Al₂O₃ 9.0 / HfO₂ 25 / PMMA 3.6)
3. I_on/I_off 정의를 "스윕 전 구간 max/min" 으로 잡은 것
4. SS 정의와 5 점 이동 회귀 창 크기, 서브스레숄드 탐색 범위
5. ΔV_th 부호 규약 (reverse − forward)
6. fit 자동 탐색 상수: 100×I_off, 최소 10 점, 최대 60 %, 동점 ΔR² < 5e-4
   → 예제 9개에서 자동 선택된 구간이 사람이 고를 구간과 일치하는지 그래프로 확인
7. 포화 조건 `|V_DS| ≥ |V_G − V_th|` 경고가 예제에서 뜨는지/안 뜨는지

**B. 그래프 양식** (사용자가 추후 업데이트하겠다고 한 부분)
8. 전체 비율 — background 10×8 inch, graph 17.9/11.58/68.2/71.77 % 를 FET 용으로 바꿀지
9. Transfer 이중축 배치 — 좌 log|I_D| / 우 √|I_D| 의 축 범위·tick 간격 기본값
10. Output 그라데이션 베이스 색 (기본 ACCENT `#ed542b`) 과 명도 단계
11. forward 실선 / reverse 파선 구분 방식
12. 인셋 구성 — 레전드 위치, 샘플명 인셋 내용, fit 결과를 인셋에 넣을지
13. 축 제목 문구: `V_G (V)` / `|I_D| (A)` / `√|I_D| (A^0.5)` / `V_D (V)` / `I_D (A)`
14. 폰트 기본 30 pt 가 FET 그래프 크기에 맞는지

**C. 동작**
15. 예제 9세트 자동 그룹핑 결과 (`1-3 best` + `1-3 out` → `1-3`)
16. output 진단 4종이 예제에서 실제로 어떤 판정을 내리는지 (특히 V_G = −60 V 블록의 게이트 누설)
17. 내보내기 PNG 투명 / JPG 흰 배경 실물 확인
18. 노트북·데스크톱 각각에서 레이아웃 확인
