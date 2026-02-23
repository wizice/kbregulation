"""
샘플 JSON 결과를 생성하고 저장하는 유틸리티
"""
import os
import sys
import json
from typing import Dict, Any

# 현재 디렉토리를 프로젝트 루트로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.json_converter import generate_sample_json


def create_sample_json(output_file: str = 'sample_result.json') -> Dict[str, Any]:
    """
    샘플 JSON 결과를 생성하고 파일로 저장합니다.
    
    Args:
        output_file: 출력 파일 경로
        
    Returns:
        생성된 샘플 JSON 구조
    """
    sample_json = generate_sample_json()
    
    # 파일로 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sample_json, f, ensure_ascii=False, indent=2)
    
    print(f"샘플 JSON 파일이 생성되었습니다: {output_file}")
    return sample_json


if __name__ == "__main__":
    # 커맨드 라인에서 실행하면 샘플 JSON 파일 생성
    output_path = 'sample_result.json'
    if len(sys.argv) > 1:
        output_path = sys.argv[1]
    
    sample_data = create_sample_json(output_path)
    
    # 콘솔에 출력
    print("\n샘플 JSON 구조:")
    print(json.dumps(sample_data, ensure_ascii=False, indent=2))

