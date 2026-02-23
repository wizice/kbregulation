# -*- coding: utf-8 -*-
"""
    query_users
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Users table query class for user management

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

#--- query_users_v2.py 
#-------------------------------------
from .timescaledb_manager_v2 import BaseTable, DatabaseConnectionManager
import logging
from app_logger import setup_logging, get_logger
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import hashlib
import secrets
import re

logger   = get_logger(__name__)

class UsersTable(BaseTable):
    """
    Users 테이블 전용 쿼리 클래스
    
    테이블 스펙:
    - users_id: BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    - username: VARCHAR(50) NOT NULL UNIQUE
    - email: VARCHAR(100) NOT NULL UNIQUE
    - password_hash: VARCHAR(255) NOT NULL
    - role: VARCHAR(50) NOT NULL 
    - salt: VARCHAR(100) NOT NULL
    - phone: VARCHAR(20)
    - full_name: VARCHAR(100) NOT NULL
    - status_code: VARCHAR(20) DEFAULT 'ACTIVE'
    - login_attempt_count: INTEGER DEFAULT 0
    - last_login_date: TIMESTAMP
    - last_login_ip: INET
    - password_change_date: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    - is_email_verified: BOOLEAN DEFAULT FALSE
    - email_verification_token: VARCHAR(255)
    - password_reset_token: VARCHAR(255)
    - password_reset_expires: TIMESTAMP
    - date_created: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    - created_by: VARCHAR(50) NOT NULL
    - date_modified: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    - modified_by: VARCHAR(50)
    - is_active: BOOLEAN DEFAULT TRUE
    - departments: VARCHAR(50)
    """
    
    TABLE_NAME = "users"
    
    # 테이블 스키마 정의
    SCHEMA = {
        "users_id": "BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY",
        "username": "VARCHAR(50) NOT NULL UNIQUE",
        "email": "VARCHAR(100) NOT NULL UNIQUE",
        "password_hash": "VARCHAR(255) NOT NULL",
        "role": "VARCHAR(50) NOT NULL ",
        "salt": "VARCHAR(100) NOT NULL",
        "phone": "VARCHAR(20)",
        "full_name": "VARCHAR(100) NOT NULL",
        "status_code": "VARCHAR(20) DEFAULT 'ACTIVE'",
        "login_attempt_count": "INTEGER DEFAULT 0",
        "last_login_date": "TIMESTAMP",
        "last_login_ip": "INET",
        "password_change_date": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "is_email_verified": "BOOLEAN DEFAULT FALSE",
        "email_verification_token": "VARCHAR(255)",
        "password_reset_token": "VARCHAR(255)",
        "password_reset_expires": "TIMESTAMP",
        "date_created": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "created_by": "VARCHAR(50) NOT NULL",
        "date_modified": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "modified_by": "VARCHAR(50)",
        "is_active": "BOOLEAN DEFAULT TRUE",
        "departments": "VARCHAR(50)"
    }
    
    # 상태 코드 상수
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_LOCKED = 'LOCKED'
    STATUS_SUSPENDED = 'SUSPENDED'
    STATUS_DELETED = 'DELETED'
    
   
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
        columns = []
        for col, spec in self.SCHEMA.items():
            columns.append(f"{col} {spec}")
        
        create_stmt = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            {', '.join(columns)}
        );
        
        -- 인덱스 생성
        CREATE INDEX IF NOT EXISTS idx_users_status_active 
        ON {self.TABLE_NAME} (status_code, is_active);
        
        CREATE INDEX IF NOT EXISTS idx_users_email_verified 
        ON {self.TABLE_NAME} (is_email_verified);
        
        -- 코멘트 추가
        COMMENT ON TABLE {self.TABLE_NAME} IS '사용자 기본정보';
        COMMENT ON COLUMN {self.TABLE_NAME}.users_id IS '사용자ID';
        COMMENT ON COLUMN {self.TABLE_NAME}.username IS '사용자명';
        COMMENT ON COLUMN {self.TABLE_NAME}.email IS '이메일';
        COMMENT ON COLUMN {self.TABLE_NAME}.password_hash IS '비밀번호해시';
        COMMENT ON COLUMN {self.TABLE_NAME}.role IS 'role';
        COMMENT ON COLUMN {self.TABLE_NAME}.salt IS '비밀번호솔트';
        COMMENT ON COLUMN {self.TABLE_NAME}.phone IS '전화번호';
        COMMENT ON COLUMN {self.TABLE_NAME}.full_name IS '전체이름';
        COMMENT ON COLUMN {self.TABLE_NAME}.status_code IS '상태코드';
        COMMENT ON COLUMN {self.TABLE_NAME}.login_attempt_count IS '로그인시도횟수';
        COMMENT ON COLUMN {self.TABLE_NAME}.last_login_date IS '마지막로그인일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.last_login_ip IS '마지막로그인IP';
        COMMENT ON COLUMN {self.TABLE_NAME}.password_change_date IS '비밀번호변경일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.is_email_verified IS '이메일인증여부';
        COMMENT ON COLUMN {self.TABLE_NAME}.email_verification_token IS '이메일인증토큰';
        COMMENT ON COLUMN {self.TABLE_NAME}.password_reset_token IS '비밀번호재설정토큰';
        COMMENT ON COLUMN {self.TABLE_NAME}.password_reset_expires IS '비밀번호재설정만료시간';
        COMMENT ON COLUMN {self.TABLE_NAME}.date_created IS '생성일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.created_by IS '생성자';
        COMMENT ON COLUMN {self.TABLE_NAME}.date_modified IS '수정일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.modified_by IS '수정자';
        COMMENT ON COLUMN {self.TABLE_NAME}.is_active IS '활성화여부';
        # COMMENT ON COLUMN {self.TABLE_NAME}.departments IS '소속 부서명';
        """
        
        try:
            self.query(create_stmt, commit=True)
            self.Log.info(f"Table {self.TABLE_NAME} created/verified successfully")
            return True
        except Exception as e:
            self.Log.error(f"Failed to create table: {e}")
            return False
    
    def _generate_salt(self) -> str:
        """비밀번호 솔트 생성"""
        return secrets.token_hex(32)
    
    def _hash_password(self, password: str, salt: str) -> str:
        """비밀번호 해시 생성"""
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def _generate_token(self) -> str:
        """랜덤 토큰 생성"""
        return secrets.token_urlsafe(32)
    
    def _validate_email(self, email: str) -> bool:
        """이메일 형식 검증"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def save(self, data: Dict[str, Any]) -> Optional[int]:
        """
        데이터 저장 (INSERT 또는 UPDATE)
        users_id가 있으면 UPDATE, 없으면 INSERT
        """
        if 'users_id' in data and data['users_id']:
            # UPDATE
            users_id = data.pop('users_id')
            data['date_modified'] = datetime.now()
            return self.update(self.TABLE_NAME, data, {"users_id": users_id}, return_key="users_id")
        else:
            # INSERT
            if 'users_id' in data:
                data.pop('users_id')
            data['date_created'] = datetime.now()
            data['date_modified'] = datetime.now()
            return self.insert(self.TABLE_NAME, data, return_key="users_id")
    
    def create_user(self, username: str, email: str, password: str, 
                   full_name: str, created_by: str,  departments: str, 
                   role: Optional[str] = 'user',
                   phone: Optional[str] = None) -> Optional[int]:
        """새 사용자 생성"""
        # 이메일 검증
        if not self._validate_email(email):
            self.Log.error(f"Invalid email format: {email}")
            raise ValueError("Invalid email format")
        
        # 중복 체크
        if self.get_by_username(username):
            self.Log.error(f"Username already exists: {username}")
            raise ValueError("Username already exists")
        
        if self.get_by_email(email):
            self.Log.error(f"Email already exists: {email}")
            raise ValueError("Email already exists")
        
        # 비밀번호 해시 생성
        salt = self._generate_salt()
        password_hash = self._hash_password(password, salt)
        
        # 이메일 인증 토큰 생성
        email_verification_token = self._generate_token()
        
        user_data = {
            "username": username,
            "email": email,
            "departments": departments,
            "password_hash": password_hash,
            "role": role,
            "salt": salt,
            "full_name": full_name,
            "phone": phone,
            "created_by": created_by,
            "email_verification_token": email_verification_token,
            "status_code": self.STATUS_ACTIVE,
            "login_attempt_count": 0,
            "is_email_verified": False,
            "is_active": True
        }
        
        self.Log.info(f"Creating new user: {username}")
        return self.save(user_data)
    
    def get_by_id(self, users_id: int) -> Optional[Dict]:
        """ID로 사용자 조회"""
        self.Log.debug(f"Getting user by id: {users_id}")
        return self.select(self.TABLE_NAME, condition={"users_id": users_id}, one=True)
    
    def get_by_username(self, username: str) -> Optional[Dict]:
        """사용자명으로 조회"""
        user =  self.select(self.TABLE_NAME, condition={"username": username}, one=True)
        self.Log.debug(f"Getting user by username: {username} row:{user}")
        return user
    
    def get_by_email(self, email: str) -> Optional[Dict]:
        """이메일로 조회"""
        self.Log.debug(f"Getting user by email: {email}")
        return self.select(self.TABLE_NAME, condition={"email": email}, one=True)
    
    def verify_password(self, username: str, password: str) -> bool:
        """비밀번호 확인"""
        user = self.get_by_username(username)
        if not user:
            self.Log.warning(f"User not found: {username}")
            return False
        
        password_hash = self._hash_password(password, user['salt'])
        #logger.debug(f"입력된 password_hash:{password_hash} db유저의 hash:{user['password_hash']}")
        return password_hash == user['password_hash']
    
    def update_login_info(self, users_id: int, login_ip: str) -> bool:
        """로그인 정보 업데이트"""
        update_data = {
            "last_login_date": datetime.now(),
            "last_login_ip": login_ip,
            "login_attempt_count": 0,
            "date_modified": datetime.now()
        }
        
        self.Log.info(f"Updating login info for user: {users_id}")
        result = self.update(self.TABLE_NAME, update_data, {"users_id": users_id})
        return result > 0
    
    def increment_login_attempts(self, username: str) -> int:
        """로그인 시도 횟수 증가"""
        user = self.get_by_username(username)
        if not user:
            return 0
        
        new_count = (user.get('login_attempt_count', 0) or 0) + 1
        update_data = {
            "login_attempt_count": new_count,
            "date_modified": datetime.now()
        }
        
        # 5회 이상 실패시 계정 잠금
        if new_count >= 5:
            update_data["status_code"] = self.STATUS_LOCKED
            self.Log.warning(f"Account locked due to multiple failed attempts: {username}")
        
        self.update(self.TABLE_NAME, update_data, {"users_id": user['users_id']})
        return new_count
    
    def change_password(self, users_id: int, new_password: str, modified_by: str) -> bool:
        """비밀번호 변경"""
        salt = self._generate_salt()
        password_hash = self._hash_password(new_password, salt)
        
        update_data = {
            "password_hash": password_hash,
            "salt": salt,
            "password_change_date": datetime.now(),
            "password_reset_token": None,
            "password_reset_expires": None,
            "date_modified": datetime.now(),
            "modified_by": modified_by
        }
        
        self.Log.info(f"Changing password for user: {users_id}")
        result = self.update(self.TABLE_NAME, update_data, {"users_id": users_id})
        return result > 0
    
    def create_password_reset_token(self, email: str) -> Optional[str]:
        """비밀번호 재설정 토큰 생성"""
        user = self.get_by_email(email)
        if not user:
            self.Log.warning(f"User not found for password reset: {email}")
            return None
        
        token = self._generate_token()
        expires = datetime.now() + timedelta(hours=1)
        
        update_data = {
            "password_reset_token": token,
            "password_reset_expires": expires,
            "date_modified": datetime.now()
        }
        
        self.update(self.TABLE_NAME, update_data, {"users_id": user['users_id']})
        self.Log.info(f"Password reset token created for: {email}")
        return token
    
    def verify_email_token(self, token: str) -> bool:
        """이메일 인증 토큰 확인"""
        query = f"""
        UPDATE {self.TABLE_NAME}
        SET is_email_verified = TRUE,
            email_verification_token = NULL,
            date_modified = CURRENT_TIMESTAMP
        WHERE email_verification_token = %s
        RETURNING users_id
        """
        
        result = self.query(query, (token,), commit=True)
        if result:
            self.Log.info(f"Email verified for user_id: {result[0]['users_id']}")
            return True
        return False
    
    def get_active_users(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """활성 사용자 목록 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE is_active = TRUE AND status_code = %s
        ORDER BY date_created DESC
        LIMIT %s OFFSET %s
        """
        
        self.Log.info(f"Getting active users: limit={limit}, offset={offset}")
        return self.query(query, (self.STATUS_ACTIVE, limit, offset))
    
    def search_users(self, search_term: str, limit: int = 50) -> List[Dict]:
        """사용자 검색 (username, email, full_name)"""
        search_pattern = f"%{search_term}%"
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE (username ILIKE %s OR email ILIKE %s OR full_name ILIKE %s)
            AND is_active = TRUE
        ORDER BY username
        LIMIT %s
        """
        
        self.Log.info(f"Searching users with term: {search_term}")
        return self.query(query, (search_pattern, search_pattern, search_pattern, limit))
    
    def get_unverified_users(self, days_old: int = 7) -> List[Dict]:
        """미인증 사용자 목록 조회"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE is_email_verified = FALSE
            AND date_created < %s
            AND is_active = TRUE
        ORDER BY date_created
        """
        
        self.Log.info(f"Getting unverified users older than {days_old} days")
        return self.query(query, (cutoff_date,))
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """사용자 통계 조회"""
        query = f"""
        SELECT 
            COUNT(*) as total_users,
            COUNT(*) FILTER (WHERE is_active = TRUE) as active_users,
            COUNT(*) FILTER (WHERE is_email_verified = TRUE) as verified_users,
            COUNT(*) FILTER (WHERE status_code = %s) as locked_users,
            COUNT(*) FILTER (WHERE last_login_date > CURRENT_TIMESTAMP - INTERVAL '30 days') as recent_logins
        FROM {self.TABLE_NAME}
        """
        
        self.Log.info("Getting user statistics")
        result = self.query(query, (self.STATUS_LOCKED,), one=True)
        return result or {}
    
    def soft_delete_user(self, users_id: int, modified_by: str) -> bool:
        """사용자 소프트 삭제 (비활성화)"""
        update_data = {
            "is_active": False,
            "status_code": self.STATUS_DELETED,
            "date_modified": datetime.now(),
            "modified_by": modified_by
        }
        
        self.Log.info(f"Soft deleting user: {users_id}")
        result = self.update(self.TABLE_NAME, update_data, {"users_id": users_id})
        return result > 0
    
    def reactivate_user(self, users_id: int, modified_by: str) -> bool:
        """사용자 재활성화"""
        update_data = {
            "is_active": True,
            "status_code": self.STATUS_ACTIVE,
            "login_attempt_count": 0,
            "date_modified": datetime.now(),
            "modified_by": modified_by
        }
        
        self.Log.info(f"Reactivating user: {users_id}")
        result = self.update(self.TABLE_NAME, update_data, {"users_id": users_id})
        return result > 0

    def check_existing_usernames(self, usernames: List[str]) -> List[str]:
        """여러 username의 존재 여부 확인"""
        if not usernames:
            return []
            
        placeholders = ','.join(['%s'] * len(usernames))
        query = f"""
        SELECT username FROM {self.TABLE_NAME}
        WHERE username IN ({placeholders})
        """
        
        result = self.query(query, tuple(usernames))
        return [row['username'] for row in result] if result else []
    
    def check_existing_emails(self, emails: List[str]) -> List[str]:
        """여러 email의 존재 여부 확인"""
        if not emails:
            return []
            
        placeholders = ','.join(['%s'] * len(emails))
        query = f"""
        SELECT email FROM {self.TABLE_NAME}
        WHERE email IN ({placeholders})
        """
        
        result = self.query(query, tuple(emails))
        return [row['email'] for row in result] if result else []

# Example Usage
if __name__ == "__main__":
    # Logger 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # UsersTable 인스턴스 생성
    users = UsersTable(
        database="your_db",
        user="your_user", 
        password="your_password",
        host="127.0.0.1",
        port=5432
    )
    
    try:
        # 테이블 생성
        users.create_table_if_not_exists()
        
        # 새 사용자 생성
        new_user_id = users.create_user(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
            full_name="Test User",
            created_by="admin",
            departments="그룹1",
            phone="+1234567890"
        )
        print(f"Created new user with ID: {new_user_id}")
        
        # ID로 사용자 조회
        user = users.get_by_id(new_user_id)
        print(f"Retrieved user: {user}")
        
        # 비밀번호 확인
        is_valid = users.verify_password("testuser", "SecurePassword123!")
        print(f"Password valid: {is_valid}")
        
        # 로그인 정보 업데이트
        if new_user_id:
            users.update_login_info(new_user_id, "192.168.1.100")
            print("Login info updated")
        
        # 이메일로 사용자 검색
        user_by_email = users.get_by_email("test@example.com")
        print(f"User by email: {user_by_email}")
        
        # 활성 사용자 목록
        active_users = users.get_active_users(limit=10)
        print(f"Active users count: {len(active_users)}")
        
        # 사용자 검색
        search_results = users.search_users("test", limit=5)
        print(f"Search results: {len(search_results)} users found")
        
        # 비밀번호 재설정 토큰 생성
        reset_token = users.create_password_reset_token("test@example.com")
        print(f"Password reset token: {reset_token}")
        
        # 비밀번호 변경
        if new_user_id:
            password_changed = users.change_password(
                new_user_id, 
                "NewSecurePassword456!", 
                "admin"
            )
            print(f"Password changed: {password_changed}")
        
        # 사용자 통계
        stats = users.get_user_statistics()
        print(f"User statistics: {stats}")
        
        # 로그인 실패 시뮬레이션
        for i in range(3):
            attempts = users.increment_login_attempts("wronguser")
            print(f"Login attempt {i+1}: {attempts} total attempts")
        
        # 미인증 사용자 조회
        unverified = users.get_unverified_users(days_old=1)
        print(f"Unverified users: {len(unverified)}")
        
        # 사용자 비활성화
        if new_user_id:
            deleted = users.soft_delete_user(new_user_id, "admin")
            print(f"User soft deleted: {deleted}")
            
            # 사용자 재활성화
            reactivated = users.reactivate_user(new_user_id, "admin")
            print(f"User reactivated: {reactivated}")
            
    except Exception as e:
        users.Log.error(f"Example failed: {e}")
    finally:
        users.close()
