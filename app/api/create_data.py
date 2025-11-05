from fastapi import APIRouter, HTTPException, BackgroundTasks
from services.data_vault import save_user_data_vault, get_user_data_service, approve_reject
from schemas.data_vault import UserDataVautltCreate, GetUserData, Decision
from sqlmodel.ext.asyncio.session import AsyncSession
from dependecies.db import get_session
from fastapi import Depends
from uuid import UUID


router = APIRouter(prefix="/data_vault", tags=["Data Vault"])

@router.post("/save_data_vault")
async def create_data_vault_entry(data_vault_create: UserDataVautltCreate, db: AsyncSession = Depends(get_session)):
    result = await save_user_data_vault(data_vault_create, db)
    return result

@router.post("/get_user_data")
async def get_user_data_api(data_request: GetUserData, db: AsyncSession = Depends(get_session)):
    try:
        user_data = await get_user_data_service(data_request=data_request, db=db)

    except Exception as e:
        raise HTTPException(detail=f"Error Gettin User Data. Full details: {e}", status_code=500)
    return user_data

@router.patch("/approve_reject")
async def data_vic_approve_reject(data_id: str, response: Decision,  background_task: BackgroundTasks, db: AsyncSession = Depends(get_session)):
    try:
        data = await approve_reject(data_id=data_id, response=response, db=db, background_task=background_task)

    except Exception as e:
        raise HTTPException(detail=f"{e}", status_code=500)

    return data
