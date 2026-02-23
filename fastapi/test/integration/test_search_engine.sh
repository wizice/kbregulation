#!/bin/bash

# 검색 엔진 테스트 스크립트
# 색인 및 검색 기능 테스트

BASE_URL="http://localhost:8800"
COOKIE_FILE="/tmp/test_cookie.txt"

echo "=========================================="
echo "검색 엔진 통합 테스트 시작"
echo "=========================================="

# 1. 로그인
echo -e "\n[1/5] 로그인 중..."
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123!@#"}' \
    -c "$COOKIE_FILE")

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo "✓ 로그인 성공"
else
    echo "✗ 로그인 실패"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

# 2. 색인 상태 확인
echo -e "\n[2/5] 색인 상태 확인 중..."
STATUS_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/v1/search/status" \
    -H "Content-Type: application/json" \
    -b "$COOKIE_FILE")

if echo "$STATUS_RESPONSE" | grep -q "success.*true"; then
    echo "✓ 색인 상태 조회 성공"
    echo "$STATUS_RESPONSE" | python3 -m json.tool | grep -E "(total_documents|indexed_documents|pending_documents)"
else
    echo "✗ 색인 상태 조회 실패"
    echo "$STATUS_RESPONSE"
fi

# 3. 전체 재색인 실행
echo -e "\n[3/5] 전체 재색인 실행 중... (시간이 걸릴 수 있습니다)"
REINDEX_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/search/reindex-all" \
    -H "Content-Type: application/json" \
    -b "$COOKIE_FILE")

if echo "$REINDEX_RESPONSE" | grep -q "success.*true"; then
    echo "✓ 재색인 완료"
    echo "$REINDEX_RESPONSE" | python3 -m json.tool | grep -E "(total|indexed|errors)"
else
    echo "✗ 재색인 실패"
    echo "$REINDEX_RESPONSE"
fi

# 4. 검색 테스트
echo -e "\n[4/5] 검색 기능 테스트 중..."

# 4-1. 간단한 검색
echo "  - 키워드 검색 테스트..."
SEARCH_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/v1/search/query?q=규정&limit=5" \
    -H "Content-Type: application/json" \
    -b "$COOKIE_FILE")

if echo "$SEARCH_RESPONSE" | grep -q "success.*true"; then
    echo "  ✓ 키워드 검색 성공"
    TOTAL=$(echo "$SEARCH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total', 0))")
    echo "    검색 결과: ${TOTAL}개"
else
    echo "  ✗ 키워드 검색 실패"
fi

# 4-2. 부서 필터 검색
echo "  - 부서 필터 검색 테스트..."
DEPT_SEARCH=$(curl -s -X GET "${BASE_URL}/api/v1/search/query?q=관리&department=인사팀&limit=5" \
    -H "Content-Type: application/json" \
    -b "$COOKIE_FILE")

if echo "$DEPT_SEARCH" | grep -q "success.*true"; then
    echo "  ✓ 부서 필터 검색 성공"
else
    echo "  ✗ 부서 필터 검색 실패"
fi

# 5. 검색 통계 확인
echo -e "\n[5/5] 검색 통계 확인 중..."
STATS_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/v1/search/stats" \
    -H "Content-Type: application/json" \
    -b "$COOKIE_FILE")

if echo "$STATS_RESPONSE" | grep -q "success.*true"; then
    echo "✓ 검색 통계 조회 성공"
    echo "$STATS_RESPONSE" | python3 -m json.tool | head -20
else
    echo "✗ 검색 통계 조회 실패"
fi

# 정리
rm -f "$COOKIE_FILE"

echo -e "\n=========================================="
echo "검색 엔진 통합 테스트 완료"
echo "=========================================="