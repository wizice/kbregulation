import json
import re
import sys
import os
import glob
import logging
from datetime import datetime

# 로그 설정
log_dir = os.path.join(os.path.dirname(__file__), 'log')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f'txt2json_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('txt2json')

class MentalHealthRegulationParser:
    def __init__(self):
        self.content = {
            "문서정보": {},
            "조문내용": []
        }
        self.current_seq = 0
    
    def parse_txt_to_json(self, text):
        """TXT 파일 내용을 JSON 형식으로 변환"""
        import time
        start_time = time.time()

        try:
            logger.info("[TXT2JSON] TXT to JSON 변환 시작")
            logger.info(f"[TXT2JSON] Input text size: {len(text)/1024:.1f}KB")

            # 문서 정보 추출
            doc_info_start = time.time()
            self.extract_document_info(text)
            doc_info_elapsed = time.time() - doc_info_start
            logger.info(f"[TXT2JSON] Document info extracted in {doc_info_elapsed:.2f}s")

            # 본문 추출 (제1조부터)
            articles_start = time.time()
            main_text_match = re.search(r'(제1조.*)', text, re.DOTALL)
            if main_text_match:
                main_text = main_text_match.group(1)
                logger.info(f"[TXT2JSON] Main text found, size: {len(main_text)/1024:.1f}KB")
                self.parse_articles(main_text)
            articles_elapsed = time.time() - articles_start
            logger.info(f"[TXT2JSON] Articles parsed in {articles_elapsed:.2f}s")

            # 조문 개수 설정
            self.content["문서정보"]["조문갯수"] = len(self.content["조문내용"])

            total_elapsed = time.time() - start_time
            logger.info(f"[TXT2JSON] JSON 변환 완료: 조문 개수 {self.content['문서정보']['조문갯수']}개")
            logger.info(f"[TXT2JSON] Total conversion time: {total_elapsed:.2f}s")

            if total_elapsed > 10:
                logger.warning(f"[BOTTLENECK] TXT to JSON conversion took {total_elapsed:.2f}s (>10s threshold)")

            return self.content
        except Exception as e:
            logger.error(f"JSON 변환 오류: {str(e)}", exc_info=True)
            raise
    
    def extract_document_info(self, text):
        """문서 정보 추출"""
        # 제목/규정명 추출 (첫 번째 주요 제목을 찾음)
        title_match = re.search(r'^[\d.]+\s+(.+?)(?:\n|$)', text, re.MULTILINE)
        if title_match:
            self.content["문서정보"]["규정명"] = title_match.group(1).strip()
            self.content["문서정보"]["규정표기명"] = title_match.group(0).strip()
        else:
            # 기본값
            self.content["문서정보"]["규정명"] = "미지정 규정"
            self.content["문서정보"]["규정표기명"] = "미지정 규정"
        
        self.content["문서정보"]["내규종류"] = "규정"
        
        # 날짜 정보 추출
        date_patterns = {
            "제정일": r'제\s*정\s*일\s*[:：]\s*(\d{4}\.\d{2}\.)',
            "최종개정일": r'최\s*종\s*개\s*정\s*일\s*[:：]\s*(\d{4}\.\d{2}\.\d{2}\.)',
            "최종검토일": r'최\s*종\s*검\s*토\s*일\s*[:：]\s*(\d{4}\.\d{2}\.\d{2}\.)'
        }
        
        for key, pattern in date_patterns.items():
            match = re.search(pattern, text[:1000])  # 문서 앞부분에서만 검색
            if match:
                self.content["문서정보"][key] = match.group(1)
        
        # 담당부서 추출
        dept_match = re.search(r'담\s*당\s*부\s*서\s*[:：]?\s*([^\n]+?)(?:\s+유\s*관\s*부\s*서|$)', text)
        if dept_match:
            dept = dept_match.group(1).strip()
            dept = re.sub(r'\s+', ' ', dept)
            self.content["문서정보"]["담당부서"] = dept
        
        # 관련기준 추출
        criteria = []
        if '4주기 정신의료기관평가기준' in text:
            criteria_match = re.search(r'4주기 정신의료기관평가기준[:：]\s*([^\n]+)', text)
            if criteria_match:
                criteria.append(f"4주기 정신의료기관평가기준: {criteria_match.group(1).strip()}")
        
        if 'JCI Standard' in text:
            jci_match = re.search(r'JCI Standard[^:：]*[:：]\s*([^\n]+)', text)
            if jci_match:
                criteria.append(f"JCI Standard 7th Edition: {jci_match.group(1).strip()}")
        
        self.content["문서정보"]["관련기준"] = criteria
        self.content["문서정보"]["이미지개수"] = 1
    
    def parse_articles(self, text):
        """조문 내용 파싱"""
        import time
        parse_start = time.time()

        # 제목 추가 (문서정보에서 가져오기)
        title = self.content["문서정보"].get("규정표기명", "")
        if title:
            self.add_article_item(0, title, "")

        # 텍스트를 줄 단위로 분리
        lines = text.split('\n')
        logger.info(f"[TXT2JSON] Parsing {len(lines)} lines")

        i = 0
        articles_count = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # 메타데이터 제외 (페이지 헤더, 바닥글 등)
            if self.is_metadata_line(line):
                i += 1
                continue

            # 다음 줄과 병합이 필요한지 확인
            merged_line = line
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue

                # 메타데이터 라인이면 스킵
                if self.is_metadata_line(next_line):
                    j += 1
                    continue

                # 병합이 필요한지 확인
                if self.should_merge_with_next_line(merged_line, next_line):
                    merged_line = merged_line + next_line
                    j += 1
                    # i를 j로 업데이트 (병합된 줄들을 건너뛰기 위해)
                    i = j - 1
                else:
                    break

            # 번호가 붙은 목록 자동 분리 처리
            if self.contains_numbered_list(merged_line):
                split_items = self.split_numbered_list(merged_line)
                for item_level, item_number, item_content in split_items:
                    self.add_article_item(item_level, item_content, item_number)
                i += 1
                continue

            # 각 패턴별로 처리
            level, number, content = self.get_line_info(merged_line)

            if level == "split_reference":
                # "제5조 (참고) 내규의 제·개정 이력" 분리 처리
                # 1. "(참고)" 항목 추가
                self.add_article_item(1, content, number)
                # 2. "내규의 제·개정 이력" 항목 추가
                self.add_article_item(1, "내규의 제·개정 이력", "")
                i += 1
            elif level == "split_reference_content":
                # "숫자. 내용 내규의 제·개정 이력" 분리 처리
                # 1. 참고 내용 항목 추가
                self.add_article_item(2, content, number)
                # 2. "내규의 제·개정 이력" 항목 추가
                self.add_article_item(1, "내규의 제·개정 이력", "")
                i += 1
            elif level == "split_reference_content_with_doc":
                # "숫자. 내용 내규의 제·개정 이력 [문서식별자]" 분리 처리
                # 1. 참고 내용 항목 추가
                self.add_article_item(2, content, number)
                # 2. "내규의 제·개정 이력" 항목 추가
                self.add_article_item(1, "내규의 제·개정 이력", "")
                i += 1
            elif level > 0:
                # 내용이 비어있지 않은 경우만 추가
                if content or number:  # 번호만 있는 경우도 처리
                    self.add_article_item(level, content, number)

                i += 1
            else:
                i += 1
    
    def should_merge_with_next_line(self, line, next_line):
        """현재 줄이 다음 줄과 병합되어야 하는지 확인"""
        if not line or not next_line:
            return False

        # 현재 줄이 불완전한 문장인지 확인하는 패턴들
        incomplete_patterns = [
            r'.*\(\s*\d+\s*-\s*$',  # "예약센터( 1599-" 같은 패턴
            r'.*\(\s*$',            # 열린 괄호로 끝나는 경우
            r'.*[,，]\s*$',         # 쉼표로 끝나는 경우
            r'.*\s+$',              # 공백으로 끝나는 경우 (단, 문장이 완성되지 않은 경우)
        ]

        # 다음 줄이 연속 내용임을 나타내는 패턴들
        continuation_patterns = [
            r'^\d+\)',               # "1004)로 시작하는 경우
            r'^[가-힣]',            # 한글로 시작하는 경우 (번호 없이)
            r'^[a-zA-Z]',           # 영어로 시작하는 경우 (번호 없이)
            r'^\)',                 # 닫힌 괄호로 시작하는 경우
        ]

        # 다음 줄이 새로운 항목임을 나타내는 패턴들 (병합하면 안됨)
        new_item_patterns = [
            r'^\d+\.\s',            # "2. " 같은 새로운 항목
            r'^\d+\)\s',            # "3) " 같은 새로운 항목 (중요!)
            r'^제\d+조',            # "제1조" 같은 새로운 조문
            r'^\([가-힣]+\)',       # "(목적)" 같은 새로운 섹션
            r'^\(\d+\)\s',          # "(1) " 같은 번호 항목
            r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟]', # 원형 번호 (확장)
            r'^\([가-힣]\)',        # "(가)" 같은 번호
            r'^[ⅰⅱⅲⅳⅴ]\)',       # 로마 숫자
            r'^[a-z]\.\s',          # "a. " 같은 하위 항목
            r'^[a-z]\)',            # "a)" 같은 하위 항목
            r'^\([a-z]\)',          # "(a)" 같은 하위 항목
        ]

        # 다음 줄이 새로운 항목인 경우 병합하지 않음
        for pattern in new_item_patterns:
            if re.match(pattern, next_line.strip()):
                return False

        # 현재 줄이 불완전하고 다음 줄이 연속 내용인 경우
        for incomplete_pattern in incomplete_patterns:
            if re.match(incomplete_pattern, line):
                # 다음 줄이 새로운 항목인지 다시 한 번 확인 (우선 순위)
                for new_pattern in new_item_patterns:
                    if re.match(new_pattern, next_line.strip()):
                        return False  # 새로운 항목이면 병합하지 않음

                # 연속 내용인지 확인
                for continuation_pattern in continuation_patterns:
                    if re.match(continuation_pattern, next_line.strip()):
                        return True

        return False

    def contains_numbered_list(self, line):
        """줄에 번호가 붙은 목록이 포함되어 있는지 확인"""
        # 패턴 1: X-Y. 형태가 2개 이상 포함된 경우
        numbered_list_pattern = r'\d+-\d+\.\s+'
        matches = re.findall(numbered_list_pattern, line)
        if len(matches) >= 2:
            return True

        # 패턴 2: 원형숫자가 2개 이상 포함된 경우
        circle_pattern = r'[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟]\s+'
        circle_matches = re.findall(circle_pattern, line)
        return len(circle_matches) >= 2  # 2개 이상의 원형숫자가 있으면 분리 대상

    def split_numbered_list(self, line):
        """번호가 붙은 목록을 개별 항목으로 분리 - 범용적 버전"""
        items = []

        # 패턴 1: "번호. 메인제목 X-Y. 하위항목1 X-Z. 하위항목2..."
        # 예: "1. 세브란스병원 주의를 요하는 의약품 목록 1-1. 냉장보관이..."
        main_with_sub_match = re.match(r'^(\d+\.)\s+([^0-9]+?)\s+(\d+-\d+\.\s+.+)$', line)

        if main_with_sub_match:
            main_number = main_with_sub_match.group(1)
            main_content = main_with_sub_match.group(2).strip()
            sub_content = main_with_sub_match.group(3)

            # 메인 항목 추가
            items.append((2, main_number, main_content))

            # 하위 목록들 분리
            self._extract_numbered_subitems(sub_content, items, 3)

        else:
            # 패턴 2: 메인 제목 없이 바로 번호 목록들
            # 예: "조제지침 1-1. 소아 조제지침 1-2. 산제 조제지침..."
            direct_list_match = re.match(r'^([^0-9]*?)\s*(\d+-\d+\.\s+.+)$', line)

            if direct_list_match:
                prefix = direct_list_match.group(1).strip()
                sub_content = direct_list_match.group(2)

                # 접두어가 있으면 메인 항목으로 추가
                if prefix:
                    items.append((2, "", prefix))

                # 하위 목록들 분리
                self._extract_numbered_subitems(sub_content, items, 3)
            else:
                # 패턴 3: 원형숫자가 포함된 경우 분리
                circle_pattern = r'([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟])\s+'
                circle_matches = re.findall(circle_pattern, line)

                if len(circle_matches) >= 2:
                    # 원형숫자로 텍스트 분리
                    self._extract_circle_number_items(line, items)

        return items if items else [(0, "", line)]

    def _extract_numbered_subitems(self, content, items, level):
        """번호가 붙은 하위 항목들을 추출"""
        # X-Y. 패턴으로 분리 (더 유연한 패턴)
        sub_pattern = r'(\d+-\d+)\.\s+([^0-9]*?)(?=\s*\d+-\d+\.|$)'
        sub_matches = re.findall(sub_pattern, content)

        for sub_number, sub_desc in sub_matches:
            clean_desc = sub_desc.strip().rstrip(',').rstrip()
            if clean_desc:  # 빈 내용이 아닐 때만 추가
                items.append((level, f"{sub_number}.", clean_desc))

    def _extract_circle_number_items(self, line, items):
        """원형숫자가 포함된 텍스트를 분리"""
        # 원형숫자 패턴으로 텍스트 분할
        circle_pattern = r'([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟])\s*'

        # 첫 번째 원형숫자 앞의 내용이 있으면 처리
        parts = re.split(circle_pattern, line)

        # parts[0]는 첫 번째 원형숫자 앞의 내용
        if parts[0].strip():
            # 기존 번호 패턴으로 레벨 판단
            prefix_level, prefix_number, prefix_content = self.get_line_info(parts[0].strip())
            if prefix_level > 0:
                items.append((prefix_level, prefix_number, prefix_content))
            else:
                items.append((5, "⑳", parts[0].strip()))  # 기본적으로 레벨 5로 설정

        # 원형숫자와 내용 쌍으로 처리
        for i in range(1, len(parts), 2):
            if i < len(parts) - 1:  # 원형숫자와 내용이 쌍으로 있는 경우
                circle_num = parts[i]
                content = parts[i + 1].strip().rstrip(',').rstrip()
                if content:
                    items.append((5, circle_num, content))

    def is_metadata_line(self, line):
        """메타데이터 라인인지 확인 (본문이 아닌 내용)"""
        metadata_patterns = [
            r'^2\.1\.2\.2\.\s*정신건강의학과.*입원환자\s*관리$',  # 페이지 헤더
            r'^페이지\s*\d+\s*/\s*\d+',  # 페이지 정보
            r'^\d{4}\.\d{2}\.\d{2}\.',  # 날짜만 있는 라인
            r'^승\s*인[:：]',  # 승인 정보
            r'^\(인\)$',  # (인)
            r'^대외비$',  # 대외비
            r'^-+\s*페이지\s*구분\s*-+$',  # 페이지 구분선
        ]
        
        for pattern in metadata_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def get_line_info(self, line):
        """라인의 레벨, 번호, 내용 반환 - 번호는 내용에서 제외"""
        # 개정 이력 특수 패턴들
        if line == "(참고)":
            return 1, "제5조", line

        if line == "내규의 제·개정 이력":
            return 1, "", line

        # "내규의 제·개정 이력 [문서식별자]" 패턴 처리
        match = re.match(r'^내규의 제·개정 이력\s+(.+)$', line)
        if match:
            # "내규의 제·개정 이력"만 추출하고 문서식별자는 무시
            return 1, "", "내규의 제·개정 이력"

        # "숫자. [텍스트] 내규의 제·개정 이력 [문서식별자]" 패턴 처리
        match = re.match(r'^(\d+\.)\s+(.+?)\s+내규의 제·개정 이력\s+(.+)$', line)
        if match:
            # 참고 내용과 "내규의 제·개정 이력"을 분리 처리
            return "split_reference_content_with_doc", match.group(1), match.group(2).strip()

        # "제5조 (참고) 내규의 제·개정 이력" 패턴을 분리 처리
        if re.match(r'^제\d+조\s*\(참고\)\s*내규의 제·개정 이력', line):
            # 먼저 "(참고)" 항목을 추가하고 특별한 처리를 위한 플래그 반환
            return "split_reference", "제5조", "(참고)"

        # "숫자. 내용 내규의 제·개정 이력" 패턴 (참고 내용 마지막에 붙은 경우)
        match = re.match(r'^(\d+\.)\s+(.+?)\s+내규의 제·개정 이력$', line)
        if match:
            # 참고 내용과 "내규의 제·개정 이력"을 분리 처리
            return "split_reference_content", match.group(1), match.group(2).strip()

        # "제1조 (내규의 제정 및 시행)" 패턴
        if re.match(r'^제1조\s*\(내규의 제정 및 시행\)', line):
            return 2, "제 1조", "(내규의 제정 및 시행)"

        # "제2조 (내규의 전면개정 및 시행)" 패턴
        if re.match(r'^제2조\s*\(내규의 전면개정 및 시행\)', line):
            return 2, "제 2조", "(내규의 전면개정 및 시행)"

        # "제3조 (내규의 개정)" 패턴
        if re.match(r'^제3조\s*\(내규의 개정\)', line):
            return 2, "제 3조", "(내규의 개정)"

        if line == "(내규의 제정 및 시행)":
            return 2, "제 1조", line

        if line == "(내규의 전면개정 및 시행)":
            return 2, "제 2조", line

        if line == "(내규의 개정)":
            return 2, "제 3조", line

        # "이 내규는...시행한다" 형식
        if line.startswith("이 내규는") and "시행한다" in line:
            return 3, "1.", line

        # "1. 이 내규는..." 형식
        if re.match(r'^1\.\s*이 내규는.*시행한다', line):
            return 3, "1.", line

        # 제X조 (목적 등)
        match = re.match(r'^(제\s*\d+\s*조)\s*\(([^)]+)\)(.*)$', line)
        if match:
            content = f"({match.group(2)}){match.group(3)}".strip()
            return 1, match.group(1), content

        # 제X조
        match = re.match(r'^(제\s*\d+\s*조)(.*)$', line)
        if match:
            content = match.group(2).strip()
            return 1, match.group(1), content

        # 1. 형식
        match = re.match(r'^(\d+\.)\s+(.*)$', line)
        if match:
            return 2, match.group(1), match.group(2).strip()

        # 1) 형식
        match = re.match(r'^(\d+\))\s*(.*)$', line)
        if match and not re.match(r'^\(\d+\)', line):
            return 3, match.group(1), match.group(2).strip()

        # (1) 형식
        match = re.match(r'^(\(\d+\))\s*(.*)$', line)
        if match:
            return 4, match.group(1), match.group(2).strip()

        # ① 형식 (확장: ①-㉟까지 지원)
        match = re.match(r'^([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟])\s*(.*)$', line)
        if match:
            return 5, match.group(1), match.group(2).strip()

        # (가) 형식
        match = re.match(r'^(\([가-하]\))\s*(.*)$', line)
        if match:
            return 4, match.group(1), match.group(2).strip()

        # a. 형식
        match = re.match(r'^([a-z]\.)\s*(.*)$', line)
        if match:
            return 6, match.group(1), match.group(2).strip()

        # a) 형식 (레벨 7)
        match = re.match(r'^([a-z]\))\s*(.*)$', line)
        if match:
            return 7, match.group(1), match.group(2).strip()

        # (a) 형식 (레벨 8)
        match = re.match(r'^(\([a-z]\))\s*(.*)$', line)
        if match:
            return 8, match.group(1), match.group(2).strip()

        # [부록X 형식
        match = re.match(r'^(\[부록\s*\d+[^\]]*\])\s*(.*)$', line)
        if match:
            return 2, match.group(1), match.group(2).strip()

        # (부록) 또는 (참고) - 특수 패턴 이외의 경우
        match = re.match(r'^(\(부록\)|\(참고\))\s*(.*)$', line)
        if match and line != "(참고)":
            return 1, match.group(1), match.group(2).strip()

        return 0, "", line
    
    def add_article_item(self, level, content, number):
        """조문 항목 추가"""
        self.current_seq += 1
        
        item = {
            "seq": self.current_seq,
            "레벨": level,
            "내용": str(content),
            "번호": str(number),
            "관련이미지": []
        }
        self.content["조문내용"].append(item)

def convert_txt_to_json(txt_content, output_file=None):
    """TXT 내용을 JSON으로 변환하는 메인 함수"""
    parser = MentalHealthRegulationParser()
    result = parser.parse_txt_to_json(txt_content)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"JSON 파일 생성 완료: {output_file}")
    
    return result

def process_folder(input_path, output_path):
    """폴더 내의 모든 TXT 파일을 처리"""
    # 출력 폴더가 없으면 생성
    os.makedirs(output_path, exist_ok=True)
    
    # TXT 파일 목록 가져오기
    txt_files = glob.glob(os.path.join(input_path, "*.txt"))
    
    if not txt_files:
        print(f"경로에 TXT 파일이 없습니다: {input_path}")
        return
    
    print(f"총 {len(txt_files)}개의 TXT 파일을 찾았습니다.")
    print("-" * 50)
    
    success_count = 0
    fail_count = 0
    
    for idx, txt_path in enumerate(txt_files, 1):
        # 파일명만 추출 (확장자 제외)
        filename = os.path.basename(txt_path)
        filename_without_ext = os.path.splitext(filename)[0]
        
        # 출력 파일 경로 생성
        json_path = os.path.join(output_path, f"{filename_without_ext}.json")
        
        print(f"\n[{idx}/{len(txt_files)}] 처리 중: {filename}")
        logger.info(f"파일 처리 중 [{idx}/{len(txt_files)}]: {filename}")

        try:
            # TXT 파일 읽기
            with open(txt_path, 'r', encoding='utf-8') as f:
                txt_content = f.read()

            # JSON 변환
            result = convert_txt_to_json(txt_content, json_path)

            # 결과 미리보기
            print(f"  - 조문 개수: {result['문서정보'].get('조문갯수', 0)}")
            logger.info(f"파일 처리 성공: {filename}, 조문 개수: {result['문서정보'].get('조문갯수', 0)}")
            success_count += 1

        except Exception as e:
            print(f"  - 오류 발생: {str(e)}")
            logger.error(f"파일 처리 실패: {filename}, 오류: {str(e)}")
            fail_count += 1
        
        print("-" * 50)
    
    # 최종 결과 출력
    print(f"\n변환 완료!")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"출력 경로: {output_path}")

# 사용 예시
if __name__ == "__main__":
    # 파일에서 읽기
    if len(sys.argv) < 2:
        print("사용법:")
        print("  단일 파일: python txt2json.py <TXT파일경로> [출력JSON파일경로]")
        print("  폴더 처리: python txt2json.py <TXT폴더경로> <출력폴더경로>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    # 입력이 디렉토리인지 파일인지 확인
    if os.path.isdir(input_path):
        # 폴더 처리 모드
        if len(sys.argv) < 3:
            print("폴더 처리 시 출력 폴더 경로가 필요합니다.")
            print("사용법: python txt2json.py <TXT폴더경로> <출력폴더경로>")
            sys.exit(1)
        
        output_path = sys.argv[2]
        process_folder(input_path, output_path)
        
    elif os.path.isfile(input_path):
        # 단일 파일 처리 모드
        if not input_path.lower().endswith('.txt'):
            print("TXT 파일이 아닙니다.")
            sys.exit(1)
        
        with open(input_path, 'r', encoding='utf-8') as f:
            txt_content = f.read()
        
        # 입력 파일명과 동일한 이름으로 .json 확장자 사용
        base_name = os.path.splitext(input_path)[0]
        output_file = sys.argv[2] if len(sys.argv) > 2 else f"{base_name}.json"
        
        result = convert_txt_to_json(txt_content, output_file)
        
        # 결과 미리보기 (첫 5개 항목만)
        print("\n[변환 결과 미리보기]")
        print(f"문서정보: {result['문서정보']}")
        print(f"\n조문내용 (첫 5개):")
        for item in result['조문내용'][:5]:
            print(f"  seq {item['seq']}: 레벨{item['레벨']} - {item['번호']} {item['내용'][:50]}...")
            
    else:
        print(f"경로를 찾을 수 없습니다: {input_path}")
        sys.exit(1)
