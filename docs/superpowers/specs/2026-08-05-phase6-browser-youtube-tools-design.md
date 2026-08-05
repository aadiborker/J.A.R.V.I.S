# Phase 6: Browser / YouTube Tools — Design

**Date:** 2026-08-05  
**Goal:** Let Jarvis open YouTube, search YouTube, and open http(s) URLs in the default browser via local fast-paths and Groq tool-calling.

## Non-goals / constraints

- No Selenium, YouTube Data API, or in-page playback control.
- No launching arbitrary desktop apps (that is a later phase).
- Only `http` and `https` URLs; reject `file:`, `javascript:`, `data:`, empty, and malformed targets.
- Prefer free stdlib (`webbrowser`, `urllib.parse`); no new paid dependency.
- Keep existing time/timer tools and offline lower-modules gate.

## Approach (approved)

**Python `webbrowser` + URL allowlist**, with regex/local fast-paths for clear phrases and Groq tools otherwise.

| Capability | Behavior |
|------------|----------|
| Open YouTube | Default browser → `https://www.youtube.com` |
| YouTube search | → `https://www.youtube.com/results?search_query=<encoded>` |
| Open URL | Normalize host-only input (`google.com` → `https://google.com`); open if scheme is http/https |

## Architecture

1. **`tools/browser_tools.py`**
   - `open_url(url: str) -> dict` — validate + `webbrowser.open`; return `{ok, url, message}` or error payload
   - `open_youtube() -> dict` — thin wrapper around YouTube home
   - `youtube_search(query: str) -> dict` — build search URL then open
   - `normalize_and_validate_url(raw: str) -> str` — raises/`None` on reject
   - Shared spoken-friendly `message` for confirmations

2. **`tools/simple_commands.py`** (extend)
   - Fast-paths (case-insensitive), examples:
     - `open youtube` / `open you tube`
     - `search youtube for <query>` / `youtube search <query>`
     - `open <url>` when token looks like URL/domain (`https://…`, `http://…`, `something.com`)
   - Return `(print_text, speech_text)` like time/timer
   - Run **before** offline gate? Prefer: allow local URL open attempt even offline (browser may still fail); **or** require online for browser tools.  
     **Decision:** require online for browser/YouTube tools (need network for useful result); offline → existing lower-modules reply unless another local tool matches first.

3. **`tools/offline_gate.py`**
   - Keep: simple handlers first (including new browser fast-paths when online)
   - Browser fast-paths should check `is_online()` themselves or live only in the online path — **Decision:** `try_handle_simple` handles browser patterns; if matched while offline, return a short “need network for browser” line instead of opening.

4. **`main.py` / Groq tool registry**
   - Register `open_url`, `open_youtube`, `youtube_search` alongside `get_time` / `set_timer`
   - Tool descriptions tell the model to use these for browser intents

5. **HUD**
   - Optional: system transcript line when a browser tool opens something (already covered by assistant reply / jarvis_typed)

## Spoken copy (examples)

- YouTube home: `Opening YouTube.`
- Search: `Searching YouTube for lo-fi beats.`
- URL: `Opening https://google.com.`
- Rejected URL: `I can only open web links.`
- Offline: `Browser tools need a network connection.`

## Error handling

- Invalid URL / blocked scheme → do not call `webbrowser`; return error dict; Jarvis speaks rejection line.
- `webbrowser.open` failure → report failure; do not crash the session.
- Empty YouTube query → ask/clarify via model or reject on fast-path.

## Verification

- Unit tests: URL normalize/validate (good https, bare domain, reject `file:`, reject empty); search URL encoding; fast-path parsing; offline browser refusal.
- Manual: “open youtube”, “search youtube for cats”, “open https://example.com”, airplane mode refusal.

## Out of scope

- App launching (Spotify, Notepad, etc.)
- Clicking play / controlling the YouTube player
- Persistent browser profiles or multi-window management
- SSH / email / memory (later phases)
