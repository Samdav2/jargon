from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from app.dependecies.db import get_session
from app.schemas.third_party import ThirdPartyCreate, ThirdPartyRegistrationResponse, ThirdPartyUpdate, ThirdPartyRead, ThirdPartyApiKeyResponse, ThirdPartyTokenResponse, ThirdPartyLogin
from app.services.third_party_service import ThirdPartyService
from sqlmodel.ext.asyncio.session import AsyncSession
from uuid import UUID

router = APIRouter()

@router.post(
    "/register",
    response_model=ThirdPartyRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Third-Party Organization",
    tags=["Third Parties"]
)
async def register_third_party(
    org_create: ThirdPartyCreate,
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
        response = await service.register_new_organization(org_create)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )

@router.get("/get_all_third_parties", tags=["Third Parties"])
async def get_all_third_parties(session: AsyncSession = Depends(get_session)):
    service = ThirdPartyService(session)

    try:
        third_parties = await service.get_all_thirdparties()
    except Exception as e:
        raise HTTPException(detail=f"{e}", status_code=500)

    return third_parties

@router.put(
    "/me",
    response_model=ThirdPartyRead,
    tags=["Organization Management"]
)
async def update_organization_me(
    update_data: ThirdPartyUpdate,
    session: Session = Depends(get_session)
):
    """
    Update the contact details for the currently logged-in organization.
    """
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
