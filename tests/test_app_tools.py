from __future__ import annotations

from tools.app_tools import list_allowlisted_apps, normalize_app_name, open_app, resolve_app_path


def test_normalize_aliases():
    assert normalize_app_name("Google Chrome") == "chrome"
    assert normalize_app_name("calc") == "calculator"
    assert normalize_app_name("file explorer") == "explorer"
    assert normalize_app_name("malware.exe") is None


def test_allowlist_nonempty():
    apps = list_allowlisted_apps()
    assert "notepad" in apps
    assert "chrome" in apps


def test_open_app_unknown():
    out = open_app("totally-fake-app-xyz")
    assert out["ok"] is False
    assert "only open" in out["message"].lower()


def test_open_app_launches_when_resolved(monkeypatch):
    import tools.app_tools as at

    monkeypatch.setattr(at, "normalize_app_name", lambda name: "notepad")
    monkeypatch.setattr(at, "resolve_app_path", lambda canonical: r"C:\Windows\System32\notepad.exe")
    launched = []

    def fake_startfile(path):
        launched.append(path)

    monkeypatch.setattr(at.os, "startfile", fake_startfile, raising=False)
    monkeypatch.setattr(at.sys, "platform", "win32")
    out = open_app("notepad")
    assert out["ok"] is True
    assert "Opening Notepad" in out["message"]
    assert launched == [r"C:\Windows\System32\notepad.exe"]


def test_resolve_notepad_usually_exists():
    # PATH resolution on Windows CI/dev machines
    path = resolve_app_path("notepad")
    if path is not None:
        assert path.lower().endswith("notepad.exe") or "notepad" in path.lower()
