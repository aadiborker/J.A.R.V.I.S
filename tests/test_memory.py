from tools import memory_store as ms


def test_remember_and_recall(tmp_path, monkeypatch):
    path = tmp_path / "memory.json"
    monkeypatch.setattr(ms, "MEMORY_PATH", path)
    monkeypatch.setattr("config.MEMORY_PATH", path)

    out = ms.remember("name", "Aadi")
    assert out["ok"] is True
    got = ms.recall("name")
    assert got["ok"] is True
    assert got["value"] == "Aadi"
    assert "Aadi" in ms.format_memory_for_prompt()
    listed = ms.list_memories()
    assert "name" in listed["facts"]


def test_normalize_key_rejects_junk():
    assert ms.normalize_key("Name") == "name"
    assert ms.normalize_key("") is None
    assert ms.normalize_key("!!!") is None


def test_memory_fast_paths(tmp_path, monkeypatch):
    import tools.simple_commands as sc

    path = tmp_path / "memory.json"
    monkeypatch.setattr(ms, "MEMORY_PATH", path)
    monkeypatch.setattr("config.MEMORY_PATH", path)

    class FakeTimer:
        def set_timer(self, *a, **k):
            return {}

    print_text, _ = sc.try_handle_simple("my name is Aadi", FakeTimer())
    assert "Remembered name: Aadi" in print_text
    print_text, _ = sc.try_handle_simple("what's my name", FakeTimer())
    assert "Aadi" in print_text
