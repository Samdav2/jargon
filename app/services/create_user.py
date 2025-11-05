from app.dependecies.user_encryption import generate_sovereign_identity, encrypt_private_key, decrypt_private_key
from app.schemas.user import UserCreate, UserProfileCreate, UserLogin, UserRead, UserLoginToken
from sqlmodel.ext.asyncio.session import AsyncSession
from app.repo.user_repo import save_user_to_db, save_user_profile_to_db, get_user_by_email
from app.dependecies.encrypt_user_data import decrypt_pw_key
from fastapi import HTTPException
from app.security.user_token import get_access_token
from bcrypt import checkpw

class CreateUserService:
    @staticmethod
    async def execute(user: UserCreate, db: AsyncSession):
        did = await generate_sovereign_identity()
        private_key = await encrypt_private_key(private_key_hex=did["private_key_hex"], user=user)
        await save_user_to_db(user, did["did"], private_key, db)
        return {"did": did["did"], "memonic":did["mnemonic_phrase"], "private_key": private_key}

    async def decrypt_user_pass(private_key_hex, password):
        result = await decrypt_private_key(encrypted_data_json=private_key_hex, password=password)
        return result

    async def create_user_profile(profile: UserProfileCreate, db: AsyncSession) -> UserRead:
        profile = await save_user_profile_to_db(profile, db)
        return profile

    async def user_login(user_details: UserLogin, db: AsyncSession):
        try:
            user = await get_user_by_email(user_details.username, db=db)
            if user:
                print("user_sample", user)
                if not checkpw(user_details.password.encode("utf-8"), user.login_password.encode("utf-8")):
                    raise HTTPException(detail=f"Incorrect User Pasword", status_code=401)
            else:
                raise HTTPException(detail=f"Incorrect email, User not found.", status_code=404)
        except Exception as e:
            raise HTTPException(detail=f"An error occured during user login. Full details: {e}", status_code=500)
        token = await get_access_token(str(user.id))

        refined_user = UserRead.model_validate(user.model_dump())
        return UserLoginToken(**refined_user.model_dump(), token=token
        )
