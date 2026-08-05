from __future__ import annotations

import random
import time
from types import SimpleNamespace

import system.power as power


def test_pick_power_joke_returns_known_line():
    joke = power.pick_power_joke(rng=random.Random(0))
    assert joke
    assert joke in power._POWER_JOKES


def test_format_boot_power_line_charging():
    status = power.PowerStatus(percent=72, charging=True, available=True)
    line = power.format_boot_power_line(status, "Test joke.")
    assert "Power at 72 percent." in line
    assert "Charging." in line
    assert "Here's a quick one: Test joke." in line


def test_format_boot_power_line_not_charging():
    status = power.PowerStatus(percent=41, charging=False, available=True)
    line = power.format_boot_power_line(status, "Nope.")
    assert "Not charging." in line
    assert "41" in line


def test_format_boot_unavailable():
    status = power.PowerStatus(percent=None, charging=None, available=False)
    assert power.format_boot_power_line(status, "x") == power.POWER_UNAVAILABLE


def test_format_transition_lines():
    assert (
        power.format_power_transition_line(charging=True, percent=72)
        == "Power connected. Power at 72 percent."
    )
    assert (
        power.format_power_transition_line(charging=False, percent=41)
        == "Running on battery. Power at 41 percent."
    )


def test_get_power_status_no_battery():
    raw = SimpleNamespace(ACLineStatus=1, BatteryFlag=128, BatteryLifePercent=255)
    result = power._status_from_win(raw)
    assert result.available is False


def test_get_power_status_charging():
    raw = SimpleNamespace(ACLineStatus=1, BatteryFlag=8, BatteryLifePercent=88)
    result = power._status_from_win(raw)
    assert result.available is True
    assert result.percent == 88
    assert result.charging is True


def test_get_power_status_on_battery():
    raw = SimpleNamespace(ACLineStatus=0, BatteryFlag=1, BatteryLifePercent=33)
    result = power._status_from_win(raw)
    assert result.available is True
    assert result.percent == 33
    assert result.charging is False


def test_power_monitor_debounces_then_fires():
    transitions: list[tuple[bool, int | None]] = []
    readings = iter(
        [
            power.PowerStatus(80, False, True),
            power.PowerStatus(80, True, True),  # blip start
            power.PowerStatus(81, True, True),  # confirm
            power.PowerStatus(81, True, True),
        ]
    )

    def fake_status():
        try:
            return next(readings)
        except StopIteration:
            return power.PowerStatus(81, True, True)

    mon = power.PowerMonitor(
        on_transition=lambda charging, status: transitions.append(
            (charging, status.percent)
        ),
        status_fn=fake_status,
        interval_s=0.01,
        debounce=2,
    )
    mon.seed(power.PowerStatus(80, False, True))
    mon.start()
    time.sleep(0.12)
    mon.stop()
    assert transitions == [(True, 81)]


def test_emit_power_ui_payload():
    assert power.emit_power_ui_payload(
        power.PowerStatus(None, None, False)
    ) == {"type": "power", "available": False}
    assert power.emit_power_ui_payload(
        power.PowerStatus(50, True, True)
    ) == {"type": "power", "available": True, "percent": 50, "charging": True}
