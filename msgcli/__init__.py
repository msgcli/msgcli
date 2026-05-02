"""msgcli — shared constants."""
import base64
import os
import socket
import sys
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("MSGCLI_HOME") or (Path.home() / ".msgcli"))
DEFAULT_DATA_PATH = CONFIG_DIR / "server.json"
DEFAULT_SERVER_PORT = 62818
__version__ = "1.2.0"

_SALT = b"msgcli-v1-salt"


def _derive_key(key: str) -> bytes:
    from cryptography.hazmat.primitives import hashes
    try:
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC as PBKDF2
    except ImportError:
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=100000,
    )
    return kdf.derive(key.encode())


def encrypt_text(text: str, key: str) -> str:
    if not key:
        return text
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aes_key = _derive_key(key)
        aesgcm = AESGCM(aes_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, text.encode("utf-8"), None)
        return base64.b64encode(nonce + ciphertext).decode("ascii")
    except ImportError:
        raise RuntimeError("encryption requires 'cryptography'. run: pip install cryptography")
    except Exception:
        return text


def decrypt_text(encrypted: str, key: str) -> str:
    if not key:
        return encrypted
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aes_key = _derive_key(key)
        aesgcm = AESGCM(aes_key)
        data = base64.b64decode(encrypted.encode("ascii"))
        nonce = data[:12]
        ciphertext = data[12:]
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
    except ImportError:
        raise RuntimeError("encryption requires 'cryptography'. run: pip install cryptography")
    except Exception:
        return encrypted


def _get_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip
