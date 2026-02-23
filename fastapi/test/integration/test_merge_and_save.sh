#!/bin/bash

# Test script for merge and save functionality
# 병합 후 저장 기능 테스트 스크립트

echo "=================================================="
echo "병합 후 저장 기능 테스트"
echo "Test: Merge and Save Functionality"
echo "=================================================="

# Base URL
BASE_URL="http://localhost:8800"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Login first to get session
echo -e "${YELLOW}[1/4] 관리자 로그인...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123!@#"}' \
    -c cookie.txt)

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✓ 로그인 성공${NC}"
else
    echo -e "${RED}✗ 로그인 실패${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

# Get a sample regulation ID for testing
echo -e "${YELLOW}[2/4] 테스트용 규정 조회...${NC}"
REGULATION_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/v1/regulations/list" \
    -b cookie.txt | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['data'][0]['wzruleseq'] if data.get('data') and len(data['data']) > 0 else 'none')" 2>/dev/null)

if [ "$REGULATION_RESPONSE" == "none" ]; then
    echo -e "${RED}✗ 규정 조회 실패${NC}"
    exit 1
fi

REGULATION_ID=$REGULATION_RESPONSE
echo -e "${GREEN}✓ 규정 ID: ${REGULATION_ID}${NC}"

# Test the update endpoint
echo -e "${YELLOW}[3/4] 규정 업데이트 테스트...${NC}"
UPDATE_RESPONSE=$(curl -s -X PUT "${BASE_URL}/api/v1/rule/update" \
    -H "Content-Type: application/json" \
    -b cookie.txt \
    -d "{
        \"wzruleseq\": \"${REGULATION_ID}\",
        \"wzname\": \"테스트 규정 - 병합 후 수정\",
        \"wzpubno\": \"TEST-001\",
        \"wzmgrdptnm\": \"정보팀\",
        \"wzestabdate\": \"2025-09-18\",
        \"wzexecdate\": \"2025-09-18\",
        \"wzversion\": \"2.0\",
        \"content_text\": \"제1조 (목적) 이 규정은 병합 후 저장 테스트를 위한 것이다.\n\n제2조 (적용범위) 모든 부서에 적용된다.\n\n제3조 (시행일) 이 규정은 공포한 날부터 시행한다.\"
    }")

if echo "$UPDATE_RESPONSE" | grep -q "success\|updated"; then
    echo -e "${GREEN}✓ 규정 업데이트 성공${NC}"
    echo "Response: $UPDATE_RESPONSE"
else
    echo -e "${RED}✗ 규정 업데이트 실패${NC}"
    echo "Response: $UPDATE_RESPONSE"
fi

# Logout
echo -e "${YELLOW}[4/4] 로그아웃...${NC}"
curl -s -X POST "${BASE_URL}/api/v1/auth/logout" -b cookie.txt > /dev/null
echo -e "${GREEN}✓ 로그아웃 완료${NC}"

# Clean up
rm -f cookie.txt

echo ""
echo "=================================================="
echo -e "${GREEN}테스트 완료${NC}"
echo "=================================================="
echo ""
echo "다음 단계:"
echo "1. 브라우저에서 직접 병합 후 저장 기능 테스트"
echo "2. 개발자 도구의 콘솔에서 에러 메시지 확인"
echo "3. RegulationEditor.currentEditingRegulation 값 확인"
echo ""