"""
KB신용정보 사규 PDF 문서를 파싱하기 위한 모듈
"""
import re
from typing import Dict, Any, List


def extract_metadata_from_pdf_text(text: str) -> Dict[str, Any]:
    """
    PDF 텍스트에서 메타데이터(제정일, 개정일 이력, 시행일)를 추출합니다.

    Args:
        text: PDF에서 추출한 텍스트

    Returns:
        메타데이터를 포함하는 사전
    """
    metadata = {
        "제정일": "",
        "개정일_이력": [],
        "시행일": "",
        "최종개정일": "",
        "소관부서": ""
    }

    # 처음 1000자 내에서 메타데이터 추출
    header_text = text[:1000]
    lines = header_text.split('\n')

    # 문서 제목 추출 (첫 번째 또는 두 번째 줄)
    for line in lines[:5]:
        line = line.strip()
        # 괄호 제거 후 제목 추출
        if line and not line.startswith('(') and not line.startswith('['):
            # "여 비 규 정" 형태의 제목
            if '규정' in line or '규칙' in line or '지침' in line or '세칙' in line:
                # 괄호 부분 제거
                title = re.sub(r'\(.*?\)', '', line).strip()
                if title and len(title) < 50:
                    metadata["문서제목"] = title
                    break

    # 소관부서 추출
    dept_match = re.search(r'\(소관부서\s*:\s*([^)]+)\)', header_text)
    if dept_match:
        metadata["소관부서"] = dept_match.group(1).strip()

    # 시행일 패턴 추출
    shihaeng_match = re.search(r'\[시행\s+([\d.\s]+)\]', header_text)
    if shihaeng_match:
        metadata["시행일"] = shihaeng_match.group(1).strip()

    # 제정/개정 이력 추출
    # 패턴: (1999. 10. 9. 제정) (2000. 3. 20. 개정) ...
    revision_pattern = re.findall(r'\(([\d.\s]+)\s*(제정|개정|일부개정|전부개정)\)', header_text)

    for date, rev_type in revision_pattern:
        date_cleaned = date.strip()

        # 제정일 추출
        if rev_type == "제정" and not metadata["제정일"]:
            metadata["제정일"] = date_cleaned

        # 개정일 이력에 추가
        metadata["개정일_이력"].append({
            "날짜": date_cleaned,
            "유형": rev_type
        })

        # 최종 개정일 업데이트
        if "개정" in rev_type:
            metadata["최종개정일"] = date_cleaned

    # 개정일 이력을 문자열로 변환
    if metadata["개정일_이력"]:
        revision_strings = [f"{item['날짜']} ({item['유형']})" for item in metadata["개정일_이력"]]
        metadata["개정일_이력_텍스트"] = ", ".join(revision_strings)

    return metadata


def extract_sections_from_pdf_text(text: str) -> List[Dict[str, Any]]:
    """
    PDF 텍스트에서 조문 구조를 추출합니다.

    Args:
        text: PDF에서 추출한 텍스트

    Returns:
        조문 리스트
    """
    sections = []
    lines = text.split('\n')

    # 제1장 또는 제1조가 나올 때까지 건너뛰기
    found_content_start = False
    current_section = None
    section_seq = 0

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # 페이지 번호 등 스킵
        if re.match(r'^\d+$', line):
            continue

        # 소관부서 정보 스킵
        if '소관부서' in line:
            continue

        # 문서 시작 감지
        if not found_content_start:
            if re.match(r'^제1장|^제1조', line):
                found_content_start = True
            else:
                continue

        # 부칙, 별표 등으로 끝나면 중단
        if re.match(r'^부\s*칙|^별\s*표|^<\s*별표', line):
            break

        # 조문 레벨 및 번호 감지
        level, number, content = parse_pdf_line(line)

        # 새로운 조문이 시작되는 경우
        if number:
            # 이전 조문이 있으면 저장
            if current_section:
                section_seq += 1
                sections.append({
                    "seq": section_seq,
                    "레벨": current_section["level"],
                    "내용": current_section["content"].strip(),
                    "번호": current_section["number"],
                    "관련이미지": []
                })

            # 새로운 조문 시작
            current_section = {
                "level": level,
                "number": number,
                "content": content
            }
        else:
            # 기존 조문의 연속 내용
            if current_section:
                # 공백으로 연결
                current_section["content"] += " " + line

    # 마지막 조문 저장
    if current_section:
        section_seq += 1
        sections.append({
            "seq": section_seq,
            "레벨": current_section["level"],
            "내용": current_section["content"].strip(),
            "번호": current_section["number"],
            "관련이미지": []
        })

    return sections


def parse_pdf_line(line: str) -> tuple:
    """
    PDF 텍스트 라인에서 레벨, 번호, 내용을 파싱합니다.

    Args:
        line: PDF 텍스트 한 줄

    Returns:
        (레벨, 번호, 내용) 튜플
    """
    # 제N장 형식
    match = re.match(r'^(제\d+장)\s+(.+)', line)
    if match:
        return 0, match.group(1), match.group(2)

    # 제N절 형식
    match = re.match(r'^(제\d+절)\s+(.+)', line)
    if match:
        return 0, match.group(1), match.group(2)

    # 제N조 형식 (괄호 있음)
    match = re.match(r'^(제\d+조)\s*\(([^)]+)\)\s*(.*)', line)
    if match:
        article_num = match.group(1)
        title = f"({match.group(2)})"
        content = match.group(3) if match.group(3) else ""
        return 1, article_num, f"{title} {content}".strip()

    # 제N조 형식 (괄호 없음)
    match = re.match(r'^(제\d+조)\s+(.+)', line)
    if match:
        return 1, match.group(1), match.group(2)

    # ① ② ③ 형식
    match = re.match(r'^([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])\s*(.+)', line)
    if match:
        return 3, match.group(1), match.group(2)

    # ⓛ (특수 문자)
    match = re.match(r'^(ⓛ)\s*(.+)', line)
    if match:
        return 3, match.group(1), match.group(2)

    # N. 형식 (숫자 점)
    match = re.match(r'^(\d+)\.\s*(.+)', line)
    if match:
        return 2, match.group(1) + ".", match.group(2)

    # N) 형식
    match = re.match(r'^(\d+)\)\s*(.+)', line)
    if match:
        return 2, match.group(1) + ")", match.group(2)

    # (N) 형식
    match = re.match(r'^\((\d+)\)\s*(.+)', line)
    if match:
        return 4, f"({match.group(1)})", match.group(2)

    # (가) (나) 형식
    match = re.match(r'^\(([가-힣])\)\s*(.+)', line)
    if match:
        return 4, f"({match.group(1)})", match.group(2)

    # 번호가 없는 경우
    return None, None, line


def parse_pdf_to_json(pdf_path: str) -> Dict[str, Any]:
    """
    PDF 파일을 파싱하여 JSON 구조로 변환합니다.

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        문서 정보와 조문 내용을 포함하는 딕셔너리
    """
    from .pdf_extractor import PDFTextExtractor

    # PDF 텍스트 추출
    extractor = PDFTextExtractor()
    text = extractor.extract_text_from_pdf(pdf_path)

    if not text:
        raise ValueError(f"PDF 파일에서 텍스트를 추출할 수 없습니다: {pdf_path}")

    # 메타데이터 추출
    metadata = extract_metadata_from_pdf_text(text)

    # 조문 추출
    sections = extract_sections_from_pdf_text(text)

    # 문서 정보 구성
    document_info = {
        "규정명": metadata.get("문서제목", ""),
        "제정일": metadata.get("제정일", ""),
        "최종개정일": metadata.get("최종개정일", ""),
        "시행일": metadata.get("시행일", ""),
        "소관부서": metadata.get("소관부서", ""),
        "조문갯수": len(sections),
        "개정이력": metadata.get("개정일_이력_텍스트", "")
    }

    # 최종 구조
    return {
        "문서정보": document_info,
        "조문내용": sections
    }
