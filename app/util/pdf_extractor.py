from fastapi import UploadFile
import PyPDF2

class PDFExtractor:
    @staticmethod
    def extract_text_from_pdf(file: UploadFile) -> str:
        try:
            pdf_reader = PyPDF2.PdfReader(file.file)
            text = ""
            for page in range(pdf_reader.getNumPages()):
                text += pdf_reader.getPage(page).extract_text()

            return text
        except Exception as e:
            raise e

