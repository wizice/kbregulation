#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Admin Password Reset Script
관리자 비밀번호를 재설정하는 스크립트
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from api.query_users_v2 import UsersTable
from api.timescaledb_manager_v2 import get_db_manager
from settings import settings

def reset_admin_password():
    """관리자 비밀번호 재설정"""
    
    # DB 설정
    db_config = {
        "database": settings.DB_NAME,
        "user": settings.DB_USER, 
        "password": settings.DB_PASSWORD,
        "host": settings.DB_HOST,
        "port": settings.DB_PORT
    }
    
    print(f"데이터베이스 연결: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    try:
        # DB 매니저 및 Users 테이블 초기화
        db_manager = get_db_manager(db_config)
        users_table = UsersTable(db_manager=db_manager)
        
        users_table.connect()
        print("데이터베이스 연결 성공")
        
        # admin 사용자 확인
        admin_user = users_table.get_by_username('admin')
        if not admin_user:
            print("❌ admin 사용자를 찾을 수 없습니다.")
            users_table.close()
            return False
            
        print("기존 admin 사용자를 찾았습니다:")
        print(f"- Username: {admin_user['username']}")
        print(f"- Email: {admin_user['email']}")
        print(f"- Role: {admin_user.get('role', 'N/A')}")
        
        # 새 비밀번호 설정
        new_password = "admin123!@#"
        
        # 비밀번호 변경
        success = users_table.change_password(admin_user['users_id'], new_password, 'system')
        
        if success:
            print("✅ 관리자 비밀번호가 성공적으로 변경되었습니다.")
            print(f"\n🔐 새로운 로그인 정보:")
            print(f"   아이디: admin")
            print(f"   비밀번호: {new_password}")
        else:
            print("❌ 비밀번호 변경에 실패했습니다.")
            
        users_table.close()
        return success
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        if 'users_table' in locals():
            users_table.close()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("세브란스 편집기 - 관리자 비밀번호 재설정")
    print("=" * 50)
    
    success = reset_admin_password()
    
    if success:
        print("\n✅ 비밀번호 재설정이 완료되었습니다!")
        print("\n🚀 이제 http://localhost:8800/login 에서 로그인할 수 있습니다.")
    else:
        print("\n❌ 비밀번호 재설정이 실패했습니다.")
        sys.exit(1)