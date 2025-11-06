from app.security.user_token import decode_access_token
from fastapi import HTTPException, Depends
from fastapi.security import APIKeyHeader, HTTPBearer
from app.dependecies.db import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from app.repo.user_repo import get_user
from app.repo.third_party_repo import ThirdPartyRepo
from app.schemas.user import UserRead


security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

async def get_current_user(
    token: str = Depends(security),
    db: AsyncSession = Depends(get_session),
):
    try:
        payload = await decode_access_token(token.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid access token payload, not valid")

        user = await get_user(user_id, db)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erorr getting current user. Full details: {e}")


async def get_current_user_safe(
    token: str = Depends(optional_security),
    db: AsyncSession = Depends(get_session),
):
    try:
        payload = await decode_access_token(token.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None

        user = await get_user(user_id, db)
        if not user:
            return None
        return user

    except Exception:
        return None
