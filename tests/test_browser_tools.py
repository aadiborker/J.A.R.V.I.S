from __future__ import annotations

from urllib.parse import unquote_plus

import tools.browser_tools as bt


def test_normalize_https_and_bare_domain():
    assert bt.normalize_and_validate_url("https://example.com/path") == "https://example.com/path"
    assert bt.normalize_and_validate_url("google.com") == "https://google.com"


def test_normalize_rejects_bad_schemes():
    assert bt.normalize_and_validate_url("file:///C:/Windows") is None
    assert bt.normalize_and_validate_url("javascript:alert(1)") is None
    assert bt.normalize_and_validate_url("") is None
    assert bt.normalize_and_validate_url("not a url") is None


def test_open_url_success(monkeypatch):
    monkeypatch.setattr(bt.webbrowser, "open", lambda url: True)
    out = bt.open_url("https://example.com")
    assert out["ok"] is True
    assert out["url"] == "https://example.com"
    assert "Opening" in out["message"]


def test_open_url_rejects_file(monkeypatch):
    called = []
    monkeypatch.setattr(bt.webbrowser, "open", lambda url: called.append(url) or True)
    out = bt.open_url("file:///tmp/x")
    assert out["ok"] is False
    assert called == []
    assert out["message"] == bt.BROWSER_REJECT_REPLY


def test_open_youtube(monkeypatch):
    monkeypatch.setattr(bt.webbrowser, "open", lambda url: True)
    out = bt.open_youtube()
    assert out["ok"] is True
    assert out["message"] == "Opening YouTube."
    assert "youtube.com" in out["url"]


def test_youtube_search_encodes_query(monkeypatch):
    opened = []
    monkeypatch.setattr(bt.webbrowser, "open", lambda url: opened.append(url) or True)
    out = bt.youtube_search("lo-fi beats")
    assert out["ok"] is True
    assert out["message"] == "Searching YouTube for lo-fi beats."
    assert "search_query=" in opened[0]
    assert "lo-fi" in unquote_plus(opened[0]) or "lo%2Dfi" in opened[0].lower() or "lo-fi" in opened[0]


def test_youtube_search_empty():
    out = bt.youtube_search("   ")
    assert out["ok"] is False
    assert "search" in out["message"].lower()


def test_youtube_play_opens_watch_url(monkeypatch):
    opened = []
    monkeypatch.setattr(bt, "resolve_youtube_video_id", lambda q: "dQw4w9wgXcQ")
    monkeypatch.setattr(bt.webbrowser, "open", lambda url: opened.append(url) or True)
    # clear any prior flag
    bt.consume_session_end_after_media()
    out = bt.youtube_play("ramayana trailer")
    assert out["ok"] is True
    assert out["video_id"] == "dQw4w9wgXcQ"
    assert opened == ["https://www.youtube.com/watch?v=dQw4w9wgXcQ"]
    assert "Playing ramayana trailer" in out["message"]
    assert out.get("end_session") is True
    assert bt.consume_session_end_after_media() is True
    assert bt.consume_session_end_after_media() is False


def test_youtube_play_falls_back_to_search(monkeypatch):
    monkeypatch.setattr(bt, "resolve_youtube_video_id", lambda q: None)
    monkeypatch.setattr(bt.webbrowser, "open", lambda url: True)
    out = bt.youtube_play("obscure query")
    assert out["ok"] is True
    assert "search_query=" in out["url"]
    assert "search results" in out["message"].lower()
