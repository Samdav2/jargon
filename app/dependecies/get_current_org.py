from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from sqlmodel.ext.asyncio.session import AsyncSession
from jose import JWTError, ExpiredSignatureError
from app.security.user_token import decode_access_token
from app.dependecies.db import get_session
from app.model.user import User
from app.repo.third_party_repo import ThirdPartyRepo
from app.schemas.third_party import ThirdPartyRead

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

async def get_current_org(
    token: str = Depends(security),
    db: AsyncSession = Depends(get_session),
):

    repo = ThirdPartyRepo(db)
    try:
        payload = await decode_access_token(token.credentials)
        org_id = payload.get("sub")
        if not org_id:
            raise HTTPException(status_code=401, detail="Invalid access token payload, not valid")

        org = await repo.get_by_org_id(org_id)
        if not org:
            raise HTTPException(status_code=401, detail="User not found")
        return org

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erorr getting current user. Full details: {e}")


async def get_current_org_safe(
    token: str = Depends(optional_security),
    db: AsyncSession = Depends(get_session),
):
    repo = ThirdPartyRepo(db)

    try:
        payload = await decode_access_token(token.credentials)
        org_id = payload.get("sub")
        if not org_id:
            return None

        org = await repo.get_by_org_id(org_id)
        if not org:
            return None
        return org

    except Exception:
        return None
