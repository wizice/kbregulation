# -*- coding: utf-8 -*-
"""
    query_synonym.py
    ~~~~~~~~~~~~~~~~

    유사어(Synonym) 데이터베이스 쿼리 모듈
    search_synonyms 테이블에서 유사어 그룹을 조회

    :copyright: (c) 2024 by wizice.
    :license: wizice.com
"""

from typing import List, Dict, Optional, Tuple
from app_logger import get_logger

logger = get_logger(__name__)


def get_all_synonyms(conn) -> List[Dict]:
    """
    활성화된 모든 유사어 그룹 조회

    Args:
        conn: 데이터베이스 연결 객체

    Returns:
        유사어 그룹 목록
        [
            {
                'synonym_id': 1,
                'group_name': '환자',
                'synonyms': ['환자', '피검자', '수진자', ...],
                'priority': 100
            },
            ...
        ]
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    synonym_id,
                    group_name,
                    synonyms,
                    priority
                FROM search_synonyms
                WHERE is_active = true
                ORDER BY priority DESC
            """)

            rows = cur.fetchall()

            results = []
            for row in rows:
                results.append({
                    'synonym_id': row[0],
                    'group_name': row[1],
                    'synonyms': row[2],  # PostgreSQL array -> Python list
                    'priority': row[3]
                })

            return results

    except Exception as e:
        logger.error(f"유사어 조회 오류: {e}")
        return []


def find_synonym_group(conn, term: str) -> Optional[Dict]:
    """
    특정 검색어가 속한 유사어 그룹 찾기

    Args:
        conn: 데이터베이스 연결 객체
        term: 검색어

    Returns:
        유사어 그룹 정보 또는 None
        {
            'synonym_id': 1,
            'group_name': '환자',
            'synonyms': ['환자', '피검자', '수진자', ...],
            'priority': 100
        }
    """
    try:
        with conn.cursor() as cur:
            # PostgreSQL array contains 연산자 사용
            cur.execute("""
                SELECT
                    synonym_id,
                    group_name,
                    synonyms,
                    priority
                FROM search_synonyms
                WHERE %s = ANY(synonyms)
                  AND is_active = true
                ORDER BY priority DESC
                LIMIT 1
            """, (term,))

            row = cur.fetchone()

            if row:
                return {
                    'synonym_id': row[0],
                    'group_name': row[1],
                    'synonyms': row[2],
                    'priority': row[3]
                }

            return None

    except Exception as e:
        logger.error(f"유사어 그룹 조회 오류: {e}")
        return None


def expand_search_terms(conn, terms: List[str]) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    검색어 목록을 유사어로 확장

    Args:
        conn: 데이터베이스 연결 객체
        terms: 원본 검색어 목록 (형태소 분석 결과)

    Returns:
        (확장된 검색어 목록, 확장 정보)

    Example:
        Input: ['피검자', '안전']
        Output: (
            ['환자', '피검자', '수진자', '진료대상자', '안전'],
            {'피검자': ['환자', '피검자', '수진자', '진료대상자', ...]}
        )
    """
    try:
        expanded_terms = set()
        expansion_info = {}

        for term in terms:
            # 원본 검색어 추가
            expanded_terms.add(term)

            # 유사어 그룹 찾기
            synonym_group = find_synonym_group(conn, term)

            if synonym_group:
                synonyms = synonym_group['synonyms']
                expansion_info[term] = {
                    'group_name': synonym_group['group_name'],
                    'synonyms': synonyms,
                    'original_term': term
                }

                # 모든 유사어 추가
                for synonym in synonyms:
                    expanded_terms.add(synonym)

                logger.debug(f"검색어 확장: '{term}' -> {synonyms}")

        return list(expanded_terms), expansion_info

    except Exception as e:
        logger.error(f"검색어 확장 오류: {e}")
        return terms, {}


def get_synonym_statistics(conn) -> Dict:
    """
    유사어 통계 조회

    Returns:
        {
            'total_groups': 12,
            'total_synonyms': 58,
            'active_groups': 12,
            'groups': [
                {'group_name': '환자', 'synonym_count': 6, 'priority': 100},
                ...
            ]
        }
    """
    try:
        with conn.cursor() as cur:
            # 그룹별 통계
            cur.execute("""
                SELECT
                    group_name,
                    array_length(synonyms, 1) as synonym_count,
                    priority,
                    is_active
                FROM search_synonyms
                ORDER BY priority DESC
            """)

            rows = cur.fetchall()

            groups = []
            total_synonyms = 0
            active_count = 0

            for row in rows:
                count = row[1] or 0
                groups.append({
                    'group_name': row[0],
                    'synonym_count': count,
                    'priority': row[2],
                    'is_active': row[3]
                })
                total_synonyms += count
                if row[3]:
                    active_count += 1

            return {
                'total_groups': len(rows),
                'active_groups': active_count,
                'total_synonyms': total_synonyms,
                'groups': groups
            }

    except Exception as e:
        logger.error(f"유사어 통계 조회 오류: {e}")
        return {
            'total_groups': 0,
            'active_groups': 0,
            'total_synonyms': 0,
            'groups': []
        }


def add_synonym_group(conn, group_name: str, synonyms: List[str],
                      description: str = None, priority: int = 50) -> bool:
    """
    새 유사어 그룹 추가

    Args:
        conn: 데이터베이스 연결 객체
        group_name: 그룹명 (대표어)
        synonyms: 유사어 목록
        description: 설명
        priority: 우선순위 (기본값 50)

    Returns:
        성공 여부
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO search_synonyms
                    (group_name, synonyms, description, priority, created_by)
                VALUES (%s, %s, %s, %s, 'api')
                RETURNING synonym_id
            """, (group_name, synonyms, description, priority))

            result = cur.fetchone()
            conn.commit()

            if result:
                logger.info(f"유사어 그룹 추가: {group_name} (ID: {result[0]})")
                return True

            return False

    except Exception as e:
        logger.error(f"유사어 그룹 추가 오류: {e}")
        conn.rollback()
        return False


def update_synonym_group(conn, synonym_id: int, synonyms: List[str] = None,
                         is_active: bool = None, priority: int = None) -> bool:
    """
    유사어 그룹 수정

    Args:
        conn: 데이터베이스 연결 객체
        synonym_id: 유사어 그룹 ID
        synonyms: 새 유사어 목록 (None이면 변경 안함)
        is_active: 활성화 여부 (None이면 변경 안함)
        priority: 우선순위 (None이면 변경 안함)

    Returns:
        성공 여부
    """
    try:
        updates = []
        params = []

        if synonyms is not None:
            updates.append("synonyms = %s")
            params.append(synonyms)

        if is_active is not None:
            updates.append("is_active = %s")
            params.append(is_active)

        if priority is not None:
            updates.append("priority = %s")
            params.append(priority)

        if not updates:
            return True

        updates.append("updated_at = NOW()")
        updates.append("updated_by = 'api'")

        params.append(synonym_id)

        with conn.cursor() as cur:
            query = f"""
                UPDATE search_synonyms
                SET {', '.join(updates)}
                WHERE synonym_id = %s
            """
            cur.execute(query, params)
            conn.commit()

            logger.info(f"유사어 그룹 수정: ID {synonym_id}")
            return True

    except Exception as e:
        logger.error(f"유사어 그룹 수정 오류: {e}")
        conn.rollback()
        return False
