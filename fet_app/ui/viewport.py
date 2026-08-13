"""표시 배율 산출 (스펙 §5.4).

뷰포트 폭 프로브가 실패해도 앱이 죽으면 안 된다. 반드시 수동 배율로 폴백한다.
"""

from __future__ import annotations

FALLBACK_SCALE = 0.60
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
