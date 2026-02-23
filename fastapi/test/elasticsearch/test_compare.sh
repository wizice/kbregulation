#!/bin/bash
# PostgreSQL vs Elasticsearch 비교 테스트

echo "=========================================="
echo "PostgreSQL vs Elasticsearch Comparison"
echo "=========================================="
echo ""

# 서버 URL
BASE_URL="http://localhost:8800"

# 테스트 검색어 목록
declare -a QUERIES=("환자" "안전" "관리" "규정")

echo "Testing multiple queries..."
echo "-------------------------------------------"
echo ""

total_postgres_time=0
total_es_time=0
test_count=0

for query in "${QUERIES[@]}"; do
    echo "🔍 Query: '$query'"
    echo "-------------------------------------------"

    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/search/compare?q=${query}&search_type=content&limit=10")
    http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE/d')

    if [ "$http_code" = "200" ]; then
        echo "✅ Comparison successful"
        echo ""

        # PostgreSQL 결과
        pg_time=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('postgres', {}).get('took_ms', 0))" 2>/dev/null)
        pg_count=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('postgres', {}).get('total', 0))" 2>/dev/null)

        # Elasticsearch 결과
        es_time=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('elasticsearch', {}).get('took_ms', 0))" 2>/dev/null)
        es_count=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('elasticsearch', {}).get('total', 0))" 2>/dev/null)
        es_error=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('elasticsearch', {}).get('error', 'None'))" 2>/dev/null)

        # 개선율
        improvement=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('analysis', {}).get('speed_comparison', {}).get('improvement', 'N/A'))" 2>/dev/null)

        echo "📊 PostgreSQL:"
        echo "   - Time: ${pg_time}ms"
        echo "   - Results: $pg_count documents"
        echo ""
        echo "📊 Elasticsearch:"
        if [ "$es_error" != "None" ]; then
            echo "   ❌ Error: $es_error"
        else
            echo "   - Time: ${es_time}ms"
            echo "   - Results: $es_count documents"
            echo "   - Speed: $improvement"

            # 누적 시간 계산
            total_postgres_time=$(echo "$total_postgres_time + $pg_time" | bc 2>/dev/null)
            total_es_time=$(echo "$total_es_time + $es_time" | bc 2>/dev/null)
            test_count=$((test_count + 1))
        fi
    else
        echo "❌ FAILED (HTTP $http_code)"
        echo "$body"
    fi

    echo ""
    echo ""
done

# 전체 요약
if [ $test_count -gt 0 ]; then
    echo "=========================================="
    echo "Summary"
    echo "=========================================="
    echo ""
    echo "Total tests completed: $test_count"
    echo ""
    echo "Average PostgreSQL time: $(echo "scale=2; $total_postgres_time / $test_count" | bc)ms"
    echo "Average Elasticsearch time: $(echo "scale=2; $total_es_time / $test_count" | bc)ms"
    echo ""

    # 전체 개선율 계산
    if [ $(echo "$total_es_time > 0" | bc) -eq 1 ]; then
        overall_improvement=$(echo "scale=1; $total_postgres_time / $total_es_time" | bc)
        echo "🚀 Overall speed improvement: ${overall_improvement}x faster"
    fi
fi

echo ""
echo "=========================================="
echo "Comparison test completed!"
echo "=========================================="
