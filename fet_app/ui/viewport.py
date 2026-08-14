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

# apply_ui_zoom()(theme.py) 가 이제 페이지 전체(패널·폰트·표·그래프)를 창 폭에
# 맞춰 비례 축소한다 — 좁은 화면 대응은 그쪽 몫이다. 이 상수는 그 축소가
# 적용되지 않는 폭(≥1440px, apply_ui_zoom 의 MAX=1.0 구간)에서 그래프가
# 어떤 크기로 나올지를 정한다. 예전엔 이 값 자체를 방어적으로 낮춰뒀는데
# (0.60→0.32→0.35→0.38 을 거쳤다), apply_ui_zoom 이 이미 좁은 화면을
# 처리하므로 이중으로 줄이는 셈이었고, 정작 넓은 화면에서도 그래프가 불필요
# 하게 작았다. 사용자가 명시적으로 "100% 가 원하는 크기"라고 확인했으므로
# 참 크기(1.0, 실측 10x8 inch)를 기본값으로 둔다.
FALLBACK_SCALE = 1.0
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
