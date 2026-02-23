import pdfplumber
import sys
import os
import re
import glob
import logging
from datetime import datetime

# 로그 설정
log_dir = os.path.join(os.path.dirname(__file__), 'log')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f'pdf2txt_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('pdf2txt')

def extract_text_from_pdf(pdf_path, txt_path=None, parse_tables=False, detect_tables_and_remove=False):
    """
    PDF 파일에서 텍스트를 추출하여 TXT 파일로 저장

    Args:
        pdf_path: 입력 PDF 파일 경로
        txt_path: 출력 TXT 파일 경로 (None일 경우 자동 생성)
        parse_tables: 테이블 파싱 여부 (기본값: False)
        detect_tables_and_remove: 테이블 감지 후 제거 여부 (기본값: False)
    """
    if txt_path is None:
        base_name = os.path.splitext(pdf_path)[0]
        txt_path = f"{base_name}.txt"
    
    try:
        logger.info(f"PDF 파일 처리 시작: {pdf_path}, 테이블 파싱: {parse_tables}, 테이블 제거: {detect_tables_and_remove}")
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            total_pages = len(pdf.pages)

            print(f"PDF 파일 열기 성공: {pdf_path}")
            print(f"총 페이지 수: {total_pages}")
            logger.info(f"PDF 파일 열기 성공: {pdf_path}, 총 페이지 수: {total_pages}")
            
            for i, page in enumerate(pdf.pages):
                print(f"페이지 {i+1}/{total_pages} 처리 중...", end='\r')
                
                # 테이블 감지 및 처리
                tables = page.extract_tables()
                table_areas = []

                if tables and detect_tables_and_remove:
                    # 테이블 영역 추출 (테이블 제거를 위해)
                    for table in tables:
                        if table:
                            # 테이블의 첫 번째와 마지막 행을 기준으로 영역 계산
                            table_area = get_table_area(page, table)
                            if table_area:
                                table_areas.append(table_area)

                    # 테이블 영역을 제외하고 텍스트 추출
                    page_text = extract_text_excluding_tables(page, table_areas)
                else:
                    # 일반 텍스트 추출
                    page_text = page.extract_text()

                    # 테이블 파싱이 활성화된 경우 테이블 데이터 추가
                    if parse_tables and tables:
                        table_text = extract_table_text(tables)
                        if table_text:
                            page_text = (page_text or "") + "\n\n" + table_text

                if page_text:
                    # 페이지 정보 제거
                    page_text = remove_page_info(page_text)
                    
                    # 텍스트 정리
                    page_text = clean_text(page_text)
                    
                    # 줄바꿈 최적화
                    page_text = optimize_line_breaks(page_text)

                    full_text += page_text + "\n"
                    
                    # 페이지 구분자 추가 (페이지 번호는 표시하지 않음)
                    if i < total_pages - 1:
                        full_text += "\n--- 페이지 구분 ---\n\n"
            
            # 최종 텍스트 정리
            full_text = final_cleanup(full_text)
            
            # TXT 파일로 저장
            with open(txt_path, 'w', encoding='utf-8') as txt_file:
                txt_file.write(full_text)
            
            print(f"\n텍스트 추출 완료: {txt_path}")
            print(f"파일 크기: {os.path.getsize(txt_path):,} bytes")
            logger.info(f"텍스트 추출 완료: {txt_path}, 파일 크기: {os.path.getsize(txt_path):,} bytes")

            return txt_path

    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        logger.error(f"PDF 처리 오류: {str(e)}", exc_info=True)
        return None

def extract_table_text(tables):
    """
    테이블 데이터를 텍스트로 변환

    Args:
        tables: pdfplumber에서 추출한 테이블 리스트

    Returns:
        테이블을 텍스트 형태로 변환한 문자열
    """
    if not tables:
        return ""

    table_texts = []
    for i, table in enumerate(tables):
        if not table:
            continue

        table_text = f"\n[테이블 {i+1}]\n"

        for row in table:
            if row:
                # None 값을 빈 문자열로 변경하고 셀을 탭으로 구분
                cleaned_row = [str(cell) if cell is not None else "" for cell in row]
                table_text += "\t".join(cleaned_row) + "\n"

        table_texts.append(table_text)

    return "\n".join(table_texts)

def get_table_area(page, table):
    """
    테이블의 영역(bbox)을 계산

    Args:
        page: pdfplumber page 객체
        table: 테이블 데이터

    Returns:
        테이블 영역 좌표 (x0, y0, x1, y1) 또는 None
    """
    try:
        # pdfplumber의 find_tables를 사용하여 테이블 객체의 bbox 가져오기
        table_objects = page.find_tables()
        for table_obj in table_objects:
            if table_obj.extract() == table:
                return table_obj.bbox
        return None
    except:
        return None

def extract_text_excluding_tables(page, table_areas):
    """
    테이블 영역을 제외하고 텍스트 추출

    Args:
        page: pdfplumber page 객체
        table_areas: 테이블 영역 리스트

    Returns:
        테이블이 제거된 텍스트
    """
    if not table_areas:
        return page.extract_text()

    try:
        # 페이지를 크롭하여 테이블 영역 제외
        page_width = page.width
        page_height = page.height

        # 테이블 영역들을 y 좌표 기준으로 정렬
        sorted_areas = sorted(table_areas, key=lambda area: area[1])

        text_parts = []
        current_y = 0

        for area in sorted_areas:
            x0, y0, x1, y1 = area

            # 테이블 위쪽 영역에서 텍스트 추출
            if y0 > current_y:
                top_crop = page.crop((0, current_y, page_width, y0))
                top_text = top_crop.extract_text()
                if top_text and top_text.strip():
                    text_parts.append(top_text)

            # 다음 영역을 위해 y 좌표 업데이트
            current_y = max(current_y, y1)

        # 마지막 테이블 아래쪽 영역 처리
        if current_y < page_height:
            bottom_crop = page.crop((0, current_y, page_width, page_height))
            bottom_text = bottom_crop.extract_text()
            if bottom_text and bottom_text.strip():
                text_parts.append(bottom_text)

        return "\n".join(text_parts)

    except Exception as e:
        # 오류가 발생하면 전체 텍스트 반환
        logger.warning(f"테이블 제거 중 오류 발생: {e}")
        return page.extract_text()

def process_folder(input_path, output_path, parse_tables=False, detect_tables_and_remove=False):
    """
    폴더 내의 모든 PDF 파일을 처리

    Args:
        input_path: PDF 파일들이 있는 폴더 경로
        output_path: TXT 파일들을 저장할 폴더 경로
        parse_tables: 테이블 파싱 여부 (기본값: False)
        detect_tables_and_remove: 테이블 감지 후 제거 여부 (기본값: False)
    """
    # 출력 폴더가 없으면 생성
    os.makedirs(output_path, exist_ok=True)
    
    # PDF 파일 목록 가져오기
    pdf_files = glob.glob(os.path.join(input_path, "*.pdf"))
    
    if not pdf_files:
        print(f"경로에 PDF 파일이 없습니다: {input_path}")
        return
    
    print(f"총 {len(pdf_files)}개의 PDF 파일을 찾았습니다.")
    print("-" * 50)
    
    success_count = 0
    fail_count = 0
    
    for idx, pdf_path in enumerate(pdf_files, 1):
        # 파일명만 추출 (확장자 제외)
        filename = os.path.basename(pdf_path)
        filename_without_ext = os.path.splitext(filename)[0]
        
        # 출력 파일 경로 생성
        txt_path = os.path.join(output_path, f"{filename_without_ext}.txt")
        
        print(f"\n[{idx}/{len(pdf_files)}] 처리 중: {filename}")
        
        # PDF 변환
        result = extract_text_from_pdf(pdf_path, txt_path, parse_tables, detect_tables_and_remove)
        
        if result:
            success_count += 1
        else:
            fail_count += 1
        
        print("-" * 50)
    
    # 최종 결과 출력
    print(f"\n변환 완료!")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"출력 경로: {output_path}")

def remove_page_info(text):
    """페이지 정보 제거"""
    # 페이지 번호 패턴들
    page_patterns = [
        # 페이지 X / Y 형식
        r'페이지\s*\d+\s*/\s*\d+',
        r'Page\s*\d+\s*/\s*\d+',
        r'page\s*\d+\s*/\s*\d+',
        r'\d+\s*/\s*\d+\s*페이지',
        
        # - X - 형식 (페이지 번호)
        r'^-\s*\d+\s*-\s*$',
        r'^\s*-\s*\d+\s*-\s*$',
        
        # 단순 페이지 번호 (줄의 시작 또는 끝)
        r'^\s*\d{1,3}\s*$',  # 줄의 전체가 1-3자리 숫자
        r'^\s*\[\s*\d+\s*\]\s*$',  # [1] 형식
        r'^\s*\(\s*\d+\s*\)\s*$',  # (1) 형식
        
        # 머리글/바닥글의 페이지 정보
        r'^\s*\d+\s*\|\s*.*$',  # 1 | 제목 형식
        r'^.*\s*\|\s*\d+\s*$',  # 제목 | 1 형식
    ]
    
    # 줄 단위로 분리하여 처리
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # 각 패턴을 확인하여 페이지 정보인지 검사
        is_page_info = False
        for pattern in page_patterns:
            if re.match(pattern, line.strip(), re.IGNORECASE):
                is_page_info = True
                break
        
        # 페이지 정보가 아닌 경우만 추가
        if not is_page_info:
            # 줄 내부의 페이지 정보도 제거
            line = re.sub(r'페이지\s*\d+\s*/\s*\d+', '', line, flags=re.IGNORECASE)
            line = re.sub(r'Page\s*\d+\s*/\s*\d+', '', line, flags=re.IGNORECASE)
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def clean_table_artifacts(text):
    """표 파싱 잔재물 및 테이블 구조 정리"""
    lines = text.split('\n')
    cleaned_lines = []

    for i, line in enumerate(lines):
        line = line.strip()

        if not line:
            cleaned_lines.append('')
            continue

        # 표 헤더로 보이는 패턴들 제거
        table_header_patterns = [
            # 반복되는 헤더 패턴 (예: "기능평가 범위 기능평가 범위 추후관리 필요 최소 기준")
            r'^(.+?)\s+\1\s+(.+?)$',  # 같은 단어가 반복되는 패턴

            # 표의 구분선이나 잘못 파싱된 구조
            r'^[-=_\s|]+$',  # 선으로만 이루어진 줄
            r'^[│┌┐└┘├┤┬┴┼]+$',  # 표 테두리 문자들

            # 표 셀 구분자가 많이 포함된 줄 (3개 이상의 탭이나 여러 공백)
            r'^.*\t.*\t.*\t.*$',  # 탭이 3개 이상 포함된 줄
        ]

        is_table_artifact = False

        # 패턴 확인
        for pattern in table_header_patterns:
            if re.match(pattern, line):
                is_table_artifact = True
                break

        # 반복 헤더 특별 처리 - 테이블 헤더에서 반복되는 구문 제거
        original_line = line

        # 번호 매김 부분 분리
        number_match = re.match(r'^(\d+\)\s*|\(\d+\)\s*)', line)
        number_prefix = number_match.group(0) if number_match else ""
        line_without_number = line[len(number_prefix):] if number_prefix else line

        # 단어를 분리하여 반복 패턴 찾기
        words = line_without_number.split()
        if len(words) >= 4:
            # 연속된 단어들이 반복되는지 확인
            for phrase_len in range(1, len(words) // 2 + 1):
                for start_pos in range(0, len(words) - phrase_len * 2 + 1):
                    first_phrase = words[start_pos:start_pos + phrase_len]
                    second_phrase = words[start_pos + phrase_len:start_pos + phrase_len * 2]

                    if first_phrase == second_phrase:
                        # 반복되는 구문을 찾았음 - 한 번만 남기고 나머지 단어들 보존
                        remaining_words = (words[:start_pos] +
                                        first_phrase +
                                        words[start_pos + phrase_len * 2:])
                        if len(remaining_words) > len(first_phrase):
                            line = number_prefix + ' '.join(remaining_words)
                            break
                if line != original_line:
                    break

        # 테이블 구조물이 아닌 경우만 추가
        if not is_table_artifact:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)

def clean_text(text):
    """텍스트 정리"""
    # 대외비, 머리글/바닥글 제거
    text = re.sub(r'대외비.*?\n', '', text)
    text = re.sub(r'CONFIDENTIAL.*?\n', '', text, flags=re.IGNORECASE)

    # 반복되는 머리글/바닥글 패턴 제거 (주의: 내용 중의 세브란스병원 내규 언급은 제거하지 않도록 수정)
    header_footer_patterns = [
        r'^세브란스병원.*?내규.*?\n',  # 줄의 시작에만 있는 경우만
        r'Severance Hospital.*?\n',
        r'Copyright.*?\n',
        r'©.*?\n',
    ]

    for pattern in header_footer_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

    # 표 패턴 제거 - 테이블 헤더나 잘못 파싱된 표 구조 정리
    text = clean_table_artifacts(text)

    # 여러 공백을 하나로
    text = re.sub(r'[ \t]+', ' ', text)

    # 연속된 빈 줄을 하나로
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text

def optimize_line_breaks(text):
    """줄바꿈 최적화 - 수정된 내규 서식 체계"""
    lines = text.split('\n')
    optimized_lines = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            optimized_lines.append('')
            i += 1
            continue
        
        # 제목이나 번호로 시작하는 경우 새 줄 유지
        title_patterns = [
            # 조문 (제목이 포함된 경우만)
            r'^제\s*\d+\s*조\s*\(',          # 제1조 (목적) - 제목이 있는 조문만
            r'^\d+\.\s*\(',                 # 1. (목적) - 조문 제목
            
            # 계층적 번호 체계 (문서 분석 결과)
            # 2.1.2.2. 같은 다중 점 번호는 내용에 부록이 있으면 제외
            r'^(?!\d+\.\d+\.\d+.*부록)\d+\.\s+',   # 1. 항 (부록이 포함된 다중점 번호는 제외)
            r'^\d+\)\s*',                   # 1) 호
            r'^\(\d+\)\s*',                 # (1) 목
            r'^[①-⑳]\s*',                  # ① 세목
            r'^[a-z]\.\s*',                 # a. 세목이하1
            r'^[a-z]\)\s*',                 # a) 세목이하2
            r'^\([a-z]\)\s*',               # (a) 세목이하3
            
            # 한글 체계 (혼용 가능)
            r'^\([가-하]\)\s*',             # (가)
            r'^[가-하]\.\s*',               # 가.
            r'^[가-하]\)\s*',               # 가)
            
            # 섹션 제목 (부록은 제외 - 내용으로 처리)
            # r'^\(부록\)',                 # (부록) - 주석 처리, 내용으로 파싱
            r'^\(참고\)',                   # (참고)
            r'^\(목적\)',                   # (목적)
            r'^\(정의\)',                   # (정의)
            r'^\(절차\)',                   # (절차)
            r'^\(내규의',                   # (내규의 제정 및 시행) 등

            # 부록/별표 제목 패턴 (번호가 있는 경우만)
            r'^부록\s*\d+',                 # 부록 1, 부록 2 등
            r'^별표\s*\d+',                 # 별표 1, 별표 2 등
            r'^\[부록\s*\d+\]',             # [부록 1] 형식
            r'^\[별표\s*\d+\]',             # [별표 1] 형식
            
            # 특수 기호
            r'^[◎◈▶▷■□◆◇○●]\s*',     # 특수 기호
            r'^[-*]\s+',                    # 대시나 별표로 시작하는 목록
            
            # 볼드체 섹션 (** 로 둘러싸인 제목)
            r'^\*\*.*\*\*',                 # **제목**
        ]
        
        # 부록이 포함된 라인에 대한 특별 처리
        # "2.1.2.2. 부록4." 같은 패턴은 내용으로 처리
        if re.match(r'^\d+(\.\d+)+.*부록', line):
            is_new_item = False  # 다중 점 번호에 부록이 있으면 내용으로 처리
        elif line.strip() == '(부록)' or line.startswith('(부록) '):
            is_new_item = False  # (부록)으로 시작하면 내용으로 처리
        else:
            is_new_item = any(re.match(pattern, line) for pattern in title_patterns)

        if is_new_item:
            # 새 항목은 빈 줄 추가 (단, 연속된 하위 항목은 제외)
            if i > 0 and optimized_lines and optimized_lines[-1] != '':
                # 이전 줄과 현재 줄의 레벨 확인
                prev_level = get_item_level(optimized_lines[-1])
                curr_level = get_item_level(line)
                
                # 같은 레벨이거나 상위 레벨로 올라가는 경우만 빈 줄 추가
                if curr_level <= prev_level:
                    optimized_lines.append('')
            
            optimized_lines.append(line)
        else:
            # 일반 텍스트는 이전 줄과 합칠지 결정
            if optimized_lines and optimized_lines[-1] != '':
                prev_line = optimized_lines[-1]

                # 문장이 완료된 경우 새 줄로
                if prev_line.endswith(('.', '다.', '요.', '함.', '임.', '됨.', '한다.')):
                    optimized_lines.append(line)
                # 콜론이나 리스트 시작인 경우 새 줄로
                elif prev_line.endswith(':') or prev_line.endswith('：'):
                    optimized_lines.append(line)
                # 표 또는 특수 서식인 경우 새 줄로
                elif '---' in prev_line or '___' in prev_line or '===' in prev_line:
                    optimized_lines.append(line)
                # 볼드체로 끝나는 경우 새 줄로
                elif prev_line.endswith('**'):
                    optimized_lines.append(line)
                # 현재 줄이 번호 매김 패턴으로 시작하는 경우 새 줄로 (중요한 수정)
                elif re.match(r'^\(\d+\)\s*', line) or re.match(r'^\d+\)\s*', line) or re.match(r'^[①-⑳]\s*', line):
                    optimized_lines.append(line)
                # 부록/별표/첨부 참조가 분리된 경우 병합 (빈 줄 건너뛰기 포함)
                elif should_merge_reference_line_with_lookahead(optimized_lines, line, lines, i):
                    # 특별 처리: 병합과 동시에 다음 인덱스 조정
                    merged_result = merge_reference_with_lookahead(optimized_lines, line, lines, i)
                    if merged_result:
                        # merged_result는 (merged_text, skip_count) 튜플
                        merged_text, skip_count = merged_result
                        optimized_lines[-1] = merged_text
                        i += skip_count
                    else:
                        optimized_lines[-1] += ' ' + line
                        i += 1
                    continue
                # 부록/별표/첨부 참조가 분리된 경우 병합 (기본)
                elif should_merge_reference_line(prev_line, line):
                    # 이전 줄과 현재 줄을 공백으로 연결
                    optimized_lines[-1] += ' ' + line
                else:
                    # 그 외는 공백으로 연결
                    optimized_lines[-1] += ' ' + line
            else:
                optimized_lines.append(line)

        i += 1
    
    return '\n'.join(optimized_lines)

def should_merge_reference_line_with_lookahead(optimized_lines, current_line, all_lines, current_index):
    """
    앞으로 보기(lookahead)를 통해 부록 참조 병합이 필요한지 판단

    Args:
        optimized_lines: 지금까지 처리된 줄들
        current_line: 현재 줄
        all_lines: 전체 줄 배열
        current_index: 현재 인덱스

    Returns:
        bool: 병합이 필요하면 True
    """
    if not optimized_lines or not optimized_lines[-1]:
        return False

    prev_line = optimized_lines[-1].strip()

    # "[부록"으로 끝나는 경우, 다음 몇 줄을 확인
    if prev_line.endswith('[부록'):
        # 현재 줄이 빈 줄이고, 다음 줄에 숫자로 시작하는 참조가 있는지 확인
        if not current_line.strip():
            # 다음 줄들을 확인
            for j in range(current_index + 1, min(current_index + 3, len(all_lines))):
                next_line = all_lines[j].strip()
                if next_line and re.match(r'^\d+\..*\]', next_line):
                    return True

    return False

def merge_reference_with_lookahead(optimized_lines, current_line, all_lines, current_index):
    """
    앞으로 보기를 통해 부록 참조를 병합

    Returns:
        tuple: (merged_text, skip_count) 또는 None
    """
    if not optimized_lines or not optimized_lines[-1]:
        return None

    prev_line = optimized_lines[-1].strip()

    # "[부록"으로 끝나는 경우 처리
    if prev_line.endswith('[부록'):
        # 빈 줄들을 건너뛰면서 참조 부분 찾기
        skip_count = 0
        for j in range(current_index, min(current_index + 3, len(all_lines))):
            line = all_lines[j].strip()
            if not line:
                skip_count += 1
                continue
            elif re.match(r'^\d+\..*\]', line):
                # 병합된 텍스트 생성
                merged_text = prev_line + ' ' + line
                return (merged_text, skip_count + 1)
            else:
                break

    return None

def should_merge_reference_line(prev_line, current_line):
    """
    부록/별표/첨부 등의 참조 표현이 줄바꿈으로 분리된 경우 병합이 필요한지 판단

    Args:
        prev_line: 이전 줄 텍스트
        current_line: 현재 줄 텍스트

    Returns:
        bool: 병합이 필요하면 True
    """
    prev_line = prev_line.strip()
    current_line = current_line.strip()

    # 패턴 1: "[부록" + "6. 응급 회송(전원) 조정 매뉴얼]"
    if (prev_line.endswith('[부록') and
        re.match(r'^\d+\..*\]', current_line)):
        return True

    # 패턴 2: "[별표" + "1. 양식명]"
    if (prev_line.endswith('[별표') and
        re.match(r'^\d+\..*\]', current_line)):
        return True

    # 패턴 3: "[첨부" + "1. 문서명]"
    if (prev_line.endswith('[첨부') and
        re.match(r'^\d+\..*\]', current_line)):
        return True

    # 패턴 4: "부록" + "6."이 분리된 경우 (대괄호 없이)
    if (prev_line.endswith('부록') and
        re.match(r'^\d+\.', current_line)):
        return True

    # 패턴 5: "별표" + "1."이 분리된 경우
    if (prev_line.endswith('별표') and
        re.match(r'^\d+\.', current_line)):
        return True

    # 패턴 6: 닫는 대괄호만 다음 줄에 있는 경우
    if current_line == ']':
        return True

    # 패턴 7: 부록 참조의 일부가 분리된 경우 (더 복잡한 패턴)
    # 예: "에 따라 전입, 전출 관리를 진행한다" + ". 단," 같은 경우는 제외
    if (re.search(r'\[부록\s*$', prev_line) and
        re.match(r'^\d+', current_line)):
        return True

    return False

def get_item_level(line):
    """항목의 레벨(깊이)을 반환 - 수정된 체계"""
    line = line.strip()
    
    # 레벨 체계 (낮은 숫자가 상위 레벨)
    if re.match(r'^제\s*\d+\s*조', line) or re.match(r'^\d+\.\s*\(', line):
        return 1  # 조문
    elif re.match(r'^\d+\.\s+', line):
        return 2  # 항
    elif re.match(r'^\d+\)\s*', line):
        return 3  # 호
    elif re.match(r'^\(\d+\)\s*', line):
        return 4  # 목
    elif re.match(r'^[①-⑳]\s*', line):
        return 5  # 세목
    elif re.match(r'^[a-z]\.\s*', line) or re.match(r'^[가-하]\.\s*', line):
        return 6  # 세목이하1
    elif re.match(r'^[a-z]\)\s*', line) or re.match(r'^[가-하]\)\s*', line):
        return 7  # 세목이하2
    elif re.match(r'^\([a-z]\)\s*', line) or re.match(r'^\([가-하]\)\s*', line):
        return 8  # 세목이하3
    elif re.match(r'^\((참고|목적|정의|절차)\)', line):
        return 1  # 주요 섹션 (부록 제외)
    elif re.match(r'^부록\s*\d+', line) or re.match(r'^\[부록\s*\d+\]', line):
        return 1  # 부록 제목 (번호가 있는 경우)
    elif re.match(r'^별표\s*\d+', line) or re.match(r'^\[별표\s*\d+\]', line):
        return 1  # 별표 제목
    elif re.match(r'^\*\*.*\*\*', line):
        return 1  # 볼드체 제목
    else:
        return 99  # 일반 텍스트

def final_cleanup(text):
    """최종 텍스트 정리"""
    # 페이지 구분자 정리
    text = re.sub(r'---\s*페이지 구분\s*---', '', text)

    # 남은 페이지 정보 제거
    text = re.sub(r'\n\s*\d{1,3}\s*\n', '\n', text)  # 독립된 페이지 번호

    # 최종 테이블 패턴 정리 (페이지 결합 후에 생성될 수 있음)
    text = clean_table_artifacts(text)

    # 부록 참조 분리 문제 최종 수정
    text = fix_split_appendix_references(text)

    # 특수문자 정규화
    text = text.replace('·', '·')  # 중점 통일

    # 최종 공백 정리
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text

def fix_split_appendix_references(text):
    """
    부록 참조가 줄바꿈으로 분리된 경우를 최종적으로 수정

    예: "[부록\n\n6. 응급 회송..." -> "[부록 6. 응급 회송..."
    """
    # 패턴 1: [부록\n\n숫자. 내용] 형태 수정
    text = re.sub(r'\[부록\s*\n\s*(\d+\.)', r'[부록 \1', text)

    # 패턴 2: [별표\n\n숫자. 내용] 형태 수정
    text = re.sub(r'\[별표\s*\n\s*(\d+\.)', r'[별표 \1', text)

    # 패턴 3: [첨부\n\n숫자. 내용] 형태 수정
    text = re.sub(r'\[첨부\s*\n\s*(\d+\.)', r'[첨부 \1', text)

    # 패턴 4: 더 일반적인 패턴 - 여러 줄에 걸쳐 분리된 경우
    text = re.sub(r'\[부록\s*\n+\s*(\d+\.[^\]]*\])', r'[부록 \1', text, flags=re.MULTILINE)
    text = re.sub(r'\[별표\s*\n+\s*(\d+\.[^\]]*\])', r'[별표 \1', text, flags=re.MULTILINE)
    text = re.sub(r'\[첨부\s*\n+\s*(\d+\.[^\]]*\])', r'[첨부 \1', text, flags=re.MULTILINE)

    return text

def main():
    if len(sys.argv) < 2:
        print("사용법:")
        print("  단일 파일: python pdf2txt.py <PDF파일경로> [출력TXT파일경로] [--tables] [--remove-tables]")
        print("  폴더 처리: python pdf2txt.py <PDF폴더경로> <출력폴더경로> [--tables] [--remove-tables]")
        print("  --tables: 테이블 파싱 활성화 (테이블을 텍스트로 변환하여 포함)")
        print("  --remove-tables: 테이블 감지 후 제거 (테이블 영역을 완전히 제외)")
        sys.exit(1)

    input_path = sys.argv[1]

    # 옵션 확인
    parse_tables = '--tables' in sys.argv
    detect_tables_and_remove = '--remove-tables' in sys.argv

    # 입력이 디렉토리인지 파일인지 확인
    if os.path.isdir(input_path):
        # 폴더 처리 모드
        if len(sys.argv) < 3:
            print("폴더 처리 시 출력 폴더 경로가 필요합니다.")
            print("사용법: python pdf2txt.py <PDF폴더경로> <출력폴더경로> [--tables] [--remove-tables]")
            sys.exit(1)

        output_path = sys.argv[2]
        if parse_tables:
            print("테이블 파싱이 활성화되었습니다.")
        if detect_tables_and_remove:
            print("테이블 감지 및 제거가 활성화되었습니다.")
        process_folder(input_path, output_path, parse_tables, detect_tables_and_remove)

    elif os.path.isfile(input_path):
        # 단일 파일 처리 모드
        if not input_path.lower().endswith('.pdf'):
            print("PDF 파일이 아닙니다.")
            sys.exit(1)

        # 출력 파일 경로 결정 (옵션들 제외)
        txt_path = None
        for i, arg in enumerate(sys.argv[2:], 2):
            if arg not in ['--tables', '--remove-tables']:
                txt_path = arg
                break

        if parse_tables:
            print("테이블 파싱이 활성화되었습니다.")
        if detect_tables_and_remove:
            print("테이블 감지 및 제거가 활성화되었습니다.")
        extract_text_from_pdf(input_path, txt_path, parse_tables, detect_tables_and_remove)

    else:
        print(f"경로를 찾을 수 없습니다: {input_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()
