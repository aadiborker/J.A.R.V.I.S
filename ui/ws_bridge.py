from __future__ import annotations

import asyncio
import json
import threading
from typing import Any


class UiBridge:
    """Thread-safe localhost WebSocket broadcaster for the Electron HUD."""

    def __init__(self, *, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = int(port)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._server: Any = None
        self._clients: set[Any] = set()
        self._lock = threading.Lock()
        self._started = threading.Event()
        self.last_event: dict[str, Any] | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._thread = threading.Thread(target=self._run, name="ui-ws-bridge", daemon=True)
        self._thread.start()
        if not self._started.wait(timeout=5.0):
            raise RuntimeError(f"UI WebSocket bridge failed to start on {self.host}:{self.port}")

    def stop(self) -> None:
        loop = self._loop
        if loop is None:
            return

        async def _shutdown() -> None:
            for ws in list(self._clients):
                try:
                    await ws.close()
                except Exception:  # noqa: BLE001
                    pass
            self._clients.clear()
            if self._server is not None:
                self._server.close()
                await self._server.wait_closed()
            loop.stop()

        try:
            asyncio.run_coroutine_threadsafe(_shutdown(), loop).result(timeout=5.0)
        except Exception:  # noqa: BLE001
            pass
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self._thread = None
        self._loop = None
        self._server = None
        self._started.clear()

    def emit(self, event: dict[str, Any]) -> None:
        self.last_event = dict(event)
        loop = self._loop
        if loop is None or not self.is_running:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._broadcast(event), loop)
        except Exception:  # noqa: BLE001
            pass

    async def _broadcast(self, event: dict[str, Any]) -> None:
        if not self._clients:
            return
        message = json.dumps(event, ensure_ascii=False)
        dead: list[Any] = []
        for ws in list(self._clients):
            try:
                await ws.send(message)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)

    def _run(self) -> None:
        try:
            import websockets
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("websockets package required for UI bridge") from exc

        async def handler(websocket: Any) -> None:
            with self._lock:
                self._clients.add(websocket)
            try:
                # Keep connection open; HUD is receive-only in v1.
                await websocket.wait_closed()
            finally:
                with self._lock:
                    self._clients.discard(websocket)

        async def main() -> None:
            self._server = await websockets.serve(handler, self.host, self.port)
            self._started.set()
            await asyncio.Future()  # run forever until loop stopped

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(main())
        except Exception:  # noqa: BLE001
            self._started.set()
        finally:
            try:
                self._loop.close()
            except Exception:  # noqa: BLE001
                pass


_bridge: UiBridge | None = None


def get_bridge() -> UiBridge | None:
    return _bridge


def enable_bridge(*, host: str, port: int) -> UiBridge:
    global _bridge
    if _bridge is not None and _bridge.is_running:
        return _bridge
    _bridge = UiBridge(host=host, port=port)
    _bridge.start()
    return _bridge


def emit_ui(event: dict[str, Any]) -> None:
    if _bridge is not None:
        _bridge.emit(event)
