#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
유사어 API 테스트

실행 방법:
    cd /home/wizice/regulation/fastapi
    python3 test/synonyms/test_synonyms_api.py

테스트 항목:
    1. 목록 조회 (GET /api/synonyms)
    2. 상세 조회 (GET /api/synonyms/{id})
    3. 등록 (POST /api/synonyms)
    4. 수정 (PUT /api/synonyms/{id})
    5. 삭제 (DELETE /api/synonyms/{id})
    6. JSON 내보내기 (GET /api/synonyms/export/json)
    7. 유사어 확장 (GET /api/synonyms/expand)
    8. JSON 검증 (POST /api/synonyms/validate)
    9. 통계 조회 (GET /api/synonyms/stats)
"""

import requests
import json
import sys

# 기본 설정
BASE_URL = "http://localhost:8800"
API_BASE = f"{BASE_URL}/api/synonyms"

# 테스트용 쿠키 (실제 환경에서는 로그인 후 쿠키 사용)
COOKIES = {}


def print_result(test_name: str, success: bool, detail: str = ""):
    """테스트 결과 출력"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}")
    if detail and not success:
        print(f"       └── {detail}")


def test_list_synonyms():
    """1. 목록 조회 테스트"""
    try:
        response = requests.get(f"{API_BASE}/", cookies=COOKIES)
        data = response.json()

        success = response.status_code == 200 and isinstance(data, list)
        print_result("목록 조회", success, f"응답 코드: {response.status_code}, 결과 수: {len(data) if success else 'N/A'}")

        if success and len(data) > 0:
            print(f"       └── 첫 번째 항목: {data[0]['group_name']} ({len(data[0]['synonyms'])}개 유사어)")

        return success
    except Exception as e:
        print_result("목록 조회", False, str(e))
        return False


def test_stats():
    """2. 통계 조회 테스트"""
    try:
        response = requests.get(f"{API_BASE}/stats", cookies=COOKIES)
        data = response.json()

        success = response.status_code == 200 and "total_groups" in data
        print_result("통계 조회", success, f"전체 그룹: {data.get('total_groups', 'N/A')}, 활성: {data.get('active_groups', 'N/A')}")

        return success
    except Exception as e:
        print_result("통계 조회", False, str(e))
        return False


def test_get_synonym():
    """3. 상세 조회 테스트"""
    try:
        # 먼저 목록에서 첫 번째 ID 가져오기
        list_response = requests.get(f"{API_BASE}/", cookies=COOKIES)
        items = list_response.json()

        if not items:
            print_result("상세 조회", False, "조회할 항목 없음")
            return False

        synonym_id = items[0]['synonym_id']

        response = requests.get(f"{API_BASE}/{synonym_id}", cookies=COOKIES)
        data = response.json()

        success = response.status_code == 200 and data.get('synonym_id') == synonym_id
        print_result("상세 조회", success, f"ID: {synonym_id}, 그룹명: {data.get('group_name', 'N/A')}")

        return success
    except Exception as e:
        print_result("상세 조회", False, str(e))
        return False


def test_create_synonym():
    """4. 등록 테스트"""
    try:
        test_data = {
            "group_name": "테스트_유사어",
            "synonyms": ["테스트1", "테스트2", "테스트3"],
            "description": "API 테스트용 유사어",
            "is_active": True,
            "priority": 999
        }

        response = requests.post(
            f"{API_BASE}/",
            json=test_data,
            params={"created_by": "test_script"},
            cookies=COOKIES
        )
        data = response.json()

        success = response.status_code == 200 and data.get('group_name') == "테스트_유사어"
        print_result("등록", success, f"생성 ID: {data.get('synonym_id', 'N/A')}")

        # 생성된 ID 반환 (나중에 삭제용)
        return data.get('synonym_id') if success else None
    except Exception as e:
        print_result("등록", False, str(e))
        return None


def test_update_synonym(synonym_id: int):
    """5. 수정 테스트"""
    if not synonym_id:
        print_result("수정", False, "수정할 ID 없음")
        return False

    try:
        update_data = {
            "synonyms": ["테스트1", "테스트2", "테스트3", "테스트4_수정됨"],
            "description": "수정된 설명",
            "priority": 888
        }

        response = requests.put(
            f"{API_BASE}/{synonym_id}",
            json=update_data,
            params={"updated_by": "test_script"},
            cookies=COOKIES
        )
        data = response.json()

        success = response.status_code == 200 and data.get('priority') == 888
        print_result("수정", success, f"수정된 우선순위: {data.get('priority', 'N/A')}")

        return success
    except Exception as e:
        print_result("수정", False, str(e))
        return False


def test_export_json():
    """6. JSON 내보내기 테스트"""
    try:
        # Elasticsearch 형식
        response = requests.get(
            f"{API_BASE}/export/json",
            params={"format": "elasticsearch"},
            cookies=COOKIES
        )
        data = response.json()

        success = response.status_code == 200 and "synonyms" in data
        print_result("JSON 내보내기 (ES)", success, f"유사어 그룹 수: {data.get('count', 'N/A')}")

        if success and data.get('synonyms'):
            print(f"       └── 예시: {data['synonyms'][0][:50]}...")

        return success
    except Exception as e:
        print_result("JSON 내보내기", False, str(e))
        return False


def test_expand_query():
    """7. 유사어 확장 테스트"""
    try:
        response = requests.get(
            f"{API_BASE}/expand",
            params={"q": "환자"},
            cookies=COOKIES
        )
        data = response.json()

        success = response.status_code == 200 and "synonyms" in data
        print_result("유사어 확장", success, f"확장됨: {data.get('expanded', 'N/A')}, 결과 수: {len(data.get('synonyms', []))}")

        if success and data.get('expanded'):
            print(f"       └── 유사어: {', '.join(data['synonyms'][:5])}...")

        return success
    except Exception as e:
        print_result("유사어 확장", False, str(e))
        return False


def test_validate_json():
    """8. JSON 검증 테스트"""
    try:
        # 유효한 데이터
        valid_data = {
            "synonyms_data": [
                {"group_name": "검증테스트1", "synonyms": ["가", "나", "다"]},
                {"group_name": "검증테스트2", "synonyms": ["라", "마", "바"]}
            ]
        }

        response = requests.post(
            f"{API_BASE}/validate",
            json=valid_data,
            cookies=COOKIES
        )
        data = response.json()

        success = response.status_code == 200 and data.get('is_valid') == True
        print_result("JSON 검증 (유효)", success, f"유효: {data.get('valid_count', 0)}개")

        # 유효하지 않은 데이터
        invalid_data = {
            "synonyms_data": [
                {"group_name": "", "synonyms": []},  # 빈 그룹명, 빈 유사어
                {"synonyms": ["가", "나"]}  # group_name 없음
            ]
        }

        response2 = requests.post(
            f"{API_BASE}/validate",
            json=invalid_data,
            cookies=COOKIES
        )
        data2 = response2.json()

        success2 = response2.status_code == 200 and data2.get('is_valid') == False
        print_result("JSON 검증 (오류)", success2, f"오류: {len(data2.get('errors', []))}개")

        return success and success2
    except Exception as e:
        print_result("JSON 검증", False, str(e))
        return False


def test_delete_synonym(synonym_id: int):
    """9. 삭제 테스트"""
    if not synonym_id:
        print_result("삭제", False, "삭제할 ID 없음")
        return False

    try:
        # 물리적 삭제
        response = requests.delete(
            f"{API_BASE}/{synonym_id}",
            params={"permanent": True},
            cookies=COOKIES
        )
        data = response.json()

        success = response.status_code == 200 and data.get('success') == True
        print_result("삭제", success, f"삭제 ID: {synonym_id}")

        return success
    except Exception as e:
        print_result("삭제", False, str(e))
        return False


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("유사어 API 테스트")
    print("=" * 60)
    print(f"대상 서버: {BASE_URL}")
    print("-" * 60)

    results = []

    # 1. 목록 조회
    results.append(test_list_synonyms())

    # 2. 통계 조회
    results.append(test_stats())

    # 3. 상세 조회
    results.append(test_get_synonym())

    # 4. 등록
    created_id = test_create_synonym()
    results.append(created_id is not None)

    # 5. 수정
    results.append(test_update_synonym(created_id))

    # 6. JSON 내보내기
    results.append(test_export_json())

    # 7. 유사어 확장
    results.append(test_expand_query())

    # 8. JSON 검증
    results.append(test_validate_json())

    # 9. 삭제 (테스트 데이터 정리)
    results.append(test_delete_synonym(created_id))

    # 결과 요약
    print("-" * 60)
    passed = sum(results)
    total = len(results)
    print(f"결과: {passed}/{total} 테스트 통과")

    if passed == total:
        print("✅ 모든 테스트 통과!")
        return 0
    else:
        print("❌ 일부 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
