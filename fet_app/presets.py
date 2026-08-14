"""서식 프리셋 추출/적용 (스펙 §7).

프리셋에는 **서식만** 들어간다. 소자 파라미터(W/L/ε/d)와 진단 임계값은
측정 조건·판단 기준이라 절대 포함하지 않는다.
"""

from __future__ import annotations

import copy
import json

PRESET_KEYS = ("transfer_geom", "output_geom", "style",
               "transfer_axes", "output_axes",
               "transfer_style", "output_style", "insets")


def extract(settings: dict) -> dict:
    return {k: copy.deepcopy(settings[k]) for k in PRESET_KEYS if k in settings}


def _deep_update(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = copy.deepcopy(v)
    return dst


def apply(settings: dict, preset: dict) -> dict:
    """알려진 키만 병합한 새 dict 를 반환한다. 원본은 건드리지 않는다."""
    out = copy.deepcopy(settings)
    for k in PRESET_KEYS:
        if k in preset and isinstance(preset[k], dict):
            if isinstance(out.get(k), dict):
                _deep_update(out[k], preset[k])
            else:
                out[k] = copy.deepcopy(preset[k])
    return out


def to_json(preset: dict) -> str:
    return json.dumps(preset, ensure_ascii=False, indent=2)


def from_json(text: str) -> dict:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("프리셋 파일은 JSON 객체여야 합니다.")
    return {k: v for k, v in data.items() if k in PRESET_KEYS}
