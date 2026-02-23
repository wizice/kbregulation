#!/bin/bash
# Elasticsearch 검색 기능 테스트

echo "=========================================="
echo "Elasticsearch Search Test"
echo "=========================================="
echo ""

# 서버 URL
BASE_URL="http://localhost:8800"

# 테스트 검색어
SEARCH_QUERY="환자"

echo "Testing search with query: '$SEARCH_QUERY'"
echo "-------------------------------------------"
echo ""

# 1. Title 검색 테스트
echo "1. Title Search Test (/api/search/es?search_type=title)"
echo "-------------------------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/search/es?q=${SEARCH_QUERY}&search_type=title&limit=5")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

echo "HTTP Status: $http_code"
if [ "$http_code" = "200" ]; then
    echo "✅ SUCCESS"
    echo ""
    echo "Response:"
    echo "$body" | python3 -m json.tool 2>/dev/null | head -50

    # 결과 수 추출
    total=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total', 0))" 2>/dev/null)
    took_ms=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('took_ms', 0))" 2>/dev/null)

    echo ""
    echo "📊 Results: $total total documents, took ${took_ms}ms"
else
    echo "❌ FAILED (HTTP $http_code)"
fi

echo ""
echo ""

# 2. Content 검색 테스트
echo "2. Content Search Test (/api/search/es?search_type=content)"
echo "-------------------------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/search/es?q=${SEARCH_QUERY}&search_type=content&limit=5")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

echo "HTTP Status: $http_code"
if [ "$http_code" = "200" ]; then
    echo "✅ SUCCESS"
    echo ""
    echo "Response:"
    echo "$body" | python3 -m json.tool 2>/dev/null | head -50

    # 결과 수 추출
    total=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total', 0))" 2>/dev/null)
    took_ms=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('took_ms', 0))" 2>/dev/null)

    echo ""
    echo "📊 Results: $total total documents, took ${took_ms}ms"
else
    echo "❌ FAILED (HTTP $http_code)"
fi

echo ""
echo ""

# 3. All 검색 테스트
echo "3. All Search Test (/api/search/es?search_type=all)"
echo "-------------------------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/search/es?q=${SEARCH_QUERY}&search_type=all&limit=5")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

echo "HTTP Status: $http_code"
if [ "$http_code" = "200" ]; then
    echo "✅ SUCCESS"
    echo ""
    echo "Response:"
    echo "$body" | python3 -m json.tool 2>/dev/null | head -50

    # 결과 수 추출
    total=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total', 0))" 2>/dev/null)
    took_ms=$(echo "$body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('took_ms', 0))" 2>/dev/null)

    echo ""
    echo "📊 Results: $total total documents, took ${took_ms}ms"
else
    echo "❌ FAILED (HTTP $http_code)"
fi

echo ""
echo "=========================================="
echo "Search test completed!"
echo "=========================================="
