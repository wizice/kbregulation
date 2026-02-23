# -*- coding: utf-8 -*-
"""
    auth_middleware
    ~~~~~~~~~~~~~~

    FastAPI 인증 미들웨어 및 의존성

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

import os
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from app_logger import setup_logging, get_logger
from functools import wraps

from .timescaledb_manager_v2 import get_db_manager
from .redis_session_manager import RedisSessionManager
from .query_users_v2 import UsersTable
from .query_user_sessions_v2 import UserSessionsTable
from settings import settings


logger = get_logger(__name__)
# Security scheme 정의
security = HTTPBearer(auto_error=False)

# 전역 변수로 매니저 인스턴스 관리
_redis_manager: Optional[RedisSessionManager] = None
_users_table: Optional[UsersTable] = None
_sessions_table: Optional[UserSessionsTable] = None

def get_redis_manager() -> RedisSessionManager:
    """Redis 세션 매니저 싱글톤 인스턴스"""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisSessionManager(
            host        =settings.redis_host or os.getenv("REDIS_HOST", "127.0.0.1"),
            port        =int(settings.redis_port or os.getenv("REDIS_PORT", 6379)),
            db          =int(settings.redis_db or os.getenv("REDIS_DB", 0)),
            password    =settings.redis_password or os.getenv("REDIS_PASSWORD"),
            session_prefix    =settings.redis_session_prefix or os.getenv("REDIS_SESSION_PREFIX"),
            refresh_prefix    =settings.redis_refresh_prefix or os.getenv("REDIS_REFRESH_PREFIX"),
            default_ttl =int(settings.redis_default_ttl or os.getenv("SESSION_TTL", 86400)),
            refresh_ttl =int(settings.redis_refresh_ttl or os.getenv("REFRESH_TTL", 604800))
        )
    return _redis_manager

def get_users_table() -> UsersTable:
    """UsersTable 싱글톤 인스턴스"""
    global _users_table
    if _users_table is None:
        # 환경변수나 설정에서 DB 설정을 가져옴
        db_config = {
            "database": settings.DB_NAME or os.getenv("DB_NAME", "wzdb"),
            "user": settings.DB_USER or os.getenv("DB_USER", "wzuser"),
            "password": settings.DB_PASSWORD or os.getenv("DB_PASSWORD", "wzuserpwd!"),
            "host": settings.DB_HOST or os.getenv("DB_HOST", "127.0.0.1"),
            "port": int(settings.DB_PORT or os.getenv("DB_PORT", 5432))
        }
        db_manager = get_db_manager(db_config)
        _users_table = UsersTable(db_manager=db_manager, logger= logger)
        
        # 테이블 생성 확인
        #_users_table.create_table_if_not_exists()
    
    return _users_table

def get_sessions_table() -> UserSessionsTable:
    """UsersTable 싱글톤 인스턴스"""
    global _sessions_table
    if _sessions_table is None:
        # 환경변수나 설정에서 DB 설정을 가져옴
        db_config = {
            "database": settings.DB_NAME or os.getenv("DB_NAME", "wzdb"),
            "user": settings.DB_USER or os.getenv("DB_USER", "wzuser"),
            "password": settings.DB_PASSWORD or os.getenv("DB_PASSWORD", "wzuserpwd!"),
            "host": settings.DB_HOST or os.getenv("DB_HOST", "127.0.0.1"),
            "port": int(settings.DB_PORT or os.getenv("DB_PORT", 5432))
        }
        db_manager = get_db_manager(db_config)
        _sessions_table = UserSessionsTable(db_manager=db_manager, logger= logger)
        
    return _sessions_table

class AuthService:
    """인증 서비스 클래스"""
    
    def __init__(self):
        self.redis_manager = get_redis_manager()
        self.users_table = get_users_table()
        self.sessions_table = get_sessions_table()
        self.logger = get_logger(__name__)
    
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        사용자 인증
        
        Args:
            username: 사용자명
            password: 비밀번호
        
        Returns:
            인증 성공 시 사용자 정보, 실패 시 None
        """
        try:
            # DB 연결
            self.users_table.connect()
            
            # 사용자 조회
            user = self.users_table.get_by_username(username)
            if not user:
                # 이메일로도 시도
                user = self.users_table.get_by_email(username)
            
            if not user:
                self.users_table.close()
                return None
            

            if not self.users_table.verify_password(user['username'], password):
                # 로그인 실패 횟수 증가
                self.users_table.increment_login_attempts(user['username'])
                self.users_table.close()
                return None

            # 계정 활성화 상태 확인
            if not user.get('is_active', True):
                self.users_table.close()
                self.Log.warning(f"Inactive account login attempt: {username}")
                return None

            # 계정 상태 확인
            if user['status_code'] != 'ACTIVE':
                self.users_table.close()
                return None
            
            # 이메일 인증 확인 (선택적)
            # if not user.get('is_email_verified', False):
            #     self.users_table.close()
            #     return None
            
            self.users_table.close()
            
            # 민감한 정보 제거
            user_data = {
                'users_id': user['users_id'],
                'username': user['username'],
                'email': user['email'],
                'full_name': user['full_name'],
                'phone': user.get('phone'),
                'role': user.get('role'),
                'is_email_verified': user.get('is_email_verified', False)
            }
            
            return user_data
            
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            if hasattr(self, 'users_table'):
                self.users_table.close()
            return None
    
    async def create_session(self, 
                           user_data: Dict[str, Any], 
                           request: Request) -> Dict[str, Any]:
        """
        세션 생성 및 로그인 기록
        
        Args:
            user_data: 사용자 데이터
            request: FastAPI Request 객체
        
        Returns:
            세션 정보
        """
        try:
            # Redis에 세션 생성
            session_info = self.redis_manager.create_session(
                user_id=user_data['users_id'],
                user_data=user_data,
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                device_info=self._get_device_info(request)
            )
            
            # PostgreSQL에 로그인 기록 저장 (Audit)
            self.sessions_table.connect()
            self.sessions_table.create_session(
                users_id=user_data['users_id'],
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                device_info=self._get_device_info(request),
                created_by=user_data['username']
            )
            
            # 사용자 로그인 정보 업데이트
            self.users_table.connect()
            self.users_table.update_login_info(
                user_data['users_id'], 
                request.client.host
            )
            
            self.sessions_table.close()
            self.users_table.close()
            
            return session_info
            
        except Exception as e:
            self.logger.error(f"Session creation error: {e}")
            if hasattr(self, 'sessions_table'):
                self.sessions_table.close()
            if hasattr(self, 'users_table'):
                self.users_table.close()
            raise
    
    async def logout(self, session_token: str) -> bool:
        """
        로그아웃 처리
        
        Args:
            session_token: 세션 토큰
        
        Returns:
            성공 여부
        """
        try:
            # Redis에서 세션 삭제
            result = self.redis_manager.end_session(session_token)
            
            # PostgreSQL에 로그아웃 기록
            if result:
                self.sessions_table.connect()
                self.sessions_table.end_session(session_token)
                self.sessions_table.close()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Logout error: {e}")
            if hasattr(self, 'sessions_table'):
                self.sessions_table.close()
            return False
    
    def _get_device_info(self, request: Request) -> str:
        """디바이스 정보 추출"""
        user_agent = request.headers.get("user-agent", "")
        if "Mobile" in user_agent:
            return "Mobile"
        elif "Tablet" in user_agent:
            return "Tablet"
        else:
            return "Desktop"

# 인증 서비스 인스턴스
auth_service = AuthService()

# API 키 prefix
API_KEY_PREFIX = "kbr_live_"

def _validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """
    API 키 검증 (지연 임포트로 순환 참조 방지)

    Args:
        api_key: API 키 문자열

    Returns:
        유효한 경우 사용자 정보, 아니면 None
    """
    try:
        from .service_api_keys import validate_api_key
        return validate_api_key(api_key)
    except Exception as e:
        logger.error(f"API key validation error: {e}")
        return None


# 인증 의존성 함수들
async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    현재 인증된 사용자 정보 가져오기

    지원하는 인증 방식:
    1. Bearer 토큰 (세션)
    2. API 키 (kbr_live_... 형식)
    3. 쿠키 세션 (웹 애플리케이션용)

    Args:
        request: FastAPI Request 객체
        credentials: Authorization 헤더 정보

    Returns:
        사용자 정보

    Raises:
        HTTPException: 인증 실패 시
    """
    token = None

    # 1. Authorization 헤더에서 토큰 추출
    if credentials is not None:
        token = credentials.credentials

    # 2. 쿠키에서 토큰 확인 (웹 애플리케이션용)
    if token is None:
        token = request.cookies.get("session_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. API 키인지 확인 (kbr_live_ prefix)
    if token.startswith(API_KEY_PREFIX):
        user_data = _validate_api_key(token)
        if user_data:
            return user_data
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 4. 세션 토큰으로 Redis에서 확인
    redis_manager = get_redis_manager()
    session = redis_manager.validate_session(token)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return session["user_data"]

async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    현재 활성 사용자 정보 가져오기
    
    Args:
        current_user: 현재 사용자 정보
    
    Returns:
        활성 사용자 정보
    
    Raises:
        HTTPException: 비활성 사용자인 경우
    """
    # 추가적인 사용자 상태 확인 가능
    # 예: 계정 상태, 권한 등
    
    return current_user

async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    선택적 사용자 인증 (인증되지 않아도 접근 가능)
    
    Args:
        request: FastAPI Request 객체
        credentials: Authorization 헤더 정보
    
    Returns:
        사용자 정보 또는 None
    """
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None

# 권한 확인 의존성
def require_role(required_role: str):
    """
    특정 역할 요구 의존성 생성
    
    Args:
        required_role: 필요한 역할
    
    Returns:
        의존성 함수
    """
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_active_user)):
        user_role = current_user.get("role", "")
        logger.debug(f"current_user:{current_user}")
        if user_role != required_role and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    
    return role_checker

# 미들웨어 클래스
class AuthMiddleware:
    """인증 미들웨어"""
    
    def __init__(self, app, exclude_paths: list = None):
        self.app = app
        self.exclude_paths = exclude_paths or [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/static"
        ]
        self.redis_manager = get_redis_manager()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"]
            
            # 제외 경로 확인
            if any(path.startswith(excluded) for excluded in self.exclude_paths):
                await self.app(scope, receive, send)
                return
            
            # 헤더에서 토큰 추출
            headers = dict(scope["headers"])
            auth_header = headers.get(b"authorization", b"").decode()
            
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                
                # 세션 확인
                session = self.redis_manager.validate_session(token)
                
                if session:
                    # 인증 성공 - scope에 사용자 정보 추가
                    scope["user"] = session["user_data"]
                else:
                    # 인증 실패 - 401 응답
                    response = {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [(b"content-type", b"application/json")],
                    }
                    await send(response)
                    
                    body = {
                        "type": "http.response.body",
                        "body": b'{"detail":"Invalid or expired session"}',
                    }
                    await send(body)
                    return
            else:
                # 토큰 없음 - 401 응답
                response = {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [(b"content-type", b"application/json")],
                }
                await send(response)
                
                body = {
                    "type": "http.response.body",
                    "body": b'{"detail":"Not authenticated"}',
                }
                await send(body)
                return
        
        await self.app(scope, receive, send)

# 데코레이터 방식의 인증 (선택적)
def login_required(redirect_to: str = "/login"):
    """
    로그인 필요 데코레이터
    
    Args:
        redirect_to: 리다이렉트할 경로
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            try:
                # 세션 확인 (쿠키 우선 - 페이지 네비게이션용)
                session_token = request.cookies.get("session_token")
                if not session_token:
                    raise HTTPException(status_code=401)

                redis_manager = get_redis_manager()
                session = redis_manager.validate_session(session_token)

                if not session:
                    raise HTTPException(status_code=401)

                # 사용자 정보를 request.state에 추가
                request.state.user = session["user_data"]

                return await func(request, *args, **kwargs)

            except HTTPException:
                # 웹 페이지 요청인 경우 리다이렉트
                if request.headers.get("accept", "").startswith("text/html"):
                    return RedirectResponse(url=redirect_to, status_code=302)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Not authenticated"
                    )
        
        return wrapper
    
    return decorator

