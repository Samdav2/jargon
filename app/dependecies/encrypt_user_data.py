import json
import binascii
from eth_account import Account
from eth_keys.backends import NativeECCBackend
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from ecies import encrypt, decrypt

import base64

ecc_backend = NativeECCBackend()


def get_public_key_from_private(private_key_hex: str) -> str:
    """
    Derives the full, uncompressed public key from a given private key.

    This is a fundamental part of asymmetric cryptography. The public key
    can always be recalculated from the private key.

    :param private_key_hex: The user's private key in hex format
    :return: The user's full public key in hex format
    """

    acct = Account.from_key(private_key_hex)


    public_key_hex = acct._key_obj
    return public_key_hex.public_key.to_hex()


def encrypt_data_with_public_key(public_key_hex: str, data_bytes: bytes) -> bytes:
    """
    Encrypts any data (bytes) using the user's PUBLIC key.
    Only the corresponding private key can decrypt this.

    This performs ECIES (Hybrid Encryption):
    1. Generates a one-time AES key.
    2. Encrypts the data with AES.
    3. Encrypts the one-time AES key with the user's Public Key.
    4. Returns (Encrypted AES Key + Encrypted Data).

    :param public_key_hex: The user's public key (from their address)
    :param data_bytes: The raw data to encrypt (e.g., a JSON string as bytes)
    :return: The encrypted "jargon" as raw bytes
    """
    print(f"[Encrypt] Encrypting {len(data_bytes)} bytes...")

    if public_key_hex.startswith('0x'):
        public_key_hex = public_key_hex[2:]

    public_key_bytes = binascii.unhexlify(public_key_hex)

    encrypted_jargon = encrypt(public_key_bytes, data_bytes)

    print("[Encrypt] Encryption successful.")
    return encrypted_jargon

async def decrypt_data_with_private_key(private_key_hex: str, encrypted_jargon: str) -> bytes: # <--- 1. Changed to str
    """
    Decrypts the ECIES "jargon" using the user's PRIVATE key.
    ...
    :param encrypted_jargon: The encrypted data blob (as a Base64 string)
    ...
    """
    print(f"[Decrypt] Decrypting {len(encrypted_jargon)} bytes of Base64 string...")

    if private_key_hex.startswith('0x'):
        private_key_hex = private_key_hex[2:]

    private_key_bytes = binascii.unhexlify(private_key_hex)

    # 2. Decode the Base64 string into raw bytes
    # You must .encode() the string before passing to b64decode
    encrypted_bytes_to_decrypt = base64.b64decode(encrypted_jargon.encode('utf-8'))
    print("Bytes Jargon", {encrypted_bytes_to_decrypt})

    try:
        # 3. Use the correct variable (the raw bytes)
        decrypted_data = decrypt(private_key_bytes, encrypted_bytes_to_decrypt)
        print("[Decrypt] Decryption successful.")
        return decrypted_data

    except Exception as e:
        print(f"[Decrypt] DECRYPTION FAILED: {e}")
        raise ValueError("Decryption failed. Invalid private key or corrupt data.")

async def encrypt_private_key(private_key_hex: str) -> str:
    load_dotenv()
    VOID = os.getenv("VOID")
    key = VOID.encode("utf-8")
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(private_key_hex.encode("utf-8"))
    return encrypted_data.decode("utf-8")

async def decrypt_private_key(encrypted_data_json: str) -> str:
    load_dotenv()
    VOID = os.getenv("VOID")
    key = VOID.encode("utf-8")
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_data_json.encode("utf-8"))
    return decrypted_data.decode("utf-8")

async def encrypt_pw_key(private_key_hex: str, token: str) -> str:

    key = token.encode("utf-8")
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(private_key_hex.encode("utf-8"))
    return encrypted_data.decode("utf-8")

async def decrypt_pw_key(encrypted_data_json: str, token: str) -> str:

    key = token.encode("utf-8")
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_data_json.encode("utf-8"))
    return decrypted_data.decode("utf-8")
