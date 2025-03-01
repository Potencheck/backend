import logging
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.report_schema import CareerInputSchema, ReportInput, Report


router = APIRouter(
    prefix="/report",
    tags=["report"]
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("app")

@router.post("/")
async def create_report(
        career: CareerInputSchema
) -> Dict:
    pass

@router.post("/share")
async def share_report(
        report_input: ReportInput
) -> Dict:
    pass

@router.get("/{report_id}", response_model=Report)
async def get_report(
        report_id: str
) -> Report:
    pass