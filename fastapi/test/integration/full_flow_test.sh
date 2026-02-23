#!/bin/bash
# 전체 사용자 플로우 통합 테스트

# 설정
TEST_HOST="http://localhost:8800"
TEST_ADMIN_USER="admin"
TEST_ADMIN_PASSWORD="admin123!@#"
COOKIE_FILE="/tmp/test_cookies_$(date +%s).txt"
TEST_LOG="/tmp/test_log_$(date +%s).log"

echo "=== 세브란스 편집기 통합 테스트 ===" | tee $TEST_LOG
echo "시작 시간: $(date)" | tee -a $TEST_LOG
echo "테스트 호스트: $TEST_HOST" | tee -a $TEST_LOG
echo "" | tee -a $TEST_LOG

# 테스트 카운터
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 테스트 함수
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_result="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo "🧪 테스트 $TOTAL_TESTS: $test_name" | tee -a $TEST_LOG
    
    # 테스트 실행
    result=$(eval "$test_command" 2>&1)
    
    # 결과 검증
    if echo "$result" | grep -q "$expected_result"; then
        echo "✅ 통과" | tee -a $TEST_LOG
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "❌ 실패" | tee -a $TEST_LOG
        echo "   예상: $expected_result" | tee -a $TEST_LOG
        echo "   실제: $result" | tee -a $TEST_LOG
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    echo "" | tee -a $TEST_LOG
}

# 테스트 시작
echo "🚀 테스트 시작" | tee -a $TEST_LOG
echo "" | tee -a $TEST_LOG

# 1. 서버 상태 확인
run_test "서버 상태 확인" \
    "curl -s -o /dev/null -w '%{http_code}' $TEST_HOST/health" \
    "200"

# 2. 로그인 페이지 접근
run_test "로그인 페이지 접근" \
    "curl -s $TEST_HOST/login | grep -o '관리자 로그인'" \
    "관리자 로그인"

# 3. 관리자 로그인
run_test "관리자 로그인" \
    "curl -s -c $COOKIE_FILE -X POST $TEST_HOST/api/v1/auth/login -H 'Content-Type: application/json' -d '{\"username\": \"$TEST_ADMIN_USER\", \"password\": \"$TEST_ADMIN_PASSWORD\", \"remember_me\": false}' | jq -r '.user.role'" \
    "admin"

# 4. 편집기 페이지 접근
run_test "편집기 페이지 접근" \
    "curl -s -b $COOKIE_FILE $TEST_HOST/admin/ | grep -o '사규자료 현행화 편집기'" \
    "사규자료 현행화 편집기"

# 5. 정적 파일 접근
run_test "CSS 파일 접근" \
    "curl -s -o /dev/null -w '%{http_code}' $TEST_HOST/static/styles.css" \
    "200"

run_test "JavaScript 파일 접근" \
    "curl -s -o /dev/null -w '%{http_code}' $TEST_HOST/static/js/regulation-editor.js" \
    "200"

# 6. API 보안 테스트
run_test "인증 없이 보호된 API 접근" \
    "curl -s -o /dev/null -w '%{http_code}' $TEST_HOST/api/v1/protected" \
    "401"

# 7. 로그아웃
run_test "로그아웃" \
    "curl -s -b $COOKIE_FILE -X POST $TEST_HOST/api/v1/auth/logout | jq -r '.message'" \
    "Successfully logged out"

# 8. 로그아웃 후 보호된 페이지 접근
run_test "로그아웃 후 보호된 페이지 접근" \
    "curl -s -o /dev/null -w '%{http_code}' -b $COOKIE_FILE $TEST_HOST/admin/" \
    "302"

# 결과 요약
echo "=== 테스트 결과 요약 ===" | tee -a $TEST_LOG
echo "총 테스트: $TOTAL_TESTS" | tee -a $TEST_LOG
echo "통과: $PASSED_TESTS" | tee -a $TEST_LOG
echo "실패: $FAILED_TESTS" | tee -a $TEST_LOG
echo "성공률: $(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)%" | tee -a $TEST_LOG
echo "" | tee -a $TEST_LOG

# 정리
rm -f $COOKIE_FILE

# 종료 상태 결정
if [ $FAILED_TESTS -eq 0 ]; then
    echo "🎉 모든 테스트가 통과했습니다!" | tee -a $TEST_LOG
    echo "로그 파일: $TEST_LOG" | tee -a $TEST_LOG
    exit 0
else
    echo "⚠️  일부 테스트가 실패했습니다." | tee -a $TEST_LOG
    echo "로그 파일: $TEST_LOG" | tee -a $TEST_LOG
    exit 1
fi