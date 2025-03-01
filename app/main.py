from fastapi import FastAPI

from app.router.report_router import router as report_router
from app.router.career_router import router as career_router
from dotenv import load_dotenv
app = FastAPI()

app.include_router(career_router)
app.include_router(report_router)
load_dotenv()
@app.get("/")
async def root():
    return {"message": "Hello World"}
