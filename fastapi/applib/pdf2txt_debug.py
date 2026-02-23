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

log_file = os.path.join(log_dir, f'pdf2txt_debug_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('pdf2txt_debug')

def extract_text_from_pdf_debug(pdf_path, txt_path=None):
    """
    PDF 파일에서 텍스트를 추출하여 디버그 정보와 함께 TXT 파일로 저장

    Args:
        pdf_path: 입력 PDF 파일 경로
        txt_path: 출력 TXT 파일 경로 (None일 경우 자동 생성)
    """
    if txt_path is None:
        base_name = os.path.splitext(pdf_path)[0]
        txt_path = f"{base_name}_debug.txt"

    try:
        logger.info(f"PDF 파일 처리 시작: {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            # 여러 버전의 텍스트 저장
            raw_text = ""
            after_page_removal = ""
            after_clean = ""
            final_text = ""

            total_pages = len(pdf.pages)

            print(f"PDF 파일 열기 성공: {pdf_path}")
            print(f"총 페이지 수: {total_pages}")
            logger.info(f"PDF 파일 열기 성공: {pdf_path}, 총 페이지 수: {total_pages}")

            for i, page in enumerate(pdf.pages):
                print(f"페이지 {i+1}/{total_pages} 처리 중...", end='\r')

                # 페이지에서 원본 텍스트 추출
                page_text = page.extract_text()

                if page_text:
                    # 1. 원본 텍스트 저장
                    raw_text += f"\n--- 페이지 {i+1} 원본 ---\n"
                    raw_text += page_text + "\n"

                    # 2. 페이지 정보 제거 후
                    page_text_no_page_info = remove_page_info(page_text)
                    after_page_removal += f"\n--- 페이지 {i+1} (페이지 정보 제거) ---\n"
                    after_page_removal += page_text_no_page_info + "\n"

                    # 3. 텍스트 정리 후
                    page_text_cleaned = clean_text(page_text_no_page_info)
                    after_clean += f"\n--- 페이지 {i+1} (텍스트 정리) ---\n"
                    after_clean += page_text_cleaned + "\n"

                    # 4. 줄바꿈 최적화 후
                    page_text_optimized = optimize_line_breaks_debug(page_text_cleaned)
                    final_text += page_text_optimized + "\n"

                    # 페이지 구분자 추가
                    if i < total_pages - 1:
                        final_text += "\n--- 페이지 구분 ---\n\n"

            # 5. 최종 텍스트 정리
            final_text = final_cleanup(final_text)

            # 디버그 정보와 함께 저장
            debug_output = f"""=== PDF 텍스트 추출 디버그 정보 ===
파일: {pdf_path}
추출일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

=== 1. 원본 텍스트 (pdfplumber 직접 추출) ===
{raw_text}

=== 2. 페이지 정보 제거 후 ===
{after_page_removal}

=== 3. 텍스트 정리 후 ===
{after_clean}

=== 4. 최종 처리 결과 ===
{final_text}
"""

            # TXT 파일로 저장
            with open(txt_path, 'w', encoding='utf-8') as txt_file:
                txt_file.write(debug_output)

            print(f"\n디버그 텍스트 추출 완료: {txt_path}")
            print(f"파일 크기: {os.path.getsize(txt_path):,} bytes")
            logger.info(f"디버그 텍스트 추출 완료: {txt_path}, 파일 크기: {os.path.getsize(txt_path):,} bytes")

            return txt_path

    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        logger.error(f"PDF 처리 오류: {str(e)}", exc_info=True)
        return None

def remove_page_info(text):
    """페이지 정보 제거 - 원본 함수와 동일"""
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

def clean_text(text):
    """텍스트 정리 - 원본 함수와 동일"""
    # 대외비, 머리글/바닥글 제거
    text = re.sub(r'대외비.*?\n', '', text)
    text = re.sub(r'CONFIDENTIAL.*?\n', '', text, flags=re.IGNORECASE)

    # 반복되는 머리글/바닥글 패턴 제거
    header_footer_patterns = [
        r'세브란스병원.*?내규.*?\n',
        r'Severance Hospital.*?\n',
        r'Copyright.*?\n',
        r'©.*?\n',
    ]

    for pattern in header_footer_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # 여러 공백을 하나로
    text = re.sub(r'[ \t]+', ' ', text)

    # 연속된 빈 줄을 하나로
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text

def optimize_line_breaks_debug(text):
    """줄바꿈 최적화 - 디버그 정보 포함"""
    lines = text.split('\n')
    optimized_lines = []
    debug_info = []

    for i, line in enumerate(lines):
        line = line.strip()

        if not line:
            optimized_lines.append('')
            debug_info.append(f"Line {i+1}: [EMPTY LINE]")
            continue

        # 제목이나 번호로 시작하는 경우 새 줄 유지
        title_patterns = [
            # 조문
            r'^제\s*\d+\s*조',              # 제1조
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
            debug_info.append(f"Line {i+1}: [APPENDIX IN MULTI-DOT] {line[:50]}...")
        elif line.strip() == '(부록)' or line.startswith('(부록) '):
            is_new_item = False  # (부록)으로 시작하면 내용으로 처리
            debug_info.append(f"Line {i+1}: [APPENDIX SECTION] {line[:50]}...")
        else:
            is_new_item = any(re.match(pattern, line) for pattern in title_patterns)
            if is_new_item:
                matched_pattern = None
                for pattern in title_patterns:
                    if re.match(pattern, line):
                        matched_pattern = pattern
                        break
                debug_info.append(f"Line {i+1}: [NEW ITEM - {matched_pattern}] {line[:50]}...")

        if is_new_item:
            # 새 항목은 빈 줄 추가 (단, 연속된 하위 항목은 제외)
            if i > 0 and optimized_lines and optimized_lines[-1] != '':
                # 이전 줄과 현재 줄의 레벨 확인
                prev_level = get_item_level(optimized_lines[-1])
                curr_level = get_item_level(line)

                # 같은 레벨이거나 상위 레벨로 올라가는 경우만 빈 줄 추가
                if curr_level <= prev_level:
                    optimized_lines.append('')
                    debug_info.append(f"Line {i+1}: [BLANK LINE ADDED] prev_level={prev_level}, curr_level={curr_level}")

            optimized_lines.append(line)
        else:
            # 일반 텍스트는 이전 줄과 합칠지 결정
            if optimized_lines and optimized_lines[-1] != '':
                prev_line = optimized_lines[-1]

                # 문장이 완료된 경우 새 줄로
                if prev_line.endswith(('.', '다.', '요.', '함.', '임.', '됨.', '한다.')):
                    optimized_lines.append(line)
                    debug_info.append(f"Line {i+1}: [NEW LINE - SENTENCE END] {line[:50]}...")
                # 콜론이나 리스트 시작인 경우 새 줄로
                elif prev_line.endswith(':') or prev_line.endswith('：'):
                    optimized_lines.append(line)
                    debug_info.append(f"Line {i+1}: [NEW LINE - COLON] {line[:50]}...")
                # 표 또는 특수 서식인 경우 새 줄로
                elif '---' in prev_line or '___' in prev_line or '===' in prev_line:
                    optimized_lines.append(line)
                    debug_info.append(f"Line {i+1}: [NEW LINE - TABLE FORMAT] {line[:50]}...")
                # 볼드체로 끝나는 경우 새 줄로
                elif prev_line.endswith('**'):
                    optimized_lines.append(line)
                    debug_info.append(f"Line {i+1}: [NEW LINE - BOLD END] {line[:50]}...")
                else:
                    # 그 외는 공백으로 연결 - 여기가 문제가 될 수 있음!
                    original_prev = optimized_lines[-1]
                    optimized_lines[-1] += ' ' + line
                    debug_info.append(f"Line {i+1}: [MERGED] '{original_prev[:30]}...' + ' ' + '{line[:30]}...' = '{optimized_lines[-1][:60]}...'")
            else:
                optimized_lines.append(line)
                debug_info.append(f"Line {i+1}: [FIRST LINE] {line[:50]}...")

    # 디버그 정보를 텍스트에 포함
    result_with_debug = f"=== 줄바꿈 최적화 디버그 정보 ===\n"
    result_with_debug += "\n".join(debug_info)
    result_with_debug += f"\n\n=== 최적화된 텍스트 ===\n"
    result_with_debug += '\n'.join(optimized_lines)

    return result_with_debug

def get_item_level(line):
    """항목의 레벨(깊이)을 반환 - 원본 함수와 동일"""
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
    """최종 텍스트 정리 - 원본 함수와 동일"""
    # 페이지 구분자 정리
    text = re.sub(r'---\s*페이지 구분\s*---', '', text)

    # 남은 페이지 정보 제거
    text = re.sub(r'\n\s*\d{1,3}\s*\n', '\n', text)  # 독립된 페이지 번호

    # 특수문자 정규화
    text = text.replace('·', '·')  # 중점 통일

    # 최종 공백 정리
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text

def main():
    if len(sys.argv) < 2:
        print("사용법: python pdf2txt_debug.py <PDF파일경로> [출력TXT파일경로]")
        sys.exit(1)

    input_path = sys.argv[1]
    txt_path = sys.argv[2] if len(sys.argv) > 2 else None

    if os.path.isfile(input_path) and input_path.lower().endswith('.pdf'):
        extract_text_from_pdf_debug(input_path, txt_path)
    else:
        print(f"올바른 PDF 파일이 아닙니다: {input_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()