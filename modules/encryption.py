"""
modules/encryption.py
Symmetric encryption (Fernet) for files and sensitive DB fields.
The key MUST come from an environment variable — never hardcode it,
never commit it to git.
"""

from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()

_KEY = os.getenv("FERNET_KEY")

if not _KEY:
    raise RuntimeError(
        "FERNET_KEY not found in environment. "
        "Run generate_key.py once and put the output in your .env file."
    )

_fernet = Fernet(_KEY.encode())


def encrypt_bytes(data: bytes) -> bytes:
    """Encrypt raw file bytes (use for scan files, PMDC license files, etc.)"""
    return _fernet.encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    """Decrypt back to raw file bytes."""
    return _fernet.decrypt(token)


def encrypt_text(text: str) -> str:
    """Encrypt a string field (e.g. for sensitive DB columns)."""
    return _fernet.encrypt(text.encode()).decode()


def decrypt_text(token: str) -> str:
    """Decrypt a string field back to plain text."""
    return _fernet.decrypt(token.encode()).decode()


def encrypt_file_to_disk(input_bytes: bytes, output_path: str) -> str:
    """
    Encrypts bytes and writes them to disk. Returns the path written.
    Use this for scan uploads and PMDC license files.
    """
    encrypted = encrypt_bytes(input_bytes)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(encrypted)
    return output_path


def decrypt_file_from_disk(file_path: str) -> bytes:
    """Reads an encrypted file from disk and returns the decrypted raw bytes."""
    with open(file_path, "rb") as f:
        encrypted = f.read()
    return decrypt_bytes(encrypted)