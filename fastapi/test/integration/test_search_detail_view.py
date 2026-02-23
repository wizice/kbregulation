#!/usr/bin/env python3
"""
검색 결과 상세보기 API 테스트
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8800"

# 로그인
print("1. 로그인 중...")
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

# 2. 검색 실행
print("2. 검색 실행...")
search_response = requests.get(
    f"{BASE_URL}/api/v1/search/query",
    params={"q": "환자", "limit": 1},
    headers=headers,
    cookies=cookies
)

if search_response.status_code == 200:
    data = search_response.json()
    if data.get('success') and data['results']:
        rule_id = data['results'][0]['rule_id']
        rule_title = data['results'][0]['title']
        print(f"✓ 검색 성공: {rule_title} (ID: {rule_id})\n")

        # 3. 상세 내용 조회
        print("3. 상세 내용 조회...")
        content_response = requests.get(
            f"{BASE_URL}/api/v1/regulation/content/{rule_id}",
            headers=headers,
            cookies=cookies
        )

        if content_response.status_code == 200:
            content_data = content_response.json()
            print("✓ 상세 내용 조회 성공")

            # 반환 데이터 키 확인
            print("\n   반환된 최상위 키:")
            for key in list(content_data.keys())[:10]:
                print(f"     - {key}")

            # 문서정보가 있는지 확인
            if '문서정보' in content_data:
                doc_info = content_data['문서정보']
                print(f"\n   제목: {doc_info.get('규정명', 'N/A')}")
                print(f"   부서: {doc_info.get('담당부서', 'N/A')}")
                print(f"   분류: {doc_info.get('분류번호', 'N/A')}")
            else:
                print("   문서정보 필드 없음")

            # content 필드 확인
            if 'content' in content_data:
                content_type = type(content_data['content'])
                print(f"   내용 타입: {content_type.__name__}")

                if isinstance(content_data['content'], dict):
                    if '문서정보' in content_data['content']:
                        print("   ✓ JSON 형식 문서정보 존재")
                    if '조문내용' in content_data['content']:
                        articles = content_data['content']['조문내용']
                        print(f"   ✓ 조문 {len(articles)}개 존재")
        else:
            print(f"✗ 상세 내용 조회 실패: {content_response.status_code}")
            print(content_response.text)
    else:
        print("✗ 검색 결과 없음")
else:
    print("✗ 검색 실패")

print("\n테스트 완료!")