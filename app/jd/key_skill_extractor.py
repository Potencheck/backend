import json
import os
import time
import re
from collections import defaultdict

class CompletionExecutor:
    def __init__(self, host, api_key, request_id):
        # host에 스킴이 있는지 확인하고 없으면 추가
        if not host.startswith(('http://', 'https://')):
            self._host = 'https://' + host
        else:
            self._host = host
        self._api_key = api_key
        self._request_id = request_id

    def execute(self, completion_request, stream=False):
        """Chat Completions API를 호출하여 응답을 받습니다."""
        import requests
        
        headers = {
            'Authorization': self._api_key,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'text/event-stream'
        }

        try:
            url = self._host + '/testapp/v1/chat-completions/HCX-003'
            
            with requests.post(url, headers=headers, json=completion_request, stream=True) as r:
                if r.status_code != 200:
                    return None
                    
                r.raise_for_status()
                
                if stream:
                    # 스트리밍 모드면 그대로 출력
                    for line in r.iter_lines():
                        if line:
                            pass
                    return None
                else:
                    # 스트리밍 모드가 아니면 전체 응답 누적
                    full_response = ""
                    for line in r.iter_lines():
                        if line:
                            decoded_line = line.decode("utf-8")
                            
                            # JSON 파싱을 시도합니다
                            if decoded_line.startswith('data:') and decoded_line != 'data:[DONE]':
                                try:
                                    # data: 접두사 제거 후 JSON 파싱
                                    json_str = decoded_line[5:]
                                    data = json.loads(json_str)
                                    
                                    # message 객체에서 content 추출
                                    if 'message' in data and 'content' in data['message']:
                                        content = data['message']['content']
                                        full_response += content
                                except json.JSONDecodeError:
                                    pass
                    
                    return full_response
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None

def load_jd_analysis(file_path):
    """JD 분석 결과를 로드합니다."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_skills(jd_list):
    """주어진 JD 목록에서 하드 스킬과 소프트 스킬을 추출합니다."""
    hard_skills = defaultdict(list)
    soft_skills = defaultdict(list)
    
    for jd in jd_list:
        # 하드 스킬 추출
        for skill, score in jd.get('하드 스킬', {}).items():
            hard_skills[skill].append(score)
        
        # 소프트 스킬 추출
        for skill, score in jd.get('소프트 스킬', {}).items():
            soft_skills[skill].append(score)
    
    return hard_skills, soft_skills

def calculate_skill_metrics(skills_dict):
    """스킬 빈도와 평균 중요도를 계산합니다."""
    skill_metrics = {}
    
    for skill, scores in skills_dict.items():
        skill_metrics[skill] = {
            'frequency': len(scores),
            'avg_score': sum(scores) / len(scores) if scores else 0
        }
    
    return skill_metrics

def get_job_category_skill_mapping():
    """직무별 하드 스킬 카테고리 매핑을 반환합니다."""
    category_mapping = {
        "backend": {
            "언어": ["Java", "Python", "Kotlin", "TypeScript", "JavaScript", "C++", "Go", "Scala", "C#", "Rust"],
            "프레임워크": ["Spring Framework", "Spring Boot", "Spring", "Django", "Node.js", "Express", "Flask", "React", "Vue.js", "NestJS", "ASP.NET"],
            "데이터베이스": ["MySQL", "RDBMS", "PostgreSQL", "MongoDB", "Oracle", "MariaDB", "Redis", "Elasticsearch", "JPA", "Hibernate", "NoSQL", "DynamoDB", "SQL", "Database"],
            "도구/인프라": ["AWS", "Docker", "Git", "Kubernetes", "Jenkins", "CI/CD", "Linux", "Nginx", "Apache", "REST API", "Azure", "GCP"]
        },
        "frontend": {
            "언어": ["JavaScript", "TypeScript", "HTML", "CSS", "Sass", "Less"],
            "프레임워크/라이브러리": ["React", "Vue.js", "Angular", "Next.js", "Nuxt.js", "jQuery", "Redux", "MobX", "Svelte"],
            "도구": ["Webpack", "Babel", "ESLint", "Jest", "Cypress", "Git", "npm", "yarn", "Storybook"],
            "디자인/UX": ["Figma", "Sketch", "Adobe XD", "UI/UX", "반응형 디자인", "웹 접근성", "CSS Grid", "Flexbox"]
        },
        "ai-ml": {
            "언어": ["Python", "R", "C++", "Java", "Julia", "Scala"],
            "라이브러리/프레임워크": ["TensorFlow", "PyTorch", "Keras", "Scikit-learn", "Pandas", "NumPy", "Hugging Face", "XGBoost", "LightGBM"],
            "알고리즘/지식": ["머신러닝", "딥러닝", "자연어처리", "컴퓨터 비전", "강화학습", "추천 시스템", "통계", "수학"],
            "도구/인프라": ["Docker", "Kubernetes", "MLOps", "AWS", "GCP", "Azure", "Hadoop", "Spark", "Airflow"]
        },
        "data": {
            "언어": ["SQL", "Python", "R", "Scala"],
            "데이터베이스/스토리지": ["MySQL", "PostgreSQL", "MongoDB", "Redshift", "BigQuery", "Snowflake", "Hadoop", "HDFS"],
            "분석/시각화": ["Tableau", "Power BI", "데이터 시각화", "통계 분석", "A/B 테스트", "Pandas", "NumPy", "Matplolib", "Seaborn"],
            "도구/인프라": ["Spark", "Kafka", "Airflow", "ETL", "ELT", "데이터 모델링", "데이터 파이프라인", "AWS", "GCP", "Azure"]
        },
        "pm-po": {
            "방법론": ["Agile", "Scrum", "Waterfall", "Kanban", "린 스타트업", "Design Thinking"],
            "도구": ["Jira", "Confluence", "Notion", "Asana", "Trello", "Figma", "Google Analytics", "Amplitude"],
            "스킬": ["제품 전략", "로드맵 설계", "시장 조사", "요구사항 분석", "사용자 조사", "A/B 테스트", "데이터 분석"],
            "비즈니스": ["비즈니스 모델", "수익화 전략", "KPI 설정", "성과 측정", "경쟁사 분석", "사용자 여정 맵"]
        },
        "planning": {
            "방법론": ["기획 방법론", "서비스 기획", "UX 기획", "컨텐츠 기획", "전략 기획"],
            "도구": ["Figma", "Sketch", "Adobe XD", "Jira", "Confluence", "Notion", "Google Analytics", "Amplitude"],
            "스킬": ["요구사항 분석", "와이어프레임", "프로토타이핑", "정보 구조화", "사용자 시나리오", "사용성 테스트"],
            "비즈니스": ["시장 조사", "경쟁사 분석", "KPI 설정", "성과 측정", "데이터 분석", "비즈니스 모델"]
        },
        "product-designer": {
            "디자인 툴": ["Figma", "Sketch", "Adobe XD", "Illustrator", "Photoshop", "Protopie", "After Effects"],
            "디자인 스킬": ["UI 디자인", "UX 디자인", "인터랙션 디자인", "시각 디자인", "디자인 시스템", "타이포그래피", "그리드 시스템"],
            "프로세스": ["디자인 씽킹", "사용자 리서치", "프로토타이핑", "와이어프레임", "사용성 테스트", "A/B 테스트"],
            "기술 이해": ["HTML", "CSS", "JavaScript", "반응형 디자인", "웹 접근성", "모바일 디자인 가이드라인", "애니메이션"]
        },
        "graphic-designer": {
            "디자인 툴": ["Photoshop", "Illustrator", "InDesign", "After Effects", "Figma", "Sketch", "Procreate"],
            "디자인 스킬": ["그래픽 디자인", "타이포그래피", "색채 이론", "레이아웃", "브랜딩", "로고 디자인", "일러스트레이션"],
            "인쇄/출판": ["인쇄 디자인", "편집 디자인", "패키지 디자인", "인쇄 공정 이해", "종이 지식", "바인딩"],
            "디지털 미디어": ["웹 디자인", "소셜 미디어 그래픽", "배너 디자인", "모션 그래픽", "디지털 마케팅 자료"]
        },
        "content-designer": {
            "라이팅 스킬": ["카피라이팅", "콘텐츠 기획", "스토리텔링", "에디팅", "번역", "톤앤매너 설정", "UX 라이팅"],
            "도구/플랫폼": ["Notion", "WordPress", "Google Analytics", "SNS 툴", "CMS", "SEO 도구", "Adobe 제품군"],
            "마케팅": ["콘텐츠 마케팅", "소셜 미디어 마케팅", "퍼포먼스 마케팅", "브랜드 마케팅", "그로스 해킹"],
            "분석": ["콘텐츠 성과 분석", "사용자 행동 분석", "트렌드 분석", "경쟁사 분석", "SEO/SEM", "A/B 테스트"]
        }
    }
    
    # 기본 매핑이 없는 직무는 공통 카테고리 사용
    default_categories = {
        "기술 스킬": [],
        "도구": [],
        "방법론": [],
        "기타": []
    }
    
    return category_mapping, default_categories

def categorize_hard_skills(hard_skills, job_category):
    """하드 스킬을 카테고리별로 분류합니다."""
    category_mapping, default_categories = get_job_category_skill_mapping()
    
    # 해당 직무의 카테고리 매핑 가져오기
    categories = category_mapping.get(job_category, default_categories)
    
    categorized_skills = {category: {} for category in categories}
    uncategorized = {}
    
    for skill, score in hard_skills.items():
        categorized = False
        for category, skill_list in categories.items():
            if skill_list and any(s.lower() in skill.lower() or skill.lower() in s.lower() for s in skill_list):
                categorized_skills[category][skill] = score
                categorized = True
                break
        
        if not categorized:
            uncategorized[skill] = score
    
    # 각 카테고리 내에서 점수 내림차순으로 정렬
    sorted_categories = {}
    for category, skills in categorized_skills.items():
        if skills:  # 빈 카테고리는 제외
            sorted_categories[category] = dict(sorted(skills.items(), key=lambda x: x[1], reverse=True))
    
    # 미분류 스킬이 있으면 추가
    if uncategorized:
        sorted_categories["기타"] = dict(sorted(uncategorized.items(), key=lambda x: x[1], reverse=True))
    
    return sorted_categories

def get_job_prompt(job_category, experience_category):
    """직무별 프롬프트를 생성합니다."""
    # 경력 표현 변경
    display_category = "신입" if experience_category == "new" else "경력"
    
    prompts = {
        "backend": f"""당신은 백엔드 개발자 채용 시장 분석 전문가입니다. 다양한 백엔드 개발자 채용공고(JD)에서 추출된 기술 역량(하드 스킬)과 인성 역량(소프트 스킬) 데이터를 분석하고 핵심 역량을 도출해 주세요.

## 분석 대상
{display_category} 백엔드 개발자 채용공고에서 추출한 역량 데이터입니다.

## 분석 목표
1. 유사하거나 중복된 스킬을 하나로 통합하세요 (예: "Java"와 "자바"는 "Java"로 통합).
2. 스킬들을 중요도에 따라 순위를 매기고, 백분위 점수로 환산하세요.
3. {display_category} 백엔드 개발자가 이력서를 작성할 때 반드시 포함해야 할 핵심 스킬을 추출하세요.
4. 모든 중요한 스킬(중요도 10점 이상)을 누락 없이 모두 포함하는 것이 가장 중요합니다.
5. 하드 스킬은 최소 10개 이상, 소프트 스킬은 최소 5개 이상 추출해주세요. 소프트 스킬이 부족하다면 유사한 개념을 세분화하거나 데이터에서 암시적으로 나타나는 역량을 추가로 도출해주세요.

## 분류 기준
1. 하드 스킬: 기술적 역량만 포함하세요. 프로그래밍 언어, 프레임워크, 도구, 인프라, 데이터베이스 등 기술적 지식과 능력.
2. 소프트 스킬: 인성 역량만 포함하세요. 의사소통 능력, 문제 해결 능력, 팀워크 등 대인관계와 관련된 스킬.""",

        "frontend": f"""당신은 프론트엔드 개발자 채용 시장 분석 전문가입니다. 다양한 프론트엔드 개발자 채용공고(JD)에서 추출된 기술 역량(하드 스킬)과 인성 역량(소프트 스킬) 데이터를 분석하고 핵심 역량을 도출해 주세요.

## 분석 대상
{display_category} 프론트엔드 개발자 채용공고에서 추출한 역량 데이터입니다.

## 분석 목표
1. 유사하거나 중복된 스킬을 하나로 통합하세요 (예: "React"와 "리액트"는 "React"로 통합).
2. 스킬들을 중요도에 따라 순위를 매기고, 백분위 점수로 환산하세요.
3. {display_category} 프론트엔드 개발자가 이력서를 작성할 때 반드시 포함해야 할 핵심 스킬을 추출하세요.
4. 모든 중요한 스킬(중요도 10점 이상)을 누락 없이 모두 포함하는 것이 가장 중요합니다.
5. 하드 스킬은 최소 10개 이상, 소프트 스킬은 최소 5개 이상 추출해주세요. 소프트 스킬이 부족하다면 유사한 개념을 세분화하거나 데이터에서 암시적으로 나타나는 역량을 추가로 도출해주세요.

## 분류 기준
1. 하드 스킬: 기술적 역량만 포함하세요. 프로그래밍 언어, 프레임워크, 라이브러리, 도구, UI/UX 관련 기술적 지식과 능력.
2. 소프트 스킬: 인성 역량만 포함하세요. 의사소통 능력, 문제 해결 능력, 팀워크 등 대인관계와 관련된 스킬.""",

        "ai-ml": f"""당신은 AI/ML 엔지니어 채용 시장 분석 전문가입니다. 다양한 AI/ML 엔지니어 채용공고(JD)에서 추출된 기술 역량(하드 스킬)과 인성 역량(소프트 스킬) 데이터를 분석하고 핵심 역량을 도출해 주세요.

## 분석 대상
{display_category} AI/ML 엔지니어 채용공고에서 추출한 역량 데이터입니다.

## 분석 목표
1. 유사하거나 중복된 스킬을 하나로 통합하세요 (예: "TensorFlow"와 "텐서플로우"는 "TensorFlow"로 통합).
2. 스킬들을 중요도에 따라 순위를 매기고, 백분위 점수로 환산하세요.
3. {display_category} AI/ML 엔지니어가 이력서를 작성할 때 반드시 포함해야 할 핵심 스킬을 추출하세요.
4. 모든 중요한 스킬(중요도 10점 이상)을 누락 없이 모두 포함하는 것이 가장 중요합니다.
5. 하드 스킬은 최소 10개 이상, 소프트 스킬은 최소 5개 이상 추출해주세요. 소프트 스킬이 부족하다면 유사한 개념을 세분화하거나 데이터에서 암시적으로 나타나는 역량을 추가로 도출해주세요.

## 분류 기준
1. 하드 스킬: 기술적 역량만 포함하세요. 프로그래밍 언어, 머신러닝/딥러닝 프레임워크, 알고리즘, 통계 지식, 데이터 처리 도구 등 기술적 지식과 능력.
2. 소프트 스킬: 인성 역량만 포함하세요. 의사소통 능력, 문제 해결 능력, 팀워크 등 대인관계와 관련된 스킬.""",

        "data": f"""당신은 데이터 분석가/과학자 채용 시장 분석 전문가입니다. 다양한 데이터 관련 직무 채용공고(JD)에서 추출된 기술 역량(하드 스킬)과 인성 역량(소프트 스킬) 데이터를 분석하고 핵심 역량을 도출해 주세요.

## 분석 대상
{display_category} 데이터 분석가/과학자 채용공고에서 추출한 역량 데이터입니다.

## 분석 목표
1. 유사하거나 중복된 스킬을 하나로 통합하세요 (예: "SQL"과 "에스큐엘"은 "SQL"로 통합).
2. 스킬들을 중요도에 따라 순위를 매기고, 백분위 점수로 환산하세요.
3. {display_category} 데이터 분석가/과학자가 이력서를 작성할 때 반드시 포함해야 할 핵심 스킬을 추출하세요.
4. 모든 중요한 스킬(중요도 10점 이상)을 누락 없이 모두 포함하는 것이 가장 중요합니다.
5. 하드 스킬은 최소 10개 이상, 소프트 스킬은 최소 5개 이상 추출해주세요. 소프트 스킬이 부족하다면 유사한 개념을 세분화하거나 데이터에서 암시적으로 나타나는 역량을 추가로 도출해주세요.

## 분류 기준
1. 하드 스킬: 기술적 역량만 포함하세요. 프로그래밍 언어, 데이터베이스, 분석 도구, 통계 지식, 데이터 시각화 도구 등 기술적 지식과 능력.
2. 소프트 스킬: 인성 역량만 포함하세요. 의사소통 능력, 문제 해결 능력, 팀워크 등 대인관계와 관련된 스킬.""",
        
        "pm-po": f"""당신은 제품 관리자(PM)/제품 책임자(PO) 채용 시장 분석 전문가입니다. 다양한 PM/PO 채용공고(JD)에서 추출된 하드 스킬과 소프트 스킬 데이터를 분석하고 핵심 역량을 도출해 주세요.

## 분석 대상
{display_category} PM/PO 채용공고에서 추출한 역량 데이터입니다.

## 분석 목표
1. 유사하거나 중복된 스킬을 하나로 통합하세요 (예: "제품 전략"과 "프로덕트 전략"은 "제품 전략"으로 통합).
2. 스킬들을 중요도에 따라 순위를 매기고, 백분위 점수로 환산하세요.
3. {display_category} PM/PO가 이력서를 작성할 때 반드시 포함해야 할 핵심 스킬을 추출하세요.
4. 모든 중요한 스킬(중요도 10점 이상)을 누락 없이 모두 포함하는 것이 가장 중요합니다.
5. 하드 스킬은 최소 10개 이상, 소프트 스킬은 최소 5개 이상 추출해주세요. 소프트 스킬이 부족하다면 유사한 개념을 세분화하거나 데이터에서 암시적으로 나타나는 역량을 추가로 도출해주세요.

## 분류 기준
1. 하드 스킬: 제품 관리에 필요한 기술적 역량, 방법론, 도구 활용 능력, 분석 기술 등을 포함합니다.
2. 소프트 스킬: 인성 역량만 포함하세요. 의사소통 능력, 리더십, 협업 능력, 문제 해결 능력 등 대인관계와 관련된 스킬.""",

        "planning": f"""당신은 서비스 기획자 채용 시장 분석 전문가입니다. 다양한 서비스 기획자 채용공고(JD)에서 추출된 하드 스킬과 소프트 스킬 데이터를 분석하고 핵심 역량을 도출해 주세요.

## 분석 대상
{display_category} 서비스 기획자 채용공고에서 추출한 역량 데이터입니다.

## 분석 목표
1. 유사하거나 중복된 스킬을 하나로 통합하세요 (예: "서비스 기획"과 "서비스 planning"은 "서비스 기획"으로 통합).
2. 스킬들을 중요도에 따라 순위를 매기고, 백분위 점수로 환산하세요.
3. {display_category} 서비스 기획자가 이력서를 작성할 때 반드시 포함해야 할 핵심 스킬을 추출하세요.
4. 모든 중요한 스킬(중요도 10점 이상)을 누락 없이 모두 포함하는 것이 가장 중요합니다.
5. 하드 스킬은 최소 10개 이상, 소프트 스킬은 최소 5개 이상 추출해주세요. 소프트 스킬이 부족하다면 유사한 개념을 세분화하거나 데이터에서 암시적으로 나타나는 역량을 추가로 도출해주세요.

## 분류 기준
1. 하드 스킬: 기획에 필요한 방법론, 도구 활용 능력, 분석 기술, 문서화 능력 등을 포함합니다.
2. 소프트 스킬: 인성 역량만 포함하세요. 의사소통 능력, 협업 능력, 문제 해결 능력 등 대인관계와 관련된 스킬.""",

        "product-designer": f"""당신은 프로덕트 디자이너 채용 시장 분석 전문가입니다. 다양한 프로덕트 디자이너 채용공고(JD)에서 추출된 하드 스킬과 소프트 스킬 데이터를 분석하고 핵심 역량을 도출해 주세요.

## 분석 대상
{display_category} 프로덕트 디자이너 채용공고에서 추출한 역량 데이터입니다.

## 분석 목표
1. 유사하거나 중복된 스킬을 하나로 통합하세요 (예: "Figma"와 "피그마"는 "Figma"로 통합).
2. 스킬들을 중요도에 따라 순위를 매기고, 백분위 점수로 환산하세요.
3. {display_category} 프로덕트 디자이너가 이력서를 작성할 때 반드시 포함해야 할 핵심 스킬을 추출하세요.
4. 모든 중요한 스킬(중요도 10점 이상)을 누락 없이 모두 포함하는 것이 가장 중요합니다.
5. 하드 스킬은 최소 10개 이상, 소프트 스킬은 최소 5개 이상 추출해주세요. 소프트 스킬이 부족하다면 유사한 개념을 세분화하거나 데이터에서 암시적으로 나타나는 역량을 추가로 도출해주세요.

## 분류 기준
1. 하드 스킬: 디자인 도구, UI/UX 디자인 기술, 프로토타이핑, 디자인 시스템, 기술적 이해 등을 포함합니다.
2. 소프트 스킬: 인성 역량만 포함하세요. 의사소통 능력, 협업 능력, 문제 해결 능력 등 대인관계와 관련된 스킬.""",

        "graphic-designer": f"""당신은 그래픽 디자이너 채용 시장 분석 전문가입니다. 다양한 그래픽 디자이너 채용공고(JD)에서 추출된 하드 스킬과 소프트 스킬 데이터를 분석하고 핵심 역량을 도출해 주세요.

## 분석 대상
{display_category} 그래픽 디자이너 채용공고에서 추출한 역량 데이터입니다.

## 분석 목표
1. 유사하거나 중복된 스킬을 하나로 통합하세요 (예: "Photoshop"과 "포토샵"은 "Photoshop"으로 통합).
2. 스킬들을 중요도에 따라 순위를 매기고, 백분위 점수로 환산하세요.
3. {display_category} 그래픽 디자이너가 이력서를 작성할 때 반드시 포함해야 할 핵심 스킬을 추출하세요.
4. 모든 중요한 스킬(중요도 10점 이상)을 누락 없이 모두 포함하는 것이 가장 중요합니다.
5. 하드 스킬은 최소 10개 이상, 소프트 스킬은 최소 5개 이상 추출해주세요. 소프트 스킬이 부족하다면 유사한 개념을 세분화하거나 데이터에서 암시적으로 나타나는 역량을 추가로 도출해주세요.

## 분류 기준
1. 하드 스킬: 디자인 도구, 그래픽 디자인 기술, 인쇄/출판 지식, 레이아웃, 색채 이론 등을 포함합니다.
2. 소프트 스킬: 인성 역량만 포함하세요. 의사소통 능력, 협업 능력, 문제 해결 능력 등 대인관계와 관련된 스킬.""",

        "content-designer": f"""당신은 콘텐츠 디자이너/라이터 채용 시장 분석 전문가입니다. 다양한 콘텐츠 디자이너/라이터 채용공고(JD)에서 추출된 하드 스킬과 소프트 스킬 데이터를 분석하고 핵심 역량을 도출해 주세요.

## 분석 대상
{display_category} 콘텐츠 디자이너/라이터 채용공고에서 추출한 역량 데이터입니다.

## 분석 목표
1. 유사하거나 중복된 스킬을 하나로 통합하세요 (예: "카피라이팅"과 "카피 작성"은 "카피라이팅"으로 통합).
2. 스킬들을 중요도에 따라 순위를 매기고, 백분위 점수로 환산하세요.
3. {display_category} 콘텐츠 디자이너/라이터가 이력서를 작성할 때 반드시 포함해야 할 핵심 스킬을 추출하세요.
4. 모든 중요한 스킬(중요도 10점 이상)을 누락 없이 모두 포함하는 것이 가장 중요합니다.
5. 하드 스킬은 최소 10개 이상, 소프트 스킬은 최소 5개 이상 추출해주세요. 소프트 스킬이 부족하다면 유사한 개념을 세분화하거나 데이터에서 암시적으로 나타나는 역량을 추가로 도출해주세요.

## 분류 기준
1. 하드 스킬: 라이팅 스킬, 콘텐츠 제작 기술, 마케팅 지식, 도구 활용 능력, SEO 지식 등을 포함합니다.
2. 소프트 스킬: 인성 역량만 포함하세요. 의사소통 능력, 창의력, 협업 능력, 문제 해결 능력 등 대인관계와 관련된 스킬."""
    }
    
    return prompts.get(job_category)

def analyze_key_skills(executor, hard_skills, soft_skills, total_jds, job_category, experience_category):
    """Clova AI를 사용하여 핵심 스킬을 분석합니다."""
    
    # 하드 스킬과 소프트 스킬 메트릭스 계산
    hard_skill_metrics = calculate_skill_metrics(hard_skills)
    soft_skill_metrics = calculate_skill_metrics(soft_skills)
    
    # 스킬 데이터 준비
    hard_skill_data = []
    for skill, metrics in hard_skill_metrics.items():
        hard_skill_data.append({
            "skill": skill,
            "frequency": metrics['frequency'],
            "occurrence_rate": metrics['frequency'] / total_jds * 100,
            "avg_score": metrics['avg_score']
        })
    
    soft_skill_data = []
    for skill, metrics in soft_skill_metrics.items():
        soft_skill_data.append({
            "skill": skill,
            "frequency": metrics['frequency'],
            "occurrence_rate": metrics['frequency'] / total_jds * 100,
            "avg_score": metrics['avg_score']
        })
    
    # 중요도 순으로 정렬
    hard_skill_data.sort(key=lambda x: (x['occurrence_rate'] * 0.6 + x['avg_score'] * 0.4), reverse=True)
    soft_skill_data.sort(key=lambda x: (x['occurrence_rate'] * 0.6 + x['avg_score'] * 0.4), reverse=True)
    
    # 경력 표현 변경
    display_category = "신입" if experience_category == "new" else "경력"
    
    # 직무별 프롬프트 가져오기
    system_prompt = get_job_prompt(job_category, experience_category)
    
    if not system_prompt:
        print(f"에러: {job_category} 직무에 대한 프롬프트를 찾을 수 없습니다.")
        return None
    
    # 사용자 프롬프트 작성
    user_prompt = f"""다음은 {total_jds}개의 {display_category} {job_category} 채용공고(JD)에서 추출한 하드 스킬과 소프트 스킬 데이터입니다. 이 데이터를 분석하여 {display_category} {job_category}에게 필요한 핵심 역량을 도출해주세요.

## 하드 스킬 데이터 (상위 50개)
{json.dumps(hard_skill_data[:50], ensure_ascii=False, indent=2)}

## 소프트 스킬 데이터 (상위 40개)
{json.dumps(soft_skill_data[:40], ensure_ascii=False, indent=2)}"""

    # 데이터 길이 제한 처리
    if len(user_prompt) > 8000:
        # 데이터 크기 줄이기
        user_prompt = f"""다음은 {display_category} {job_category} 채용공고(JD)에서 추출한 하드 스킬과 소프트 스킬 데이터입니다. 데이터가 많아 상위 항목만 표시합니다.

## 하드 스킬 데이터 (상위 30개)
{json.dumps(hard_skill_data[:30], ensure_ascii=False, indent=2)}

## 소프트 스킬 데이터 (상위 20개)
{json.dumps(soft_skill_data[:20], ensure_ascii=False, indent=2)}"""

    # HCX-003 모델에 맞는 메시지 포맷으로 변경
    request_data = {
        'messages': [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        'topP': 0.8,
        'topK': 0,
        'maxTokens': 4000,
        'temperature': 0.1,
        'repeatPenalty': 5.0,
        'stopBefore': [],
        'includeAiFilters': True,
        'seed': 0
    }
    
    print(f"{display_category} {job_category} 채용 공고 핵심 스킬 분석 중...")
    try:
        result = executor.execute(request_data, stream=False)
        print(f"{display_category} {job_category} 분석 완료!")
        
        if result is None:
            print(f"{display_category} {job_category} - API에서 응답을 받지 못했습니다.")
            return None
            
        # JSON 추출 시도
        json_pattern = r'```(?:json)?\s*({[\s\S]*?})\s*```'
        match = re.search(json_pattern, result, re.DOTALL)
        
        if match:
            json_str = match.group(1).strip()
            try:
                # 직접 JSON으로 파싱 시도
                parsed_result = json.loads(json_str)
                
                # 하드 스킬과 소프트 스킬을 점수 기준으로 내림차순 정렬
                if "하드 스킬" in parsed_result:
                    parsed_result["하드 스킬"] = dict(sorted(parsed_result["하드 스킬"].items(), 
                                            key=lambda x: x[1], reverse=True))
                    parsed_result["하드 스킬(카테고리별)"] = categorize_hard_skills(parsed_result["하드 스킬"], job_category)
                
                if "소프트 스킬" in parsed_result:
                    parsed_result["소프트 스킬"] = dict(sorted(parsed_result["소프트 스킬"].items(), 
                                             key=lambda x: x[1], reverse=True))
                
                return parsed_result
                
            except json.JSONDecodeError:
                print(f"{display_category} {job_category} - JSON 파싱 실패, 응답 내용을 정제합니다.")
                
                # 백분위 표기 정제 (예: 74.41(백분위) -> 74.41)
                cleaned_json_str = re.sub(r'(\d+(?:\.\d+)?)\(백분위\)', r'\1', json_str)
                
                try:
                    # 정제된 문자열로 다시 시도
                    parsed_result = json.loads(cleaned_json_str)
                    
                    # 하드 스킬과 소프트 스킬을 점수 기준으로 내림차순 정렬
                    if "하드 스킬" in parsed_result:
                        parsed_result["하드 스킬"] = dict(sorted(parsed_result["하드 스킬"].items(), 
                                                key=lambda x: x[1], reverse=True))
                        parsed_result["하드 스킬(카테고리별)"] = categorize_hard_skills(parsed_result["하드 스킬"], job_category)
                    
                    if "소프트 스킬" in parsed_result:
                        parsed_result["소프트 스킬"] = dict(sorted(parsed_result["소프트 스킬"].items(), 
                                                 key=lambda x: x[1], reverse=True))
                    
                    return parsed_result
                    
                except json.JSONDecodeError:
                    print(f"{display_category} {job_category} - 정제 후에도 JSON 파싱 실패, 수동으로 파싱합니다.")
                    
                    # 응답에 구조화된 내용이 있는지 확인
                    if "하드 스킬" in result and "소프트 스킬" in result:
                        # 기본 구조 생성
                        skills_result = {
                            "하드 스킬": {},
                            "소프트 스킬": {},
                            "분석 결과": f"{display_category} {job_category}에게 필요한 핵심 역량 분석 결과"
                        }
                        
                        # 기존 데이터에서 상위 항목 추출
                        for i, skill_data in enumerate(hard_skill_data[:15]):
                            skill_name = skill_data["skill"]
                            importance = 100 - (i * 3)  # 순위에 따라 점수 부여
                            skills_result["하드 스킬"][skill_name] = importance
                        
                        for i, skill_data in enumerate(soft_skill_data[:10]):
                            skill_name = skill_data["skill"]
                            importance = 95 - (i * 5)  # 순위에 따라 점수 부여
                            skills_result["소프트 스킬"][skill_name] = importance
                        
                        skills_result["하드 스킬(카테고리별)"] = categorize_hard_skills(skills_result["하드 스킬"], job_category)
                        return skills_result
        
        # JSON 패턴 찾지 못한 경우
        print(f"{display_category} {job_category} - 구조화된 응답을 찾지 못함, 기본 결과를 반환합니다.")
        
        # 기본 결과 생성
        default_result = {
            "하드 스킬": {},
            "소프트 스킬": {},
            "분석 결과": f"{display_category} {job_category}에게 필요한 핵심 역량 분석 결과"
        }
        
        # 상위 스킬 추출
        for i, skill_data in enumerate(hard_skill_data[:15]):
            skill_name = skill_data["skill"]
            importance = 100 - (i * 3)  # 순위에 따라 점수 부여
            default_result["하드 스킬"][skill_name] = importance
        
        for i, skill_data in enumerate(soft_skill_data[:10]):
            skill_name = skill_data["skill"]
            importance = 95 - (i * 5)  # 순위에 따라 점수 부여
            default_result["소프트 스킬"][skill_name] = importance
        
        default_result["하드 스킬(카테고리별)"] = categorize_hard_skills(default_result["하드 스킬"], job_category)
        return default_result
            
    except Exception as e:
        print(f"{display_category} {job_category} 분석 중 오류 발생: {str(e)}")
        return None

def extract_key_skills_for_job(executor, job_category):
    """특정 직무에 대한 핵심 스킬을 추출합니다."""
    input_dir = f'jobs/{job_category}'
    
    # 디렉토리가 존재하는지 확인
    if not os.path.exists(input_dir):
        print(f"에러: {input_dir} 디렉토리를 찾을 수 없습니다.")
        return
    
    # 신입 JD 분석
    new_jd_path = os.path.join(input_dir, 'jd_analysis_new.json')
    new_output_path = os.path.join(input_dir, 'key_skills_new.json')
    
    if os.path.exists(new_jd_path):
        print(f"신입 {job_category} JD 분석 중...")
        new_jd_analysis = load_jd_analysis(new_jd_path)
        new_total_jds = len(new_jd_analysis)
        
        # 스킬 추출
        new_hard_skills, new_soft_skills = extract_skills(new_jd_analysis)
        
        # 핵심 스킬 분석 (Clova AI 사용)
        new_key_skills = analyze_key_skills(executor, new_hard_skills, new_soft_skills, new_total_jds, job_category, "new")
        
        if new_key_skills:
            # 결과 저장
            with open(new_output_path, 'w', encoding='utf-8') as f:
                json.dump(new_key_skills, f, ensure_ascii=False, indent=2)
            print(f"신입 {job_category} 분석 결과가 '{new_output_path}'에 저장되었습니다.")
    else:
        print(f"신입 {job_category} 분석 파일이 없습니다: {new_jd_path}")
    
    # 경력 JD 분석
    old_jd_path = os.path.join(input_dir, 'jd_analysis_old.json')
    old_output_path = os.path.join(input_dir, 'key_skills_old.json')
    
    if os.path.exists(old_jd_path):
        print(f"경력 {job_category} JD 분석 중...")
        old_jd_analysis = load_jd_analysis(old_jd_path)
        old_total_jds = len(old_jd_analysis)
        
        # 스킬 추출
        old_hard_skills, old_soft_skills = extract_skills(old_jd_analysis)
        
        # 핵심 스킬 분석 (Clova AI 사용)
        old_key_skills = analyze_key_skills(executor, old_hard_skills, old_soft_skills, old_total_jds, job_category, "old")
        
        if old_key_skills:
            # 결과 저장
            with open(old_output_path, 'w', encoding='utf-8') as f:
                json.dump(old_key_skills, f, ensure_ascii=False, indent=2)
            print(f"경력 {job_category} 분석 결과가 '{old_output_path}'에 저장되었습니다.")
    else:
        print(f"경력 {job_category} 분석 파일이 없습니다: {old_jd_path}")

def main():
    """모든 직무에 대한 핵심 스킬을 추출합니다."""
    # API 설정 - Clova AI 호출을 위한 설정
    completion_executor = CompletionExecutor(
        host='https://clovastudio.stream.ntruss.com',
        api_key='Bearer nv-9d109a0cd3fd45f98d1f8ae4cbf69f5dNM8S',
        request_id='key-skills-analyzer-' + str(int(time.time()))
    )
    
    # 모든 직무에 대해 핵심 스킬 추출
    job_categories = [
        "backend", "frontend", "data", "ai-ml", 
        "pm-po", "planning", "product-designer", 
        "graphic-designer", "content-designer"
    ]
    
    for job_category in job_categories:
        try:
            print(f"========== {job_category} 직무 분석 시작 ==========")
            extract_key_skills_for_job(completion_executor, job_category)
            print(f"========== {job_category} 직무 분석 완료 ==========\n")
        except Exception as e:
            print(f"{job_category} 분석 중 오류 발생: {str(e)}\n")

if __name__ == "__main__":
    main()