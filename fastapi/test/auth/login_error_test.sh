#!/bin/bash

# 로그인 에러 메시지 테스트 스크립트
# 목적: 다양한 로그인 실패 시나리오에서 에러 메시지가 올바르게 표시되는지 확인

BASE_URL="http://127.0.0.1:8800"

echo "======================================"
echo "로그인 에러 메시지 테스트"
echo "======================================"
echo ""

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 테스트 1: non-admin 계정으로 로그인 시도
echo -e "${YELLOW}[테스트 1] test 아이디로 로그인 (관리자 아님)${NC}"
response=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "wrongpass", "remember_me": false}')

echo "API 응답: $response"
if echo "$response" | grep -q "Invalid username or password"; then
    echo -e "${GREEN}✓ 예상대로 401 에러 반환${NC}"
else
    echo -e "${RED}✗ 예상과 다른 응답${NC}"
fi
echo ""

# 테스트 2: admin 계정으로 잘못된 비밀번호 입력
echo -e "${YELLOW}[테스트 2] admin 아이디 + 잘못된 비밀번호${NC}"
response=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "wrongpassword", "remember_me": false}')

echo "API 응답: $response"
if echo "$response" | grep -q "Invalid username or password"; then
    echo -e "${GREEN}✓ 예상대로 401 에러 반환${NC}"
else
    echo -e "${RED}✗ 예상과 다른 응답${NC}"
fi
echo ""

# 테스트 3: 빈 값 입력 (클라이언트 사이드 검증)
echo -e "${YELLOW}[테스트 3] 빈 아이디/비밀번호 (클라이언트 검증)${NC}"
echo "→ 이 테스트는 브라우저에서 수동으로 확인 필요"
echo "   예상 메시지: '관리자 아이디와 비밀번호를 모두 입력해주세요.'"
echo ""

# 테스트 4: 존재하지 않는 계정
echo -e "${YELLOW}[테스트 4] 존재하지 않는 계정${NC}"
response=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "nonexistent", "password": "password123", "remember_me": false}')

echo "API 응답: $response"
if echo "$response" | grep -q "Invalid username or password"; then
    echo -e "${GREEN}✓ 예상대로 401 에러 반환${NC}"
else
    echo -e "${RED}✗ 예상과 다른 응답${NC}"
fi
echo ""

echo "======================================"
echo "브라우저 테스트 가이드"
echo "======================================"
echo ""
echo "1. 브라우저에서 https://policyeditor.wizice.com:8443/login 접속"
echo ""
echo "2. 다음 시나리오를 테스트:"
echo "   a) 아이디: test, 비밀번호: 아무거나"
echo "      → '입력하신 로그인 정보가 올바르지 않습니다.'"
echo ""
echo "   b) 아이디: admin, 비밀번호: 잘못된 비밀번호"
echo "      → '입력하신 로그인 정보가 올바르지 않습니다.'"
echo ""
echo "   c) 아이디: (빈칸), 비밀번호: (빈칸)"
echo "      → '관리자 아이디와 비밀번호를 모두 입력해주세요.'"
echo ""
echo "3. 콘솔에서 에러 확인:"
echo "   - F12 키를 눌러 개발자 도구 열기"
echo "   - Console 탭에서 'Login error' 메시지 확인"
echo "   - [object Object]가 표시되지 않는지 확인"
echo ""
echo "======================================"
echo "테스트 완료"
echo "======================================"
