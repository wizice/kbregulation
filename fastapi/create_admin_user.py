#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Admin User Creation Script
관리자 계정을 생성하는 스크립트
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from api.query_users_v2 import UsersTable
from api.timescaledb_manager_v2 import get_db_manager
from settings import settings

def create_admin_user():
    """관리자 사용자 계정 생성"""
    
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
        
        # 기존 admin 사용자 확인
        existing_admin = users_table.get_by_username('admin')
        if existing_admin:
            print("기존 admin 사용자가 이미 존재합니다:")
            print(f"- Username: {existing_admin['username']}")
            print(f"- Email: {existing_admin['email']}")
            print(f"- Role: {existing_admin.get('role', 'N/A')}")
            
            # 비밀번호 변경 옵션
            change_password = input("비밀번호를 변경하시겠습니까? (y/N): ").strip().lower()
            if change_password == 'y':
                new_password = input("새 비밀번호를 입력하세요: ").strip()
                if new_password:
                    success = users_table.change_password(existing_admin['users_id'], new_password, 'admin')
                    if success:
                        print("✅ 관리자 비밀번호가 성공적으로 변경되었습니다.")
                    else:
                        print("❌ 비밀번호 변경에 실패했습니다.")
                else:
                    print("비밀번호가 입력되지 않았습니다.")
            
        else:
            print("새로운 admin 사용자를 생성합니다...")
            
            # 관리자 계정 정보
            admin_data = {
                'username': 'admin',
                'email': 'admin@severance.yonsei.ac.kr',
                'password': 'admin123!@#',  # 기본 비밀번호
                'full_name': '시스템 관리자',
                'phone': None,
                'role': 'admin',
                'created_by': 'system'
            }
            
            print(f"관리자 정보:")
            print(f"- Username: {admin_data['username']}")
            print(f"- Email: {admin_data['email']}")
            print(f"- Password: {admin_data['password']}")
            print(f"- Role: {admin_data['role']}")
            
            # 사용자 생성
            user_id = users_table.create_user(
                username=admin_data['username'],
                email=admin_data['email'],
                password=admin_data['password'],
                full_name=admin_data['full_name'],
                phone=admin_data['phone'],
                created_by=admin_data['created_by']
            )
            
            if user_id:
                # 관리자 역할 설정
                users_table.update_user_role(user_id, 'admin', 'system')
                
                print(f"✅ 관리자 계정이 성공적으로 생성되었습니다. (ID: {user_id})")
                print("\n🔐 로그인 정보:")
                print(f"   아이디: admin")
                print(f"   비밀번호: admin123!@#")
                print("\n⚠️  보안을 위해 첫 로그인 후 반드시 비밀번호를 변경하세요!")
                
            else:
                print("❌ 관리자 계정 생성에 실패했습니다.")
                
        users_table.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        if 'users_table' in locals():
            users_table.close()
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("세브란스 편집기 - 관리자 계정 생성")
    print("=" * 50)
    
    success = create_admin_user()
    
    if success:
        print("\n✅ 작업이 완료되었습니다!")
        print("\n🚀 이제 http://localhost:8800/login 에서 로그인할 수 있습니다.")
    else:
        print("\n❌ 작업이 실패했습니다.")
        sys.exit(1)