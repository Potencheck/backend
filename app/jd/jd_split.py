import json
import os
import glob

def split_jd_by_exp():
    """
    jobs 디렉토리 내의 모든 직무 폴더에서 jd_analysis_result.json 파일을 찾아
    신입/경력 기준으로 분류하여 jd_analysis_new.json, jd_analysis_old.json으로 저장합니다.
    """
    # jobs 디렉토리 내의 모든 폴더 찾기
    job_directories = glob.glob('jobs/*/')
    
    for job_dir in job_directories:
        result_file = os.path.join(job_dir, 'jd_analysis_result.json')
        
        # 결과 파일이 존재하는지 확인
        if not os.path.exists(result_file):
            print(f"{result_file} 파일이 없습니다. 건너뜁니다.")
            continue
        
        try:
            # 파일 읽기
            with open(result_file, 'r', encoding='utf-8') as f:
                jd_data = json.load(f)
            
            # 신입과 경력을 분리할 리스트 생성
            new_data = []
            old_data = []
            
            # 데이터 분류
            for jd in jd_data:
                if "경력" not in jd:
                    print(f"경력 필드가 없는 데이터를 발견했습니다: {jd.get('공고 제목', '제목 없음')}")
                    continue
                    
                career = jd["경력"]
                if "신입" in career:
                    new_data.append(jd)
                if "경력" in career:
                    old_data.append(jd)
            
            # 신입 데이터 저장
            new_file = os.path.join(job_dir, 'jd_analysis_new.json')
            with open(new_file, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)
            
            # 경력 데이터 저장
            old_file = os.path.join(job_dir, 'jd_analysis_old.json')
            with open(old_file, 'w', encoding='utf-8') as f:
                json.dump(old_data, f, ensure_ascii=False, indent=2)
            
            print(f"{job_dir} - 신입 데이터 {len(new_data)}개, 경력 데이터 {len(old_data)}개 분류 완료")
            
        except Exception as e:
            print(f"{job_dir} 처리 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    split_jd_by_exp() 