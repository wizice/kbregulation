# ga4_analyzer.py
"""GA4 데이터 분석 유틸리티"""

import re
from urllib.parse import urlparse, parse_qs, unquote
from typing import Dict, List, Tuple, Set, Optional
from collections import Counter
import pandas as pd

class GA4Analyzer:
    """GA4 데이터 분석기"""
    
    def __init__(self, sc_word_threshold: int = 1, top_n_sc_words: int = 100):
        self.sc_word_threshold = sc_word_threshold
        self.top_n_sc_words = top_n_sc_words
        self.include_keys = ["page", "sc_area", "sc_section_code", "sc_word"]
        
    def classify_page_type(self, path: str, query: dict) -> str:
        """페이지 유형 분류"""
        path_lower = path.lower()
        
        if "articleview.html" in path_lower and query.get("idxno"):
            return "상세기사"
        elif path == "/" or path == "":
            return "홈"
        elif "articlelist.html" in path_lower:
            return "기사목록"
        elif "bbs/list.html" in path_lower:
            return "게시판목록"
        elif "bbs/view.html" in path_lower:
            return "게시판상세"
        else:
            return "기타"
    
    def type_to_code(self, type_str: str) -> str:
        """유형을 코드로 변환"""
        mapping = {
            "기사목록": "[A]",
            "상세기사": "[V]",
            "홈": "[H]",
            "게시판목록": "[B]",
            "게시판상세": "[D]",
            "기타": "[O]"
        }
        return mapping.get(type_str, "[O]")
    
    def extract_idxno(self, url: str) -> Optional[str]:
        """URL에서 idxno 추출"""
        if pd.isna(url):
            return None
        match = re.search(r'idxno=(\d+)', str(url))
        return match.group(1) if match else None
    
    def normalize_url(self, url: str, top_sc_words: Set[str]) -> Tuple[str, str, Dict]:
        """URL 정규화 및 파라미터 추출"""
        parsed = urlparse(url)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        # 유형 분류
        type_str = self.classify_page_type(path, query)
        type_code = self.type_to_code(type_str)
        
        # 쿼리 파라미터 정규화
        norm_query = []
        params = {}
        
        for key in self.include_keys:
            if key == "page":
                if key in query and query[key][0].isdigit():
                    page_num = int(query[key][0])
                    if page_num > 1:
                        norm_query.append(f"page={page_num}")
                        params['page'] = page_num
            elif key == "sc_word":
                if key in query:
                    word = unquote(query[key][0])
                    if word in top_sc_words:
                        norm_query.append(f"sc_word={word}")
                        params['sc_word'] = word
                    else:
                        norm_query.append("sc_word=기타")
                        params['sc_word'] = "기타"
            elif key in query:
                # sc_area, sc_section_code 처리
                value = unquote(query[key][0])
                norm_query.append(f"{key}={value}")
                params[key] = value
        
        # 최종 URL 구성
        query_str = "&".join(norm_query)
        if type_str == "상세기사":
            final_url = f"{path}?idxno="
            params['idxno'] = self.extract_idxno(url)
        else:
            final_url = f"{path}?{query_str}" if query_str else path
        
        return type_code, final_url, params

    
    def analyze_sc_words(self, df: pd.DataFrame) -> Set[str]:
        """sc_word 빈도 분석 및 상위 단어 추출"""
        sc_words = []
        
        for url in df['pageLocation']:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            sc_word = unquote(query.get("sc_word", [""])[0])
            if sc_word:
                sc_words.append(sc_word)
        
        # 빈도 계산
        word_counter = Counter(sc_words)
        
        # 상위 단어 추출
        sorted_words = sorted(word_counter.items(), key=lambda x: x[1], reverse=True)
        top_words = [
            word for word, count in sorted_words 
            if count > self.sc_word_threshold
        ][:self.top_n_sc_words]
        
        return set(top_words)

