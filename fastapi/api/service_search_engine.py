# -*- coding: utf-8 -*-
"""
    service_search_engine.py
    ~~~~~~~~~~~~~~~~~~~~~~~~

    검색 엔진 서비스 - PostgreSQL FTS 기반
    JSON 파일 색인 및 검색 기능

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, Optional, List
import json
import os
from datetime import datetime
import logging
from pathlib import Path

from .auth_middleware import get_current_user
from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/search",
    tags=["search"],
    responses={404: {"description": "Not found"}},
)

# JSON 파일 기본 경로
JSON_BASE_PATH = Path(f"{settings.APPLIB_DIR}/json")
JSON_MERGED_PATH = Path(f"{settings.APPLIB_DIR}/merged")


def get_db_connection():
    """데이터베이스 연결 생성"""
    db_config = {
        'database': settings.DB_NAME,
        'user': settings.DB_USER,
        'password': settings.DB_PASSWORD,
        'host': settings.DB_HOST,
        'port': settings.DB_PORT
    }
    return DatabaseConnectionManager(**db_config)


def find_json_file_for_rule(rule_name: str, pub_no: str = None) -> Optional[Path]:
    """규정명으로 JSON 파일 자동 찾기"""
    try:
        # 1. merged 폴더에서 검색 (우선순위)
        if JSON_MERGED_PATH.exists():
            # 파일명 패턴: merged_1.1.1. 정확한 환자 확인_202503개정_*.json
            for json_file in JSON_MERGED_PATH.glob('merged_*.json'):
                filename = json_file.name
                # 규정명이 파일명에 포함되어 있는지 확인
                if rule_name in filename:
                    return json_file

        # 2. json 폴더에서 검색
        if JSON_BASE_PATH.exists():
            for json_file in JSON_BASE_PATH.glob('*.json'):
                filename = json_file.name
                if rule_name in filename:
                    return json_file

        return None
    except Exception as e:
        logger.error(f"Error finding JSON file for {rule_name}: {e}")
        return None


def read_json_file(file_path: str) -> Optional[Dict]:
    """JSON 파일 읽기"""
    try:
        # Handle different path formats
        if os.path.isabs(file_path):
            # Absolute path
            full_path = Path(file_path)
        elif file_path.startswith('applib/json/'):
            # Path relative to fastapi directory
            full_path = Path(settings.FASTAPI_DIR) / file_path
        elif file_path.startswith('applib/merged/'):
            # Path relative to fastapi directory
            full_path = Path(settings.FASTAPI_DIR) / file_path
        else:
            # Path relative to JSON_BASE_PATH
            full_path = JSON_BASE_PATH / file_path

        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"JSON file not found: {full_path}")
            return None
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {e}")
        return None


def extract_text_from_json(json_data: Dict) -> str:
    """JSON 데이터에서 검색용 텍스트 추출"""
    text_parts = []

    # 문서 정보 추출
    doc_info = json_data.get('문서정보', {})
    if doc_info:
        text_parts.append(doc_info.get('규정명', ''))
        text_parts.append(doc_info.get('담당부서', ''))
        if '관련기준' in doc_info:
            text_parts.extend(doc_info.get('관련기준', []))

    # 조문 내용 추출
    articles = json_data.get('조문내용', [])
    for article in articles:
        content = article.get('내용', '')
        if content:
            text_parts.append(content)

    # 모든 텍스트를 공백으로 연결
    return ' '.join(text_parts)


@router.post("/reindex-all")
async def reindex_all_regulations(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """모든 규정 문서 재색인"""
    try:
        db_manager = get_db_connection()
        indexed_count = 0
        error_count = 0
        errors = []

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 모든 규정 목록 가져오기 (현행만) - wzcontent_path 조건 제거
                cur.execute("""
                    SELECT wzruleseq, wzname, wzcontent_path, wzpubno
                    FROM wz_rule
                    WHERE wzNewFlag = '현행'
                    ORDER BY wzruleseq
                """)

                rules = cur.fetchall()
                total_count = len(rules)

                logger.info(f"Starting reindex for {total_count} regulations")

                for rule_id, rule_name, content_path, pub_no in rules:
                    try:
                        # 상태 업데이트 - 색인 중
                        cur.execute("""
                            UPDATE wz_rule
                            SET index_status = 'indexing'
                            WHERE wzruleseq = %s
                        """, (rule_id,))

                        json_data = None
                        found_path = None

                        # JSON 파일 읽기 시도
                        if content_path and content_path.strip():
                            # 경로가 있으면 해당 경로에서 읽기 시도
                            json_data = read_json_file(content_path)
                            found_path = content_path

                        # 경로가 없거나 파일을 찾지 못한 경우, 자동으로 찾기
                        if not json_data:
                            auto_path = find_json_file_for_rule(rule_name, pub_no)
                            if auto_path:
                                json_data = read_json_file(str(auto_path))
                                found_path = str(auto_path)

                                # DB에 경로 업데이트
                                cur.execute("""
                                    UPDATE wz_rule
                                    SET wzcontent_path = %s
                                    WHERE wzruleseq = %s
                                """, (found_path, rule_id))
                                logger.info(f"Auto-matched JSON for '{rule_name}': {found_path}")

                        if json_data:
                            # 텍스트 추출
                            content_text = extract_text_from_json(json_data)

                            # DB 업데이트
                            cur.execute("""
                                UPDATE wz_rule
                                SET content_text = %s,
                                    indexed_at = %s,
                                    index_status = 'completed'
                                WHERE wzruleseq = %s
                            """, (content_text, datetime.now(), rule_id))

                            indexed_count += 1
                            logger.debug(f"Indexed: {rule_name}")
                        else:
                            # JSON 파일 없음
                            cur.execute("""
                                UPDATE wz_rule
                                SET index_status = 'error'
                                WHERE wzruleseq = %s
                            """, (rule_id,))

                            error_count += 1
                            errors.append({
                                'rule_id': rule_id,
                                'rule_name': rule_name,
                                'error': 'JSON file not found'
                            })

                    except Exception as e:
                        error_count += 1
                        errors.append({
                            'rule_id': rule_id,
                            'rule_name': rule_name,
                            'error': str(e)
                        })

                        # 에러 상태 업데이트
                        cur.execute("""
                            UPDATE wz_rule
                            SET index_status = 'error'
                            WHERE wzruleseq = %s
                        """, (rule_id,))

                        logger.error(f"Error indexing rule {rule_id}: {e}")

                conn.commit()

                return {
                    "success": True,
                    "message": f"Reindexing completed",
                    "total": total_count,
                    "indexed": indexed_count,
                    "errors": error_count,
                    "error_details": errors[:10]  # 처음 10개 에러만 반환
                }

    except Exception as e:
        logger.error(f"Error in reindex_all: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_index_status(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """색인 상태 조회"""
    try:
        db_manager = get_db_connection()

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 전체 통계
                cur.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN index_status = 'completed' THEN 1 END) as indexed,
                        COUNT(CASE WHEN index_status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN index_status = 'error' THEN 1 END) as errors,
                        MAX(indexed_at) as last_indexed
                    FROM wz_rule
                    WHERE wzNewFlag = '현행'
                """)

                stats = cur.fetchone()

                # 색인된 문서 크기
                cur.execute("""
                    SELECT
                        SUM(LENGTH(content_text)) as total_size,
                        AVG(LENGTH(content_text)) as avg_size
                    FROM wz_rule
                    WHERE index_status = 'completed'
                """)

                size_stats = cur.fetchone()

                return {
                    "success": True,
                    "stats": {
                        "total_documents": stats[0] or 0,
                        "indexed_documents": stats[1] or 0,
                        "pending_documents": stats[2] or 0,
                        "error_documents": stats[3] or 0,
                        "last_indexed_at": stats[4].isoformat() if stats[4] else None,
                        "total_size_bytes": size_stats[0] or 0,
                        "avg_size_bytes": int(size_stats[1]) if size_stats[1] else 0,
                        "index_percentage": round((stats[1] or 0) / (stats[0] or 1) * 100, 1)
                    }
                }

    except Exception as e:
        logger.error(f"Error getting index status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query")
async def search_regulations(
    q: str = Query(..., description="검색어"),
    department: Optional[str] = Query(None, description="부서 필터"),
    classification: Optional[str] = Query(None, description="분류 필터"),
    limit: int = Query(20, description="결과 수 제한"),
    offset: int = Query(0, description="페이지 오프셋"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """규정 검색"""
    try:
        if not q or len(q.strip()) < 2:
            raise HTTPException(status_code=400, detail="검색어는 2자 이상 입력해주세요")

        db_manager = get_db_connection()

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 검색 쿼리 구성
                query_parts = []
                params = []

                # 기본 검색 조건 - 제목 또는 내용에서 검색
                search_pattern = f'%{q}%'
                query_parts.append("""
                    SELECT
                        wzruleseq,
                        wzname,
                        wzmgrdptnm,
                        wzpubno,
                        wzestabdate,
                        wzexecdate,
                        SUBSTRING(content_text, 1, 200) as snippet,
                        CASE
                            WHEN wzname ILIKE %s THEN 2
                            WHEN content_text ILIKE %s THEN 1
                            ELSE 0
                        END as relevance
                    FROM wz_rule
                    WHERE wzNewFlag = '현행'
                    AND index_status = 'completed'
                    AND (wzname ILIKE %s OR content_text ILIKE %s)
                """)
                params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

                # 부서 필터
                if department:
                    query_parts.append("AND wzmgrdptnm = %s")
                    params.append(department)

                # 분류 필터
                if classification:
                    query_parts.append("AND wzpubno LIKE %s")
                    params.append(f'{classification}.%')

                # 정렬 및 페이징
                query_parts.append("ORDER BY relevance DESC, wzname")
                query_parts.append("LIMIT %s OFFSET %s")
                params.extend([limit, offset])

                full_query = ' '.join(query_parts)
                cur.execute(full_query, params)

                results = cur.fetchall()

                # 전체 결과 수 조회
                count_query = """
                    SELECT COUNT(*)
                    FROM wz_rule
                    WHERE wzNewFlag = '현행'
                    AND index_status = 'completed'
                    AND (wzname ILIKE %s OR content_text ILIKE %s)
                """
                count_params = [search_pattern, search_pattern]

                if department:
                    count_query += " AND wzmgrdptnm = %s"
                    count_params.append(department)

                if classification:
                    count_query += " AND wzpubno LIKE %s"
                    count_params.append(f'{classification}.%')

                cur.execute(count_query, count_params)
                total_count = cur.fetchone()[0]

                # 결과 포맷팅
                search_results = []
                for row in results:
                    search_results.append({
                        'rule_id': row[0],
                        'title': row[1],
                        'department': row[2],
                        'classification': row[3],
                        'established_date': row[4],
                        'effective_date': row[5],
                        'snippet': row[6],
                        'relevance': row[7]
                    })

                return {
                    "success": True,
                    "query": q,
                    "total": total_count,
                    "results": search_results,
                    "limit": limit,
                    "offset": offset
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_search_stats(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """검색 통계 조회"""
    try:
        db_manager = get_db_connection()

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 부서별 색인 문서 수
                cur.execute("""
                    SELECT
                        wzmgrdptnm,
                        COUNT(*) as count
                    FROM wz_rule
                    WHERE index_status = 'completed'
                    AND wzmgrdptnm IS NOT NULL
                    GROUP BY wzmgrdptnm
                    ORDER BY count DESC
                    LIMIT 10
                """)

                dept_stats = [
                    {"department": row[0], "count": row[1]}
                    for row in cur.fetchall()
                ]

                # 최근 색인된 문서
                cur.execute("""
                    SELECT
                        wzruleseq,
                        wzname,
                        indexed_at
                    FROM wz_rule
                    WHERE index_status = 'completed'
                    AND indexed_at IS NOT NULL
                    ORDER BY indexed_at DESC
                    LIMIT 5
                """)

                recent_indexed = [
                    {
                        "rule_id": row[0],
                        "title": row[1],
                        "indexed_at": row[2].isoformat() if row[2] else None
                    }
                    for row in cur.fetchall()
                ]

                return {
                    "success": True,
                    "department_stats": dept_stats,
                    "recent_indexed": recent_indexed
                }

    except Exception as e:
        logger.error(f"Error getting search stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))