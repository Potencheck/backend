import logging
from typing import Protocol, Dict, Any, Union

from fastapi import UploadFile

from app.util.pdf_extractor import PDFExtractor
from app.util.completion_excute import ResumeExtract
from playwright.async_api import async_playwright
import asyncio

logger = logging.getLogger("app")


class CareerServiceInterface(Protocol):
    """경력 정보 추출 서비스의 인터페이스입니다."""
    def extract_str_from_pdf(self, file: UploadFile) -> str:
        pass

    def extract_str_from_url(self, link_url: str) -> str:
        pass
    def extract_career_from_pdf(self, file: UploadFile) -> Dict[str, Any]:
        """PDF에서 경력 정보를 추출합니다."""
        pass

    async def extract_career_from_url(self, link_url: str) -> Dict[str, Any]:
        """URL에서 경력 정보를 추출합니다."""
        pass


class CareerService:
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.resume_extractor = ResumeExtract(
            host='https://clovastudio.stream.ntruss.com',
            request_id='89dab0b98f924b67afbb3110e7835477'
        )
    def extract_str_from_pdf(self, file: UploadFile) -> str:
        return self.pdf_extractor.extract_text_from_pdf(file)

    def extract_str_from_url(self, link_url: str) -> str:
        return asyncio.run(self.async_crawler(link_url))

    def extract_career_from_pdf(self, file: UploadFile) -> Dict[str, Any]:
        text = self.pdf_extractor.extract_text_from_pdf(file)

        if not text.strip():
            logger.warning("PDF에서 추출된 텍스트가 없습니다.")
            return {
                "career": [],
                "activities": [],
                "certifications": []
            }

        return self.resume_extractor.extract(text)

    async def extract_career_from_url(self, url: str) -> Dict[str, Any]:
        text = await self.async_crawler(url)
        if not text or not text.strip():
            logger.warning(f"URL에서 추출된 텍스트가 없습니다: {url}")
            return {
                "career": [],
                "activities": [],
                "certifications": []
            }
        return self.resume_extractor.extract(text)

    async def async_crawler(self, url: str) -> Union[str, None]:
        logger.info(f"URL 접근 중: {url}")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-gpu',
                        '--disable-dev-shm-usage',
                        '--disable-setuid-sandbox',
                        '--no-sandbox',
                    ]
                )

                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                    device_scale_factor=1,
                )

                context.set_default_timeout(60000)
                page = await context.new_page()

                try:
                    if "notion.site" in url:
                        logger.debug("Notion 페이지 접근 중...")
                        await page.goto(url, wait_until="load", timeout=45000)
                        await page.wait_for_timeout(5000)

                        try:
                            await page.wait_for_selector("div.notion-page-content", timeout=10000)
                        except Exception:
                            pass
                    else:
                        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                    await self._scroll_page(page)
                    text = await self._extract_text_with_fallbacks(page)

                    if text and len(text.strip()) > 0:
                        logger.info(f"텍스트 추출 성공: {len(text)} 글자")
                        return text.strip()
                    else:
                        raise ValueError("텍스트 추출 실패")

                except Exception as e:
                    logger.error(f"페이지 접근 중 오류 발생: {str(e)}")
                    return None

                finally:
                    await browser.close()

        except Exception as e:
            logger.error(f"Playwright 실행 중 오류 발생: {str(e)}")
            return None

    async def _scroll_page(self, page):
        try:
            page_height = await page.evaluate("document.body.scrollHeight")
            view_height = await page.evaluate("window.innerHeight")

            if page_height > view_height:
                for i in range(0, page_height, view_height):
                    await page.evaluate(f"window.scrollTo(0, {i})")
                    await page.wait_for_timeout(300)

                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(500)

        except Exception as e:
            logger.debug(f"스크롤 중 오류: {str(e)}")

    async def _extract_text_with_fallbacks(self, page):
        # 방법 1: body.innerText
        try:
            text = await page.evaluate("document.body.innerText")
            if text and len(text.strip()) > 0:
                return text
        except Exception:
            pass

        # 방법 2: 모든 텍스트 노드 추출
        try:
            text = await page.evaluate("""
            Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, p, li, td, th, span, div, a'))
                .map(el => el.textContent)
                .filter(text => text.trim().length > 0)
                .join('\\n')
            """)
            if text and len(text.strip()) > 0:
                return text
        except Exception:
            pass

        # 방법 3: Notion 특화 선택자
        if "notion.site" in page.url:
            try:
                text = await page.evaluate("""
                Array.from(document.querySelectorAll('.notion-page-content *'))
                    .map(el => el.textContent)
                    .filter(text => text.trim().length > 0)
                    .join('\\n')
                """)
                if text and len(text.strip()) > 0:
                    return text
            except Exception:
                pass

        # 방법 4: HTML 내용으로부터 텍스트 추출
        try:
            import re
            from bs4 import BeautifulSoup

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text()
            text = text.strip()

            # 중복된 공백 제거
            text = re.sub(r'\s+', ' ', text)
            # 중복된 빈 줄 제거
            text = re.sub(r'\n\s*\n', '\n\n', text)

            if text and len(text.strip()) > 0:
                return text
        except Exception:
            pass

        return ""