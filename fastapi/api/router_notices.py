"""
공지사항 관리 API Router (파일 업로드 포함)
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from settings import settings
import os
import uuid
import shutil

router = APIRouter(prefix="/api/notices", tags=["notices"])

# 첨부파일 저장 경로
UPLOAD_DIR = f"{settings.FASTAPI_DIR}/static/notices_attachments"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
class NoticeResponse(BaseModel):
    notice_id: int
    title: str
    content: str
    is_important: bool
    view_count: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    is_active: bool
    attachment_path: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_size: Optional[int] = None


class NoticeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_important: Optional[bool] = None
    is_active: Optional[bool] = None


# 공지사항 목록 조회
@router.get("/", response_model=List[NoticeResponse])
async def get_notices(
    is_active: Optional[bool] = True,
    limit: int = 100,
    offset: int = 0
):
    """공지사항 목록 조회"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        where_clause = ""
        params = []

        if is_active is not None:
            where_clause = "WHERE is_active = %s"
            params.append(is_active)

        query = f"""
            SELECT
                notice_id, title, content, is_important, view_count,
                created_at, updated_at, created_by, is_active,
                attachment_path, attachment_name, attachment_size
            FROM notices
            {where_clause}
            ORDER BY is_important DESC, created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        notices = [dict(row) for row in rows]

        cur.close()
        conn.close()
        return notices

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공지사항 조회 실패: {str(e)}")


# 공지사항 상세 조회
@router.get("/{notice_id}", response_model=NoticeResponse)
async def get_notice(notice_id: int):
    """공지사항 상세 조회 및 조회수 증가"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 조회수 증가
        cur.execute(
            "UPDATE notices SET view_count = view_count + 1 WHERE notice_id = %s",
            (notice_id,)
        )

        # 공지사항 조회
        cur.execute(
            """
            SELECT
                notice_id, title, content, is_important, view_count,
                created_at, updated_at, created_by, is_active,
                attachment_path, attachment_name, attachment_size
            FROM notices
            WHERE notice_id = %s
            """,
            (notice_id,)
        )
        row = cur.fetchone()

        if not row:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다")

        notice = dict(row)

        conn.commit()
        cur.close()
        conn.close()
        return notice

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공지사항 조회 실패: {str(e)}")


# 공지사항 등록 (파일 업로드 포함)
@router.post("/", response_model=NoticeResponse)
async def create_notice(
    title: str = Form(...),
    content: str = Form(...),
    is_important: bool = Form(False),
    created_by: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """공지사항 등록 (파일 첨부 가능)"""
    try:
        attachment_path = None
        attachment_name = None
        attachment_size = None

        # 파일 업로드 처리
        if file and file.filename:
            # 파일명 생성 (UUID + 원본 파일명)
            file_ext = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)

            # 파일 저장
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # 파일 크기 확인
            file_size = os.path.getsize(file_path)

            attachment_path = f"/static/notices_attachments/{unique_filename}"
            attachment_name = file.filename
            attachment_size = file_size

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            INSERT INTO notices (
                title, content, is_important, created_by,
                attachment_path, attachment_name, attachment_size
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING notice_id, title, content, is_important, view_count,
                      created_at, updated_at, created_by, is_active,
                      attachment_path, attachment_name, attachment_size
            """,
            (title, content, is_important, created_by,
             attachment_path, attachment_name, attachment_size)
        )
        row = cur.fetchone()
        new_notice = dict(row)

        conn.commit()
        cur.close()
        conn.close()
        return new_notice

    except Exception as e:
        # 오류 발생 시 업로드된 파일 삭제
        if attachment_path and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"공지사항 등록 실패: {str(e)}")


# 공지사항 수정 (파일 업로드 포함)
@router.put("/{notice_id}", response_model=NoticeResponse)
async def update_notice(
    notice_id: int,
    title: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    is_important: Optional[bool] = Form(None),
    is_active: Optional[bool] = Form(None),
    file: Optional[UploadFile] = File(None),
    remove_attachment: bool = Form(False)
):
    """공지사항 수정 (파일 첨부 가능)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 기존 공지사항 조회
        cur.execute(
            "SELECT attachment_path FROM notices WHERE notice_id = %s",
            (notice_id,)
        )
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다")

        old_attachment_path = existing['attachment_path']

        update_fields = []
        params = []

        if title is not None:
            update_fields.append("title = %s")
            params.append(title)

        if content is not None:
            update_fields.append("content = %s")
            params.append(content)

        if is_important is not None:
            update_fields.append("is_important = %s")
            params.append(is_important)

        if is_active is not None:
            update_fields.append("is_active = %s")
            params.append(is_active)

        # 첨부파일 삭제 요청
        if remove_attachment and old_attachment_path:
            old_file_path = os.path.join(settings.FASTAPI_DIR, old_attachment_path.lstrip('/'))
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            update_fields.extend(["attachment_path = NULL", "attachment_name = NULL", "attachment_size = NULL"])

        # 새 파일 업로드
        elif file and file.filename:
            # 기존 파일 삭제
            if old_attachment_path:
                old_file_path = os.path.join(settings.FASTAPI_DIR, old_attachment_path.lstrip('/'))
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)

            # 새 파일 저장
            file_ext = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_size = os.path.getsize(file_path)

            attachment_path = f"/static/notices_attachments/{unique_filename}"
            update_fields.extend([
                "attachment_path = %s",
                "attachment_name = %s",
                "attachment_size = %s"
            ])
            params.extend([attachment_path, file.filename, file_size])

        if not update_fields:
            raise HTTPException(status_code=400, detail="수정할 내용이 없습니다")

        params.append(notice_id)

        query = f"""
            UPDATE notices
            SET {", ".join(update_fields)}
            WHERE notice_id = %s
            RETURNING notice_id, title, content, is_important, view_count,
                      created_at, updated_at, created_by, is_active,
                      attachment_path, attachment_name, attachment_size
        """

        cur.execute(query, tuple(params))
        row = cur.fetchone()

        if not row:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다")

        updated_notice = dict(row)

        conn.commit()
        cur.close()
        conn.close()
        return updated_notice

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공지사항 수정 실패: {str(e)}")


# 공지사항 삭제
@router.delete("/{notice_id}")
async def delete_notice(notice_id: int, permanent: bool = False):
    """공지사항 삭제"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 첨부파일 확인
        cur.execute(
            "SELECT attachment_path FROM notices WHERE notice_id = %s",
            (notice_id,)
        )
        notice = cur.fetchone()

        if permanent:
            # 물리적 삭제 시 첨부파일도 삭제
            if notice and notice['attachment_path']:
                file_path = os.path.join(settings.FASTAPI_DIR, notice['attachment_path'].lstrip('/'))
                if os.path.exists(file_path):
                    os.remove(file_path)

            cur.execute(
                "DELETE FROM notices WHERE notice_id = %s RETURNING notice_id",
                (notice_id,)
            )
        else:
            cur.execute(
                "UPDATE notices SET is_active = FALSE WHERE notice_id = %s RETURNING notice_id",
                (notice_id,)
            )

        row = cur.fetchone()

        if not row:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다")

        conn.commit()
        cur.close()
        conn.close()

        return {"message": "공지사항이 삭제되었습니다", "notice_id": notice_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공지사항 삭제 실패: {str(e)}")


# 첨부파일 다운로드
@router.get("/download/{notice_id}")
async def download_attachment(notice_id: int):
    """첨부파일 다운로드"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            "SELECT attachment_path, attachment_name FROM notices WHERE notice_id = %s",
            (notice_id,)
        )
        row = cur.fetchone()

        cur.close()
        conn.close()

        if not row or not row['attachment_path']:
            raise HTTPException(status_code=404, detail="첨부파일이 없습니다")

        file_path = os.path.join(settings.FASTAPI_DIR, row['attachment_path'].lstrip('/'))

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

        return FileResponse(
            path=file_path,
            filename=row['attachment_name'],
            media_type='application/octet-stream'
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 다운로드 실패: {str(e)}")


# 공지사항 통계
@router.get("/stats/summary")
async def get_notices_stats():
    """공지사항 통계 조회"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active,
                COUNT(CASE WHEN is_important = TRUE AND is_active = TRUE THEN 1 END) as important,
                SUM(view_count) as total_views
            FROM notices
        """)
        row = cur.fetchone()

        stats = {
            "total": row[0],
            "active": row[1],
            "important": row[2],
            "total_views": row[3] or 0
        }

        cur.close()
        conn.close()
        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")
