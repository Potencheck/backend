from fastapi import FastAPI

from app.router.career_router import router as career_router
from app.router.user_router import router as user_router
from app.database import Base, engine
from dotenv import load_dotenv
app = FastAPI()


# 테이블 생성 보장
Base.metadata.create_all(bind=engine)

app.include_router(user_router)
app.include_router(career_router)
load_dotenv()
@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}