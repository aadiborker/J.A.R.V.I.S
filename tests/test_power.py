from __future__ import annotations

import time
from types import SimpleNamespace

import system.power as power


def test_format_boot_power_line_charging():
    status = power.PowerStatus(percent=72, charging=True, available=True)
    line = power.format_boot_power_line(status)
    assert line == "Power at 72 percent. Charging."
    assert power.CHARGER_HINT not in line


def test_format_boot_power_line_not_charging():
    status = power.PowerStatus(percent=41, charging=False, available=True)
    line = power.format_boot_power_line(status)
    assert "Power at 41 percent." in line
    assert "Not charging." in line
    assert power.CHARGER_HINT in line
    assert "joke" not in line.lower()


def test_format_boot_unavailable():
    status = power.PowerStatus(percent=None, charging=None, available=False)
    assert power.format_boot_power_line(status) == power.POWER_UNAVAILABLE


def test_format_transition_lines():
    assert (
        power.format_power_transition_line(charging=True, percent=72)
        == "Power connected. Power at 72 percent."
    )
    unplugged = power.format_power_transition_line(charging=False, percent=41)
    assert unplugged.startswith("Running on battery.")
    assert "Power at 41 percent." in unplugged
    assert power.CHARGER_HINT in unplugged


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
            power.PowerStatus(80, True, True),
            power.PowerStatus(81, True, True),
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
