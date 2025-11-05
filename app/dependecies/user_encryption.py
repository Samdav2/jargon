from eth_account import Account
from eth_account.hdaccount import Mnemonic
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import json
import binascii
from app.schemas.user import UserCreate
import hashlib
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

PEPPER = os.getenv("PEPPERL")
SALT = os.getenv("SALTL")

SDE_DERIVATION_PATH = "m/44'/60'/0'/0/0"

async def generate_sovereign_identity():
    """
    Generates a new BIP39 Mnemonic phrase and derives the primary
    SDE key pair from it.

    This function should be run on the CLIENT-SIDE (e.g., in the user's app).
    """


    mnemonic_phrase = Mnemonic("english").generate(15)
    print("Generated Mnemonic Phrase:", mnemonic_phrase)

    Account.enable_unaudited_hdwallet_features()

    derived_account = Account.from_mnemonic(
        mnemonic=mnemonic_phrase,
        account_path=SDE_DERIVATION_PATH
    )

    address = derived_account.address
    private_key_hex = derived_account.key.hex()


    did = f"did:sde:mainnet:{address}"

    return {
        "mnemonic_phrase": mnemonic_phrase,
        "did": did,
        "address": address,
        "private_key_hex": private_key_hex
    }

async def encrypt_private_key(private_key_hex: str, user: UserCreate) -> str:
    """
    Encrypts a private key using AES-256-GCM, the industry standard.
    This is what will be stored on the server.
    """

    key = user.password.ljust(32, '0')[:32].encode('utf-8')
    data = binascii.unhexlify(private_key_hex)

    cipher = AES.new(key, AES.MODE_GCM)

    ciphertext, tag = cipher.encrypt_and_digest(data)


    encrypted_data = json.dumps({
        'nonce': binascii.hexlify(cipher.nonce).decode('utf-8'),
        'tag': binascii.hexlify(tag).decode('utf-8'),
        'ciphertext': binascii.hexlify(ciphertext).decode('utf-8')
    })

    return encrypted_data

async def decrypt_private_key(encrypted_data_json: str, password: str) -> str:
    """
    Decrypts the AES-256-GCM encrypted private key.
    """
    try:
        encrypted_data = json.loads(encrypted_data_json)
        nonce = binascii.unhexlify(encrypted_data['nonce'])
        tag = binascii.unhexlify(encrypted_data['tag'])
        ciphertext = binascii.unhexlify(encrypted_data['ciphertext'])

        key = password.ljust(32, '0')[:32].encode('utf-8')

        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        decrypted_data = cipher.decrypt_and_verify(ciphertext, tag)

        return binascii.hexlify(decrypted_data).decode('utf-8')

    except (ValueError, KeyError, binascii.Error):
        raise Exception("Decryption failed. Invalid password or corrupt data.")



async def hash_identifier(email: str) -> str:
    """
    Hashes an email with the secret pepper so it
    can be stored and looked up deterministically.
    """
    # print("Thsis is pepper", PEPPER)
    print("Thsis is SALT", SALT)


    to_hash = (email.lower() + PEPPER + SALT).encode('utf-8')
    return hashlib.sha256(to_hash).hexdigest()
