from jose import jwt
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any
from datetime import timedelta, datetime, timezone
from fastapi import HTTPException
from pathlib import Path
import asyncio


PRIVATE_KEY = Path("./jgxxkkprivate.pem").read_text()
PUBLIC_KEY = Path("./jgxxkkpublic.pem").read_text()

load_dotenv()

ALGORITHM = os.getenv("ALGORITHM")
USER_TOKEN_EXPIRE_TIME = os.getenv("USER_TOKEN_EXPIRE_MINUTE")


async def get_access_token(subject: str, data: Dict[str, Any] = None, expire: timedelta = None) -> str:
    to_encode = {"sub": subject}

    if data:
        to_encode.update(data)

    expire_time = datetime.now(timezone.utc) + (expire or(timedelta(minutes=int(USER_TOKEN_EXPIRE_TIME))))
    to_encode.update({"exp": expire_time})
    return jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)


async def decode_access_token(token: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM], options = options)
        return payload
    except Exception as e:
        raise HTTPException(detail=f"Error Decoding Token. Full details{e}", status_code=500)
