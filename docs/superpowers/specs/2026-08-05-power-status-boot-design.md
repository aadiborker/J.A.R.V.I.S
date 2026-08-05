# Power Status Design — Boot Report + Charge Transitions

**Date:** 2026-08-05  
**Goal:** On boot, announce power level and charging state with a short joke; while running, announce when power is plugged or unplugged (same spirit as network mode).

## Non-goals / constraints

- Wording uses **“power”**, not “battery” (e.g. `Power at 72 percent`).
- Joke plays **once at boot only** — not on every plug/unplug.
- No cloud dependency; local Windows status only.
- Desktop PCs without a battery: do not invent a percent; announce that power status is unavailable (or AC-only) and skip transition monitoring.
- Keep `speak(text)` as the TTS entry; pause wake-word while speaking (same as network transitions).

## Approach (approved)

**Background power poller** (like `NetworkMonitor`):

| Moment | Behavior |
|--------|----------|
| Boot | After network boot cue: say power % + charging/not charging + one funny joke from a local list |
| Plug / unplug | Debounced announce of charge-state change + current power % (no joke) |
| HUD (optional) | Emit `{"type":"power","percent":N,"charging":bool}` (or `available:false`) |

## Spoken copy

**Boot (examples):**

- `Power at 72 percent. Charging. Here's a quick one: Why did the computer go to the doctor? It had a virus.`
- `Power at 41 percent. Not charging. Here's a quick one: …`

**Transition (examples):**

- Plugged in: `Power connected. Power at 72 percent.`
- Unplugged: `Running on battery. Power at 41 percent.`  
  (Transition lines may say “battery” only in the “running on …” phrase if natural; prefer `Running on power reserve.` if we must avoid “battery” entirely — **default:** use `Running on battery.` for clarity when unplugged.)

**Unavailable:**

- `Power status unavailable.`

## Architecture

1. **`system/power.py`** (new):
   - `PowerStatus` dataclass: `percent: int | None`, `charging: bool | None`, `available: bool`
   - `get_power_status() -> PowerStatus` via `ctypes` + `GetSystemPowerStatus` (`BatteryFlag == 128` → no system battery → `available=False`)
   - `format_boot_power_line(status, joke: str) -> str`
   - `format_power_transition_line(charging: bool, percent: int | None) -> str`
   - `pick_power_joke(rng=None) -> str` — small curated list of clean, short one-liners
   - `PowerMonitor` — poll every `POWER_CHECK_INTERVAL_SECONDS` (default 15); debounce charge-state flips (`POWER_DEBOUNCE_CHECKS = 2`); callback `on_transition(charging: bool, status: PowerStatus)`

2. **`config.py`:**
   - `POWER_CHECK_INTERVAL_SECONDS = 15`
   - `POWER_DEBOUNCE_CHECKS = 2`

3. **`main.py` boot order:**
   1. Network boot cue (`System Online.` / offline line)
   2. Power boot line (status + joke) — speak & transcript
   3. Daily greeting  
   Start `PowerMonitor` after initial status seed (only if `available`).

4. **HUD:** small power chip or reuse a status pill from `power` WS events (percent + charging icon/text). Bridge Connected/Offline and WAN chips stay unchanged.

## Error handling

- API failure → `available=False`, speak unavailable once at boot; do not start monitor.
- Percent `255` (unknown) → treat as unavailable or omit percent in the sentence.
- Debounce flaps from flaky chargers.
- Transition TTS errors → log; keep internal state correct.

## Verification

- Unit tests: mock `GetSystemPowerStatus` structs for charging / not charging / no battery; formatters; joke non-empty; monitor fires once after debounce on charge flip.
- Manual: boot hears power + joke; unplug/plug laptop hears transition; HUD updates if present.

## Out of scope

- Low-battery warnings at thresholds (can add later).
- Asking “what’s my power?” as a voice tool (can add later via local fast-path).
- macOS/Linux power APIs.
