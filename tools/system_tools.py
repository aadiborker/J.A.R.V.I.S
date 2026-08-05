from __future__ import annotations

import datetime
import os
import subprocess
import sys
from pathlib import Path


def _gb(nbytes: float) -> float:
    return round(nbytes / (1024**3), 1)


def get_system_status(**_kwargs) -> dict:
    """Return RAM and CPU usage (requires psutil)."""
    try:
        import psutil
    except ImportError:
        return {
            "ok": False,
            "message": "System stats need the psutil package installed.",
        }

    mem = psutil.virtual_memory()
    # Short interval sample; 0.0 returns last known / quick reading.
    cpu = float(psutil.cpu_percent(interval=0.2))
    used_gb = _gb(mem.used)
    total_gb = _gb(mem.total)
    ram_pct = int(round(mem.percent))
    cpu_pct = int(round(cpu))
    message = (
        f"RAM is at {ram_pct} percent — about {used_gb} of {total_gb} gigabytes used. "
        f"CPU is at {cpu_pct} percent."
    )
    return {
        "ok": True,
        "ram_percent": ram_pct,
        "ram_used_gb": used_gb,
        "ram_total_gb": total_gb,
        "cpu_percent": cpu_pct,
        "message": message,
    }


def _audio_endpoint():
    from ctypes import POINTER, cast

    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def set_volume(level: int | float = 50, **_kwargs) -> dict:
    """Set master volume 0–100 (Windows Core Audio via pycaw)."""
    if sys.platform != "win32":
        return {"ok": False, "message": "Volume control is only supported on Windows."}
    try:
        level_i = int(round(float(level)))
    except (TypeError, ValueError):
        return {"ok": False, "message": "Volume level must be a number from 0 to 100."}
    level_i = max(0, min(100, level_i))
    try:
        endpoint = _audio_endpoint()
        endpoint.SetMasterVolumeLevelScalar(level_i / 100.0, None)
        if level_i > 0:
            endpoint.SetMute(0, None)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Couldn't set volume: {exc}"}
    return {"ok": True, "level": level_i, "message": f"Volume set to {level_i} percent."}


def set_mute(muted: bool = True, **_kwargs) -> dict:
    """Mute or unmute the default playback device."""
    if sys.platform != "win32":
        return {"ok": False, "message": "Mute control is only supported on Windows."}
    flag = bool(muted)
    try:
        endpoint = _audio_endpoint()
        endpoint.SetMute(1 if flag else 0, None)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Couldn't change mute: {exc}"}
    return {
        "ok": True,
        "muted": flag,
        "message": "Muted." if flag else "Unmuted.",
    }


def _lock_workstation() -> None:
    import ctypes

    ctypes.windll.user32.LockWorkStation()


def lock_pc(**_kwargs) -> dict:
    """Lock the Windows workstation."""
    if sys.platform != "win32":
        return {"ok": False, "message": "Lock is only supported on Windows."}
    try:
        _lock_workstation()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Couldn't lock the PC: {exc}"}
    return {"ok": True, "message": "Locking the PC."}


def take_screenshot(**_kwargs) -> dict:
    """Capture the primary screen to the Desktop (PNG)."""
    if sys.platform != "win32":
        return {"ok": False, "message": "Screenshots are only supported on Windows."}

    desktop = Path.home() / "Desktop"
    if not desktop.is_dir():
        desktop = Path.home() / "OneDrive" / "Desktop"
    if not desktop.is_dir():
        desktop = Path.home() / "Pictures"
    desktop.mkdir(parents=True, exist_ok=True)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = desktop / f"jarvis-screenshot-{stamp}.png"

    ps = f"""
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bmp.Save('{str(out_path).replace("'", "''")}')
$g.Dispose(); $bmp.Dispose()
"""
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Couldn't take a screenshot: {exc}"}

    if proc.returncode != 0 or not out_path.is_file():
        err = (proc.stderr or proc.stdout or "").strip() or "unknown error"
        return {"ok": False, "message": f"Couldn't take a screenshot: {err}"}

    return {
        "ok": True,
        "path": str(out_path),
        "message": f"Screenshot saved to {out_path.name} on the Desktop.",
    }


def set_brightness(level: int | float = 50, **_kwargs) -> dict:
    """Best-effort display brightness 0–100 (laptop WMI)."""
    if sys.platform != "win32":
        return {"ok": False, "message": "Brightness control is only supported on Windows."}
    try:
        level_i = int(round(float(level)))
    except (TypeError, ValueError):
        return {"ok": False, "message": "Brightness level must be a number from 0 to 100."}
    level_i = max(0, min(100, level_i))

    ps = (
        f"$b = Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods "
        f"-ErrorAction SilentlyContinue; "
        f"if (-not $b) {{ Write-Error 'no brightness interface'; exit 2 }}; "
        f"$b | ForEach-Object {{ $_.WmiSetBrightness(1, {level_i}) }}"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Couldn't set brightness: {exc}"}

    if proc.returncode != 0:
        return {
            "ok": False,
            "message": "Brightness isn't available on this display (often desktop monitors).",
        }
    return {
        "ok": True,
        "level": level_i,
        "message": f"Brightness set to {level_i} percent.",
    }
