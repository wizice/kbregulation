#!/usr/bin/env python3
"""
검색 엔진 간단 테스트
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8800"

# 1. 로그인
print("1. 로그인 중...")
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"username": "admin", "password": "admin123!@#"}
)

if login_response.status_code == 200:
    print("✓ 로그인 성공")
    # Get session token from response
    session_token = login_response.json().get('access_token')
    # Also get cookies if any
    cookies = login_response.cookies
    # Create headers with authorization
    headers = {
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json"
    }
else:
    print("✗ 로그인 실패")
    print(login_response.text)
    sys.exit(1)

# 2. 색인 상태 확인
print("\n2. 색인 상태 확인...")
status_response = requests.get(
    f"{BASE_URL}/api/v1/search/status",
    headers=headers,
    cookies=cookies
)

if status_response.status_code == 200:
    data = status_response.json()
    print(f"✓ 전체: {data['stats']['total_documents']}개")
    print(f"  색인: {data['stats']['indexed_documents']}개")
    print(f"  대기: {data['stats']['pending_documents']}개")
    print(f"  오류: {data['stats']['error_documents']}개")
else:
    print("✗ 상태 조회 실패")
    print(status_response.text)

# 3. 재색인 실행 (작은 테스트)
print("\n3. 재색인 실행 중...")
reindex_response = requests.post(
    f"{BASE_URL}/api/v1/search/reindex-all",
    headers=headers,
    cookies=cookies
)

if reindex_response.status_code == 200:
    data = reindex_response.json()
    print(f"✓ 재색인 완료")
    print(f"  전체: {data['total']}개")
    print(f"  성공: {data['indexed']}개")
    print(f"  실패: {data['errors']}개")

    if data.get('error_details'):
        print("\n  오류 상세 (처음 3개):")
        for err in data['error_details'][:3]:
            print(f"    - [{err['rule_id']}] {err['rule_name']}: {err['error']}")
else:
    print("✗ 재색인 실패")
    print(reindex_response.text)

# 4. 검색 테스트
print("\n4. 검색 테스트...")
search_response = requests.get(
    f"{BASE_URL}/api/v1/search/query",
    params={"q": "규정", "limit": 5},
    headers=headers,
    cookies=cookies
)

if search_response.status_code == 200:
    data = search_response.json()
    if data.get('success'):
        print(f"✓ 검색 성공: {data['total']}개 결과")
        if data['results']:
            print("  검색 결과 샘플:")
            for r in data['results'][:3]:
                print(f"    - {r['title']}")
    else:
        print("✗ 검색 실패:", data.get('message'))
elif search_response.status_code == 400:
    print("✗ 검색 실패: 검색어가 너무 짧습니다 (2자 이상)")
else:
    print("✗ 검색 실패")
    print(search_response.text)

print("\n테스트 완료!")