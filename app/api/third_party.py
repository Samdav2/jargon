from fastapi import APIRouter, Depends, HTTPException, status, Form, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from app.dependecies.db import get_session
from app.schemas.third_party import ThirdPartyCreate, ThirdPartyRegistrationResponse, ThirdPartyUpdate, ThirdPartyRead, ThirdPartyApiKeyResponse, ThirdPartyTokenResponse, ThirdPartyLogin, ThirdPartytDataVaultEmail, ThirdPartyUpdateRead
from app.services.third_party_service import ThirdPartyService
from sqlmodel.ext.asyncio.session import AsyncSession
from uuid import UUID
from app.repo.data_vault_repo import get_data_by_type, decrypt_user_tk_data
from app.dependecies.get_current_org import get_current_org, get_current_org_safe

router = APIRouter(prefix="/org")

@router.post(
    "/register",
    response_model=ThirdPartyRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Third-Party Organization",
    tags=["Organizations"]
)


async def register_third_party(
    org_create: ThirdPartyCreate,
    background_task: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Endpoint for a new organization (bank, firm, govt) to register
    for SDE access.

    This endpoint accepts the organization's details and their
    initial verification (KYC/KYB) documents.

    On success, the organization is created with a status of
    **'un_approved'** and awaits administrative review.
    """
    service = ThirdPartyService(session)

    try:
        response = await service.register_new_organization(org_create, background_task)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )

@router.get("/get_all_third_parties", tags=["Organizations"])
async def get_all_third_parties(session: AsyncSession = Depends(get_session)):
    service = ThirdPartyService(session)

    try:
        third_parties = await service.get_all_thirdparties()
    except Exception as e:
        raise HTTPException(detail=f"{e}", status_code=500)

    return third_parties

@router.put(
    "/me",
    response_model=ThirdPartyUpdateRead,
    tags=["Organization Management"]
)
async def update_organization_me(
    update_data: ThirdPartyUpdate,
    session: Session = Depends(get_session),
    current_org = Depends(get_current_org)
):
    """
    Update the contact details for the currently logged-in organization.
    """
    update_data.org_id = current_org.id
    service = ThirdPartyService(session)
    return await service.update_organization_info(update_data)

@router.post(
    "/admin/approve/{org_id}",
    response_model=ThirdPartyApiKeyResponse,
    tags=["Admin"]
)
async def approve_organization(
    org_id: UUID,
    session: AsyncSession = Depends(get_session),
    # admin_user: Any = Depends(get_current_admin_user)
):
    """
    [ADMIN-ONLY]
    Approve an organization's registration.

    This sets their status to 'approved' and generates their first
    API key, which is returned *one time* in the response.
    """
    service = ThirdPartyService(session)
    return await service.approve_organization(org_id)
@router.delete(
    "/delete_third_party/{ord_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Organization Management"]
)

async def delete_organization_me(
    org_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Delete the currently logged-in organization's account.
    (This is a destructive, irreversible action).
    """
    service = ThirdPartyService(session)
    return await service.delete_organization(org_id)

@router.post(
    "/login",
    response_model=ThirdPartyTokenResponse,
    tags=["Organizations"]
)
async def login_organization(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """
    Endpoint for an organization's dashboard login.
    Returns a JWT for session management.
    """

    user_info = ThirdPartyLogin.model_validate({
        "username": form_data.username,
        "password": form_data.password
    })

    service = ThirdPartyService(session)
    return await service.login_organization(user_info)


@router.post("/get_user_data", tags=["Organizations"])
async def get_data_by_user_type(
    description: str,
    email: str,
    data_type: list[str],
    background_task: BackgroundTasks,
    minutes: int,
    org = Depends(get_current_org),
    db: AsyncSession = (Depends(get_session)),
    current_org = Depends(get_current_org)
    ):
    try:
        service = ThirdPartyService(db)
        data = await service.get_data_by_type_service(
            org_id=str(current_org.id),
            description=description,
            email=email,
            data_type=data_type,
            db=db,
            expire=minutes,
            org_name = org.organization_name,
            background_task=background_task
            )
        return data
    except Exception as e:
        raise HTTPException(detail=f"Error getting User data: Full details {e}", status_code=500)

@router.post("/detokenize_data", tags=["Organizations"])
async def detokenize(token: str, current_org = Depends(get_current_org), db: AsyncSession = Depends(get_session)):
    if current_org.status != "approved":
        raise HTTPException(detail=f"You Must Be Approved To Use This Service", status_code=403)

    service = ThirdPartyService(db)
    detokenized_data = await  service.detonize_user_data_service(token)
    return detokenized_data


@router.get("/decrypt_user_request_data", tags=["Organizations"])
async def decrypt_request_data(email: str, db: AsyncSession = Depends(get_session), current_org = Depends(get_current_org)):
    if current_org.status != "approved":
        raise HTTPException(f"You Must Be Approved To Use This Service")
    try:
        service = ThirdPartyService(db)
        decrypted_user_data = await service.decrypt_data_request(email, str(current_org.id), db)
        return decrypted_user_data
    except Exception as e:
        raise HTTPException(detail=f"{e}", status_code=500)


@router.post("/add_user_vic_data", tags=["Organizations"])
async def add_user_vic_data(vic_data: ThirdPartytDataVaultEmail, db: AsyncSession = Depends(get_session), current_org = Depends(get_current_org)):
    if vic_data:
        vic_data.added_by = current_org.id
        vic_data.org_name = current_org.organization_name
        service = ThirdPartyService(db)
        try:
            user_vic_data = await service.adding_user_vic(data_vic=vic_data, db=db)
        except Exception as e:
            raise HTTPException(detail=f"{e}", status_code=500)

        return user_vic_data

@router.post("/get_user_vic_data", tags=["Organizations"])
async def get_user_vic_data_request(db: AsyncSession = Depends(get_session), current_org = Depends(get_current_org)):
    if current_org.id:
        service = ThirdPartyService(db)
        try:
            user_vic_data = await service.get_vic_request(org_id=current_org.id, db=db)
        except Exception as e:
            raise HTTPException(detail=f"{e}", status_code=500)

        return user_vic_data

@router.put("/verify_email", tags=["Organizations"])
async def verify_org_email(
    token: str,
    background_task: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    ):
    service = ThirdPartyService(db)
    try:
        data = await service.verify_email_service(token=token, background_task=background_task, db=db)

    except Exception as e:
        raise HTTPException(detail=f"{e}", status_code=500)
    if data:
        return {"message":"Email Verified Successfully"}


@router.post("/send_email_verification", tags=["Organizations"])
async def send_email_verfication(background_task: BackgroundTasks, org = Depends(get_current_org),  db: AsyncSession = Depends(get_session)):
    service = ThirdPartyService(db)
    try:

        data = await service.send_email_verication_x(org_id=org.id, background_task=background_task, db=db)

    except Exception as e:
        raise HTTPException(detail=f"{e}", status_code=500)
    if data:
        return {"message":"Email Sent Successfully"}


@router.put("/change_password", tags=["Organizations"])
async def chnage_user_password(new_pass: str, token: str,  background_task: BackgroundTasks, db: AsyncSession = Depends(get_session)):
    service = ThirdPartyService(db)

    try:
        result = await service.change_pass_service(token=token, org_pass=new_pass, db=db, background_task=background_task)
        return result
    except Exception as e:
        raise HTTPException(detail=f"{e}", status_code=500)

@router.put("/change_password_email", tags=["Organizations"])
async def password_reset_link(
    background_task: BackgroundTasks,
    email: str = None,
    current_org: ThirdPartyRead = Depends(get_current_org_safe),
    db: AsyncSession = Depends(get_session)
    ):
    service = ThirdPartyService(db)

    if current_org == None:
        if email:
            org = await service.get_org_by_email_service(email, db)
            await service.send_email_pass_email(org, background_task)
            return {"message":"Password Link SuccessfullY Sent"}

    else:
        try:
            await service.send_email_pass_email(current_org, background_task)
            return {"message":"Password Link SuccessfullY Sent"}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error Sending Pass Reset Link. Full details: {e}")

@router.get("/get_org_stat", tags=["Organizations"])
async def get_org_full_stats(current_org = Depends(get_current_org), db: AsyncSession = Depends(get_session)):
    if current_org:
        service = ThirdPartyService(db)

        stats = await service.get_organization_stats(org_id=str(current_org.id), db=db)
        return stats
