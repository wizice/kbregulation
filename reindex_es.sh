#!/bin/bash
##############################################################################
# reindex_es.sh - Elasticsearch 전체 재색인 스크립트
#
# 사용법:
#   /home/wizice/kbregulation/reindex_es.sh
#   /home/wizice/kbregulation/reindex_es.sh --es-ip localhost --es-port 9200
#
# 기능:
#   1. Elasticsearch 연결 대기
#   2. 규정 목록 인덱스 생성 + 색인 (kbregulation_policy_rule)
#   3. 조문 인덱스 생성 + 색인 (kbregulation_policy_article)
#   4. 부록 인덱스 생성 + 색인 (kbregulation_policy_appendix)
#   5. 색인 결과 확인
#
# 의존성:
#   - Python venv: /home/wizice/venv3
#   - 앱 코드:    /home/wizice/kbregulation/fastapi/index_sev.py
#   - JSON 파일:  /home/wizice/kbregulation/www/static/file/*.json
#   - PostgreSQL:  localhost:35432 (부록 색인 시 필요)
#   - Elasticsearch: localhost:9200
##############################################################################
set -euo pipefail

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# 기본값
ES_IP="localhost"
ES_PORT="9200"
VENV_DIR="/home/wizice/venv3"
APP_DIR="/home/wizice/kbregulation"
FASTAPI_DIR="${APP_DIR}/fastapi"
INDEX_RULE="kbregulation_policy_rule"
INDEX_ARTICLE="kbregulation_policy_article"
INDEX_APPENDIX="kbregulation_policy_appendix"
MAX_WAIT=180

# 인자 파싱
while [[ $# -gt 0 ]]; do
  case $1 in
    --es-ip)   ES_IP="$2";   shift 2 ;;
    --es-port) ES_PORT="$2"; shift 2 ;;
    --max-wait) MAX_WAIT="$2"; shift 2 ;;
    -h|--help)
      echo "사용법: $0 [--es-ip IP] [--es-port PORT] [--max-wait SECONDS]"
      echo ""
      echo "옵션:"
      echo "  --es-ip     Elasticsearch IP (기본값: localhost)"
      echo "  --es-port   Elasticsearch 포트 (기본값: 9200)"
      echo "  --max-wait  ES 대기 최대 시간 초 (기본값: 180)"
      exit 0 ;;
    *) echo "알 수 없는 옵션: $1"; exit 1 ;;
  esac
done

ES_URL="http://${ES_IP}:${ES_PORT}"
SCRIPT_LOG="${APP_DIR}/reindex_es.log"

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$SCRIPT_LOG"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] [경고]${NC} $1" | tee -a "$SCRIPT_LOG"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] [오류]${NC} $1" | tee -a "$SCRIPT_LOG"; }
info() { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$SCRIPT_LOG"; }

echo "" > "$SCRIPT_LOG"
log "====================================================="
log "  Elasticsearch 전체 재색인"
log "  ES: ${ES_URL}"
log "  시작: $(date '+%Y-%m-%d %H:%M:%S')"
log "====================================================="

##############################################################################
# 1. 사전 검사
##############################################################################
log ""
log "===== [사전검사] ====="

# venv 확인 및 활성화
if [ ! -f "${VENV_DIR}/bin/activate" ]; then
  err "Python venv를 찾을 수 없습니다: ${VENV_DIR}"
  exit 1
fi
source "${VENV_DIR}/bin/activate"
log "Python venv 활성화: $(python3 --version)"

# index_sev.py 확인
if [ ! -f "${FASTAPI_DIR}/index_sev.py" ]; then
  err "index_sev.py를 찾을 수 없습니다: ${FASTAPI_DIR}/index_sev.py"
  exit 1
fi
log "index_sev.py 확인 OK"

# JSON 파일 확인
JSON_COUNT=$(ls "${APP_DIR}/www/static/file/"*.json 2>/dev/null | wc -l)
if [ "$JSON_COUNT" -eq 0 ]; then
  err "JSON 파일이 없습니다: ${APP_DIR}/www/static/file/"
  exit 1
fi
log "JSON 파일: ${JSON_COUNT}개"

# 로그 디렉토리 생성
mkdir -p "${FASTAPI_DIR}/logs" 2>/dev/null || true

##############################################################################
# 2. Elasticsearch 연결 대기
##############################################################################
log ""
log "===== [ES 연결 대기] ====="

WAITED=0
ES_READY=false

while [ $WAITED -lt $MAX_WAIT ]; do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${ES_URL}" 2>/dev/null || echo "000")

  if [ "$HTTP_CODE" = "200" ]; then
    ES_READY=true
    break
  fi

  # HTTPS 리다이렉트(301) 또는 인증 필요(401)인 경우 안내
  if [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "403" ]; then
    err "ES가 HTTPS/인증을 요구합니다 (HTTP ${HTTP_CODE})"
    err "elasticsearch.yml에서 xpack.security.enabled: false 설정 필요"
    exit 1
  fi

  if [ "$HTTP_CODE" = "401" ]; then
    err "ES 인증이 필요합니다 (HTTP 401)"
    err "elasticsearch.yml에서 xpack.security.enabled: false 설정 필요"
    exit 1
  fi

  info "  ES 응답 대기 중... (${WAITED}/${MAX_WAIT}초, HTTP=${HTTP_CODE})"
  sleep 5
  WAITED=$((WAITED + 5))
done

if [ "$ES_READY" = false ]; then
  err "Elasticsearch 연결 실패 (${MAX_WAIT}초 초과): ${ES_URL}"
  err "확인 사항:"
  err "  1. systemctl status elasticsearch"
  err "  2. journalctl -u elasticsearch --no-pager -n 30"
  err "  3. elasticsearch.yml 에서 xpack.security.enabled: false 확인"
  exit 1
fi

# 클러스터 상태 확인
ES_STATUS=$(curl -s "${ES_URL}/_cluster/health?timeout=30s" 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null \
  || echo "unknown")
ES_VERSION=$(curl -s "${ES_URL}" 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('version',{}).get('number','unknown'))" 2>/dev/null \
  || echo "unknown")

log "ES 연결 성공 (version: ${ES_VERSION}, status: ${ES_STATUS})"

if [ "$ES_STATUS" = "red" ]; then
  warn "클러스터 상태가 RED입니다. 색인을 계속 시도합니다..."
fi

##############################################################################
# 3. 규정 목록 색인 (Rule Index)
##############################################################################
log ""
log "===== [1/3] 규정 목록 색인 ====="
log "  인덱스: ${INDEX_RULE}"

cd "${FASTAPI_DIR}"

log "  (a) 매핑 생성..."
python3 index_sev.py \
  --cmd=CRM \
  --index="${INDEX_RULE}" \
  --es_ip="${ES_IP}" \
  --es_port="${ES_PORT}" 2>&1 | tee -a "$SCRIPT_LOG"

log "  (b) 데이터 색인..."
python3 index_sev.py \
  --cmd=CRI \
  --index="${INDEX_RULE}" \
  --es_ip="${ES_IP}" \
  --es_port="${ES_PORT}" 2>&1 | tee -a "$SCRIPT_LOG"

# 색인 건수 확인 (ES 반영 대기)
sleep 2
RULE_COUNT=$(curl -s "${ES_URL}/${INDEX_RULE}/_count" 2>/dev/null \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null \
  || echo "?")
log "  [1/3] 완료: 규정 ${RULE_COUNT}건 색인됨"

##############################################################################
# 4. 조문 색인 (Article Index)
##############################################################################
log ""
log "===== [2/3] 조문 색인 ====="
log "  인덱스: ${INDEX_ARTICLE}"

log "  (a) 매핑 생성..."
python3 index_sev.py \
  --cmd=CAM \
  --index="${INDEX_ARTICLE}" \
  --es_ip="${ES_IP}" \
  --es_port="${ES_PORT}" 2>&1 | tee -a "$SCRIPT_LOG"

log "  (b) 전체 데이터 색인 (시간이 소요됩니다)..."
python3 index_sev.py \
  --cmd=CAIA \
  --index="${INDEX_ARTICLE}" \
  --es_ip="${ES_IP}" \
  --es_port="${ES_PORT}" 2>&1 | tee -a "$SCRIPT_LOG"

sleep 2
ARTICLE_COUNT=$(curl -s "${ES_URL}/${INDEX_ARTICLE}/_count" 2>/dev/null \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null \
  || echo "?")
log "  [2/3] 완료: 조문 ${ARTICLE_COUNT}건 색인됨"

##############################################################################
# 5. 부록 색인 (Appendix Index)
##############################################################################
log ""
log "===== [3/3] 부록 색인 ====="
log "  인덱스: ${INDEX_APPENDIX}"

log "  (a) 매핑 생성..."
python3 index_sev.py \
  --cmd=CPAM \
  --index="${INDEX_APPENDIX}" \
  --es_ip="${ES_IP}" \
  --es_port="${ES_PORT}" 2>&1 | tee -a "$SCRIPT_LOG"

log "  (b) 전체 데이터 색인..."
python3 index_sev.py \
  --cmd=CPAI \
  --index="${INDEX_APPENDIX}" \
  --es_ip="${ES_IP}" \
  --es_port="${ES_PORT}" 2>&1 | tee -a "$SCRIPT_LOG"

sleep 2
APPENDIX_COUNT=$(curl -s "${ES_URL}/${INDEX_APPENDIX}/_count" 2>/dev/null \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null \
  || echo "?")
log "  [3/3] 완료: 부록 ${APPENDIX_COUNT}건 색인됨"

##############################################################################
# 6. 최종 결과 확인
##############################################################################
log ""
log "====================================================="
log "  재색인 완료 요약"
log "====================================================="
log ""
log "  --- 인덱스 현황 ---"
curl -s "${ES_URL}/_cat/indices?v&h=index,docs.count,store.size" 2>/dev/null \
  | grep -E "(index|kbregulation)" | tee -a "$SCRIPT_LOG"
log ""
log "  규정 목록 (rule):     ${RULE_COUNT}건"
log "  조문 (article):       ${ARTICLE_COUNT}건"
log "  부록 (appendix):      ${APPENDIX_COUNT}건"
log ""
log "  로그 파일: ${SCRIPT_LOG}"
log "  완료: $(date '+%Y-%m-%d %H:%M:%S')"
log "====================================================="
