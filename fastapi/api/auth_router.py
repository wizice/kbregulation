# -*- coding: utf-8 -*-
"""
    auth_router
    ~~~~~~~~~~

    인증 관련 API 라우터

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Response, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app_logger import setup_logging, get_logger

from .auth_middleware import (
    auth_service, 
    get_current_user, 
    get_current_active_user,
    get_redis_manager
)

# Pydantic 모델 정의
class LoginRequest(BaseModel):
    username: str = Field(..., description="사용자명 또는 이메일")
    password: str = Field(..., min_length=6)
    remember_me: Optional[bool] = False

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class UserResponse(BaseModel):
    users_id: int
    username: str
    email: str
    full_name: str
    phone: Optional[str] = None
    is_email_verified: bool
    last_login_date: Optional[datetime] = None

# 라우터 생성
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}},
)

logger = get_logger(__name__)

@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest
):
    """
    사용자 로그인
    
    - username: 사용자명 또는 이메일
    - password: 비밀번호
    - remember_me: 자동 로그인 여부
    """
    try:
        # 사용자 인증
        user_data = await auth_service.authenticate_user(
            login_data.username,
            login_data.password
        )
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password."
            )
        
        # 세션 생성
        session_info = await auth_service.create_session(user_data, request)

        # 중복 로그인 방지: 기존 세션 모두 종료 (새로 생성된 세션 제외)
        redis_manager = get_redis_manager()
        terminated_count = redis_manager.terminate_user_sessions(
            user_data['users_id'],
            except_token=session_info["session_token"]
        )
        if terminated_count > 0:
            logger.info(f"Terminated {terminated_count} previous session(s) for user {user_data['users_id']} (single login enforcement)")

        # 쿠키 설정 (세션 쿠키 - 브라우저 종료 시 삭제)
        response.set_cookie(
            key="session_token",
            value=session_info["session_token"],
            httponly=True,  # XSS 공격 방지
            secure=True,
            samesite="lax"
        )

        return TokenResponse(
            access_token=session_info["session_token"],
            refresh_token=session_info["refresh_token"],
            expires_in=session_info["expires_in"],
            user=user_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/register", response_model=UserResponse)
async def register(register_data: RegisterRequest):
    """
    신규 사용자 등록
    
    - username: 사용자명 (중복 불가)
    - email: 이메일 (중복 불가)
    - password: 비밀번호 (최소 8자)
    - full_name: 전체 이름
    - phone: 전화번호 (선택)
    """
    try:
        users_table = auth_service.users_table
        users_table.connect()
        
        # 사용자 생성
        user_id = users_table.create_user(
            username=register_data.username,
            email=register_data.email,
            password=register_data.password,
            full_name=register_data.full_name,
            phone=register_data.phone,
            created_by="self_registration"
        )
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User registration failed"
            )
        
        # 생성된 사용자 정보 조회
        new_user = users_table.get_by_id(user_id)
        users_table.close()
        
        # TODO: 이메일 인증 메일 발송
        # send_verification_email(new_user['email'], new_user['email_verification_token'])
        
        return UserResponse(
            users_id=new_user['users_id'],
            username=new_user['username'],
            email=new_user['email'],
            full_name=new_user['full_name'],
            phone=new_user.get('phone'),
            is_email_verified=new_user.get('is_email_verified', False),
            last_login_date=new_user.get('last_login_date')
        )
        
    except ValueError as e:
        # 중복 사용자명/이메일 등
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        if 'users_table' in locals():
            users_table.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_data: RefreshTokenRequest
):
    """
    토큰 갱신
    
    리프레시 토큰을 사용하여 새로운 액세스 토큰 발급
    """
    try:
        redis_manager = get_redis_manager()
        
        # 세션 갱신
        new_session = redis_manager.refresh_session(refresh_data.refresh_token)
        
        if not new_session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # 사용자 정보 조회
        users_table = auth_service.users_table
        users_table.connect()
        user = users_table.get_by_id(new_session["user_id"])
        users_table.close()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_data = {
            'users_id': user['users_id'],
            'username': user['username'],
            'email': user['email'],
            'full_name': user['full_name'],
            'phone': user.get('phone'),
            'is_email_verified': user.get('is_email_verified', False)
        }
        
        # 쿠키 업데이트
        response.set_cookie(
            key="session_token",
            value=new_session["session_token"],
            httponly=True,
            secure=True,
            samesite="lax"
        )
        
        return TokenResponse(
            access_token=new_session["session_token"],
            refresh_token=new_session["refresh_token"],
            expires_in=new_session["expires_in"],
            user=user_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    로그아웃
    
    현재 세션을 종료하고 토큰을 무효화
    """
    try:
        # ⭐ Authorization 헤더 또는 쿠키에서 토큰 가져오기 (호환성)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_token = auth_header[7:]
        else:
            session_token = request.cookies.get("session_token")

        if session_token:
            # 로그아웃 처리 (서버 세션 삭제)
            await auth_service.logout(session_token)

        # ⭐ sessionStorage 방식: 쿠키 삭제하지 않음
        # 클라이언트가 sessionStorage를 직접 정리

        return {"message": "Successfully logged out"}

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return {"message": "Logged out"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    현재 로그인한 사용자 정보 조회
    """
    try:
        # 최신 사용자 정보 조회
        users_table = auth_service.users_table
        users_table.connect()
        user = users_table.get_by_id(current_user['users_id'])
        users_table.close()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(
            users_id=user['users_id'],
            username=user['username'],
            email=user['email'],
            full_name=user['full_name'],
            phone=user.get('phone'),
            is_email_verified=user.get('is_email_verified', False),
            last_login_date=user.get('last_login_date')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        if 'users_table' in locals():
            users_table.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )

@router.put("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    비밀번호 변경
    """
    try:
        users_table = auth_service.users_table
        users_table.connect()
        
        # 현재 비밀번호 확인
        if not users_table.verify_password(
            current_user['username'], 
            password_data.current_password
        ):
            users_table.close()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        # 비밀번호 변경
        success = users_table.change_password(
            current_user['users_id'],
            password_data.new_password,
            current_user['username']
        )
        
        users_table.close()
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to change password"
            )
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        if 'users_table' in locals():
            users_table.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

@router.get("/sessions")
async def get_my_sessions(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    현재 사용자의 활성 세션 목록 조회
    """
    try:
        redis_manager = get_redis_manager()
        sessions = redis_manager.get_user_sessions(current_user['users_id'])
        
        # 민감한 정보 제거 및 포맷팅
        session_list = []
        for session in sessions:
            session_list.append({
                "session_token": session['session_token'][:8] + "...",  # 일부만 표시
                "created_at": session['created_at'],
                "last_accessed": session['last_accessed'],
                "ip_address": session.get('ip_address'),
                "device_info": session.get('device_info'),
                "user_agent": session.get('user_agent', '')[:50] + "..."
            })
        
        return {
            "sessions": session_list,
            "count": len(session_list)
        }
        
    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sessions"
        )

@router.post("/logout-all")
async def logout_all_sessions(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    모든 세션에서 로그아웃 (현재 세션 포함)
    """
    try:
        redis_manager = get_redis_manager()
        
        # 모든 세션 종료
        terminated = redis_manager.terminate_user_sessions(current_user['users_id'])
        
        # PostgreSQL에도 기록
        sessions_table = auth_service.sessions_table
        sessions_table.connect()
        sessions_table.terminate_user_sessions(
            current_user['users_id'],
            modified_by=current_user['username']
        )
        sessions_table.close()
        
        return {
            "message": f"Successfully logged out from {terminated} sessions",
            "terminated_count": terminated
        }
        
    except Exception as e:
        logger.error(f"Logout all error: {e}")
        if 'sessions_table' in locals():
            sessions_table.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout from all sessions"
        )

@router.post("/logout-other")
async def logout_other_sessions(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    다른 모든 세션에서 로그아웃 (현재 세션 제외)
    """
    try:
        # 현재 세션 토큰 가져오기
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            current_token = auth_header[7:]
        else:
            current_token = request.cookies.get("session_token")
        
        redis_manager = get_redis_manager()
        
        # 현재 세션을 제외한 모든 세션 종료
        terminated = redis_manager.terminate_user_sessions(
            current_user['users_id'],
            except_token=current_token
        )
        
        # PostgreSQL에도 기록
        sessions_table = auth_service.sessions_table
        sessions_table.connect()
        sessions_table.terminate_user_sessions(
            current_user['users_id'],
            except_token=current_token,
            modified_by=current_user['username']
        )
        sessions_table.close()
        
        return {
            "message": f"Successfully logged out from {terminated} other sessions",
            "terminated_count": terminated
        }
        
    except Exception as e:
        logger.error(f"Logout other sessions error: {e}")
        if 'sessions_table' in locals():
            sessions_table.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout from other sessions"
        )

# 이메일 인증 관련 엔드포인트 (구현 필요)
@router.get("/verify-email/{token}")
async def verify_email(token: str):
    """이메일 인증"""
    try:
        users_table = auth_service.users_table
        users_table.connect()
        
        success = users_table.verify_email_token(token)
        users_table.close()
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
        return {"message": "Email verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        if 'users_table' in locals():
            users_table.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )

@router.post("/forgot-password")
async def forgot_password(email: EmailStr):
    """비밀번호 재설정 요청"""
    try:
        users_table = auth_service.users_table
        users_table.connect()
        
        reset_token = users_table.create_password_reset_token(email)
        users_table.close()
        
        if not reset_token:
            # 보안상 이메일이 존재하지 않아도 성공 메시지 반환
            return {"message": "If the email exists, a password reset link has been sent"}
        
        # TODO: 비밀번호 재설정 이메일 발송
        # send_password_reset_email(email, reset_token)
        
        return {"message": "If the email exists, a password reset link has been sent"}
        
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        if 'users_table' in locals():
            users_table.close()
        return {"message": "If the email exists, a password reset link has been sent"}

