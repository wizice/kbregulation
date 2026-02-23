#!/usr/bin/env python3
"""
검색 엔진 고급 테스트
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8800"

# 로그인
print("로그인 중...")
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"username": "admin", "password": "admin123!@#"}
)

if login_response.status_code == 200:
    session_token = login_response.json().get('access_token')
    cookies = login_response.cookies
    headers = {
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json"
    }
    print("✓ 로그인 성공\n")
else:
    print("✗ 로그인 실패")
    sys.exit(1)

print("=" * 60)
print("검색 기능 테스트")
print("=" * 60)

# 1. 간단한 키워드 검색
print("\n1. 키워드 검색: '환자'")
response = requests.get(
    f"{BASE_URL}/api/v1/search/query",
    params={"q": "환자", "limit": 3},
    headers=headers,
    cookies=cookies
)
if response.status_code == 200:
    data = response.json()
    print(f"   결과: {data['total']}개 문서")
    for r in data['results'][:3]:
        print(f"   - {r['title']} ({r['department']})")

# 2. 부서 필터 검색
print("\n2. 부서 필터: '감염관리실'에서 '관리' 검색")
response = requests.get(
    f"{BASE_URL}/api/v1/search/query",
    params={"q": "관리", "department": "감염관리실", "limit": 3},
    headers=headers,
    cookies=cookies
)
if response.status_code == 200:
    data = response.json()
    print(f"   결과: {data['total']}개 문서")
    for r in data['results'][:3]:
        print(f"   - {r['title']}")

# 3. 분류 필터 검색
print("\n3. 분류 필터: '1.' (안전보장목표)으로 시작하는 문서")
response = requests.get(
    f"{BASE_URL}/api/v1/search/query",
    params={"q": "환자", "classification": "1", "limit": 3},
    headers=headers,
    cookies=cookies
)
if response.status_code == 200:
    data = response.json()
    print(f"   결과: {data['total']}개 문서")
    for r in data['results'][:3]:
        print(f"   - {r['title']} (분류: {r['classification']})")

# 4. 긴 검색어 테스트
print("\n4. 긴 검색어: '환자 안전 관리'")
response = requests.get(
    f"{BASE_URL}/api/v1/search/query",
    params={"q": "환자 안전 관리", "limit": 3},
    headers=headers,
    cookies=cookies
)
if response.status_code == 200:
    data = response.json()
    print(f"   결과: {data['total']}개 문서")
    for r in data['results'][:3]:
        print(f"   - {r['title']}")

# 5. 검색 통계 확인
print("\n" + "=" * 60)
print("검색 통계")
print("=" * 60)

response = requests.get(
    f"{BASE_URL}/api/v1/search/stats",
    headers=headers,
    cookies=cookies
)
if response.status_code == 200:
    data = response.json()
    print("\n부서별 색인 문서 (상위 5개):")
    for dept in data['department_stats'][:5]:
        print(f"   {dept['department']:20} : {dept['count']:3}개")

    print("\n최근 색인된 문서:")
    for doc in data['recent_indexed'][:3]:
        print(f"   - {doc['title']}")

print("\n테스트 완료!")