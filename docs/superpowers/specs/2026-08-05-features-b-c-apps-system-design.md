# Features B + C — Desktop Apps & System Controls

**Date:** 2026-08-05  
**Goal:** Voice/tool support to open allowlisted apps, and to query/control basic PC state (RAM, CPU, volume, mute, lock, screenshot).

## B — Desktop apps
- Tool: `open_app(name)`
- Allowlist only (e.g. notepad, calculator, chrome, edge, explorer, spotify, cmd, powershell)
- Resolve via `shutil.which` + common install paths
- Fast-path: `open notepad`, `launch chrome`, etc.
- Offline: allowed (local)

## C — System controls
- `get_system_status()` → RAM used/total/%, CPU %
- `set_volume(level_0_to_100)` / `set_mute(muted: bool)`
- `lock_pc()`
- `take_screenshot()` → save under user Desktop / Pictures, return path
- Brightness: best-effort on laptops; skip if unavailable
- Fast-paths for clear phrases (“how much ram”, “mute”, “lock the pc”, “screenshot”)
- Prefer `psutil` + Windows APIs (`ctypes` / Core Audio)

## Out of scope
- Arbitrary executable paths from the model
- Killing processes / admin elevation
- Feature A memory, D VAD, etc.
