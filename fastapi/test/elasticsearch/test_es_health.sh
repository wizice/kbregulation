#!/bin/bash
# Elasticsearch 헬스체크 테스트

echo "=========================================="
echo "Elasticsearch Health Check Test"
echo "=========================================="
echo ""

# 서버 URL
BASE_URL="http://localhost:8800"

echo "1. Testing /api/search/es/health endpoint..."
echo "-------------------------------------------"

response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/search/es/health")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

echo "HTTP Status: $http_code"
echo ""
echo "Response:"
echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
echo ""

if [ "$http_code" = "200" ]; then
    echo "✅ SUCCESS: Elasticsearch is healthy!"

    # 인덱스 문서 수 추출
    rule_count=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('indices', {}).get('rules', {}).get('document_count', 0))" 2>/dev/null)
    article_count=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('indices', {}).get('articles', {}).get('document_count', 0))" 2>/dev/null)

    echo ""
    echo "📊 Index Statistics:"
    echo "  - Rules Index: $rule_count documents"
    echo "  - Articles Index: $article_count documents"
else
    echo "❌ FAILED: Elasticsearch health check failed (HTTP $http_code)"
    exit 1
fi

echo ""
echo "=========================================="
echo "Test completed successfully!"
echo "=========================================="
