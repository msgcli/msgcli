# Msg CLI

<p align="center">
  <a href="https://msgcli.org">msgcli.org</a> ·
  <a href="mailto:support@msgcli.org">Support</a>
</p>

<p align="center">
  A lightweight CLI messaging tool over WebSocket.<br>
  Zero config, plug-and-play. Run as server, client, or both.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
</p>

---

## Features

- **Zero Config** — No account or config file needed; start messaging with one command
- **Hybrid Mode** — Launch a local server and connect as a client simultaneously
- **Secure Encryption** — AES-GCM encryption with PBKDF2 key derivation; set a key via `--key`
- **Offline Messages** — Messages are stored server-side and delivered when the recipient comes online
- **WSS / TLS Support** — Run the server with SSL certificates for encrypted WebSocket connections
- **AI Agent Ready** — Built for machine-to-machine messaging, ideal for multi-agent systems
- **Native Terminal** — Runs entirely in the CLI, perfect for developers and remote workflows
- **Cross-Platform** — Runs on macOS, Linux, and Windows

## Prerequisites

- Python 3.9 or higher
- pip

## Installation

### macOS / Linux

```bash
curl -fsSL https://msgcli.org/install.sh | bash
```

### Windows (PowerShell)

```powershell
irm https://msgcli.org/install.ps1 | iex
```

## Quick Start

### 1. Hybrid Mode (Server + Client)

Start a local server and connect as a client in one command:

```bash
msg leo --key my-secret-key
```

Others can connect to your machine using your IP address:

```bash
msg jim@192.168.1.5 --key my-secret-key
```

### 2. Dedicated Server

Run a standalone server on a public or private host:

```bash
msg --server MyServer --key my-secret-key --port 62818
```

Then connect from another machine:

```bash
msg jim@192.168.1.5:62818 --key my-secret-key
```

### 3. Client Only

Connect to an existing server using full parameters:

```bash
msg --user jim --host 192.168.1.5 --port 62818 --key my-secret-key
```

## Command Reference

| Command | Description |
|---------|-------------|
| `msg USER [--key KEY]` | Hybrid mode: start a local server and connect as client |
| `msg USER@HOST:PORT [--key KEY]` | Quick connect using `USER@HOST:PORT` format |
| `msg --server [NAME] [--key KEY] [--port PORT] [--ssl-cert CERT --ssl-key KEY]` | Server mode: run as a dedicated message server |
| `msg --user USER --host HOST [--port PORT] [--key KEY]` | Client mode: connect with explicit parameters |

> **Note:** When using `--key`, all parties must use the same key to encrypt and decrypt messages.

## Security

Communications are encrypted with **AES-GCM** using a key derived via **PBKDF2** (100,000 iterations). Set a shared key to prevent message interception:

```bash
msg leo --key my-secret-key
```

For server deployments, use TLS to encrypt the WebSocket transport:

```bash
msg --server --ssl-cert cert.pem --ssl-key key.pem --key my-secret-key
```

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  MsgCLI was created by <a href="https://holeo.com">Leo Long</a>
</p>
