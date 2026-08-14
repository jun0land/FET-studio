"""표시 배율 산출 (스펙 §5.4).

뷰포트 폭 프로브가 실패해도 앱이 죽으면 안 된다. 반드시 수동 배율로 폴백한다.
설치된 Streamlit 1.61.1 에서는 ``st.context`` 에 ``viewport`` 속성 자체가
없다(``dir(st.context)`` 로 확인 — cookies/headers/ip_address/is_embedded/
locale/theme/timezone/timezone_offset/url 뿐, viewport 없음). 즉
``probe_viewport_width()`` 는 이 버전에서는 항상 None 을 돌려주고, '자동'
모드는 실전에서 사실상 항상 FALLBACK_SCALE 을 쓴다 — 이건 예외적인 폴백이
아니라 지금은 사실상 기본 동작값이다.
"""

from __future__ import annotations

# st.context 에는 viewport 속성이 없다(설치된 Streamlit 버전에서 확인—
# dir(st.context) 에 없음). 그래서 probe_viewport_width() 는 실전에서 항상
# None 을 돌려주고, '자동' 모드는 사실상 항상 이 값을 쓴다.
#
# 예전엔 노트북 화면에서 그래프 두 개가 넘치는 것을 막으려고 이 값을
# 방어적으로 작게 잡았었다. 지금은 theme.apply_ui_zoom() 이 1440px
# 기준 폭보다 좁은 실제 화면에서 패널·그래프·표를 통째로 비례 축소하므로,
# 좁은 화면 오버플로 방지는 그쪽 몫이다 — FALLBACK_SCALE 자체를 좁은 화면
# 대비용으로 낮게 잡을 필요가 없다.
#
# 그 대신 이 값은 apply_ui_zoom() 의 기준 폭인 1440px 에서, 그래프의
# 렌더링 폭이 바로 아래 st.table 진단표(자기 컬럼 폭을 꽉 채우는)와
# 시각적으로 맞도록 튜닝한다. 1440px 기준 좌측 패널(clamp 상한 480px ->
# 실측 0.30*1440=432px)/우측 패널(0.13*1440≈187px)/본문 패딩
# (1.6rem*2≈51px)/3열 gap(2개≈48px)/그래프 2열 내부 gap(1개≈24px) 을
# 빼고 그래프 하나에 남는 폭을 어림하면 (1440-432-187-51-48-24)/2 ≈ 349px
# -> k ≈ 349/960(GRAPH_DESIGN_PX) ≈ 0.364.
#
# 이 수치는 DOM 실측이 아니라 위 여백/패딩 값들에 대한 추정치다(이 Streamlit
# 빌드엔 st.context.viewport 가 없어 실측 프로브가 항상 실패한다).
#
# 0.60 -> 0.32(오버플로 방지, 너무 작아짐) -> 0.35(어림값 0.364 보다 보수적으로
# 낮춤, 그런데 변화가 너무 작아 체감이 안 됨) 를 거쳐, 이제 어림값에 거의
# 그대로 맞춘 0.38 로 둔다. 1440px 정확히 그 폭에서는 그래프 2개+gap 이
# 예산(~722px)을 근소하게 넘길 수 있지만(약 30px), 그보다 좁은 화면은 전부
# apply_ui_zoom() 이 비례 축소로 흡수하고, 정확히 1440px 인 경우는 아주 좁은
# 경우의 수라 이 정도 여유는 감수한다 — 표 폭과 맞춰 보이는 쪽이 우선이다.
FALLBACK_SCALE = 0.38
GRAPH_DESIGN_PX = 960  # 10 inch x 96 dpi


def scale_for_width(container_px: float) -> float:
    """그래프 하나에 배정된 픽셀 폭 -> 배율. 0.25~1.0 로 자른다."""
    if not container_px or container_px <= 0:
        return FALLBACK_SCALE
    return max(0.25, min(1.0, float(container_px) / GRAPH_DESIGN_PX))


def probe_viewport_width() -> float | None:
    """1회성 뷰포트 폭 측정. 실패하면 None (앱은 계속 동작한다).

    Streamlit 버전에 따라 ``st.context.viewport`` 가 없거나 브라우저 컨텍스트가
    없을 수 있다 — 어떤 예외도 밖으로 내보내지 않고 None 을 돌려준다.
    """
    try:
        import streamlit as st

        # st.context.viewport 가 있으면 그것을 우선 쓴다 (컴포넌트 불필요).
        ctx = getattr(st, "context", None)
        width = getattr(getattr(ctx, "viewport", None), "width", None)
        return float(width) if width else None
    except Exception:  # noqa: BLE001
        return None


def preview_scale(app) -> float:
    """AppState.preview_scale 이 None 이면 자동, 아니면 수동값을 그대로 쓴다."""
    if app.preview_scale is not None:
        return float(app.preview_scale)
    width = probe_viewport_width()
    if width is None:
        return FALLBACK_SCALE
    # 3열에서 그래프 두 개가 나눠 갖는 폭 추정: 본문 - 좌우 패널 - 여백.
    # 좌측 패널은 이제 최대 480px (theme.RESPONSIVE_CSS 의 clamp 상한).
    usable = min(float(width), 1760.0) - 480 - 230 - 80
    return scale_for_width(max(200.0, usable / 2.0))
