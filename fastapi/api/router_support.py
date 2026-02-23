"""
지원 페이지 관리 API Router
- 세브란스병원 내규 제개정절차
- 사용방법
- 자주 묻는 질문 (FAQ)
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from settings import settings
from api.auth_middleware import get_current_user
import os
import uuid
import shutil
from pathlib import Path

router = APIRouter(prefix="/api/support", tags=["support"])

# 첨부파일 저장 경로
from settings import settings
UPLOAD_DIR = Path(f"{settings.FASTAPI_DIR}/static/support_attachments")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_db_connection():
    """데이터베이스 연결"""
    return psycopg2.connect(
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )


# Pydantic 모델
class SupportPageResponse(BaseModel):
    page_id: int
    page_type: str  # 'procedure', 'usage', 'faq'
    title: str
    content: str
    order_no: int
    view_count: int
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str]
    is_active: bool
    is_important: Optional[bool] = False
    attachment_path: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_size: Optional[int] = None


class SupportPageUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    order_no: Optional[int] = None
    is_active: Optional[bool] = None


# 지원 페이지 목록 조회 (공개 - 사용자 화면용)
@router.get("/pages/public", response_model=List[SupportPageResponse])
async def get_public_support_pages(
    page_type: Optional[str] = None
):
    """지원 페이지 목록 조회 (공개 - 활성 페이지만)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        where_clauses = ["is_active = true"]
        params = []

        if page_type:
            where_clauses.append("page_type = %s")
            params.append(page_type)

        where_clause = " AND ".join(where_clauses)

        query = f"""
            SELECT
                page_id, page_type, title, content, order_no, view_count,
                created_at, updated_at, updated_by, is_active, is_important,
                attachment_path, attachment_name, attachment_size
            FROM wz_support_pages
            WHERE {where_clause}
            ORDER BY page_type, order_no, page_id DESC
        """

        cur.execute(query, params)
        rows = cur.fetchall()

        cur.close()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch support pages: {str(e)}")


# 지원 페이지 목록 조회 (관리자용)
@router.get("/pages", response_model=List[SupportPageResponse])
async def get_support_pages(
    page_type: Optional[str] = None,
    is_active: Optional[bool] = True,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """지원 페이지 목록 조회 (관리자용)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        where_clauses = []
        params = []

        if page_type:
            where_clauses.append("page_type = %s")
            params.append(page_type)

        if is_active is not None:
            where_clauses.append("is_active = %s")
            params.append(is_active)

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
            SELECT
                page_id, page_type, title, content, order_no, view_count,
                created_at, updated_at, updated_by, is_active, is_important,
                attachment_path, attachment_name, attachment_size
            FROM wz_support_pages
            WHERE {where_clause}
            ORDER BY page_type, order_no, page_id DESC
        """

        cur.execute(query, params)
        rows = cur.fetchall()

        cur.close()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch support pages: {str(e)}")


# 특정 지원 페이지 조회
@router.get("/pages/{page_id}", response_model=SupportPageResponse)
async def get_support_page(page_id: int):
    """특정 지원 페이지 조회"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 조회수 증가
        cur.execute("""
            UPDATE wz_support_pages
            SET view_count = view_count + 1
            WHERE page_id = %s
        """, (page_id,))

        # 페이지 정보 조회
        cur.execute("""
            SELECT
                page_id, page_type, title, content, order_no, view_count,
                created_at, updated_at, updated_by, is_active, is_important,
                attachment_path, attachment_name, attachment_size
            FROM wz_support_pages
            WHERE page_id = %s
        """, (page_id,))

        row = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Support page not found")

        return dict(row)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch support page: {str(e)}")


# 지원 페이지 생성
@router.post("/pages")
async def create_support_page(
    page_type: str = Form(...),  # 'procedure', 'usage', 'faq'
    title: str = Form(...),
    content: str = Form(...),
    order_no: int = Form(0),
    is_active: bool = Form(True),
    is_important: bool = Form(False),
    attachment: Optional[UploadFile] = File(None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """지원 페이지 생성 (관리자 전용)"""
    try:
        # 첨부파일 처리
        attachment_path = None
        attachment_name = None
        attachment_size = None

        if attachment and attachment.filename:
            # 고유한 파일명 생성
            file_ext = os.path.splitext(attachment.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = UPLOAD_DIR / unique_filename

            # 파일 저장
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(attachment.file, buffer)

            attachment_path = str(file_path)
            attachment_name = attachment.filename
            attachment_size = os.path.getsize(file_path)

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO wz_support_pages
            (page_type, title, content, order_no, is_active, is_important, updated_by,
             attachment_path, attachment_name, attachment_size, view_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
            RETURNING page_id, created_at
        """, (page_type, title, content, order_no, is_active, is_important, user.get('username'),
              attachment_path, attachment_name, attachment_size))

        result = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        return {
            "success": True,
            "message": "지원 페이지가 생성되었습니다",
            "page_id": result['page_id'],
            "created_at": result['created_at']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create support page: {str(e)}")


# 지원 페이지 수정
@router.put("/pages/{page_id}")
async def update_support_page(
    page_id: int,
    title: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    order_no: Optional[int] = Form(None),
    is_active: Optional[bool] = Form(None),
    is_important: Optional[bool] = Form(None),
    remove_attachment: bool = Form(False),
    attachment: Optional[UploadFile] = File(None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """지원 페이지 수정 (관리자 전용)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 기존 페이지 정보 조회
        cur.execute("""
            SELECT attachment_path
            FROM wz_support_pages
            WHERE page_id = %s
        """, (page_id,))

        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Support page not found")

        old_attachment_path = row['attachment_path']

        # 업데이트할 필드 구성
        update_fields = []
        params = []

        if title is not None:
            update_fields.append("title = %s")
            params.append(title)

        if content is not None:
            update_fields.append("content = %s")
            params.append(content)

        if order_no is not None:
            update_fields.append("order_no = %s")
            params.append(order_no)

        if is_active is not None:
            update_fields.append("is_active = %s")
            params.append(is_active)

        if is_important is not None:
            update_fields.append("is_important = %s")
            params.append(is_important)

        # 첨부파일 처리
        if remove_attachment and old_attachment_path:
            # 기존 파일 삭제
            if os.path.exists(old_attachment_path):
                os.remove(old_attachment_path)
            update_fields.append("attachment_path = NULL")
            update_fields.append("attachment_name = NULL")
            update_fields.append("attachment_size = NULL")

        if attachment and attachment.filename:
            # 기존 파일 삭제
            if old_attachment_path and os.path.exists(old_attachment_path):
                os.remove(old_attachment_path)

            # 새 파일 저장
            file_ext = os.path.splitext(attachment.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = UPLOAD_DIR / unique_filename

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(attachment.file, buffer)

            update_fields.append("attachment_path = %s")
            params.append(str(file_path))
            update_fields.append("attachment_name = %s")
            params.append(attachment.filename)
            update_fields.append("attachment_size = %s")
            params.append(os.path.getsize(file_path))

        if not update_fields:
            return {"success": True, "message": "변경사항이 없습니다"}

        update_fields.append("updated_by = %s")
        params.append(user.get('username'))
        update_fields.append("updated_at = NOW()")

        params.append(page_id)

        query = f"""
            UPDATE wz_support_pages
            SET {', '.join(update_fields)}
            WHERE page_id = %s
            RETURNING updated_at
        """

        cur.execute(query, params)
        result = cur.fetchone()

        conn.commit()
        cur.close()
        conn.close()

        return {
            "success": True,
            "message": "지원 페이지가 수정되었습니다",
            "updated_at": result['updated_at']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update support page: {str(e)}")


# 지원 페이지 삭제
@router.delete("/pages/{page_id}")
async def delete_support_page(
    page_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """지원 페이지 삭제 (관리자 전용)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 첨부파일 경로 조회
        cur.execute("""
            SELECT attachment_path
            FROM wz_support_pages
            WHERE page_id = %s
        """, (page_id,))

        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Support page not found")

        # 첨부파일 삭제
        if row['attachment_path'] and os.path.exists(row['attachment_path']):
            os.remove(row['attachment_path'])

        # 데이터베이스에서 삭제
        cur.execute("""
            DELETE FROM wz_support_pages
            WHERE page_id = %s
        """, (page_id,))

        conn.commit()
        cur.close()
        conn.close()

        return {
            "success": True,
            "message": "지원 페이지가 삭제되었습니다"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete support page: {str(e)}")


# 첨부파일 다운로드
@router.get("/attachments/{page_id}")
async def download_attachment(page_id: int):
    """첨부파일 다운로드"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT attachment_path, attachment_name
            FROM wz_support_pages
            WHERE page_id = %s
        """, (page_id,))

        row = cur.fetchone()

        cur.close()
        conn.close()

        if not row or not row['attachment_path']:
            raise HTTPException(status_code=404, detail="Attachment not found")

        if not os.path.exists(row['attachment_path']):
            raise HTTPException(status_code=404, detail="Attachment file not found on server")

        return FileResponse(
            path=row['attachment_path'],
            filename=row['attachment_name'],
            media_type='application/octet-stream'
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download attachment: {str(e)}")
