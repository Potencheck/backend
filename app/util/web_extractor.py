import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

logger = logging.getLogger("app")

class WebExtractor:
    @staticmethod
    def extract_text_from_url(url: str) -> str:
        """
        URL에서 웹 페이지 콘텐츠를 가져와 텍스트를 추출합니다.
        
        Args:
            url: 텍스트를 추출할 웹 페이지의 URL
            
        Returns:
            추출된 텍스트
        """
        try:
            # URL 유효성 검사
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                logger.error(f"유효하지 않은 URL: {url}")
                raise ValueError(f"유효하지 않은 URL: {url}")
            
            # 웹 페이지 요청
            logger.info(f"웹 페이지 요청: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # 4xx, 5xx 응답 확인
            
            # 콘텐츠 타입 확인
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                logger.warning(f"웹 페이지가 HTML이 아닙니다. Content-Type: {content_type}")
            
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 불필요한 요소 제거
            for tag in soup(["script", "style", "meta", "noscript", "header", "footer", "aside"]):
                tag.extract()
            
            # 텍스트 추출 및 정리
            text = soup.get_text(separator=' ', strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = "\n".join(lines)
            
            total_text_length = len(text)
            logger.info(f"웹 페이지에서 추출된 텍스트 길이: {total_text_length} 문자")
            
            return text
            
        except requests.RequestException as e:
            logger.error(f"웹 페이지 요청 중 오류: {str(e)}")
            raise ValueError(f"웹 페이지를 불러올 수 없습니다: {str(e)}")
        except Exception as e:
            logger.error(f"웹 페이지 처리 중 오류: {str(e)}")
            raise ValueError(f"웹 페이지 처리 중 오류: {str(e)}") 