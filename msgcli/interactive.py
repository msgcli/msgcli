"""msg — message client and server launcher."""
from __future__ import annotations

import argparse
import asyncio
import json
import queue
import signal
import sys
import threading
import time

import websockets

from msgcli import DEFAULT_DATA_PATH, DEFAULT_SERVER_PORT, _get_ip, __version__, decrypt_text, encrypt_text

GREEN = "\033[32m" if sys.stdout.isatty() else ""
RED = "\033[31m" if sys.stdout.isatty() else ""
GRAY = "\033[38;5;242m" if sys.stdout.isatty() else ""
RESET = "\033[0m" if sys.stdout.isatty() else ""


def _to_ws_url(addr: str) -> str:
    if addr.startswith("ws://") or addr.startswith("wss://"):
        return addr
    if addr.startswith("http://"):
        return addr.replace("http://", "ws://", 1)
    if addr.startswith("https://"):
        return addr.replace("https://", "wss://", 1)
    return f"ws://{addr}"


def _display_addr(ws_url: str) -> str:
    addr = ws_url.replace("ws://", "").replace("wss://", "")
    if addr.endswith(f":{DEFAULT_SERVER_PORT}"):
        addr = addr[:-len(f":{DEFAULT_SERVER_PORT}")]
    return addr


async def recv_task(ws, shutdown_event, user, key):
    try:
        async for raw in ws:
            data = json.loads(raw)
            action = data.get("action")

            if action == "push":
                m = data["msg"]
                ts = time.strftime("%H:%M:%S", time.localtime(m["ts"]))
                text = decrypt_text(m["text"], key)
                line = f"[{ts}] {m['from']}: {text}"
                print(f"\r\033[K{line}\n{GREEN}{user}>{RESET} ", end="", flush=True)
            elif action == "synced":
                pass
            elif data.get("ok") and data.get("offline"):
                notice = data.get("notice", "")
                if notice:
                    print(f"\r\033[K{GRAY}{notice}{RESET}\n{GREEN}{user}>{RESET} ", end="", flush=True)
            elif "error" in data:
                print(f"\r\033[K{RED}error: {data['error']}{RESET}\n{GREEN}{user}>{RESET} ", end="", flush=True)
    except (asyncio.CancelledError, websockets.exceptions.ConnectionClosed):
        pass
    finally:
        shutdown_event.set()


def _ascii_banner():
    return (
        "\n"
        " _ __ ___  ___  __ _\n"
        "| '_ ` _ \/ __|/ _` |\n"
        "| | | | | \__ \ (_| |\n"
        "|_| |_| |_|___/\__, |\n"
        "               |___/  CLI"
    )


async def client_mode(ws_url: str, key: str, user: str, show_banner: bool = True, prefer_wss: bool = True):
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
            sys.exit(f"{RED}encryption requires 'cryptography'. run: pip install cryptography{RESET}")
    if show_banner:
        print(f"{GREEN}{_ascii_banner()}{RESET}")
        print(f"{GREEN}v{__version__}{RESET}")
        print()
    urls = [ws_url]
    if prefer_wss and ws_url.startswith("ws://"):
        urls.insert(0, ws_url.replace("ws://", "wss://", 1))

    ws = None
    prompt_q = None
    recv_t = None
    connected = False
    for url in urls:
        try:
            ws = await websockets.connect(url)
            connected = True
            break
        except (ConnectionRefusedError, OSError):
            continue

    if not connected:
        print(f"{RED}connection refused: server is not running{RESET}")
        return

    try:
        await ws.send(json.dumps({"action": "auth", "key": key, "user": user}))
        resp = json.loads(await ws.recv())
        if not resp.get("ok"):
            raise RuntimeError(f"auth failed: {resp.get('error', 'unknown')}")

        name = resp.get("name", "")
        if name:
            print(f"Welcome to {name}\n")
        print(f"Connected as '{user}' to {_display_addr(url)}")
        print("Type '@user message' to send, Ctrl+C to quit.")
        print(f"{GRAY}For more details, visit https://msgcli.org{RESET}\n")

        input_q = queue.Queue()
        prompt_q = queue.Queue()

        def read_input():
            while True:
                prompt = prompt_q.get()
                if prompt is None:
                    break
                try:
                    line = input(prompt)
                    input_q.put(("line", line))
                except EOFError:
                    input_q.put(("eof", None))
                    break

        threading.Thread(target=read_input, daemon=True).start()
        prompt_q.put(f"{GREEN}{user}>{RESET} ")

        interrupt_count = 0
        shutdown_event = asyncio.Event()

        recv_t = asyncio.create_task(recv_task(ws, shutdown_event, user, key))

        def on_sigint():
            nonlocal interrupt_count
            interrupt_count += 1
            if interrupt_count == 1:
                print("\nPress Ctrl+C again to exit.", flush=True)
            else:
                shutdown_event.set()

        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, on_sigint)

        try:
            while not shutdown_event.is_set():
                try:
                    kind, data = input_q.get_nowait()
                except queue.Empty:
                    try:
                        await asyncio.wait_for(shutdown_event.wait(), timeout=0.05)
                        break
                    except asyncio.TimeoutError:
                        continue

                if kind == "eof":
                    break
                line = data.strip()
                if not line:
                    prompt_q.put(f"{GREEN}{user}>{RESET} ")
                    continue

                if line.startswith("@"):
                    parts = line[1:].split(" ", 1)
                    if len(parts) < 2:
                        print(f"{RED}Usage: @user message{RESET}")
                        prompt_q.put(f"{GREEN}{user}>{RESET} ")
                        continue
                    to, text = parts
                    encrypted = encrypt_text(text, key)
                    await ws.send(json.dumps({"action": "send", "to": to, "text": encrypted}))
                    ts = time.strftime("%H:%M:%S", time.localtime())
                    print(f"\033[A\033[K{GREEN}[{ts}] @{to} {text}{RESET}")
                else:
                    print(f"{RED}Usage: @user message  (e.g. @bob hello){RESET}")
                prompt_q.put(f"{GREEN}{user}>{RESET} ")
        finally:
            loop.remove_signal_handler(signal.SIGINT)
    except websockets.exceptions.ConnectionClosed:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        if prompt_q is not None:
            prompt_q.put(None)
        if recv_t is not None:
            recv_t.cancel()
            try:
                await recv_t
            except asyncio.CancelledError:
                pass
        if ws is not None:
            try:
                await ws.close()
            except Exception:
                pass

    print("Bye!")


async def hybrid_mode(user: str, key: str, port: int, ssl_cert: str | None = None, ssl_key: str | None = None):
    from msgcli.server import cmd_serve_async

    server_args = argparse.Namespace(
        name="",
        key=key,
        port=port,
        host="0.0.0.0",
        data=None,
        ssl_cert=ssl_cert,
        ssl_key=ssl_key,
    )

    server_stop = asyncio.Event()
    server_task = asyncio.create_task(cmd_serve_async(server_args, stop_event=server_stop, handle_signals=False, show_footer=False))

    await asyncio.sleep(0.5)

    if server_task.done():
        try:
            await server_task
        except Exception as e:
            print(f"{RED}server failed to start: {e}{RESET}")
            return

    ws_url = _to_ws_url(f"127.0.0.1:{port}")
    try:
        await client_mode(ws_url, key, user, show_banner=False, prefer_wss=False)
    finally:
        server_stop.set()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


def _parse_shortcut(shortcut: str) -> tuple[str, str, int]:
    """Parse 'user@host:port' into (user, host, port)."""
    if "@" not in shortcut:
        sys.exit(f"{RED}invalid shortcut format: {shortcut} (expected user@host or user@host:port){RESET}")
    user, rest = shortcut.split("@", 1)
    if ":" in rest:
        host, port_str = rest.rsplit(":", 1)
        if not port_str.isdigit():
            sys.exit(f"{RED}invalid port in shortcut: {port_str}{RESET}")
        return user, host, int(port_str)
    return user, rest, DEFAULT_SERVER_PORT


def main(argv: list | None = None) -> None:
    p = argparse.ArgumentParser(prog="msg", description="Message client and server.", usage=argparse.SUPPRESS)
    p.add_argument("--server", nargs="?", const="", default=None,
                   help="run as server")
    p.add_argument("--user", default=None, help="your username")
    p.add_argument("--host", default="0.0.0.0", help="server host")
    p.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT, help="server port (default: 62818)")
    p.add_argument("--key", default="", help="access key")
    p.add_argument("--ssl-cert", default=None, help="SSL certificate file")
    p.add_argument("--ssl-key", default=None, help="SSL private key file")
    p.add_argument("shortcut", nargs="?", help="shortcut: user@host or user@host:port")
    args = p.parse_args(argv)

    # Parse shortcut: leo@127.0.0.1 or leo@127.0.0.1:62818
    # Hybrid mode: msg leo (no @, starts local server + client)
    if args.shortcut:
        if "@" in args.shortcut:
            user, host, port = _parse_shortcut(args.shortcut)
            args.user = user
            args.host = host
            args.port = port
        else:
            args.user = args.shortcut
            args.host = "127.0.0.1"

    if args.server is not None and args.user is not None:
        sys.exit(f"{RED}error: --server and --user are mutually exclusive{RESET}")

    if args.server is not None:
        # Server mode
        from msgcli.server import cmd_serve_async
        server_args = argparse.Namespace(
            name=args.server,
            key=args.key,
            port=args.port,
            host=args.host,
            data=None,
            ssl_cert=args.ssl_cert,
            ssl_key=args.ssl_key,
        )
        try:
            asyncio.run(cmd_serve_async(server_args))
        except RuntimeError as e:
            print(f"{RED}{e}{RESET}")
        except KeyboardInterrupt:
            print("\nshutting down")

    elif args.user is not None and args.shortcut is not None and "@" not in args.shortcut:
        # Hybrid mode: start server + connect as client locally
        try:
            asyncio.run(hybrid_mode(args.user, args.key, args.port, args.ssl_cert, args.ssl_key))
        except RuntimeError as e:
            print(f"{RED}{e}{RESET}")
        except KeyboardInterrupt:
            pass

    elif args.user is not None:
        # Client mode
        ws_url = _to_ws_url(f"{args.host}:{args.port}")
        try:
            asyncio.run(client_mode(ws_url, args.key, args.user))
        except RuntimeError as e:
            print(f"{RED}{e}{RESET}")
        except KeyboardInterrupt:
            pass

    else:
        sys.exit(
            "usage:\n"
            "  Server: msg --server [NAME] [--key KEY] [--port PORT]\n"
            "  Client: msg --user USER --host HOST [--port PORT] [--key KEY]\n"
            "  Hybrid: msg USER [--key KEY]\n"
            "  Shortcut: msg USER@HOST:PORT [--key KEY]"
        )


if __name__ == "__main__":
    main()
