"""
편집기 접근 허용 IP 관리 API
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import ipaddress
import logging
import time

from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/admin/allowed-ips",
    tags=["IP 관리"],
)

# --- IP 캐시 ---
_allowed_ips_cache = {"ips": set(), "updated_at": 0}
CACHE_TTL = 300  # 5분


def get_db_connection():
    return psycopg2.connect(
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )


def invalidate_ip_cache():
    """캐시 즉시 무효화"""
    _allowed_ips_cache["updated_at"] = 0


def get_allowed_ips() -> set:
    """허용 IP 목록 조회 (캐시 사용)"""
    now = time.time()
    if now - _allowed_ips_cache["updated_at"] < CACHE_TTL and _allowed_ips_cache["ips"]:
        return _allowed_ips_cache["ips"]

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT ip_address FROM wz_allowed_ips WHERE is_active = true")
        ips = {row[0] for row in cur.fetchall()}
        cur.close()
        conn.close()

        _allowed_ips_cache["ips"] = ips
        _allowed_ips_cache["updated_at"] = now
        return ips
    except Exception as e:
        logger.error(f"허용 IP 조회 실패: {e}")
        return _allowed_ips_cache["ips"]  # 이전 캐시 반환


def get_client_ip(request: Request) -> str:
    """클라이언트 IP 추출 (X-Forwarded-For → X-Real-IP → client.host)"""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


# --- Pydantic 모델 ---
class IpCreateRequest(BaseModel):
    ip_address: str = Field(..., description="IP 주소")
    description: str = Field("", description="설명")

    @validator("ip_address")
    def validate_ip(cls, v):
        v = v.strip()
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"유효하지 않은 IP 주소: {v}")
        return v


class IpUpdateRequest(BaseModel):
    description: Optional[str] = None
    is_active: Optional[bool] = None


# --- API ---
@router.get("/")
async def list_allowed_ips():
    """허용 IP 목록 조회"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, ip_address, description, is_active, created_by,
                   created_at, updated_at
            FROM wz_allowed_ips
            ORDER BY id
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        result = []
        for row in rows:
            item = dict(row)
            if item.get("created_at"):
                item["created_at"] = item["created_at"].isoformat()
            if item.get("updated_at"):
                item["updated_at"] = item["updated_at"].isoformat()
            result.append(item)

        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"IP 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def add_allowed_ip(req: IpCreateRequest, request: Request):
    """허용 IP 추가"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO wz_allowed_ips (ip_address, description, created_by)
            VALUES (%s, %s, %s)
            RETURNING id, ip_address, description, is_active, created_by, created_at
        """, (req.ip_address, req.description, "admin"))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        invalidate_ip_cache()
        logger.info(f"허용 IP 추가: {req.ip_address}")

        item = dict(row)
        if item.get("created_at"):
            item["created_at"] = item["created_at"].isoformat()
        return {"success": True, "data": item}
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail=f"이미 등록된 IP입니다: {req.ip_address}")
    except Exception as e:
        logger.error(f"IP 추가 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{ip_id}")
async def update_allowed_ip(ip_id: int, req: IpUpdateRequest):
    """허용 IP 수정 (설명, 활성 상태)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        updates = []
        params = []
        if req.description is not None:
            updates.append("description = %s")
            params.append(req.description)
        if req.is_active is not None:
            updates.append("is_active = %s")
            params.append(req.is_active)

        if not updates:
            raise HTTPException(status_code=400, detail="수정할 항목이 없습니다")

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(ip_id)

        cur.execute(f"""
            UPDATE wz_allowed_ips SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, ip_address, description, is_active, updated_at
        """, params)
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="IP를 찾을 수 없습니다")

        conn.commit()
        cur.close()
        conn.close()

        invalidate_ip_cache()

        item = dict(row)
        if item.get("updated_at"):
            item["updated_at"] = item["updated_at"].isoformat()
        return {"success": True, "data": item}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"IP 수정 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{ip_id}")
async def delete_allowed_ip(ip_id: int):
    """허용 IP 삭제"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM wz_allowed_ips WHERE id = %s RETURNING ip_address", (ip_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="IP를 찾을 수 없습니다")
        conn.commit()
        cur.close()
        conn.close()

        invalidate_ip_cache()
        logger.info(f"허용 IP 삭제: {row[0]}")

        return {"success": True, "message": f"IP {row[0]} 삭제됨"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"IP 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-ip")
async def get_my_ip(request: Request):
    """현재 요청자의 IP 반환"""
    client_ip = get_client_ip(request)
    allowed_ips = get_allowed_ips()
    return {
        "success": True,
        "ip": client_ip,
        "is_allowed": client_ip in allowed_ips
    }
