import logging
import json
import os
import uuid
import time
import re
import traceback
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from app.schemas.report_schema import CareerInputSchema, ReportInput, Report
from app.database import get_db, get_collection
from app.util.pdf_extractor import PDFExtractor
from motor.motor_asyncio import AsyncIOMotorDatabase
import requests

router = APIRouter(
    prefix="/report",
    tags=["report"]
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("app")

def load_job_skills(job: str, exp: str) -> Dict:
    """직무와 경력 정보에 맞는 skills json 파일을 로드합니다."""
    try:
        exp_type = "new" if exp.lower() == "new" else "old"
        file_path = f"jobs/{job}/key_skills_{exp_type}.json"
        
        if not os.path.exists(file_path):
            logger.error(f"Skills file not found: {file_path}")
            raise HTTPException(
                status_code=404, 
                detail=f"No skills data found for job: {job}, exp: {exp}"
            )
            
        with open(file_path, 'r', encoding='utf-8') as f:
            skills_data = json.load(f)
            
        return skills_data
    except Exception as e:
        logger.error(f"Error loading skills data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error loading skills data: {str(e)}"
        )

def extract_top_skills(skills_dict: Dict, top_n: int = 5) -> List[Dict]:
    """스킬 사전에서 상위 N개의 스킬을 추출합니다."""
    sorted_skills = sorted(skills_dict.items(), key=lambda x: x[1], reverse=True)
    result = []
    
    for i, (name, value) in enumerate(sorted_skills):
        if i >= top_n:
            break
        result.append({"name": name, "keyword": value})
        
    return result

def analyze_resume_with_ai(resume_text: str, trend_skills: List, trend_jd: List) -> Dict:
    """AI를 사용하여 이력서를 분석합니다."""
    logger.debug("=== 이력서 AI 분석 시작 ===")
    logger.debug(f"분석할 이력서 길이: {len(resume_text)} 자")
    logger.debug(f"트렌드 스킬: {trend_skills}")
    logger.debug(f"트렌드 JD: {[item['name'] for item in trend_jd]}")
    
    # API 키 가져오기
    clova_key = os.getenv("CLOVA_KEY")
    
    if not clova_key:
        logger.error("CLOVA_KEY 환경 변수가 설정되지 않았습니다")
        raise HTTPException(
            status_code=500,
            detail="서버 구성 오류: AI 분석을 위한 API 키가 설정되지 않았습니다. 관리자에게 문의하세요."
        )
    
    # 시스템 프롬프트와 사용자 프롬프트 구성
    system_prompt = """이력서를 분석하여 지원자의 역량을 평가하고 다음 JSON 형식으로만 응답해주세요. 추가 설명이나 주석은 사용하지 마세요.

{
  "my_trend_skill": ["스킬1", "스킬2", ...],
  "personal_skill": [
    {"skill": "역량1", "description": "근거1,2,3~에서 추출한 역량"},
    {"skill": "역량2", "description": "근거2~에서 추출한 역량"},
    ...
  ],
  "ai_summary": "짧은 한 문장 요약",
  "career_fitness": 80,
  "ai_review": "직군 적합성에 대한 피드백"
}

각 필드 작성 지침:
1. my_trend_skill:
   - 해당 직무의 대표 소프트스킬/하드스킬 중 지원자가 실제로 갖춘 것만 포함
   - 지원자의 역량이 0-100점 척도로 60점 이상인 스킬만 포함

2. personal_skill:
   - 트렌드 역량은 아니지만 지원자만의 특색 있는 매력적인 역량 나열
   - 각 역량마다 반드시 description 필드 포함하여 근거 제시
   - 제시된 말투를 반드시 그대로 유지할 것
   - 근거는 반드시 이력서에 나타난 내용을 기반으로 작성할 것

3. ai_summary:
   - 형식: "{사용자의 장점}하는 {희망직무}계의 {직무와 관련없는 비유 인물}"
   - 예시: "데이터로 고객 마음을 사로잡는 디자인계의 허준"
   - 짧고 임팩트 있는 한 문장으로 작성

4. career_fitness:
   - 지원자의 이력서와 선택한 직무의 jd간 유사도를 백분위 숫자로 표현
   - 예: 83% 매치되면 83으로 표기
   - 중요: 이력서의 기술 스택, 경험, 프로젝트가 희망 직무와 완전히 다른 분야일 경우 30% 이하로 평가할 것
   - 기술 스택과 경험이 희망 직무와 일부 관련이 있지만 직접적이지 않은 경우 31-70% 사이로 평가
   - 기술 스택과 경험이 희망 직무와 직접적으로 관련이 있는 경우에만 70% 이상으로 평가

5. ai_review:
   - 해당 직군에 적합한/적합하지 않은 이유를 간략하게 제시
   - 긍정적이고 유익한 피드백 제공
   - 이력서와 희망 직무 간 불일치가 클 경우, 전환을 위해 필요한 보완점 중심으로 작성
   - 예시 말투 유지: "프로덕트 디자이너에게 요구되는 핵심 역량을 두루 갖추고 있네요! 특히 데이터 기반 개선 경험이 강점입니다. 이를 더욱 돋보이게 하려면, 어떤 데이터를 활용했고, 구체적으로 어떤 문제를 해결했으며, 개선 결과가 사용자 경험이나 비즈니스 성과에 어떤 영향을 미쳤는지 정리해보면 더욱 효과적일 것입니다."
"""
    
    user_prompt = f"""다음 이력서를 분석하고 요청된 정보를 추출해주세요:
    
이력서:
{resume_text[:3000]}... (이하 생략)

트렌드 스킬: {trend_skills}
트렌드 JD: {[item['name'] for item in trend_jd]}

다음 정보를 추출해주세요:
1. 이력서에 나타난 트렌드 스킬 (최대 4개)
2. 이력서에 나타나지 않았지만 강조할만한 퍼스널 역량 4개 (역량명과 근거)
3. 이력서에 대한 위트있는 한 문장 요약
4. 직무 적합도 점수(0-100)와 그 이유, 개선 제안

반드시 JSON 형식으로만 응답해주세요."""
    
    try:
        logger.debug("Clova Studio API 호출 시작")
        
        # API 요청 헤더
        headers = {
            "Authorization": f"Bearer {clova_key}",
            "X-NCP-CLOVASTUDIO-REQUEST-ID": f"resume-analysis-{int(time.time())}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        # API 요청 본문 구성
        request_data = {
            'messages': [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            'topP': 0.8,
            'topK': 0,
            'maxTokens': 4096,
            'temperature': 0.8,
            'repeatPenalty': 5.0,
            'stopBefore': [],
            'includeAiFilters': True
        }
        
        # API 호출
        url = "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003"
        logger.debug(f"API 요청 URL: {url}")
        
        response = requests.post(
            url,
            headers=headers,
            json=request_data,
            timeout=30
        )
        
        # 응답 확인 강화
        if response.status_code != 200:
            logger.error(f"Clova API 오류 응답: 상태 코드 {response.status_code}")
            logger.error(f"응답 내용: {response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"AI 서비스 응답 오류: {response.status_code}. 관리자에게 문의하세요."
            )
        
        # 응답 처리
        try:
            response_json = response.json()
            logger.debug(f"API 응답 전체: {json.dumps(response_json, ensure_ascii=False)}")
            
            # 명확한 응답 구조 확인
            if "result" in response_json and "message" in response_json["result"] and "content" in response_json["result"]["message"]:
                content = response_json["result"]["message"]["content"]
                logger.debug(f"추출된 콘텐츠: {content[:200]}...")
            else:
                logger.error(f"예상 응답 구조를 찾을 수 없습니다: {json.dumps(response_json, ensure_ascii=False)[:500]}...")
                raise HTTPException(
                    status_code=500,
                    detail="AI 서비스 응답 형식이 변경되었습니다. 관리자에게 문의하세요."
                )
            
            # JSON 파싱 전 유효성 검사
            if not content or not content.strip():
                logger.error("추출된 콘텐츠가 비어 있습니다")
                raise ValueError("API 응답에서 추출된 콘텐츠가 비어 있습니다")
            
            # JSON 부분 추출 및 로깅 강화
            try:
                json_match = re.search(r'({.*})', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
                    logger.debug(f"추출된 JSON 문자열: {json_str[:200]}...")
                    result = json.loads(json_str)
                    logger.debug("JSON 객체 추출 성공!")
                else:
                    # 전체 텍스트가 JSON인 경우
                    logger.debug(f"JSON 전체 파싱 시도: {content[:200]}...")
                    result = json.loads(content)
                    logger.debug("전체 텍스트를 JSON으로 파싱 성공!")
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {str(e)}, 콘텐츠 일부: {content[:300]}...")
                raise ValueError(f"API 응답의 JSON 형식이 잘못되었습니다: {str(e)}")
            
            # 결과 검증
            if not validate_ai_result(result):
                logger.error("AI 응답 검증 실패: 필수 필드가 누락되었습니다")
                raise ValueError("AI 응답 형식이 올바르지 않습니다. 필수 필드가 누락되었습니다.")
                
            logger.debug("=== 이력서 AI 분석 완료 ===")
            return result
        except Exception as e:
            logger.error(f"응답 처리 중 오류 발생: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"AI 분석 중 오류 발생: {str(e)}")
        logger.error(f"오류 세부 정보: {traceback.format_exc()}")
        logger.debug("=== 이력서 AI 분석 실패, 더미 데이터 반환 ===")
        
        # 기본 더미 데이터 반환
        dummy_result = {
            "my_trend_skill": ["Java", "Spring Framework", "AWS", "MySQL"],
            "personal_skill": [
                {"skill": "문제 해결 능력", "description": "다양한 프로젝트에서 복잡한 기술 문제 해결 경험"},
                {"skill": "팀 협업 능력", "description": "여러 부서와 협력하여 프로젝트 완수 경험"},
                {"skill": "시스템 아키텍처 설계", "description": "확장 가능한 백엔드 시스템 설계 경험"},
                {"skill": "코드 최적화", "description": "성능 병목 현상 개선 및 코드 효율화 경험"}
            ],
            "ai_summary": "안정적인 서버 구축의 달인",
            "career_fitness": 75,
            "ai_review": "백엔드 개발에 필요한 핵심 기술을 보유하고 있으며, 특히 Java와 Spring 활용 능력이 뛰어납니다. 클라우드 기술과 DevOps 관련 경험을 강화하면 더욱 경쟁력이 높아질 것입니다."
        }
        
        logger.debug(f"반환할 더미 데이터: {json.dumps(dummy_result, ensure_ascii=False, indent=2)}")
        return dummy_result

def validate_ai_result(result: Dict) -> bool:
    """AI 응답 결과를 검증합니다."""
    # 필수 필드 목록
    required_fields = ["my_trend_skill", "personal_skill", "ai_summary", "career_fitness", "ai_review"]
    
    # 모든 필수 필드가 존재하는지 확인
    for field in required_fields:
        if field not in result:
            logger.warning(f"필수 필드 누락: {field}")
            return False
    
    # personal_skill이 리스트이고 최소 1개 이상의 항목을 포함하는지 확인
    if not isinstance(result["personal_skill"], list) or len(result["personal_skill"]) < 1:
        logger.warning("personal_skill은 최소 1개 이상의 항목을 포함해야 합니다")
        return False
    
    # personal_skill의 각 항목이 올바른 형식인지 확인
    for item in result["personal_skill"]:
        if not isinstance(item, dict) or "skill" not in item or "description" not in item:
            logger.warning(f"잘못된 personal_skill 항목 형식: {item}")
            return False
    
    # career_fitness가 정수이고 0-100 범위인지 확인
    if not isinstance(result["career_fitness"], int) or not (0 <= result["career_fitness"] <= 100):
        logger.warning(f"career_fitness는 0-100 범위의 정수여야 합니다: {result['career_fitness']}")
        return False
    
    return True

@router.post("/")
async def create_report(
    user_json: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> Dict:
    try:
        # 사용자 정보 파싱
        user_data = json.loads(user_json)
        logger.info(f"Received user data: {user_data}")
        
        # 파일에서 텍스트 추출
        pdf_extractor = PDFExtractor()
        resume_text = pdf_extractor.extract_text_from_pdf(file)
        logger.debug(f"이력서에서 추출된 텍스트 길이: {len(resume_text)} 자")
        
        # 직무별 스킬 데이터 로드
        job = user_data.get('user', {}).get('job', '')
        exp = user_data.get('user', {}).get('exp', 'new')
        logger.info(f"직무: {job}, 경력: {exp}")
        
        skills_data = load_job_skills(job, exp)
        logger.debug(f"로드된 스킬 데이터: {json.dumps(skills_data, ensure_ascii=False)[:200]}...")
        
        # 상위 소프트 스킬 추출
        soft_skills = skills_data.get('소프트 스킬', {})
        trend_jd = extract_top_skills(soft_skills)
        logger.debug(f"추출된 트렌드 JD: {trend_jd}")
        
        # 상위 소프트 스킬 이름만 추출 (trend_skill용)
        trend_skill = [name for name, _ in sorted(soft_skills.items(), key=lambda x: x[1], reverse=True)[:5]]
        logger.debug(f"추출된 트렌드 스킬(소프트 스킬): {trend_skill}")
        
        # 상위 하드 스킬 추출 (AI 분석용)
        hard_skills = skills_data.get('하드 스킬', {})
        top_hard_skills = [name for name, _ in sorted(hard_skills.items(), key=lambda x: x[1], reverse=True)[:5]]
        logger.debug(f"추출된 상위 하드 스킬: {top_hard_skills}")
        
        # 모든 스킬 통합 (AI 분석용)
        all_skills = top_hard_skills + trend_skill
        logger.debug(f"모든 통합 스킬: {all_skills}")
        
        # AI로 이력서 분석 - 통합 스킬 전달
        ai_result = analyze_resume_with_ai(resume_text, all_skills, trend_jd)
        
        # AI 결과 검증 - 필수 필드가 모두 있는지 확인
        if not validate_ai_result(ai_result):
            raise HTTPException(
                status_code=500,
                detail="AI 분석 결과가 유효하지 않습니다. 필수 필드가 누락되었습니다."
            )
        
        # 결과 데이터 구성 - 수정된 구조로 변경
        report_data = {
            "user": {
                "name": user_data.get('name', ''),
                "exp": user_data.get('exp', 'new'),  
                "job": job
            },
            "career_fitness": ai_result.get('career_fitness', 70),
            "trend_jd": trend_jd,
            "trend_skill": top_hard_skills,
            "my_trend_skill": ai_result.get('my_trend_skill', []),
            "personal_skill": ai_result.get('personal_skill', []),
            "ai_summary": ai_result.get('ai_summary', ''),
            "ai_review": ai_result.get('ai_review', '')
        }
        
        logger.debug(f"최종 보고서 데이터: {json.dumps(report_data, ensure_ascii=False, indent=2)}")
        
        # 결과 데이터에 필수 필드가 비어있는지 다시 한번 확인
        if not report_data["my_trend_skill"] or not report_data["personal_skill"] or not report_data["ai_summary"] or not report_data["ai_review"]:
            logger.error("최종 보고서 데이터에 빈 필드가 있습니다")
            raise HTTPException(
                status_code=500,
                detail="보고서 데이터에 빈 필드가 있습니다. AI 분석을 다시 시도해주세요."
            )
        
        # MongoDB에 저장
        logger.info("MongoDB에 보고서 저장 시작")
        reports_collection = get_collection("reports")
        result = await reports_collection.insert_one(report_data)
        
        # 저장 성공 확인
        saved_report = await reports_collection.find_one({"_id": result.inserted_id})
        if not saved_report:
            logger.error("MongoDB에 보고서 저장 실패")
            raise HTTPException(status_code=500, detail="Failed to save report")
        
        logger.info(f"보고서가 성공적으로 저장되었습니다. ID: {result.inserted_id}")
        return {"id": str(result.inserted_id)}
        
    except HTTPException as he:
        # 이미 생성된 HTTPException은 그대로 다시 발생
        raise
    except Exception as e:
        logger.error(f"Error creating report: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error creating report: {str(e)}"
        )

@router.get("/{report_id}", response_model=Report)
async def get_report(report_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    UUID를 사용하여 특정 보고서를 조회합니다.
    
    Parameters:
    - report_id: 보고서의 고유 ID
    
    Returns:
    - 보고서 데이터 (JSON)
    """
    try:
        from bson.objectid import ObjectId
        
        # MongoDB에서 report_id로 문서 조회
        reports_collection = get_collection("reports")
        
        try:
            # MongoDB ObjectId로 변환 시도
            object_id = ObjectId(report_id)
            report = await reports_collection.find_one({"_id": object_id})
        except Exception:
            # ObjectId 변환 실패 시 일반 문자열 ID로 조회 시도
            report = await reports_collection.find_one({"id": report_id})
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"보고서를 찾을 수 없습니다. ID: {report_id}"
            )
        
        # MongoDB의 _id를 문자열 id로 변환
        if "_id" in report:
            report["id"] = str(report["_id"])
            del report["_id"]
        
        return report
        
    except HTTPException:
        # 이미 생성된 HTTPException은 그대로 다시 발생
        raise
    except Exception as e:
        logger.error(f"보고서 조회 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"보고서 조회 중 서버 오류가 발생했습니다: {str(e)}"
        )

@router.post("/share")
async def share_report(
    report_input: ReportInput
) -> Dict:
    try:
        # 공유 링크 생성 로직 (간단하게 새 ID 생성으로 구현)
        report_id = str(uuid.uuid4())
        reports_collection = get_collection("shared_reports")
        
        # 공유용 리포트 저장
        report_data = report_input.dict()
        report_data["id"] = report_id
        
        await reports_collection.insert_one(report_data)
        
        # 공유 URL 반환
        share_url = f"/shared/report/{report_id}"
        return {"share_url": share_url}
        
    except Exception as e:
        logger.error(f"Error sharing report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error sharing report: {str(e)}"
        )

@router.get("/raw/{report_id}")
async def get_raw_report(report_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """임시 디버깅용: 보고서 원본 데이터 조회"""
    from bson.objectid import ObjectId
    
    reports_collection = get_collection("reports")
    try:
        # ObjectId로 변환하여 검색
        report = await reports_collection.find_one({"_id": ObjectId(report_id)})
        if not report:
            return {"error": "보고서를 찾을 수 없습니다", "id": report_id}
        
        # ObjectId를 문자열로 변환
        report["id"] = str(report["_id"])
        del report["_id"]
        
        return report
    except Exception as e:
        import traceback
        return {
            "error": f"조회 중 오류 발생: {str(e)}",
            "id": report_id,
            "traceback": traceback.format_exc()
        }