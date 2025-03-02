from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware
from app.router.report_router import router as report_router
from app.router.career_router import router as career_router
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

app.include_router(career_router)
app.include_router(report_router)
load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://frontend-delta-ruddy.vercel.app",
        "http://potencheck.site",
        "https://api.potencheck.site",
        "https://potenday.potencheck.site"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
async def root():
    return {"message": "Hello World"}

