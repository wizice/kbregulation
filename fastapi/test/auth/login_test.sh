#!/bin/bash
# 로그인 기능 테스트

# 설정
TEST_HOST="http://localhost:8800"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/../fixtures"

echo "=== 로그인 기능 테스트 ==="
echo "호스트: $TEST_HOST"
echo ""

# 테스트 카운터
TESTS=0
PASSED=0

# 테스트 함수
test_login() {
    local test_name="$1"
    local username="$2"
    local password="$3"
    local expected="$4"
    
    TESTS=$((TESTS + 1))
    echo "테스트 $TESTS: $test_name"
    
    # JSON 생성
    local json_data="{\"username\": \"$username\", \"password\": \"$password\", \"remember_me\": false}"
    
    # API 호출
    local response=$(curl -s -X POST "$TEST_HOST/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "$json_data")
    
    # 결과 검증
    if echo "$response" | grep -q "$expected"; then
        echo "✅ 통과"
        PASSED=$((PASSED + 1))
    else
        echo "❌ 실패"
        echo "   응답: $response"
        echo "   예상: $expected"
    fi
    echo ""
}

# 테스트 실행
echo "🧪 로그인 테스트 시작"
echo ""

# 1. 성공적인 로그인
test_login "관리자 로그인 성공" "admin" "admin123!@#" "access_token"

# 2. 잘못된 사용자명
test_login "존재하지 않는 사용자" "nonexistent" "password123" "관리자 계정만 접속 가능합니다."

# 3. 잘못된 비밀번호
test_login "잘못된 비밀번호" "admin" "wrongpassword" "관리자 계정만 접속 가능합니다."

# 4. 짧은 비밀번호 (유효성 검사)
test_login "짧은 비밀번호" "admin" "123" "String should have at least 6 characters"

# 5. 빈 사용자명
test_login "빈 사용자명" "" "password123" "field required"

# 6. 로그인 페이지 접근 테스트
echo "테스트 $((TESTS + 1)): 로그인 페이지 접근"
TESTS=$((TESTS + 1))
PAGE_RESPONSE=$(curl -s "$TEST_HOST/login")
if echo "$PAGE_RESPONSE" | grep -q "관리자 로그인"; then
    echo "✅ 통과"
    PASSED=$((PASSED + 1))
else
    echo "❌ 실패"
    echo "   로그인 페이지를 불러올 수 없습니다."
fi
echo ""

# 7. 세션 쿠키 설정 테스트
echo "테스트 $((TESTS + 1)): 세션 쿠키 설정"
TESTS=$((TESTS + 1))
COOKIE_FILE="/tmp/test_login_cookies.txt"
COOKIE_RESPONSE=$(curl -s -c "$COOKIE_FILE" -X POST "$TEST_HOST/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123!@#", "remember_me": false}')

if [ -f "$COOKIE_FILE" ] && grep -q "session_token" "$COOKIE_FILE"; then
    echo "✅ 통과"
    PASSED=$((PASSED + 1))
else
    echo "❌ 실패"
    echo "   세션 쿠키가 설정되지 않았습니다."
fi
rm -f "$COOKIE_FILE"
echo ""

# 결과 요약
echo "=== 테스트 결과 ==="
echo "총 테스트: $TESTS"
echo "통과: $PASSED"
echo "실패: $((TESTS - PASSED))"
echo "성공률: $(echo "scale=1; $PASSED * 100 / $TESTS" | bc -l)%"

if [ $PASSED -eq $TESTS ]; then
    echo "🎉 모든 테스트 통과!"
    exit 0
else
    echo "⚠️ 일부 테스트 실패"
    exit 1
fi
