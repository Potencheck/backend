import logging
from fastapi import UploadFile
import PyPDF2

logger = logging.getLogger("app")


class PDFExtractor:
    @staticmethod
    def extract_text_from_pdf(file: UploadFile) -> str:
        try:
            # 파일 내용을 읽고 포인터 위치 리셋
            file_content = file.file.read()
            file.file.seek(0)

            logger.info(f"PDF 파일 크기: {len(file_content)} 바이트")

            # PDF 읽기
            pdf_reader = PyPDF2.PdfReader(file.file)
            page_count = len(pdf_reader.pages)
            logger.info(f"PDF 페이지 수: {page_count}")

            if page_count == 0:
                logger.warning("PDF에 페이지가 없습니다.")
                return ""

            text = ""
            for i, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text() or ""
                    text += page_text
                    logger.info(f"페이지 {i + 1} 텍스트 길이: {len(page_text)} 문자")
                except Exception as page_error:
                    logger.error(f"페이지 {i + 1} 텍스트 추출 오류: {str(page_error)}")

            # 추출된 텍스트 로깅
            total_text_length = len(text)
            logger.info(f"전체 추출된 텍스트 길이: {total_text_length} 문자")

            if total_text_length == 0:
                logger.warning("PDF에서 텍스트를 추출할 수 없습니다. 이미지 기반 PDF일 수 있습니다.")
            elif total_text_length < 100:
                logger.info(f"추출된 텍스트 샘플: {text}")

            # 파일 포인터 위치 리셋
            file.file.seek(0)
            return text

        except Exception as e:
            logger.error(f"PDF 처리 중 오류 발생: {str(e)}")
            raise e