from fastapi import APIRouter, BackgroundTasks, HTTPException
from services.create_user import CreateUserService, UserProfileCreate
from schemas.user import UserCreate, UserLoginToken, UserLogin, UserRead
from sqlmodel.ext.asyncio.session import AsyncSession
from dependecies.db import get_session
from fastapi import Depends, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from dependecies.get_current_user import get_current_user, get_current_user_safe
from schemas.data_vault import Decision



router = APIRouter()

@router.post("/create_user", tags=["Users"])
async def create_user(user: UserCreate, background_task: BackgroundTasks, db: AsyncSession = Depends(get_session)):
    result = await CreateUserService.execute(user, background_task, db)
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

@router.put("/verify_email", tags=["Users"])
async def verify_user_email(token: str, background_task: BackgroundTasks, db: AsyncSession = Depends(get_session)):
    try:
        data = await CreateUserService.verify_email(token=token, background_task=background_task, db=db)

    except Exception as e:
        raise HTTPException(detail=f"{e}", status_code=500)
    if data:
        return {"message":"Email Verified Successfully"}


@router.post("/send_email_verification", tags=["Users"])
async def send_email_verfication(user_did: str, background_task: BackgroundTasks, db: AsyncSession = Depends(get_session)):
    try:

        data = await CreateUserService.send_email_verication_x(user_did=user_did, background_task=background_task, db=db)

    except Exception as e:
        raise HTTPException(detail=f"{e}", status_code=500)
    if data:
        return {"message":"Email Sent Successfully"}


@router.put("/change_password", tags=["Users"])
async def chnage_user_password(new_pass: str, token: str, background_task: BackgroundTasks,  db: AsyncSession = Depends(get_session)):
    try:
        result = await CreateUserService.change_pass_service(token=token, user_pass=new_pass, db=db, background_task=background_task)
        return result
    except Exception as e:
        raise HTTPException(detail=f"{e}", status_code=500)

@router.put("/change_password_email", tags=["Users"])
async def password_reset_link(
    background_task: BackgroundTasks,
    email: str = None,
    current_user: UserRead = Depends(get_current_user_safe),
    db: AsyncSession = Depends(get_session)
    ):

    if current_user == None:
        if email:
            user = await CreateUserService.get_user_by_email_service(email, db)
            await CreateUserService.send_email_pass_email(user, background_task)
            return {"message":"Password Link SuccessfullY Sent"}

    else:
        try:
            print("This is me", current_user.name)
            await CreateUserService.send_email_pass_email(current_user, background_task)
            return {"message":"Password Link SuccessfullY Sent"}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error Sending Pass Reset Link. Full details: {e}")


@router.post("/get_user_vic_data", tags=["Users"])
async def get_user_vic_data_input_request(db: AsyncSession = Depends(get_session), user = Depends(get_current_user)):
    if user:
        try:
            user_vic_data = await CreateUserService.get_vic_request(user_id=user.id, db=db)
        except Exception as e:
            raise HTTPException(detail=f"{e}", status_code=500)

        return user_vic_data

@router.get("/get_thirdparty_data_requests", tags=["Users"])
async def get_third_party_data_request(db: AsyncSession = Depends(get_session), user = Depends(get_current_user)):
    if user:
        try:
            third_party_request = await CreateUserService.get_thirdparty_data_request(email=user.email, db=db)
        except Exception as e:
            raise HTTPException(detail=f"{e}", status_code=500)

        return third_party_request

@router.patch("/approve_reject", tags=["Users"])
async def data_request_approve_reject(data_id: str, response: Decision,  background_task: BackgroundTasks, db: AsyncSession = Depends(get_session)):
    try:
        data = await CreateUserService.approve_reject(data_id=data_id, response=response, db=db, background_task=background_task)

    except Exception as e:
        raise HTTPException(detail=f"{e}", status_code=500)

    return data
