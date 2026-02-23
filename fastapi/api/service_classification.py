# -*- coding: utf-8 -*-
"""
    service_classification.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    분류(장) 관리 API

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging
from pydantic import BaseModel, field_validator
from .auth_middleware import get_current_user
from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)

# Pydantic 모델
class CategoryCreate(BaseModel):
    chapter_number: int
    name: str

class CategoryUpdate(BaseModel):
    new_name: str

    @field_validator('new_name')
    @classmethod
    def validate_new_name(cls, v):
        if not v or not v.strip():
            raise ValueError('분류명은 비어있을 수 없습니다.')
        if len(v.strip()) < 1:
            raise ValueError('분류명은 최소 1자 이상이어야 합니다.')
        if len(v.strip()) > 200:
            raise ValueError('분류명은 200자를 초과할 수 없습니다.')
        return v.strip()

router = APIRouter(
    prefix="/api/v1/classification",
    tags=["classification"],
    responses={404: {"description": "Not found"}},
)

@router.get("/list")
async def get_classifications(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """분류 목록 조회 (wz_cate 테이블)"""
    try:
        db_config = {
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'host': settings.DB_HOST,
            'port': settings.DB_PORT
        }

        db_manager = DatabaseConnectionManager(**db_config)

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # wz_cate 테이블에서 분류 목록 조회
                cur.execute("""
                    SELECT
                        wzcateseq,
                        wzcatename,
                        wzorder
                    FROM wz_cate
                    WHERE wzvisible = 'Y' OR wzvisible IS NULL
                    ORDER BY wzorder, wzcateseq
                """)

                results = cur.fetchall()

                classifications = []
                for row in results:
                    cate_seq = row[0]

                    # 각 분류의 규정 수 계산 (현행 규정만)
                    cur.execute("""
                        SELECT COUNT(*)
                        FROM wz_rule
                        WHERE wzpubno LIKE %s
                        AND (wzNewFlag = '현행' OR wzNewFlag IS NULL)
                    """, (f'{cate_seq}.%',))

                    count = cur.fetchone()[0]

                    classifications.append({
                        "id": str(cate_seq),
                        "name": row[1].strip() if row[1] else '',
                        "order": row[2],
                        "count": count
                    })

                return {
                    "success": True,
                    "classifications": classifications,
                    "total": len(classifications)
                }

    except Exception as e:
        logger.error(f"Error getting classifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_classification(
    category: CategoryCreate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """새 분류 생성"""
    try:
        db_config = {
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'host': settings.DB_HOST,
            'port': settings.DB_PORT
        }

        db_manager = DatabaseConnectionManager(**db_config)

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 중복 확인
                cur.execute("""
                    SELECT COUNT(*) FROM wz_cate
                    WHERE wzcateseq = %s
                """, (category.chapter_number,))

                if cur.fetchone()[0] > 0:
                    return {
                        "success": False,
                        "error": "duplicate",
                        "message": f"제{category.chapter_number}장이 이미 존재합니다."
                    }

                # 새 분류 삽입
                cur.execute("""
                    INSERT INTO wz_cate (wzcateseq, wzcatename, wzparentseq, wzorder, wzvisible, wzcreatedby, wzmodifiedby)
                    VALUES (%s, %s, NULL, %s, 'Y', %s, %s)
                """, (category.chapter_number, category.name, category.chapter_number, user['username'], user['username']))

                conn.commit()

                return {
                    "success": True,
                    "message": f"제{category.chapter_number}장 '{category.name}'가 추가되었습니다."
                }

    except Exception as e:
        logger.error(f"Error creating classification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update/{cate_seq}")
async def update_classification(
    cate_seq: int,
    category: CategoryUpdate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """분류명 수정"""
    try:
        db_config = {
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'host': settings.DB_HOST,
            'port': settings.DB_PORT
        }

        db_manager = DatabaseConnectionManager(**db_config)

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 분류 존재 확인
                cur.execute("""
                    SELECT wzcatename FROM wz_cate
                    WHERE wzcateseq = %s
                """, (cate_seq,))

                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="분류를 찾을 수 없습니다.")

                old_name = result[0].strip() if result[0] else ''

                # 분류명 업데이트
                cur.execute("""
                    UPDATE wz_cate
                    SET wzcatename = %s, wzmodifiedby = %s
                    WHERE wzcateseq = %s
                """, (category.new_name, user['username'], cate_seq))

                conn.commit()

                return {
                    "success": True,
                    "message": f"제{cate_seq}장이 '{old_name}'에서 '{category.new_name}'로 변경되었습니다."
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating classification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regulations/{cate_seq}")
async def get_regulations_by_category(
    cate_seq: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """특정 분류의 규정 목록 조회"""
    try:
        db_config = {
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'host': settings.DB_HOST,
            'port': settings.DB_PORT
        }

        db_manager = DatabaseConnectionManager(**db_config)

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 분류 존재 확인
                cur.execute("""
                    SELECT wzcatename FROM wz_cate
                    WHERE wzcateseq = %s
                """, (cate_seq,))

                cate_result = cur.fetchone()
                if not cate_result:
                    raise HTTPException(status_code=404, detail="분류를 찾을 수 없습니다.")

                cate_name = cate_result[0].strip() if cate_result[0] else ''

                # 해당 분류의 규정 목록 조회
                cur.execute("""
                    SELECT
                        wzruleseq,
                        wzname,
                        wzpubno,
                        wzFileJson,
                        wzNewFlag,
                        wzmgrdptorgcd,
                        wzmgrdptnm,
                        wzestabdate,
                        wzexecdate,
                        wzlastrevdate
                    FROM wz_rule
                    WHERE wzpubno LIKE %s
                    AND (wzNewFlag = '현행' OR wzNewFlag IS NULL)
                    ORDER BY wzpubno
                """, (f'{cate_seq}.%',))

                results = cur.fetchall()

                regulations = []
                for row in results:
                    regulations.append({
                        "id": row[0],
                        "name": row[1].strip() if row[1] else '',
                        "pubno": row[2].strip() if row[2] else '',
                        "filejson": row[3].strip() if row[3] else '',
                        "status": row[4] if row[4] else '현행',
                        "deptCode": row[5] if row[5] else '',
                        "deptName": row[6].strip() if row[6] else '',
                        "estabDate": row[7] if row[7] else '',
                        "execDate": row[8] if row[8] else '',
                        "lastRevDate": row[9] if row[9] else ''
                    })

                return {
                    "success": True,
                    "categoryId": cate_seq,
                    "categoryName": cate_name,
                    "regulations": regulations,
                    "total": len(regulations)
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting regulations by category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{cate_seq}")
async def delete_classification(
    cate_seq: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """분류 삭제"""
    try:
        db_config = {
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'host': settings.DB_HOST,
            'port': settings.DB_PORT
        }

        db_manager = DatabaseConnectionManager(**db_config)

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 분류 존재 확인
                cur.execute("""
                    SELECT wzcatename FROM wz_cate
                    WHERE wzcateseq = %s
                """, (cate_seq,))

                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="분류를 찾을 수 없습니다.")

                cate_name = result[0].strip() if result[0] else ''

                # 해당 분류에 연결된 규정이 있는지 확인
                cur.execute("""
                    SELECT COUNT(*) FROM wz_rule
                    WHERE wzpubno LIKE %s
                """, (f'{cate_seq}.%',))

                regulation_count = cur.fetchone()[0]
                if regulation_count > 0:
                    return {
                        "success": False,
                        "error": "has_regulations",
                        "message": f"제{cate_seq}장 '{cate_name}'에 {regulation_count}개의 규정이 있어 삭제할 수 없습니다."
                    }

                # 분류 삭제
                cur.execute("""
                    DELETE FROM wz_cate
                    WHERE wzcateseq = %s
                """, (cate_seq,))

                conn.commit()

                return {
                    "success": True,
                    "message": f"제{cate_seq}장 '{cate_name}'가 삭제되었습니다."
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting classification: {e}")
        raise HTTPException(status_code=500, detail=str(e))