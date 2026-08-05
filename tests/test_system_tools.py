from __future__ import annotations

from tools import system_tools as st


class _Mem:
    percent = 42.4
    used = 8.2 * (1024**3)
    total = 16.0 * (1024**3)


def test_get_system_status(monkeypatch):
    class FakePsutil:
        @staticmethod
        def virtual_memory():
            return _Mem()

        @staticmethod
        def cpu_percent(interval=0.2):
            return 11.6

    monkeypatch.setitem(__import__("sys").modules, "psutil", FakePsutil)
    # Force re-import path: get_system_status imports psutil inside
    out = st.get_system_status()
    assert out["ok"] is True
    assert out["ram_percent"] == 42
    assert out["ram_used_gb"] == 8.2
    assert out["ram_total_gb"] == 16.0
    assert out["cpu_percent"] == 12
    assert "RAM is at 42 percent" in out["message"]
    assert "CPU is at 12 percent" in out["message"]


def test_set_volume_clamps(monkeypatch):
    monkeypatch.setattr(st.sys, "platform", "win32")

    class FakeEp:
        def __init__(self):
            self.scalar = None
            self.mute = None

        def SetMasterVolumeLevelScalar(self, v, _):
            self.scalar = v

        def SetMute(self, m, _):
            self.mute = m

    ep = FakeEp()
    monkeypatch.setattr(st, "_audio_endpoint", lambda: ep)
    out = st.set_volume(150)
    assert out["ok"] is True
    assert out["level"] == 100
    assert ep.scalar == 1.0
    assert ep.mute == 0


def test_set_mute(monkeypatch):
    monkeypatch.setattr(st.sys, "platform", "win32")

    class FakeEp:
        def SetMute(self, m, _):
            self.flag = m

    ep = FakeEp()
    monkeypatch.setattr(st, "_audio_endpoint", lambda: ep)
    out = st.set_mute(True)
    assert out["message"] == "Muted."
    assert ep.flag == 1


def test_lock_pc(monkeypatch):
    monkeypatch.setattr(st.sys, "platform", "win32")
    called = []
    monkeypatch.setattr(st, "_lock_workstation", lambda: called.append(True))
    out = st.lock_pc()
    assert out["ok"] is True
    assert called == [True]


def test_take_screenshot_success(monkeypatch, tmp_path):
    import re

    monkeypatch.setattr(st.sys, "platform", "win32")
    monkeypatch.setattr(st.Path, "home", classmethod(lambda cls: tmp_path))
    desk = tmp_path / "Desktop"
    desk.mkdir()

    def fake_run(cmd, **kwargs):
        script = " ".join(str(c) for c in cmd)
        m = re.search(r"\$bmp\.Save\('([^']+)'\)", script)
        assert m, script
        st.Path(m.group(1)).write_bytes(b"png")
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    monkeypatch.setattr(st.subprocess, "run", fake_run)
    out = st.take_screenshot()
    assert out["ok"] is True
    assert "Screenshot saved" in out["message"]
