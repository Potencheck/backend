import os
from typing import Protocol, Dict, Any

from fastapi import UploadFile

from app.util.pdf_extractor import PDFExtractor
from app.util.completion_excute import ResumeExtract  # ResumeExtract 클래스 임포트


class CareerServiceInterface(Protocol):
    def extract_career_from_pdf(self, file: UploadFile) -> Dict[str, Any]:
        pass


class CareerService(CareerServiceInterface):
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        # ResumeExtract 클래스 사용
        self.resume_extractor = ResumeExtract(
            host='https://clovastudio.stream.ntruss.com',
            request_id='89dab0b98f924b67afbb3110e7835477'
        )

    def extract_career_from_pdf(self, file: UploadFile) -> Dict[str, Any]:
        # PDF에서 텍스트 추출
        text = self.pdf_extractor.extract_text_from_pdf(file)

        # 텍스트가 비어있는지 확인
        if not text.strip():
            return {
                "career": [],
                "activities": [],
                "certifications": []
            }

        # ResumeExtract를 사용하여 추출된 텍스트에서 경력 정보 등 추출
        return self.resume_extractor.extract(text)