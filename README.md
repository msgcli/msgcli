# Msg CLI

<p align="center">
  A lightweight tool for sending and receiving messages in the terminal.
  <br>
  Zero config, plug-and-play. Both server and client, peer-to-peer.
</p>

<p align="center">
  <a href="https://msgcli.org">msgcli.org</a> ·
  <a href="mailto:support@msgcli.org">Support</a>
</p>

---

## Features

- **Zero Config** — No account or config file needed, start messaging with one command
- **Hybrid Mode** — Both server and client, peer-to-peer without intermediary service
- **Secure Encryption** — Set a key via `--key` parameter to secure communications
- **Native Terminal** — Runs entirely in the CLI, perfect for developers and tech pros
- **AI Agent Ready** — Built for machine-to-machine messaging, ideal for multi-agent systems
- **Cross-Platform** — Runs on macOS, Linux, and Windows with a single binary

## Installation

### macOS / Linux

```bash
curl -fsSL https://msgcli.org/install.sh | bash
```

### Windows

```powershell
irm https://msgcli.org/install.ps1 | iex
```

## Quick Start

### 1. Launch (Hybrid Mode)

Runs as both server and client, waiting for connection:

```bash
msg user
```

### 2. Connect and Chat

Connect from another machine and start chatting:

```bash
msg user@host
```

## Command Reference

| Command | Description |
|---------|-------------|
| `msg USER [--key KEY]` | Hybrid Mode — runs as both server and client, waiting for remote connection |
| `msg USER@HOST:PORT [--key KEY]` | Client (Quick Connect) — quick connect via `USER@HOST:PORT` format |
| `msg --server [NAME] [--key KEY] [--port PORT]` | Server Mode — runs only as a message server |
| `msg --user USER --host HOST [--port PORT] [--key KEY]` | Client (Full Parameters) — connect using full parameter format |

## Security

Use the `--key` flag to encrypt your communications:

```bash
msg user --key my-secret-key
```

## License

Open-source CLI messaging tool.

---

<p align="center">
  MsgCLI was created by <a href="https://holeo.com">Leo Long</a>
</p>
