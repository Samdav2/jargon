from app.schemas.data_vault import UserDataVautltCreate, UserDataVaultUpdate, GetUserData
from sqlmodel.ext.asyncio.session import AsyncSession
from app.model.user import UserDataVault
from uuid import uuid4
from fastapi import HTTPException
from app.repo.user_repo import get_user
from app.dependecies.encrypt_user_data import decrypt_private_key as decrypt_xk, encrypt_data_with_public_key, get_public_key_from_private, decrypt_data_with_private_key, decrypt_pw_key
from app.repo.data_vault_repo import save_user_data_to_db, get_user_data
from app.dependecies.user_encryption import decrypt_private_key
import base64
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("VOID_PW")

async def save_user_data_vault(data_vault_create: UserDataVautltCreate, db: AsyncSession):
    try:
        user = await get_user(data_vault_create.user_id, db)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while verifying user existence: {str(e)}")

    else:
        try:
            xxx_kkk = user.xxx_kkk
            pwx = await decrypt_pw_key(user.password, token=TOKEN)
            decrypt_xxx_kkk = await decrypt_xk(xxx_kkk)
            token = await decrypt_private_key(decrypt_xxx_kkk, pwx)
            print("Decryp KK", decrypt_xxx_kkk)
            print("token", token)

        except Exception as e:
            raise HTTPException(detail=f"Error verifying user xxx_kkk. Full details {e}", status_code=403)

        else:
            public_key = get_public_key_from_private(token)
            encrypted_data_xk = encrypt_data_with_public_key(
                data_bytes=data_vault_create.encrypted_data.encode("utf-8"), public_key_hex= public_key
                )

            data_vault_create.encrypted_data = base64.b64encode(encrypted_data_xk).decode("utf-8")
            try:
                result = await save_user_data_to_db(data_vault_create, db)
                return {"Message": "Data Saved Successfully"}
            except Exception as e:
                raise  HTTPException(detail=f"Error Saving Data. Full details {e} ", status_code=500)

async def get_user_data_service(data_request: GetUserData, db: AsyncSession):
    data_list = []
    try:
        user_details = await get_user_data(data_request, db)
        user = user_details["user"]
        data = user_details["data"]
        print("user Data Sample", data)


    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while verifying user existence: {str(e)}")

    else:
        try:
            xxx_kkk = user.xxx_kkk
            pwx = await decrypt_pw_key(user.password, token=TOKEN)
            decrypt_xxx_kkk = await decrypt_xk(xxx_kkk)
            token = await decrypt_private_key(decrypt_xxx_kkk, pwx)
            print("Decryp KK", decrypt_xxx_kkk)
            print("token", token)


        except Exception as e:
            raise HTTPException(detail=f"Error verifying user xxx_kkk. Full details {e}", status_code=403)

        else:
            try:
                for d in data:
                    print(f"data loop, {d}")
                    user_data = await decrypt_data_with_private_key(encrypted_jargon=d.encrypted_data, private_key_hex=token)
                    data_list.append({"Data Type": d.data_type, "Data": user_data, "Created At": d.created_at, "Updated At": d.updated_at})
            except Exception as e:
                raise HTTPException(detail=f"Error Decrypting User Data. Full details: {e}", status_code=500)
            return data_list
