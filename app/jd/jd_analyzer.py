import csv
import json
import re
import time
import requests
from collections import defaultdict
import os
import argparse
import pandas as pd
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class CompletionExecutor:
    def __init__(self, host, api_key=None, request_id=None):
        # host에 스킴이 있는지 확인하고 없으면 추가
        if not host.startswith(('http://', 'https://')):
            self._host = 'https://' + host
        else:
            self._host = host
            
        # API 키가 제공되지 않으면 환경 변수에서 로드
        if api_key is None:
            clova_key = os.getenv('CLOVA_KEY')
            if clova_key:
                self._api_key = f'Bearer {clova_key}'
            else:
                raise ValueError("CLOVA_KEY 환경 변수가 설정되지 않았습니다.")
        else:
            self._api_key = api_key
            
        if request_id is None:
            self._request_id = 'jd-analyzer-' + str(int(time.time()))
        else:
            self._request_id = request_id

    def execute(self, completion_request, stream=False):
        """Chat Completions API를 호출하여 응답을 받습니다."""
        headers = {
            'Authorization': self._api_key,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'text/event-stream'
        }

        try:
            url = self._host + '/testapp/v1/chat-completions/HCX-003'
            print(f"API 요청 URL: {url}")
            
            with requests.post(url, headers=headers, json=completion_request, stream=True) as r:
                print(f"응답 상태 코드: {r.status_code}")
                
                if r.status_code != 200:
                    print(f"API 오류 응답: {r.text[:500]}")
                    return None
                    
                r.raise_for_status()
                
                if stream:
                    # 스트리밍 모드면 그대로 출력
                    for line in r.iter_lines():
                        if line:
                            print(line.decode("utf-8"))
                    return None
                else:
                    # 스트리밍 모드가 아니면 전체 응답 누적
                    full_response = ""
                    last_full_content = None  # 마지막으로 받은 전체 콘텐츠
                    
                    for line in r.iter_lines():
                        if line:
                            decoded_line = line.decode("utf-8")
                            # 디버그 메시지 제거
                            # print(f"디버그: 응답 라인 - {decoded_line[:100]}")
                            
                            # JSON 파싱을 시도합니다
                            if decoded_line.startswith('data:') and 'data:[DONE]' not in decoded_line:
                                try:
                                    # data: 접두사 제거 후 JSON 파싱
                                    json_str = decoded_line[5:]
                                    data = json.loads(json_str)
                                    
                                    # 이벤트가 'result'인 경우 - 전체 응답을 한 번에 받음
                                    if 'event' in decoded_line and 'result' in decoded_line:
                                        if 'message' in data and 'content' in data['message']:
                                            full_content = data['message']['content']
                                            if full_content != last_full_content:  # 중복 방지
                                                full_response = full_content  # 전체 응답으로 교체
                                                last_full_content = full_content
                                    # 일반 토큰 이벤트
                                    elif 'message' in data and 'content' in data['message']:
                                        content = data['message']['content']
                                        full_response += content
                                        # 디버그 메시지 제거
                                        # print(f"추출된 내용: {content}")
                                except json.JSONDecodeError:
                                    print(f"JSON 파싱 실패: {decoded_line}")
                    
                    return full_response
        except Exception as e:
            print(f"API 요청 중 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def analyze_jd(self, jd_text, job_type, original_career):
        """JD를 분석하여 스킬과 중요도를 추출합니다."""
        system_prompt = self._get_system_prompt(job_type)
        
        # 텍스트 길이 제한 (최대 4000자로 제한)
        if len(jd_text) > 4000:
            jd_text = jd_text[:4000] + "\n\n(내용이 길어 일부 생략됨)"
        
        # system prompt와 user prompt를 구분하여 messages 배열로 구성
        user_prompt = f"다음 {job_type} 채용공고를 분석해주세요. 결과는 반드시 JSON 형식으로만 응답해주세요:\n\n{jd_text}"
        
        request_data = {
            'messages': [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            'topP': 0.8,
            'topK': 0,
            'maxTokens': 2048,
            'temperature': 0.1,
            'repeatPenalty': 5.0,
            'stopBefore': [],
            'includeAiFilters': True
        }
        
        print(f"프롬프트 길이: {len(system_prompt) + len(user_prompt)}자")
        print("JD 분석 중...")
        
        try:
            result = self.execute(request_data, stream=False)
            print("API 응답 수신 완료!")
            
            # 응답 내용 자세히 로깅
            print("\n--- API 응답 원본 ---")
            print(result)
            print("---------------------\n")
            
            try:
                # 방법 1: 중복 JSON 처리 부분 개선
                json_match = re.search(r'({.*?})\s*{', result, re.DOTALL)
                if json_match:
                    try:
                        json_str = json_match.group(1).strip()
                        json_result = json.loads(json_str)
                        print("첫 번째 JSON 객체 추출 성공!")
                        json_result["경력"] = original_career
                        return json_result
                    except json.JSONDecodeError as e:
                        print(f"첫 번째 JSON 객체 파싱 실패: {e}")
                
                # 방법 2: 전체 JSON 직접 추출 시도
                json_match = re.search(r'^({.*})$', result.strip(), re.DOTALL)
                if json_match:
                    try:
                        json_str = json_match.group(1).strip()
                        json_result = json.loads(json_str)
                        print("단일 JSON 객체 추출 성공!")
                        json_result["경력"] = original_career
                        return json_result
                    except json.JSONDecodeError as e:
                        print(f"단일 JSON 객체 파싱 실패: {e}")
                
                # 방법 3: 수동 파싱 - 공고 제목, 회사명만이라도 추출
                title_match = re.search(r'"공고 제목"[:\s]*"([^"]+)"', result)
                company_match = re.search(r'"회사명"[:\s]*"([^"]+)"', result)
                
                if title_match and company_match:
                    print("부분적인 정보 추출 성공!")
                    return {
                        "공고 제목": title_match.group(1),
                        "회사명": company_match.group(1),
                        "직무": job_type,
                        "경력": original_career,
                        "주요 업무 요약": "부분 파싱 성공",
                        "하드 스킬": {"정보 추출 실패": 100},
                        "소프트 스킬": {"정보 추출 실패": 100},
                        "추가 통찰": "API 응답에서 JSON 구조를 추출하지 못했습니다."
                    }
                
                print("모든 JSON 추출 방법 실패")
                return None
            except json.JSONDecodeError:
                print("직접 JSON 파싱 실패, 텍스트에서 JSON 추출 시도...")
                
                # 방법 2: 정규 표현식으로 JSON 부분 추출 시도 (개선된 패턴)
                json_patterns = [
                    r'```json\s*({[\s\S]*?})\s*```',  # 마크다운 JSON 코드 블록
                    r'({[\s\S]*"추가 통찰"[\s\S]*?})',  # 추가 통찰 키를 포함한 JSON
                    r'({[\s\S]*"하드 스킬"[\s\S]*"소프트 스킬"[\s\S]*?})'  # 하드 스킬과 소프트 스킬 키를 포함한 JSON
                ]
                
                for pattern in json_patterns:
                    match = re.search(pattern, result, re.DOTALL)
                    if match:
                        try:
                            json_str = match.group(1).strip()
                            # JSON 문자열 정리 (작은따옴표를 큰따옴표로 변경, 후행 쉼표 제거 등)
                            json_str = re.sub(r"'", '"', json_str)
                            json_str = re.sub(r",\s*}", "}", json_str)
                            
                            json_result = json.loads(json_str)
                            print(f"패턴 '{pattern}'으로 JSON 추출 성공!")
                            # 경력 정보 추가
                            json_result["경력"] = original_career
                            return json_result
                        except json.JSONDecodeError as e:
                            print(f"패턴 '{pattern}'으로 추출했지만 JSON 파싱 실패: {e}")
                
                # 방법 3: 수동 파싱 - 공고 제목, 회사명만이라도 추출
                title_match = re.search(r'"공고 제목"[:\s]*"([^"]+)"', result)
                company_match = re.search(r'"회사명"[:\s]*"([^"]+)"', result)
                
                if title_match and company_match:
                    print("부분적인 정보 추출 성공!")
                    return {
                        "공고 제목": title_match.group(1),
                        "회사명": company_match.group(1),
                        "직무": job_type,
                        "경력": original_career,
                        "주요 업무 요약": "부분 파싱 성공",
                        "하드 스킬": {"정보 추출 실패": 100},
                        "소프트 스킬": {"정보 추출 실패": 100},
                        "추가 통찰": "API 응답에서 JSON 구조를 추출하지 못했습니다."
                    }
                
                print("모든 JSON 추출 방법 실패")
                return None
        except Exception as e:
            print(f"JD 분석 중 오류 발생: {str(e)}")
            return None

    def _get_system_prompt(self, job_type):
        """직무에 맞는 시스템 프롬프트를 반환합니다."""
        prompts = {
            "백엔드 개발자": """백엔드 개발자 채용공고(JD)를 분석하여 핵심 기술 역량(하드 스킬)과 인성 역량(소프트 스킬)을 모두 추출하고, 해당 JD를 작성한 담당자라고 생각하세요. 

미리 정의된 스킬 목록에 의존하지 말고, JD 내용을 기반으로 실제 요구되는 스킬들을 자유롭게 도출해주세요. 각 역량의 중요도를 점수로 평가해주세요. 각 역량은 최대 100점, 최소 10점을 가지며 10점 이하의 중요도를 가졌다고 생각되는 스킬은 결과에서 제외해주세요. 

중요도를 평가할 때는 면접관의 입장에서 해당 스킬은 반드시 확인할 것 같은 스킬이 제일 중요합니다. JD에 명시적으로 언급된 기술이나 역량, 그리고 자격 요건에 포함된 항목은 우대사항보다 더 높은 중요도를 부여해주세요.

추가 통찰 부분은 해당 공고를 가볍게 요약하면 되며, 어떤 지원자를 원하고 있는 것 같은지 설명하면 됩니다. 결과로 나오는 역량의 수는 정해져 있지 않습니다. 결과는 반드시 다음 JSON 형식으로만 제공하고, 주석은 사용하지 마세요:
{"공고 제목": "", "회사명": "", "직무": "백엔드·서버", "주요 업무 요약": "", 
"하드 스킬": {"기술명1": 40, "기술명2": 30, "기술명3": 15, "기술명4": 10, "기술명5": 5}, 
"소프트 스킬": {"역량1": 40, "역량2": 30, "역량3": 15, "역량4": 10, "역량5": 5}, 
"추가 통찰": ""}""",

            "프론트엔드 개발자": """프론트엔드 개발자 채용공고(JD)를 분석하여 핵심 기술 역량(하드 스킬)과 인성 역량(소프트 스킬)을 모두 추출하고, 해당 JD를 작성한 담당자라고 생각하세요. 

미리 정의된 스킬 목록에 의존하지 말고, JD 내용을 기반으로 실제 요구되는 스킬들을 자유롭게 도출해주세요. 각 역량의 중요도를 점수로 평가해주세요. 각 역량은 최대 100점, 최소 10점을 가지며 10점 이하의 중요도를 가졌다고 생각되는 스킬은 결과에서 제외해주세요. 

중요도를 평가할 때는 면접관의 입장에서 해당 스킬은 반드시 확인할 것 같은 스킬이 제일 중요합니다. JD에 명시적으로 언급된 기술이나 역량, 그리고 자격 요건에 포함된 항목은 우대사항보다 더 높은 중요도를 부여해주세요.

추가 통찰 부분은 해당 공고를 가볍게 요약하면 되며, 어떤 지원자를 원하고 있는 것 같은지 설명하면 됩니다. 결과로 나오는 역량의 수는 정해져 있지 않습니다. 결과는 반드시 다음 JSON 형식으로만 제공하고, 주석은 사용하지 마세요:
{"공고 제목": "", "회사명": "", "직무": "프론트엔드", "주요 업무 요약": "", 
"하드 스킬": {"기술명1": 40, "기술명2": 30, "기술명3": 15, "기술명4": 10, "기술명5": 5}, 
"소프트 스킬": {"역량1": 40, "역량2": 30, "역량3": 15, "역량4": 10, "역량5": 5}, 
"추가 통찰": ""}""",

            "AI/ML 엔지니어": """AI/ML 엔지니어 채용공고(JD)를 분석하여 핵심 기술 역량(하드 스킬)과 인성 역량(소프트 스킬)을 모두 추출하고, 해당 JD를 작성한 담당자라고 생각하세요. 

미리 정의된 스킬 목록에 의존하지 말고, JD 내용을 기반으로 실제 요구되는 스킬들을 자유롭게 도출해주세요. 각 역량의 중요도를 점수로 평가해주세요. 각 역량은 최대 100점, 최소 10점을 가지며 10점 이하의 중요도를 가졌다고 생각되는 스킬은 결과에서 제외해주세요. 

중요도를 평가할 때는 면접관의 입장에서 해당 스킬은 반드시 확인할 것 같은 스킬이 제일 중요합니다. JD에 명시적으로 언급된 기술이나 역량, 그리고 자격 요건에 포함된 항목은 우대사항보다 더 높은 중요도를 부여해주세요.

추가 통찰 부분은 해당 공고를 가볍게 요약하면 되며, 어떤 지원자를 원하고 있는 것 같은지 설명하면 됩니다. 결과로 나오는 역량의 수는 정해져 있지 않습니다. 결과는 반드시 다음 JSON 형식으로만 제공하고, 주석은 사용하지 마세요:
{"공고 제목": "", "회사명": "", "직무": "AI/ML", "주요 업무 요약": "", 
"하드 스킬": {"기술명1": 40, "기술명2": 30, "기술명3": 15, "기술명4": 10, "기술명5": 5}, 
"소프트 스킬": {"역량1": 40, "역량2": 30, "역량3": 15, "역량4": 10, "역량5": 5}, 
"추가 통찰": ""}""",

            "데이터 분석가": """데이터 분석가 채용공고(JD)를 분석하여 핵심 기술 역량(하드 스킬)과 인성 역량(소프트 스킬)을 모두 추출하고, 해당 JD를 작성한 담당자라고 생각하세요. 

미리 정의된 스킬 목록에 의존하지 말고, JD 내용을 기반으로 실제 요구되는 스킬들을 자유롭게 도출해주세요. 각 역량의 중요도를 점수로 평가해주세요. 각 역량은 최대 100점, 최소 10점을 가지며 10점 이하의 중요도를 가졌다고 생각되는 스킬은 결과에서 제외해주세요. 

중요도를 평가할 때는 면접관의 입장에서 해당 스킬은 반드시 확인할 것 같은 스킬이 제일 중요합니다. JD에 명시적으로 언급된 기술이나 역량, 그리고 자격 요건에 포함된 항목은 우대사항보다 더 높은 중요도를 부여해주세요.

추가 통찰 부분은 해당 공고를 가볍게 요약하면 되며, 어떤 지원자를 원하고 있는 것 같은지 설명하면 됩니다. 결과로 나오는 역량의 수는 정해져 있지 않습니다. 결과는 반드시 다음 JSON 형식으로만 제공하고, 주석은 사용하지 마세요:
{"공고 제목": "", "회사명": "", "직무": "데이터 분석", "주요 업무 요약": "", 
"하드 스킬": {"기술명1": 40, "기술명2": 30, "기술명3": 15, "기술명4": 10, "기술명5": 5}, 
"소프트 스킬": {"역량1": 40, "역량2": 30, "역량3": 15, "역량4": 10, "역량5": 5}, 
"추가 통찰": ""}""",

            "제품 기획자": """제품 기획자 채용공고(JD)를 분석하여 핵심 기술 역량(하드 스킬)과 인성 역량(소프트 스킬)을 모두 추출하고, 해당 JD를 작성한 담당자라고 생각하세요. 

미리 정의된 스킬 목록에 의존하지 말고, JD 내용을 기반으로 실제 요구되는 스킬들을 자유롭게 도출해주세요. 각 역량의 중요도를 점수로 평가해주세요. 각 역량은 최대 100점, 최소 10점을 가지며 10점 이하의 중요도를 가졌다고 생각되는 스킬은 결과에서 제외해주세요. 

중요도를 평가할 때는 면접관의 입장에서 해당 스킬은 반드시 확인할 것 같은 스킬이 제일 중요합니다. JD에 명시적으로 언급된 기술이나 역량, 그리고 자격 요건에 포함된 항목은 우대사항보다 더 높은 중요도를 부여해주세요.

추가 통찰 부분은 해당 공고를 가볍게 요약하면 되며, 어떤 지원자를 원하고 있는 것 같은지 설명하면 됩니다. 결과로 나오는 역량의 수는 정해져 있지 않습니다. 결과는 반드시 다음 JSON 형식으로만 제공하고, 주석은 사용하지 마세요:
{"공고 제목": "", "회사명": "", "직무": "제품 기획", "주요 업무 요약": "", 
"하드 스킬": {"기술명1": 40, "기술명2": 30, "기술명3": 15, "기술명4": 10, "기술명5": 5}, 
"소프트 스킬": {"역량1": 40, "역량2": 30, "역량3": 15, "역량4": 10, "역량5": 5}, 
"추가 통찰": ""}""",

            "PM/PO": """PM/PO 채용공고(JD)를 분석하여 핵심 기술 역량(하드 스킬)과 인성 역량(소프트 스킬)을 모두 추출하고, 해당 JD를 작성한 담당자라고 생각하세요. 

미리 정의된 스킬 목록에 의존하지 말고, JD 내용을 기반으로 실제 요구되는 스킬들을 자유롭게 도출해주세요. 각 역량의 중요도를 점수로 평가해주세요. 각 역량은 최대 100점, 최소 10점을 가지며 10점 이하의 중요도를 가졌다고 생각되는 스킬은 결과에서 제외해주세요. 

중요도를 평가할 때는 면접관의 입장에서 해당 스킬은 반드시 확인할 것 같은 스킬이 제일 중요합니다. JD에 명시적으로 언급된 기술이나 역량, 그리고 자격 요건에 포함된 항목은 우대사항보다 더 높은 중요도를 부여해주세요.

추가 통찰 부분은 해당 공고를 가볍게 요약하면 되며, 어떤 지원자를 원하고 있는 것 같은지 설명하면 됩니다. 결과로 나오는 역량의 수는 정해져 있지 않습니다. 결과는 반드시 다음 JSON 형식으로만 제공하고, 주석은 사용하지 마세요:
{"공고 제목": "", "회사명": "", "직무": "PM/PO", "주요 업무 요약": "", 
"하드 스킬": {"기술명1": 40, "기술명2": 30, "기술명3": 15, "기술명4": 10, "기술명5": 5}, 
"소프트 스킬": {"역량1": 40, "역량2": 30, "역량3": 15, "역량4": 10, "역량5": 5}, 
"추가 통찰": ""}""",

            "프로덕트 디자이너": """프로덕트 디자이너 채용공고(JD)를 분석하여 핵심 기술 역량(하드 스킬)과 인성 역량(소프트 스킬)을 모두 추출하고, 해당 JD를 작성한 담당자라고 생각하세요. 

미리 정의된 스킬 목록에 의존하지 말고, JD 내용을 기반으로 실제 요구되는 스킬들을 자유롭게 도출해주세요. 각 역량의 중요도를 점수로 평가해주세요. 각 역량은 최대 100점, 최소 10점을 가지며 10점 이하의 중요도를 가졌다고 생각되는 스킬은 결과에서 제외해주세요. 

중요도를 평가할 때는 면접관의 입장에서 해당 스킬은 반드시 확인할 것 같은 스킬이 제일 중요합니다. JD에 명시적으로 언급된 기술이나 역량, 그리고 자격 요건에 포함된 항목은 우대사항보다 더 높은 중요도를 부여해주세요.

추가 통찰 부분은 해당 공고를 가볍게 요약하면 되며, 어떤 지원자를 원하고 있는 것 같은지 설명하면 됩니다. 결과로 나오는 역량의 수는 정해져 있지 않습니다. 결과는 반드시 다음 JSON 형식으로만 제공하고, 주석은 사용하지 마세요:
{"공고 제목": "", "회사명": "", "직무": "프로덕트 디자이너", "주요 업무 요약": "", 
"하드 스킬": {"기술명1": 40, "기술명2": 30, "기술명3": 15, "기술명4": 10, "기술명5": 5}, 
"소프트 스킬": {"역량1": 40, "역량2": 30, "역량3": 15, "역량4": 10, "역량5": 5}, 
"추가 통찰": ""}""",

            "그래픽 디자이너": """그래픽 디자이너 채용공고(JD)를 분석하여 핵심 기술 역량(하드 스킬)과 인성 역량(소프트 스킬)을 모두 추출하고, 해당 JD를 작성한 담당자라고 생각하세요. 

미리 정의된 스킬 목록에 의존하지 말고, JD 내용을 기반으로 실제 요구되는 스킬들을 자유롭게 도출해주세요. 각 역량의 중요도를 점수로 평가해주세요. 각 역량은 최대 100점, 최소 10점을 가지며 10점 이하의 중요도를 가졌다고 생각되는 스킬은 결과에서 제외해주세요. 

중요도를 평가할 때는 면접관의 입장에서 해당 스킬은 반드시 확인할 것 같은 스킬이 제일 중요합니다. JD에 명시적으로 언급된 기술이나 역량, 그리고 자격 요건에 포함된 항목은 우대사항보다 더 높은 중요도를 부여해주세요.

추가 통찰 부분은 해당 공고를 가볍게 요약하면 되며, 어떤 지원자를 원하고 있는 것 같은지 설명하면 됩니다. 결과로 나오는 역량의 수는 정해져 있지 않습니다. 결과는 반드시 다음 JSON 형식으로만 제공하고, 주석은 사용하지 마세요:
{"공고 제목": "", "회사명": "", "직무": "그래픽 디자이너", "주요 업무 요약": "", 
"하드 스킬": {"기술명1": 40, "기술명2": 30, "기술명3": 15, "기술명4": 10, "기술명5": 5}, 
"소프트 스킬": {"역량1": 40, "역량2": 30, "역량3": 15, "역량4": 10, "역량5": 5}, 
"추가 통찰": ""}""",

            "콘텐츠 디자이너": """콘텐츠 디자이너 채용공고(JD)를 분석하여 핵심 기술 역량(하드 스킬)과 인성 역량(소프트 스킬)을 모두 추출하고, 해당 JD를 작성한 담당자라고 생각하세요. 

미리 정의된 스킬 목록에 의존하지 말고, JD 내용을 기반으로 실제 요구되는 스킬들을 자유롭게 도출해주세요. 각 역량의 중요도를 점수로 평가해주세요. 각 역량은 최대 100점, 최소 10점을 가지며 10점 이하의 중요도를 가졌다고 생각되는 스킬은 결과에서 제외해주세요. 

중요도를 평가할 때는 면접관의 입장에서 해당 스킬은 반드시 확인할 것 같은 스킬이 제일 중요합니다. JD에 명시적으로 언급된 기술이나 역량, 그리고 자격 요건에 포함된 항목은 우대사항보다 더 높은 중요도를 부여해주세요.

추가 통찰 부분은 해당 공고를 가볍게 요약하면 되며, 어떤 지원자를 원하고 있는 것 같은지 설명하면 됩니다. 결과로 나오는 역량의 수는 정해져 있지 않습니다. 결과는 반드시 다음 JSON 형식으로만 제공하고, 주석은 사용하지 마세요:
{"공고 제목": "", "회사명": "", "직무": "콘텐츠 디자이너", "주요 업무 요약": "", 
"하드 스킬": {"기술명1": 40, "기술명2": 30, "기술명3": 15, "기술명4": 10, "기술명5": 5}, 
"소프트 스킬": {"역량1": 40, "역량2": 30, "역량3": 15, "역량4": 10, "역량5": 5}, 
"추가 통찰": ""}"""
        }
        
        # 기본 프롬프트 (직무별 프롬프트가 없는 경우)
        default_prompt = f"""{job_type} 채용공고(JD)를 분석하여 핵심 기술 역량(하드 스킬)과 인성 역량(소프트 스킬)을 모두 추출하고, 해당 JD를 작성한 담당자라고 생각하세요. 

미리 정의된 스킬 목록에 의존하지 말고, JD 내용을 기반으로 실제 요구되는 스킬들을 자유롭게 도출해주세요. 각 역량의 중요도를 점수로 평가해주세요. 각 역량은 최대 100점, 최소 10점을 가지며 10점 이하의 중요도를 가졌다고 생각되는 스킬은 결과에서 제외해주세요. 

중요도를 평가할 때는 면접관의 입장에서 해당 스킬은 반드시 확인할 것 같은 스킬이 제일 중요합니다. JD에 명시적으로 언급된 기술이나 역량, 그리고 자격 요건에 포함된 항목은 우대사항보다 더 높은 중요도를 부여해주세요.

추가 통찰 부분은 해당 공고를 가볍게 요약하면 되며, 어떤 지원자를 원하고 있는 것 같은지 설명하면 됩니다. 결과로 나오는 역량의 수는 정해져 있지 않습니다. 결과는 반드시 다음 JSON 형식으로만 제공하고, 주석은 사용하지 마세요:
{{"공고 제목": "", "회사명": "", "직무": "{job_type}", "주요 업무 요약": "", 
"하드 스킬": {{"기술명1": 40, "기술명2": 30, "기술명3": 15, "기술명4": 10, "기술명5": 5}}, 
"소프트 스킬": {{"역량1": 40, "역량2": 30, "역량3": 15, "역량4": 10, "역량5": 5}}, 
"추가 통찰": ""}}"""
        
        return prompts.get(job_type, default_prompt)

def load_jd_data(csv_path, job_type=None):
    """CSV 파일에서 JD 데이터를 로드합니다. 직무 유형에 따라 다른 CSV 구조를 처리합니다."""
    try:
        # CSV 파일 읽기
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # 데이터프레임이 비어있는지 확인
        if df.empty:
            print(f"경고: {csv_path} 파일에 데이터가 없습니다.")
            return []
        
        # 결과를 저장할 리스트
        jd_list = []
        
        # 직무 유형에 따른 열 매핑
        if job_type and job_type.lower() == 'backend':
            # backend 직무는 기존 구조 유지
            for _, row in df.iterrows():
                jd_dict = {
                    '경력': row.get('경력', ''),
                    '공고명': row.get('공고명', ''),
                    '기업명': row.get('기업명', ''),
                    '주요 업무': row.get('주요 업무', ''),
                    '자격 요건': row.get('자격 요건', ''),
                    '우대사항': row.get('우대사항', ''),
                    '기술': row.get('기술', '')
                }
                jd_list.append(jd_dict)
        else:
            # 다른 직무는 새로운 구조(경력,주요 업무,자격 요건,우대사항,기술)
            for _, row in df.iterrows():
                jd_dict = {
                    '경력': row.get('경력', ''),
                    '주요 업무': row.get('주요 업무', ''),
                    '자격 요건': row.get('자격 요건', ''),
                    '우대사항': row.get('우대사항', ''),
                    '기술': row.get('기술', '')
                }
                jd_list.append(jd_dict)
        
        return jd_list
    
    except Exception as e:
        print(f"CSV 파일 로드 중 오류 발생: {str(e)}")
        return []

def test_api_connection(executor):
    """Clova API 연결을 테스트합니다."""
    print("Clova API 연결 테스트 중...")
    
    # 매우 단순한 테스트 요청
    request_data = {
        'messages': [
            {"role": "user", "content": "숫자 5를 출력해주세요."}
        ],
        'maxTokens': 10,
        'temperature': 0.1
    }
    
    try:
        print(f"API 요청 데이터: {json.dumps(request_data, indent=2)}")
        result = executor.execute(request_data, stream=False)
        
        print(f"API 테스트 응답: '{result}'")
        
        if result and "5" in result:
            print("✅ API 테스트 성공!")
            return True
        else:
            print("❌ API 응답에 예상 결과가 없습니다.")
            return False
    except Exception as e:
        print(f"❌ API 테스트 중 오류 발생: {str(e)}")
        return False

def format_jd_text(jd):
    """채용공고 데이터를 텍스트로 포맷팅합니다."""
    if '공고명' in jd:
        title = jd.get('공고명', '')
        company = jd.get('기업명', '')
    else:
        title = ""  # 공고명이 없는 경우 (직무별 형식이 다른 경우)
        company = ""
    
    career = jd.get('경력', '미기재')
    main_duties = jd.get('주요 업무', '')
    requirements = jd.get('자격 요건', '')
    preferences = jd.get('우대사항', '')
    tech_stack = jd.get('기술', '')
    
    return f"""공고명: {title}
기업명: {company}
경력: {career}

주요 업무:
{main_duties}

자격 요건:
{requirements}

우대사항:
{preferences}

기술 스택: {tech_stack}
"""

def analyze_jds(executor, jd_data, job_type):
    """모든 JD를 분석하고 결과를 반환합니다."""
    results = []
    
    for i, jd in enumerate(jd_data):
        if '공고명' in jd:
            print(f"JD 분석 중 ({i+1}/{len(jd_data)}): {jd.get('공고명', '제목 없음')} - {jd.get('기업명', '회사명 없음')}")
        else:
            print(f"JD 분석 중 ({i+1}/{len(jd_data)})")
        
        # JD 텍스트 포맷팅
        jd_text = format_jd_text(jd)
        
        # 원본 경력 정보 추출
        original_career = jd.get('경력', '미기재')
        
        # 최대 3번 재시도
        max_retries = 3
        for retry in range(max_retries):
            try:
                # JD 분석 (경력 정보 포함)
                analysis_result = executor.analyze_jd(jd_text, job_type, original_career)
                
                if analysis_result:
                    results.append(analysis_result)
                    break  # 성공하면 재시도 루프 종료
                else:
                    print(f"시도 {retry+1}/{max_retries}: 분석 결과가 None입니다. 재시도 중...")
                    time.sleep(10)  # 더 긴 대기 시간
            except Exception as e:
                print(f"시도 {retry+1}/{max_retries}: 오류 발생 - {str(e)}")
                if retry < max_retries - 1:  # 마지막 시도가 아니면 재시도
                    time.sleep(10)  # 오류 발생 시 10초 대기
        else:  # 모든 재시도 실패 시
            job_title = jd.get('공고명', '제목 없음')
            company_name = jd.get('기업명', '회사명 없음')
            print(f"'{job_title}' JD 분석 실패 - 모든 재시도 실패")
            # 간단한 대체 결과 생성
            results.append({
                "공고 제목": job_title,
                "회사명": company_name,
                "직무": job_type,
                "경력": original_career,
                "주요 업무 요약": "분석 실패",
                "하드 스킬": {},
                "소프트 스킬": {},
                "추가 통찰": "분석 중 오류 발생"
            })
        
        # API 요청 간 딜레이 - 속도 제한 오류 방지를 위해 5초로 증가
        time.sleep(5)
    
    return results

def main():
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(description='JD 분석 스크립트')
    parser.add_argument('--job_type', type=str, required=True, help='분석할 직무 유형 (예: 백엔드, 프론트엔드, AI/ML 등)')
    parser.add_argument('--input', type=str, required=True, help='JD CSV 파일 경로')
    parser.add_argument('--output', type=str, required=True, help='결과를 저장할 JSON 파일 경로')
    args = parser.parse_args()
    
    # API 설정 - 환경 변수에서 API 키 로드
    completion_executor = CompletionExecutor(
        host='https://clovastudio.stream.ntruss.com'
    )
    
    # 데이터 로드 - job_type 인자 추가
    print(f"채용공고 데이터 로드 중... ({args.input})")
    jd_data = load_jd_data(args.input, args.job_type)
    print(f"로드 완료: 채용공고 {len(jd_data)}개")
    
    # API 연결 테스트
    api_available = test_api_connection(completion_executor)
    
    if not api_available:
        print("Clova API를 사용할 수 없습니다. 프로그램을 종료합니다.")
        return
    
    # JD 분석
    print(f"{args.job_type} JD 분석 시작...")
    results = analyze_jds(completion_executor, jd_data, args.job_type)
    
    # 결과를 JSON으로 저장
    output_path = args.output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"분석 완료! 결과가 '{output_path}' 파일에 저장되었습니다.")

if __name__ == "__main__":
    main()