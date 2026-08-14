"""번들 폰트의 OS 등록 (fet_app/fonts_setup.py).

실제 fontconfig 는 Linux 에만 있으므로, 여기서는 platform 과 fc-cache 호출을
가로채 복사·스탬프·멱등성 로직을 검증한다. 어떤 경우에도 예외가 밖으로 새면
안 된다 — 폰트 설치 실패로 앱이 죽으면 안 되기 때문이다.
"""

import subprocess

import pytest

from fet_app import fonts_setup

MYRIAD = {
    "MyriadPro-Black.otf", "MyriadPro-BlackIt.otf", "MyriadPro-Bold.otf",
    "MyriadPro-BoldIt.otf", "MyriadPro-It.otf", "MyriadPro-Light.otf",
    "MyriadPro-LightIt.otf", "MyriadPro-Regular.otf", "MyriadPro-Semibold.otf",
    "MyriadPro-SemiboldIt.otf",
}


@pytest.fixture(autouse=True)
def _reset_result():
    """프로세스 전역 결과 캐시가 테스트 사이에 새지 않게 한다."""
    fonts_setup._result = None
    yield
    fonts_setup._result = None


@pytest.fixture
def fake_linux(monkeypatch, tmp_path):
    """Linux + 임시 XDG 홈 + fc-cache 스텁. 반환값은 호출 기록 리스트."""
    monkeypatch.setattr(fonts_setup.platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(fonts_setup.subprocess, "run", fake_run)
    return calls


def test_bundled_myriad_faces_are_installable():
    """theme.py 의 @font-face 가 쓰는 10종이 설치 대상에 그대로 들어와야 한다."""
    names = {p.name for p in fonts_setup.sources()}
    assert MYRIAD <= names, MYRIAD - names


def test_font_root_follows_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert fonts_setup.font_root() == tmp_path / "fonts"
    monkeypatch.delenv("XDG_DATA_HOME")
    assert fonts_setup.font_root().parts[-3:] == (".local", "share", "fonts")


def test_non_linux_is_silent_noop(monkeypatch, tmp_path):
    """로컬 Windows/macOS 개발 환경에서는 아무것도 하지 않고 조용히 넘어간다."""
    monkeypatch.setattr(fonts_setup.platform, "system", lambda: "Windows")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert fonts_setup.ensure_installed(force=True) == "skipped-not-linux"
    assert not (tmp_path / "fonts").exists()


def test_installs_fonts_and_refreshes_cache(fake_linux, tmp_path):
    assert fonts_setup.ensure_installed(force=True) == "installed"
    target = tmp_path / "share" / "fonts" / "fet-studio"
    assert MYRIAD <= {p.name for p in target.iterdir()}
    assert (target / fonts_setup._STAMP_NAME).is_file()
    assert fake_linux == [["fc-cache", "-f", str(tmp_path / "share" / "fonts")]]


def test_second_boot_skips_copy_and_fc_cache(fake_linux, tmp_path):
    """스탬프가 맞으면 프로세스가 새로 떠도 복사·fc-cache 를 건너뛴다."""
    assert fonts_setup.ensure_installed(force=True) == "installed"
    fake_linux.clear()
    assert fonts_setup.ensure_installed(force=True) == "cached"
    assert fake_linux == []


def test_rerun_uses_process_cache(fake_linux, monkeypatch):
    """Streamlit rerun 마다 다시 검사하지 않는다 (force 없이 호출)."""
    calls = []
    monkeypatch.setattr(fonts_setup, "_install", lambda: calls.append(1) or "installed")
    assert fonts_setup.ensure_installed() == "installed"
    assert fonts_setup.ensure_installed() == "installed"
    assert len(calls) == 1


def test_missing_fc_cache_is_not_fatal(monkeypatch, tmp_path):
    """fontconfig 가 없는 이미지에서도 죽지 않고, 스탬프를 남기지 않아 다음 부팅이 재시도한다."""
    monkeypatch.setattr(fonts_setup.platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))

    def boom(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(fonts_setup.subprocess, "run", boom)
    assert fonts_setup.ensure_installed(force=True) == "copied-no-fc-cache"
    target = tmp_path / "share" / "fonts" / "fet-studio"
    assert MYRIAD <= {p.name for p in target.iterdir()}   # 복사는 됐다
    assert not (target / fonts_setup._STAMP_NAME).exists()


def test_fc_cache_failure_is_reported_not_raised(monkeypatch, tmp_path):
    monkeypatch.setattr(fonts_setup.platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setattr(fonts_setup.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "nope"))
    assert fonts_setup.ensure_installed(force=True) == "copied-fc-cache-rc1"


def test_copy_error_is_swallowed(monkeypatch, tmp_path):
    """권한 문제 등으로 복사가 실패해도 앱 부팅을 막지 않는다."""
    monkeypatch.setattr(fonts_setup.platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setattr(fonts_setup.shutil, "copyfile",
                        lambda *a, **k: (_ for _ in ()).throw(PermissionError("denied")))
    assert fonts_setup.ensure_installed(force=True).startswith("failed:PermissionError")


def test_no_sources_is_skipped(monkeypatch, tmp_path):
    monkeypatch.setattr(fonts_setup.platform, "system", lambda: "Linux")
    monkeypatch.setattr(fonts_setup, "sources", lambda: [])
    assert fonts_setup.ensure_installed(force=True) == "skipped-no-fonts"
