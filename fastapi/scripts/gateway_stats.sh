#!/bin/bash
# Gateway 접속 통계 생성 스크립트

LOG_FILE="logs/gateway.log"

# 로그 파일 존재 확인
if [ ! -f "$LOG_FILE" ]; then
    echo "Error: $LOG_FILE not found"
    exit 1
fi

echo "===== Gateway 접속 통계 ====="
echo ""
echo "분석 대상: $LOG_FILE"
echo "생성 시각: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

echo "1. 전체 요청 수"
TOTAL_REQUESTS=$(grep -c "\[ENTRY\]" $LOG_FILE 2>/dev/null || echo "0")
echo "  총 요청: $TOTAL_REQUESTS"

echo ""
echo "2. 인증 성공/실패"
AUTH_SUCCESS=$(grep -c "AUTH_SUCCESS" $LOG_FILE 2>/dev/null || echo "0")
AUTH_FAILURE=$(grep -c "AUTH_FAILURE" $LOG_FILE 2>/dev/null || echo "0")
echo "  성공: $AUTH_SUCCESS"
echo "  실패: $AUTH_FAILURE"

if [ "$TOTAL_REQUESTS" -gt 0 ] 2>/dev/null; then
    SUCCESS_RATE=$(echo "scale=2; $AUTH_SUCCESS * 100 / $TOTAL_REQUESTS" | bc 2>/dev/null || echo "0")
    echo "  성공률: ${SUCCESS_RATE}%"
fi

echo ""
echo "3. 네트워크별 통계"
EXTERNAL=$(grep -c "Network=외부망" $LOG_FILE 2>/dev/null || echo "0")
INTERNAL=$(grep -c "Network=내부망" $LOG_FILE 2>/dev/null || echo "0")
echo "  외부망: $EXTERNAL"
echo "  내부망: $INTERNAL"

echo ""
echo "4. 디바이스별 통계 (인증 성공 기준)"
MOBILE=$(grep "AUTH_SUCCESS" $LOG_FILE 2>/dev/null | grep -c "Device=모바일" || echo "0")
PC=$(grep "AUTH_SUCCESS" $LOG_FILE 2>/dev/null | grep -c "Device=PC" || echo "0")
echo "  모바일: $MOBILE"
echo "  PC: $PC"

echo ""
echo "5. 주요 실패 사유 (Top 5)"
if [ "$AUTH_FAILURE" -gt 0 ] 2>/dev/null; then
    grep "AUTH_FAILURE" $LOG_FILE 2>/dev/null | \
      grep -o "Result=[^|]*" | \
      sed 's/Result=/  /' | \
      sort | uniq -c | sort -rn | head -5
else
    echo "  (실패 기록 없음)"
fi

echo ""
echo "6. 시간대별 요청 분포 (최근 24시간)"
if command -v bc >/dev/null 2>&1; then
    echo "  00-06시: $(grep "$(date +%Y-%m-%d) 0[0-5]:" $LOG_FILE 2>/dev/null | wc -l)"
    echo "  06-12시: $(grep "$(date +%Y-%m-%d) (06|07|08|09|10|11):" $LOG_FILE 2>/dev/null | wc -l)"
    echo "  12-18시: $(grep "$(date +%Y-%m-%d) (12|13|14|15|16|17):" $LOG_FILE 2>/dev/null | wc -l)"
    echo "  18-24시: $(grep "$(date +%Y-%m-%d) (18|19|20|21|22|23):" $LOG_FILE 2>/dev/null | wc -l)"
else
    echo "  (bc 패키지 필요)"
fi

echo ""
echo "===== 통계 생성 완료 ====="
