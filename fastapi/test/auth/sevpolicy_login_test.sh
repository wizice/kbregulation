#!/bin/bash

# 보안 강화 계정 로그인 테스트 스크립트
# 목적: sevpolicy 계정으로 정상 로그인 확인

BASE_URL="http://127.0.0.1:8800"

echo "======================================"
echo "보안 강화 계정 로그인 테스트"
echo "======================================"
echo ""

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 테스트 1: sevpolicy 계정 로그인
echo -e "${YELLOW}[테스트 1] sevpolicy 계정 로그인${NC}"

cat > /tmp/login_sevpolicy.json << 'EOF'
{
  "username": "sevpolicy",
  "password": "sevpolicy123!@#",
  "remember_me": false
}
EOF

response=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d @/tmp/login_sevpolicy.json)

echo "API 응답:"
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
echo ""

if echo "$response" | grep -q "access_token"; then
    echo -e "${GREEN}✅ sevpolicy 계정 로그인 성공!${NC}"

    # 사용자 정보 확인
    username=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('user', {}).get('username', 'N/A'))" 2>/dev/null)
    role=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('user', {}).get('role', 'N/A'))" 2>/dev/null)

    echo "   - Username: $username"
    echo "   - Role: $role"
else
    echo -e "${RED}✗ sevpolicy 계정 로그인 실패${NC}"
fi
echo ""

# 테스트 2: 잘못된 비밀번호
echo -e "${YELLOW}[테스트 2] 잘못된 비밀번호로 로그인 시도${NC}"

cat > /tmp/login_wrong.json << 'EOF'
{
  "username": "sevpolicy",
  "password": "wrongpassword",
  "remember_me": false
}
EOF

response=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d @/tmp/login_wrong.json)

if echo "$response" | grep -q "Invalid username or password"; then
    echo -e "${GREEN}✅ 잘못된 비밀번호 차단 성공${NC}"
else
    echo -e "${RED}✗ 예상과 다른 응답${NC}"
    echo "응답: $response"
fi
echo ""

# 테스트 3: 기존 admin 계정 (선택적 비활성화)
echo -e "${YELLOW}[테스트 3] 기존 admin 계정 로그인 시도${NC}"

cat > /tmp/login_admin.json << 'EOF'
{
  "username": "admin",
  "password": "admin123!@#",
  "remember_me": false
}
EOF

response=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d @/tmp/login_admin.json)

if echo "$response" | grep -q "access_token"; then
    echo -e "${YELLOW}⚠️  admin 계정이 아직 활성화되어 있습니다${NC}"
    echo "   보안을 위해 admin 계정 비활성화를 권장합니다."
    echo "   python3 create_sevpolicy_admin.py 실행 후 비활성화 선택"
else
    echo -e "${GREEN}✅ admin 계정이 비활성화되어 있거나 차단되었습니다${NC}"
fi
echo ""

# 정리
rm -f /tmp/login_*.json

echo "======================================"
echo "브라우저 테스트 가이드"
echo "======================================"
echo ""
echo "1. 브라우저에서 https://policyeditor.wizice.com:8443/login 접속"
echo ""
echo "2. 새로운 계정으로 로그인"
echo "   아이디: sevpolicy"
echo "   비밀번호: sevpolicy123!@#"
echo ""
echo "3. 로그인 성공 후 /regulations/current 페이지로 이동 확인"
echo ""
echo "4. 우측 상단 로그아웃 버튼 확인"
echo ""
echo "5. (권장) 첫 로그인 후 비밀번호 변경"
echo "   - 프로필 설정에서 비밀번호 변경"
echo "   - 더욱 복잡한 비밀번호로 변경"
echo ""
echo "======================================"
echo "보안 권고사항"
echo "======================================"
echo ""
echo "✓ 기존 admin 계정 비활성화"
echo "✓ 첫 로그인 후 비밀번호 변경"
echo "✓ 비밀번호 정기적 변경 (90일)"
echo "✓ 비밀번호 규칙:"
echo "  - 최소 12자 이상"
echo "  - 대문자, 소문자, 숫자, 특수문자 포함"
echo "  - 사전 단어 사용 금지"
echo "  - 개인정보 사용 금지"
echo ""
echo "======================================"
echo "테스트 완료"
echo "======================================"
