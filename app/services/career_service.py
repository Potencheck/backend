import os
import logging
from typing import Protocol, Dict, Any

from fastapi import UploadFile

from app.util.pdf_extractor import PDFExtractor
from app.util.completion_excute import ResumeExtract  # ResumeExtract 클래스 임포트
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 로거 설정
logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


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
            logger.warning("PDF에서 추출된 텍스트가 없습니다.")
            return {
                "career": [],
                "activities": [],
                "certifications": []
            }

        # ResumeExtract를 사용하여 추출된 텍스트에서 경력 정보 등 추출
        return self.resume_extractor.extract(text)

    def extract_career_from_url(self, url: str) -> Dict[str, Any]:
        # URL에서 페이지 텍스트 추출
        text = self.crawler(url)
        if not text.strip():
            logger.warning(f"URL에서 추출된 텍스트가 없습니다: {url}")
            return {
                "career": [],
                "activities": [],
                "certifications": []
            }
        # 추출된 텍스트로부터 경력 정보를 가져옴
        return self.resume_extractor.extract(text)

    def crawler(self, url: str) -> str:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        try:
            service = Service(executable_path="/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
            logger.info("ChromeDriver 실행 성공")
        except Exception as e:
            logger.error(f"ChromeDriver 실행 오류: {e}")
            return ""

        try:
            driver.get(url)
            logger.info(f"URL 접근 중: {url}")

            # Explicit Wait (최대 10초 대기)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            body = driver.find_element(By.TAG_NAME, "body")
            text = body.text.strip()

            if not text:
                raise ValueError("페이지에서 텍스트를 추출하지 못했습니다.")

            logger.info(f"텍스트 추출 성공: {len(text)} 글자")
            return text

        except Exception as e:
            logger.error(f"크롤링 중 오류 발생: {e}")
            return ""

        finally:
            driver.quit()
            logger.info("ChromeDriver 종료")