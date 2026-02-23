"""
app.py와 통합하기 위한 이미지 추출 유틸리티 모듈
"""
import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple

# 이미지 추출 클래스 가져오기
from utils.docx_image_extractor import DocxImageExtractor
from utils.enhanced_table_converter import EnhancedTableConverter


def is_article_5_or_later(section_number: str) -> bool:
    """제5조 이상인지 확인하는 함수"""
    import re
    if not section_number:
        return False

    match = re.match(r'^제(\d+)조', section_number)
    if match:
        article_num = int(match.group(1))
        return article_num >= 5

    return False


def is_after_revision_history(section_content: str, section_number: str) -> bool:
    """부록, 참고, 내규의 제·개정 이력 이후 섹션인지 확인하는 함수"""
    # (부록), (참고) 섹션 자체와 그 이후 모든 내용
    if section_content == "(부록)" or section_content == "(참고)" or "내규의 제·개정 이력" in section_content:
        return True

    # 개정 이력 관련 내용들
    revision_patterns = [
        "(내규의 제정 및 시행)",
        "(내규의 전면개정 및 시행)",
        "(내규의 개정)",
        "이 내규는.*시행한다"
    ]

    for pattern in revision_patterns:
        if pattern in section_content:
            return True

    # 제4조(부록), 제5조(참고) 및 제 N조 형식의 개정 이력 번호들 (제 1조, 제 2조, 제 3조)
    import re
    if section_number == "제4조" or section_number == "제5조":
        return True
    if re.match(r'^제 \d+조$', section_number):
        return True

    return False


def extract_images_for_app(docx_path: str, output_dir: str,
                          enable_table_conversion: bool = True,
                          article_range: Optional[Tuple[int, int]] = None,
                          use_enhanced_table_conversion: bool = False,
                          wzruleid: Optional[str] = None) -> Dict[str, Any]:
    """
    app.py에서 사용하기 위한 이미지 추출 함수입니다.

    Args:
        docx_path: Word 문서 경로
        output_dir: 이미지 저장 디렉토리
        enable_table_conversion: 표를 이미지로 변환할지 여부 (기본값: True)
        article_range: 추출할 조문 범위 (시작조, 끝조) 예: (1, 3), None이면 전체 범위
        use_enhanced_table_conversion: Enhanced HTML+Playwright 방식 사용 여부 (기본값: False)
        wzruleid: 규정 ID (이미지 파일명 접두사로 사용)

    Returns:
        앱에서 사용할 수 있는 형식의 이미지 정보
    """
    # 테이블 변환 활성화
    print(f"이미지 추출 모드: 테이블 변환={'활성화' if enable_table_conversion else '비활성화'}")
    extractor = DocxImageExtractor(output_dir,
                                  enable_table_conversion=enable_table_conversion,
                                  article_range=article_range,
                                  wzruleid=wzruleid)
    combined_images = extractor.extract_images_from_docx(docx_path)

    # 앱에서 사용할 형식으로 변환
    return format_image_info_for_app(combined_images)


def format_image_info_for_app(image_info_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    이미지 정보를 앱에서 사용하기 쉬운 형식으로 변환합니다.
    
    Args:
        image_info_list: 이미지 정보 리스트
        
    Returns:
        앱에서 사용하기 쉬운 형식의 이미지 정보
    """
    image_entries = []
    
    for idx, img_info in enumerate(image_info_list):
        # 텍스트 컨텍스트 추출 (앞뒤 텍스트)
        prev_text = img_info.get("previous_text", "").strip()
        next_text = img_info.get("next_text", "").strip()
        caption = img_info.get("caption", "").strip()
        
        # 이미지 캡션 및 주변 텍스트에서 제목/설명 추출 시도
        image_title = ""
        image_description = ""
        
        if caption:
            image_title = caption
        elif img_info.get("paragraph_text"):
            image_title = img_info["paragraph_text"]
        
        # 이미지의 컨텍스트 정보 구성
        context_info = []
        if prev_text:
            context_info.append(f"이전 텍스트: {prev_text}")
        if next_text:
            context_info.append(f"다음 텍스트: {next_text}")
        if img_info.get("context"):
            context_info.append(f"컨텍스트: {img_info['context']}")
        if img_info.get("table_location"):
            context_info.append(f"위치: {img_info['table_location']}")

        # 표 이미지인 경우 추가 정보
        if img_info.get("is_table"):
            table_data = img_info.get("table_data", [])
            if table_data:
                rows = len(table_data)
                cols = max(len(row) for row in table_data) if table_data else 0
                context_info.append(f"표 크기: {rows}행 {cols}열")
                # 첫 번째 행(헤더)의 내용 추가
                if table_data and table_data[0]:
                    header = " | ".join([cell[:20] + "..." if len(cell) > 20 else cell for cell in table_data[0][:3]])
                    context_info.append(f"표 헤더: {header}")

        image_description = "\n".join(context_info)
        
        # 최종 이미지 정보 항목
        entry = {
            "seq": idx + 1,
            "file_name": img_info["file_name"],
            "file_path": img_info["file_path"].replace("\\", "/"),  # 경로 정규화
            "title": image_title,
            "description": image_description,
            "previous_text": prev_text,
            "next_text": next_text,
            "content_type": img_info["content_type"],
            "is_table": img_info.get("is_table", False),  # 표 이미지 여부
            "table_data": img_info.get("table_data", [])  # 표 데이터 (표 이미지인 경우)
        }
        
        image_entries.append(entry)
    
    return {
        "image_count": len(image_entries),
        "images": image_entries
    }


def merge_json_with_images(json_data: Dict[str, Any], image_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    JSON 문서 데이터와 이미지 정보를 병합합니다.

    Args:
        json_data: 문서 구조 JSON 데이터
        image_info: 이미지 정보

    Returns:
        병합된 JSON 데이터
    """
    # 이미지 관련 정보가 없을 경우 원본 JSON 반환
    if not image_info or not image_info.get("images"):
        return json_data

    # 이미지 정보 복사
    result = json_data.copy()

    # 조문 내용과 이미지 연결
    if "조문내용" in result:
        # 모든 이미지를 적절한 조문에 유니크하게 할당
        assign_images_to_sections(result["조문내용"], image_info["images"])
    
    # 문서 정보에 이미지 개수 추가
    if "문서정보" in result:
        result["문서정보"]["이미지개수"] = image_info["image_count"]
    
    return result


def assign_images_to_sections(sections: List[Dict[str, Any]], images: List[Dict[str, Any]]) -> None:
    """
    모든 이미지를 적절한 조문에 할당합니다.
    각 이미지는 가장 적합한 하나의 조문에만 연결됩니다.
    별표(별지) 표 이미지는 해당 섹션에 연결됩니다.

    Args:
        sections: 조문 리스트
        images: 이미지 정보 리스트
    """
    if not images:
        return

    print(f"[이미지-섹션 연결] 총 {len(images)}개 이미지, {len(sections)}개 섹션")

    # 별표 섹션 인덱스 찾기 (별표가 언급된 섹션들)
    byulpyo_sections = {}  # {'별표 제1호': section_index, ...}
    for i, section in enumerate(sections):
        content = section.get("내용", "")
        # 별표 제N호 패턴 찾기
        matches = re.findall(r'『?별표\s*제?(\d+)호?』?', content)
        for match in matches:
            key = f"별표{match}"
            if key not in byulpyo_sections:
                byulpyo_sections[key] = i
                print(f"  별표 섹션 발견: {key} -> seq {section.get('seq')}")

    # 제4조 이후(제4조 포함) 섹션들을 찾아서 제외할 인덱스 범위 결정
    # 단, 별표가 포함된 섹션 및 별표 하위 섹션은 제외하지 않음
    excluded_section_indices = set()

    # 먼저 별표 섹션들의 인덱스를 수집하고, 별표 범위(별표 헤더~다음 별표 전) 계산
    byulpyo_range_indices = set()
    byulpyo_header_indices = []
    for i, section in enumerate(sections):
        content = re.sub(r'<[^>]+>', '', section.get("내용", ""))
        if re.match(r'^『별표', content.strip()):
            byulpyo_header_indices.append(i)

    # 각 별표 헤더로부터 다음 별표 전까지를 별표 범위로 마킹
    for idx, header_idx in enumerate(byulpyo_header_indices):
        next_header_idx = byulpyo_header_indices[idx + 1] if idx + 1 < len(byulpyo_header_indices) else len(sections)
        for j in range(header_idx, next_header_idx):
            byulpyo_range_indices.add(j)

    for i, section in enumerate(sections):
        section_number = section.get("번호", "").strip()
        section_content = section.get("내용", "").strip()

        # 별표 범위 내 섹션은 제외하지 않음
        if i in byulpyo_range_indices:
            continue

        # 제4조(부록) 또는 제5조(참고)가 나타나면 해당 섹션부터 끝까지 모든 섹션을 제외
        if section_number == "제4조" or section_number == "제5조":
            for j in range(i, len(sections)):
                if j not in byulpyo_range_indices:
                    excluded_section_indices.add(j)
            break

        # 또는 개정이력 관련 내용이 나타나면 그 섹션부터 끝까지 모든 섹션을 제외
        if is_after_revision_history(section_content, section_number):
            for j in range(i, len(sections)):
                if j not in byulpyo_range_indices:
                    excluded_section_indices.add(j)
            break

    # 각 이미지별로 최적의 조문 찾기
    last_byulpyo_header_idx = None  # 가장 최근에 매칭된 별표 헤더 인덱스 (연속 표 처리용)
    for img_idx, img in enumerate(images):
        previous_text = img.get("previous_text", "")
        is_table = img.get("is_table", False)

        # 관련 없는 이미지 필터링 (도장, 승인 관련 등)
        if should_exclude_image(img, previous_text):
            print(f"  이미지 {img_idx} 제외: 필터링됨")
            continue

        best_match_section = None

        # 표 이미지: previous_text 기반으로 해당 별표 섹션에 개별 할당
        # previous_text에 『별표 제N호』가 있으면 해당 N호 섹션 찾기
        if is_table:
            # 1순위: previous_text에서 별표 번호 추출하여 매칭
            byulpyo_match = re.search(r'『?별표\s*제?(\d+)호?』?', previous_text)
            if byulpyo_match:
                target_num = byulpyo_match.group(1)
                # 별표 제N호가 시작되는 섹션(헤더)을 역순으로 찾기
                byulpyo_header_idx = None
                for i in range(len(sections) - 1, -1, -1):
                    if i in excluded_section_indices:
                        continue
                    content = re.sub(r'<[^>]+>', '', sections[i].get("내용", ""))
                    if content.strip().startswith(f'『별표 제{target_num}호') or \
                       content.strip().startswith(f'『별표 {target_num}호') or \
                       content.strip().startswith(f'별표 제{target_num}호'):
                        byulpyo_header_idx = i
                        break

                if byulpyo_header_idx is not None:
                    # previous_text에서 서브섹션 키워드 추출하여 매칭
                    prev_lines = [l.strip() for l in previous_text.strip().split('\n') if l.strip()]
                    subsection_match = None

                    for line in reversed(prev_lines):
                        # 별표 헤더 라인은 건너뛰기
                        if re.match(r'^『?별표', line):
                            continue
                        # 번호가 있는 라인 또는 표 제목 텍스트에서 키워드 추출
                        line_keyword = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
                        if line_keyword and len(line_keyword) >= 2:
                            # 별표 헤더 이후 ~ 다음 별표 전까지 검색
                            for j in range(byulpyo_header_idx + 1, len(sections)):
                                if j in excluded_section_indices:
                                    continue
                                sec_content = re.sub(r'<[^>]+>', '', sections[j].get("내용", ""))
                                if re.match(r'^『별표', sec_content.strip()):
                                    break  # 다음 별표 시작이면 중단
                                if line_keyword in sec_content:
                                    subsection_match = sections[j]
                                    print(f"  표 이미지 {img_idx} -> 별표 제{target_num}호 서브섹션 (seq {sections[j].get('seq')}, keyword='{line_keyword[:20]}')")
                                    break
                            if subsection_match:
                                break

                    best_match_section = subsection_match or sections[byulpyo_header_idx]
                    last_byulpyo_header_idx = byulpyo_header_idx  # 연속 표 처리용
                    if not subsection_match:
                        print(f"  표 이미지 {img_idx} -> 별표 제{target_num}호 헤더 (seq {sections[byulpyo_header_idx].get('seq')})")

            # 2순위: previous_text에서 서브섹션 키워드를 추출하여 별표 범위 내 매칭
            if not best_match_section and previous_text:
                prev_lines = [l.strip() for l in previous_text.strip().split('\n') if l.strip()]

                # last_byulpyo_header_idx가 있으면 해당 별표 범위 내에서만 검색
                if last_byulpyo_header_idx is not None:
                    for line in reversed(prev_lines):
                        line_keyword = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
                        if not line_keyword or len(line_keyword) < 2 or re.match(r'^[\d\s,\.]+$', line_keyword):
                            continue
                        if line_keyword.startswith('(단위'):
                            continue
                        # 마지막 별표 헤더 이후 ~ 다음 별표 전까지만 검색
                        for j in range(last_byulpyo_header_idx + 1, len(sections)):
                            if j in excluded_section_indices:
                                continue
                            sec_content = re.sub(r'<[^>]+>', '', sections[j].get("내용", ""))
                            if re.match(r'^『별표', sec_content.strip()):
                                break  # 다음 별표 시작이면 중단
                            if line_keyword in sec_content:
                                best_match_section = sections[j]
                                print(f"  표 이미지 {img_idx} -> 별표 범위 내 서브섹션 (seq {sections[j].get('seq')}, keyword='{line_keyword[:30]}')")
                                break
                        if best_match_section:
                            break

                    # 서브섹션 매칭 안되면 마지막 별표 헤더에 할당
                    if not best_match_section:
                        best_match_section = sections[last_byulpyo_header_idx]
                        print(f"  표 이미지 {img_idx} -> 이전 별표 헤더 fallback (seq {sections[last_byulpyo_header_idx].get('seq')})")

                # last_byulpyo_header_idx가 없으면 기존 방식으로 fallback
                if not best_match_section:
                    for i in range(len(sections) - 1, -1, -1):
                        if i in excluded_section_indices:
                            continue
                        content = re.sub(r'<[^>]+>', '', sections[i].get("내용", ""))
                        if any(kw in content for kw in ["별표", "별지", "별첨"]):
                            for line in prev_lines:
                                if len(line) > 3 and line in content:
                                    best_match_section = sections[i]
                                    print(f"  표 이미지 {img_idx} -> 별표 내용 매칭 (seq {sections[i].get('seq')})")
                                    break
                            if best_match_section:
                                break

            # 3순위: 마지막 별표 섹션에 할당 (fallback)
            if not best_match_section:
                for i in range(len(sections) - 1, -1, -1):
                    if i in excluded_section_indices:
                        continue
                    content = sections[i].get("내용", "")
                    if any(kw in content for kw in ["별표", "별지", "별첨"]):
                        best_match_section = sections[i]
                        print(f"  표 이미지 {img_idx} -> fallback 문서 끝 (seq {sections[i].get('seq')})")
                        break

        if previous_text and not best_match_section:
            # 1순위: 이미지/표 참조 태그가 있는 섹션을 우선 검색
            image_ref_patterns = [
                r'<그림\s*\d+>',      # <그림1>, <그림 1> 등
                r'<표\s*\d+>',        # <표1>, <표 1> 등
                r'<첨부\s*\d+>',      # <첨부1>, <첨부 1> 등
                r'\[그림\s*\d*[^\]]*\]', # [그림1], [그림 1. 제목] 등
                r'\[표\s*\d*[^\]]*\]',   # [표1], [표 1. 제목] 등
                r'\[첨부\s*\d*[^\]]*\]'  # [첨부1], [첨부 1. 파일명] 등
            ]

            # 이미지 참조 태그가 있는 섹션 찾기 (제외 섹션 제외)
            # 단, 해당 이미지의 previous_text와 관련성이 있는지도 확인
            for i, section in enumerate(sections):
                if i in excluded_section_indices:
                    continue
                section_content = section.get("내용", "")
                for pattern in image_ref_patterns:
                    if re.search(pattern, section_content):
                        # 이미지 참조 태그가 있는 첫 번째 섹션을 우선 매칭
                        # 단, 각 이미지는 해당 섹션 근처에 위치해야 함
                        if is_image_related_to_section(previous_text, section, sections, i):
                            best_match_section = section
                            break
                if best_match_section:
                    break

            # 2순위: 직접적인 내용 매칭 시도 (이미지 태그가 없는 경우만)
            if not best_match_section:
                previous_lines = previous_text.strip().split('\n')
                last_line = previous_lines[-1].strip() if previous_lines else ""

                # 먼저 마지막 라인과 정확히 일치하는 섹션을 찾기
                for i, section in enumerate(sections):
                    if i in excluded_section_indices:
                        continue  # 제외된 섹션은 건너뛰기
                    section_content = section.get("내용", "").strip()
                    if section_content and section_content == last_line:
                        best_match_section = section
                        break

                # 마지막 라인 매칭이 안된 경우 부분 매칭 시도
                if not best_match_section:
                    # 마지막 라인에 섹션 내용이 포함된 경우
                    for i, section in enumerate(sections):
                        if i in excluded_section_indices:
                            continue  # 제외된 섹션은 건너뛰기
                        section_content = section.get("내용", "").strip()
                        if section_content and len(section_content) > 3 and section_content in last_line:
                            best_match_section = section
                            break

                    # 그래도 안되면 전체 previous_text에서 찾기 (역순으로)
                    if not best_match_section:
                        for i in range(len(sections) - 1, -1, -1):
                            if i in excluded_section_indices:
                                continue  # 제외된 섹션은 건너뛰기
                            section = sections[i]
                            section_content = section.get("내용", "").strip()
                            if section_content and len(section_content) > 3 and section_content in previous_text:
                                best_match_section = section
                                break

            # 직접 매칭이 안된 경우 키워드 매칭 시도
            if not best_match_section:
                if is_table:
                    # 테이블의 경우
                    end_keywords = ["내규", "시행", "개정", "승인", "전면개정"]
                    has_end_keywords = any(keyword in previous_text for keyword in end_keywords)

                    if has_end_keywords:
                        # 끝부분 조문 우선 매칭
                        end_sections = sections[-5:] if len(sections) >= 5 else sections
                        best_match_section = find_best_matching_section_unique(previous_text, end_sections)
                    else:
                        # 일반 매칭
                        best_match_section = find_best_matching_section_unique(previous_text, sections)
                else:
                    # 일반 이미지의 경우 - 더 정확한 키워드 매칭
                    best_match_section = find_best_matching_section_unique(previous_text, sections)

        if not best_match_section and sections:
            # 매칭이 안되면 마지막 조문에 할당 (단, 제5조(참고) 제외)
            potential_section = sections[-1]
            section_content = potential_section.get("내용", "").strip()
            section_number = potential_section.get("번호", "").strip()

            # 내규의 제·개정 이력 이후로는 이미지 할당 제외
            if is_after_revision_history(section_content, section_number):
                best_match_section = None
            else:
                best_match_section = potential_section

        if best_match_section:
            # 해당 섹션이 제외 대상인지 확인
            section_index = None
            for i, section in enumerate(sections):
                if section is best_match_section:
                    section_index = i
                    break

            # 제외 대상 섹션이면 이미지 할당하지 않음
            if section_index is not None and section_index in excluded_section_indices:
                continue  # 제4조 이후 또는 개정이력 이후는 스킵

            # 추가 안전성 확인 (기존 로직 유지)
            section_content = best_match_section.get("내용", "").strip()
            section_number = best_match_section.get("번호", "").strip()
            if is_after_revision_history(section_content, section_number):
                continue  # 내규의 제·개정 이력 이후는 스킵

            # 관련이미지가 없으면 초기화
            if "관련이미지" not in best_match_section:
                best_match_section["관련이미지"] = []

            # 이미지 정보 추가
            image_entry = {
                "seq": img["seq"],
                "file_name": img["file_name"],
                "file_path": img["file_path"],
                "title": img["title"]
            }

            # 표 이미지인 경우 추가 정보 포함
            if img.get("is_table"):
                image_entry["is_table"] = True
                image_entry["table_data"] = img.get("table_data", [])

            best_match_section["관련이미지"].append(image_entry)

    # 표 이미지에서 제목/단위를 제외했으므로 텍스트는 그대로 보존
    # (이전: _strip_duplicate_byulpyo_text(sections))


def _strip_duplicate_byulpyo_text(sections: List[Dict[str, Any]]) -> None:
    """
    표 이미지가 연결된 별표 섹션에서 이미지와 중복되는 제목/단위 텍스트를 제거합니다.
    이미지에 이미 포함된 center-aligned 제목과 right-aligned 단위를 텍스트에서 삭제합니다.
    """
    for section in sections:
        content = section.get("내용", "")
        images = section.get("관련이미지", [])

        # 별표 섹션이고 표 이미지가 있는 경우만 처리
        if not images or "별표" not in content:
            continue

        has_table_image = any(img.get("is_table") for img in images)
        if not has_table_image:
            continue

        # 이미지와 중복되는 center/right 정렬 텍스트 제거
        # <div style="text-align:center">...</div> → 제목 (이미지에 포함)
        # <div style="text-align:right">...</div> → 단위 (이미지에 포함)
        content = re.sub(r'<div style="text-align:center">[^<]*(?:<[^>]+>[^<]*)*</div>', '', content)
        content = re.sub(r'<div style="text-align:right">[^<]*(?:<[^>]+>[^<]*)*</div>', '', content)

        section["내용"] = content.strip()


def should_exclude_image(img: Dict[str, Any], previous_text: str) -> bool:
    """
    관련 없는 이미지(도장, 승인 관련 등)를 필터링

    Args:
        img: 이미지 정보
        previous_text: 이미지의 previous_text

    Returns:
        제외해야 하면 True, 포함해야 하면 False
    """
    # 표 이미지는 더 관대하게 처리 (previous_text가 없어도 포함 가능)
    is_table = img.get("is_table", False)

    # 표 이미지인 경우 table_data로 직접 판단
    if is_table:
        table_data = img.get("table_data", [])
        if table_data:
            # 표의 모든 셀 텍스트 합치기
            all_cells = " ".join(" ".join(str(cell) for cell in row) for row in table_data)

            # 메타데이터/승인란 표 패턴 확인
            metadata_patterns = ["제정일", "최종개정일", "승인", "병원장", "(인)", "날인"]
            is_metadata_table = any(pattern in all_cells for pattern in metadata_patterns)

            if is_metadata_table:
                return True  # 메타데이터 표는 제외

            # 실제 내용이 있는 표는 포함
            if len(table_data) >= 2 and len(all_cells.strip()) > 20:
                return False  # 본문 표는 포함

    if not previous_text:
        return True  # previous_text가 없고 표도 아니면 제외

    # 1. 조문과 관련된 핵심 키워드가 있으면 우선 포함 고려
    include_keywords = [
        "감염관리실", "조직", "체계", "운영", "관리",
        "위원회", "부서", "업무", "절차", "구성",
        "검사", "검체", "보고", "결과", "TAT", "항목", "기준",
        "여비", "교통비", "숙박비", "일비", "체재비", "별표"
    ]

    has_relevant_content = any(keyword in previous_text for keyword in include_keywords)

    # 2. 도장/승인 관련 키워드 확인
    exclude_keywords = [
        "승인", "날인", "도장", "인장", "서명", "결재",
        "책임", "확인", "검토", "승인자", "결재자"
    ]

    has_admin_content = any(keyword in previous_text for keyword in exclude_keywords)

    # 표 이미지의 경우 승인란 판별을 더 엄격하게 (실제 데이터 확인)
    if is_table:
        table_data = img.get("table_data", [])
        if table_data:
            # 표의 모든 셀 텍스트 합치기
            all_cells = " ".join(" ".join(row) for row in table_data)

            # 승인란 특징: "승인", "병원장", "(인)" 등이 함께 있음
            is_approval_table = (
                "승" in all_cells and
                ("병원장" in all_cells or "(인)" in all_cells)
            )

            if is_approval_table:
                return True  # 승인란 표는 제외

            # 실제 데이터가 있는 표는 포함
            if len(table_data) >= 2:  # 헤더 + 데이터 1행 이상
                # 조문 관련 키워드가 있거나, 의미있는 내용이 있으면 포함
                if has_relevant_content or len(all_cells.strip()) > 20:
                    return False  # 표 데이터 포함

    # 일반 이미지의 경우 기존 로직 적용
    # 승인 관련 키워드가 있고 조문 관련 키워드가 없으면 제외
    if has_admin_content and not has_relevant_content and not is_table:
        return True

    # 3. 날짜 패턴이 많이 포함된 경우 (승인란으로 판단)
    date_patterns = [
        r'\d{4}[년.-]\s*\d{1,2}[월.-]\s*\d{1,2}일?',  # 2025년 3월 25일
        r'\d{4}[.-]\d{1,2}[.-]\d{1,2}',               # 2025.03.25
        r'\d{1,2}[월/]\s*\d{1,2}일?'                  # 3월 25일
    ]

    date_matches = 0
    for pattern in date_patterns:
        date_matches += len(re.findall(pattern, previous_text))

    # 표가 아니고 날짜가 많으면 제외
    if date_matches >= 3 and not has_relevant_content and not is_table:
        return True

    # 4. previous_text가 너무 짧으면 제외 (단, 표는 예외)
    if len(previous_text.strip()) < 10 and not is_table:
        return True

    # 5. 문서 구조와 관련 없는 단순 텍스트 패턴 제외
    simple_patterns = [
        r'^[\s\d\.\-/]+$',  # 숫자, 점, 대시, 슬래시만 있는 경우
        r'^[^가-힣]*$'      # 한글이 전혀 없는 경우
    ]

    for pattern in simple_patterns:
        if re.match(pattern, previous_text.strip()):
            return True

    return False


def is_image_related_to_section(previous_text: str, section: Dict[str, Any], sections: List[Dict[str, Any]], section_index: int) -> bool:
    """
    이미지의 previous_text가 해당 섹션과 실제로 관련이 있는지 확인

    Args:
        previous_text: 이미지의 previous_text
        section: 확인할 섹션
        sections: 전체 섹션 리스트
        section_index: 해당 섹션의 인덱스

    Returns:
        관련성이 있으면 True, 없으면 False
    """
    if not previous_text or not section:
        return False

    section_content = section.get("내용", "").strip()

    # 1. 섹션 내용이 previous_text에 직접 포함되어 있는지 확인
    if section_content and len(section_content) > 5 and section_content in previous_text:
        return True

    # 2. 인접한 섹션들(앞뒤 1개씩만)의 내용이 previous_text에 포함되어 있는지 확인
    start_idx = max(0, section_index - 1)
    end_idx = min(len(sections), section_index + 2)

    related_sections = sections[start_idx:end_idx]

    # 인접 섹션 내용이 previous_text에 포함되어 있는지 직접 확인
    for related_section in related_sections:
        related_content = related_section.get("내용", "").strip()
        if related_content and len(related_content) > 5 and related_content in previous_text:
            return True

    # 3. 이미지 참조가 있는 섹션의 경우, 더 엄격한 키워드 매칭
    section_keywords = re.findall(r'[가-힣]{3,}', section_content)
    previous_keywords = re.findall(r'[가-힣]{3,}', previous_text)

    # 공통 키워드가 3개 이상이면 관련성 있음
    common_keywords = set(section_keywords) & set(previous_keywords)
    if len(common_keywords) >= 3:
        return True

    # 4. 특별한 키워드가 있는 경우 (조직도, 체계도 등)
    special_keywords = ["조직", "체계", "구조", "관리", "운영"]
    if any(keyword in previous_text and keyword in section_content for keyword in special_keywords):
        return True

    return False


def find_best_matching_section_unique(text: str, sections: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    주어진 텍스트와 가장 잘 매칭되는 조문을 하나만 찾습니다.
    이미지 중복 할당을 방지하기 위한 함수입니다.

    Args:
        text: 매칭할 텍스트
        sections: 조문 리스트

    Returns:
        가장 적합한 조문 (없으면 None)
    """
    if not sections:
        return None

    # 1단계: 이미지/표 참조 태그가 있는 섹션을 우선 검색
    image_ref_patterns = [
        r'<그림\s*\d+>',      # <그림1>, <그림 1> 등
        r'<표\s*\d+>',        # <표1>, <표 1> 등
        r'<첨부\s*\d+>',      # <첨부1>, <첨부 1> 등
        r'\[그림\s*\d*[^\]]*\]', # [그림1], [그림 1. 제목] 등
        r'\[표\s*\d*[^\]]*\]',   # [표1], [표 1. 제목] 등
        r'\[첨부\s*\d*[^\]]*\]'  # [첨부1], [첨부 1. 파일명] 등
    ]

    for section in sections:
        section_content = section.get("내용", "")
        # 이미지/표 참조 태그가 있는 섹션이면 우선 반환
        for pattern in image_ref_patterns:
            if re.search(pattern, section_content):
                return section

    # 2단계: 기존 키워드 매칭 로직 수행
    keywords = re.findall(r'[가-힣]{2,}', text)

    if not keywords:
        return None

    best_section = None
    max_matches = 0

    # 각 조문과 키워드 매칭 점수 계산
    for section in sections:
        section_text = section.get("내용", "")
        matches = sum(1 for keyword in keywords if keyword in section_text)

        if matches > max_matches:
            max_matches = matches
            best_section = section

    # 최소 매칭 조건을 만족하는 경우에만 반환
    if max_matches >= 2:  # 최소 2개 이상의 키워드가 매칭되어야 함
        return best_section

    return None


def find_best_matching_section(text: str, sections: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    주어진 텍스트와 가장 잘 매칭되는 조문을 찾습니다.

    Args:
        text: 매칭할 텍스트
        sections: 조문 리스트

    Returns:
        가장 적합한 조문 (없으면 마지막 조문)
    """
    if not sections:
        return None

    # 텍스트의 키워드들 추출 (한글 단어 위주)
    keywords = re.findall(r'[가-힣]{2,}', text)

    if not keywords:
        # 키워드가 없으면 마지막 조문 반환
        return sections[-1]

    best_section = None
    max_matches = 0
    best_candidates = []

    # 각 조문과 키워드 매칭 점수 계산
    for i, section in enumerate(sections):
        section_text = section.get("내용", "")
        matches = sum(1 for keyword in keywords if keyword in section_text)

        if matches > max_matches:
            max_matches = matches
            best_section = section
            best_candidates = [(section, i)]
        elif matches == max_matches and matches > 0:
            best_candidates.append((section, i))

    # 매칭 점수가 같은 후보들이 있으면 가장 뒤쪽(끝에 가까운) 조문 선택
    if best_candidates:
        best_candidates.sort(key=lambda x: x[1], reverse=True)  # 인덱스 기준 내림차순
        return best_candidates[0][0]

    # 매칭이 전혀 없으면 마지막 조문 반환
    return sections[-1]


def find_relevant_images(section_text: str, images: List[Dict[str, Any]], exclude_tables: bool = False) -> List[Dict[str, Any]]:
    """
    섹션 텍스트와 관련된 이미지를 찾습니다.

    Args:
        section_text: 섹션 텍스트
        images: 이미지 정보 리스트
        exclude_tables: 테이블 이미지를 제외할지 여부

    Returns:
        관련 이미지 리스트
    """
    relevant_images = []

    for image in images:
        # 테이블 제외 옵션이 켜져 있고 현재 이미지가 테이블이면 건너뜀
        if exclude_tables and image.get("is_table"):
            continue
        # 1. 이미지의 이전/다음 텍스트에 섹션 텍스트가 포함되어 있는지 확인
        if (section_text in image.get("previous_text", "") or 
            section_text in image.get("next_text", "")):
            relevant_images.append({
                "seq": image["seq"],
                "file_name": image["file_name"],
                "file_path": image["file_path"],
                "title": image["title"]
            })
            continue
        
        # 2. 섹션 텍스트에 이미지 제목이나 캡션이 포함되어 있는지 확인
        if image["title"] and image["title"] in section_text:
            relevant_images.append({
                "seq": image["seq"],
                "file_name": image["file_name"],
                "file_path": image["file_path"],
                "title": image["title"]
            })
            continue

        # 3. 표 이미지의 경우 표 데이터와 섹션 텍스트 매칭
        if image.get("is_table") and image.get("table_data"):
            table_data = image["table_data"]
            # 표의 모든 셀 텍스트를 하나의 문자열로 합침
            table_text = " ".join(" ".join(row) for row in table_data)

            # 섹션 텍스트와 표 텍스트의 유사성 확인 (간단한 키워드 매칭)
            section_words = set(section_text.lower().split())
            table_words = set(table_text.lower().split())

            # 공통 단어가 3개 이상이거나, 섹션이 짧고 50% 이상 일치하는 경우
            common_words = section_words.intersection(table_words)
            if (len(common_words) >= 3 or
                (len(section_words) <= 10 and len(common_words) / len(section_words) >= 0.5)):
                relevant_images.append({
                    "seq": image["seq"],
                    "file_name": image["file_name"],
                    "file_path": image["file_path"],
                    "title": image["title"]
                })
                continue
    
    return relevant_images


def get_table_summary(table_data: List[List[str]]) -> str:
    """
    표 데이터의 요약 정보를 생성합니다.

    Args:
        table_data: 2차원 배열 형태의 표 데이터

    Returns:
        표 요약 정보
    """
    if not table_data:
        return "빈 표"

    rows = len(table_data)
    cols = max(len(row) for row in table_data) if table_data else 0

    summary = f"{rows}행 {cols}열 표"

    # 헤더가 있는 경우 헤더 정보 추가
    if table_data and table_data[0]:
        headers = [cell[:15] + "..." if len(cell) > 15 else cell for cell in table_data[0][:3]]
        if any(headers):
            summary += f" (헤더: {' | '.join(filter(None, headers))})"

    return summary


# 앱에서 사용할 수 있도록 이미지 정보를 JSON 파일로 저장하는 함수
def save_image_info_json(image_info: Dict[str, Any], output_file: str) -> None:
    """
    이미지 정보를 JSON 파일로 저장합니다.
    
    Args:
        image_info: 이미지 정보
        output_file: 출력 파일 경로
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(image_info, f, ensure_ascii=False, indent=2)

