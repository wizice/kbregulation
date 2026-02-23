# -*- coding: utf-8 -*-
"""
    indexing_service.py
    ~~~~~~~~~~~~~~~~~~~

    규정 검색 색인 서비스
    - 자동 색인 (규정 생성/수정 시)
    - 수동 색인 (관리자 요청)
    - 색인 진행 상태 추적
    - 색인 로그 관리

    :copyright: (c) 2025 by wizice.
    :license: wizice.com
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import Dict, Any, Optional, List, Tuple
import json
import os
import logging
from datetime import datetime
from pathlib import Path
import threading
import time
from enum import Enum

from .auth_middleware import get_current_user, require_role
from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/indexing",
    tags=["indexing"],
    responses={404: {"description": "Not found"}},
)

# 색인 상태 열거형
class IndexStatus(str, Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    COMPLETED = "completed"
    ERROR = "error"

# 글로벌 색인 상태
indexing_state = {
    "is_running": False,
    "total": 0,
    "processed": 0,
    "current_item": "",
    "start_time": None,
    "errors": []
}

# 색인 진행 상태 업데이트
indexing_lock = threading.Lock()


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


def read_json_file(file_path: str) -> Optional[Dict]:
    """JSON 파일 읽기"""
    try:
        # 절대 경로인 경우 그대로 사용
        if os.path.isabs(file_path):
            full_path = Path(file_path)
        # www/static/file/로 시작하는 경우 (DB에 저장된 상대 경로)
        elif file_path.startswith('www/static/file/'):
            full_path = Path(settings.BASE_DIR) / file_path
        # static/file/로 시작하는 경우
        elif file_path.startswith('static/file/'):
            full_path = Path(settings.WWW_DIR) / file_path
        # applib/json/로 시작하는 경우
        elif file_path.startswith('applib/json/'):
            full_path = Path(settings.FASTAPI_DIR) / file_path
        # 기타 상대 경로는 여러 위치 시도
        else:
            # 1. www/static/file 경로 시도
            full_path = Path(settings.WWW_STATIC_FILE_DIR) / file_path
            if not full_path.exists():
                # 2. fastapi/applib 경로 시도
                full_path = Path(settings.APPLIB_DIR) / file_path

        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"JSON file not found: {full_path}")
            return None
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {e}")
        return None


def extract_text_from_json(json_data: Dict) -> Dict[str, str]:
    """JSON 데이터에서 제목/본문/부록 텍스트 추출"""
    result = {
        "title_text": "",
        "content_text": "",
        "appendix_text": ""
    }

    try:
        # 제목 텍스트 추출
        doc_info = json_data.get('문서정보', {})
        if doc_info:
            result["title_text"] = doc_info.get('규정명', '')

        # 본문 텍스트 추출
        articles = json_data.get('조문내용', [])
        content_parts = []
        for article in articles:
            content = article.get('내용', '')
            if content:
                content_parts.append(content)
        result["content_text"] = ' '.join(content_parts)

        # 부록 텍스트 추출
        appendices = json_data.get('부록', [])
        appendix_parts = []
        for appendix in appendices:
            appendix_parts.append(appendix.get('부록명', ''))
            appendix_parts.append(appendix.get('내용', ''))
        result["appendix_text"] = ' '.join(appendix_parts)

    except Exception as e:
        logger.error(f"Error extracting text from JSON: {e}")

    return result


def save_indexing_log(
    db_manager: DatabaseConnectionManager,
    rule_id: int,
    rule_name: str,
    status: IndexStatus,
    error_message: str = None,
    indexed_at: datetime = None
):
    """색인 로그 저장"""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO wz_indexing_log
                    (wzruleseq, wzname, index_status, error_message, indexed_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (rule_id, rule_name, status.value, error_message, indexed_at, datetime.now()))
                conn.commit()
    except Exception as e:
        logger.error(f"Error saving indexing log: {e}")


def index_single_regulation(
    db_manager: DatabaseConnectionManager,
    rule_id: int,
    rule_name: str,
    content_path: str
) -> Tuple[bool, str]:
    """단일 규정 색인 처리"""
    try:
        # JSON 파일 읽기
        json_data = read_json_file(content_path)
        if not json_data:
            error_msg = "JSON file not found"
            save_indexing_log(db_manager, rule_id, rule_name, IndexStatus.ERROR, error_msg)
            return False, error_msg

        # 텍스트 추출
        extracted_text = extract_text_from_json(json_data)

        # 데이터베이스 업데이트
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE wz_rule
                    SET
                        content_text = %s,
                        title_text = %s,
                        appendix_text = %s,
                        indexed_at = %s,
                        index_status = %s
                    WHERE wzruleseq = %s
                """, (
                    extracted_text["content_text"],
                    extracted_text["title_text"],
                    extracted_text["appendix_text"],
                    datetime.now(),
                    IndexStatus.COMPLETED.value,
                    rule_id
                ))
                conn.commit()

        # 로그 저장
        save_indexing_log(
            db_manager, rule_id, rule_name,
            IndexStatus.COMPLETED, None, datetime.now()
        )

        logger.info(f"Successfully indexed: {rule_name} (ID: {rule_id})")
        return True, "Success"

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error indexing regulation {rule_id}: {error_msg}")
        save_indexing_log(db_manager, rule_id, rule_name, IndexStatus.ERROR, error_msg)
        return False, error_msg


# ============================================================================
# 자동 색인 (규정 생성/수정 시 트리거)
# ============================================================================

def trigger_auto_indexing(rule_id: int, rule_name: str, content_path: str):
    """규정 생성/수정 시 자동 색인 트리거"""
    try:
        logger.info(f"Auto-indexing triggered for: {rule_name}")
        db_manager = get_db_connection()
        index_single_regulation(db_manager, rule_id, rule_name, content_path)
    except Exception as e:
        logger.error(f"Error in auto-indexing: {e}")


# ============================================================================
# API: 수동 색인 관리
# ============================================================================

@router.post("/manual-index")
async def manual_index_single(
    rule_id: int = Query(..., description="규정 ID"),
    background_tasks: BackgroundTasks = None,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """특정 규정 수동 색인"""
    try:
        db_manager = get_db_connection()

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 규정 정보 조회
                cur.execute("""
                    SELECT wzruleseq, wzname, wzcontent_path, wznewflag
                    FROM wz_rule
                    WHERE wzruleseq = %s
                """, (rule_id,))

                rule = cur.fetchone()
                if not rule:
                    raise HTTPException(status_code=404, detail="Regulation not found")

                rule_id, rule_name, content_path, status = rule

                if not content_path:
                    raise HTTPException(status_code=400, detail="Regulation has no content path")

                # 색인 상태 업데이트
                cur.execute("""
                    UPDATE wz_rule
                    SET index_status = %s
                    WHERE wzruleseq = %s
                """, (IndexStatus.INDEXING.value, rule_id))
                conn.commit()

        # 백그라운드에서 색인 실행
        if background_tasks:
            background_tasks.add_task(index_single_regulation, db_manager, rule_id, rule_name, content_path)

        return {
            "success": True,
            "message": "Indexing started",
            "rule_id": rule_id,
            "rule_name": rule_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manual_index_single: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex-all")
async def reindex_all(
    background_tasks: BackgroundTasks = None,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """모든 규정 재색인"""
    global indexing_state

    with indexing_lock:
        if indexing_state["is_running"]:
            raise HTTPException(status_code=400, detail="Indexing already in progress")

        indexing_state["is_running"] = True
        indexing_state["start_time"] = datetime.now()
        indexing_state["errors"] = []

    try:
        db_manager = get_db_connection()

        # 백그라운드에서 색인 실행
        if background_tasks:
            background_tasks.add_task(_reindex_all_background, db_manager)
        else:
            # 동기 실행 (테스트용)
            _reindex_all_background(db_manager)

        return {
            "success": True,
            "message": "Reindexing started",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        with indexing_lock:
            indexing_state["is_running"] = False
        logger.error(f"Error in reindex_all: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _reindex_all_background(db_manager: DatabaseConnectionManager):
    """백그라운드 재색인 처리"""
    global indexing_state

    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 현행 규정 목록 조회
                cur.execute("""
                    SELECT wzruleseq, wzname, wzcontent_path
                    FROM wz_rule
                    WHERE wznewflag = '현행'
                    AND wzcontent_path IS NOT NULL
                    ORDER BY wzruleseq
                """)

                rules = cur.fetchall()

        with indexing_lock:
            indexing_state["total"] = len(rules)
            indexing_state["processed"] = 0

        indexed_count = 0
        error_count = 0

        for rule_id, rule_name, content_path in rules:
            with indexing_lock:
                indexing_state["current_item"] = f"{rule_name} ({rule_id})"
                indexing_state["processed"] += 1

            success, message = index_single_regulation(
                db_manager, rule_id, rule_name, content_path
            )

            if success:
                indexed_count += 1
            else:
                error_count += 1
                with indexing_lock:
                    indexing_state["errors"].append({
                        "rule_id": rule_id,
                        "rule_name": rule_name,
                        "error": message
                    })

            # 진행 상황 로깅
            progress = (indexing_state["processed"] / indexing_state["total"] * 100)
            if indexing_state["processed"] % 10 == 0:
                logger.info(f"Reindexing progress: {progress:.1f}% ({indexing_state['processed']}/{indexing_state['total']})")

        # 색인 완료
        logger.info(f"Reindexing completed: {indexed_count} indexed, {error_count} errors")

    except Exception as e:
        logger.error(f"Error in background reindexing: {e}")
        with indexing_lock:
            indexing_state["errors"].append({
                "error": str(e),
                "type": "system"
            })

    finally:
        with indexing_lock:
            indexing_state["is_running"] = False


@router.get("/progress")
async def get_indexing_progress(
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """색인 진행 상태 조회"""
    with indexing_lock:
        progress_data = {
            "is_running": indexing_state["is_running"],
            "total": indexing_state["total"],
            "processed": indexing_state["processed"],
            "current_item": indexing_state["current_item"],
            "start_time": indexing_state["start_time"].isoformat() if indexing_state["start_time"] else None,
            "errors": indexing_state["errors"]
        }

    if progress_data["total"] > 0:
        progress_data["progress_percent"] = round(
            (progress_data["processed"] / progress_data["total"]) * 100, 1
        )
    else:
        progress_data["progress_percent"] = 0

    if progress_data["is_running"] and progress_data["start_time"]:
        elapsed_seconds = (datetime.now() - datetime.fromisoformat(progress_data["start_time"])).total_seconds()
        progress_data["elapsed_seconds"] = elapsed_seconds
        if progress_data["processed"] > 0:
            avg_per_item = elapsed_seconds / progress_data["processed"]
            remaining_items = progress_data["total"] - progress_data["processed"]
            progress_data["estimated_remaining_seconds"] = int(avg_per_item * remaining_items)

    return progress_data


# ============================================================================
# API: 색인 로그 조회
# ============================================================================

@router.get("/logs")
async def get_indexing_logs(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(50, ge=1, le=100, description="페이지당 항목 수"),
    status: Optional[str] = Query(None, description="색인 상태 필터"),
    rule_name: Optional[str] = Query(None, description="규정명 검색"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """색인 로그 조회"""
    try:
        db_manager = get_db_connection()
        offset = (page - 1) * limit

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 필터 구성
                where_clauses = []
                params = []

                if status:
                    where_clauses.append("index_status = %s")
                    params.append(status)

                if rule_name:
                    where_clauses.append("wzname ILIKE %s")
                    params.append(f"%{rule_name}%")

                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

                # 전체 개수 조회
                count_query = f"SELECT COUNT(*) FROM wz_indexing_log WHERE {where_sql}"
                cur.execute(count_query, params)
                total_count = cur.fetchone()[0]

                # 로그 조회
                log_query = f"""
                    SELECT
                        log_id,
                        wzruleseq,
                        wzname,
                        index_status,
                        error_message,
                        indexed_at,
                        created_at
                    FROM wz_indexing_log
                    WHERE {where_sql}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])
                cur.execute(log_query, params)
                logs = cur.fetchall()

        # 결과 포맷팅
        log_items = []
        for log in logs:
            log_items.append({
                "log_id": log[0],
                "rule_id": log[1],
                "rule_name": log[2],
                "status": log[3],
                "error_message": log[4],
                "indexed_at": log[5].isoformat() if log[5] else None,
                "created_at": log[6].isoformat() if log[6] else None
            })

        return {
            "success": True,
            "total": total_count,
            "page": page,
            "limit": limit,
            "logs": log_items
        }

    except Exception as e:
        logger.error(f"Error in get_indexing_logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_indexing_stats(
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """색인 통계 조회"""
    try:
        db_manager = get_db_connection()

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 전체 통계
                cur.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN index_status = %s THEN 1 END) as indexed,
                        COUNT(CASE WHEN index_status = %s THEN 1 END) as pending,
                        COUNT(CASE WHEN index_status = %s THEN 1 END) as errors,
                        MAX(indexed_at) as last_indexed
                    FROM wz_rule
                    WHERE wznewflag = '현행'
                """, (IndexStatus.COMPLETED.value, IndexStatus.PENDING.value, IndexStatus.ERROR.value))

                stats = cur.fetchone()

                # 색인된 문서 크기
                cur.execute("""
                    SELECT
                        SUM(LENGTH(COALESCE(title_text, ''))) as title_size,
                        SUM(LENGTH(COALESCE(content_text, ''))) as content_size,
                        SUM(LENGTH(COALESCE(appendix_text, ''))) as appendix_size
                    FROM wz_rule
                    WHERE index_status = %s
                """, (IndexStatus.COMPLETED.value,))

                size_stats = cur.fetchone()

                return {
                    "success": True,
                    "stats": {
                        "total_regulations": stats[0] or 0,
                        "indexed_count": stats[1] or 0,
                        "pending_count": stats[2] or 0,
                        "error_count": stats[3] or 0,
                        "last_indexed_at": stats[4].isoformat() if stats[4] else None,
                        "index_percentage": round((stats[1] or 0) / (stats[0] or 1) * 100, 1),
                        "indexed_size": {
                            "title_bytes": size_stats[0] or 0,
                            "content_bytes": size_stats[1] or 0,
                            "appendix_bytes": size_stats[2] or 0,
                            "total_bytes": (size_stats[0] or 0) + (size_stats[1] or 0) + (size_stats[2] or 0)
                        }
                    }
                }

    except Exception as e:
        logger.error(f"Error in get_indexing_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/logs")
async def clear_indexing_logs(
    keep_days: int = Query(30, ge=1, description="유지할 일수"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """오래된 색인 로그 삭제"""
    try:
        db_manager = get_db_connection()

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM wz_indexing_log
                    WHERE created_at < NOW() - INTERVAL '%s days'
                """, (keep_days,))
                deleted_count = cur.rowcount
                conn.commit()

        return {
            "success": True,
            "message": f"Deleted {deleted_count} old log entries",
            "deleted_count": deleted_count
        }

    except Exception as e:
        logger.error(f"Error in clear_indexing_logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API: 검색 (사용자 인터페이스용)
# ============================================================================

@router.get("/search")
async def search_regulations(
    q: str = Query(..., min_length=1, max_length=200, description="검색어"),
    search_type: str = Query("content", description="검색 타입: title, content, appendix, all"),
    limit: int = Query(50, ge=1, le=200, description="최대 결과 수"),
    page: int = Query(1, ge=1, description="페이지 번호")
):
    """색인된 규정 검색 (사용자 인터페이스용)

    Args:
        q: 검색어
        search_type: 검색 타입 (title, content, appendix, all)
        limit: 최대 결과 수 (기본값: 50)
        page: 페이지 번호 (기본값: 1)

    Returns:
        검색 결과 목록
    """
    try:
        logger.info(f"Search request: q='{q}', search_type='{search_type}', limit={limit}, page={page}")

        db_manager = get_db_connection()
        offset = (page - 1) * limit

        # 검색 타입 검증
        valid_types = ['title', 'content', 'appendix', 'all']
        if search_type not in valid_types:
            logger.warning(f"Invalid search_type: {search_type}")
            raise HTTPException(status_code=400, detail=f"Invalid search_type. Must be one of {valid_types}")

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 검색 쿼리 구성
                search_conditions = []

                if search_type in ['title', 'all']:
                    search_conditions.append(f"(title_text ILIKE %s)")
                if search_type in ['content', 'all']:
                    search_conditions.append(f"(content_text ILIKE %s)")
                if search_type in ['appendix', 'all']:
                    search_conditions.append(f"(appendix_text ILIKE %s)")

                where_clause = " OR ".join(search_conditions)

                # 검색어 패턴 (정확히 일치하거나 포함)
                search_pattern = f"%{q}%"
                search_params = [search_pattern] * len(search_conditions)

                logger.debug(f"Search conditions: {len(search_conditions)} fields, pattern: {search_pattern}")

                # 전체 개수 조회
                count_query = f"""
                    SELECT COUNT(*)
                    FROM wz_rule
                    WHERE wznewflag = '현행'
                    AND index_status = %s
                    AND ({where_clause})
                """
                count_params = [IndexStatus.COMPLETED.value] + search_params
                logger.debug(f"Count query: {count_query}")
                cur.execute(count_query, count_params)
                total_count = cur.fetchone()[0]
                logger.info(f"Total matching records: {total_count}")

                # 검색 결과 조회
                search_query = f"""
                    SELECT
                        wzruleseq,
                        wzname,
                        wzcode,
                        wzcontent_path,
                        title_text,
                        content_text,
                        appendix_text,
                        indexed_at,
                        wzestabdate,
                        wzmodifydate,
                        wzwdept
                    FROM wz_rule
                    WHERE wznewflag = '현행'
                    AND index_status = %s
                    AND ({where_clause})
                    ORDER BY indexed_at DESC NULLS LAST
                    LIMIT %s OFFSET %s
                """
                search_params.extend([limit, offset])
                logger.debug(f"Search query with offset {offset}, limit {limit}")
                cur.execute(search_query, [IndexStatus.COMPLETED.value] + search_params)
                results = cur.fetchall()
                logger.info(f"Retrieved {len(results) if results else 0} results")

        # 결과 포맷팅
        search_results = []
        if results:
            for result in results:
                try:
                    wzruleseq, wzname, wzcode, wzcontent_path, title_text, content_text, appendix_text, indexed_at, wzestabdate, wzmodifydate, wzwdept = result

                    search_results.append({
                        "rule_id": wzruleseq,
                        "rule_name": wzname,
                        "rule_code": wzcode,
                        "content_path": wzcontent_path,
                        "title": title_text,
                        "indexed_at": indexed_at.isoformat() if indexed_at else None,
                        "estab_date": wzestabdate,
                        "modify_date": wzmodifydate,
                        "department": wzwdept,
                        "match_type": search_type
                    })
                except Exception as row_error:
                    logger.error(f"Error processing result row: {row_error}")
                    continue

        logger.info(f"Search completed: {len(search_results)} formatted results")

        return {
            "success": True,
            "query": q,
            "search_type": search_type,
            "total": total_count,
            "page": page,
            "limit": limit,
            "results": search_results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search_regulations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
