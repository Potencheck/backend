import os
from fastapi import UploadFile
from pydantic.v1 import Protocol

from app.util.completion_excute import CompletionExecutor
from app.util.pdf_extractor import PDFExtractor


class CareerServiceInterface(Protocol):
    def extract_career_from_pdf(self, file: UploadFile) -> str:
        pass


class CareerService:
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.completion_executor = CompletionExecutor(
            host='https://clovastudio.stream.ntruss.com',
            api_key='Bearer {}'.format(os.getenv("CLOVA_KEY")),
            request_id='89dab0b98f924b67afbb3110e7835477'
        )

    def extract_career_from_pdf(self, file: UploadFile) -> str:
        text = self.pdf_extractor.extract_text_from_pdf(file)
        return self.completion_executor.execute(text)