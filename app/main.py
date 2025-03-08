from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware
from app.router.report_router import router as report_router
from app.router.career_router import router as career_router
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(
    title="PotenCheck API",
    description="경력 분석 보고서 생성 및 관리를 위한 API",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "report",
            "description": "이력서 분석 및 보고서 생성 관련 API"
        },
        {
            "name": "career",
            "description": "경력 정보 관련 API"
        }
    ]
)

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

