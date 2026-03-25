"""
자동번호매기기 기능을 제공하는 유틸리티 모듈
"""
import re
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from collections import Counter
from typing import Dict, Any, List, Tuple, Optional
from .docx_parser import extract_formatted_text_from_paragraph, extract_rich_text_from_paragraph


# 번호 접두어 제거용 패턴 (convert_to_sections_format과 extract_numbers_from_docx에서 공유)
NUMBER_PREFIX_PATTERNS = [
    r'^\d+\)\s*',  # 1), 2), 3) 등
    r'^\(\d+\)\s*',  # (1), (2), (3) 등
    r'^[가-힣]\)\s*',  # 가), 나), 다) 등
    r'^\([가-힣]\)\s*',  # (가), (나), (다) 등
    r'^[ⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ]+\)\s*',  # ⅰ), ⅱ), ⅲ) 등
    r'^\([ⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ]+\)\s*',  # (ⅰ), (ⅱ), (ⅲ) 등
    r'^\?\)\s*',  # ?) 패턴
    r'^\(\?\)\s*',  # (?) 패턴
    r'^[a-z]\.\s*',  # a., b., c. 등 (레벨 3, 6용)
    r'^[a-z]\)\s*',  # a), b), c) 등 (레벨 7용)
    r'^\([a-z]\)\s*',  # (a), (b), (c) 등 (레벨 8용)
    r'^[A-Z]\.\s*',  # A., B., C. 등 (대문자)
    r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟]\s*',  # ① ② ③ 등
    r'^[ⓐ-ⓩ]\s*',  # ⓐ ⓑ ⓒ 등 (원형 알파벳)
    r'^[㉮-㉻]\s*',  # ㉮ ㉯ ㉰ 등 (원형 한글)
    r'^[㉠-㉥]\s*',  # ㉠ ㉡ ㉢ 등 (원형 한글 자음)
    r'^제\s*\d+\s*장\s*',  # 제1장, 제 1 장 등
    r'^제\s*\d+\s*조\s*',  # 제1조, 제 1 조 등
    r'^\d+\.\s*',  # 1., 2., 3. 등 (숫자 점)
]


def extract_numbers_from_docx(file_path: str) -> List[Dict[str, Any]]:
    """
    Word 문서에서 자동번호매기기 형식을 추출합니다.
    
    Args:
        file_path: Word 문서 파일 경로
        
    Returns:
        추출된 번호 정보 리스트
    """
    doc = docx.Document(file_path)
    results = []

    # ── 테이블 직후 문단 감지 ──
    # document.paragraphs는 <w:tbl>을 건너뛰므로 body를 직접 스캔
    from docx.oxml.ns import qn as _qn
    _after_table_indices = set()
    _prev_was_table = False
    _para_idx = 0
    for _elem in doc.element.body:
        _tag = _elem.tag.split('}')[-1] if '}' in _elem.tag else _elem.tag
        if _tag == 'p':
            if _prev_was_table:
                # 빈 문단은 건너뛰고 첫 번째 비어있지 않은 문단만 마킹
                _text = ''
                for _t in _elem.iter(_qn('w:t')):
                    if _t.text:
                        _text += _t.text
                if _text.strip():
                    _after_table_indices.add(_para_idx)
                    _prev_was_table = False
                # 빈 문단이면 _prev_was_table 유지 (bridge over)
            _para_idx += 1
        elif _tag == 'tbl':
            _prev_was_table = True
    
    # 레벨별 번호 추적 - 최대 8레벨까지 지원하도록 확장
    level_counters = {
        0: 0,  # 레벨 0 ("제N장")
        1: 0,  # 레벨 1 ("제N조" 또는 "N.")
        2: 0,  # 레벨 2 ("N-N.")
        3: 0,  # 레벨 3 ("N)")
        4: 0,  # 레벨 4 ("(N)")
        5: 0,  # 레벨 5 ("①, ②" 또는 "가, 나")
        6: 0,  # 레벨 6 ("a.")
        7: 0,  # 레벨 7 ("a)")
        8: 0   # 레벨 8 ("(a)")
    }

        # 상위 레벨 변경 추적
    parent_level_changes = {
        0: 0,  # 레벨 0 변경 카운터 (장)
        1: 0,  # 레벨 1 변경 카운터
        2: 0,  # 레벨 2 변경 카운터
        3: 0,  # 레벨 3 변경 카운터
        4: 0,  # 레벨 4 변경 카운터
        5: 0,  # 레벨 5 변경 카운터
        6: 0,  # 레벨 6 변경 카운터
        7: 0,  # 레벨 7 변경 카운터
        8: 0   # 레벨 8 변경 카운터
    }
    
    current_level = 0
    found_content_start = False
    parsing_revision_history = False

    # ── 테이블 1x1 셀의 장/절 제목을 paragraph 목록에 삽입 ──
    # body 요소를 순서대로 순회하여 table → paragraph 순서 유지
    from docx.oxml.ns import qn as _qn2
    from docx.table import Table as _Table
    from docx.text.paragraph import Paragraph as _Paragraph

    _ordered_elements = []  # (type, element) 리스트
    for _elem in doc.element.body:
        _tag = _elem.tag.split('}')[-1] if '}' in _elem.tag else _elem.tag
        if _tag == 'p':
            _ordered_elements.append(('para', _Paragraph(_elem, doc)))
        elif _tag == 'tbl':
            _tbl = _Table(_elem, doc)
            # 1x1 테이블이고 장/절/서문 제목인 경우만 추출
            if len(_tbl.rows) == 1 and len(_tbl.columns) == 1:
                _cell_text = _tbl.cell(0, 0).text.strip()
                if _cell_text and (re.match(r'^제\s*\d+\s*(장|절)', _cell_text) or
                                   re.match(r'^(서\s*문|전\s*문|총\s*칙|부\s*칙)', _cell_text) or
                                   len(_cell_text) < 30):
                    _ordered_elements.append(('table_title', _cell_text))

    # paragraph 인덱스 매핑 (기존 _after_table_indices와 호환)
    _para_counter = 0
    _all_paragraphs = []  # (index_for_compat, paragraph_or_text, is_table_title)
    for etype, elem in _ordered_elements:
        if etype == 'para':
            _all_paragraphs.append((_para_counter, elem, False))
            _para_counter += 1
        elif etype == 'table_title':
            _all_paragraphs.append((-1, elem, True))

    for i, (orig_idx, para_or_text, is_table_title) in enumerate(_all_paragraphs):
        if is_table_title:
            # 테이블 제목 → 가상 paragraph로 처리
            text = para_or_text.strip()
            raw_indent = 0
            original_text = text
            paragraph = None  # alignment 등 없음
        else:
            paragraph = para_or_text
            # 윗첨자/아랫첨자를 포함한 텍스트 추출
            raw_text = extract_formatted_text_from_paragraph(paragraph)
            raw_indent = len(raw_text) - len(raw_text.lstrip())
            text = raw_text.strip()
            if not text:
                continue
            original_text = text
        
        # 문서 시작 지점 감지 - KB신용정보 사규는 제1장 또는 제1조로 시작
        if not found_content_start:
            # 제1장 또는 제1조 패턴 확인 (공백 허용: "제 1 장", "제 1 조")
            if re.match(r'^제\s*1\s*장|^제\s*1\s*조', text):
                found_content_start = True
            # 비정형 문서: 제X장/제X조 없이 "총칙", "1. xxx" 등으로 시작하는 경우
            elif re.match(r'^(총\s*칙|서\s*문|전\s*문)', text):
                found_content_start = True
            elif i > 5 and re.match(r'^\d+\.\s+\S', text):
                # 6번째 paragraph 이후에 "1. xxx" 패턴이 나오면 시작으로 간주
                found_content_start = True
            # 시행일, 제정일 등의 메타데이터를 건너뜀
            if not found_content_start:
                continue
        
        # 내규의 제·개정 이력 섹션 처리
        if "내규의 제·개정 이력" in text:
            parsing_revision_history = True

        # 번호 형식 추출
        if paragraph is not None:
            number_info = extract_numbering(paragraph, text)
        else:
            # 테이블 제목: 텍스트 기반으로 장/절 감지
            number_info = None
            m = re.match(r'^제\s*(\d+)\s*(장|절)', text)
            if m:
                number_info = {"level": 0, "number": f"제{m.group(1)}{m.group(2)}", "type": "chapter"}
            elif re.match(r'^(서\s*문|전\s*문)', text):
                number_info = {"level": 0, "number": "", "type": "chapter"}

        # 번호 형식이 추출된 경우 레벨별 카운터 관리
        if number_info:
            level = number_info["level"]

            # 컨텍스트 기반 레벨 조정: "N." 형식의 경우
            if number_info.get("type") == "section_number" and level == 1:
                # 현재 활성화된 상위 레벨이 있으면 하위 레벨로 조정
                if current_level >= 1 and level_counters[1] > 0:
                    # "제N조" 조문이 활성화되어 있으면 "N."을 레벨 2로 조정
                    level = 2
                    number_info["level"] = 2

            # 현재 레벨이 이전 레벨보다 높으면 하위 레벨 카운터 초기화
            if level < current_level:
                for l in range(level+1, 9):  # 8레벨까지 지원
                    level_counters[l] = 0

            # 레벨 0이 변경되면 (제N장) 하위 레벨 모두 초기화
            if level == 0:
                match = re.match(r'^제(\d+)장', text)
                if match:
                    level_counters[0] = int(match.group(1))
                else:
                    level_counters[0] += 1

                # 하위 레벨 모두 초기화
                for l in range(1, 9):
                    level_counters[l] = 0
                parent_level_changes[0] += 1

            # 레벨 1이 변경되면 상위 레벨 변경 카운터 증가 및 하위 레벨 초기화
            elif level == 1:
                # "제N조" 형식에서 N 추출
                match = re.match(r'^제(\d+)조', text)
                if match:
                    level_counters[1] = int(match.group(1))
                else:
                    # "N." 형식에서 N 추출
                    match = re.match(r'^(\d+)\.', text)
                    if match:
                        level_counters[1] = int(match.group(1))
                    else:
                        level_counters[1] += 1
                
                for l in range(2, 6):  # 하위 레벨 초기화
                    level_counters[l] = 0
                parent_level_changes[1] += 1
            
            # 레벨 2가 변경되면 상위 레벨 변경 카운터 증가 및 하위 레벨 초기화
            elif level == 2:
                # "N-N." 형식에서 두 번째 N 추출 또는 "1)" 형식
                match = re.match(r'^\d+-(\d+)\.', text)
                if match:
                    level_counters[2] = int(match.group(1))
                else:
                    # "N." 형식에서 N 추출 (컨텍스트 조정된 경우)
                    match = re.match(r'^(\d+)\.', text)
                    if match:
                        level_counters[2] = int(match.group(1))
                    else:
                        # 원형 숫자 형식 (①, ②, ③ 등) - KB신용정보 사규에서 항으로 사용
                        match = re.match(r'^\s*([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟])', text)
                        if match:
                            circle_numbers = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟"
                            level_counters[2] = circle_numbers.index(match.group(1)) + 1
                        else:
                            # "N)" 형식은 스킵
                            # match = re.match(r'^\s*(\d+)\)', text)
                            # if match:
                            #     level_counters[2] = int(match.group(1))
                            # else:
                            level_counters[2] += 1

                for l in range(3, 6):  # 하위 레벨 초기화
                    level_counters[l] = 0
                parent_level_changes[2] += 1
            
            # 레벨 3이 변경되면 하위 레벨 초기화
            elif level == 3:
                # 다양한 번호 형식 처리 (1), (가), ①, a. 등
                match = re.match(r'^\s*\((\d+)\)', text)  # (1) 형식
                if match:
                    level_counters[3] = int(match.group(1))
                else:
                    # match = re.match(r'^\s*(\d+)\)', text)  # 1) 형식 스킵
                    # if match:
                    #     level_counters[3] = int(match.group(1))
                    # else:
                        match = re.match(r'^([a-z])\.\s*', text)  # a. 형식
                        if match:
                            level_counters[3] = ord(match.group(1)) - ord('a') + 1
                        else:
                            match = re.match(r'^\s*([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟])', text)  # ① 형식 (확장)
                            if match:
                                circle_numbers = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟"
                                level_counters[3] = circle_numbers.index(match.group(1)) + 1
                            else:
                                level_counters[3] += 1
                                
                for l in range(4, 6):  # 하위 레벨 초기화
                    level_counters[l] = 0
                parent_level_changes[3] += 1
                
            # 레벨 4 처리
            elif level == 4:
                # (가), ㉮, ㉠, A. 등의 형식 처리
                match = re.match(r'^\s*\(([가-힣])\)', text)  # (가) 형식
                if match:
                    korean_chars = "가나다라마바사아자차카타파하"
                    level_counters[4] = korean_chars.find(match.group(1)) + 1
                else:
                    match = re.match(r'^\s*([㉮-㉻])', text)  # ㉮ 형식
                    if match:
                        circle_korean_chars = "㉮㉯㉰㉱㉲㉳㉴㉵㉶㉷㉸㉹㉺㉻"
                        level_counters[4] = circle_korean_chars.find(match.group(1)) + 1
                    else:
                        match = re.match(r'^\s*([㉠-㉥])', text)  # ㉠ 형식
                        if match:
                            circle_korean_consonants = "㉠㉡㉢㉣㉤㉥"
                            level_counters[4] = circle_korean_consonants.find(match.group(1)) + 1
                        else:
                            match = re.match(r'^\s*([A-Za-z])\.\s*', text)  # A. 형식
                            if match:
                                if match.group(1).isupper():  # 대문자
                                    level_counters[4] = ord(match.group(1)) - ord('A') + 1
                                else:  # 소문자
                                    level_counters[4] = ord(match.group(1)) - ord('a') + 1
                            else:
                                level_counters[4] += 1
                                
                level_counters[5] = 0  # 하위 레벨 초기화
                parent_level_changes[4] += 1
                
            # 레벨 5 처리
            elif level == 5:
                # ⓐ, ⒜, i), 또는 기타 형식
                match = re.match(r'^\s*([ⓐ-ⓩ])', text)  # ⓐ 형식
                if match:
                    circle_alpha = "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ"
                    level_counters[5] = circle_alpha.find(match.group(1)) + 1
                else:
                    match = re.match(r'^\s*([ⅰ-ⅹ])\)', text)  # ⅰ) 형식 (로마자)
                    if match:
                        roman_numerals = "ⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ"
                        level_counters[5] = roman_numerals.find(match.group(1)) + 1
                    else:
                        level_counters[5] += 1

                # 하위 레벨 초기화
                for l in range(6, 9):
                    level_counters[l] = 0
                parent_level_changes[5] += 1

            # 레벨 6 처리
            elif level == 6:
                # a. 형식 재사용 (소문자 알파벳)
                match = re.match(r'^([a-z])\.\s*', text)
                if match:
                    level_counters[6] = ord(match.group(1)) - ord('a') + 1
                else:
                    level_counters[6] += 1
                # 하위 레벨 초기화
                for l in range(7, 9):
                    level_counters[l] = 0
                parent_level_changes[6] += 1

            # 레벨 7 처리
            elif level == 7:
                # a) 형식 (소문자 알파벳)
                match = re.match(r'^([a-z])\)\s*', text)
                if match:
                    level_counters[7] = ord(match.group(1)) - ord('a') + 1
                else:
                    level_counters[7] += 1
                # 하위 레벨 초기화
                level_counters[8] = 0
                parent_level_changes[7] += 1

            # 레벨 8 처리
            elif level == 8:
                # (a) 형식 (소문자 알파벳)
                match = re.match(r'^\(([a-z])\)\s*', text)
                if match:
                    level_counters[8] = ord(match.group(1)) - ord('a') + 1
                else:
                    level_counters[8] += 1
                parent_level_changes[8] += 1
            
            # 번호 형식에 따라 번호 생성
            # 개정 이력 섹션의 특수 패턴들은 직접 번호 사용
            if number_info["type"] in ["reference_section", "revision_history_title", "revision_enactment", "revision_full_amendment", "revision_amendment", "revision_detail"]:
                generated_number = number_info["number"]
            else:
                generated_number = generate_number_by_level(level, level_counters, number_info["type"])
            
            # 원래 텍스트에 번호가 있는지 확인 (원형 숫자 범위 확장, 제N장 추가)
            has_numbering = bool(re.match(r'^제\s*\d+\s*장|^제\s*\d+\s*조|^\d+\.|^\d+-\d+\.|^\s*\d+\)|^[a-z]\.|^\s*\([^)]+\)|^\s*[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟]|^\s*[㉮-㉻]|^\s*[㉠-㉥]|^\s*[ⓐ-ⓩ]|^\s*[ⅰ-ⅹ]\)', text))
            
            # 번호를 포함한 전체 텍스트 생성
            if has_numbering:
                full_text = text  # 이미 번호가 있는 경우
            else:
                full_text = f"{generated_number} {text}"  # 번호 추가

            # rich_content 계산 (bold 서식 보존)
            if paragraph is not None:
                plain_from_runs = ''.join(run.text for run in paragraph.runs if run.text)
                _leading_ws = len(plain_from_runs) - len(plain_from_runs.lstrip())
                _prefix_len = 0
                if has_numbering:
                    _stripped = plain_from_runs.strip()
                    for _p in NUMBER_PREFIX_PATTERNS:
                        _m = re.match(_p, _stripped)
                        if _m:
                            _prefix_len = len(_m.group(0))
                            break
                rich_content = extract_rich_text_from_paragraph(
                    paragraph, skip_prefix_len=_leading_ws + _prefix_len)

                # 정렬 정보 추출
                try:
                    _align_val = paragraph.paragraph_format.alignment
                except ValueError:
                    _align_val = None
                _alignment = None
                if _align_val == WD_ALIGN_PARAGRAPH.CENTER:
                    _alignment = 'center'
                elif _align_val == WD_ALIGN_PARAGRAPH.RIGHT:
                    _alignment = 'right'

                # 폰트 크기/패밀리 추출
                _size_counter = Counter()
                for _run in paragraph.runs:
                    if _run.font.size and _run.text.strip():
                        _size_counter[_run.font.size / 12700] += len(_run.text.strip())
                _font_size_pt = _size_counter.most_common(1)[0][0] if _size_counter else None

                _font_counter = Counter()
                for _run in paragraph.runs:
                    if _run.font.name and _run.text.strip():
                        _font_counter[_run.font.name] += len(_run.text.strip())
                _font_family = _font_counter.most_common(1)[0][0] if _font_counter else None
            else:
                # 테이블 제목: 서식 정보 없음
                rich_content = f"<b>{text}</b>"
                _alignment = 'center'
                _font_size_pt = None
                _font_family = None

            # 결과 저장
            results.append({
                "paragraph_index": i,
                "original_text": original_text,
                "extracted_number": generated_number,
                "level": level,
                "numbering_type": number_info["type"],
                "level_counter": level_counters.copy(),
                "parent_changes": parent_level_changes.copy(),
                "full_text": full_text,
                "raw_indent": raw_indent,
                "rich_content": rich_content,
                "alignment": _alignment,
                "font_size_pt": _font_size_pt,
                "font_family": _font_family,
                "after_table": is_table_title or (orig_idx in _after_table_indices),
            })

            current_level = level
        else:
            # 번호가 없는 일반 텍스트의 경우
            # 들여쓰기에 따라 레벨 추정
            indent_level = 0
            for char in text:
                if char in [' ', '\t']:
                    indent_level += 1
                else:
                    break
                    
            level = 1  # 기본 레벨
            if indent_level >= 12:
                level = 5
            elif indent_level >= 10:
                level = 4
            elif indent_level >= 8:
                level = 3
            elif indent_level >= 4:
                level = 2
                
            # rich_content 계산
            if paragraph is not None:
                plain_from_runs = ''.join(run.text for run in paragraph.runs if run.text)
                _leading_ws = len(plain_from_runs) - len(plain_from_runs.lstrip())
                rich_content = extract_rich_text_from_paragraph(
                    paragraph, skip_prefix_len=_leading_ws)

                try:
                    _align_val = paragraph.paragraph_format.alignment
                except ValueError:
                    _align_val = None
                _alignment = None
                if _align_val == WD_ALIGN_PARAGRAPH.CENTER:
                    _alignment = 'center'
                elif _align_val == WD_ALIGN_PARAGRAPH.RIGHT:
                    _alignment = 'right'

                _size_counter = Counter()
                for _run in paragraph.runs:
                    if _run.font.size and _run.text.strip():
                        _size_counter[_run.font.size / 12700] += len(_run.text.strip())
                _font_size_pt = _size_counter.most_common(1)[0][0] if _size_counter else None

                _font_counter = Counter()
                for _run in paragraph.runs:
                    if _run.font.name and _run.text.strip():
                        _font_counter[_run.font.name] += len(_run.text.strip())
                _font_family = _font_counter.most_common(1)[0][0] if _font_counter else None
            else:
                rich_content = f"<b>{text}</b>"
                _alignment = 'center'
                _font_size_pt = None
                _font_family = None

            results.append({
                "paragraph_index": i,
                "original_text": original_text,
                "extracted_number": "",
                "level": level,
                "numbering_type": "none",
                "level_counter": level_counters.copy(),
                "parent_changes": parent_level_changes.copy(),
                "full_text": text,
                "raw_indent": raw_indent,
                "rich_content": rich_content,
                "alignment": _alignment,
                "font_size_pt": _font_size_pt,
                "font_family": _font_family,
                "after_table": is_table_title or (orig_idx in _after_table_indices),
            })
    
    return results


def generate_number_by_level(level: int, counters: Dict[int, int], number_type: str) -> str:
    """
    레벨과 카운터에 따라 번호를 생성합니다.

    Args:
        level: 번호 레벨
        counters: 레벨별 카운터 사전
        number_type: 번호 유형

    Returns:
        생성된 번호 문자열
    """
    if level == 0:
        # "제N장" 형식
        return f"제{counters[0]}장"

    elif level == 1:
        if "article" in number_type:
            # "제N조" 형식
            return f"제{counters[1]}조"
        else:
            # "N." 형식
            return f"{counters[1]}."
    
    elif level == 2:
        if "subsection" in number_type:
            # "N-N." 형식 - 첫 번째 N은 상위 레벨 번호
            return f"{counters[1]}-{counters[2]}."
        elif "circle_number" in number_type:
            # 원형 숫자 형식 (①, ②, ③ 등) - KB신용정보 사규에서 항(項)으로 사용
            circle_numbers = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟"
            circle_num = circle_numbers[counters[2] - 1] if 1 <= counters[2] <= 35 else '?'
            return circle_num
        elif "section" in number_type:
            # "N." 형식 - 원본 문서의 항(項) 표기 유지 (1., 2., 3.)
            return f"{counters[2]}."
        else:
            # "N)" 형식
            return f"{counters[2]})"
    
    elif level == 3:
        if "item_number" in number_type or "xml_item" in number_type:
            # "N)" 형식
            return f"{counters[3]})"
        elif "parenthesis" in number_type:
            # "(N)" 형식
            return f"({counters[3]})"
        elif "alpha_point" in number_type:
            # "a." 형식 - 숫자를 알파벳으로 변환
            alpha = chr(ord('a') + counters[3] - 1) if 1 <= counters[3] <= 26 else '?'
            return f"{alpha}."
        elif "circle_number" in number_type:
            # 원형 숫자 형식 (확장)
            circle_numbers = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟"
            circle_num = circle_numbers[counters[3] - 1] if 1 <= counters[3] <= 35 else '?'
            return circle_num
        else:
            # 기타 형식 - 기본적으로 "(N)" 형식 사용
            return f"({counters[3]})"
    
    elif level == 4:
        if "korean_char" in number_type:
            # "(가)" 형식 - 한글 자모
            korean_chars = "가나다라마바사아자차카타파하"
            korean_char = korean_chars[counters[4] - 1] if 1 <= counters[4] <= len(korean_chars) else '?'
            return f"({korean_char})"
        elif "circle_korean" in number_type:
            # "㉮" 형식 - 원형 한글
            circle_korean_chars = "㉮㉯㉰㉱㉲㉳㉴㉵㉶㉷㉸㉹㉺㉻"
            circle_korean = circle_korean_chars[counters[4] - 1] if 1 <= counters[4] <= len(circle_korean_chars) else '?'
            return circle_korean
        elif "alpha_upper" in number_type:
            # "A." 형식 - 대문자 알파벳
            alpha = chr(ord('A') + counters[4] - 1) if 1 <= counters[4] <= 26 else '?'
            return f"{alpha}."
        else:
            # 기타 형식 - 기본적으로 한글 자모 사용
            korean_chars = "가나다라마바사아자차카타파하"
            korean_char = korean_chars[counters[4] - 1] if 1 <= counters[4] <= len(korean_chars) else '?'
            return f"({korean_char})"
    
    elif level == 5:
        if "circle_alpha" in number_type:
            # "ⓐ" 형식 - 원형 알파벳
            circle_alpha = "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ"
            circle_a = circle_alpha[counters[5] - 1] if 1 <= counters[5] <= 26 else '?'
            return circle_a
        elif "roman_numeral" in number_type:
            # "ⅰ)" 형식 - 로마자
            roman_numerals = "ⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ"
            roman = roman_numerals[counters[5] - 1] if 1 <= counters[5] <= 10 else '?'
            return f"{roman})"
        else:
            # 기타 형식 - 기본적으로 로마자 형식 사용
            roman_numerals = "ⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ"
            roman = roman_numerals[counters[5] - 1] if 1 <= counters[5] <= 10 else '?'
            return f"{roman})"

    elif level == 6:
        # "a." 형식 - 소문자 알파벳 재사용
        alpha = chr(ord('a') + counters[6] - 1) if 1 <= counters[6] <= 26 else '?'
        return f"{alpha}."

    elif level == 7:
        # "a)" 형식 - 소문자 알파벳
        alpha = chr(ord('a') + counters[7] - 1) if 1 <= counters[7] <= 26 else '?'
        return f"{alpha})"

    elif level == 8:
        # "(a)" 형식 - 소문자 알파벳
        alpha = chr(ord('a') + counters[8] - 1) if 1 <= counters[8] <= 26 else '?'
        return f"({alpha})"

    return ""


def extract_numbering(paragraph, text: str) -> Optional[Dict[str, Any]]:
    """
    텍스트와 단락 객체에서 번호 형식을 추출합니다.
    
    Args:
        paragraph: docx 단락 객체
        text: 단락 텍스트
        
    Returns:
        번호 정보 사전 또는 None
    """
    # 개정 이력 특수 패턴들
    if text == "(참고)":
        return {
            "number": "제5조",
            "level": 1,
            "type": "reference_section"
        }

    if text == "내규의 제·개정 이력":
        return {
            "number": "",
            "level": 1,
            "type": "revision_history_title"
        }

    if text == "(내규의 제정 및 시행)":
        return {
            "number": "제 1조",
            "level": 2,
            "type": "revision_enactment"
        }

    if text == "(내규의 전면개정 및 시행)":
        return {
            "number": "제 2조",
            "level": 2,
            "type": "revision_full_amendment"
        }

    if text == "(내규의 개정)":
        return {
            "number": "제 3조",
            "level": 2,
            "type": "revision_amendment"
        }

    # 개정 이력 하위 항목들 (번호 없이 시작하는 경우)
    if text.startswith("이 내규는") and ("시행한다" in text):
        return {
            "number": "1)",
            "level": 3,
            "type": "revision_detail"
        }

    # "1. 이 내규는..." 형식
    if re.match(r'^1\.\s*이 내규는.*시행한다', text):
        return {
            "number": "1)",
            "level": 3,
            "type": "revision_detail"
        }

    # 제N장 형식 (장 제목) - 공백 허용: "제 1 장"
    match_chapter = re.match(r'^제\s*(\d+)\s*장\s+(.+)', text)
    if match_chapter:
        return {
            "number": f"제{match_chapter.group(1)}장",
            "level": 0,
            "type": "chapter_ko"
        }

    # 제N조 형식 (한글 조문) - 공백 허용: "제 1 조(목적)"
    match_article = re.match(r'^제\s*(\d+)\s*조\s*\(([^)]+)\)', text)
    if match_article:
        return {
            "number": f"제{match_article.group(1)}조",
            "level": 1,
            "type": "article_ko"
        }

    # 제N조 형식 (괄호 없이) - 공백 허용: "제 10 조 삭제"
    match_article_simple = re.match(r'^제\s*(\d+)\s*조\s+', text)
    if match_article_simple:
        return {
            "number": f"제{match_article_simple.group(1)}조",
            "level": 1,
            "type": "article_ko"
        }
    
    # N. (목적) 형식 (숫자 점 괄호)
    match_section = re.match(r'^(\d+)\.\s*\(([^)]+)\)', text)
    if match_section:
        return {
            "number": f"{match_section.group(1)}.",
            "level": 1,
            "type": "section_number"
        }
    
    # N. 형식 (숫자 점)
    match_simple_section = re.match(r'^(\d+)\.\s+', text)
    if match_simple_section:
        return {
            "number": f"{match_simple_section.group(1)}.",
            "level": 1,
            "type": "section_number"
        }
    
    # N-N. 형식 (숫자-숫자 점)
    match_subsection = re.match(r'^(\d+-\d+)\.\s*', text)
    if match_subsection:
        return {
            "number": match_subsection.group(1) + ".",
            "level": 2,
            "type": "subsection_number"
        }
    
    # N) 형식 (숫자 괄호)
    match_item = re.match(r'^\s*(\d+)\)\s*', text)
    if match_item:
        # 수준 결정 - 들여쓰기를 기반으로
        indent_level = 0
        for char in text:
            if char in [' ', '\t']:
                indent_level += 1
            else:
                break

        # 기본 레벨 결정
        basic_level = 3 if indent_level >= 8 else 2

        # 문맥 기반 레벨 조정: 내용에 "위원회"가 있고 번호가 1)이나 2)인 경우 레벨 3으로 조정
        item_number = int(match_item.group(1))
        if (item_number <= 5 and any(keyword in text for keyword in ['위원회는', '위원회 전반', '위원회의'])):
            basic_level = 3

        return {
            "number": match_item.group(1) + ")",
            "level": basic_level,
            "type": "item_number"
        }
    
    # (N) 형식 (괄호 숫자 괄호)
    match_parenthesis = re.match(r'^\s*\((\d+)\)\s*', text)
    if match_parenthesis:
        return {
            "number": f"({match_parenthesis.group(1)})",
            "level": 3,
            "type": "parenthesis_number"
        }
    
    # a. 형식 (알파벳 점) - 들여쓰기에 따라 레벨 결정
    match_alpha = re.match(r'^([a-z])\.\s*', text)
    if match_alpha:
        # 들여쓰기 정도에 따라 레벨 결정
        indent_level = 0
        for char in text:
            if char in [' ', '\t']:
                indent_level += 1
            else:
                break

        # 들여쓰기가 많으면 레벨 6, 적으면 레벨 3
        alpha_level = 6 if indent_level >= 16 else 3

        return {
            "number": match_alpha.group(1) + ".",
            "level": alpha_level,
            "type": "alpha_point"
        }
    
    # A. 형식 (대문자 알파벳 점)
    match_alpha_upper = re.match(r'^([A-Z])\.\s*', text)
    if match_alpha_upper:
        return {
            "number": match_alpha_upper.group(1) + ".",
            "level": 4,
            "type": "alpha_upper"
        }
    
    # 원형 숫자 형식 (①, ②, ...) - 확장
    # KB신용정보 사규에서는 항(項)으로 사용되므로 레벨 2
    match_circle = re.match(r'^\s*([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟])\s*', text)
    if match_circle:
        return {
            "number": match_circle.group(1),
            "level": 2,  # 레벨 3 → 2로 수정 (항)
            "type": "circle_number"
        }
    
    # (가) 형식 (한글 자모)
    match_korean_char = re.match(r'^\s*\(([가-힣])\)\s*', text)
    if match_korean_char:
        return {
            "number": f"({match_korean_char.group(1)})",
            "level": 4,
            "type": "korean_char"
        }
    
    # ㉮ 형식 (원형 한글)
    match_circle_korean = re.match(r'^\s*([㉮-㉻])\s*', text)
    if match_circle_korean:
        return {
            "number": match_circle_korean.group(1),
            "level": 4,
            "type": "circle_korean"
        }
    
    # ㉠ 형식 (원형 한글 자음)
    match_circle_korean_consonant = re.match(r'^\s*([㉠-㉥])\s*', text)
    if match_circle_korean_consonant:
        return {
            "number": match_circle_korean_consonant.group(1),
            "level": 4,
            "type": "circle_korean_consonant"
        }
    
    # ⓐ 형식 (원형 알파벳)
    match_circle_alpha = re.match(r'^\s*([ⓐ-ⓩ])\s*', text)
    if match_circle_alpha:
        return {
            "number": match_circle_alpha.group(1),
            "level": 5,
            "type": "circle_alpha"
        }
    
    # ⅰ) 형식 (로마자)
    match_roman = re.match(r'^\s*([ⅰ-ⅹ])\)\s*', text)
    if match_roman:
        return {
            "number": f"{match_roman.group(1)})",
            "level": 5,
            "type": "roman_numeral"
        }

    # a) 형식 (레벨 7)
    match_alpha_paren = re.match(r'^([a-z])\)\s*', text)
    if match_alpha_paren:
        return {
            "number": f"{match_alpha_paren.group(1)})",
            "level": 7,
            "type": "alpha_paren"
        }

    # (a) 형식 (레벨 8)
    match_alpha_parenthesis = re.match(r'^\(([a-z])\)\s*', text)
    if match_alpha_parenthesis:
        return {
            "number": f"({match_alpha_parenthesis.group(1)})",
            "level": 8,
            "type": "alpha_parenthesis"
        }

    # XML에서 자동번호매기기 속성 확인
    number_from_xml = extract_numbering_from_xml(paragraph)
    if number_from_xml:
        return number_from_xml

    return None


def extract_numbering_from_xml(paragraph) -> Optional[Dict[str, Any]]:
    """
    단락의 XML에서 자동번호매기기 속성을 추출합니다.
    
    Args:
        paragraph: docx 단락 객체
        
    Returns:
        번호 정보 사전 또는 None
    """
    try:
        if hasattr(paragraph, '_element') and paragraph._element is not None:
            # numPr 요소 확인 (번호 매기기 속성)
            num_pr = paragraph._element.xpath('.//w:numPr')
            if num_pr:
                # numId와 ilvl 값을 확인
                num_id = paragraph._element.xpath('.//w:numId/@w:val')
                level_id = paragraph._element.xpath('.//w:ilvl/@w:val')
                
                if num_id and level_id:
                    level = int(level_id[0])
                    
                    # 이미지에서 보이는 패턴과 매핑 - 수정된 로직
                    if level == 0:
                        return {
                            "number": "1.",  # 기본 레벨 1 번호
                            "level": 1,
                            "type": "xml_section"
                        }
                    elif level == 1:
                        return {
                            "number": "숫자.",  # 실제로는 "1.", "2." 등으로 변환됨
                            "level": 2,
                            "type": "xml_section"
                        }
                    elif level == 2:
                        return {
                            "number": "숫자)",  # 실제로는 "1)", "2)" 등으로 변환됨
                            "level": 3,
                            "type": "xml_item"
                        }
                    elif level == 3:
                        return {
                            "number": "(숫자)",  # 실제로는 "(1)", "(2)" 등으로 변환됨
                            "level": 4,
                            "type": "xml_parenthesis"
                        }
                    elif level == 4:
                        return {
                            "number": "(가)",  # 실제로는 "(가)", "(나)" 등으로 변환됨
                            "level": 5,
                            "type": "xml_korean_char"
                        }
                    elif level == 5:
                        return {
                            "number": "a.",  # 실제로는 "a.", "b." 등으로 변환됨
                            "level": 6,
                            "type": "xml_alpha_point"
                        }
                    else:
                        return {
                            "number": "기타",
                            "level": min(level + 1, 8),  # 최대 레벨 8
                            "type": "xml_other"
                        }
    except Exception:
        pass
    
    return None


def convert_to_sections_format(extract_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    추출 결과를 조문내용 형식으로 변환합니다.

    Args:
        extract_results: extract_numbers_from_docx 함수의 결과

    Returns:
        조문내용 형식의 리스트
    """
    sections = []

    # 모듈 상수 NUMBER_PREFIX_PATTERNS 사용
    number_patterns = NUMBER_PREFIX_PATTERNS

    # 이미지 캡션 패턴 제거를 위한 정규식 (더 구체적으로)
    caption_patterns = [
        r'\s*\[그림\s*\d*[^\]]*\]\s*$',  # [그림1], [그림 1. 제목] 등
        r'\s*\[표\s*\d*[^\]]*\]\s*$',   # [표1], [표 1. 제목] 등
        r'\s*\[첨부\s*\d*[^\]]*\]\s*$', # [첨부1], [첨부 1. 파일명] 등
        r'\s*<[가-힣\s]+>\s*$',          # 끝에 있는 <한글캡션> 패턴 (HTML 태그 제외)
    ]

    # 문서의 기본 폰트 크기 계산 (가장 많이 사용된 크기)
    _all_sizes = Counter()
    for item in extract_results:
        _fs = item.get('font_size_pt')
        if _fs is not None:
            _text_len = len(item.get('original_text', ''))
            _all_sizes[_fs] += _text_len
    base_font_size = _all_sizes.most_common(1)[0][0] if _all_sizes else None

    # 문서의 기본 폰트 패밀리 계산 (가장 많이 사용된 폰트)
    _all_fonts = Counter()
    for item in extract_results:
        _ff = item.get('font_family')
        if _ff:
            _all_fonts[_ff] += len(item.get('original_text', ''))
    base_font_family = _all_fonts.most_common(1)[0][0] if _all_fonts else None

    # 연속된 내용 병합을 위한 임시 섹션 생성
    temp_sections = []

    for i, item in enumerate(extract_results):
        if item.get('level') is not None:  # 번호 매기기가 있는 항목만 포함
            full_text = item.get('full_text', '')

            # 내용에서 처음 나오는 번호 패턴 제거 (plain text용)
            cleaned_text = full_text
            for pattern in number_patterns:
                cleaned_text = re.sub(pattern, '', cleaned_text)
                if cleaned_text != full_text:  # 패턴이 매치되어 제거된 경우
                    break

            # rich_content 사용 (bold 서식 보존), 없으면 cleaned_text 사용
            display_text = item.get('rich_content', '') or cleaned_text

            # 내용 끝부분의 이미지 캡션 패턴 제거
            for pattern in caption_patterns:
                display_text = re.sub(pattern, '', display_text).strip()

            temp_sections.append({
                "seq": i + 1,
                "레벨": item.get('level'),
                "내용": display_text,
                "번호": item.get('extracted_number', ''),
                "numbering_type": item.get('numbering_type', 'none'),
                "raw_indent": item.get('raw_indent', 0),
                "alignment": item.get('alignment'),
                "font_size_pt": item.get('font_size_pt'),
                "after_table": item.get('after_table', False),
                "관련이미지": []
            })

    # 연속된 내용 병합 처리
    merged_sections = []
    i = 0
    while i < len(temp_sections):
        current_section = temp_sections[i]

        # 연속된 번호 없는 단락들을 모두 병합
        while i + 1 < len(temp_sections):
            next_section = temp_sections[i + 1]

            # 다음 섹션이 번호가 없고 새로운 조문이 아닌 경우 병합
            # HTML 태그 제거 후 순수 텍스트로 판단
            _next_plain = re.sub(r'<[^>]+>', '', next_section['내용']).strip()
            if (next_section['번호'] == '' and
                next_section['numbering_type'] == 'none' and
                # 테이블 직후 문단은 병합 금지 (주: 텍스트가 이미지 아래로 분리)
                not next_section.get('after_table') and
                # 다음 내용이 명백히 새로운 조문/장이 아닌 경우
                not re.match(r'^제\s*\d+\s*장|^제\s*\d+\s*절|^제\s*\d+\s*조|^\([목적정의절차부록참고]|^[가-힣]+위원회$', _next_plain) and
                # 『별표 제N호』는 별표 섹션의 시작 → 병합 중단
                not re.match(r'^『별표', _next_plain) and
                # "부칙" / "부 칙" 은 별도 섹션으로 분리
                not re.match(r'^부\s*칙\s*$', _next_plain)):

                next_content = next_section['내용']
                next_alignment = next_section.get('alignment')
                current_alignment = current_section.get('alignment')

                # 다른 정렬의 문단은 <div> 태그로 감싸서 정렬 보존
                if next_alignment and next_alignment != current_alignment:
                    div_style = f'text-align:{next_alignment}'
                    _next_fs = next_section.get('font_size_pt')
                    if _next_fs is not None and base_font_size is not None and abs(_next_fs - base_font_size) >= 1.0:
                        div_style += f'; font-size:{_next_fs}pt'
                    next_content = f'<div style="{div_style}">{next_content}</div>'
                    separator = ''
                else:
                    # 높은 들여쓰기(>=10) 문단은 시각적 레이아웃 (분수식 등)
                    raw_indent = next_section.get('raw_indent', 0)
                    if raw_indent >= 10:
                        separator = '<br>'
                    else:
                        separator = ' '

                merged_content = current_section['내용'] + separator + next_content
                current_section['내용'] = merged_content

                # 다음 섹션은 건너뜀
                i += 1
            else:
                # 병합 조건을 만족하지 않으면 중단
                break

        # 정렬 정보를 최종 섹션에 저장 (첫 문단의 정렬)
        section_dict = {
            "seq": len(merged_sections) + 1,
            "레벨": current_section['레벨'],
            "내용": current_section['내용'],
            "번호": current_section['번호'],
            "관련이미지": current_section['관련이미지']
        }
        if current_section.get('alignment'):
            section_dict['정렬'] = current_section['alignment']
        # 글꼴 크기: 기본 크기 대비 1pt 이상 차이나는 경우 저장
        _sect_fs = current_section.get('font_size_pt')
        if _sect_fs is not None and base_font_size is not None and abs(_sect_fs - base_font_size) >= 1.0:
            section_dict['글꼴크기'] = _sect_fs
        merged_sections.append(section_dict)

        i += 1

    # 분수 수식 후처리: 밑줄(____) 패턴을 HTML 분수로 변환
    fraction_pattern = re.compile(
        r'<br>([^<]+?)<br>([^<]*?)_{4,}[^<]*?<br>(\s*\S+)',
        re.DOTALL
    )
    for section in merged_sections:
        content = section.get('내용', '')
        if '____' in content:
            def replace_fraction(m):
                numerator = m.group(1).strip()
                prefix_line = m.group(2).strip()
                denominator = m.group(3).strip()
                # prefix에서 밑줄 제거하고 × 앞부분 추출
                prefix = re.sub(r'\s*_{4,}.*', '', prefix_line).strip()
                if prefix:
                    prefix_html = f'{prefix} '
                else:
                    prefix_html = ''
                return (f'<div class="formula-wrapper">'
                        f'{prefix_html}'
                        f'<span class="fraction">'
                        f'<span class="numerator">{numerator}</span>'
                        f'<span class="denominator">{denominator}</span>'
                        f'</span></div>')
            section['내용'] = fraction_pattern.sub(replace_fraction, content)

    return merged_sections, base_font_family
