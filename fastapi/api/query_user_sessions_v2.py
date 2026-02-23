# -*- coding: utf-8 -*-
"""
    query_user_sessions
    ~~~~~~~~~~~~~~~~~~~~~~~~

    User sessions table query class

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

#--- query_user_sessions_v1.py 
#-------------------------------------
from .timescaledb_manager_v2 import BaseTable, DatabaseConnectionManager
import logging
from app_logger import setup_logging, get_logger
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import secrets
import hashlib

class UserSessionsTable(BaseTable):
    """
    User Sessions 테이블 전용 쿼리 클래스
    
    테이블 스펙:
    - user_sessions_id: BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    - users_id: BIGINT NOT NULL
    - session_token: VARCHAR(255) UNIQUE NOT NULL
    - refresh_token: VARCHAR(255) UNIQUE
    - session_start_date: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    - session_end_date: TIMESTAMP NULL
    - expires_at: TIMESTAMP NOT NULL
    - ip_address: INET
    - user_agent: TEXT
    - device_info: VARCHAR(200)
    - is_expired: BOOLEAN DEFAULT FALSE
    - is_active: BOOLEAN DEFAULT TRUE
    - date_created: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    - created_by: VARCHAR(50) NOT NULL
    - date_modified: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    - modified_by: VARCHAR(50)
    """
    
    TABLE_NAME = "user_sessions"
    
    # 테이블 스키마 정의
    SCHEMA = {
        "user_sessions_id": "BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY",
        "users_id": "BIGINT NOT NULL",
        "session_token": "VARCHAR(255) NOT NULL",
        "refresh_token": "VARCHAR(255)",
        "session_start_date": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "session_end_date": "TIMESTAMP NULL",
        "expires_at": "TIMESTAMP NOT NULL",
        "ip_address": "INET",
        "user_agent": "TEXT",
        "device_info": "VARCHAR(200)",
        "is_expired": "BOOLEAN DEFAULT FALSE",
        "is_active": "BOOLEAN DEFAULT TRUE",
        "date_created": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "created_by": "VARCHAR(50) NOT NULL",
        "date_modified": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "modified_by": "VARCHAR(50)"
    }
    
    def __init__(self, db_manager: Optional[DatabaseConnectionManager] = None, logger: Optional[logging.Logger] = None):
        """
        Args:
            db_manager: 공유할 DatabaseConnectionManager 인스턴스
            logger: 로거 인스턴스
        """
        super().__init__(db_manager, logger)
        self.Log     = logger if logger else get_logger(__name__)
     
    
    def create_table_if_not_exists(self):
        """테이블이 없으면 생성"""
        return
        columns = []
        for col, spec in self.SCHEMA.items():
            columns.append(f"{col} {spec}")
        
        create_stmt = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            {', '.join(columns)}
        );
        
        -- 인덱스 생성
        CREATE UNIQUE INDEX IF NOT EXISTS uk_user_sessions_token 
        ON {self.TABLE_NAME} (session_token);
        
        CREATE UNIQUE INDEX IF NOT EXISTS uk_user_sessions_refresh_token 
        ON {self.TABLE_NAME} (refresh_token);
        
        CREATE INDEX IF NOT EXISTS idx_user_sessions_expires 
        ON {self.TABLE_NAME} (expires_at);
        
        CREATE INDEX IF NOT EXISTS idx_user_sessions_user_active 
        ON {self.TABLE_NAME} (users_id, is_active);
        
        -- 테이블 코멘트
        COMMENT ON TABLE {self.TABLE_NAME} IS '사용자 세션정보';
        COMMENT ON COLUMN {self.TABLE_NAME}.user_sessions_id IS '사용자세션ID';
        COMMENT ON COLUMN {self.TABLE_NAME}.users_id IS '사용자ID';
        COMMENT ON COLUMN {self.TABLE_NAME}.session_token IS '세션토큰';
        COMMENT ON COLUMN {self.TABLE_NAME}.refresh_token IS '리프레시토큰';
        COMMENT ON COLUMN {self.TABLE_NAME}.session_start_date IS '세션시작일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.session_end_date IS '세션종료일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.expires_at IS '만료일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.ip_address IS 'IP주소';
        COMMENT ON COLUMN {self.TABLE_NAME}.user_agent IS '사용자에이전트';
        COMMENT ON COLUMN {self.TABLE_NAME}.device_info IS '디바이스정보';
        COMMENT ON COLUMN {self.TABLE_NAME}.is_expired IS '만료여부';
        COMMENT ON COLUMN {self.TABLE_NAME}.is_active IS '활성화여부';
        COMMENT ON COLUMN {self.TABLE_NAME}.date_created IS '생성일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.created_by IS '생성자';
        COMMENT ON COLUMN {self.TABLE_NAME}.date_modified IS '수정일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.modified_by IS '수정자';
        """
        
        try:
            self.query(create_stmt, commit=True)
            self.Log.info(f"Table {self.TABLE_NAME} created/verified successfully")
            return True
        except Exception as e:
            self.Log.error(f"Failed to create table: {e}")
            return False
    
    def generate_tokens(self) -> Dict[str, str]:
        """세션 토큰과 리프레시 토큰 생성"""
        session_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        return {
            "session_token": session_token,
            "refresh_token": refresh_token
        }
    
    def create_session(self, users_id: int, ip_address: str = None, 
                      user_agent: str = None, device_info: str = None,
                      created_by: str = "system", 
                      session_duration_hours: int = 24) -> Optional[Dict]:
        """새로운 세션 생성"""
        tokens = self.generate_tokens()
        expires_at = datetime.now() + timedelta(hours=session_duration_hours)
        
        session_data = {
            "users_id": users_id,
            "session_token": tokens["session_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_at": expires_at,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_info": device_info,
            "created_by": created_by
        }
        
        try:
            session_id = self.insert(self.TABLE_NAME, session_data, return_key="user_sessions_id")
            if session_id:
                self.Log.info(f"Created new session for user {users_id}: {session_id}")
                return self.get_by_id(session_id)
            return None
        except Exception as e:
            self.Log.error(f"Failed to create session: {e}")
            return None
    
    def get_by_id(self, user_sessions_id: int) -> Optional[Dict]:
        """세션 ID로 조회"""
        self.Log.debug(f"Getting session by id: {user_sessions_id}")
        return self.select(self.TABLE_NAME, 
                         condition={"user_sessions_id": user_sessions_id}, 
                         one=True)
    
    def get_by_token(self, session_token: str) -> Optional[Dict]:
        """세션 토큰으로 조회"""
        self.Log.debug(f"Getting session by token")
        return self.select(self.TABLE_NAME, 
                         condition={"session_token": session_token}, 
                         one=True)
    
    def get_active_sessions_by_user(self, users_id: int) -> List[Dict]:
        """사용자의 활성 세션 목록 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE users_id = %s 
          AND is_active = TRUE 
          AND is_expired = FALSE
          AND expires_at > NOW()
        ORDER BY session_start_date DESC
        """
        self.Log.info(f"Getting active sessions for user: {users_id}")
        return self.query(query, (users_id,))
    
    def validate_session(self, session_token: str) -> Optional[Dict]:
        """세션 유효성 검증"""
        session = self.get_by_token(session_token)
        
        if not session:
            self.Log.warning("Session not found")
            return None
            
        # 만료 여부 확인
        if session['is_expired'] or not session['is_active']:
            self.Log.warning(f"Session is expired or inactive: {session['user_sessions_id']}")
            return None
            
        # 만료 시간 확인
        if session['expires_at'] < datetime.now():
            self.Log.warning(f"Session has expired: {session['user_sessions_id']}")
            # 만료 상태 업데이트
            self.expire_session(session['user_sessions_id'])
            return None
            
        self.Log.debug(f"Session is valid: {session['user_sessions_id']}")
        return session
    
    def refresh_session(self, refresh_token: str, 
                       session_duration_hours: int = 24) -> Optional[Dict]:
        """리프레시 토큰으로 세션 갱신"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE refresh_token = %s AND is_active = TRUE
        """
        session = self.query(query, (refresh_token,), one=True)
        
        if not session:
            self.Log.warning("Invalid refresh token")
            return None
            
        # 새로운 토큰 생성
        new_tokens = self.generate_tokens()
        new_expires_at = datetime.now() + timedelta(hours=session_duration_hours)
        
        # 세션 업데이트
        update_data = {
            "session_token": new_tokens["session_token"],
            "refresh_token": new_tokens["refresh_token"],
            "expires_at": new_expires_at,
            "date_modified": datetime.now(),
            "modified_by": "refresh"
        }
        
        result = self.update(self.TABLE_NAME, update_data, 
                           {"user_sessions_id": session['user_sessions_id']})
        
        if result:
            self.Log.info(f"Session refreshed: {session['user_sessions_id']}")
            return self.get_by_id(session['user_sessions_id'])
        
        return None
    
    def end_session(self, session_token: str, modified_by: str = "system") -> bool:
        """세션 종료"""
        session = self.get_by_token(session_token)
        if not session:
            return False
            
        update_data = {
            "session_end_date": datetime.now(),
            "is_active": False,
            "date_modified": datetime.now(),
            "modified_by": modified_by
        }
        
        result = self.update(self.TABLE_NAME, update_data, 
                           {"user_sessions_id": session['user_sessions_id']})
        
        self.Log.info(f"Session ended: {session['user_sessions_id']}")
        return result > 0
    
    def expire_session(self, user_sessions_id: int) -> bool:
        """세션 만료 처리"""
        update_data = {
            "is_expired": True,
            "is_active": False,
            "date_modified": datetime.now(),
            "modified_by": "expire_job"
        }
        
        result = self.update(self.TABLE_NAME, update_data, 
                           {"user_sessions_id": user_sessions_id})
        
        self.Log.info(f"Session expired: {user_sessions_id}")
        return result > 0
    
    def expire_old_sessions(self) -> int:
        """만료된 세션들 일괄 처리"""
        query = f"""
        UPDATE {self.TABLE_NAME}
        SET is_expired = TRUE, 
            is_active = FALSE,
            date_modified = NOW(),
            modified_by = 'expire_job'
        WHERE expires_at < NOW() 
          AND is_expired = FALSE
        """
        
        try:
            result = self.query(query, commit=True)
            self.Log.info(f"Expired {result} sessions")
            return result
        except Exception as e:
            self.Log.error(f"Failed to expire sessions: {e}")
            return 0
    
    def terminate_user_sessions(self, users_id: int, 
                              except_token: str = None,
                              modified_by: str = "system") -> int:
        """사용자의 모든 세션 종료 (특정 토큰 제외 가능)"""
        query = f"""
        UPDATE {self.TABLE_NAME}
        SET is_active = FALSE,
            session_end_date = NOW(),
            date_modified = NOW(),
            modified_by = %s
        WHERE users_id = %s AND is_active = TRUE
        """
        params = [modified_by, users_id]
        
        if except_token:
            query += " AND session_token != %s"
            params.append(except_token)
            
        try:
            result = self.query(query, tuple(params), commit=True)
            self.Log.info(f"Terminated {result} sessions for user {users_id}")
            return result
        except Exception as e:
            self.Log.error(f"Failed to terminate sessions: {e}")
            return 0
    
    def get_session_statistics(self, users_id: int = None) -> Dict:
        """세션 통계 조회"""
        base_query = f"""
        SELECT 
            COUNT(*) FILTER (WHERE is_active = TRUE AND is_expired = FALSE) as active_sessions,
            COUNT(*) FILTER (WHERE is_active = FALSE) as inactive_sessions,
            COUNT(*) FILTER (WHERE is_expired = TRUE) as expired_sessions,
            COUNT(*) as total_sessions,
            MAX(session_start_date) as last_session_date
        FROM {self.TABLE_NAME}
        """
        
        if users_id:
            query = base_query + " WHERE users_id = %s"
            params = (users_id,)
        else:
            query = base_query
            params = None
            
        result = self.query(query, params, one=True)
        return result if result else {}
    
    def cleanup_old_sessions(self, days: int = 90) -> int:
        """오래된 세션 데이터 삭제"""
        cutoff_date = datetime.now() - timedelta(days=days)
        query = f"""
        DELETE FROM {self.TABLE_NAME}
        WHERE (is_expired = TRUE OR is_active = FALSE)
          AND date_created < %s
        """
        
        try:
            result = self.query(query, (cutoff_date,), commit=True)
            self.Log.info(f"Deleted {result} old sessions")
            return result
        except Exception as e:
            self.Log.error(f"Failed to cleanup sessions: {e}")
            return 0


# Example Usage
if __name__ == "__main__":
    # Logger 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # UserSessionsTable 인스턴스 생성
    sessions = UserSessionsTable(
        database="your_db",
        user="your_user", 
        password="your_password",
        host="127.0.0.1",
        port=5432
    )
    
    try:
        # 테이블 생성
        sessions.create_table_if_not_exists()
        
        # 새 세션 생성
        new_session = sessions.create_session(
            users_id=123,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            device_info="Windows PC",
            created_by="login_service"
        )
        
        if new_session:
            print(f"Created new session: {new_session['user_sessions_id']}")
            print(f"Session token: {new_session['session_token']}")
            
            # 세션 검증
            valid_session = sessions.validate_session(new_session['session_token'])
            if valid_session:
                print(f"Session is valid for user: {valid_session['users_id']}")
            
            # 사용자의 활성 세션 조회
            active_sessions = sessions.get_active_sessions_by_user(123)
            print(f"User has {len(active_sessions)} active sessions")
            
            # 세션 갱신
            refreshed = sessions.refresh_session(
                new_session['refresh_token'],
                session_duration_hours=48
            )
            if refreshed:
                print(f"Session refreshed with new token: {refreshed['session_token']}")
            
            # 세션 통계
            stats = sessions.get_session_statistics(123)
            print(f"Session statistics: {stats}")
            
            # 다른 세션들 종료 (현재 세션 제외)
            terminated = sessions.terminate_user_sessions(
                123, 
                except_token=refreshed['session_token'] if refreshed else new_session['session_token']
            )
            print(f"Terminated {terminated} other sessions")
            
            # 세션 종료
            ended = sessions.end_session(
                refreshed['session_token'] if refreshed else new_session['session_token'],
                modified_by="logout_service"
            )
            print(f"Session ended: {ended}")
        
        # 만료된 세션 처리
        expired_count = sessions.expire_old_sessions()
        print(f"Expired {expired_count} old sessions")
        
        # 전체 통계
        total_stats = sessions.get_session_statistics()
        print(f"Total session statistics: {total_stats}")
        
        # 오래된 세션 정리
        cleaned = sessions.cleanup_old_sessions(days=30)
        print(f"Cleaned up {cleaned} old sessions")
        
    except Exception as e:
        sessions.Log.error(f"Example failed: {e}")
    finally:
        sessions.close()
