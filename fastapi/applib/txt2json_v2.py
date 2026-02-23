"""
범용 규정 파서 v2 - 여비규정, 인사규정 등 회사 규정 문서 지원
기존 병원 내규도 호환 가능
"""
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

log_file = os.path.join(log_dir, f'txt2json_v2_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('txt2json_v2')


class UniversalRegulationParser:
    """범용 규정 파서 - 법규, 병원 내규, 회사 규정 등 지원"""

    def __init__(self):
        self.content = {
            "문서정보": {},
            "조문내용": []
        }
        self.current_seq = 0
        self.last_level_type = None  # 마지막 항목의 타입 추적 (article, item1, item2 등)

    def parse_txt_to_json(self, text):
        """TXT 파일 내용을 JSON 형식으로 변환"""
        import time
        start_time = time.time()

        try:
            logger.info("[TXT2JSON-V2] TXT to JSON 변환 시작")
            logger.info(f"[TXT2JSON-V2] Input text size: {len(text)/1024:.1f}KB")

            # 문서 정보 추출
            doc_info_start = time.time()
            self.extract_document_info(text)
            doc_info_elapsed = time.time() - doc_info_start
            logger.info(f"[TXT2JSON-V2] Document info extracted in {doc_info_elapsed:.2f}s")
            logger.info(f"[TXT2JSON-V2] 규정명: {self.content['문서정보'].get('규정명', 'N/A')}")

            # 본문 추출 (제1장 우선, 없으면 제1조부터)
            articles_start = time.time()
            # 제1장이 있으면 제1장부터 시작
            main_text_match = re.search(r'(제1장.*)', text, re.DOTALL)
            if not main_text_match:
                # 제1장이 없으면 제1조부터 시작
                main_text_match = re.search(r'(제1조.*)', text, re.DOTALL)

            if main_text_match:
                main_text = main_text_match.group(1)
                logger.info(f"[TXT2JSON-V2] Main text found, size: {len(main_text)/1024:.1f}KB")
                self.parse_articles(main_text)
            else:
                # 제1조/제1장이 없으면 전체 텍스트 파싱
                logger.warning("[TXT2JSON-V2] No '제1조' or '제1장' found, parsing full text")
                self.parse_articles(text)

            articles_elapsed = time.time() - articles_start
            logger.info(f"[TXT2JSON-V2] Articles parsed in {articles_elapsed:.2f}s")

            # 조문 개수 설정
            self.content["문서정보"]["조문갯수"] = len(self.content["조문내용"])

            total_elapsed = time.time() - start_time
            logger.info(f"[TXT2JSON-V2] JSON 변환 완료: 조문 개수 {self.content['문서정보']['조문갯수']}개")
            logger.info(f"[TXT2JSON-V2] Total conversion time: {total_elapsed:.2f}s")

            if total_elapsed > 10:
                logger.warning(f"[BOTTLENECK] TXT to JSON conversion took {total_elapsed:.2f}s (>10s threshold)")

            return self.content
        except Exception as e:
            logger.error(f"JSON 변환 오류: {str(e)}", exc_info=True)
            raise

    def extract_document_info(self, text):
        """문서 정보 추출 - 개선된 버전"""
        # 1. 규정명 추출 (첫 줄에서 우선 추출)
        first_line = text.split('\n')[0] if text else ""

        # "XX규정" 패턴 추출
        title_match = re.search(r'([가-힣]+규정)', first_line)
        if title_match:
            self.content["문서정보"]["규정명"] = title_match.group(1)
            self.content["문서정보"]["규정표기명"] = title_match.group(1)
            logger.info(f"[규정명 추출] {title_match.group(1)}")
        else:
            # 기존 방식 (병원 내규용)
            title_match = re.search(r'^[\d.]+\s+(.+?)(?:\n|$)', text, re.MULTILINE)
            if title_match:
                self.content["문서정보"]["규정명"] = title_match.group(1).strip()
                self.content["문서정보"]["규정표기명"] = title_match.group(0).strip()
            else:
                self.content["문서정보"]["규정명"] = "미지정 규정"
                self.content["문서정보"]["규정표기명"] = "미지정 규정"

        self.content["문서정보"]["내규종류"] = "규정"

        # 2. 소관부서 추출 (회사 규정용)
        dept_match = re.search(r'소관부서\s*[:：]\s*([^\)]+)', text[:500])
        if dept_match:
            dept = dept_match.group(1).strip()
            self.content["문서정보"]["담당부서"] = dept
            logger.info(f"[소관부서 추출] {dept}")
        else:
            # 기존 방식 (병원 내규용)
            dept_match = re.search(r'담\s*당\s*부\s*서\s*[:：]?\s*([^\n]+?)(?:\s+유\s*관\s*부\s*서|$)', text)
            if dept_match:
                dept = dept_match.group(1).strip()
                dept = re.sub(r'\s+', ' ', dept)
                self.content["문서정보"]["담당부서"] = dept

        # 3. 날짜 정보 추출
        # 제정일
        enact_match = re.search(r'제\s*정\s*일?\s*[:：]?\s*[:：]?\s*(\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?)', text[:1000])
        if enact_match:
            self.content["문서정보"]["제정일"] = enact_match.group(1).strip()
        else:
            # (YYYY. MM. DD. 제정) 패턴
            enact_match = re.search(r'\((\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.)\s*제정\)', text[:1000])
            if enact_match:
                self.content["문서정보"]["제정일"] = enact_match.group(1).strip()

        # 최종개정일 - 여러 개정일 중 최신 것 추출
        # 공백이 여러 개 있을 수 있으므로 \s*로 매칭
        revision_dates = re.findall(r'\((\d{4}\.\s*\d+\s*\.\s*\d+\.?)\s*개정\)', text[:2000])
        if revision_dates:
            # 마지막(최신) 개정일 선택하고 공백 정규화
            latest = revision_dates[-1].strip()
            latest = re.sub(r'\s+', ' ', latest)  # 여러 공백을 하나로
            latest = re.sub(r'\s*\.\s*', '.', latest)  # ". " → "."
            self.content["문서정보"]["최종개정일"] = latest
            logger.info(f"[최종개정일 추출] {latest} (총 {len(revision_dates)}개 개정 이력)")
        else:
            # 기존 방식
            revision_match = re.search(r'최\s*종\s*개\s*정\s*일\s*[:：]\s*(\d{4}\.\d{2}\.\d{2}\.)', text[:1000])
            if revision_match:
                self.content["문서정보"]["최종개정일"] = revision_match.group(1)

        # 최종검토일
        review_match = re.search(r'최\s*종\s*검\s*토\s*일\s*[:：]\s*(\d{4}\.\d{2}\.\d{2}\.)', text[:1000])
        if review_match:
            self.content["문서정보"]["최종검토일"] = review_match.group(1)

        # 4. 관련기준 추출 (병원 내규용)
        criteria = []
        if '4주기 정신의료기관평가기준' in text or '4주기 의료기관인증기준' in text:
            criteria_match = re.search(r'4주기 [정신]*의료기관[인증평가]*기준[:：]\s*([^\n]+)', text)
            if criteria_match:
                criteria.append(criteria_match.group(0).strip())

        if 'JCI Standard' in text:
            jci_match = re.search(r'JCI Standard[^:：]*[:：]\s*([^\n]+)', text)
            if jci_match:
                criteria.append(jci_match.group(0).strip())

        self.content["문서정보"]["관련기준"] = criteria
        self.content["문서정보"]["이미지개수"] = 0

    def _preprocess_text(self, text):
        """텍스트 전처리 - 장/절 분리 등"""
        # "제X장 내용 제X절 내용" → "제X장 내용\n제X절 내용"
        text = re.sub(r'(제\s*\d+\s*장\s+[^\n]+?)\s+(제\s*\d+\s*절)', r'\1\n\2', text)

        return text

    def parse_articles(self, text):
        """조문 내용 파싱 - 개선된 버전"""
        import time
        parse_start = time.time()

        # 제목 추가
        title = self.content["문서정보"].get("규정표기명", "")
        if title and title != "미지정 규정":
            self.add_article_item(0, title, "")

        # 전처리: 장/절이 한 줄에 있으면 분리
        text = self._preprocess_text(text)

        # 텍스트를 줄 단위로 분리
        lines = text.split('\n')
        logger.info(f"[TXT2JSON-V2] Parsing {len(lines)} lines")

        i = 0
        while i < len(lines):
            # 앞뒤 공백 제거 (들여쓰기 무시)
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # 메타데이터 제외
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

                if self.is_metadata_line(next_line):
                    j += 1
                    continue

                if self.should_merge_with_next_line(merged_line, next_line):
                    merged_line = merged_line + next_line
                    j += 1
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

            # 특수 처리 케이스들
            if level == "split_reference":
                self.add_article_item(1, content, number)
                self.add_article_item(1, "내규의 제·개정 이력", "")
                i += 1
            elif level == "split_reference_content":
                self.add_article_item(2, content, number)
                self.add_article_item(1, "내규의 제·개정 이력", "")
                i += 1
            elif level == "split_reference_content_with_doc":
                self.add_article_item(2, content, number)
                self.add_article_item(1, "내규의 제·개정 이력", "")
                i += 1
            elif level > 0:
                if content or number:
                    self.add_article_item(level, content, number)
                i += 1
            else:
                i += 1

    def get_line_info(self, line):
        """라인의 레벨, 번호, 내용 반환 - 개선된 버전"""

        # === 장/절 구조 인식 (회사 규정용) ===
        # 주의: "제2장 국내여비 제1절 출장여비"처럼 장과 절이 한 줄에 있을 수 있음

        # 제X장과 제X절이 한 줄에 있는 경우 (예: "제2장 국내여비 제1절 출장여비")
        # 이 경우 제X장만 반환하고, 다음 파싱에서 제X절을 처리
        match = re.match(r'^.*?(제\s*\d+\s*장)\s+(.+?)\s+(제\s*\d+\s*절.*)$', line)
        if match:
            # 제X장만 먼저 처리
            self.last_level_type = 'chapter'
            return 0, match.group(1), match.group(2).strip()

        # 제X장 (레벨 0)
        match = re.match(r'^.*?(제\s*\d+\s*장)\s+(.*)$', line)
        if match:
            self.last_level_type = 'chapter'
            return 0, match.group(1), match.group(2).strip()

        # 제X절 (레벨 1)
        match = re.match(r'^.*?(제\s*\d+\s*절)\s+(.*)$', line)
        if match:
            self.last_level_type = 'section'
            return 1, match.group(1), match.group(2).strip()

        # === 개정 이력 특수 패턴들 ===

        if line == "(참고)":
            self.last_level_type = 'article'
            return 1, "제5조", line

        if line == "내규의 제·개정 이력":
            self.last_level_type = 'history'
            return 1, "", line

        match = re.match(r'^내규의 제·개정 이력\s+(.+)$', line)
        if match:
            self.last_level_type = 'history'
            return 1, "", "내규의 제·개정 이력"

        match = re.match(r'^(\d+\.)\s+(.+?)\s+내규의 제·개정 이력\s+(.+)$', line)
        if match:
            return "split_reference_content_with_doc", match.group(1), match.group(2).strip()

        if re.match(r'^제\d+조\s*\(참고\)\s*내규의 제·개정 이력', line):
            return "split_reference", "제5조", "(참고)"

        match = re.match(r'^(\d+\.)\s+(.+?)\s+내규의 제·개정 이력$', line)
        if match:
            return "split_reference_content", match.group(1), match.group(2).strip()

        # === 제X조 패턴 ===

        # 제X조 (제목) 형식
        match = re.match(r'^(제\s*\d+\s*조)\s*\(([^)]+)\)(.*)$', line)
        if match:
            self.last_level_type = 'article'
            content = f"({match.group(2)}){match.group(3)}".strip()
            # 장/절이 있으면 제X조는 레벨2, 없으면 레벨1
            level = 2 if self._has_chapter_or_section() else 1
            return level, match.group(1), content

        # 제X조만 있는 형식
        match = re.match(r'^(제\s*\d+\s*조)(.*)$', line)
        if match:
            self.last_level_type = 'article'
            content = match.group(2).strip()
            level = 2 if self._has_chapter_or_section() else 1
            return level, match.group(1), content

        # === 번호 매기기 패턴 ===

        # 1. 형식
        match = re.match(r'^(\d+\.)\s+(.*)$', line)
        if match:
            self.last_level_type = 'item1'
            return 2, match.group(1), match.group(2).strip()

        # 1) 형식
        match = re.match(r'^(\d+\))\s*(.*)$', line)
        if match and not re.match(r'^\(\d+\)', line):
            self.last_level_type = 'item2'
            return 3, match.group(1), match.group(2).strip()

        # (1) 형식
        match = re.match(r'^(\(\d+\))\s*(.*)$', line)
        if match:
            self.last_level_type = 'paren'
            return 4, match.group(1), match.group(2).strip()

        # === ①, ② 원형 번호 - 동적 레벨 할당 ===
        match = re.match(r'^([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟ⓛ])\s*(.*)$', line)
        if match:
            # 마지막 항목이 '제X조'면 레벨2 (조문의 항)
            # 마지막 항목이 '제X조 바로 다음 원형 번호'면 레벨2 (조문의 항 계속)
            # 마지막 항목이 '1)' 등이면 레벨5 (하위 세부 항목)
            if self._last_item_was_article() or self._last_item_was_circle_under_article():
                self.last_level_type = 'circle_under_article'
                return 2, match.group(1), match.group(2).strip()
            else:
                self.last_level_type = 'circle'
                return 5, match.group(1), match.group(2).strip()

        # (가) 형식
        match = re.match(r'^(\([가-하]\))\s*(.*)$', line)
        if match:
            self.last_level_type = 'hangul_paren'
            return 4, match.group(1), match.group(2).strip()

        # a. 형식
        match = re.match(r'^([a-z]\.)\s*(.*)$', line)
        if match:
            self.last_level_type = 'alpha_dot'
            return 6, match.group(1), match.group(2).strip()

        # a) 형식
        match = re.match(r'^([a-z]\))\s*(.*)$', line)
        if match:
            self.last_level_type = 'alpha_paren'
            return 7, match.group(1), match.group(2).strip()

        # (a) 형식
        match = re.match(r'^(\([a-z]\))\s*(.*)$', line)
        if match:
            self.last_level_type = 'alpha_paren_enclosed'
            return 8, match.group(1), match.group(2).strip()

        # [부록X] 형식
        match = re.match(r'^(\[부록\s*\d+[^\]]*\])\s*(.*)$', line)
        if match:
            self.last_level_type = 'appendix'
            return 2, match.group(1), match.group(2).strip()

        # (부록) 또는 (참고)
        match = re.match(r'^(\(부록\)|\(참고\))\s*(.*)$', line)
        if match and line != "(참고)":
            self.last_level_type = 'reference'
            return 1, match.group(1), match.group(2).strip()

        # 매칭 안됨
        return 0, "", line

    def _has_chapter_or_section(self):
        """문서에 장/절 구조가 있는지 확인"""
        for item in self.content["조문내용"]:
            if item["번호"].startswith("제") and ("장" in item["번호"] or "절" in item["번호"]):
                return True
        return False

    def _last_item_was_article(self):
        """마지막 항목이 '제X조'인지 확인"""
        if not self.content["조문내용"]:
            return False

        # 최근 5개 항목 중에서 '제X조' 찾기
        recent_items = self.content["조문내용"][-5:]
        for item in reversed(recent_items):
            number = item["번호"]
            if number.startswith("제") and "조" in number:
                return True
            # 다른 번호 형식을 만나면 중단
            if number and not number.startswith("제"):
                return False

        return False

    def _last_item_was_circle_under_article(self):
        """마지막 항목이 '제X조 바로 다음 원형 번호'인지 확인
        예: 제3조 → ① → ②인 경우, ②의 다음 ③도 같은 레벨이어야 함
        """
        if not self.content["조문내용"]:
            return False

        last_item = self.content["조문내용"][-1]
        last_number = last_item["번호"]
        last_level = last_item["레벨"]

        # 마지막 항목이 레벨2이고 원형 번호인 경우
        circle_pattern = r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟ⓛ]$'
        if last_level == 2 and re.match(circle_pattern, last_number):
            return True

        return False

    def should_merge_with_next_line(self, line, next_line):
        """현재 줄이 다음 줄과 병합되어야 하는지 확인"""
        if not line or not next_line:
            return False

        # 불완전한 문장 패턴
        incomplete_patterns = [
            r'.*\(\s*\d+\s*-\s*$',
            r'.*\(\s*$',
            r'.*[,，]\s*$',
            r'.*\s+$',
        ]

        # 연속 내용 패턴
        continuation_patterns = [
            r'^\d+\)',
            r'^[가-힣]',
            r'^[a-zA-Z]',
            r'^\)',
        ]

        # 새로운 항목 패턴
        new_item_patterns = [
            r'^\d+\.\s',
            r'^\d+\)\s',
            r'^제\d+조',
            r'^제\d+장',
            r'^제\d+절',
            r'^\([가-힣]+\)',
            r'^\(\d+\)\s',
            r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟ⓛ]',
            r'^\([가-하]\)',
            r'^[ⅰⅱⅲⅳⅴ]\)',
            r'^[a-z]\.\s',
            r'^[a-z]\)',
            r'^\([a-z]\)',
        ]

        # 새로운 항목이면 병합하지 않음
        for pattern in new_item_patterns:
            if re.match(pattern, next_line.strip()):
                return False

        # 불완전한 문장이고 연속 내용인 경우
        for incomplete_pattern in incomplete_patterns:
            if re.match(incomplete_pattern, line):
                for new_pattern in new_item_patterns:
                    if re.match(new_pattern, next_line.strip()):
                        return False

                for continuation_pattern in continuation_patterns:
                    if re.match(continuation_pattern, next_line.strip()):
                        return True

        return False

    def contains_numbered_list(self, line):
        """줄에 번호가 붙은 목록이 포함되어 있는지 확인"""
        numbered_list_pattern = r'\d+-\d+\.\s+'
        matches = re.findall(numbered_list_pattern, line)
        if len(matches) >= 2:
            return True

        circle_pattern = r'[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟]\s+'
        circle_matches = re.findall(circle_pattern, line)
        return len(circle_matches) >= 2

    def split_numbered_list(self, line):
        """번호가 붙은 목록을 개별 항목으로 분리"""
        items = []

        main_with_sub_match = re.match(r'^(\d+\.)\s+([^0-9]+?)\s+(\d+-\d+\.\s+.+)$', line)
        if main_with_sub_match:
            main_number = main_with_sub_match.group(1)
            main_content = main_with_sub_match.group(2).strip()
            sub_content = main_with_sub_match.group(3)
            items.append((2, main_number, main_content))
            self._extract_numbered_subitems(sub_content, items, 3)
        else:
            direct_list_match = re.match(r'^([^0-9]*?)\s*(\d+-\d+\.\s+.+)$', line)
            if direct_list_match:
                prefix = direct_list_match.group(1).strip()
                sub_content = direct_list_match.group(2)
                if prefix:
                    items.append((2, "", prefix))
                self._extract_numbered_subitems(sub_content, items, 3)
            else:
                circle_pattern = r'([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟])\s+'
                circle_matches = re.findall(circle_pattern, line)
                if len(circle_matches) >= 2:
                    self._extract_circle_number_items(line, items)

        return items if items else [(0, "", line)]

    def _extract_numbered_subitems(self, content, items, level):
        """번호가 붙은 하위 항목들을 추출"""
        sub_pattern = r'(\d+-\d+)\.\s+([^0-9]*?)(?=\s*\d+-\d+\.|$)'
        sub_matches = re.findall(sub_pattern, content)
        for sub_number, sub_desc in sub_matches:
            clean_desc = sub_desc.strip().rstrip(',').rstrip()
            if clean_desc:
                items.append((level, f"{sub_number}.", clean_desc))

    def _extract_circle_number_items(self, line, items):
        """원형숫자가 포함된 텍스트를 분리"""
        circle_pattern = r'([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟])\s*'
        parts = re.split(circle_pattern, line)

        if parts[0].strip():
            prefix_level, prefix_number, prefix_content = self.get_line_info(parts[0].strip())
            if prefix_level > 0:
                items.append((prefix_level, prefix_number, prefix_content))
            else:
                items.append((5, "⑳", parts[0].strip()))

        for i in range(1, len(parts), 2):
            if i < len(parts) - 1:
                circle_num = parts[i]
                content = parts[i + 1].strip().rstrip(',').rstrip()
                if content:
                    items.append((5, circle_num, content))

    def is_metadata_line(self, line):
        """메타데이터 라인인지 확인"""
        metadata_patterns = [
            r'^2\.1\.2\.2\.\s*정신건강의학과.*입원환자\s*관리$',
            r'^페이지\s*\d+\s*/\s*\d+',
            r'^\d{4}\.\d{2}\.\d{2}\.',
            r'^승\s*인[:：]',
            r'^\(인\)$',
            r'^대외비$',
            r'^-+\s*페이지\s*구분\s*-+$',
            r'^여비규정\(소관부서\s*:\s*[^\)]+\)$',  # 헤더 반복
        ]

        for pattern in metadata_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False

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
    parser = UniversalRegulationParser()
    result = parser.parse_txt_to_json(txt_content)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"JSON 파일 생성 완료: {output_file}")

    return result


def process_folder(input_path, output_path):
    """폴더 내의 모든 TXT 파일을 처리"""
    os.makedirs(output_path, exist_ok=True)

    txt_files = glob.glob(os.path.join(input_path, "*.txt"))

    if not txt_files:
        print(f"경로에 TXT 파일이 없습니다: {input_path}")
        return

    print(f"총 {len(txt_files)}개의 TXT 파일을 찾았습니다.")
    print("-" * 50)

    success_count = 0
    fail_count = 0

    for idx, txt_path in enumerate(txt_files, 1):
        filename = os.path.basename(txt_path)
        filename_without_ext = os.path.splitext(filename)[0]
        json_path = os.path.join(output_path, f"{filename_without_ext}.json")

        print(f"\n[{idx}/{len(txt_files)}] 처리 중: {filename}")
        logger.info(f"파일 처리 중 [{idx}/{len(txt_files)}]: {filename}")

        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                txt_content = f.read()

            result = convert_txt_to_json(txt_content, json_path)

            print(f"  - 조문 개수: {result['문서정보'].get('조문갯수', 0)}")
            logger.info(f"파일 처리 성공: {filename}, 조문 개수: {result['문서정보'].get('조문갯수', 0)}")
            success_count += 1

        except Exception as e:
            print(f"  - 오류 발생: {str(e)}")
            logger.error(f"파일 처리 실패: {filename}, 오류: {str(e)}")
            fail_count += 1

        print("-" * 50)

    print(f"\n변환 완료!")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"출력 경로: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법:")
        print("  단일 파일: python txt2json_v2.py <TXT파일경로> [출력JSON파일경로]")
        print("  폴더 처리: python txt2json_v2.py <TXT폴더경로> <출력폴더경로>")
        sys.exit(1)

    input_path = sys.argv[1]

    if os.path.isdir(input_path):
        if len(sys.argv) < 3:
            print("폴더 처리 시 출력 폴더 경로가 필요합니다.")
            print("사용법: python txt2json_v2.py <TXT폴더경로> <출력폴더경로>")
            sys.exit(1)

        output_path = sys.argv[2]
        process_folder(input_path, output_path)

    elif os.path.isfile(input_path):
        if not input_path.lower().endswith('.txt'):
            print("TXT 파일이 아닙니다.")
            sys.exit(1)

        with open(input_path, 'r', encoding='utf-8') as f:
            txt_content = f.read()

        base_name = os.path.splitext(input_path)[0]
        output_file = sys.argv[2] if len(sys.argv) > 2 else f"{base_name}.json"

        result = convert_txt_to_json(txt_content, output_file)

        print("\n[변환 결과 미리보기]")
        print(f"문서정보: {result['문서정보']}")
        print(f"\n조문내용 (첫 10개):")
        for item in result['조문내용'][:10]:
            print(f"  seq {item['seq']}: 레벨{item['레벨']} - {item['번호']} {item['내용'][:50]}...")

    else:
        print(f"경로를 찾을 수 없습니다: {input_path}")
        sys.exit(1)
