# FET Studio

Keithley 측정 파일에서 FET transfer/output curve 를 자동 인식해 논문용 그래프를 그리고
성능 지표를 계산·내보내는 Streamlit 앱.

- 파일 이름 규칙 없음. `Settings` 의 Forcing Function 과 `Data` 열 구조로 커브 종류를 판정한다.
- 여러 파일을 한 번에 올리면 파일명 stem 으로 소자를 자동 그룹핑한다.
- 계산하는 지표: V_th, μ_sat, I_on/I_off, SS, ΔV_th, output 진단 4종.
- **모든 수식·상수·임계값은 [MANUAL.md](MANUAL.md) 에 있다.**
- 사용법은 [METHODS.md](METHODS.md) 를 참고한다.

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
