from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.services.create_user import CreateUserService, UserProfileCreate
from app.schemas.user import UserCreate, UserLoginToken, UserLogin, UserRead, UserProfileUpdate, NotificationCreate, NotificationUpdate
from sqlmodel.ext.asyncio.session import AsyncSession
from app.dependecies.db import get_session
from fastapi import Depends, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from app.dependecies.get_current_user import get_current_user, get_current_user_safe
from app.schemas.data_vault import Decision



router = APIRouter()

@router.post("/create_user", tags=["Users"], response_model = UserRead)
async def create_user(user: UserCreate, background_task: BackgroundTasks, db: AsyncSession = Depends(get_session)):
    result = await CreateUserService.execute(user, background_task, db)
    return result

@router.post("/decrypt_user", tags=["Users"])
async def decrypt_user(current_user = Depends(get_current_user)):
    result = await CreateUserService.decrypt_user_pass(private_key_hex=current_user.xxx_kkk, password=current_user.password)
    return result

@router.post("/create_user_profile", tags=["Users"])
async def create_user_profile(profile: UserProfileCreate, db: AsyncSession = Depends(get_session), current_user = Depends(get_current_user)):
    profile.user_id = current_user.id
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
async def send_email_verfication(background_task: BackgroundTasks, db: AsyncSession = Depends(get_session), current_user = Depends(get_current_user)):
    try:

        data = await CreateUserService.send_email_verication_x(user_did=current_user.user_did, background_task=background_task, db=db)

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
async def data_request_approve_reject(data_id: str, response: Decision,  background_task: BackgroundTasks, db: AsyncSession = Depends(get_session), current_user = Depends(get_current_user)):
    try:
        data = await CreateUserService.approve_reject(data_id=data_id, response=response, db=db, background_task=background_task)

    except Exception as e:
        raise HTTPException(detail=f"{e}", status_code=500)

    return data

@router.get("/get_user_profile", tags=["Users"])
async def get_user_profile(current_user = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    if current_user.id:
        user_profile = await CreateUserService.get_user_profile_service(user_id=str(current_user.id), db=db)
        return user_profile

@router.patch("/update_user_profile", tags=["Users"])
async def update_user_profile(profile_update: UserProfileUpdate, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    if current_user.id:
        user_profile_update = await CreateUserService.update_user_profile_service(profile_update=profile_update, user_id=str(current_user.id), db=db)
        return user_profile_update

@router.post("/create_user_notification", tags=["Users"])
async def create_user_notification(notification:NotificationCreate, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    if  notification and current_user:
        notification.user_id = current_user.id
        result = await  CreateUserService.create_notification_service(notification=notification, db=db)
        return result

@router.patch("/update_read_user_notification", tags=["Users"])
async def update_read_user_notification(notification:NotificationUpdate, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    if  notification and current_user:
        result = await  CreateUserService.update_or_read_notification_service(notification=notification, db=db)
        return result

@router.get("/get_user_notification", tags=["Users"])
async def get_user_notfication(current_user = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    if current_user:
        result = await CreateUserService.get_user_notfication_service(user_id=create_user.id, db=db)
        return result
