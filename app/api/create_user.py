from fastapi import APIRouter
from app.services.create_user import CreateUserService, UserProfileCreate
from app.schemas.user import UserCreate, UserLoginToken, UserLogin
from sqlmodel.ext.asyncio.session import AsyncSession
from app.dependecies.db import get_session
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter()

@router.post("/create_user", tags=["Users"])
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_session)):
    result = await CreateUserService.execute(user, db)
    return result

@router.post("/decrypt_user", tags=["Users"])
async def decrypt_user(private_key: str, password: str):
    result = await CreateUserService.decrypt_user_pass(private_key_hex=private_key, password=password)
    return result

@router.post("/create_user_profile", tags=["Users"])
async def create_user_profile(profile: UserProfileCreate, db: AsyncSession = Depends(get_session)):
    profile = await CreateUserService.create_user_profile(profile, db)
    return {"status": "profile created", "profile": profile }

@router.post("/user_login", response_model=UserLoginToken, tags=["Users"])
async def user_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_session)
):
    """
    Endpoint for user login with jwt token
    """

    user_info = UserLogin.model_validate({
        "username": form_data.username,
        "password": form_data.password
    })

    user = await CreateUserService.user_login(user_info, db=db)
    return user
