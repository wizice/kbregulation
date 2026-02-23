#!/bin/bash
# 모든 테스트를 실행하는 마스터 스크립트

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
LOG_FILE="/tmp/all_tests_$(date +%Y%m%d_%H%M%S).log"

echo "=== 세브란스 편집기 - 전체 테스트 실행 ===" | tee $LOG_FILE
echo "시작 시간: $(date)" | tee -a $LOG_FILE
echo "로그 파일: $LOG_FILE" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# 테스트 결과 추적
TOTAL_SUITES=0
PASSED_SUITES=0
FAILED_SUITES=0

# 테스트 스위트 실행 함수
run_test_suite() {
    local suite_name="$1"
    local script_path="$2"
    
    TOTAL_SUITES=$((TOTAL_SUITES + 1))
    echo "🧪 테스트 스위트 $TOTAL_SUITES: $suite_name" | tee -a $LOG_FILE
    echo "스크립트: $script_path" | tee -a $LOG_FILE
    
    if [ -f "$script_path" ] && [ -x "$script_path" ]; then
        echo "실행 중..." | tee -a $LOG_FILE
        
        # 테스트 실행
        if "$script_path" >> $LOG_FILE 2>&1; then
            echo "✅ 통과" | tee -a $LOG_FILE
            PASSED_SUITES=$((PASSED_SUITES + 1))
        else
            echo "❌ 실패" | tee -a $LOG_FILE
            FAILED_SUITES=$((FAILED_SUITES + 1))
        fi
    else
        echo "⚠️  스크립트를 찾을 수 없거나 실행할 수 없습니다." | tee -a $LOG_FILE
        FAILED_SUITES=$((FAILED_SUITES + 1))
    fi
    
    echo "" | tee -a $LOG_FILE
}

# 사전 체크
echo "🔍 환경 사전 체크" | tee -a $LOG_FILE

# 서버 실행 확인
if curl -s http://localhost:8800/health > /dev/null; then
    echo "✅ 서버 실행 중 (포트 8800)" | tee -a $LOG_FILE
else
    echo "❌ 서버가 실행 중이 아닙니다. uvicorn을 먼저 시작하세요." | tee -a $LOG_FILE
    exit 1
fi

# PostgreSQL 연결 확인 (선택적)
if command -v psql > /dev/null; then
    if PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ 데이터베이스 연결 정상" | tee -a $LOG_FILE
    else
        echo "⚠️  데이터베이스 연결 확인 불가" | tee -a $LOG_FILE
    fi
fi

# Redis 연결 확인 (선택적)
if command -v redis-cli > /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis 연결 정상" | tee -a $LOG_FILE
    else
        echo "⚠️  Redis 연결 확인 불가" | tee -a $LOG_FILE
    fi
fi

echo "" | tee -a $LOG_FILE

# 테스트 스위트 실행
echo "🚀 테스트 스위트 실행 시작" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# 1. 인증 테스트
run_test_suite "로그인 기능 테스트" "$SCRIPT_DIR/auth/login_test.sh"

# 2. 통합 테스트
run_test_suite "전체 플로우 통합 테스트" "$SCRIPT_DIR/integration/full_flow_test.sh"

# 추가 테스트 스위트가 있다면 여기에 추가
# run_test_suite "API 테스트" "$SCRIPT_DIR/api/api_test.py"
# run_test_suite "성능 테스트" "$SCRIPT_DIR/integration/performance_test.py"

# 최종 결과
echo "=== 전체 테스트 결과 ===" | tee -a $LOG_FILE
echo "총 테스트 스위트: $TOTAL_SUITES" | tee -a $LOG_FILE
echo "통과한 스위트: $PASSED_SUITES" | tee -a $LOG_FILE
echo "실패한 스위트: $FAILED_SUITES" | tee -a $LOG_FILE

if [ $TOTAL_SUITES -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=1; $PASSED_SUITES * 100 / $TOTAL_SUITES" | bc -l)
    echo "성공률: $SUCCESS_RATE%" | tee -a $LOG_FILE
fi

echo "종료 시간: $(date)" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# 상세 로그 정보
echo "📋 상세 로그 위치: $LOG_FILE" | tee -a $LOG_FILE
echo "로그 확인: tail -f $LOG_FILE" | tee -a $LOG_FILE

# 종료 상태
if [ $FAILED_SUITES -eq 0 ]; then
    echo "🎉 모든 테스트 스위트가 성공했습니다!" | tee -a $LOG_FILE
    exit 0
else
    echo "⚠️  일부 테스트 스위트가 실패했습니다." | tee -a $LOG_FILE
    exit 1
fi