"""
규정별 안내사항 관리 API Router
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from settings import settings

router = APIRouter(prefix="/api/regulation-notices", tags=["regulation-notices"])


def get_db_connection():
    return psycopg2.connect(
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )


def ensure_table():
    """테이블이 없으면 생성"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wz_regulation_notices (
                id SERIAL PRIMARY KEY,
                regulation_code VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                created_by VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_reg_notices_code
            ON wz_regulation_notices(regulation_code)
        """)
        conn.commit()
    finally:
        conn.close()


# 앱 시작 시 테이블 보장
try:
    ensure_table()
except Exception:
    pass


class RegulationNoticeCreate(BaseModel):
    content: str
    created_by: Optional[str] = None


class RegulationNoticeUpdate(BaseModel):
    content: str


class RegulationNoticeResponse(BaseModel):
    id: int
    regulation_code: str
    content: str
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime


@router.get("/{regulation_code}", response_model=List[RegulationNoticeResponse])
async def get_notices(regulation_code: str):
    """규정별 안내사항 목록 조회"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """SELECT id, regulation_code, content, created_by, created_at, updated_at
               FROM wz_regulation_notices
               WHERE regulation_code = %s
               ORDER BY created_at DESC""",
            (regulation_code,)
        )
        return cur.fetchall()
    finally:
        conn.close()


@router.post("/{regulation_code}", response_model=RegulationNoticeResponse)
async def create_notice(regulation_code: str, body: RegulationNoticeCreate):
    """안내사항 생성"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """INSERT INTO wz_regulation_notices (regulation_code, content, created_by)
               VALUES (%s, %s, %s)
               RETURNING id, regulation_code, content, created_by, created_at, updated_at""",
            (regulation_code, body.content, body.created_by)
        )
        conn.commit()
        return cur.fetchone()
    finally:
        conn.close()


@router.put("/{regulation_code}/{notice_id}", response_model=RegulationNoticeResponse)
async def update_notice(regulation_code: str, notice_id: int, body: RegulationNoticeUpdate):
    """안내사항 수정"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """UPDATE wz_regulation_notices
               SET content = %s, updated_at = NOW()
               WHERE id = %s AND regulation_code = %s
               RETURNING id, regulation_code, content, created_by, created_at, updated_at""",
            (body.content, notice_id, regulation_code)
        )
        conn.commit()
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="안내사항을 찾을 수 없습니다.")
        return result
    finally:
        conn.close()


@router.delete("/{regulation_code}/{notice_id}")
async def delete_notice(regulation_code: str, notice_id: int):
    """안내사항 삭제"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM wz_regulation_notices WHERE id = %s AND regulation_code = %s",
            (notice_id, regulation_code)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="안내사항을 찾을 수 없습니다.")
        return {"message": "삭제되었습니다."}
    finally:
        conn.close()
