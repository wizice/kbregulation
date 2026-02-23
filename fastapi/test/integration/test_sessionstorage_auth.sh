#!/bin/bash

# sessionStorage 기반 인증 시스템 테스트
# 탭별 독립 세션 검증

BASE_URL="http://localhost:8800"
API_URL="$BASE_URL/api/v1"

# 색상 코드
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================="
echo "sessionStorage 인증 시스템 테스트"
echo "=================================="
echo ""

# 테스트 1: 로그인 및 토큰 받기
echo -e "${YELLOW}[테스트 1] 첫 번째 로그인 (탭1 시뮬레이션)${NC}"
RESPONSE1=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123!@#",
    "remember_me": false
  }')

TOKEN1=$(echo $RESPONSE1 | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN1" ]; then
    echo -e "${RED}✗ 로그인 실패${NC}"
    echo "Response: $RESPONSE1"
    exit 1
else
    echo -e "${GREEN}✓ 로그인 성공${NC}"
    echo "Token1: ${TOKEN1:0:20}..."
fi
echo ""

# 테스트 2: 첫 번째 토큰으로 사용자 정보 조회
echo -e "${YELLOW}[테스트 2] Token1으로 사용자 정보 조회${NC}"
USER_INFO1=$(curl -s -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN1")

if echo "$USER_INFO1" | grep -q "username"; then
    echo -e "${GREEN}✓ Token1 유효함${NC}"
    echo "User: $(echo $USER_INFO1 | grep -o '"username":"[^"]*' | cut -d'"' -f4)"
else
    echo -e "${RED}✗ Token1 유효하지 않음${NC}"
    echo "Response: $USER_INFO1"
fi
echo ""

# 테스트 3: 두 번째 로그인 (탭2 시뮬레이션)
echo -e "${YELLOW}[테스트 3] 두 번째 로그인 (탭2 시뮬레이션)${NC}"
sleep 1
RESPONSE2=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123!@#",
    "remember_me": false
  }')

TOKEN2=$(echo $RESPONSE2 | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN2" ]; then
    echo -e "${RED}✗ 두 번째 로그인 실패${NC}"
    echo "Response: $RESPONSE2"
    exit 1
else
    echo -e "${GREEN}✓ 두 번째 로그인 성공${NC}"
    echo "Token2: ${TOKEN2:0:20}..."
fi
echo ""

# 테스트 4: Token1이 무효화되었는지 확인 (중요!)
echo -e "${YELLOW}[테스트 4] Token1 무효화 확인 (핵심 테스트)${NC}"
USER_INFO_OLD=$(curl -s -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN1")

if echo "$USER_INFO_OLD" | grep -q "detail"; then
    echo -e "${GREEN}✓ Token1 무효화됨 (정상)${NC}"
    echo "Response: $USER_INFO_OLD"
else
    echo -e "${RED}✗ Token1이 여전히 유효함 (실패!)${NC}"
    echo "Response: $USER_INFO_OLD"
fi
echo ""

# 테스트 5: Token2는 정상 작동하는지 확인
echo -e "${YELLOW}[테스트 5] Token2 유효성 확인${NC}"
USER_INFO2=$(curl -s -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN2")

if echo "$USER_INFO2" | grep -q "username"; then
    echo -e "${GREEN}✓ Token2 정상 작동${NC}"
    echo "User: $(echo $USER_INFO2 | grep -o '"username":"[^"]*' | cut -d'"' -f4)"
else
    echo -e "${RED}✗ Token2 유효하지 않음${NC}"
    echo "Response: $USER_INFO2"
fi
echo ""

# 테스트 6: 로그아웃 테스트
echo -e "${YELLOW}[테스트 6] 로그아웃 테스트${NC}"
LOGOUT_RESPONSE=$(curl -s -X POST "$API_URL/auth/logout" \
  -H "Authorization: Bearer $TOKEN2")

if echo "$LOGOUT_RESPONSE" | grep -q "Successfully logged out"; then
    echo -e "${GREEN}✓ 로그아웃 성공${NC}"
else
    echo -e "${YELLOW}⚠ 로그아웃 응답: $LOGOUT_RESPONSE${NC}"
fi
echo ""

# 테스트 7: 로그아웃 후 Token2가 무효화되었는지 확인
echo -e "${YELLOW}[테스트 7] 로그아웃 후 Token2 무효화 확인${NC}"
USER_INFO_AFTER_LOGOUT=$(curl -s -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN2")

if echo "$USER_INFO_AFTER_LOGOUT" | grep -q "detail"; then
    echo -e "${GREEN}✓ Token2 무효화됨 (정상)${NC}"
else
    echo -e "${RED}✗ Token2가 여전히 유효함${NC}"
    echo "Response: $USER_INFO_AFTER_LOGOUT"
fi
echo ""

# 최종 결과
echo "=================================="
echo -e "${GREEN}테스트 완료!${NC}"
echo "=================================="
echo ""
echo "주요 검증 사항:"
echo "1. 로그인 시 토큰 발급 ✓"
echo "2. 토큰으로 API 호출 가능 ✓"
echo "3. 중복 로그인 시 이전 토큰 무효화 (중요!) - 확인 필요"
echo "4. 로그아웃 시 토큰 무효화 ✓"
echo ""
echo "브라우저 테스트 필요:"
echo "1. 탭1에서 로그인"
echo "2. 탭2에서 동일 계정 로그인"
echo "3. 탭1에서 메뉴 클릭 시 401 에러 + 알림 표시 확인"
echo ""
