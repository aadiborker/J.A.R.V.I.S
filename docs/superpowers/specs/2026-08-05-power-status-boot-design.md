# Power Status Design — Boot Report + Charge Transitions

**Date:** 2026-08-05  
**Goal:** On boot, announce power level and charging state; while running, announce when power is plugged or unplugged (same spirit as network mode).

## Non-goals / constraints

- Wording uses **“power”**, not “battery” for the percent line (e.g. `Power at 72 percent`).
- No jokes on boot or transitions.
- When not charging (boot or unplug), append: `Please connect a charger for longer usability.`
- No cloud dependency; local Windows status only.
- Desktop PCs without a battery: do not invent a percent; announce that power status is unavailable and skip transition monitoring.
- Keep `speak(text)` as the TTS entry; pause wake-word while speaking (same as network transitions).

## Spoken copy

**Boot:**

- Charging: `Power at 72 percent. Charging.`
- Not charging: `Power at 41 percent. Not charging. Please connect a charger for longer usability.`

**Transition:**

- Plugged in: `Power connected. Power at 72 percent.`
- Unplugged: `Running on battery. Power at 41 percent. Please connect a charger for longer usability.`

**Unavailable:** `Power status unavailable.`


## Architecture

1. **`system/power.py`:**
   - `PowerStatus`, `get_power_status()`, `format_boot_power_line(status)`, `format_power_transition_line(...)`, `PowerMonitor`
   - Not-charging lines append `CHARGER_HINT`
2. **`config.py`:** `POWER_CHECK_INTERVAL_SECONDS`, `POWER_DEBOUNCE_CHECKS`
3. **`main.py` boot order:** network cue → power line → daily greeting; start `PowerMonitor` if available
4. **HUD:** `power` WS events for the power chip

## Error handling

- API failure → unavailable at boot; no monitor
- Debounce charger flaps; log TTS errors on transitions

## Verification

- Unit tests for formatters + monitor debounce
- Manual: boot / unplug hear charger hint when not charging

## Out of scope

- Low-battery threshold warnings
- Voice “what’s my power?” tool
- Non-Windows power APIs
