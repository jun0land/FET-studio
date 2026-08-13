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
# None 을 돌려주고, '자동' 모드는 사실상 항상 이 값을 쓴다. 좌측 패널(최대
# 480px)+우측 패널(최대 230px)이 넓어진 뒤로 0.60 은 1280~1440px 폭의
# 노트북 화면에서 그래프 두 개가 옆으로 넘쳐 우측 소자 리스트를 화면 밖으로
# 밀어냈다. 그 폭 대에서 넘치지 않는 값으로 낮춘다. 화면이 넓은 사용자는
# [내보내기] 탭의 '미리보기 배율 자동' 체크를 풀고 수동으로 키우면 된다.
FALLBACK_SCALE = 0.32
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
