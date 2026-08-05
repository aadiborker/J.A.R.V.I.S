from __future__ import annotations

import json
from ui.ws_bridge import UiBridge


def test_emit_noop_when_not_started():
    bridge = UiBridge(host="127.0.0.1", port=18765)
    # Must not raise when nobody is listening / not started.
    bridge.emit({"type": "status", "state": "idle", "detail": "hi"})


def test_emit_records_last_event_for_tests():
    bridge = UiBridge(host="127.0.0.1", port=18766)
    bridge.emit({"type": "ready"})
    assert bridge.last_event == {"type": "ready"}


def test_event_json_roundtrip_shape():
    payload = {"type": "transcript", "role": "user", "text": "hello"}
    encoded = json.dumps(payload)
    assert json.loads(encoded) == payload
