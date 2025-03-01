import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

class CompletionExecutor:
    def __init__(self, host: str, api_key: str, request_id: str):
        self.host = host
        self.api_key = api_key
        self.request_id = request_id

    def execute(self, completion_request) -> str:
        headers = {
            'Authorization': self.api_key,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self.request_id,
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'text/event-stream'
        }

        final_result = ""
        is_result_event = False  # event:result 이벤트가 시작되었는지 여부

        # SSE 응답 스트림 처리
        with requests.post(
            self.host + '/testapp/v1/chat-completions/HCX-DASH-001',
            headers=headers,
            json=completion_request,
            stream=True
        ) as r:
            for line in r.iter_lines():
                if line:
                    decoded_line = line.decode("utf-8").strip()
                    if decoded_line.startswith("event:result"):
                        is_result_event = True
                    elif decoded_line.startswith("data:") and is_result_event:
                        final_result = decoded_line[len("data:"):].strip()
                        is_result_event = False
        return final_result

class ResumeExtract:
    """
    CLOVA API를 사용하여 텍스트 기반 이력서에서 career, activities, certifications 정보를 추출합니다.
    최종적으로 JSON 객체(파이썬 dict)를 반환합니다.
    """
    def __init__(self, host: str, request_id: str):
        # .env 파일에서 CLOVA_KEY를 가져와 Bearer 토큰 형식으로 설정합니다.
        api_key = "Bearer {}".format(os.getenv("CLOVA_KEY"))
        self.executor = CompletionExecutor(host, api_key, request_id)
        self.system_prompt = (
            '다음 사용자의 이력서에서 "career", "activities", "certifications" 정보를 추출하여 순수한 JSON 텍스트로 출력하세요.\n\n'
            '⚠️ 주의사항:\n'
            '- "career"는 이력서에 회사명과 직무(직무 제목)가 함께 명시된 경우에만 추출합니다. 만약 한 경력 항목에 여러 회사가 언급된다면, 각 회사를 별도의 career 항목으로 분리하여 "job"과 "company"를 명확하게 출력하세요. 해당 회사에서 수행한 업무 내역(담당 업무, 역할 등)이 명시되어 있다면 "description" 필드를 포함하고, 그렇지 않으면 생략합니다. 직무 경험이 명확하지 않으면 "career": []를 반환하세요.\n'
            '- "activities"는 동아리, 대외활동, 교육 과정(부트캠프 등)에서 **활동의 제목만** 추출합니다. 활동에 대한 세부 설명은 포함하지 마세요. 출력은 반드시 `{ "name": "활동명" }` 형태의 객체 배열로 반환하세요.\n'
            '- "certifications"는 자격증의 이름만 추출합니다. 취득일이나 발급기관 등의 추가 정보는 포함하지 마세요.\n'
            '- 경력사항의 세부 업무, 수상내역, 자기소개서 항목 등 기타 불필요한 내용은 모두 제외하세요.\n'
            '- 출력은 반드시 아래 JSON 예시와 동일한 형식이어야 하며, 추가적인 텍스트나 코드 블록 마크업 또는 HTML 태그가 포함되면 안 됩니다.\n'
            '- 모든 항목에 정보가 없으면 각각 빈 배열([])을 반환하세요.\n\n'
            '출력 예시 (반드시 이와 동일한 JSON 형식으로 출력):\n'
            '{\n'
            '  "career": [\n'
            '    {\n'
            '      "job": "예시 직무",\n'
            '      "company": "예시 회사",\n'
            '      "description": "예시 회사에서 수행한 직무 내역 (해당 내용이 있을 경우만 포함)"\n'
            '    },\n'
            '    {\n'
            '      "job": "예시 직무 2",\n'
            '      "company": "예시 회사 2"\n'
            '    }\n'
            '  ],\n'
            '  "activities": [\n'
            '    { "name": "예시 활동 제목 1" },\n'
            '    { "name": "예시 활동 제목 2" }\n'
            '  ],\n'
            '  "certifications": [\n'
            '    "예시 자격증 1",\n'
            '    "예시 자격증 2"\n'
            '  ]\n'
            '}'
        )

    def extract(self, resume_text: str) -> dict:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": resume_text}
        ]

        request_data = {
            'messages': messages,
            'topP': 0.8,
            'topK': 0,
            'maxTokens': 3000,
            'temperature': 0.5,
            'repeatPenalty': 5.0,
            'stopBefore': [],
            'includeAiFilters': True,
            'seed': 0
        }

        # API 요청하여 응답 받기
        raw_response = self.executor.execute(request_data)

        try:
            # 문자열 응답을 먼저 JSON으로 파싱
            response_dict = json.loads(raw_response)

            # message.content 필드에서 실제 JSON 추출
            if 'message' in response_dict and 'content' in response_dict['message']:
                content_str = response_dict['message']['content']
                # content 문자열을 다시 JSON으로 파싱
                content_json = json.loads(content_str)
                return content_json
            else:
                # 예상치 못한 응답 구조인 경우
                return {
                    "error": "Unexpected API response structure",
                    "career": [],
                    "activities": [],
                    "certifications": []
                }
        except json.JSONDecodeError as e:
            # JSON 파싱 실패 시 오류 정보 포함하여 반환
            return {
                "error": f"JSON parsing error: {str(e)}",
                "career": [],
                "activities": [],
                "certifications": []
            }
        except Exception as e:
            # 기타 예외 발생 시
            return {
                "error": f"Error processing API response: {str(e)}",
                "career": [],
                "activities": [],
                "certifications": []
            }