# -*- coding: utf-8 -*-
"""
    hanparse.py
    ~~~~~~~~~~~

    한글 형태소 분석 간소화 버전
    연세대 krlaws.hanparse.HanParse 호환 인터페이스

    :copyright: (c) 2025
    :license: BSD
"""

import re
from typing import List, Optional


class HanParse:
    """
    한글 텍스트 파싱 클래스

    연세대 krlaws.hanparse.HanParse와 호환되는 인터페이스 제공
    간소화된 버전으로 기본적인 토큰화와 형태소 추출 기능 구현
    """

    def __init__(self):
        """초기화"""
        # 한글 음절 패턴
        self.hangul_pattern = re.compile(r'[가-힣]+')
        # 영문 단어 패턴
        self.english_pattern = re.compile(r'[a-zA-Z]+')
        # 숫자 패턴
        self.number_pattern = re.compile(r'\d+')
        # Reference 번호 패턴 (점으로 연결된 번호)
        # 예: 3.2.2, 11.5.4, COP.4.1, COP.3, IPSG.6, MMU.3.2
        # 패턴1: 영문.숫자(.숫자)* - COP.3, COP.4.1, MMU.3.2
        # 패턴2: 숫자.숫자(.숫자)* - 3.2.2, 11.5.4
        self.ref_pattern = re.compile(r'[A-Za-z]+\.\d+(?:\.\d+)*|(?:\d+\.)+\d+')
        # 특수문자 제거 패턴
        self.special_pattern = re.compile(r'[^\w\s가-힣]')

    def utf8(self, text: str) -> str:
        """
        UTF-8 문자열 처리

        Args:
            text: 입력 텍스트

        Returns:
            UTF-8 인코딩된 문자열
        """
        if not text:
            return ""

        if isinstance(text, bytes):
            return text.decode('utf-8', errors='ignore')

        return str(text)

    def parse(self, text: str, join_sep: Optional[str] = None) -> List[str]:
        """
        텍스트를 파싱하여 토큰 리스트 반환

        Args:
            text: 입력 텍스트
            join_sep: 조인 구분자 (None이면 리스트 반환, 문자열이면 조인하여 반환)

        Returns:
            토큰 리스트
        """
        if not text:
            return [] if join_sep is None else ""

        text = self.utf8(text)
        tokens = []

        # Reference 번호 추출 및 마스킹 (점으로 연결된 번호: 3.2.2, COP.4.1 등)
        # Reference로 인식된 부분은 개별 토큰으로 분리하지 않음
        ref_numbers = self.ref_pattern.findall(text)
        masked_text = text
        for ref in ref_numbers:
            tokens.append(ref.lower())
            # Reference 부분을 마스킹하여 개별 토큰 추출 방지
            masked_text = masked_text.replace(ref, ' ' * len(ref))

        # 한글 추출 (2글자 이상)
        hangul_words = self.hangul_pattern.findall(masked_text)
        for word in hangul_words:
            if len(word) >= 2:
                tokens.append(word)
                # 2-gram 추출 (더 정확한 검색을 위해)
                if len(word) >= 3:
                    for i in range(len(word) - 1):
                        tokens.append(word[i:i+2])

        # 영문 추출 (3글자 이상) - Reference에서 이미 추출된 부분 제외
        english_words = self.english_pattern.findall(masked_text)
        for word in english_words:
            if len(word) >= 3:
                tokens.append(word.lower())

        # 숫자 추출 - Reference에서 이미 추출된 부분 제외
        numbers = self.number_pattern.findall(masked_text)
        tokens.extend(numbers)

        # 중복 제거
        unique_tokens = list(set(tokens))

        if join_sep is not None:
            return join_sep.join(unique_tokens)

        return unique_tokens

    def parse_join(self, text: str, join_sep: str = " ") -> str:
        """
        텍스트를 파싱하여 공백으로 조인된 문자열 반환

        Args:
            text: 입력 텍스트
            join_sep: 조인 구분자 (기본값: 공백)

        Returns:
            토큰들이 조인된 문자열
        """
        tokens = self.parse(text)
        return join_sep.join(tokens)

    def extract_keywords(self, text: str, min_length: int = 2, max_count: int = 50) -> List[str]:
        """
        주요 키워드 추출

        Args:
            text: 입력 텍스트
            min_length: 최소 키워드 길이
            max_count: 최대 키워드 개수

        Returns:
            키워드 리스트
        """
        if not text:
            return []

        tokens = self.parse(text)

        # 길이 필터링
        keywords = [t for t in tokens if len(t) >= min_length]

        # 개수 제한
        return keywords[:max_count]

    def normalize(self, text: str) -> str:
        """
        텍스트 정규화 (특수문자 제거, 공백 정리)

        Args:
            text: 입력 텍스트

        Returns:
            정규화된 텍스트
        """
        if not text:
            return ""

        text = self.utf8(text)

        # 특수문자를 공백으로 변환
        text = self.special_pattern.sub(' ', text)

        # 연속된 공백을 하나로
        text = re.sub(r'\s+', ' ', text)

        return text.strip()


# 전역 인스턴스 (연세대 방식 호환)
_global_parser = None

def get_parser() -> HanParse:
    """전역 파서 인스턴스 반환"""
    global _global_parser
    if _global_parser is None:
        _global_parser = HanParse()
    return _global_parser


# 테스트 코드
if __name__ == '__main__':
    parser = HanParse()

    # 테스트 텍스트
    test_texts = [
        "11.5.4. 레이저 및 기타 광학 방사선 기기 안전 관리 프로그램",
        "세브란스병원 의료질향상 및 환자안전위원회",
        "환자 치료 및 시술에 사용되는 레이저",
        "JCI Standard 7th Edition: COP.4, 4.1"
    ]

    print("=== 한글 파싱 테스트 ===\n")

    for text in test_texts:
        print(f"원문: {text}")
        print(f"토큰: {parser.parse(text)}")
        print(f"조인: {parser.parse_join(text)}")
        print(f"키워드: {parser.extract_keywords(text)}")
        print()
