"""
FAQ 관리 API 라우터
자주 묻는 질문을 관리하는 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .timescaledb_manager_v2 import DatabaseConnectionManager
from .auth_middleware import require_role, get_current_user
from settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/faqs",
    tags=["faqs"],
    responses={404: {"description": "Not found"}},
)

# DB 연결 설정
db_config = {
    "host": settings.DB_HOST,
    "port": settings.DB_PORT,
    "database": settings.DB_NAME,
    "user": settings.DB_USER,
    "password": settings.DB_PASSWORD
}
db_manager = DatabaseConnectionManager(**db_config)


# Pydantic 모델
class FAQCreate(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="질문 내용")
    answer: str = Field(..., min_length=1, description="답변 내용")
    category: str = Field(default="일반", max_length=100, description="카테고리")
    display_order: int = Field(default=0, description="표시 순서")
    is_active: bool = Field(default=True, description="활성화 여부")


class FAQUpdate(BaseModel):
    question: Optional[str] = Field(None, min_length=1, max_length=1000)
    answer: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, max_length=100)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class FAQResponse(BaseModel):
    faq_id: int
    question: str
    answer: str
    category: str
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str


# ================== FAQ 목록 조회 (사용자용 - 인증 불필요) ==================
@router.get("/", response_model=List[FAQResponse])
async def get_faqs(
    is_active: Optional[bool] = Query(True, description="활성화된 FAQ만 조회"),
    category: Optional[str] = Query(None, description="카테고리별 필터"),
    limit: int = Query(50, ge=1, le=100, description="조회 개수")
):
    """
    FAQ 목록 조회 (사용자 화면용)
    - 인증 없이 접근 가능
    - 활성화된 FAQ만 기본 조회
    - display_order 순으로 정렬
    """
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT faq_id, question, answer, category, display_order,
                           is_active, created_at, updated_at, created_by
                    FROM faqs
                    WHERE 1=1
                """
                params = []

                if is_active is not None:
                    query += " AND is_active = %s"
                    params.append(is_active)

                if category:
                    query += " AND category = %s"
                    params.append(category)

                query += " ORDER BY display_order ASC, faq_id ASC LIMIT %s"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                faqs = []
                for row in rows:
                    faqs.append({
                        "faq_id": row[0],
                        "question": row[1],
                        "answer": row[2],
                        "category": row[3],
                        "display_order": row[4],
                        "is_active": row[5],
                        "created_at": row[6],
                        "updated_at": row[7],
                        "created_by": row[8]
                    })

                return faqs

    except Exception as e:
        logger.error(f"FAQ 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="FAQ 목록 조회 중 오류가 발생했습니다")


# ================== FAQ 상세 조회 ==================
@router.get("/{faq_id}", response_model=FAQResponse)
async def get_faq(faq_id: int):
    """FAQ 상세 정보 조회"""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT faq_id, question, answer, category, display_order,
                           is_active, created_at, updated_at, created_by
                    FROM faqs
                    WHERE faq_id = %s
                """, (faq_id,))

                row = cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="FAQ를 찾을 수 없습니다")

                return {
                    "faq_id": row[0],
                    "question": row[1],
                    "answer": row[2],
                    "category": row[3],
                    "display_order": row[4],
                    "is_active": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "created_by": row[8]
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FAQ 상세 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="FAQ 조회 중 오류가 발생했습니다")


# ================== FAQ 생성 (관리자 전용) ==================
@router.post("/", response_model=FAQResponse)
async def create_faq(
    faq_data: FAQCreate,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    새 FAQ 생성 (관리자 전용)
    """
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO faqs (question, answer, category, display_order, is_active, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING faq_id, question, answer, category, display_order,
                              is_active, created_at, updated_at, created_by
                """, (
                    faq_data.question,
                    faq_data.answer,
                    faq_data.category,
                    faq_data.display_order,
                    faq_data.is_active,
                    user.get("username", "관리자")
                ))

                conn.commit()
                row = cursor.fetchone()

                logger.info(f"FAQ 생성 성공: {row[0]} by {user.get('username')}")

                return {
                    "faq_id": row[0],
                    "question": row[1],
                    "answer": row[2],
                    "category": row[3],
                    "display_order": row[4],
                    "is_active": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "created_by": row[8]
                }

    except Exception as e:
        logger.error(f"FAQ 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="FAQ 생성 중 오류가 발생했습니다")


# ================== FAQ 수정 (관리자 전용) ==================
@router.put("/{faq_id}", response_model=FAQResponse)
async def update_faq(
    faq_id: int,
    faq_data: FAQUpdate,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """FAQ 수정 (관리자 전용)"""
    try:
        # 업데이트할 필드 구성
        update_fields = []
        params = []

        if faq_data.question is not None:
            update_fields.append("question = %s")
            params.append(faq_data.question)

        if faq_data.answer is not None:
            update_fields.append("answer = %s")
            params.append(faq_data.answer)

        if faq_data.category is not None:
            update_fields.append("category = %s")
            params.append(faq_data.category)

        if faq_data.display_order is not None:
            update_fields.append("display_order = %s")
            params.append(faq_data.display_order)

        if faq_data.is_active is not None:
            update_fields.append("is_active = %s")
            params.append(faq_data.is_active)

        if not update_fields:
            raise HTTPException(status_code=400, detail="수정할 내용이 없습니다")

        params.append(faq_id)

        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # FAQ 존재 확인
                cursor.execute("SELECT faq_id FROM faqs WHERE faq_id = %s", (faq_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="FAQ를 찾을 수 없습니다")

                # 업데이트 실행
                query = f"""
                    UPDATE faqs
                    SET {', '.join(update_fields)}
                    WHERE faq_id = %s
                    RETURNING faq_id, question, answer, category, display_order,
                              is_active, created_at, updated_at, created_by
                """

                cursor.execute(query, params)
                conn.commit()

                row = cursor.fetchone()

                logger.info(f"FAQ 수정 성공: {faq_id} by {user.get('username')}")

                return {
                    "faq_id": row[0],
                    "question": row[1],
                    "answer": row[2],
                    "category": row[3],
                    "display_order": row[4],
                    "is_active": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "created_by": row[8]
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FAQ 수정 실패: {e}")
        raise HTTPException(status_code=500, detail="FAQ 수정 중 오류가 발생했습니다")


# ================== FAQ 삭제 (관리자 전용) ==================
@router.delete("/{faq_id}")
async def delete_faq(
    faq_id: int,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """FAQ 삭제 (관리자 전용)"""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # FAQ 존재 확인
                cursor.execute("SELECT faq_id FROM faqs WHERE faq_id = %s", (faq_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="FAQ를 찾을 수 없습니다")

                # 삭제 실행
                cursor.execute("DELETE FROM faqs WHERE faq_id = %s", (faq_id,))
                conn.commit()

                logger.info(f"FAQ 삭제 성공: {faq_id} by {user.get('username')}")

                return {"message": "FAQ가 삭제되었습니다", "faq_id": faq_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FAQ 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail="FAQ 삭제 중 오류가 발생했습니다")


# ================== 카테고리 목록 조회 ==================
@router.get("/categories/list")
async def get_categories():
    """FAQ 카테고리 목록 조회"""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT category, COUNT(*) as count
                    FROM faqs
                    WHERE is_active = true
                    GROUP BY category
                    ORDER BY category
                """)

                rows = cursor.fetchall()
                categories = [{"category": row[0], "count": row[1]} for row in rows]

                return categories

    except Exception as e:
        logger.error(f"카테고리 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="카테고리 목록 조회 중 오류가 발생했습니다")
