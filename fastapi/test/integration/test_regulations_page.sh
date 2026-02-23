#!/bin/bash

# 테스트 스크립트: 새로운 regulations/current 페이지 테스트
# 실행 방법: ./test/integration/test_regulations_page.sh

echo "============================================="
echo "새로운 regulations/current 페이지 테스트"
echo "============================================="

BASE_URL="https://policyeditor.wizice.com:8443"
COOKIE_FILE="/tmp/test_cookies.txt"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 로그인
echo -e "\n${YELLOW}1. 로그인 테스트${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123!@#"}' \
    -c "$COOKIE_FILE" \
    -k)

if echo "$LOGIN_RESPONSE" | grep -q '"access_token"'; then
    echo -e "${GREEN}✓ 로그인 성공${NC}"
else
    echo -e "${RED}✗ 로그인 실패${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

# 2. 새로운 regulations/current 페이지 접근 테스트
echo -e "\n${YELLOW}2. regulations/current 페이지 접근 테스트${NC}"
PAGE_RESPONSE=$(curl -s -X GET "$BASE_URL/regulations/current" \
    -b "$COOKIE_FILE" \
    -k \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$PAGE_RESPONSE" | tail -n 1)
PAGE_CONTENT=$(echo "$PAGE_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ 페이지 접근 성공 (HTTP $HTTP_CODE)${NC}"

    # 페이지 내 필수 요소 체크
    if echo "$PAGE_CONTENT" | grep -q "사규자료 현행화 편집기"; then
        echo -e "${GREEN}✓ 페이지 타이틀 확인${NC}"
    else
        echo -e "${RED}✗ 페이지 타이틀 미확인${NC}"
    fi

    if echo "$PAGE_CONTENT" | grep -q "현행 사규목록"; then
        echo -e "${GREEN}✓ 현행 사규목록 탭 확인${NC}"
    else
        echo -e "${RED}✗ 현행 사규목록 탭 미확인${NC}"
    fi

    if echo "$PAGE_CONTENT" | grep -q "연혁 목록"; then
        echo -e "${GREEN}✓ 연혁 목록 탭 확인${NC}"
    else
        echo -e "${RED}✗ 연혁 목록 탭 미확인${NC}"
    fi

    if echo "$PAGE_CONTENT" | grep -q "분류 관리"; then
        echo -e "${GREEN}✓ 분류 관리 탭 확인${NC}"
    else
        echo -e "${RED}✗ 분류 관리 탭 미확인${NC}"
    fi

    if echo "$PAGE_CONTENT" | grep -q "부서 관리"; then
        echo -e "${GREEN}✓ 부서 관리 탭 확인${NC}"
    else
        echo -e "${RED}✗ 부서 관리 탭 미확인${NC}"
    fi
else
    echo -e "${RED}✗ 페이지 접근 실패 (HTTP $HTTP_CODE)${NC}"
fi

# 3. 현행 사규목록 API 테스트
echo -e "\n${YELLOW}3. 현행 사규목록 API 테스트${NC}"
API_RESPONSE=$(curl -s -X GET "$BASE_URL/regulations/api/current" \
    -b "$COOKIE_FILE" \
    -k)

if echo "$API_RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✓ API 호출 성공${NC}"

    # 데이터 개수 확인
    TOTAL_COUNT=$(echo "$API_RESPONSE" | grep -o '"total_count":[0-9]*' | cut -d: -f2)
    echo -e "${GREEN}✓ 조회된 규정 수: $TOTAL_COUNT${NC}"
else
    echo -e "${RED}✗ API 호출 실패${NC}"
    echo "Response: $API_RESPONSE"
fi

# 4. 연혁목록 API 테스트
echo -e "\n${YELLOW}4. 연혁목록 API 테스트${NC}"
HISTORY_RESPONSE=$(curl -s -X GET "$BASE_URL/regulations/api/history" \
    -b "$COOKIE_FILE" \
    -k)

if echo "$HISTORY_RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✓ 연혁목록 API 호출 성공${NC}"

    # 데이터 개수 확인
    HISTORY_COUNT=$(echo "$HISTORY_RESPONSE" | grep -o '"total_count":[0-9]*' | cut -d: -f2)
    echo -e "${GREEN}✓ 조회된 연혁 수: $HISTORY_COUNT${NC}"
else
    echo -e "${RED}✗ 연혁목록 API 호출 실패${NC}"
    echo "Response: $HISTORY_RESPONSE"
fi

# 5. JavaScript 리소스 확인
echo -e "\n${YELLOW}5. JavaScript 리소스 로드 테스트${NC}"
JS_FILES=("common.js" "rule-editor.js" "classification-manager.js" "department-manager.js" "search-engine.js" "service-manager.js" "edit-window.js" "regulations.js")

for JS_FILE in "${JS_FILES[@]}"; do
    JS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/static/js/$JS_FILE" -k)
    if [ "$JS_RESPONSE" = "200" ]; then
        echo -e "${GREEN}✓ $JS_FILE 로드 성공${NC}"
    else
        echo -e "${RED}✗ $JS_FILE 로드 실패 (HTTP $JS_RESPONSE)${NC}"
    fi
done

# 6. CSS 리소스 확인
echo -e "\n${YELLOW}6. CSS 리소스 로드 테스트${NC}"
CSS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/static/styles.css" -k)
if [ "$CSS_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ styles.css 로드 성공${NC}"
else
    echo -e "${RED}✗ styles.css 로드 실패 (HTTP $CSS_RESPONSE)${NC}"
fi

CSS_REG_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/static/css/regulations.css" -k)
if [ "$CSS_REG_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ regulations.css 로드 성공${NC}"
else
    echo -e "${YELLOW}⚠ regulations.css 로드 실패 (HTTP $CSS_REG_RESPONSE) - 파일이 없을 수 있음${NC}"
fi

# 로그아웃
echo -e "\n${YELLOW}7. 로그아웃 테스트${NC}"
LOGOUT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/logout" \
    -b "$COOKIE_FILE" \
    -k)

if echo "$LOGOUT_RESPONSE" | grep -q '"message"'; then
    echo -e "${GREEN}✓ 로그아웃 성공${NC}"
else
    echo -e "${RED}✗ 로그아웃 실패${NC}"
fi

# 정리
rm -f "$COOKIE_FILE"

echo -e "\n============================================="
echo -e "${GREEN}테스트 완료!${NC}"
echo "============================================="
echo ""
echo "다음 단계:"
echo "1. 브라우저에서 직접 접속 테스트: $BASE_URL/regulations/current"
echo "2. 개발자 도구 콘솔에서 JavaScript 에러 확인"
echo "3. 네트워크 탭에서 API 호출 확인"
echo ""