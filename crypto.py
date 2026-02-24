import base64
import hashlib
import json
import os

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from mnemonic import Mnemonic


def generate_mnemonic() -> str:
    """Generate a new BIP39 12-word mnemonic (128 bits entropy)."""
    return Mnemonic("english").generate(strength=128)


def normalize_mnemonic(mnemonic: str) -> str:
    return " ".join(mnemonic.strip().lower().split())


def derive_user_id(mnemonic: str) -> str:
    normalized = normalize_mnemonic(mnemonic)
    return hashlib.sha256(normalized.encode()).hexdigest()


def derive_email(mnemonic: str) -> str:
    """Derives a deterministic email address from the mnemonic.
    
    Format: user.{userIdHash}@crypticnotes.local
    This matches the Flutter app's MnemonicService.deriveEmail() implementation.
    """
    user_id_hash = derive_user_id(mnemonic)
    return f"user.{user_id_hash}@crypticnotes.local"


def derive_password(mnemonic: str) -> str:
    """Derives a deterministic password from the mnemonic.
    
    Uses SHA256 hash of mnemonic + "password" salt for additional security.
    This matches the Flutter app's MnemonicService.derivePassword() implementation.
    """
    normalized = normalize_mnemonic(mnemonic)
    # Use a different salt than userIdHash to ensure different output
    salted = f"{normalized}:crypticnotes:password".encode()
    digest = hashlib.sha256(salted).digest()
    # Use base64url encoding to ensure password-safe characters
    return base64.urlsafe_b64encode(digest).decode().rstrip('=')


def derive_key(mnemonic: str) -> bytes:
    normalized = normalize_mnemonic(mnemonic)
    return hashlib.sha256(normalized.encode()).digest()


def decrypt_note(ciphertext: str, iv: str, mnemonic: str) -> dict:
    key = derive_key(mnemonic)
    iv_bytes = base64.b64decode(iv)
    cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
    decrypted = unpad(cipher.decrypt(base64.b64decode(ciphertext)), AES.block_size)
    return json.loads(decrypted.decode())


def encrypt_note(title: str, body: str, mnemonic: str) -> tuple[str, str]:
    key = derive_key(mnemonic)
    iv_bytes = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
    payload = json.dumps({"title": title, "body": body}).encode()
    # PKCS7 padding
    pad_len = 16 - (len(payload) % 16)
    padded = payload + bytes([pad_len] * pad_len)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode(), base64.b64encode(iv_bytes).decode()
