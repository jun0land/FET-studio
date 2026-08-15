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


_RENDER_FAIL_MSG = (
    "이미지 렌더에 실패했습니다 (kaleido/Chromium). "
    "HTML 다운로드로 대체하거나 로컬에서 다시 시도하세요."
)


def _prepared_figure(fig, fmt: str):
    """(배경까지 적용한 figure 사본, kaleido 형식 이름). 원본은 건드리지 않는다."""
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
    return export_fig, kfmt


def figure_bytes(fig, fmt: str, scale: int = 1) -> bytes:
    """PNG 는 투명, JPG/PDF 는 흰 배경. 원본 figure 는 건드리지 않는다."""
    export_fig, kfmt = _prepared_figure(fig, fmt)
    try:
        return export_fig.to_image(format=kfmt, scale=scale)
    except Exception as e:  # noqa: BLE001
        raise KaleidoUnavailable(_RENDER_FAIL_MSG) from e


def _single_or_none(fig, fmt: str, scale: int) -> bytes | None:
    """배치 안에서 개별 렌더로 되돌아갈 때 쓰는 래퍼. 형식 오류는 그대로 던진다."""
    _prepared_figure(fig, fmt)   # ValueError 는 배치에서도 즉시 드러나야 한다
    try:
        return figure_bytes(fig, fmt, scale)
    except KaleidoUnavailable:
        return None


def _kaleido_opts(fig_dict: dict, kfmt: str, scale: int) -> dict:
    """plotly.io._kaleido.to_image 과 똑같은 opts 를 만든다.

    width/height 를 layout -> template.layout -> plotly 기본값 순으로 찾는 것까지
    맞춰야 개별 다운로드(figure_bytes)와 배치가 같은 그림을 낸다.
    """
    from plotly.io._kaleido import defaults

    layout = fig_dict.get("layout", {})
    tpl_layout = layout.get("template", {}).get("layout", {})
    return {
        "format": kfmt,
        "width": layout.get("width") or tpl_layout.get("width") or defaults.default_width,
        "height": layout.get("height") or tpl_layout.get("height") or defaults.default_height,
        "scale": scale or defaults.default_scale,
    }


def figure_bytes_batch(items: list[tuple[object, str]],
                       scale: int = 1) -> list[bytes | None]:
    """여러 장을 Chromium **한 번만** 띄워 연속으로 렌더한다. 실패한 항목은 None.

    figure_bytes 가 타는 plotly fig.to_image() -> kaleido.calc_fig_sync() 경로는
    호출 한 번마다 `async with Kaleido(...)` 로 Chromium 을 새로 띄우고 내린다
    (kaleido 1.x 소스 확인). 그래서 ZIP 처럼 여러 장을 만들 때 기동 비용이
    장 수만큼 그대로 붙는다. 여기서는 세션 하나를 열어 두고 재사용한다.

    실측(Example 1-1 transfer, 8장 연속, PNG 1x):
      개별 to_image  장당 약 3.3 초 / 8장 합계 26.5 초
      세션 재사용    기동 약 3.8 초 + 장당 약 0.36 초 / 8장 합계 6.7 초

    한 장짜리라면 이득이 없으므로 그대로 figure_bytes 로 넘긴다.

    opts/kopts 구성은 plotly.io._kaleido.to_image 와 일치시킨다 — 어긋나면
    plotly 가 번들한 plotly.js 대신 CDN 을 보거나 크기가 달라져서 개별
    다운로드와 다른 그림이 나온다.
    """
    if not items:
        return []
    if len(items) == 1:
        return [_single_or_none(items[0][0], items[0][1], scale)]

    import asyncio

    import kaleido
    from plotly.io._kaleido import defaults
    from plotly.io._utils import validate_coerce_fig_to_dict

    specs = []
    for fig, fmt in items:
        export_fig, kfmt = _prepared_figure(fig, fmt)
        fig_dict = validate_coerce_fig_to_dict(export_fig, False)
        specs.append((fig_dict, _kaleido_opts(fig_dict, kfmt, scale)))

    kopts: dict = {"n": 1}
    if defaults.plotlyjs:
        kopts["plotlyjs"] = defaults.plotlyjs
    if defaults.mathjax:
        kopts["mathjax"] = defaults.mathjax
    if defaults.headers:
        kopts["headers"] = defaults.headers

    out: list[bytes | None] = [None] * len(specs)

    async def _render_all() -> None:
        async with kaleido.Kaleido(**kopts) as k:
            for i, (fig_dict, opts) in enumerate(specs):
                try:
                    out[i] = await k.calc_fig(fig_dict, opts=opts,
                                              topojson=defaults.topojson)
                except Exception:  # noqa: BLE001, S110
                    out[i] = None   # 이 장만 실패. 나머지는 계속 만든다.

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        # 이미 이벤트 루프 안이면 asyncio.run 을 못 쓴다. 여기서 전부 실패로
        # 처리하면 '이미지가 하나도 안 만들어졌다'가 되어버리므로, 느리더라도
        # 개별 경로로 돌아간다.
        return [_single_or_none(fig, fmt, scale) for fig, fmt in items]

    try:
        asyncio.run(_render_all())
    except Exception:  # noqa: BLE001
        # 세션 자체를 못 띄운 경우. 장마다 figure_bytes 를 부른 것과 같은
        # 결과(전부 실패)라 호출부의 기존 실패 처리가 그대로 먹는다.
        return [None] * len(specs)
    return out


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
