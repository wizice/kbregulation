# -*- coding: utf-8 -*-
"""
API 키 관리 서비스

기능:
- API 키 생성 (SHA-256 해시 저장)
- API 키 검증
- API 키 목록 조회
- API 키 삭제

API 키 형식: kbr_live_<32자 랜덤 문자열>

:copyright: (c) 2025 by wizice.
:license: wizice.com
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import secrets
import hashlib
import string

from .auth_middleware import get_current_user
from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/api-keys",
    tags=["api-keys"]
)

# DB 설정
db_config = {
    'database': settings.DB_NAME,
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD,
    'host': settings.DB_HOST,
    'port': settings.DB_PORT
}

# API 키 Prefix
API_KEY_PREFIX = "kbr_live_"


# ==================== Pydantic 모델 ====================

class CreateApiKeyRequest(BaseModel):
    """API 키 생성 요청"""
    key_name: Optional[str] = Field("", max_length=100, description="키 별명 (예: 테스트용, CI/CD)")


class ApiKeyResponse(BaseModel):
    """API 키 응답"""
    api_key_id: int
    key_name: Optional[str]
    key_prefix: str
    is_active: bool
    last_used_at: Optional[str]
    use_count: int
    created_at: str


class CreateApiKeyResponse(BaseModel):
    """API 키 생성 응답"""
    success: bool
    api_key: str  # 전체 키 (생성 시에만 반환)
    key_prefix: str
    key_name: Optional[str]
    message: str


# ==================== 헬퍼 함수 ====================

def get_db_manager():
    """DB 매니저 인스턴스 반환"""
    return DatabaseConnectionManager(**db_config)


def generate_api_key() -> tuple[str, str, str]:
    """
    새 API 키 생성

    Returns:
        (전체 키, prefix, hash)
    """
    # 32자 랜덤 문자열 생성 (a-z, 0-9)
    alphabet = string.ascii_lowercase + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(32))

    # 전체 키
    full_key = f"{API_KEY_PREFIX}{random_part}"

    # 표시용 prefix (앞 16자)
    key_prefix = f"{API_KEY_PREFIX}{random_part[:8]}..."

    # SHA-256 해시
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    return full_key, key_prefix, key_hash


def hash_api_key(api_key: str) -> str:
    """API 키를 SHA-256 해시로 변환"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """
    API 키 검증

    Args:
        api_key: API 키 문자열

    Returns:
        유효한 경우 사용자 정보, 아니면 None
    """
    if not api_key or not api_key.startswith(API_KEY_PREFIX):
        return None

    try:
        key_hash = hash_api_key(api_key)

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # API 키 조회 및 사용자 정보 가져오기
                cur.execute("""
                    SELECT
                        k.api_key_id,
                        k.users_id,
                        k.username,
                        k.key_name,
                        k.is_active,
                        u.email,
                        u.full_name,
                        u.role,
                        u.departments
                    FROM wz_api_keys k
                    JOIN users u ON k.users_id = u.users_id
                    WHERE k.key_hash = %s AND k.is_active = TRUE
                """, (key_hash,))

                row = cur.fetchone()
                if not row:
                    return None

                (api_key_id, users_id, username, key_name, is_active,
                 email, full_name, role, departments) = row

                # 사용 통계 업데이트 (비동기 처리가 바람직하나 간단히 구현)
                cur.execute("""
                    UPDATE wz_api_keys
                    SET last_used_at = NOW(), use_count = use_count + 1
                    WHERE api_key_id = %s
                """, (api_key_id,))
                conn.commit()

                logger.info(f"[API Key] 인증 성공: user={username}, key_name={key_name}")

                return {
                    'users_id': users_id,
                    'username': username,
                    'email': email,
                    'full_name': full_name,
                    'name': full_name,  # 호환성
                    'role': role,
                    'departments': departments,
                    'auth_type': 'api_key',
                    'api_key_name': key_name
                }

    except Exception as e:
        logger.error(f"[API Key] 검증 오류: {e}")
        return None


# ==================== API 엔드포인트 ====================

@router.post("/create", response_model=CreateApiKeyResponse)
async def create_api_key(
    request_data: CreateApiKeyRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    새 API 키 생성

    로그인한 사용자를 위한 새 API 키를 생성합니다.
    생성된 키는 이 응답에서만 확인 가능하며, 다시 조회할 수 없습니다.
    """
    try:
        users_id = user.get('users_id')
        username = user.get('username', '')

        # API 키 생성
        full_key, key_prefix, key_hash = generate_api_key()

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 기존 키 개수 확인 (제한 설정 가능)
                cur.execute("""
                    SELECT COUNT(*) FROM wz_api_keys
                    WHERE users_id = %s AND is_active = TRUE
                """, (users_id,))
                key_count = cur.fetchone()[0]

                if key_count >= 10:  # 최대 10개 제한
                    raise HTTPException(
                        status_code=400,
                        detail="API 키는 최대 10개까지 생성할 수 있습니다."
                    )

                # API 키 저장
                cur.execute("""
                    INSERT INTO wz_api_keys
                        (users_id, username, key_name, key_prefix, key_hash)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING api_key_id
                """, (
                    users_id,
                    username,
                    request_data.key_name or f"API Key {key_count + 1}",
                    key_prefix,
                    key_hash
                ))

                api_key_id = cur.fetchone()[0]
                conn.commit()

                logger.info(f"[API Key] 키 생성: user={username}, id={api_key_id}")

                return CreateApiKeyResponse(
                    success=True,
                    api_key=full_key,
                    key_prefix=key_prefix,
                    key_name=request_data.key_name,
                    message="API 키가 생성되었습니다. 이 키는 다시 표시되지 않으니 안전하게 보관하세요."
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API Key] 키 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"API 키 생성 실패: {str(e)}")


@router.get("/list")
async def list_api_keys(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    내 API 키 목록 조회

    현재 사용자의 모든 API 키 목록을 반환합니다.
    보안상 키의 prefix만 표시됩니다.
    """
    try:
        users_id = user.get('users_id')

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        api_key_id,
                        key_name,
                        key_prefix,
                        is_active,
                        last_used_at,
                        use_count,
                        created_at
                    FROM wz_api_keys
                    WHERE users_id = %s
                    ORDER BY created_at DESC
                """, (users_id,))

                columns = [
                    'api_key_id', 'key_name', 'key_prefix', 'is_active',
                    'last_used_at', 'use_count', 'created_at'
                ]

                keys = []
                for row in cur.fetchall():
                    item = dict(zip(columns, row))
                    for date_field in ['last_used_at', 'created_at']:
                        if item[date_field]:
                            item[date_field] = item[date_field].isoformat()
                    keys.append(item)

                return {
                    "success": True,
                    "data": keys,
                    "count": len(keys)
                }

    except Exception as e:
        logger.error(f"[API Key] 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="API 키 목록 조회 실패")


@router.delete("/{api_key_id}")
async def delete_api_key(
    api_key_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    API 키 삭제

    지정된 API 키를 비활성화합니다.
    삭제된 키는 즉시 사용 불가능해집니다.
    """
    try:
        users_id = user.get('users_id')

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 소유권 확인 및 삭제
                cur.execute("""
                    UPDATE wz_api_keys
                    SET is_active = FALSE
                    WHERE api_key_id = %s AND users_id = %s
                    RETURNING api_key_id, key_name
                """, (api_key_id, users_id))

                result = cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="API 키를 찾을 수 없거나 삭제 권한이 없습니다."
                    )

                conn.commit()

                logger.info(f"[API Key] 키 삭제: id={api_key_id}, user={user.get('username')}")

                return {
                    "success": True,
                    "message": f"API 키 '{result[1]}'가 삭제되었습니다."
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API Key] 키 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail="API 키 삭제 실패")


@router.post("/{api_key_id}/delete")
async def delete_api_key_post(
    api_key_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    API 키 삭제 (POST 방식)

    DELETE 메서드가 차단된 환경을 위한 대안 엔드포인트입니다.
    지정된 API 키를 비활성화합니다.
    """
    try:
        users_id = user.get('users_id')

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE wz_api_keys
                    SET is_active = FALSE
                    WHERE api_key_id = %s AND users_id = %s
                    RETURNING api_key_id, key_name
                """, (api_key_id, users_id))

                result = cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="API 키를 찾을 수 없거나 삭제 권한이 없습니다."
                    )

                conn.commit()

                logger.info(f"[API Key] 키 삭제(POST): id={api_key_id}, user={user.get('username')}")

                return {
                    "success": True,
                    "message": f"API 키 '{result[1]}'가 삭제되었습니다."
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API Key] 키 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail="API 키 삭제 실패")


@router.post("/{api_key_id}/regenerate")
async def regenerate_api_key(
    api_key_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    API 키 재생성

    기존 키를 삭제하고 새 키를 생성합니다.
    이전 키는 즉시 사용 불가능해집니다.
    """
    try:
        users_id = user.get('users_id')
        username = user.get('username', '')

        # 새 API 키 생성
        full_key, key_prefix, key_hash = generate_api_key()

        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 기존 키 정보 조회 및 소유권 확인
                cur.execute("""
                    SELECT key_name FROM wz_api_keys
                    WHERE api_key_id = %s AND users_id = %s AND is_active = TRUE
                """, (api_key_id, users_id))

                result = cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="API 키를 찾을 수 없거나 재생성 권한이 없습니다."
                    )

                key_name = result[0]

                # 키 업데이트
                cur.execute("""
                    UPDATE wz_api_keys
                    SET key_prefix = %s,
                        key_hash = %s,
                        last_used_at = NULL,
                        use_count = 0,
                        created_at = NOW()
                    WHERE api_key_id = %s
                """, (key_prefix, key_hash, api_key_id))

                conn.commit()

                logger.info(f"[API Key] 키 재생성: id={api_key_id}, user={username}")

                return {
                    "success": True,
                    "api_key": full_key,
                    "key_prefix": key_prefix,
                    "key_name": key_name,
                    "message": "API 키가 재생성되었습니다. 이 키는 다시 표시되지 않으니 안전하게 보관하세요."
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API Key] 키 재생성 실패: {e}")
        raise HTTPException(status_code=500, detail="API 키 재생성 실패")


@router.get("/usage-guide")
async def get_usage_guide():
    """
    API 키 사용 가이드

    인증 없이 접근 가능한 가이드 정보를 반환합니다.
    """
    return {
        "success": True,
        "data": {
            "key_format": "kbr_live_<32자 랜덤 문자열>",
            "header_format": "Authorization: Bearer <API_KEY>",
            "example_curl": 'curl -H "Authorization: Bearer kbr_live_abc123..." https://kbregulationeditor.wizice.com/api/v1/...',
            "example_python": """
import requests

API_KEY = "kbr_live_abc123..."
headers = {"Authorization": f"Bearer {API_KEY}"}

response = requests.get("https://kbregulationeditor.wizice.com/api/v1/...", headers=headers)
print(response.json())
""",
            "security_tips": [
                "API 키를 환경변수에 저장하세요",
                ".env 파일을 .gitignore에 추가하세요",
                "CI/CD에서는 Secrets 관리 기능을 사용하세요",
                "주기적으로 키를 회전하세요 (예: 3개월마다)"
            ],
            "limits": {
                "max_keys_per_user": 10
            }
        }
    }
