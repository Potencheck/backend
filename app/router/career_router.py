import json
import logging
from typing import Dict, Any, Union

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File

from app.dependencies.dependency import get_career_service
from app.services.career_service import CareerServiceInterface

router = APIRouter(
    prefix="/career",
    tags=["career"]
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("app")

@router.post("/extract")
async def extract_career_from_resume(
        file: UploadFile = File(...),
        career_service: CareerServiceInterface = Depends(get_career_service)
) -> Dict[str, Any]:
    """
    Upload a PDF resume file and extract career, activities, and certifications information.

    Returns:
        JSON object containing extracted career, activities, and certifications.
    """
    logger.info(f"Received file: {file.filename}")
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        # Extract career info from the PDF
        logger.info("Extracting career information from the PDF file...")
        result = career_service.extract_career_from_pdf(file)

        # 타입에 따라 다르게 처리
        logger.info("Parsing the extracted result...")
        if isinstance(result, dict):
            # 이미 딕셔너리인 경우 그대로 반환
            return result
        elif isinstance(result, str):
            # 문자열인 경우 JSON으로 파싱 시도
            try:
                parsed_result = json.loads(result)
                return parsed_result
            except json.JSONDecodeError:
                # 유효한 JSON이 아닌 경우
                return {"error": "Invalid JSON response", "raw_result": result}
        else:
            # 예상치 못한 타입인 경우
            return {"error": "Unexpected result type", "raw_result": str(result)}

    except Exception as e:
        logger.error(f"Error processing the file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing the file: {str(e)}")