"""좌측 패널 — fit 구간. 자동 탐색 결과를 보여주고 수동으로 덮어쓸 수 있다."""

from __future__ import annotations

import streamlit as st


def fit_range_for(app, name: str):
    """수동 지정이 켜져 있으면 (lo, hi), 아니면 None (= 자동 탐색)."""
    return st.session_state.get(f"fitrange_{name}")


def render_device(g, *, compact: bool = False) -> None:
    """소자 하나의 fit 구간 위젯. 위젯 key 가 소자 이름에서 나오므로 한 화면에
    여러 소자를 나란히 놓아도(멀티 커브 편집) 서로 섞이지 않고, 정보 탭과
    같은 세션 값을 공유하므로 어느 쪽에서 바꿔도 같은 fit 이다.

    ``compact`` 면 안내 문구를 생략한다 — 카드 여러 장이 쌓이는 화면에서 같은
    문장이 소자 수만큼 반복되는 것을 막는다.
    """
    if g is None or g.transfer is None or g.transfer.forward.empty:
        return
    name = g.name
    # 진실 값은 위젯 키가 아닌 fitrange_{name} 하나다. Streamlit 은 한 rerun 에
    # 그려지지 않은 위젯의 세션 키를 지우므로, 토글/숫자 위젯 키를 진실 값으로
    # 쓰면 다른 소자를 보거나 다른 창(요약·Transfer 비교)에 다녀오는 순간 수동
    # 구간이 사라진다. 그래서 위젯은 매번 저장된 값에서 다시 시작한다.
    saved = st.session_state.get(f"fitrange_{name}")
    manual = st.toggle("수동 지정", value=saved is not None, key=f"fitmode_w_{name}")

    v = g.transfer.forward["V_G"]
    v_lo, v_hi = float(v.min()), float(v.max())
    if manual:
        init_lo, init_hi = saved if saved is not None else (v_lo, v_hi)
        c1, c2 = st.columns(2)
        with c1:
            lo = st.number_input("V_G 하한 (V)", value=float(init_lo), step=1.0,
                                 key=f"fl_w_{name}")
        with c2:
            hi = st.number_input("V_G 상한 (V)", value=float(init_hi), step=1.0,
                                 key=f"fh_w_{name}")
        st.session_state[f"fitrange_{name}"] = (float(lo), float(hi))
    else:
        st.session_state.pop(f"fitrange_{name}", None)
        if not compact:
            st.caption("R² 최대 구간을 자동으로 찾습니다. 동점이면 긴 구간을 택합니다.")


def render(app) -> None:
    g = app.device(app.selected)
    if g is None or g.transfer is None:
        return
    st.markdown("**Fit 구간**")
    render_device(g)
