#!/bin/bash
# test_pdf_logging.sh
# 부록 PDF 조회 로깅 시스템 자동 테스트 스크립트

# PostgreSQL pager 비활성화
export PAGER=""

echo "=== 부록 PDF 조회 로깅 시스템 테스트 ==="

# Test 1: API 엔드포인트
echo -e "\n[Test 1] API 엔드포인트 확인"
PDF_TYPE=$(curl -s "http://localhost:8800/api/v1/pdf-file/1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf" | file - | grep -o "PDF document")
if [ "$PDF_TYPE" = "PDF document" ]; then
    echo "✅ PASS: PDF 파일 정상 반환"
else
    echo "❌ FAIL: PDF 파일 반환 실패"
fi

# 잠시 대기 (로그 기록 완료 대기)
sleep 1

# Test 2: 로그 기록 확인
echo -e "\n[Test 2] 로그 기록 확인"
LOG_COUNT=$(PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -t -A --pset pager=off -c \
"SELECT COUNT(*) FROM regulation_view_logs WHERE rule_id IS NULL AND viewed_at > NOW() - INTERVAL '1 minute';" 2>&1 | grep -v "Pager usage" | tr -d ' ')
if [ "$LOG_COUNT" -gt 0 ]; then
    echo "✅ PASS: 로그 기록됨 (최근 1분 내 $LOG_COUNT건)"
else
    echo "❌ FAIL: 로그 기록 안됨"
fi

# Test 3: 파싱 정확도 확인
echo -e "\n[Test 3] 파일명 파싱 정확도"
PARSED_NAME=$(PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -t -A --pset pager=off -c \
"SELECT rule_name FROM regulation_view_logs WHERE rule_id IS NULL ORDER BY viewed_at DESC LIMIT 1;" 2>&1 | grep -v "Pager usage" | xargs)
EXPECTED="부록1. 구두처방 의약품 목록"
if [ "$PARSED_NAME" = "$EXPECTED" ]; then
    echo "✅ PASS: 파일명 파싱 정확 (결과: $PARSED_NAME)"
else
    echo "❌ FAIL: 파일명 파싱 오류 (기대: $EXPECTED, 실제: $PARSED_NAME)"
fi

# Test 4: rule_pubno 형식 확인
echo -e "\n[Test 4] rule_pubno 형식 확인"
RULE_PUBNO=$(PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance -t -A --pset pager=off -c \
"SELECT rule_pubno FROM regulation_view_logs WHERE rule_id IS NULL ORDER BY viewed_at DESC LIMIT 1;" 2>&1 | grep -v "Pager usage" | xargs)
EXPECTED_PUBNO="1.2.1."
if [ "$RULE_PUBNO" = "$EXPECTED_PUBNO" ]; then
    echo "✅ PASS: rule_pubno 형식 정확 (결과: $RULE_PUBNO)"
else
    echo "⚠️  WARNING: rule_pubno 형식 확인 필요 (기대: $EXPECTED_PUBNO, 실제: $RULE_PUBNO)"
fi

# Test 5: 최근 로그 상세 정보
echo -e "\n[Test 5] 최근 로그 상세 정보"
PGPASSWORD="rkatkseverance!" psql -h localhost -p 35432 -U severance -d severance --pset pager=off -c \
"SELECT log_id, rule_id, rule_name, rule_pubno, viewed_at
 FROM regulation_view_logs
 WHERE rule_id IS NULL
 ORDER BY viewed_at DESC
 LIMIT 3;"

echo -e "\n=== 테스트 완료 ==="
