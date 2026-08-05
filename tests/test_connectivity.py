from __future__ import annotations

import time

import net.connectivity as conn


def test_announcement_strings():
    assert conn.OFFLINE_ANNOUNCE == "Network offline. Switching to lower modules."
    assert conn.ONLINE_ANNOUNCE == "Network restored. Full systems online."


def test_boot_status_line():
    assert conn.boot_status_line(True) == "System Online."
    assert conn.boot_status_line(False) == conn.OFFLINE_ANNOUNCE


def test_set_online_is_threadsafe_readable():
    conn.set_online(True)
    assert conn.is_online() is True
    conn.set_online(False)
    assert conn.is_online() is False


def test_check_internet_true_when_connect_ok(monkeypatch):
    class FakeSock:
        def settimeout(self, t):
            self.t = t

        def connect(self, addr):
            self.addr = addr

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(conn.socket, "socket", lambda *a, **k: FakeSock())
    monkeypatch.setattr(conn, "NETWORK_PROBE_HOSTS", (("1.1.1.1", 443),))
    assert conn.check_internet() is True


def test_check_internet_false_when_all_hosts_fail(monkeypatch):
    class BadSock:
        def settimeout(self, t):
            pass

        def connect(self, addr):
            raise OSError("no route")

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(conn.socket, "socket", lambda *a, **k: BadSock())
    monkeypatch.setattr(conn, "NETWORK_PROBE_HOSTS", (("1.1.1.1", 443), ("8.8.8.8", 443)))
    assert conn.check_internet() is False


def test_monitor_debounces_single_blip():
    transitions: list[bool] = []
    results = iter([True, False, True, True, True])

    def fake_check():
        try:
            return next(results)
        except StopIteration:
            return True

    conn.set_online(True)
    mon = conn.NetworkMonitor(
        on_transition=lambda online: transitions.append(online),
        check_fn=fake_check,
        interval_s=0.01,
        debounce=2,
    )
    mon.start()
    time.sleep(0.12)
    mon.stop()
    assert transitions == []


def test_monitor_announces_after_debounce():
    transitions: list[bool] = []
    results = iter([False, False, False, False])

    def fake_check():
        try:
            return next(results)
        except StopIteration:
            return False

    conn.set_online(True)
    mon = conn.NetworkMonitor(
        on_transition=lambda online: transitions.append(online),
        check_fn=fake_check,
        interval_s=0.01,
        debounce=2,
    )
    mon.start()
    time.sleep(0.12)
    mon.stop()
    assert transitions == [False]
    assert conn.is_online() is False
