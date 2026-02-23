#!/bin/bash
# 모든 Elasticsearch 테스트 일괄 실행

echo "=========================================="
echo "Elasticsearch Test Suite"
echo "Running all tests..."
echo "=========================================="
echo ""

# 테스트 결과 카운터
total_tests=0
passed_tests=0
failed_tests=0

# 현재 디렉토리 저장
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 1. Health Check Test
echo "▶ Running Health Check Test..."
echo ""
if bash "$SCRIPT_DIR/test_es_health.sh"; then
    passed_tests=$((passed_tests + 1))
else
    failed_tests=$((failed_tests + 1))
fi
total_tests=$((total_tests + 1))
echo ""
echo ""

# 2. Search Test
echo "▶ Running Search Test..."
echo ""
if bash "$SCRIPT_DIR/test_es_search.sh"; then
    passed_tests=$((passed_tests + 1))
else
    failed_tests=$((failed_tests + 1))
fi
total_tests=$((total_tests + 1))
echo ""
echo ""

# 3. Comparison Test
echo "▶ Running Comparison Test..."
echo ""
if bash "$SCRIPT_DIR/test_compare.sh"; then
    passed_tests=$((passed_tests + 1))
else
    failed_tests=$((failed_tests + 1))
fi
total_tests=$((total_tests + 1))
echo ""
echo ""

# 최종 요약
echo "=========================================="
echo "Test Suite Summary"
echo "=========================================="
echo ""
echo "Total Tests: $total_tests"
echo "Passed: ✅ $passed_tests"
echo "Failed: ❌ $failed_tests"
echo ""

if [ $failed_tests -eq 0 ]; then
    echo "🎉 All tests passed!"
    echo ""
    echo "✅ Elasticsearch is ready for production use!"
    echo ""
    echo "Next steps:"
    echo "  1. Share /api/search/es endpoint with beta users"
    echo "  2. Monitor performance and collect feedback"
    echo "  3. Implement feature flag for gradual rollout"
    exit 0
else
    echo "⚠️  Some tests failed. Please review the errors above."
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check Elasticsearch server status"
    echo "  2. Verify required packages are installed"
    echo "  3. Review application logs: logs/app.log"
    exit 1
fi
