# -*- coding: utf-8 -*-
"""
router_synonyms.py
~~~~~~~~~~~~~~~~~~

검색 엔진 유사어(Synonym) 관리 API

엔드포인트:
- GET    /api/synonyms              : 유사어 목록 조회
- GET    /api/synonyms/{id}         : 유사어 상세 조회
- POST   /api/synonyms              : 유사어 등록
- PUT    /api/synonyms/{id}         : 유사어 수정
- DELETE /api/synonyms/{id}         : 유사어 삭제
- GET    /api/synonyms/export/json  : JSON 형식으로 내보내기 (ES용)
- GET    /api/synonyms/expand       : 검색어 유사어 확장
- POST   /api/synonyms/validate     : JSON 데이터 검증

:copyright: (c) 2025 by wizice.
:license: wizice.com
"""

from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import re
import logging
import os

from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)

# 유사어 JSON 파일 저장 경로
SYNONYMS_EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "applib", "synonyms")

router = APIRouter(prefix="/api/synonyms", tags=["synonyms"])


def get_db_connection():
    """데이터베이스 연결"""
    return psycopg2.connect(
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )


# ============================================================================
# Pydantic 모델
# ============================================================================

class SynonymCreate(BaseModel):
    """유사어 생성 모델"""
    group_name: str = Field(..., min_length=1, max_length=100, description="유사어 그룹명")
    synonyms: List[str] = Field(..., min_items=1, description="유사어 목록")
    description: Optional[str] = Field(None, max_length=500, description="그룹 설명")
    is_active: bool = Field(True, description="활성화 여부")
    priority: int = Field(0, ge=0, le=1000, description="우선순위")

    @validator('synonyms')
    def validate_synonyms(cls, v):
        # 빈 문자열 제거 및 중복 제거
        cleaned = list(set([s.strip() for s in v if s and s.strip()]))
        if len(cleaned) < 1:
            raise ValueError('유사어는 최소 1개 이상 입력해야 합니다.')
        return cleaned

    @validator('group_name')
    def validate_group_name(cls, v):
        if not v or not v.strip():
            raise ValueError('그룹명은 필수입니다.')
        return v.strip()


class SynonymUpdate(BaseModel):
    """유사어 수정 모델"""
    group_name: Optional[str] = Field(None, min_length=1, max_length=100)
    synonyms: Optional[List[str]] = Field(None, min_items=1)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)

    @validator('synonyms')
    def validate_synonyms(cls, v):
        if v is None:
            return v
        cleaned = list(set([s.strip() for s in v if s and s.strip()]))
        if len(cleaned) < 1:
            raise ValueError('유사어는 최소 1개 이상 입력해야 합니다.')
        return cleaned


class SynonymResponse(BaseModel):
    """유사어 응답 모델"""
    synonym_id: int
    group_name: str
    synonyms: List[str]
    description: Optional[str]
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]


class SynonymValidateRequest(BaseModel):
    """JSON 검증 요청 모델"""
    synonyms_data: List[Dict[str, Any]] = Field(..., description="검증할 유사어 데이터")


class SynonymValidateResponse(BaseModel):
    """JSON 검증 응답 모델"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    valid_count: int
    invalid_count: int


# ============================================================================
# API 엔드포인트
# ============================================================================

@router.get("/", response_model=List[SynonymResponse])
async def get_synonyms(
    is_active: Optional[bool] = Query(None, description="활성화 여부 필터"),
    search: Optional[str] = Query(None, description="그룹명 또는 유사어 검색"),
    limit: int = Query(100, ge=1, le=500, description="최대 결과 수"),
    offset: int = Query(0, ge=0, description="시작 위치")
):
    """
    유사어 목록 조회

    - 우선순위 내림차순 정렬
    - 활성화 여부 필터링 가능
    - 그룹명/유사어 검색 가능
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        where_clauses = []
        params = []

        if is_active is not None:
            where_clauses.append("is_active = %s")
            params.append(is_active)

        if search:
            where_clauses.append("(group_name ILIKE %s OR %s = ANY(synonyms))")
            params.append(f"%{search}%")
            params.append(search)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        query = f"""
            SELECT
                synonym_id, group_name, synonyms, description,
                is_active, priority, created_at, updated_at,
                created_by, updated_by
            FROM search_synonyms
            {where_sql}
            ORDER BY priority DESC, group_name ASC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        cur.close()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"유사어 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"유사어 목록 조회 실패: {str(e)}")


@router.get("/stats")
async def get_synonyms_stats():
    """유사어 통계 조회"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_count,
                COUNT(CASE WHEN is_active = FALSE THEN 1 END) as inactive_count,
                SUM(array_length(synonyms, 1)) as total_synonyms
            FROM search_synonyms
        """)
        row = cur.fetchone()

        cur.close()
        conn.close()

        return {
            "total_groups": row[0],
            "active_groups": row[1],
            "inactive_groups": row[2],
            "total_synonyms": row[3] or 0
        }

    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


@router.get("/groups")
async def get_synonym_groups():
    """
    유사어 그룹 목록 조회 (프론트엔드 표시용)

    Returns:
        활성화된 유사어 그룹 목록 (그룹명과 포함된 단어들)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT group_name, synonyms
            FROM synonym_groups
            WHERE is_active = true
            ORDER BY group_name
        """)

        rows = cur.fetchall()
        cur.close()
        conn.close()

        groups = []
        for row in rows:
            groups.append({
                "group_name": row[0],
                "words": row[1] if row[1] else []
            })

        return {
            "success": True,
            "groups": groups,
            "total": len(groups)
        }

    except Exception as e:
        logger.error(f"유사어 그룹 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"유사어 그룹 목록 조회 실패: {str(e)}")


@router.get("/export/json")
async def export_synonyms_json(
    format: str = Query("elasticsearch", description="출력 형식: elasticsearch, solr, array"),
    save_to_server: bool = Query(False, description="서버에 파일 저장 여부")
):
    """
    유사어를 JSON 형식으로 내보내기 (검색 엔진용)

    형식:
    - elasticsearch: ES synonym filter 형식
    - solr: Solr synonym 형식
    - array: 단순 배열 형식

    save_to_server=True 시 /fastapi/applib/synonyms/ 에 파일 저장
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT group_name, synonyms
            FROM search_synonyms
            WHERE is_active = TRUE
            ORDER BY priority DESC
        """)
        rows = cur.fetchall()

        cur.close()
        conn.close()

        result = None

        if format == "elasticsearch":
            # Elasticsearch synonym filter 형식
            # "환자, 피검자, 수진자" 형태
            synonyms_list = []
            for row in rows:
                synonyms_list.append(", ".join(row['synonyms']))

            result = {
                "format": "elasticsearch",
                "synonyms": synonyms_list,
                "count": len(synonyms_list),
                "config_example": {
                    "settings": {
                        "analysis": {
                            "filter": {
                                "synonym_filter": {
                                    "type": "synonym",
                                    "synonyms": synonyms_list
                                }
                            }
                        }
                    }
                }
            }

        elif format == "solr":
            # Solr synonym 형식
            # "환자, 피검자, 수진자 => 환자"
            synonyms_list = []
            for row in rows:
                main_word = row['group_name']
                all_words = ", ".join(row['synonyms'])
                synonyms_list.append(f"{all_words} => {main_word}")

            result = {
                "format": "solr",
                "synonyms": synonyms_list,
                "count": len(synonyms_list)
            }

        else:  # array
            # 단순 배열 형식
            synonyms_dict = {}
            for row in rows:
                synonyms_dict[row['group_name']] = row['synonyms']

            result = {
                "format": "array",
                "synonyms": synonyms_dict,
                "count": len(synonyms_dict)
            }

        # 서버에 파일 저장
        if save_to_server:
            os.makedirs(SYNONYMS_EXPORT_DIR, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"synonyms_{format}_{timestamp}.json"
            filepath = os.path.join(SYNONYMS_EXPORT_DIR, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            # 최신 파일도 별도 저장 (검색엔진에서 참조용)
            latest_filename = f"synonyms_{format}_latest.json"
            latest_filepath = os.path.join(SYNONYMS_EXPORT_DIR, latest_filename)

            with open(latest_filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            logger.info(f"유사어 JSON 저장: {filepath}")

            result["saved_file"] = filepath
            result["latest_file"] = latest_filepath

        return result

    except Exception as e:
        logger.error(f"유사어 내보내기 실패: {e}")
        raise HTTPException(status_code=500, detail=f"유사어 내보내기 실패: {str(e)}")


@router.get("/expand")
async def expand_search_query(
    q: str = Query(..., min_length=1, description="검색어")
):
    """
    검색어에 대한 유사어 확장

    입력된 검색어가 유사어 그룹에 포함되어 있으면
    해당 그룹의 모든 유사어를 반환
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 검색어가 포함된 유사어 그룹 찾기
        cur.execute("""
            SELECT group_name, synonyms
            FROM search_synonyms
            WHERE is_active = TRUE
            AND %s = ANY(synonyms)
            ORDER BY priority DESC
        """, (q,))

        rows = cur.fetchall()

        cur.close()
        conn.close()

        if not rows:
            return {
                "original_query": q,
                "expanded": False,
                "synonyms": [q],
                "groups": []
            }

        # 모든 관련 유사어 수집
        all_synonyms = set([q])
        groups = []

        for row in rows:
            all_synonyms.update(row['synonyms'])
            groups.append({
                "group_name": row['group_name'],
                "synonyms": row['synonyms']
            })

        return {
            "original_query": q,
            "expanded": True,
            "synonyms": list(all_synonyms),
            "groups": groups
        }

    except Exception as e:
        logger.error(f"유사어 확장 실패: {e}")
        raise HTTPException(status_code=500, detail=f"유사어 확장 실패: {str(e)}")


@router.get("/{synonym_id}", response_model=SynonymResponse)
async def get_synonym(synonym_id: int = Path(..., description="유사어 ID")):
    """유사어 상세 조회"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                synonym_id, group_name, synonyms, description,
                is_active, priority, created_at, updated_at,
                created_by, updated_by
            FROM search_synonyms
            WHERE synonym_id = %s
        """, (synonym_id,))

        row = cur.fetchone()

        cur.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="유사어를 찾을 수 없습니다")

        return dict(row)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"유사어 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"유사어 조회 실패: {str(e)}")


@router.post("/", response_model=SynonymResponse)
async def create_synonym(data: SynonymCreate, created_by: str = Query("admin", description="생성자")):
    """
    유사어 등록

    - group_name: 유사어 그룹명 (대표 단어)
    - synonyms: 유사어 목록 (배열)
    - description: 그룹 설명
    - is_active: 활성화 여부
    - priority: 우선순위 (0-1000)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 중복 체크
        cur.execute("""
            SELECT synonym_id FROM search_synonyms
            WHERE group_name = %s
        """, (data.group_name,))

        if cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=400, detail=f"'{data.group_name}' 그룹명이 이미 존재합니다")

        cur.execute("""
            INSERT INTO search_synonyms
            (group_name, synonyms, description, is_active, priority, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING
                synonym_id, group_name, synonyms, description,
                is_active, priority, created_at, updated_at,
                created_by, updated_by
        """, (
            data.group_name,
            data.synonyms,
            data.description,
            data.is_active,
            data.priority,
            created_by
        ))

        row = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"유사어 생성: {data.group_name} (ID: {row['synonym_id']})")

        return dict(row)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"유사어 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"유사어 생성 실패: {str(e)}")


@router.put("/{synonym_id}", response_model=SynonymResponse)
async def update_synonym(
    synonym_id: int = Path(..., description="유사어 ID"),
    data: SynonymUpdate = None,
    updated_by: str = Query("admin", description="수정자")
):
    """유사어 수정"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 존재 확인
        cur.execute("SELECT synonym_id FROM search_synonyms WHERE synonym_id = %s", (synonym_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="유사어를 찾을 수 없습니다")

        # 동적 업데이트 쿼리 생성
        update_fields = []
        params = []

        if data.group_name is not None:
            # 중복 체크
            cur.execute("""
                SELECT synonym_id FROM search_synonyms
                WHERE group_name = %s AND synonym_id != %s
            """, (data.group_name, synonym_id))
            if cur.fetchone():
                cur.close()
                conn.close()
                raise HTTPException(status_code=400, detail=f"'{data.group_name}' 그룹명이 이미 존재합니다")

            update_fields.append("group_name = %s")
            params.append(data.group_name)

        if data.synonyms is not None:
            update_fields.append("synonyms = %s")
            params.append(data.synonyms)

        if data.description is not None:
            update_fields.append("description = %s")
            params.append(data.description)

        if data.is_active is not None:
            update_fields.append("is_active = %s")
            params.append(data.is_active)

        if data.priority is not None:
            update_fields.append("priority = %s")
            params.append(data.priority)

        if not update_fields:
            raise HTTPException(status_code=400, detail="수정할 내용이 없습니다")

        update_fields.append("updated_by = %s")
        params.append(updated_by)

        params.append(synonym_id)

        query = f"""
            UPDATE search_synonyms
            SET {", ".join(update_fields)}
            WHERE synonym_id = %s
            RETURNING
                synonym_id, group_name, synonyms, description,
                is_active, priority, created_at, updated_at,
                created_by, updated_by
        """

        cur.execute(query, tuple(params))
        row = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"유사어 수정: ID {synonym_id}")

        return dict(row)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"유사어 수정 실패: {e}")
        raise HTTPException(status_code=500, detail=f"유사어 수정 실패: {str(e)}")


@router.delete("/{synonym_id}")
async def delete_synonym(
    synonym_id: int = Path(..., description="유사어 ID"),
    permanent: bool = Query(False, description="물리적 삭제 여부")
):
    """
    유사어 삭제

    - permanent=False: 비활성화 (soft delete)
    - permanent=True: 물리적 삭제 (hard delete)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if permanent:
            cur.execute("""
                DELETE FROM search_synonyms
                WHERE synonym_id = %s
                RETURNING synonym_id
            """, (synonym_id,))
        else:
            cur.execute("""
                UPDATE search_synonyms
                SET is_active = FALSE
                WHERE synonym_id = %s
                RETURNING synonym_id
            """, (synonym_id,))

        row = cur.fetchone()

        if not row:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="유사어를 찾을 수 없습니다")

        conn.commit()
        cur.close()
        conn.close()

        action = "삭제" if permanent else "비활성화"
        logger.info(f"유사어 {action}: ID {synonym_id}")

        return {
            "success": True,
            "message": f"유사어가 {action}되었습니다",
            "synonym_id": synonym_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"유사어 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"유사어 삭제 실패: {str(e)}")


@router.post("/validate", response_model=SynonymValidateResponse)
async def validate_synonyms_json(data: SynonymValidateRequest):
    """
    유사어 JSON 데이터 검증

    입력 형식:
    ```json
    {
        "synonyms_data": [
            {"group_name": "환자", "synonyms": ["환자", "피검자", "수진자"]},
            {"group_name": "의약품", "synonyms": ["의약품", "약품", "약물"]}
        ]
    }
    ```
    """
    errors = []
    warnings = []
    valid_count = 0
    invalid_count = 0

    seen_groups = set()
    seen_synonyms = set()

    for idx, item in enumerate(data.synonyms_data):
        item_errors = []

        # group_name 검증
        group_name = item.get('group_name', '')
        if not group_name or not isinstance(group_name, str):
            item_errors.append(f"[{idx+1}] group_name이 없거나 유효하지 않습니다")
        elif len(group_name) > 100:
            item_errors.append(f"[{idx+1}] group_name이 100자를 초과합니다")
        elif group_name in seen_groups:
            item_errors.append(f"[{idx+1}] 중복된 group_name: '{group_name}'")
        else:
            seen_groups.add(group_name)

        # synonyms 검증
        synonyms = item.get('synonyms', [])
        if not synonyms or not isinstance(synonyms, list):
            item_errors.append(f"[{idx+1}] synonyms가 없거나 배열이 아닙니다")
        else:
            # 빈 문자열 체크
            valid_synonyms = [s for s in synonyms if s and isinstance(s, str) and s.strip()]
            if len(valid_synonyms) < 1:
                item_errors.append(f"[{idx+1}] 유효한 유사어가 1개 이상 필요합니다")

            # 중복 유사어 체크
            for syn in valid_synonyms:
                if syn in seen_synonyms:
                    warnings.append(f"[{idx+1}] 다른 그룹과 중복된 유사어: '{syn}'")
                seen_synonyms.add(syn)

        # priority 검증 (선택)
        priority = item.get('priority', 0)
        if priority and (not isinstance(priority, int) or priority < 0 or priority > 1000):
            item_errors.append(f"[{idx+1}] priority는 0-1000 사이의 정수여야 합니다")

        if item_errors:
            errors.extend(item_errors)
            invalid_count += 1
        else:
            valid_count += 1

    return SynonymValidateResponse(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        valid_count=valid_count,
        invalid_count=invalid_count
    )


@router.post("/import")
async def import_synonyms_json(
    data: SynonymValidateRequest,
    skip_duplicates: bool = Query(True, description="중복 시 건너뛰기"),
    created_by: str = Query("admin", description="생성자")
):
    """
    유사어 JSON 데이터 일괄 가져오기

    입력 형식:
    ```json
    {
        "synonyms_data": [
            {"group_name": "환자", "synonyms": ["환자", "피검자"], "priority": 100},
            {"group_name": "의약품", "synonyms": ["의약품", "약품"], "priority": 90}
        ]
    }
    ```
    """
    try:
        # 먼저 검증
        validation = await validate_synonyms_json(data)
        if not validation.is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "데이터 검증 실패",
                    "errors": validation.errors
                }
            )

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        imported = []
        skipped = []

        for item in data.synonyms_data:
            group_name = item.get('group_name', '').strip()
            synonyms = [s.strip() for s in item.get('synonyms', []) if s and s.strip()]
            description = item.get('description', '')
            priority = item.get('priority', 0)
            is_active = item.get('is_active', True)

            # 중복 체크
            cur.execute(
                "SELECT synonym_id FROM search_synonyms WHERE group_name = %s",
                (group_name,)
            )

            if cur.fetchone():
                if skip_duplicates:
                    skipped.append(group_name)
                    continue
                else:
                    # 업데이트
                    cur.execute("""
                        UPDATE search_synonyms
                        SET synonyms = %s, description = %s, priority = %s,
                            is_active = %s, updated_by = %s
                        WHERE group_name = %s
                        RETURNING synonym_id
                    """, (synonyms, description, priority, is_active, created_by, group_name))
            else:
                # 새로 삽입
                cur.execute("""
                    INSERT INTO search_synonyms
                    (group_name, synonyms, description, priority, is_active, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING synonym_id
                """, (group_name, synonyms, description, priority, is_active, created_by))

            row = cur.fetchone()
            imported.append({
                "synonym_id": row['synonym_id'],
                "group_name": group_name
            })

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"유사어 일괄 가져오기: {len(imported)}개 성공, {len(skipped)}개 건너뜀")

        return {
            "success": True,
            "message": f"{len(imported)}개 가져오기 완료",
            "imported_count": len(imported),
            "skipped_count": len(skipped),
            "imported": imported,
            "skipped": skipped
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"유사어 가져오기 실패: {e}")
        raise HTTPException(status_code=500, detail=f"유사어 가져오기 실패: {str(e)}")
