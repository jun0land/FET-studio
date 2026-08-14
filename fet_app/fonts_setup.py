"""번들 폰트를 OS 폰트 시스템(fontconfig)에 등록한다 — 내보내기 렌더용.

왜 필요한가: 화면과 내보내기는 서로 다른 경로로 폰트를 찾는다.

* 화면 — 사용자의 브라우저가 그린다. ``theme.py`` 의 ``@font-face`` 가
  ``app/static/fonts/`` 에서 Myriad Pro 를 직접 받아가므로 OS 설치 여부와 무관하다.
* 내보내기(PNG/JPG/PDF) — kaleido 1.x 가 그린다. 이 버전은 자체 번들 Chromium 이
  아니라 **시스템 Chromium 을 CDP 로 띄워** 렌더링하는 진짜 브라우저이고, 그
  브라우저에는 앱의 ``@font-face`` CSS 가 닿지 않는다. 따라서 ``font.family``
  ("Myriad Pro") 는 **OS 의 폰트 시스템**에서 조회된다 — Linux 라면 fontconfig.
  등록돼 있지 않으면 조용히 대체 폰트로 폴백해서 화면과 다른 결과가 나온다.

그래서 앱 부팅 시 ``static/fonts/`` 의 같은 파일들을 fontconfig 가 기본으로 훑는
사용자 폰트 경로(``$XDG_DATA_HOME/fonts`` 또는 ``~/.local/share/fonts``)로 복사하고
``fc-cache`` 로 인덱싱해 두 경로의 폰트를 일치시킨다.

멱등성: Streamlit 은 rerun 마다 스크립트를 다시 실행하므로 ``ensure_installed()``
는 여러 번 불려도 싸야 한다. 프로세스 안에서는 모듈 전역 결과 캐시로 즉시 반환하고
(모듈은 sys.modules 에 남으므로 rerun 이 재import 하지 않는다), 프로세스가 새로 떠도
대상 디렉터리의 스탬프 파일이 원본 목록과 같으면 복사·fc-cache 를 모두 건너뛴다.

실패는 절대 앱을 죽이지 않는다. Linux 가 아니거나(로컬 Windows 개발) fc-cache 가
없으면 상태 문자열만 돌려주고 조용히 넘어간다 — 내보내기는 대체 폰트로라도 된다.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import threading
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _ROOT / "static" / "fonts"

# fontconfig(FreeType)가 확실히 읽는 형식만 넘긴다. woff2 는 빌드에 따라 인덱싱되지
# 않을 수 있어 제외한다 — 화면용(@font-face)으로는 그대로 쓰이므로 손해가 없다.
_PATTERNS = ("*.otf", "*.ttf", "*.ttc")

_SUBDIR = "fet-studio"          # 사용자 폰트 경로 안에서 이 앱 몫만 격리
_STAMP_NAME = ".fet-studio-manifest"
_FC_CACHE_TIMEOUT = 120

_lock = threading.Lock()
_result: str | None = None


def font_root() -> Path:
    """fontconfig 가 기본 설정으로 훑는 사용자 폰트 경로.

    기본 ``fonts.conf`` 에는 ``<dir prefix="xdg">fonts</dir>`` 항목이 있어
    ``$XDG_DATA_HOME/fonts`` (미설정 시 ``~/.local/share/fonts``) 를 재귀로 훑는다.
    """
    xdg = os.environ.get("XDG_DATA_HOME") or ""
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "fonts"


def sources() -> list[Path]:
    """설치 대상 번들 폰트 파일 목록 (이름순)."""
    if not _SRC_DIR.is_dir():
        return []
    found: list[Path] = []
    for pattern in _PATTERNS:
        found.extend(p for p in _SRC_DIR.glob(pattern) if p.is_file())
    return sorted(found, key=lambda p: p.name)


def _manifest(paths: list[Path]) -> str:
    """스탬프 내용 — 파일명과 크기. mtime 은 체크아웃마다 달라져서 쓰지 않는다."""
    return "\n".join(f"{p.name}:{p.stat().st_size}" for p in paths)


def _run_fc_cache(target_root: Path) -> str:
    """새로 복사한 폰트를 fontconfig 인덱스에 반영한다."""
    cmd = ["fc-cache", "-f", str(target_root)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=_FC_CACHE_TIMEOUT, check=False)
    except FileNotFoundError:
        # fontconfig 패키지가 없는 환경. 복사는 끝났으니 fontconfig 가 런타임에
        # 디렉터리를 직접 훑어 찾을 수도 있다 — 실패로 보지 않고 넘어간다.
        return "copied-no-fc-cache"
    except (OSError, subprocess.SubprocessError) as e:  # noqa: BLE001
        return f"copied-fc-cache-error:{type(e).__name__}"
    if proc.returncode != 0:
        return f"copied-fc-cache-rc{proc.returncode}"
    return "installed"


def _install() -> str:
    if platform.system() != "Linux":
        # fontconfig 는 Linux 관례다. Windows/macOS 는 OS 폰트 설치가 별개 절차라
        # 개발 환경에서는 조용히 넘어간다 (내보내기는 OS 에 설치된 폰트를 쓴다).
        return "skipped-not-linux"

    files = sources()
    if not files:
        return "skipped-no-fonts"

    target = font_root() / _SUBDIR
    stamp = target / _STAMP_NAME
    manifest = _manifest(files)

    try:
        if stamp.is_file() and stamp.read_text(encoding="utf-8") == manifest:
            return "cached"

        target.mkdir(parents=True, exist_ok=True)
        for src in files:
            dst = target / src.name
            if dst.is_file() and dst.stat().st_size == src.stat().st_size:
                continue
            shutil.copyfile(src, dst)

        status = _run_fc_cache(font_root())
        if status == "installed":
            # fc-cache 까지 성공했을 때만 스탬프를 남긴다. 그래야 fontconfig 가
            # 나중에 설치된 환경에서 다음 부팅이 fc-cache 를 다시 시도한다.
            stamp.write_text(manifest, encoding="utf-8")
        return status
    except Exception as e:  # noqa: BLE001 — 폰트 설치 실패로 앱이 죽으면 안 된다.
        return f"failed:{type(e).__name__}:{e}"


def ensure_installed(force: bool = False) -> str:
    """번들 폰트를 OS 에 등록한다. 예외를 던지지 않고 상태 문자열을 돌려준다.

    상태: ``installed`` / ``cached`` / ``copied-*`` (복사는 됐으나 fc-cache 이슈) /
    ``skipped-*`` / ``failed:*``.

    ``force=True`` 는 프로세스 내 결과 캐시를 무시하고 다시 시도한다 (테스트용).
    """
    global _result
    with _lock:
        if _result is None or force:
            _result = _install()
        return _result
