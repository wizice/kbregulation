"""
문서 구조를 1차원 JSON 배열 형식으로 변환하는 모듈
"""
import json
import re
from typing import Dict, List, Any, Optional


def parse_document_structure(metadata: Dict[str, str], content_structure: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    메타데이터와 내용 구조를 결합하여 전체 문서 구조를 생성합니다.
    
    Args:
        metadata: 메타데이터 사전
        content_structure: 내용 구조 리스트
        
    Returns:
        문서 구조를 나타내는 사전
    """
    # 문서 제목 추출 - 첫 번째 줄이나 메타데이터에서 파일명을 기준으로
    doc_title = ""
    if "문서제목" in metadata:
        doc_title = metadata["문서제목"]
    elif content_structure and content_structure[0] and "content" in content_structure[0]:
        doc_title = content_structure[0].get("content", "").replace("1.1.1.", "").strip()
    
    # 정규화된 메타데이터 생성
    related_standards = []
    if "관련기준" in metadata and metadata["관련기준"]:
        related_standards = [item.strip() for item in metadata["관련기준"].split("\n") if item.strip()]
    
    # 문서 정보 구성
    document_info = {
        "규정명": doc_title,
        "내규종류": "규정",  # 기본값
        "규정표기명": doc_title,
        "제정일": metadata.get("제정일", "").strip(),
        "최종개정일": metadata.get("최종개정일", "").strip(),
        "최종검토일": metadata.get("최종검토일", "").strip(),
        "담당부서": metadata.get("담당부서", "").strip(),
        "관련기준": related_standards,
        "조문갯수": len(content_structure)
    }
    
    # 섹션 처리 및 1차원 배열 생성
    sections = process_sections_flat(content_structure)
    
    # 문서 구조 정의
    document_structure = {
        "문서정보": document_info,
        "조문내용": sections
    }
    
    return document_structure


def create_document_structure(document_info: Dict[str, Any], sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    문서 정보와 섹션 내용을 결합하여 문서 구조를 생성합니다.
    
    Args:
        document_info: 문서 정보 사전
        sections: 섹션 내용 리스트
        
    Returns:
        문서 구조를 나타내는 사전
    """
    return {
        "문서정보": document_info,
        "조문내용": sections
    }


def process_sections_flat(content_structure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    내용 구조를 처리하여 1차원 배열로 변환합니다.
    추출된 번호를 유지하여 순차적으로 증가하는 번호를 표시합니다.
    
    Args:
        content_structure: 내용 구조 리스트
        
    Returns:
        1차원 섹션 배열
    """
    flat_sections = []
    seq = 1
    
    for section in content_structure:
        section_number, section_title = extract_section_info(section["content"])
        extracted_number = section.get("number", "")
        
        flat_sections.append({
            "seq": seq,
            "레벨": section["level"],
            "내용": section["content"],
            "원본내용": section.get("original_content", section["content"]),
            "번호": extracted_number or section_number,
            "관련이미지": []
        })
        seq += 1
        
        # 하위 섹션 처리
        if section.get("subsections"):
            for subsection in section["subsections"]:
                subsection_number, subsection_title = extract_section_info(subsection["content"])
                extracted_sub_number = subsection.get("number", "")
                
                flat_sections.append({
                    "seq": seq,
                    "레벨": subsection["level"],
                    "내용": subsection["content"],
                    "원본내용": subsection.get("original_content", subsection["content"]),
                    "번호": extracted_sub_number or subsection_number,
                    "관련이미지": []
                })
                seq += 1
    
    return flat_sections


def extract_section_info(text: str) -> tuple:
    """
    섹션 텍스트에서 번호와 제목을 추출합니다.
    
    Args:
        text: 섹션 텍스트
        
    Returns:
        (번호, 제목) 튜플
    """
    # 1. (목적) 패턴
    level1_match = re.match(r'^(\d+)\.\s*\(([^)]+)\)', text)
    if level1_match:
        return level1_match.group(1), level1_match.group(2)
    
    # 제1조 (목적) 패턴
    level1_alt_match = re.match(r'^제(\d+)조\s*\(([^)]+)\)', text)
    if level1_alt_match:
        return f"제{level1_alt_match.group(1)}조", level1_alt_match.group(2)
    
    # 1-1. 정확한 환자 확인 패턴
    level2_match = re.match(r'^(\d+-\d+)\.\s*(.*?)(?::|$)', text)
    if level2_match:
        return level2_match.group(1), level2_match.group(2)
    
    # a. 약물 투여 전 패턴
    level3_match = re.match(r'^([a-z])\.\s*(.*)', text)
    if level3_match:
        return level3_match.group(1), level3_match.group(2)
    
    # 1) 패턴 - 스킵
    # level3_numbered_match = re.match(r'^\s*(\d+)\)\s*(.*)', text)
    # if level3_numbered_match:
    #     return level3_numbered_match.group(1), level3_numbered_match.group(2)
    
    # ① 패턴 (동그라미 숫자)
    level3_circle_match = re.match(r'^\s*([①②③④⑤⑥⑦⑧⑨⑩])\s*(.*)', text)
    if level3_circle_match:
        circle_numbers = "①②③④⑤⑥⑦⑧⑨⑩"
        number = circle_numbers.index(level3_circle_match.group(1)) + 1
        return str(number), level3_circle_match.group(2)
    
    return "", text


def save_to_json(document_structure: Dict[str, Any], output_file: str) -> None:
    """
    문서 구조를 JSON 파일로 저장합니다.
    
    Args:
        document_structure: 문서 구조 사전
        output_file: 출력 파일 경로
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(document_structure, f, ensure_ascii=False, indent=2)


def convert_to_json_string(document_structure: Dict[str, Any]) -> str:
    """
    문서 구조를 JSON 문자열로 변환합니다.
    
    Args:
        document_structure: 문서 구조 사전
        
    Returns:
        JSON 문자열
    """
    return json.dumps(document_structure, ensure_ascii=False, indent=2)


def generate_sample_json() -> Dict[str, Any]:
    """
    샘플 JSON 구조를 생성합니다. (개발 및 테스트용)
    
    Returns:
        샘플 JSON 구조
    """
    return {
        "문서정보": {
            "규정명": "정확한 환자 확인",
            "내규종류": "규정",
            "규정표기명": "정확한 환자 확인",
            "제정일": "2008.09.",
            "최종개정일": "2025.03.25.",
            "최종검토일": "2025.03.25.",
            "담당부서": "의료질향상 및 환자안전위원회",
            "관련기준": [
                "4주기 의료기관인증기준: 1.1 정확한 환자 확인",
                "JCI Standard 7th Edition: IPSG.1"
            ],
            "조문갯수": 24
        },
        "조문내용": [
            {
                "seq": 1,
                "레벨": 1,
                "내용": "제1조 (목적)",
                "번호": "제1조",
                "관련이미지": []
            },
            {
                "seq": 2,
                "레벨": 2,
                "내용": "1. 환자확인과 관련하여 발생할 수 있는 오류를 예방하기 위해 모든 직원이 일관되고 정확하게 환자확인을 수행하기 위함이다.",
                "번호": "1.",
                "관련이미지": []
            },
            {
                "seq": 3,
                "레벨": 1,
                "내용": "제2조 (정의)",
                "번호": "제2조",
                "관련이미지": []
            },
            {
                "seq": 4,
                "레벨": 2,
                "내용": "1. 정확한 환자 확인: 환자 이름과 등록번호 두 가지 지표를 사용하여 환자를 정확하게 확인하는 절차",
                "번호": "1.",
                "관련이미지": []
            },
            {
                "seq": 5,
                "레벨": 1,
                "내용": "제3조 (절차)",
                "번호": "제3조",
                "관련이미지": []
            },
            {
                "seq": 6,
                "레벨": 2,
                "내용": "1. 환자 확인이 필요한 시점",
                "번호": "1.",
                "관련이미지": []
            },
            {
                "seq": 7,
                "레벨": 3,
                "내용": "1) 약물 투여 전",
                "번호": "1)",
                "관련이미지": []
            },
            {
                "seq": 8,
                "레벨": 3,
                "내용": "2) 혈액 및 혈액제제 투여 전",
                "번호": "2)",
                "관련이미지": []
            },
            {
                "seq": 9,
                "레벨": 3,
                "내용": "3) 진단적 검사 시행 전",
                "번호": "3)",
                "관련이미지": []
            },
            {
                "seq": 10,
                "레벨": 3,
                "내용": "4) 진료, 치료, 처치 및 시술 전",
                "번호": "4)",
                "관련이미지": []
            },
            {
                "seq": 11,
                "레벨": 3,
                "내용": "5) 혈액 및 기타 검체 채취 전",
                "번호": "5)",
                "관련이미지": []
            },
            {
                "seq": 12,
                "레벨": 3,
                "내용": "6) 환자 이송 시",
                "번호": "6)",
                "관련이미지": []
            },
            {
                "seq": 13,
                "레벨": 3,
                "내용": "7) 치료식이 제공 전",
                "번호": "7)",
                "관련이미지": []
            },
            {
                "seq": 14,
                "레벨": 3,
                "내용": "8) 진료 및 치료 관련 라벨링 시(혈액 및 기타 검체, 식판, 모유 등)",
                "번호": "8)",
                "관련이미지": []
            },
            {
                "seq": 15,
                "레벨": 3,
                "내용": "9) 기타 서비스 제공 시",
                "번호": "9)",
                "관련이미지": []
            },
            {
                "seq": 16,
                "레벨": 2,
                "내용": "2. 환자 확인 수행자",
                "번호": "2.",
                "관련이미지": []
            },
            {
                "seq": 17,
                "레벨": 3,
                "내용": "1) 환자 확인이 필요한 시점에 해당 행위를 수행하는 자가 환자 확인을 수행한다.",
                "번호": "1)",
                "관련이미지": []
            },
            {
                "seq": 18,
                "레벨": 2,
                "내용": "3. 정확한 환자 확인 방법",
                "번호": "3.",
                "관련이미지": []
            },
            {
                "seq": 19,
                "레벨": 2,
                "내용": "4. 입원환자 대상 정확한 환자 확인 방법",
                "번호": "4.",
                "관련이미지": []
            },
            {
                "seq": 20,
                "레벨": 2,
                "내용": "5. 외래환자 및 가정간호 환자 확인 방법",
                "번호": "5.",
                "관련이미지": []
            },
            {
                "seq": 21,
                "레벨": 2,
                "내용": "6. 헌혈실 내 환자 확인 방법",
                "번호": "6.",
                "관련이미지": []
            },
            {
                "seq": 22,
                "레벨": 2,
                "내용": "7. 방사선 치료 환자의 환자 확인 방법",
                "번호": "7.",
                "관련이미지": []
            },
            {
                "seq": 23,
                "레벨": 1,
                "내용": "제4조 (부록)",
                "번호": "제4조",
                "관련이미지": []
            },
            {
                "seq": 24,
                "레벨": 1,
                "내용": "제5조 (참고)",
                "번호": "제5조",
                "관련이미지": []
            }
        ]
    }



def extract_section_info(text: str) -> tuple:
    """
    섹션 텍스트에서 번호와 제목을 추출합니다.
    
    Args:
        text: 섹션 텍스트
        
    Returns:
        (번호, 제목) 튜플
    """
    # 1. (목적) 패턴
    level1_match = re.match(r'^(\d+)\.\s*\(([^)]+)\)', text)
    if level1_match:
        return level1_match.group(1), level1_match.group(2)
    
    # 1-1. 정확한 환자 확인 패턴
    level2_match = re.match(r'^(\d+-\d+)\.\s*(.*?)(?::|$)', text)
    if level2_match:
        return level2_match.group(1), level2_match.group(2)
    
    # a. 약물 투여 전 패턴
    level3_match = re.match(r'^([a-z])\.\s*(.*)', text)
    if level3_match:
        return level3_match.group(1), level3_match.group(2)
    
    return "", text


def save_to_json(document_structure: Dict[str, Any], output_file: str) -> None:
    """
    문서 구조를 JSON 파일로 저장합니다.
    
    Args:
        document_structure: 문서 구조 사전
        output_file: 출력 파일 경로
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(document_structure, f, ensure_ascii=False, indent=2)


def convert_to_json_string(document_structure: Dict[str, Any]) -> str:
    """
    문서 구조를 JSON 문자열로 변환합니다.
    
    Args:
        document_structure: 문서 구조 사전
        
    Returns:
        JSON 문자열
    """
    return json.dumps(document_structure, ensure_ascii=False, indent=2)


def generate_sample_json() -> Dict[str, Any]:
    """
    샘플 JSON 구조를 생성합니다. (개발 및 테스트용)
    
    Returns:
        샘플 JSON 구조
    """
    return {
        "문서정보": {
            "규정명": "정확한 환자 확인",
            "내규종류": "규정",
            "규정표기명": "정확한 환자 확인",
            "제정일": "2008.09.",
            "최종개정일": "2025.03.25.",
            "최종검토일": "2025.03.25.",
            "담당부서": "의료질향상 및 환자안전위원회",
            "관련기준": [
                "4주기 의료기관인증기준: 1.1 정확한 환자 확인",
                "JCI Standard 7th Edition: IPSG.1"
            ],
            "조문갯수": 16
        },
        "조문내용": [
            {
                "seq": 1,
                "레벨": 1,
                "내용": "1. (목적)",
                "관련이미지": []
            },
            {
                "seq": 2,
                "레벨": 2,
                "내용": "1-1. 환자확인과 관련하여 발생할 수 있는 오류를 예방하기 위해 모든 직원이 일관되고 정확하게 환자확인을 수행하기 위함이다.",
                "관련이미지": []
            },
            {
                "seq": 3,
                "레벨": 1,
                "내용": "2. (정의)",
                "관련이미지": []
            },
            {
                "seq": 4,
                "레벨": 2,
                "내용": "2-1. 정확한 환자 확인: 환자 이름과 등록번호 두 가지 지표를 사용하여 환자를 정확하게 확인하는 절차",
                "관련이미지": []
            },
            {
                "seq": 5,
                "레벨": 1,
                "내용": "3. (절차)",
                "관련이미지": []
            },
            {
                "seq": 6,
                "레벨": 2,
                "내용": "3-1. 환자 확인이 필요한 시점",
                "관련이미지": []
            },
            {
                "seq": 7,
                "레벨": 2,
                "내용": "3-2. 환자 확인 수행자",
                "관련이미지": []
            },
            {
                "seq": 8,
                "레벨": 2,
                "내용": "3-3. 정확한 환자 확인 방법",
                "관련이미지": []
            },
            {
                "seq": 9,
                "레벨": 2,
                "내용": "3-4. 입원환자 대상 정확한 환자 확인 방법",
                "관련이미지": []
            },
            {
                "seq": 10,
                "레벨": 2,
                "내용": "3-5. 외래환자 및 가정간호 환자 확인 방법",
                "관련이미지": []
            },
            {
                "seq": 11,
                "레벨": 2,
                "내용": "3-6. 헌혈실 내 환자 확인 방법",
                "관련이미지": []
            },
            {
                "seq": 12,
                "레벨": 2,
                "내용": "3-7. 방사선 치료 환자의 환자 확인 방법",
                "관련이미지": []
            },
            {
                "seq": 13,
                "레벨": 1,
                "내용": "4. (부록)",
                "관련이미지": []
            },
            {
                "seq": 14,
                "레벨": 1,
                "내용": "5. (참고)",
                "관련이미지": []
            }
        ]
    }

