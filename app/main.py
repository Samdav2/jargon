from fastapi import FastAPI, APIRouter
from app.api.create_user import router as create_user_router
from app.api.create_data import router as create_data_router
from app.api.third_party import router as third_party_router
import uvicorn
from app.dependecies.db import init_db
from contextlib import asynccontextmanager
from app.model.user import User, UserProfile
from app.model.third_party import ThirdPartyVerification, ThirdParty
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan,
              title="Jargon",
              )

origins = [
    "http://localhost:3000",
    "http://localhost",
    "http://127.0.0.1",
    "https://jargon-frontend.vercel.app/",
    "https://www.jargon-frontend.vercel.app/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(create_user_router, prefix="/api")
app.include_router(create_data_router, prefix="/api")
app.include_router(third_party_router, prefix="/api")


@app.get("/")
async def read_root():
    return {"Hello": "World"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
