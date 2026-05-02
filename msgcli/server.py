"""msgserver — WebSocket message server with user auth."""
from __future__ import annotations

import asyncio
import getpass
import json
import logging
import signal
import ssl
import sys
import time
import uuid
from pathlib import Path
from threading import Lock

import websockets

logging.getLogger("websockets.server").setLevel(logging.CRITICAL)

from msgcli import DEFAULT_DATA_PATH, DEFAULT_SERVER_PORT, _get_ip, __version__

GREEN = "\033[32m" if sys.stdout.isatty() else ""
RED = "\033[31m" if sys.stdout.isatty() else ""
GRAY = "\033[38;5;242m" if sys.stdout.isatty() else ""
RESET = "\033[0m" if sys.stdout.isatty() else ""


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"messages": []}))
        self._lock = Lock()

    def _load(self) -> dict:
        return json.loads(self.path.read_text())

    def _save(self, data: dict) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self.path)

    def add(self, msg: dict) -> None:
        with self._lock:
            data = self._load()
            data["messages"].append(msg)
            self._save(data)

    def take(self, user: str) -> list:
        with self._lock:
            data = self._load()
            taken, kept = [], []
            for m in data["messages"]:
                (taken if m["to"] == user else kept).append(m)
            data["messages"] = kept
            self._save(data)
            return taken


class ServerState:
    def __init__(self, name: str, key: str, store: Store):
        self.name = name
        self.key = key
        self.store = store


CONNECTIONS: dict[str, any] = {}
SERVER_STATE: ServerState | None = None


async def handler(websocket):
    try:
        raw = await websocket.recv()
        data = json.loads(raw)
    except Exception:
        await websocket.close(1008, "invalid auth")
        return

    if data.get("action") != "auth":
        await websocket.send(json.dumps({"error": "auth required"}))
        await websocket.close(1008, "auth required")
        return

    key = data.get("key")
    user = (data.get("user") or "").strip()

    if key != SERVER_STATE.key:
        await websocket.send(json.dumps({"error": "invalid key"}))
        await websocket.close(1008, "invalid key")
        return

    if not user:
        await websocket.send(json.dumps({"error": "user required"}))
        await websocket.close(1008, "user required")
        return

    if user in CONNECTIONS:
        await websocket.send(json.dumps({"error": "user already logged in"}))
        await websocket.close(1008, "user already logged in")
        return

    # Auth success
    CONNECTIONS[user] = websocket
    await websocket.send(json.dumps({"ok": True, "name": SERVER_STATE.name}))

    # Send offline messages
    offline = SERVER_STATE.store.take(user)
    for m in offline:
        await websocket.send(json.dumps({"action": "push", "msg": m}))

    await websocket.send(json.dumps({"action": "synced"}))

    try:
        async for raw in websocket:
            data = json.loads(raw)
            action = data.get("action")

            if action == "send":
                to = (data.get("to") or "").strip()
                text = data.get("text")
                if not to or not text:
                    await websocket.send(json.dumps({"error": "to and text required"}))
                    continue

                msg = {
                    "id": uuid.uuid4().hex,
                    "from": user,
                    "to": to,
                    "text": text,
                    "ts": time.time(),
                }
                SERVER_STATE.store.add(msg)

                if to in CONNECTIONS:
                    try:
                        await CONNECTIONS[to].send(json.dumps({"action": "push", "msg": msg}))
                    except Exception:
                        pass
                    await websocket.send(json.dumps({"ok": True, "id": msg["id"]}))
                else:
                    await websocket.send(json.dumps({"ok": True, "id": msg["id"], "offline": True, "notice": f"{to} is offline, message stored"}))
            else:
                await websocket.send(json.dumps({"error": "unknown action"}))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if user in CONNECTIONS and CONNECTIONS[user] is websocket:
            del CONNECTIONS[user]


async def cmd_serve_async(args: argparse.Namespace, stop_event: asyncio.Event | None = None, handle_signals: bool = True, show_footer: bool = True):
    global SERVER_STATE

    name = args.name
    show_name = bool(name)
    key = args.key

    if not name:
        name = "msgcli"

    if not key:
        print(f"{RED}Warning: no access key set, messages will be sent in plain text{RESET}")
    else:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            try:
                from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC as _PBKDF2
            except ImportError:
                from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2 as _PBKDF2
        except ImportError:
            raise RuntimeError("encryption requires 'cryptography'. run: pip install cryptography")

    store = Store(Path(args.data) if args.data else DEFAULT_DATA_PATH)
    SERVER_STATE = ServerState(name, key, store)

    host = args.host
    port = args.port
    display_host = _get_ip() if host == "0.0.0.0" else host
    if port == DEFAULT_SERVER_PORT:
        address = display_host
    else:
        address = f"{display_host}:{port}"

    ssl_context = None
    ssl_cert = getattr(args, "ssl_cert", None)
    ssl_key = getattr(args, "ssl_key", None)
    if ssl_cert and ssl_key:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(ssl_cert, ssl_key)
        scheme = "wss://"
    else:
        scheme = "ws://"

    banner = (
        " _ __ ___  ___  __ _\n"
        "| '_ ` _ \/ __|/ _` |\n"
        "| | | | | \__ \ (_| |\n"
        "|_| |_| |_|___/\__, |\n"
        "               |___/  CLI"
    )

    print()
    print(f"{GREEN}{banner}{RESET}")
    print(f"{GREEN}v{__version__}{RESET}")
    print()
    print("msg server is running")
    print(f"Host: {address}")
    if show_name:
        print(f"Name: {name}")
    if key:
        print(f"Key:  {key}")
    print()
    print(f"Type 'msg user@{address}' client connect and chat, Ctrl+C to shutdown.")
    if show_footer:
        print(f"{GRAY}For more details, visit https://msgcli.org{RESET}")
    print()

    if stop_event is None:
        stop_event = asyncio.Event()
    interrupt_count = 0

    def on_sigint():
        nonlocal interrupt_count
        interrupt_count += 1
        if interrupt_count >= 2:
            stop_event.set()
        else:
            print("\nPress Ctrl+C again to exit.", flush=True)

    loop = asyncio.get_running_loop()

    def _exception_handler(_loop, context):
        exc = context.get("exception")
        if isinstance(exc, websockets.exceptions.InvalidMessage):
            return
        loop.default_exception_handler(context)

    loop.set_exception_handler(_exception_handler)

    if handle_signals:
        loop.add_signal_handler(signal.SIGINT, on_sigint)

    try:
        async with websockets.serve(handler, host, port, ping_interval=60, ping_timeout=10, ssl=ssl_context):
            await stop_event.wait()
    finally:
        loop.set_exception_handler(None)
        if handle_signals:
            loop.remove_signal_handler(signal.SIGINT)
        for ws in list(CONNECTIONS.values()):
            try:
                await ws.close()
            except Exception:
                pass
        CONNECTIONS.clear()
    if handle_signals:
        print("\nshutting down")
