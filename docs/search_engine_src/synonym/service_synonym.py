# -*- coding: utf-8 -*-
"""
    service_synonym.py
    ~~~~~~~~~~~~~~~~~~

    유사어(Synonym) 검색 확장 서비스
    검색어를 유사어로 확장하여 검색 품질 향상

    사용 예:
        synonym_service = SynonymService(db_connection)
        expanded = synonym_service.expand_query(['피검자', '안전'])
        # 결과: ['환자', '피검자', '수진자', ...', '안전']

    :copyright: (c) 2024 by wizice.
    :license: wizice.com
"""

from typing import List, Dict, Optional, Tuple, Set
from app_logger import get_logger
from . import query_synonym

logger = get_logger(__name__)


class SynonymService:
    """유사어 검색 확장 서비스"""

    def __init__(self, db_manager=None):
        """
        초기화

        Args:
            db_manager: DatabaseConnectionManager 인스턴스
        """
        self.db_manager = db_manager
        self._cache = {}  # 유사어 캐시 (메모리)
        self._cache_loaded = False

    def _get_connection(self):
        """DB 연결 가져오기"""
        if self.db_manager:
            return self.db_manager.get_connection()
        return None

    def load_synonyms_to_cache(self) -> bool:
        """
        모든 유사어를 메모리 캐시에 로드

        Returns:
            성공 여부
        """
        try:
            conn_ctx = self._get_connection()
            if not conn_ctx:
                logger.warning("DB 연결 없음 - 유사어 캐시 로드 실패")
                return False

            with conn_ctx as conn:
                synonyms = query_synonym.get_all_synonyms(conn)

                # 캐시 구조: {검색어: 유사어_목록}
                self._cache = {}

                for group in synonyms:
                    synonym_list = group['synonyms']
                    group_name = group['group_name']

                    # 각 유사어를 키로 하여 전체 유사어 목록 저장
                    for term in synonym_list:
                        self._cache[term] = {
                            'group_name': group_name,
                            'synonyms': synonym_list,
                            'priority': group['priority']
                        }

                self._cache_loaded = True
                logger.info(f"유사어 캐시 로드 완료: {len(synonyms)}개 그룹, {len(self._cache)}개 검색어")
                return True

        except Exception as e:
            logger.error(f"유사어 캐시 로드 오류: {e}")
            return False

    def expand_query(self, terms: List[str], use_cache: bool = True) -> Dict:
        """
        검색어 목록을 유사어로 확장

        Args:
            terms: 원본 검색어 목록 (형태소 분석 결과)
            use_cache: 캐시 사용 여부

        Returns:
            {
                'original_terms': ['피검자', '안전'],
                'expanded_terms': ['환자', '피검자', '수진자', ...', '안전'],
                'expansion_info': {
                    '피검자': {
                        'group_name': '환자',
                        'synonyms': ['환자', '피검자', '수진자', ...],
                        'original_term': '피검자'
                    }
                },
                'expanded_count': 5,
                'was_expanded': True
            }
        """
        result = {
            'original_terms': terms,
            'expanded_terms': list(terms),
            'expansion_info': {},
            'expanded_count': 0,
            'was_expanded': False
        }

        if not terms:
            return result

        try:
            expanded_terms = set(terms)
            expansion_info = {}

            if use_cache and self._cache_loaded:
                # 캐시에서 유사어 조회
                for term in terms:
                    if term in self._cache:
                        cache_entry = self._cache[term]
                        synonyms = cache_entry['synonyms']

                        expansion_info[term] = {
                            'group_name': cache_entry['group_name'],
                            'synonyms': synonyms,
                            'original_term': term
                        }

                        for synonym in synonyms:
                            expanded_terms.add(synonym)

                        logger.debug(f"[Cache] 검색어 확장: '{term}' -> {len(synonyms)}개 유사어")

            else:
                # DB에서 직접 조회
                conn_ctx = self._get_connection()
                if conn_ctx:
                    with conn_ctx as conn:
                        expanded_terms, expansion_info = query_synonym.expand_search_terms(
                            conn, terms
                        )
                        expanded_terms = set(expanded_terms)

            result['expanded_terms'] = list(expanded_terms)
            result['expansion_info'] = expansion_info
            result['expanded_count'] = len(expanded_terms) - len(terms)
            result['was_expanded'] = len(expansion_info) > 0

            if result['was_expanded']:
                logger.info(f"검색어 확장: {terms} -> {len(expanded_terms)}개 ({result['expanded_count']}개 추가)")

            return result

        except Exception as e:
            logger.error(f"검색어 확장 오류: {e}")
            return result

    def find_synonyms(self, term: str) -> Optional[List[str]]:
        """
        특정 검색어의 유사어 목록 조회

        Args:
            term: 검색어

        Returns:
            유사어 목록 또는 None
        """
        # 캐시에서 먼저 조회
        if self._cache_loaded and term in self._cache:
            return self._cache[term]['synonyms']

        # DB에서 조회
        conn_ctx = self._get_connection()
        if conn_ctx:
            with conn_ctx as conn:
                group = query_synonym.find_synonym_group(conn, term)
                if group:
                    return group['synonyms']

        return None

    def get_all_groups(self) -> List[Dict]:
        """
        모든 유사어 그룹 조회

        Returns:
            유사어 그룹 목록
        """
        conn_ctx = self._get_connection()
        if conn_ctx:
            with conn_ctx as conn:
                return query_synonym.get_all_synonyms(conn)
        return []

    def get_statistics(self) -> Dict:
        """
        유사어 통계 조회

        Returns:
            통계 정보
        """
        conn_ctx = self._get_connection()
        if conn_ctx:
            with conn_ctx as conn:
                stats = query_synonym.get_synonym_statistics(conn)
                stats['cache_loaded'] = self._cache_loaded
                stats['cache_size'] = len(self._cache)
                return stats
        return {
            'total_groups': 0,
            'active_groups': 0,
            'total_synonyms': 0,
            'groups': [],
            'cache_loaded': self._cache_loaded,
            'cache_size': len(self._cache)
        }

    def build_es_should_clauses(self, terms: List[str], field: str = "tags",
                                 expand_synonyms: bool = True) -> Tuple[List[Dict], Dict]:
        """
        Elasticsearch should 절 생성 (유사어 확장 포함)

        Args:
            terms: 검색어 목록
            field: 검색할 필드명
            expand_synonyms: 유사어 확장 여부

        Returns:
            (should_clauses, expansion_info)

        Example:
            should_clauses, info = service.build_es_should_clauses(['환자'])
            # should_clauses: [
            #     {"match": {"tags": "환자"}},
            #     {"match": {"tags": "피검자"}},
            #     {"match": {"tags": "수진자"}},
            #     ...
            # ]
        """
        should_clauses = []
        expansion_info = {}

        if expand_synonyms:
            expansion_result = self.expand_query(terms)
            search_terms = expansion_result['expanded_terms']
            expansion_info = expansion_result['expansion_info']
        else:
            search_terms = terms

        for term in search_terms:
            should_clauses.append({
                "match": {
                    field: term
                }
            })

        return should_clauses, expansion_info

    def build_es_query_with_synonyms(self, original_terms: List[str],
                                      expand_synonyms: bool = True) -> Dict:
        """
        유사어 확장이 포함된 Elasticsearch 쿼리 생성

        기존 AND 검색을 유지하면서 유사어 확장 적용:
        - 원본 검색어 각각에 대해 OR로 유사어 확장
        - 확장된 그룹 간에는 AND 유지

        Args:
            original_terms: 원본 검색어 (형태소 분석 결과)
            expand_synonyms: 유사어 확장 여부

        Returns:
            {
                'query': {...},  # ES query body
                'expansion_info': {...},
                'was_expanded': bool
            }

        Example:
            검색어: ['피검자', '안전']

            확장 전: tags:피검자 AND tags:안전
            확장 후: (tags:환자 OR tags:피검자 OR tags:수진자...) AND tags:안전
        """
        must_clauses = []
        all_expansion_info = {}
        was_expanded = False

        for term in original_terms:
            if expand_synonyms:
                # 해당 검색어의 유사어 찾기
                synonyms = self.find_synonyms(term)

                if synonyms:
                    # 유사어가 있으면 OR 절로 확장
                    should_clauses = []
                    for synonym in synonyms:
                        should_clauses.append({
                            "match": {"tags": synonym}
                        })

                    must_clauses.append({
                        "bool": {
                            "should": should_clauses,
                            "minimum_should_match": 1
                        }
                    })

                    all_expansion_info[term] = {
                        'synonyms': synonyms,
                        'expanded': True
                    }
                    was_expanded = True
                else:
                    # 유사어가 없으면 원본 검색어 사용
                    must_clauses.append({
                        "match": {"tags": term}
                    })
                    all_expansion_info[term] = {
                        'synonyms': [term],
                        'expanded': False
                    }
            else:
                # 유사어 확장 안함
                must_clauses.append({
                    "match": {"tags": term}
                })

        # 구문 매칭 boost (원본 검색어 기준)
        original_query_text = ' '.join(original_terms)

        query = {
            "bool": {
                "must": must_clauses,
                "should": [
                    {
                        "match_phrase": {
                            "tags": {
                                "query": original_query_text,
                                "slop": 2,
                                "boost": 2.0
                            }
                        }
                    }
                ]
            }
        }

        return {
            'query': query,
            'expansion_info': all_expansion_info,
            'was_expanded': was_expanded,
            'original_terms': original_terms
        }


# 전역 서비스 인스턴스 (지연 초기화용)
_synonym_service = None


def get_synonym_service(db_manager=None) -> SynonymService:
    """
    유사어 서비스 싱글톤 인스턴스 반환

    Args:
        db_manager: DatabaseConnectionManager (첫 호출 시 필요)

    Returns:
        SynonymService 인스턴스
    """
    global _synonym_service

    if _synonym_service is None:
        _synonym_service = SynonymService(db_manager)
        # 캐시 로드
        _synonym_service.load_synonyms_to_cache()

    elif db_manager and _synonym_service.db_manager is None:
        _synonym_service.db_manager = db_manager
        _synonym_service.load_synonyms_to_cache()

    return _synonym_service


def reload_synonym_cache(db_manager=None) -> bool:
    """
    유사어 캐시 갱신

    Returns:
        성공 여부
    """
    service = get_synonym_service(db_manager)
    return service.load_synonyms_to_cache()
