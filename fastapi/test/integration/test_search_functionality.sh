#!/bin/bash

# 검색 기능 테스트 스크립트
# 사용법: ./test_search_functionality.sh

echo "================================================="
echo "세브란스 편집기 - 검색 기능 테스트"
echo "================================================="

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 테스트 서버 정보
BASE_URL="http://localhost:8800"
ADMIN_USER="admin"
ADMIN_PASS="admin123!@#"

# 쿠키 파일
COOKIE_FILE="/tmp/test_search_cookies.txt"

# 테스트 결과 카운터
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 함수: 테스트 결과 출력
print_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"

    ((TOTAL_TESTS++))

    if [ "$result" = "PASS" ]; then
        ((PASSED_TESTS++))
        echo -e "${GREEN}✓${NC} $test_name - ${GREEN}PASS${NC}"
        if [ -n "$message" ]; then
            echo "  └─ $message"
        fi
    else
        ((FAILED_TESTS++))
        echo -e "${RED}✗${NC} $test_name - ${RED}FAIL${NC}"
        if [ -n "$message" ]; then
            echo "  └─ $message"
        fi
    fi
}

# 함수: JSON 값 추출
get_json_value() {
    echo "$1" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data$2 if '$2' else json.dumps(data, indent=2))"
}

# 1. 로그인
echo ""
echo "1. 관리자 로그인..."
echo "=================================="

LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${ADMIN_USER}\",\"password\":\"${ADMIN_PASS}\"}" \
    -c "$COOKIE_FILE" \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$LOGIN_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$LOGIN_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    print_result "로그인" "PASS" "HTTP $HTTP_CODE"
else
    print_result "로그인" "FAIL" "HTTP $HTTP_CODE"
    echo "$RESPONSE_BODY"
    exit 1
fi

# 2. 전체 규정 목록 조회
echo ""
echo "2. 전체 규정 목록 조회..."
echo "=================================="

ALL_REGULATIONS=$(curl -s -X GET "${BASE_URL}/api/v1/regulations/current" \
    -b "$COOKIE_FILE" \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$ALL_REGULATIONS" | tail -n 1)
RESPONSE_BODY=$(echo "$ALL_REGULATIONS" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL_COUNT=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data['data']) if 'data' in data else 0)")
    print_result "전체 규정 목록 조회" "PASS" "총 ${TOTAL_COUNT}개 규정"
else
    print_result "전체 규정 목록 조회" "FAIL" "HTTP $HTTP_CODE"
fi

# 3. JavaScript 검색 함수 테스트 (Headless 브라우저 대신 API 직접 테스트)
echo ""
echo "3. 검색 필터 테스트..."
echo "=================================="

# 3.1 키워드 검색 테스트
echo "  3.1 키워드 검색 테스트"
TEST_KEYWORDS=("환자" "안전" "진료" "규정")

for keyword in "${TEST_KEYWORDS[@]}"; do
    SEARCH_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/v1/regulations/search?keyword=${keyword}" \
        -b "$COOKIE_FILE" \
        -w "\n%{http_code}")

    HTTP_CODE=$(echo "$SEARCH_RESPONSE" | tail -n 1)

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ]; then
        print_result "    키워드 검색: '$keyword'" "PASS" ""
    else
        print_result "    키워드 검색: '$keyword'" "FAIL" "HTTP $HTTP_CODE"
    fi
done

# 3.2 부서 필터 API 테스트
echo "  3.2 부서 필터 옵션 로드 테스트"
DEPT_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/v1/dept/search?search_keyword=&is_for_filter=true" \
    -b "$COOKIE_FILE" \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$DEPT_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$DEPT_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    DEPT_COUNT=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('data', [])))" 2>/dev/null || echo "0")
    print_result "    부서 목록 로드" "PASS" "${DEPT_COUNT}개 부서"
else
    print_result "    부서 목록 로드" "FAIL" "HTTP $HTTP_CODE"
fi

# 4. 페이지 접근 테스트
echo ""
echo "4. 페이지 접근 및 JavaScript 로드 테스트..."
echo "=================================="

# 4.1 현행 규정 페이지 접근
PAGE_RESPONSE=$(curl -s -X GET "${BASE_URL}/regulations/current" \
    -b "$COOKIE_FILE" \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$PAGE_RESPONSE" | tail -n 1)
PAGE_BODY=$(echo "$PAGE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    # JavaScript 파일 로드 확인
    if echo "$PAGE_BODY" | grep -q "rule-editor.js"; then
        print_result "rule-editor.js 로드" "PASS" ""
    else
        print_result "rule-editor.js 로드" "FAIL" "스크립트를 찾을 수 없음"
    fi

    # 검색 요소 확인
    if echo "$PAGE_BODY" | grep -q 'id="searchInput"'; then
        print_result "검색 입력 필드 존재" "PASS" ""
    else
        print_result "검색 입력 필드 존재" "FAIL" ""
    fi

    if echo "$PAGE_BODY" | grep -q 'id="classificationFilter"'; then
        print_result "분류 필터 존재" "PASS" ""
    else
        print_result "분류 필터 존재" "FAIL" ""
    fi

    if echo "$PAGE_BODY" | grep -q 'id="departmentFilter"'; then
        print_result "부서 필터 존재" "PASS" ""
    else
        print_result "부서 필터 존재" "FAIL" ""
    fi

    if echo "$PAGE_BODY" | grep -q 'id="statusFilter"'; then
        print_result "상태 필터 존재" "PASS" ""
    else
        print_result "상태 필터 존재" "FAIL" ""
    fi

    if echo "$PAGE_BODY" | grep -q 'id="periodFilter"'; then
        print_result "기간 필터 존재" "PASS" ""
    else
        print_result "기간 필터 존재" "FAIL" ""
    fi

    if echo "$PAGE_BODY" | grep -q 'onclick="RuleEditor.searchRegulations()"'; then
        print_result "검색 버튼 이벤트 연결" "PASS" ""
    else
        print_result "검색 버튼 이벤트 연결" "FAIL" ""
    fi
else
    print_result "현행 규정 페이지 접근" "FAIL" "HTTP $HTTP_CODE"
fi

# 5. JavaScript 함수 존재 확인
echo ""
echo "5. JavaScript 함수 검증..."
echo "=================================="

JS_FILE="/home/wizice/regulation/fastapi/static/js/rule-editor.js"

if [ -f "$JS_FILE" ]; then
    # searchRegulations 함수 확인
    if grep -q "searchRegulations()" "$JS_FILE"; then
        print_result "searchRegulations() 함수 존재" "PASS" ""

        # ID 매칭 확인
        if grep -q "getElementById('searchInput')" "$JS_FILE"; then
            print_result "searchInput ID 매칭" "PASS" ""
        else
            print_result "searchInput ID 매칭" "FAIL" ""
        fi

        if grep -q "getElementById('departmentFilter')" "$JS_FILE"; then
            print_result "departmentFilter ID 매칭" "PASS" ""
        else
            print_result "departmentFilter ID 매칭" "FAIL" ""
        fi

        if grep -q "getElementById('classificationFilter')" "$JS_FILE"; then
            print_result "classificationFilter ID 매칭" "PASS" ""
        else
            print_result "classificationFilter ID 매칭" "FAIL" ""
        fi
    else
        print_result "searchRegulations() 함수 존재" "FAIL" ""
    fi

    # loadFilters 함수 확인
    if grep -q "loadFilters()" "$JS_FILE"; then
        print_result "loadFilters() 함수 존재" "PASS" ""
    else
        print_result "loadFilters() 함수 존재" "FAIL" ""
    fi
else
    print_result "rule-editor.js 파일 존재" "FAIL" "파일을 찾을 수 없음"
fi

# 6. 테스트 결과 요약
echo ""
echo "================================================="
echo "테스트 결과 요약"
echo "================================================="
echo -e "총 테스트: ${TOTAL_TESTS}"
echo -e "성공: ${GREEN}${PASSED_TESTS}${NC}"
echo -e "실패: ${RED}${FAILED_TESTS}${NC}"

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "\n${GREEN}✓ 모든 테스트가 성공했습니다!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ 일부 테스트가 실패했습니다.${NC}"
    exit 1
fi

# 쿠키 파일 정리
rm -f "$COOKIE_FILE"