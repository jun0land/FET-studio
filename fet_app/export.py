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


def figure_bytes(fig, fmt: str, scale: int = 1) -> bytes:
    """PNG 는 투명, JPG/PDF 는 흰 배경. 원본 figure 는 건드리지 않는다."""
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

    try:
        return export_fig.to_image(format=kfmt, scale=scale)
    except Exception as e:  # noqa: BLE001
        raise KaleidoUnavailable(
            "이미지 렌더에 실패했습니다 (kaleido/Chromium). "
            "HTML 다운로드로 대체하거나 로컬에서 다시 시도하세요."
        ) from e


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
