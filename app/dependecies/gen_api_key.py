import secrets

async def generate_api_key(prefix="jargon_encryption"):
    """
    Generates a new API key with a prefix and returns the
    plain-text key (to show to the user) and its SHA-256 hash (to store).
    """
    token = secrets.token_urlsafe(32)

    plain_text_key = f"{prefix}_{token}"
    return plain_text_key
