from fastapi import FastAPI, APIRouter
from api.create_user import router as create_user_router
from api.create_data import router as create_data_router
from api.third_party import router as third_party_router
import uvicorn
from dependecies.db import init_db
from contextlib import asynccontextmanager
from model.user import User, UserProfile
from model.third_party import ThirdPartyVerification, ThirdParty


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan,
              title="Jargon",
              )

app.include_router(create_user_router, prefix="/api")
app.include_router(create_data_router, prefix="/api")
app.include_router(third_party_router, prefix="/api")


@app.get("/")
async def read_root():
    return {"Hello": "World"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
