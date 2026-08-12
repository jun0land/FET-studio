"""소자 기하·유전체 파라미터와 C_ox 계산 (스펙 §3.1)."""

from __future__ import annotations

from dataclasses import dataclass

from fet_app.constants import EPSILON_0


def c_ox_from(eps_r: float, d_nm: float) -> float:
    """C_ox = eps_0 * eps_r / d.  d 는 nm 입력, 내부에서 cm 로 환산(x1e-7).

    반환 단위: F/cm^2
    """
    if d_nm is None or float(d_nm) <= 0:
        raise ValueError("유전체 두께는 0보다 커야 합니다.")
    if eps_r is None or float(eps_r) <= 0:
        raise ValueError("유전상수는 0보다 커야 합니다.")
    d_cm = float(d_nm) * 1e-7
    return EPSILON_0 * float(eps_r) / d_cm


@dataclass
class DeviceParams:
    """채널 폭/길이는 UI 입력이 um, 유전체 두께는 nm. 내부 계산은 전부 cm."""

    w_um: float | None = None
    l_um: float | None = None
    eps_r: float | None = None
    d_nm: float | None = None

    def w_cm(self) -> float:
        return float(self.w_um) * 1e-4

    def l_cm(self) -> float:
        return float(self.l_um) * 1e-4

    def c_ox(self) -> float:
        return c_ox_from(self.eps_r, self.d_nm)

    def is_complete(self) -> bool:
        vals = (self.w_um, self.l_um, self.eps_r, self.d_nm)
        return all(v is not None and float(v) > 0 for v in vals)

    def merged_with(self, fallback: "DeviceParams") -> "DeviceParams":
        """비어 있는 항목만 전역 기본값에서 상속받는다."""
        return DeviceParams(
            w_um=self.w_um if self.w_um is not None else fallback.w_um,
            l_um=self.l_um if self.l_um is not None else fallback.l_um,
            eps_r=self.eps_r if self.eps_r is not None else fallback.eps_r,
            d_nm=self.d_nm if self.d_nm is not None else fallback.d_nm,
        )
