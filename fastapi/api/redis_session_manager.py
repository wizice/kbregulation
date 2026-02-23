# -*- coding: utf-8 -*-
"""
    redis_session_manager
    ~~~~~~~~~~~~~~~~~~~

    Redis를 사용한 세션 관리 모듈

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

import redis
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
from app_logger import setup_logging, get_logger

class RedisSessionManager:
    """Redis를 사용한 세션 관리 클래스"""
    
    def __init__(self, 
                 host: str = "127.0.0.1", 
                 port: int = 6379, 
                 db: int = 0,
                 password: Optional[str] = None,
                 decode_responses: bool = True,
                 session_prefix: str = "session:",
                 refresh_prefix: str = "refresh:",
                 default_ttl: int = 7200,   # 2시간 (보안 우선)
                 refresh_ttl: int = 28800,  # 8시간 (업무 시간 내)
                 logger: Optional[logging.Logger] = None):
        """
        Redis 세션 매니저 초기화
        
        Args:
            host: Redis 호스트
            port: Redis 포트
            db: Redis DB 번호
            password: Redis 비밀번호
            decode_responses: 응답 디코딩 여부
            session_prefix: 세션 키 프리픽스
            refresh_prefix: 리프레시 토큰 키 프리픽스
            default_ttl: 기본 세션 TTL (초)
            refresh_ttl: 리프레시 토큰 TTL (초)
            logger: 로거 인스턴스
        """
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=decode_responses
        )
        self.session_prefix = session_prefix
        self.refresh_prefix = refresh_prefix
        self.default_ttl = default_ttl
        self.refresh_ttl = refresh_ttl
        self.logger = logger or get_logger(__name__)
        
        # Redis 연결 테스트
        try:
            self.redis_client.ping()
            self.logger.info("Redis connection established")
        except redis.ConnectionError as e:
            self.logger.error(f"Redis connection failed: {e}")
            raise
    
    def generate_tokens(self) -> Dict[str, str]:
        """세션 토큰과 리프레시 토큰 생성"""
        return {
            "session_token": secrets.token_urlsafe(32),
            "refresh_token": secrets.token_urlsafe(32)
        }
    
    def create_session(self, 
                      user_id: int,
                      user_data: Dict[str, Any],
                      ip_address: Optional[str] = None,
                      user_agent: Optional[str] = None,
                      device_info: Optional[str] = None,
                      custom_ttl: Optional[int] = None) -> Dict[str, Any]:
        """
        새로운 세션 생성
        
        Args:
            user_id: 사용자 ID
            user_data: 세션에 저장할 사용자 데이터
            ip_address: IP 주소
            user_agent: User Agent
            device_info: 디바이스 정보
            custom_ttl: 커스텀 TTL (초)
        
        Returns:
            세션 정보 딕셔너리
        """
        tokens = self.generate_tokens()
        session_token = tokens["session_token"]
        refresh_token = tokens["refresh_token"]
        
        # 세션 데이터 구성
        session_data = {
            "user_id": user_id,
            "session_token": session_token,
            "refresh_token": refresh_token,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_info": device_info,
            "user_data": user_data
        }
        
        # Redis에 세션 저장
        session_key = f"{self.session_prefix}{session_token}"
        refresh_key = f"{self.refresh_prefix}{refresh_token}"
        
        ttl = custom_ttl or self.default_ttl
        
        try:
            # 세션 토큰 저장
            self.redis_client.setex(
                session_key,
                ttl,
                json.dumps(session_data)
            )
            
            # 리프레시 토큰 저장 (user_id와 session_token 매핑)
            refresh_data = {
                "user_id": user_id,
                "session_token": session_token
            }
            self.redis_client.setex(
                refresh_key,
                self.refresh_ttl,
                json.dumps(refresh_data)
            )
            
            # 사용자별 활성 세션 목록에 추가
            user_sessions_key = f"user_sessions:{user_id}"
            self.redis_client.sadd(user_sessions_key, session_token)
            self.redis_client.expire(user_sessions_key, self.refresh_ttl)
            
            self.logger.info(f"Session created for user {user_id}: {session_token}")
            
            return {
                "session_token": session_token,
                "refresh_token": refresh_token,
                "expires_in": ttl,
                "user_id": user_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create session: {e}")
            raise
    
    def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        세션 조회
        
        Args:
            session_token: 세션 토큰
        
        Returns:
            세션 데이터 또는 None
        """
        session_key = f"{self.session_prefix}{session_token}"
        
        try:
            session_data = self.redis_client.get(session_key)
            if session_data:
                session = json.loads(session_data)
                
                # 마지막 접근 시간 업데이트
                session["last_accessed"] = datetime.now().isoformat()
                
                # TTL 연장
                ttl = self.redis_client.ttl(session_key)
                if ttl > 0:
                    self.redis_client.setex(
                        session_key,
                        max(ttl, self.default_ttl // 2),  # 최소 절반의 TTL 보장
                        json.dumps(session)
                    )
                
                return session
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get session: {e}")
            return None
    
    def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        세션 유효성 검증
        
        Args:
            session_token: 세션 토큰
        
        Returns:
            유효한 경우 세션 데이터, 무효한 경우 None
        """
        session = self.get_session(session_token)
        
        if session:
            self.logger.debug(f"Session valid for user {session['user_id']}")
            return session
        
        self.logger.warning(f"Invalid session token: {session_token}")
        return None
    
    def refresh_session(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        리프레시 토큰으로 세션 갱신
        
        Args:
            refresh_token: 리프레시 토큰
        
        Returns:
            새로운 세션 정보 또는 None
        """
        refresh_key = f"{self.refresh_prefix}{refresh_token}"
        
        try:
            refresh_data = self.redis_client.get(refresh_key)
            if not refresh_data:
                self.logger.warning("Invalid refresh token")
                return None
            
            refresh_info = json.loads(refresh_data)
            old_session_token = refresh_info["session_token"]
            user_id = refresh_info["user_id"]
            
            # 기존 세션 데이터 가져오기
            old_session = self.get_session(old_session_token)
            if not old_session:
                # 세션은 만료되었지만 리프레시 토큰은 유효한 경우
                old_session = {"user_data": {}}
            
            # 새로운 토큰 생성
            new_tokens = self.generate_tokens()
            new_session_token = new_tokens["session_token"]
            new_refresh_token = new_tokens["refresh_token"]
            
            # 새로운 세션 데이터
            new_session_data = {
                "user_id": user_id,
                "session_token": new_session_token,
                "refresh_token": new_refresh_token,
                "created_at": old_session.get("created_at", datetime.now().isoformat()),
                "refreshed_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
                "ip_address": old_session.get("ip_address"),
                "user_agent": old_session.get("user_agent"),
                "device_info": old_session.get("device_info"),
                "user_data": old_session.get("user_data", {})
            }
            
            # 새로운 세션 저장
            new_session_key = f"{self.session_prefix}{new_session_token}"
            new_refresh_key = f"{self.refresh_prefix}{new_refresh_token}"
            
            self.redis_client.setex(
                new_session_key,
                self.default_ttl,
                json.dumps(new_session_data)
            )
            
            # 새로운 리프레시 토큰 저장
            self.redis_client.setex(
                new_refresh_key,
                self.refresh_ttl,
                json.dumps({
                    "user_id": user_id,
                    "session_token": new_session_token
                })
            )
            
            # 기존 토큰 삭제
            self.redis_client.delete(f"{self.session_prefix}{old_session_token}")
            self.redis_client.delete(refresh_key)
            
            # 사용자 세션 목록 업데이트
            user_sessions_key = f"user_sessions:{user_id}"
            self.redis_client.srem(user_sessions_key, old_session_token)
            self.redis_client.sadd(user_sessions_key, new_session_token)
            
            self.logger.info(f"Session refreshed for user {user_id}")
            
            return {
                "session_token": new_session_token,
                "refresh_token": new_refresh_token,
                "expires_in": self.default_ttl,
                "user_id": user_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to refresh session: {e}")
            return None
    
    def end_session(self, session_token: str) -> bool:
        """
        세션 종료
        
        Args:
            session_token: 세션 토큰
        
        Returns:
            성공 여부
        """
        session = self.get_session(session_token)
        if not session:
            return False
        
        try:
            # 세션 삭제
            session_key = f"{self.session_prefix}{session_token}"
            self.redis_client.delete(session_key)
            
            # 리프레시 토큰 삭제
            refresh_token = session.get("refresh_token")
            if refresh_token:
                refresh_key = f"{self.refresh_prefix}{refresh_token}"
                self.redis_client.delete(refresh_key)
            
            # 사용자 세션 목록에서 제거
            user_id = session.get("user_id")
            if user_id:
                user_sessions_key = f"user_sessions:{user_id}"
                self.redis_client.srem(user_sessions_key, session_token)
            
            self.logger.info(f"Session ended: {session_token}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to end session: {e}")
            return False
    
    def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """
        사용자의 모든 활성 세션 조회
        
        Args:
            user_id: 사용자 ID
        
        Returns:
            세션 목록
        """
        user_sessions_key = f"user_sessions:{user_id}"
        
        try:
            session_tokens = self.redis_client.smembers(user_sessions_key)
            sessions = []
            
            for token in session_tokens:
                session = self.get_session(token)
                if session:
                    sessions.append(session)
                else:
                    # 만료된 세션은 목록에서 제거
                    self.redis_client.srem(user_sessions_key, token)
            
            return sessions
            
        except Exception as e:
            self.logger.error(f"Failed to get user sessions: {e}")
            return []
    
    def terminate_user_sessions(self, user_id: int, except_token: Optional[str] = None) -> int:
        """
        사용자의 모든 세션 종료 (특정 토큰 제외 가능)
        
        Args:
            user_id: 사용자 ID
            except_token: 제외할 세션 토큰
        
        Returns:
            종료된 세션 수
        """
        user_sessions_key = f"user_sessions:{user_id}"
        terminated_count = 0
        
        try:
            session_tokens = self.redis_client.smembers(user_sessions_key)
            
            for token in session_tokens:
                if token != except_token:
                    if self.end_session(token):
                        terminated_count += 1
            
            self.logger.info(f"Terminated {terminated_count} sessions for user {user_id}")
            return terminated_count
            
        except Exception as e:
            self.logger.error(f"Failed to terminate user sessions: {e}")
            return 0
    
    def update_session_data(self, session_token: str, user_data: Dict[str, Any]) -> bool:
        """
        세션의 사용자 데이터 업데이트
        
        Args:
            session_token: 세션 토큰
            user_data: 업데이트할 사용자 데이터
        
        Returns:
            성공 여부
        """
        session = self.get_session(session_token)
        if not session:
            return False
        
        try:
            # 사용자 데이터 업데이트
            session["user_data"].update(user_data)
            session["last_accessed"] = datetime.now().isoformat()
            
            # Redis에 저장
            session_key = f"{self.session_prefix}{session_token}"
            ttl = self.redis_client.ttl(session_key)
            
            if ttl > 0:
                self.redis_client.setex(
                    session_key,
                    ttl,
                    json.dumps(session)
                )
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to update session data: {e}")
            return False
    
    def get_session_count(self, user_id: Optional[int] = None) -> int:
        """
        활성 세션 수 조회
        
        Args:
            user_id: 특정 사용자 ID (None이면 전체)
        
        Returns:
            세션 수
        """
        try:
            if user_id:
                user_sessions_key = f"user_sessions:{user_id}"
                return self.redis_client.scard(user_sessions_key)
            else:
                # 전체 세션 수 (근사치)
                keys = self.redis_client.keys(f"{self.session_prefix}*")
                return len(keys)
                
        except Exception as e:
            self.logger.error(f"Failed to get session count: {e}")
            return 0
    
    def cleanup_expired_sessions(self) -> int:
        """
        만료된 세션 정리 (Redis TTL이 자동으로 처리하지만, 세션 목록 정리용)
        
        Returns:
            정리된 세션 수
        """
        cleaned_count = 0
        
        try:
            # 모든 사용자 세션 목록 키 조회
            user_session_keys = self.redis_client.keys("user_sessions:*")
            
            for key in user_session_keys:
                session_tokens = self.redis_client.smembers(key)
                
                for token in session_tokens:
                    session_key = f"{self.session_prefix}{token}"
                    if not self.redis_client.exists(session_key):
                        # 세션이 없으면 목록에서 제거
                        self.redis_client.srem(key, token)
                        cleaned_count += 1
            
            self.logger.info(f"Cleaned up {cleaned_count} expired session references")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0

