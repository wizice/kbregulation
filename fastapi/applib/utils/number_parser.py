"""
Word 문서의 자동번호매기기를 순차적으로 증가하는 번호로 추출하는 모듈
"""
import re
from typing import Dict, Any, List, Tuple, Optional
import docx

class NumberingParser:
    """
    Word 문서의 자동번호매기기를 파싱하는 클래스
    """
    def __init__(self):
        # 레벨별 번호 추적
        self.level_counters = {
            1: 0,  # 레벨 1 ("제N조" 또는 "N.")
            2: 0,  # 레벨 2 ("N-N.")
            3: 0,  # 레벨 3 ("N)" 또는 "a.")
            4: 0,  # 레벨 4 ("(가)" 등)
            5: 0,  # 레벨 5 ("ⓐ" 등)
            6: 0   # 레벨 6 ("a." 재사용)
        }
        
        # 상위 레벨 변경 추적
        self.parent_level_changes = {
            1: 0,  # 레벨 1 변경 카운터
            2: 0,  # 레벨 2 변경 카운터
            3: 0,  # 레벨 3 변경 카운터
            4: 0,  # 레벨 4 변경 카운터
            5: 0,  # 레벨 5 변경 카운터
            6: 0   # 레벨 6 변경 카운터
        }
        
        # 현재 상위 레벨 번호
        self.current_parent_numbers = {
            1: 0,  # 레벨 1 번호
            2: 0,  # 레벨 2 번호
            3: 0,  # 레벨 3 번호
            4: 0,  # 레벨 4 번호
            5: 0,  # 레벨 5 번호
            6: 0   # 레벨 6 번호
        }
        
        self.current_level = 0
        self.found_content_start = False

    def reset(self):
        """상태 초기화"""
        self.level_counters = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        self.parent_level_changes = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        self.current_parent_numbers = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        self.current_level = 0
        self.found_content_start = False

    def parse_document(self, doc: docx.Document) -> List[Dict[str, Any]]:
        """
        Word 문서를 파싱하여 번호매기기가 포함된 내용을 추출합니다.
        
        Args:
            doc: docx.Document 객체
            
        Returns:
            추출된 내용 리스트 (순차적 번호가 적용됨)
        """
        self.reset()
        results = []
        
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if not text:
                continue
                
            # 문서 제목 시작 감지
            if "정확한 환자 확인" in text and not self.found_content_start:
                results.append({
                    "seq": len(results) + 1,
                    "레벨": 0,  # 제목 레벨
                    "내용": text,
                    "관련이미지": []
                })
                continue
                
            # 제N조 패턴 확인 - 본문 시작 감지
            if re.match(r'^제\d+조\s*\([목적정의절차부록참고]', text) and not self.found_content_start:
                self.found_content_start = True
                
            # 메타데이터 표 이후의 내용만 처리
            if not self.found_content_start and not re.match(r'^제\d+조', text):
                continue
                
            # 내규의 제·개정 이력 섹션에 도달하면 처리 중단
            if "내규의 제·개정 이력" in text:
                break
            
            # 번호 추출 및 변환
            number_info = self.extract_and_update_numbering(paragraph, text)
            
            if number_info:
                # 번호 정보가 추출된 경우
                level = number_info["level"]
                extracted_number = number_info["number"]
                
                # 원래 텍스트에 번호가 있는지 확인
                number_in_text = bool(re.match(r'^제\d+조|^\d+\.|^\d+-\d+\.|^\s*\d+\)|^[a-z]\.|^[①②③④⑤⑥⑦⑧⑨⑩]', text))
                
                # 번호가 텍스트에 없으면 추가
                final_text = text
                if not number_in_text and extracted_number:
                    # 추출된 번호에 따라 텍스트 앞에 번호 추가
                    final_text = f"{extracted_number} {text}"
                
                results.append({
                    "seq": len(results) + 1,
                    "레벨": level,
                    "내용": final_text,
                    "번호": extracted_number,
                    "관련이미지": []
                })
            else:
                # 번호 정보가 없는 일반 텍스트
                # 들여쓰기에 따라 레벨 추정
                indent_level = 0
                for char in text:
                    if char in [' ', '\t']:
                        indent_level += 1
                    else:
                        break
                        
                level = 1  # 기본 레벨
                if indent_level >= 16:
                    level = 6
                elif indent_level >= 12:
                    level = 5
                elif indent_level >= 10:
                    level = 4
                elif indent_level >= 8:
                    level = 3
                elif indent_level >= 4:
                    level = 2
                    
                results.append({
                    "seq": len(results) + 1,
                    "레벨": level,
                    "내용": text,
                    "관련이미지": []
                })
        
        return results

    def extract_and_update_numbering(self, paragraph, text: str) -> Optional[Dict[str, Any]]:
        """
        텍스트와 단락 객체에서 번호 형식을 추출하고 카운터를 업데이트합니다.
        
        Args:
            paragraph: docx 단락 객체
            text: 단락 텍스트
            
        Returns:
            번호 정보 사전 또는 None
        """
        # 번호 형식 추출
        number_info = self.extract_numbering(paragraph, text)
        
        if not number_info:
            return None
            
        level = number_info["level"]
        number_type = number_info["type"]
        
        # 레벨이 바뀌면 하위 레벨 번호 초기화
        if level < self.current_level:
            for l in range(level + 1, 7):
                self.level_counters[l] = 0
        
        # 상위 레벨 변경 추적
        if level == 1:
            # "제N조" 형식에서 N 추출
            if "제" in number_info["number"]:
                match = re.search(r'\d+', number_info["number"])
                if match:
                    num = int(match.group())
                    self.level_counters[1] = num
                else:
                    self.level_counters[1] += 1
            else:
                self.level_counters[1] += 1
                
            self.current_parent_numbers[1] = self.level_counters[1]
            self.level_counters[2] = 0
            self.level_counters[3] = 0
            self.parent_level_changes[1] += 1
        elif level == 2:
            # 상위 레벨이 바뀌었는지 확인
            if self.current_parent_numbers[1] != self.level_counters[1]:
                # 상위 레벨이 바뀌었으면 번호 초기화
                self.level_counters[2] = 1
                self.current_parent_numbers[1] = self.level_counters[1]
            else:
                # 아니면 이전 번호에 1 증가
                self.level_counters[2] += 1
                
            self.current_parent_numbers[2] = self.level_counters[2]
            self.level_counters[3] = 0
            self.parent_level_changes[2] += 1
        elif level == 3:
            # 상위 레벨이 바뀌었는지 확인
            if self.current_parent_numbers[2] != self.level_counters[2]:
                # 상위 레벨이 바뀌었으면 번호 초기화
                self.level_counters[3] = 1
                self.current_parent_numbers[2] = self.level_counters[2]
            else:
                # 아니면 이전 번호에 1 증가
                self.level_counters[3] += 1
        
        # 생성된 번호로 업데이트
        number_info["number"] = self.generate_number_by_level(level, number_type)
        self.current_level = level
        
        return number_info

    def generate_number_by_level(self, level: int, number_type: str) -> str:
        """
        레벨과 카운터에 따라 번호를 생성합니다.
        
        Args:
            level: 번호 레벨
            number_type: 번호 유형
            
        Returns:
            생성된 번호 문자열
        """
        if level == 1:
            if number_type == "article_ko" or number_type.startswith("xml_article"):
                # "제N조" 형식
                return f"제{self.level_counters[1]}조"
            else:
                # "N." 형식
                return f"{self.level_counters[1]}."
        
        elif level == 2:
            if number_type == "subsection_number" or number_type.startswith("xml_subsection"):
                # "N-N." 형식 - 첫 번째 N은 상위 레벨 번호
                return f"{self.level_counters[1]}-{self.level_counters[2]}."
            else:
                # 기타 형식
                return f"{self.level_counters[2]}."
        
        elif level == 3:
            if number_type == "item_number" or number_type.startswith("xml_item"):
                # "N)" 형식
                return f"{self.level_counters[3]})"
            elif number_type == "alpha_point":
                # "a." 형식 - 숫자를 알파벳으로 변환
                alpha = chr(ord('a') + self.level_counters[3] - 1) if 1 <= self.level_counters[3] <= 26 else '?'
                return f"{alpha}."
            elif number_type == "circle_number":
                # 원형 숫자 형식
                circle_numbers = "①②③④⑤⑥⑦⑧⑨⑩"
                circle_num = circle_numbers[self.level_counters[3] - 1] if 1 <= self.level_counters[3] <= 10 else '?'
                return circle_num
            else:
                # 기타 형식
                return f"{self.level_counters[3]})"
        
        return ""

    def extract_numbering(self, paragraph, text: str) -> Optional[Dict[str, Any]]:
        """
        텍스트와 단락 객체에서 번호 형식을 추출합니다.
        
        Args:
            paragraph: docx 단락 객체
            text: 단락 텍스트
            
        Returns:
            번호 정보 사전 또는 None
        """
        # 제N조 형식 (한글 조문)
        match_article = re.match(r'^제(\d+)조\s*\(([^)]+)\)', text)
        if match_article:
            return {
                "number": f"제{match_article.group(1)}조",
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
        
        # N-N. 형식 (숫자-숫자 점)
        match_subsection = re.match(r'^(\d+-\d+)\.\s*', text)
        if match_subsection:
            return {
                "number": match_subsection.group(1) + ".",
                "level": 2,
                "type": "subsection_number"
            }
        
        # N) 형식 (숫자 괄호) - 스킵
        # match_item = re.match(r'^\s*(\d+)\)\s*', text)
        # if match_item:
        #     return {
        #         "number": match_item.group(1) + ")",
        #         "level": 3,
        #         "type": "item_number"
        #     }
        
        # a. 형식 (알파벳 점)
        match_alpha = re.match(r'^([a-z])\.\s*', text)
        if match_alpha:
            return {
                "number": match_alpha.group(1) + ".",
                "level": 3,
                "type": "alpha_point"
            }
        
        # 원형 숫자 형식 (①, ②, ...)
        match_circle = re.match(r'^\s*([①②③④⑤⑥⑦⑧⑨⑩])\s*', text)
        if match_circle:
            circle_numbers = "①②③④⑤⑥⑦⑧⑨⑩"
            number_idx = circle_numbers.index(match_circle.group(1)) + 1
            return {
                "number": match_circle.group(1),
                "level": 3,
                "type": "circle_number"
            }
        
        # XML에서 자동번호매기기 속성 확인
        xml_number_info = self.extract_numbering_from_xml(paragraph)
        if xml_number_info:
            return xml_number_info
        
        return None

    def extract_numbering_from_xml(self, paragraph) -> Optional[Dict[str, Any]]:
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
                        
                        # 이미지에서 보이는 패턴과 매핑
                        if level == 0:
                            return {
                                "number": "제조",  # 실제로는 "제1조", "제2조" 등으로 변환됨
                                "level": 1,
                                "type": "xml_article"
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
                        else:
                            # 기타 레벨
                            return {
                                "number": "기타",
                                "level": min(level + 1, 3),  # 최대 레벨 3
                                "type": "xml_other"
                            }
        except Exception:
            pass
        
        return None


def parse_docx_with_sequential_numbers(file_path: str) -> List[Dict[str, Any]]:
    """
    Word 문서를 파싱하여 순차적 번호가 적용된 내용을 추출합니다.
    
    Args:
        file_path: Word 문서 파일 경로
        
    Returns:
        추출된 내용 리스트
    """
    doc = docx.Document(file_path)
    parser = NumberingParser()
    return parser.parse_document(doc)


if __name__ == "__main__":
    import sys
    import os
    
    if len(sys.argv) < 2:
        print("사용법: python -m utils.number_parser <docx_file_path>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"오류: 파일을 찾을 수 없습니다 - {file_path}")
        sys.exit(1)
        
    results = parse_docx_with_sequential_numbers(file_path)
    
    # 결과 출력
    print(f"총 {len(results)}개 항목 추출:")
    print("-" * 80)
    
    for item in results:
        level_indent = "  " * (item["레벨"] - 1) if item["레벨"] > 0 else ""
        print(f"{level_indent}[{item['seq']}] 레벨: {item['레벨']}")
        print(f"{level_indent}내용: {item['내용']}")
        if "번호" in item:
            print(f"{level_indent}번호: {item['번호']}")
        print("-" * 80)

