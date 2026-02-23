#!/bin/bash
#==============================================================================
# Elasticsearch 색인 스크립트 (운영 환경)
#==============================================================================
# 설명: 세브란스 내규 Elasticsearch 초기 색인 및 재색인
# 작성일: 2025-12-18
# 사용법:
#   ./elasticsearch_index_production.sh init      # 초기 색인 (전체)
#   ./elasticsearch_index_production.sh reindex   # 재색인 (데이터만)
#   ./elasticsearch_index_production.sh verify    # 검증만
#   ./elasticsearch_index_production.sh help      # 도움말
#==============================================================================

set -e  # 오류 발생 시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 프로젝트 루트 경로
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 로그 파일
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/elasticsearch_indexing_$(date +%Y%m%d_%H%M%S).log"

# Python 스크립트 경로
INDEX_SCRIPT="$SCRIPT_DIR/index_sev.py"

# 환경 설정 로드 (.env 파일)
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
    echo -e "${GREEN}✓${NC} .env 파일 로드됨"
else
    echo -e "${YELLOW}⚠${NC}  .env 파일이 없습니다. 기본 설정 사용"
fi

# Elasticsearch 설정 (기본값)
ES_HOST="${ES_HOST:-localhost}"
ES_PORT="${ES_PORT:-9200}"
ES_INDEX_RULE="${ES_INDEX_RULE:-severance_policy_rule}"
ES_INDEX_ARTICLE="${ES_INDEX_ARTICLE:-severance_policy_article}"
ES_INDEX_APPENDIX="${ES_INDEX_APPENDIX:-severance_policy_appendix}"

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR"

#==============================================================================
# 함수 정의
#==============================================================================

# 로그 함수
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# 에러 메시지 출력 및 종료
error_exit() {
    echo -e "${RED}✗ 오류: $1${NC}" >&2
    log "ERROR" "$1"
    exit 1
}

# 성공 메시지 출력
success() {
    echo -e "${GREEN}✓ $1${NC}"
    log "INFO" "$1"
}

# 경고 메시지 출력
warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
    log "WARN" "$1"
}

# 정보 메시지 출력
info() {
    echo -e "${BLUE}ℹ $1${NC}"
    log "INFO" "$1"
}

# Elasticsearch 서버 상태 확인
check_elasticsearch() {
    info "Elasticsearch 서버 연결 확인 중... ($ES_HOST:$ES_PORT)"

    if ! curl -s -f "http://$ES_HOST:$ES_PORT" > /dev/null 2>&1; then
        error_exit "Elasticsearch 서버에 연결할 수 없습니다: $ES_HOST:$ES_PORT"
    fi

    local es_info=$(curl -s "http://$ES_HOST:$ES_PORT")
    local es_version=$(echo "$es_info" | python3 -c "import sys, json; print(json.load(sys.stdin)['version']['number'])" 2>/dev/null || echo "알 수 없음")

    success "Elasticsearch 연결 성공 (버전: $es_version)"
}

# Python 환경 확인
check_python_env() {
    info "Python 환경 확인 중..."

    if ! command -v python3 &> /dev/null; then
        error_exit "Python3가 설치되어 있지 않습니다."
    fi

    # 필수 패키지 확인
    local required_packages=("elasticsearch" "hanparse")
    local missing_packages=()

    for package in "${required_packages[@]}"; do
        if ! python3 -c "import $package" &> /dev/null; then
            missing_packages+=("$package")
        fi
    done

    if [ ${#missing_packages[@]} -gt 0 ]; then
        error_exit "필수 Python 패키지가 설치되어 있지 않습니다: ${missing_packages[*]}\n설치: pip3 install ${missing_packages[*]}"
    fi

    success "Python 환경 정상"
}

# index_sev.py 스크립트 확인
check_index_script() {
    info "색인 스크립트 확인 중..."

    if [ ! -f "$INDEX_SCRIPT" ]; then
        error_exit "색인 스크립트를 찾을 수 없습니다: $INDEX_SCRIPT"
    fi

    success "색인 스크립트 확인 완료: $INDEX_SCRIPT"
}

# 인덱스 존재 여부 확인
check_index_exists() {
    local index_name=$1

    if curl -s -f -o /dev/null "http://$ES_HOST:$ES_PORT/$index_name" 2>/dev/null; then
        return 0  # 존재
    else
        return 1  # 없음
    fi
}

# 인덱스 문서 수 조회
get_index_count() {
    local index_name=$1

    if check_index_exists "$index_name"; then
        local count=$(curl -s "http://$ES_HOST:$ES_PORT/$index_name/_count" | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])" 2>/dev/null || echo "0")
        echo "$count"
    else
        echo "0"
    fi
}

# 인덱스 백업 (스냅샷)
backup_index() {
    local index_name=$1

    if check_index_exists "$index_name"; then
        warning "기존 인덱스 발견: $index_name"

        # 백업 여부 확인 (자동 백업은 안함, 수동 확인만)
        info "재색인 시 기존 인덱스는 자동 삭제됩니다."
        info "필요 시 수동으로 스냅샷을 생성하세요."
    fi
}

# 규정 매핑 생성
create_rule_mapping() {
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "단계 1/6: 규정 인덱스 매핑 생성 ($ES_INDEX_RULE)"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    backup_index "$ES_INDEX_RULE"

    python3 "$INDEX_SCRIPT" \
        --cmd=CRM \
        --index="$ES_INDEX_RULE" \
        --es_ip="$ES_HOST" \
        --es_port="$ES_PORT" \
        2>&1 | tee -a "$LOG_FILE"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        success "규정 매핑 생성 완료"
    else
        error_exit "규정 매핑 생성 실패"
    fi
}

# 규정 데이터 색인
index_rules() {
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "단계 2/6: 규정 데이터 색인 ($ES_INDEX_RULE)"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    python3 "$INDEX_SCRIPT" \
        --cmd=CRI \
        --index="$ES_INDEX_RULE" \
        --es_ip="$ES_HOST" \
        --es_port="$ES_PORT" \
        2>&1 | tee -a "$LOG_FILE"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        local count=$(get_index_count "$ES_INDEX_RULE")
        success "규정 색인 완료 (문서 수: $count)"
    else
        error_exit "규정 색인 실패"
    fi
}

# 조문 매핑 생성
create_article_mapping() {
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "단계 3/6: 조문 인덱스 매핑 생성 ($ES_INDEX_ARTICLE)"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    backup_index "$ES_INDEX_ARTICLE"

    python3 "$INDEX_SCRIPT" \
        --cmd=CAM \
        --index="$ES_INDEX_ARTICLE" \
        --es_ip="$ES_HOST" \
        --es_port="$ES_PORT" \
        2>&1 | tee -a "$LOG_FILE"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        success "조문 매핑 생성 완료"
    else
        error_exit "조문 매핑 생성 실패"
    fi
}

# 조문 데이터 색인
index_articles() {
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "단계 4/6: 조문 데이터 색인 ($ES_INDEX_ARTICLE)"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    python3 "$INDEX_SCRIPT" \
        --cmd=CAIA \
        --index="$ES_INDEX_ARTICLE" \
        --es_ip="$ES_HOST" \
        --es_port="$ES_PORT" \
        2>&1 | tee -a "$LOG_FILE"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        local count=$(get_index_count "$ES_INDEX_ARTICLE")
        success "조문 색인 완료 (문서 수: $count)"
    else
        error_exit "조문 색인 실패"
    fi
}

# 부록 매핑 생성
create_appendix_mapping() {
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "단계 5/6: 부록 인덱스 매핑 생성 ($ES_INDEX_APPENDIX)"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    backup_index "$ES_INDEX_APPENDIX"

    python3 "$INDEX_SCRIPT" \
        --cmd=CPAM \
        --index="$ES_INDEX_APPENDIX" \
        --es_ip="$ES_HOST" \
        --es_port="$ES_PORT" \
        --root_path="/home/wizice/regulation" \
        2>&1 | tee -a "$LOG_FILE"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        success "부록 매핑 생성 완료"
    else
        error_exit "부록 매핑 생성 실패"
    fi
}

# 부록 데이터 색인
index_appendices() {
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "단계 6/6: 부록 데이터 색인 ($ES_INDEX_APPENDIX)"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    python3 "$INDEX_SCRIPT" \
        --cmd=CPAI \
        --index="$ES_INDEX_APPENDIX" \
        --es_ip="$ES_HOST" \
        --es_port="$ES_PORT" \
        --root_path="/home/wizice/regulation" \
        2>&1 | tee -a "$LOG_FILE"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        local count=$(get_index_count "$ES_INDEX_APPENDIX")
        success "부록 색인 완료 (문서 수: $count)"
    else
        error_exit "부록 색인 실패"
    fi
}

# 색인 검증
verify_indices() {
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "색인 검증"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    echo ""
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│                    색인 결과 요약                         │"
    echo "├─────────────────────────────────────────────────────────┤"

    # 규정 인덱스
    local rule_count=$(get_index_count "$ES_INDEX_RULE")
    if [ "$rule_count" -gt 0 ]; then
        printf "│ ${GREEN}✓${NC} %-30s : %8s 문서    │\n" "규정 ($ES_INDEX_RULE)" "$rule_count"
    else
        printf "│ ${RED}✗${NC} %-30s : %8s 문서    │\n" "규정 ($ES_INDEX_RULE)" "$rule_count"
    fi

    # 조문 인덱스
    local article_count=$(get_index_count "$ES_INDEX_ARTICLE")
    if [ "$article_count" -gt 0 ]; then
        printf "│ ${GREEN}✓${NC} %-30s : %8s 문서    │\n" "조문 ($ES_INDEX_ARTICLE)" "$article_count"
    else
        printf "│ ${RED}✗${NC} %-30s : %8s 문서    │\n" "조문 ($ES_INDEX_ARTICLE)" "$article_count"
    fi

    # 부록 인덱스
    local appendix_count=$(get_index_count "$ES_INDEX_APPENDIX")
    if [ "$appendix_count" -gt 0 ]; then
        printf "│ ${GREEN}✓${NC} %-30s : %8s 문서    │\n" "부록 ($ES_INDEX_APPENDIX)" "$appendix_count"
    else
        printf "│ ${YELLOW}⚠${NC} %-30s : %8s 문서    │\n" "부록 ($ES_INDEX_APPENDIX)" "$appendix_count"
    fi

    echo "├─────────────────────────────────────────────────────────┤"
    local total_count=$((rule_count + article_count + appendix_count))
    printf "│ %-30s : %8s 문서    │\n" "총 문서 수" "$total_count"
    echo "└─────────────────────────────────────────────────────────┘"
    echo ""

    # 클러스터 상태
    info "Elasticsearch 클러스터 상태:"
    curl -s "http://$ES_HOST:$ES_PORT/_cluster/health?pretty" | grep -E "cluster_name|status|number_of_nodes"

    echo ""

    if [ "$rule_count" -eq 0 ] || [ "$article_count" -eq 0 ]; then
        warning "필수 인덱스에 데이터가 없습니다!"
        return 1
    else
        success "색인 검증 완료"
        return 0
    fi
}

# 샘플 검색 테스트
test_search() {
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "검색 기능 테스트"
    info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    echo ""
    info "규정 검색 테스트 (검색어: 환자)"
    curl -s "http://$ES_HOST:$ES_PORT/$ES_INDEX_RULE/_search?q=규정명:*환자*&size=3" | \
        python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"검색 결과: {data['hits']['total']['value']}건\"); [print(f\"  - {hit['_source']['규정명']}\") for hit in data['hits']['hits'][:3]]" 2>/dev/null || \
        warning "검색 테스트 실패"

    echo ""
}

# 초기 색인 (전체)
init_all() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║       Elasticsearch 초기 색인 시작 (운영 환경)            ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""

    info "Elasticsearch 서버: $ES_HOST:$ES_PORT"
    info "규정 인덱스: $ES_INDEX_RULE"
    info "조문 인덱스: $ES_INDEX_ARTICLE"
    info "부록 인덱스: $ES_INDEX_APPENDIX"
    info "로그 파일: $LOG_FILE"
    echo ""

    # 사전 확인
    check_elasticsearch
    check_python_env
    check_index_script

    echo ""
    read -p "색인을 시작하시겠습니까? (기존 인덱스는 삭제됩니다) [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "색인 취소됨"
        exit 0
    fi

    local start_time=$(date +%s)

    # 색인 실행
    create_rule_mapping
    index_rules
    create_article_mapping
    index_articles
    create_appendix_mapping
    index_appendices

    # 검증
    if verify_indices; then
        test_search
    fi

    local end_time=$(date +%s)
    local elapsed=$((end_time - start_time))
    local minutes=$((elapsed / 60))
    local seconds=$((elapsed % 60))

    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║              색인 작업 완료!                              ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    success "총 소요 시간: ${minutes}분 ${seconds}초"
    info "로그 파일: $LOG_FILE"
    echo ""
}

# 재색인 (매핑 유지, 데이터만)
reindex_all() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║           Elasticsearch 재색인 시작 (데이터만)            ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""

    check_elasticsearch
    check_python_env
    check_index_script

    echo ""
    read -p "재색인을 시작하시겠습니까? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "재색인 취소됨"
        exit 0
    fi

    local start_time=$(date +%s)

    # 데이터만 재색인
    index_rules
    index_articles
    index_appendices

    # 검증
    verify_indices

    local end_time=$(date +%s)
    local elapsed=$((end_time - start_time))
    local minutes=$((elapsed / 60))
    local seconds=$((elapsed % 60))

    echo ""
    success "재색인 완료! (소요 시간: ${minutes}분 ${seconds}초)"
    info "로그 파일: $LOG_FILE"
    echo ""
}

# 검증만 실행
verify_only() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║              Elasticsearch 색인 검증                      ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""

    check_elasticsearch

    if verify_indices; then
        test_search
        success "검증 완료"
    else
        error_exit "검증 실패"
    fi

    echo ""
}

# 도움말
show_help() {
    cat << EOF

╔═══════════════════════════════════════════════════════════╗
║   Elasticsearch 색인 스크립트 - 사용법                    ║
╚═══════════════════════════════════════════════════════════╝

사용법: $0 <command>

명령어:
  init      초기 색인 (매핑 생성 + 데이터 색인)
            - 기존 인덱스 삭제 후 새로 생성
            - 처음 설치 시 또는 전체 재구성 시 사용

  reindex   재색인 (데이터만 업데이트)
            - 매핑은 유지하고 데이터만 재색인
            - 정기 업데이트 시 사용

  verify    검증만 (색인 상태 확인)
            - 인덱스 존재 여부 및 문서 수 확인
            - 검색 기능 테스트

  help      이 도움말 표시

환경 변수 (.env 파일):
  ES_HOST              Elasticsearch 호스트 (기본값: localhost)
  ES_PORT              Elasticsearch 포트 (기본값: 9200)
  ES_INDEX_RULE        규정 인덱스명
  ES_INDEX_ARTICLE     조문 인덱스명
  ES_INDEX_APPENDIX    부록 인덱스명

예시:
  # 초기 색인 (처음 실행 시)
  $0 init

  # 데이터 업데이트 (재색인)
  $0 reindex

  # 색인 상태 확인
  $0 verify

로그:
  모든 실행 로그는 $LOG_DIR/ 에 저장됩니다.

EOF
}

#==============================================================================
# 메인 로직
#==============================================================================

case "${1:-}" in
    init)
        init_all
        ;;
    reindex)
        reindex_all
        ;;
    verify)
        verify_only
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}오류: 올바른 명령어를 입력하세요.${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

exit 0
