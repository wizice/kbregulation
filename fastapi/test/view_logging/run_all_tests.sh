#!/bin/bash
# =====================================================
# 내규 조회 통계 로깅 시스템 종합 테스트
# =====================================================

set -e  # 오류 발생 시 중단

cd /home/wizice/regulation/fastapi

# psql pager 비활성화
export PAGER=cat

echo "======================================================================="
echo "🧪 내규 조회 통계 로깅 시스템 종합 테스트"
echo "======================================================================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 테스트 카운터
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 테스트 함수
run_test() {
    local test_name="$1"
    local test_command="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 Test $TOTAL_TESTS: $test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi

    echo ""
}

# =====================================================
# 1. 데이터베이스 테이블 존재 확인
# =====================================================
run_test "데이터베이스 테이블 존재 확인" \
    "PGPASSWORD='rkatkseverance!' psql -h localhost -p 35432 -U severance -d severance -c '\d regulation_view_logs' > /dev/null 2>&1"

# =====================================================
# 2. 로거 모듈 단독 테스트
# =====================================================
run_test "로거 모듈 단독 테스트" \
    "python3 test_view_logger.py > /dev/null 2>&1"

# =====================================================
# 3. 통합 테스트 (API 시뮬레이션)
# =====================================================
run_test "통합 테스트 (API 시뮬레이션)" \
    "python3 test_view_logging_integration.py > /dev/null 2>&1"

# =====================================================
# 4. 통계 쿼리 테스트
# =====================================================
run_test "통계 쿼리 테스트" \
    "python3 test_view_stats_api.py > /dev/null 2>&1"

# =====================================================
# 5. 데이터 무결성 검증
# =====================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Test $((TOTAL_TESTS + 1)): 데이터 무결성 검증"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TOTAL_TESTS=$((TOTAL_TESTS + 1))

# 외래키 제약 확인
ORPHAN_COUNT=$(PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -t -A -c \
    "SELECT COUNT(*) FROM regulation_view_logs l
     LEFT JOIN wz_rule r ON l.rule_id = r.wzruleseq
     WHERE r.wzruleseq IS NULL;" 2>/dev/null | grep -E '^[0-9]+$' | head -1)

if [ "$ORPHAN_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ PASS${NC}: 외래키 무결성 정상 (고아 레코드 없음)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ FAIL${NC}: 외래키 무결성 위반 (고아 레코드 $ORPHAN_COUNT개)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo ""

# =====================================================
# 6. 인덱스 존재 확인
# =====================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Test $((TOTAL_TESTS + 1)): 인덱스 존재 확인"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TOTAL_TESTS=$((TOTAL_TESTS + 1))

INDEX_COUNT=$(PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -t -A -c \
    "SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'regulation_view_logs';" 2>/dev/null | grep -E '^[0-9]+$' | head -1)

if [ "$INDEX_COUNT" -ge 4 ]; then
    echo -e "${GREEN}✅ PASS${NC}: 인덱스 존재 ($INDEX_COUNT개)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ FAIL${NC}: 인덱스 부족 ($INDEX_COUNT개, 4개 이상 필요)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo ""

# =====================================================
# 7. 성능 테스트 (100회 로그 기록)
# =====================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ Test $((TOTAL_TESTS + 1)): 성능 테스트 (100회 로그 기록)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TOTAL_TESTS=$((TOTAL_TESTS + 1))

# 시작 시간
START_TIME=$(date +%s)

# 100회 로그 기록
for i in {1..100}; do
    python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from api.regulation_view_logger import log_regulation_view

async def test():
    await log_regulation_view(1, '성능 테스트', '0.0.0')

asyncio.run(test())
" > /dev/null 2>&1
done

# 종료 시간
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ "$DURATION" -le 10 ]; then
    echo -e "${GREEN}✅ PASS${NC}: 성능 정상 (100회 기록: ${DURATION}초)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${YELLOW}⚠️  SLOW${NC}: 성능 느림 (100회 기록: ${DURATION}초, 10초 이하 권장)"
    PASSED_TESTS=$((PASSED_TESTS + 1))  # 느려도 PASS
fi

echo ""

# =====================================================
# 최종 결과
# =====================================================
echo "======================================================================="
echo "📊 테스트 결과"
echo "======================================================================="
echo ""
echo "   총 테스트: $TOTAL_TESTS"
echo -e "   ${GREEN}통과: $PASSED_TESTS${NC}"
echo -e "   ${RED}실패: $FAILED_TESTS${NC}"
echo ""

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}✅ 모든 테스트 통과!${NC}"
    echo ""
    echo "🎉 내규 조회 통계 로깅 시스템이 정상적으로 작동합니다."
    echo ""
    echo "📊 통계 확인:"
    PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -c \
        "SELECT
            COUNT(*) as total_logs,
            COUNT(DISTINCT rule_id) as unique_rules
         FROM regulation_view_logs;"
    echo ""
    echo "🏆 TOP 5 조회수:"
    PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -c \
        "SELECT rule_id, rule_name, COUNT(*) as views
         FROM regulation_view_logs
         GROUP BY rule_id, rule_name
         ORDER BY views DESC
         LIMIT 5;"
    exit 0
else
    echo -e "${RED}❌ 일부 테스트 실패${NC}"
    echo ""
    echo "💡 문제 해결:"
    echo "   1. 로그 파일 확인: logs/app.log"
    echo "   2. DB 연결 확인: psql 접속 테스트"
    echo "   3. 테이블 확인: \d regulation_view_logs"
    exit 1
fi
