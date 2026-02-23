# ga4_db_converter.py
"""GA4 데이터를 DB 저장 형식으로 변환"""

import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, parse_qs, unquote

class GA4DBConverter:
    """GA4 데이터를 knews_galogs 테이블 형식으로 변환"""
    
    # 조회 타입 매핑
    VIEW_TYPE_MAPPING = {
        "상세기사": "상세기사",
        "기사목록": "기사목록", 
        "홈": "홈",
        "게시판목록": "게시판목록",
        "게시판상세": "게시판상세",
        "기타": "기타"
    }
    
    def __init__(self):
        self.stats = {
            'total': 0,
            'converted': 0,
            'skipped': 0,
            'errors': []
        }
    
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
    
    def extract_search_keyword(self, query: dict) -> Optional[str]:
        """검색어 추출"""
        sc_word = query.get('sc_word', [None])[0]
        if sc_word:
            return unquote(sc_word)
        return None
    
    def convert_record(self, ga_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """GA4 레코드를 DB 형식으로 변환"""
        try:
            url = ga_record.get('pageLocation', '')
            if not url:
                return None
            
            # URL 파싱
            parsed = urlparse(url)
            path = parsed.path
            query = parse_qs(parsed.query)
            
            # 페이지 유형 분류
            page_type = self.classify_page_type(path, query)
            
            # 기본 데이터
            db_record = {
                'visit_date': ga_record.get('date'),
                'view_type': self.VIEW_TYPE_MAPPING.get(page_type, '기타'),
                'page_views': int(float(ga_record.get('screenPageViews', 0))),
                'active_users': int(float(ga_record.get('activeUsers', 0)))
            }
            
            # 상세기사인 경우 idxno 추출
            if page_type == "상세기사":
                idxno_match = re.search(r'idxno=(\d+)', url)
                if idxno_match:
                    db_record['idxno'] = idxno_match.group(1)
            
            # 검색어가 있는 경우
            keyword = self.extract_search_keyword(query)
            if keyword and keyword != "기타":  # "기타"는 제외
                # 검색어가 있으면 별도 레코드로 저장
                search_record = db_record.copy()
                search_record['view_type'] = '검색어'
                search_record['keyword'] = keyword
                search_record['idxno'] = None
                return [db_record, search_record]
            
            return [db_record]
            
        except Exception as e:
            self.stats['errors'].append({
                'url': ga_record.get('pageLocation', 'unknown'),
                'error': str(e)
            })
            return None
    
    def convert_batch(self, ga_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """GA4 레코드 배치 변환"""
        converted_records = []
        self.stats['total'] = len(ga_records)
        
        for record in ga_records:
            result = self.convert_record(record)
            if result:
                if isinstance(result, list):
                    converted_records.extend(result)
                    self.stats['converted'] += len(result)
                else:
                    converted_records.append(result)
                    self.stats['converted'] += 1
            else:
                self.stats['skipped'] += 1
        
        return converted_records
    
    def aggregate_by_key(self, records: List[Dict[str, Any]], debug: bool = False) -> List[Dict[str, Any]]:
        """동일 키로 레코드 집계 (날짜, 유형, idxno/keyword)"""
        aggregated = {}
        aggregation_log = []  # 집계 로그
        
        for record in records:
            # 집계 키 생성
            key_parts = [
                record['visit_date'],
                record['view_type'],
                record.get('idxno', ''),
                record.get('keyword', '')
            ]
            key = '|'.join(str(p) for p in key_parts)
            
            if key in aggregated:
                # 기존 레코드에 누적
                before_views = aggregated[key]['page_views']
                before_users = aggregated[key]['active_users']
                
                aggregated[key]['page_views'] += record['page_views']
                aggregated[key]['active_users'] += record['active_users']
                
                if debug:
                    aggregation_log.append({
                        'key': key,
                        'action': 'aggregate',
                        'before': {'views': before_views, 'users': before_users},
                        'added': {'views': record['page_views'], 'users': record['active_users']},
                        'after': {'views': aggregated[key]['page_views'], 'users': aggregated[key]['active_users']}
                    })
            else:
                # 새 레코드
                aggregated[key] = record.copy()
                if debug:
                    aggregation_log.append({
                        'key': key,
                        'action': 'new',
                        'record': record.copy()
                    })
        
        if debug:
            self.aggregation_log = aggregation_log
        
        return list(aggregated.values())

