#!/bin/bash
##############################################################################
# deploy.sh - 반복 배포 패키지 생성 스크립트 (개발 서버용)
#
# 사용법:
#   ./deploy.sh init                # 초기 스냅샷 생성
#   ./deploy.sh update              # 코드 + DB + 변경된 규정 데이터 (일반)
#   ./deploy.sh code                # 소스코드만
#   ./deploy.sh db                  # DB 덤프만
#   ./deploy.sh data                # 규정 데이터만
#   ./deploy.sh full                # 전체
#
# 옵션:
#   --include-media                 # PDF/이미지 포함
#   --include-venv                  # Python venv 포함
#   --include-rpms                  # RPM 패키지 포함
#   --dry-run                       # 실제 패키지 생성 없이 변경 목록만 출력
#
# 설명:
#   스냅샷 기반 변경 감지로 변경된 파일만 패키지에 포함.
#   운영 서버에서 apply_update.sh로 적용.
##############################################################################
set -euo pipefail

# ─── 경로 설정 ───────────────────────────────────────────────────────────────
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_STATE="${BASE_DIR}/.deploy_state"
SNAPSHOT_FILE="${DEPLOY_STATE}/snapshot.txt"
HISTORY_FILE="${DEPLOY_STATE}/deploy_history.json"

VENV_DIR="/home/wizice/venv3"
FASTAPI_DIR="${BASE_DIR}/fastapi"
DB_USER="kbregulation"
DB_NAME="kbregulation"
DB_HOST="127.0.0.1"
DB_PORT="35432"

# ─── 색상 ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] [경고]${NC} $1"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] [오류]${NC} $1"; }
info() { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $1"; }

# ─── 파일 분류 패턴 ─────────────────────────────────────────────────────────

# A등급: 소스코드 (항상 추적)
SOURCE_PATTERNS=(
    "*.py" "*.html" "*.js" "*.css"
    "*.sql" "*.sh" "*.cfg" "*.conf"
    "*.json"   # fastapi/ 내 설정 JSON
    "*.ini" "*.yml" "*.yaml" "*.toml"
    "*.env.production" "*.env.development"
    "*.wsgi" "*.service"
)

# 소스코드 디렉토리
SOURCE_DIRS=(
    "fastapi"
    "www"
)

# B등급: 규정 데이터 (update, data 모드)
DATA_DIRS=(
    "www/static/file"
    "www/static/pdf_txt"
)

# C등급: 규정 미디어 (--include-media 시)
MEDIA_DIRS=(
    "www/static/pdf"
    "www/static/extracted_images"
)

# D등급: 정적 에셋 (full 모드만)
STATIC_DIRS=(
    "docs"
    "www/static/webfonts"
    "www/static/viewer"
    "www/static/lib"
    "www/static/font"
    "www/static/symbol"
)

# 제외 패턴
EXCLUDE_PATTERNS=(
    ".git/"
    "__pycache__/"
    "*.pyc"
    "*.pyo"
    "logs/"
    "fastapi/logs/"
    "log/"
    "pip_file/"
    ".deploy_state/"
    ".deploy_backups/"
    "tmp_zip/"
    "test/"
    "*.dmp"
    "*.tgz"
    "*.tar.gz"
    "*.zip"
    ".env"
    ".env.local"
    "*.log"
    "node_modules/"
    ".vscode/"
    ".idea/"
    "venv/"
    ".venv/"
    "fastapi/db/*.dmp"
)

# ─── 함수 ────────────────────────────────────────────────────────────────────

usage() {
    echo ""
    echo -e "${BOLD}사용법:${NC} $0 <모드> [옵션]"
    echo ""
    echo -e "${BOLD}모드:${NC}"
    echo "  init              초기 스냅샷 생성 (최초 1회)"
    echo "  update            코드 + DB + 변경된 규정 데이터 (일반적 사용)"
    echo "  code              소스코드만 (3~8MB)"
    echo "  db                DB 덤프만 (~5MB)"
    echo "  data              규정 데이터만 (JSON/PDF텍스트)"
    echo "  full              전체 (초기 설치 이후 재구성 용)"
    echo ""
    echo -e "${BOLD}옵션:${NC}"
    echo "  --include-media   변경된 PDF/이미지 포함"
    echo "  --include-venv    Python venv 포함"
    echo "  --include-rpms    RPM 패키지 포함"
    echo "  --dry-run         패키지 생성 없이 변경 목록만 출력"
    echo "  -h, --help        도움말"
    echo ""
    echo -e "${BOLD}예시:${NC}"
    echo "  $0 init                       # 초기 스냅샷 생성"
    echo "  $0 update                     # 코드+DB+규정 데이터 업데이트"
    echo "  $0 update --include-media     # PDF/이미지도 포함"
    echo "  $0 code                       # 소스코드만"
    echo ""
}

# 파일이 제외 대상인지 확인
is_excluded() {
    local file="$1"
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        case "$file" in
            *${pattern}*) return 0 ;;
        esac
    done
    return 1
}

# 파일 확장자가 소스코드인지 확인
is_source_file() {
    local file="$1"
    local ext="${file##*.}"
    case ".$ext" in
        .py|.html|.js|.css|.sql|.sh|.cfg|.conf|.ini|.yml|.yaml|.toml|.wsgi|.service)
            return 0 ;;
    esac
    return 1
}

# 추적 대상 파일 목록 생성 (모드에 따라)
build_file_list() {
    local mode="$1"
    local include_media="$2"
    local tmpfile
    tmpfile=$(mktemp)

    case "$mode" in
        code)
            # A등급만: 소스코드 파일
            for dir in "${SOURCE_DIRS[@]}"; do
                [ -d "${BASE_DIR}/${dir}" ] || continue
                find "${BASE_DIR}/${dir}" -type f \( \
                    -name "*.py" -o -name "*.html" -o -name "*.js" -o -name "*.css" \
                    -o -name "*.sql" -o -name "*.sh" -o -name "*.cfg" -o -name "*.conf" \
                    -o -name "*.ini" -o -name "*.yml" -o -name "*.yaml" -o -name "*.toml" \
                    -o -name "*.wsgi" \
                \) 2>/dev/null
            done | while read -r f; do
                is_excluded "$f" || echo "$f"
            done > "$tmpfile"
            # 루트 레벨 스크립트/설정
            find "${BASE_DIR}" -maxdepth 1 -type f \( \
                -name "*.py" -o -name "*.sh" -o -name "*.cfg" -o -name "*.conf" \
                -o -name "*.wsgi" -o -name "*.yml" \
            \) 2>/dev/null | while read -r f; do
                is_excluded "$f" || echo "$f"
            done >> "$tmpfile"
            ;;

        data)
            # B등급: 규정 데이터
            for dir in "${DATA_DIRS[@]}"; do
                [ -d "${BASE_DIR}/${dir}" ] || continue
                find "${BASE_DIR}/${dir}" -type f 2>/dev/null
            done | while read -r f; do
                is_excluded "$f" || echo "$f"
            done > "$tmpfile"
            if [ "$include_media" = "true" ]; then
                for dir in "${MEDIA_DIRS[@]}"; do
                    [ -d "${BASE_DIR}/${dir}" ] || continue
                    find "${BASE_DIR}/${dir}" -type f 2>/dev/null
                done | while read -r f; do
                    is_excluded "$f" || echo "$f"
                done >> "$tmpfile"
            fi
            ;;

        update)
            # A+B등급: 소스코드 + 규정 데이터
            build_file_list "code" "false" > /dev/null
            cat "$(build_file_list_path code)" > "$tmpfile"
            build_file_list "data" "$include_media" > /dev/null
            cat "$(build_file_list_path data)" >> "$tmpfile"
            ;;

        full)
            # 전체: A+B+C+D
            for dir in "${SOURCE_DIRS[@]}" "${DATA_DIRS[@]}" "${MEDIA_DIRS[@]}" "${STATIC_DIRS[@]}"; do
                [ -d "${BASE_DIR}/${dir}" ] || continue
                find "${BASE_DIR}/${dir}" -type f 2>/dev/null
            done | while read -r f; do
                is_excluded "$f" || echo "$f"
            done > "$tmpfile"
            find "${BASE_DIR}" -maxdepth 1 -type f 2>/dev/null | while read -r f; do
                is_excluded "$f" || echo "$f"
            done >> "$tmpfile"
            ;;
    esac

    sort -u "$tmpfile"
    rm -f "$tmpfile"
}

# 모드별 임시 파일 경로 (재귀 호출 지원)
build_file_list_path() {
    echo "/tmp/deploy_filelist_$1"
}

# md5 스냅샷 생성
create_snapshot() {
    local file_list="$1"
    local output="$2"
    local count=0
    local total
    total=$(wc -l < "$file_list")

    > "$output"
    while IFS= read -r filepath; do
        if [ -f "$filepath" ]; then
            local relpath="${filepath#${BASE_DIR}/}"
            local md5
            md5=$(md5sum "$filepath" | awk '{print $1}')
            echo "${md5}  ${relpath}" >> "$output"
            count=$((count + 1))
            if [ $((count % 500)) -eq 0 ]; then
                info "  스냅샷 진행: ${count}/${total} 파일..."
            fi
        fi
    done < "$file_list"
    log "  스냅샷 완료: ${count}개 파일"
}

# 스냅샷 비교 → 변경/신규/삭제 파일 목록
diff_snapshots() {
    local old_snap="$1"
    local new_snap="$2"
    local changed_file="$3"
    local added_file="$4"
    local deleted_file="$5"

    > "$changed_file"
    > "$added_file"
    > "$deleted_file"

    # old를 연관 배열로 로드
    declare -A old_map
    if [ -f "$old_snap" ]; then
        while IFS= read -r line; do
            local md5="${line%%  *}"
            local path="${line#*  }"
            old_map["$path"]="$md5"
        done < "$old_snap"
    fi

    # new 스냅샷 순회
    declare -A new_map
    while IFS= read -r line; do
        local md5="${line%%  *}"
        local path="${line#*  }"
        new_map["$path"]="$md5"

        if [ -z "${old_map[$path]+x}" ]; then
            echo "$path" >> "$added_file"
        elif [ "${old_map[$path]}" != "$md5" ]; then
            echo "$path" >> "$changed_file"
        fi
    done < "$new_snap"

    # 삭제된 파일 (old에 있지만 new에 없고, 실제로 디스크에서도 없는 경우)
    if [ -f "$old_snap" ]; then
        while IFS= read -r line; do
            local path="${line#*  }"
            if [ -z "${new_map[$path]+x}" ]; then
                # 실제로 파일이 삭제된 경우만 포함
                if [ ! -f "${BASE_DIR}/${path}" ]; then
                    echo "$path" >> "$deleted_file"
                fi
            fi
        done < "$old_snap"
    fi
}

# DB 덤프 생성
dump_database() {
    local output_dir="$1"
    mkdir -p "${output_dir}/db"
    log "  DB 덤프 중..."
    export PGPASSWORD='rhj3r>PL*sXO#t0>E'
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        -d "$DB_NAME" -Fc \
        -f "${output_dir}/db/pg_dump.dmp" 2>/dev/null; then
        local size
        size=$(du -sh "${output_dir}/db/pg_dump.dmp" | awk '{print $1}')
        log "  DB 덤프 완료: ${size}"
        # SQL 형식으로도 생성 (마이그레이션 용이)
        pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
            -d "$DB_NAME" --clean --if-exists --no-owner \
            -f "${output_dir}/db/pg_dump.sql" 2>/dev/null || true
    else
        warn "  DB 덤프 실패 (패키지에 DB 미포함)"
        return 1
    fi
    unset PGPASSWORD
}

# 마이그레이션 SQL 수집
collect_migrations() {
    local output_dir="$1"
    if [ -d "${FASTAPI_DIR}/sql" ]; then
        local sql_count
        sql_count=$(find "${FASTAPI_DIR}/sql" -name "*.sql" -type f 2>/dev/null | wc -l)
        if [ "$sql_count" -gt 0 ]; then
            mkdir -p "${output_dir}/db/migrations"
            cp -r "${FASTAPI_DIR}/sql/"*.sql "${output_dir}/db/migrations/" 2>/dev/null || true
            log "  마이그레이션 SQL: ${sql_count}개 수집"
        fi
    fi
}

# JSON 파일에서 규정 seq 추출
extract_rule_seq_from_json() {
    local json_file="$1"
    local basename
    basename=$(basename "$json_file" .json)
    # JSON 파일명은 보통 "{seq}_*.json" 또는 "{seq}.json" 형식
    echo "$basename" | grep -oP '^\d+' || true
}

# ES 재색인 전략 결정
determine_reindex_strategy() {
    local changed_file="$1"
    local added_file="$2"
    local deleted_file="$3"

    local json_changes=0
    local pdf_txt_changes=0
    local code_changes=0
    local rule_seqs=()

    for listfile in "$changed_file" "$added_file"; do
        [ -f "$listfile" ] || continue
        while IFS= read -r path; do
            case "$path" in
                www/static/file/*.json)
                    json_changes=$((json_changes + 1))
                    local seq
                    seq=$(extract_rule_seq_from_json "$path")
                    [ -n "$seq" ] && rule_seqs+=("$seq")
                    ;;
                www/static/pdf_txt/*)
                    pdf_txt_changes=$((pdf_txt_changes + 1))
                    ;;
                *)
                    code_changes=$((code_changes + 1))
                    ;;
            esac
        done < "$listfile"
    done

    # 삭제된 JSON도 카운트
    if [ -f "$deleted_file" ]; then
        while IFS= read -r path; do
            case "$path" in
                www/static/file/*.json)
                    json_changes=$((json_changes + 1))
                    ;;
            esac
        done < "$deleted_file"
    fi

    # 고유 rule_seq
    local unique_seqs=()
    if [ ${#rule_seqs[@]} -gt 0 ]; then
        mapfile -t unique_seqs < <(printf '%s\n' "${rule_seqs[@]}" | sort -un)
    fi

    local reindex_mode="none"
    local reindex_targets=""

    if [ "$json_changes" -eq 0 ] && [ "$pdf_txt_changes" -eq 0 ]; then
        reindex_mode="none"
    elif [ "$json_changes" -gt 80 ]; then
        reindex_mode="full"
    elif [ "$json_changes" -gt 0 ]; then
        reindex_mode="selective"
        reindex_targets=$(printf '%s,' "${unique_seqs[@]}" | sed 's/,$//')
    fi

    local reindex_appendix="false"
    if [ "$pdf_txt_changes" -gt 0 ]; then
        reindex_appendix="true"
    fi

    echo "${reindex_mode}|${reindex_targets}|${reindex_appendix}|${json_changes}|${pdf_txt_changes}"
}

# manifest.json 생성
create_manifest() {
    local output_dir="$1"
    local mode="$2"
    local changed_file="$3"
    local added_file="$4"
    local deleted_file="$5"
    local include_media="$6"
    local include_venv="$7"
    local include_rpms="$8"

    local changed_count=0 added_count=0 deleted_count=0
    [ -f "$changed_file" ] && changed_count=$(wc -l < "$changed_file")
    [ -f "$added_file" ] && added_count=$(wc -l < "$added_file")
    [ -f "$deleted_file" ] && deleted_count=$(wc -l < "$deleted_file")

    # ES 재색인 전략
    local es_info
    es_info=$(determine_reindex_strategy "$changed_file" "$added_file" "$deleted_file")
    IFS='|' read -r reindex_mode reindex_targets reindex_appendix json_changes pdf_txt_changes <<< "$es_info"

    # 서비스 재시작 여부
    local restart_fastapi="true"
    if [ "$mode" = "db" ]; then
        restart_fastapi="false"
    fi

    # 삭제 파일 JSON 배열
    local deleted_json="[]"
    if [ -f "$deleted_file" ] && [ "$deleted_count" -gt 0 ]; then
        deleted_json="["
        local first=true
        while IFS= read -r path; do
            if [ "$first" = true ]; then
                first=false
            else
                deleted_json+=","
            fi
            deleted_json+="\"${path}\""
        done < "$deleted_file"
        deleted_json+="]"
    fi

    cat > "${output_dir}/manifest.json" << MANIFEST_EOF
{
    "version": "1.0",
    "created": "$(date -Iseconds)",
    "created_by": "$(whoami)@$(hostname)",
    "mode": "${mode}",
    "base_dir": "/home/wizice/kbregulation",
    "summary": {
        "changed_files": ${changed_count},
        "added_files": ${added_count},
        "deleted_files": ${deleted_count},
        "total_files": $((changed_count + added_count))
    },
    "options": {
        "include_media": ${include_media},
        "include_venv": ${include_venv},
        "include_rpms": ${include_rpms}
    },
    "service": {
        "restart_fastapi": ${restart_fastapi},
        "service_name": "fastapi-kbregulation"
    },
    "database": {
        "included": $([ -f "${output_dir}/db/pg_dump.dmp" ] && echo "true" || echo "false"),
        "format": "custom",
        "db_name": "${DB_NAME}",
        "db_user": "${DB_USER}",
        "db_port": "${DB_PORT}"
    },
    "elasticsearch": {
        "reindex_mode": "${reindex_mode}",
        "reindex_targets": "${reindex_targets}",
        "reindex_appendix": ${reindex_appendix},
        "json_changes": ${json_changes},
        "pdf_txt_changes": ${pdf_txt_changes}
    },
    "deleted_files": ${deleted_json}
}
MANIFEST_EOF

    log "  manifest.json 생성 완료"
}

# apply_update.sh 생성
generate_apply_script() {
    local output_dir="$1"
    cat > "${output_dir}/apply_update.sh" << 'APPLY_EOF'
#!/bin/bash
##############################################################################
# apply_update.sh - 운영 서버용 업데이트 적용 스크립트
#
# 사용법:
#   sudo ./apply_update.sh              # 업데이트 적용
#   sudo ./apply_update.sh --dry-run    # 시뮬레이션만
#   sudo ./apply_update.sh --rollback   # 최근 백업으로 복원
#   sudo ./apply_update.sh --skip-es    # ES 재색인 건너뛰기
#   sudo ./apply_update.sh --skip-db    # DB 복원 건너뛰기
##############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MANIFEST="${SCRIPT_DIR}/manifest.json"

# ─── 색상 ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] [경고]${NC} $1"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] [오류]${NC} $1"; }
info() { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $1"; }

# ─── JSON 파서 (Python 사용) ─────────────────────────────────────────────────
json_val() {
    python3 -c "import json,sys; d=json.load(open('${MANIFEST}')); print(d${1})" 2>/dev/null
}

json_arr() {
    python3 -c "
import json,sys
d=json.load(open('${MANIFEST}'))
arr=d${1}
for item in arr:
    print(item)
" 2>/dev/null
}

# ─── 인자 파싱 ───────────────────────────────────────────────────────────────
DRY_RUN=false
ROLLBACK=false
SKIP_ES=false
SKIP_DB=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)   DRY_RUN=true;  shift ;;
        --rollback)  ROLLBACK=true; shift ;;
        --skip-es)   SKIP_ES=true;  shift ;;
        --skip-db)   SKIP_DB=true;  shift ;;
        -h|--help)
            echo "사용법: sudo $0 [--dry-run] [--rollback] [--skip-es] [--skip-db]"
            exit 0 ;;
        *) echo "알 수 없는 옵션: $1"; exit 1 ;;
    esac
done

# ─── 기본 설정 ───────────────────────────────────────────────────────────────
BASE_DIR=$(json_val "['base_dir']")
BACKUP_ROOT="${BASE_DIR}/.deploy_backups"
STATE_DIR="${BASE_DIR}/.deploy_state"
VENV_DIR="/home/wizice/venv3"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
LOG_FILE="${STATE_DIR}/apply_${TIMESTAMP}.log"

SERVICE_NAME=$(json_val "['service']['service_name']")
RESTART_FASTAPI=$(json_val "['service']['restart_fastapi']")
DB_INCLUDED=$(json_val "['database']['included']")
DB_NAME=$(json_val "['database']['db_name']")
DB_USER=$(json_val "['database']['db_user']")
DB_PORT=$(json_val "['database']['db_port']")
REINDEX_MODE=$(json_val "['elasticsearch']['reindex_mode']")
REINDEX_TARGETS=$(json_val "['elasticsearch']['reindex_targets']")
REINDEX_APPENDIX=$(json_val "['elasticsearch']['reindex_appendix']")
MODE=$(json_val "['mode']")

mkdir -p "$STATE_DIR" "$BACKUP_ROOT"

exec > >(tee -a "$LOG_FILE") 2>&1

# ─── 롤백 처리 ───────────────────────────────────────────────────────────────
if [ "$ROLLBACK" = true ]; then
    log "===== 롤백 모드 ====="
    LATEST_BACKUP=$(ls -td "${BACKUP_ROOT}/"*/ 2>/dev/null | head -1)
    if [ -z "$LATEST_BACKUP" ]; then
        err "복원 가능한 백업이 없습니다."
        exit 1
    fi
    log "복원 대상: ${LATEST_BACKUP}"

    if [ -f "${LATEST_BACKUP}/db_backup.dmp" ]; then
        log "DB 복원 중..."
        export PGPASSWORD='rhj3r>PL*sXO#t0>E'
        pg_restore -h 127.0.0.1 -p "$DB_PORT" -U "$DB_USER" \
            -d "$DB_NAME" --clean --if-exists --no-owner \
            "${LATEST_BACKUP}/db_backup.dmp" 2>&1 | grep -v "WARNING" || true
        unset PGPASSWORD
        log "DB 복원 완료"
    fi

    if [ -f "${LATEST_BACKUP}/files_backup.tar.gz" ]; then
        log "파일 복원 중..."
        tar xzf "${LATEST_BACKUP}/files_backup.tar.gz" -C /
        log "파일 복원 완료"
    fi

    systemctl restart "$SERVICE_NAME" 2>/dev/null || true
    log "===== 롤백 완료 ====="
    exit 0
fi

# ─── 메인 적용 시작 ──────────────────────────────────────────────────────────
log "====================================================="
log "  업데이트 적용 시작"
log "  모드: ${MODE}"
log "  시간: $(date '+%Y-%m-%d %H:%M:%S')"
if [ "$DRY_RUN" = true ]; then
    log "  *** DRY-RUN 모드 (실제 변경 없음) ***"
fi
log "====================================================="
echo ""

# ─── 1. 검증 ─────────────────────────────────────────────────────────────────
log "[1/9] manifest 검증..."
if [ ! -f "$MANIFEST" ]; then
    err "manifest.json을 찾을 수 없습니다: ${MANIFEST}"
    exit 1
fi

CHANGED=$(json_val "['summary']['changed_files']")
ADDED=$(json_val "['summary']['added_files']")
DELETED=$(json_val "['summary']['deleted_files']")
TOTAL=$((CHANGED + ADDED))

log "  변경: ${CHANGED}, 신규: ${ADDED}, 삭제: ${DELETED}, 총: ${TOTAL}개 파일"
log "  DB 포함: ${DB_INCLUDED}, ES 재색인: ${REINDEX_MODE}"

# ─── 2. 백업 ─────────────────────────────────────────────────────────────────
log "[2/9] 현재 상태 백업..."
if [ "$DRY_RUN" = false ]; then
    mkdir -p "$BACKUP_DIR"

    # 변경될 파일 백업
    if [ -d "${SCRIPT_DIR}/files" ] && [ "$TOTAL" -gt 0 ]; then
        BACKUP_FILES_LIST=$(mktemp)
        find "${SCRIPT_DIR}/files" -type f | while read -r src; do
            local relpath="${src#${SCRIPT_DIR}/files/}"
            local target="${BASE_DIR}/${relpath}"
            if [ -f "$target" ]; then
                echo "$target"
            fi
        done > "$BACKUP_FILES_LIST" 2>/dev/null || true

        # 삭제 대상 파일도 백업 목록에 추가
        json_arr "['deleted_files']" >> "$BACKUP_FILES_LIST" 2>/dev/null || true

        if [ -s "$BACKUP_FILES_LIST" ]; then
            tar czf "${BACKUP_DIR}/files_backup.tar.gz" \
                -T "$BACKUP_FILES_LIST" 2>/dev/null || true
        fi
        rm -f "$BACKUP_FILES_LIST"
    fi

    # DB 백업
    if [ "$DB_INCLUDED" = "True" ] || [ "$DB_INCLUDED" = "true" ]; then
        export PGPASSWORD='rhj3r>PL*sXO#t0>E'
        pg_dump -h 127.0.0.1 -p "$DB_PORT" -U "$DB_USER" \
            -d "$DB_NAME" -Fc \
            -f "${BACKUP_DIR}/db_backup.dmp" 2>/dev/null || warn "DB 백업 실패"
        unset PGPASSWORD
    fi

    log "  백업 저장: ${BACKUP_DIR}"

    # 오래된 백업 정리 (최근 5개 유지)
    ls -td "${BACKUP_ROOT}/"*/ 2>/dev/null | tail -n +6 | while read -r old; do
        rm -rf "$old"
    done
else
    log "  [DRY-RUN] 백업 건너뜀"
fi

# ─── 3. 서비스 중지 ──────────────────────────────────────────────────────────
log "[3/9] 서비스 중지..."
if [ "$DRY_RUN" = false ] && [ "$RESTART_FASTAPI" = "True" ] || [ "$RESTART_FASTAPI" = "true" ]; then
    systemctl stop "$SERVICE_NAME" 2>/dev/null || warn "서비스 중지 실패 (이미 중지 상태일 수 있음)"
    sleep 1
    log "  ${SERVICE_NAME} 중지됨"
else
    log "  [건너뜀] 서비스 중지 불필요"
fi

# ─── 4. DB 적용 ──────────────────────────────────────────────────────────────
log "[4/9] DB 적용..."
if [ "$SKIP_DB" = true ]; then
    log "  [건너뜀] --skip-db 옵션"
elif [ "$DB_INCLUDED" = "True" ] || [ "$DB_INCLUDED" = "true" ]; then
    if [ "$DRY_RUN" = false ]; then
        export PGPASSWORD='rhj3r>PL*sXO#t0>E'

        # 마이그레이션 SQL 먼저 실행
        if [ -d "${SCRIPT_DIR}/db/migrations" ]; then
            for sql_file in "${SCRIPT_DIR}/db/migrations/"*.sql; do
                [ -f "$sql_file" ] || continue
                log "  마이그레이션 실행: $(basename "$sql_file")"
                psql -h 127.0.0.1 -p "$DB_PORT" -U "$DB_USER" \
                    -d "$DB_NAME" -f "$sql_file" 2>&1 || warn "SQL 실행 경고: $(basename "$sql_file")"
            done
        fi

        # DB 덤프 복원
        if [ -f "${SCRIPT_DIR}/db/pg_dump.dmp" ]; then
            log "  DB 덤프 복원 중..."
            pg_restore -h 127.0.0.1 -p "$DB_PORT" -U "$DB_USER" \
                -d "$DB_NAME" --clean --if-exists --no-owner \
                --disable-triggers \
                "${SCRIPT_DIR}/db/pg_dump.dmp" 2>&1 | grep -v "WARNING" || true
            log "  DB 복원 완료"
        fi

        unset PGPASSWORD
    else
        log "  [DRY-RUN] DB 적용 건너뜀"
    fi
else
    log "  [건너뜀] DB 미포함"
fi

# ─── 5. 파일 적용 ────────────────────────────────────────────────────────────
log "[5/9] 파일 적용..."
APPLIED=0

if [ -d "${SCRIPT_DIR}/files" ]; then
    # 변경/신규 파일 복사
    find "${SCRIPT_DIR}/files" -type f | while IFS= read -r src; do
        relpath="${src#${SCRIPT_DIR}/files/}"
        target="${BASE_DIR}/${relpath}"
        target_dir="$(dirname "$target")"

        if [ "$DRY_RUN" = true ]; then
            info "  [DRY-RUN] 복사: ${relpath}"
        else
            mkdir -p "$target_dir"
            cp -f "$src" "$target"
        fi
    done
    APPLIED=$(find "${SCRIPT_DIR}/files" -type f | wc -l)
    log "  ${APPLIED}개 파일 복사 완료"
fi

# 삭제 파일 처리
DELETED_COUNT=0
while IFS= read -r delpath; do
    [ -z "$delpath" ] && continue
    target="${BASE_DIR}/${delpath}"
    if [ -f "$target" ]; then
        if [ "$DRY_RUN" = true ]; then
            info "  [DRY-RUN] 삭제: ${delpath}"
        else
            rm -f "$target"
        fi
        DELETED_COUNT=$((DELETED_COUNT + 1))
    fi
done < <(json_arr "['deleted_files']" 2>/dev/null || true)

[ "$DELETED_COUNT" -gt 0 ] && log "  ${DELETED_COUNT}개 파일 삭제"

# 소유권 수정
if [ "$DRY_RUN" = false ] && [ "$APPLIED" -gt 0 ]; then
    chown -R wizice:wizice "$BASE_DIR" 2>/dev/null || true
fi

# ─── 6. venv/RPM 적용 ────────────────────────────────────────────────────────
log "[6/9] venv/RPM 적용..."
if [ -d "${SCRIPT_DIR}/venv" ] && [ "$DRY_RUN" = false ]; then
    log "  venv 파일 복사 중..."
    cp -rf "${SCRIPT_DIR}/venv/"* "${VENV_DIR}/" 2>/dev/null || true
    chown -R wizice:wizice "${VENV_DIR}" 2>/dev/null || true
    log "  venv 적용 완료"
elif [ -d "${SCRIPT_DIR}/rpms" ] && [ "$DRY_RUN" = false ]; then
    log "  RPM 설치 중..."
    rpm -Uvh "${SCRIPT_DIR}/rpms/"*.rpm 2>/dev/null || true
    log "  RPM 설치 완료"
else
    log "  [건너뜀] venv/RPM 미포함"
fi

# ─── 7. 서비스 시작 ──────────────────────────────────────────────────────────
log "[7/9] 서비스 시작..."
if [ "$DRY_RUN" = false ] && { [ "$RESTART_FASTAPI" = "True" ] || [ "$RESTART_FASTAPI" = "true" ]; }; then
    systemctl start "$SERVICE_NAME"
    sleep 3

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log "  ${SERVICE_NAME} 시작됨 (정상)"
    else
        err "  ${SERVICE_NAME} 시작 실패!"
        warn "  롤백하려면: sudo ./apply_update.sh --rollback"
    fi
else
    log "  [건너뜀] 서비스 시작"
fi

# ─── 8. ES 재색인 ────────────────────────────────────────────────────────────
log "[8/9] Elasticsearch 재색인..."
if [ "$SKIP_ES" = true ]; then
    log "  [건너뜀] --skip-es 옵션"
elif [ "$REINDEX_MODE" = "none" ]; then
    log "  [건너뜀] 재색인 불필요"
elif [ "$DRY_RUN" = true ]; then
    log "  [DRY-RUN] 재색인 모드: ${REINDEX_MODE}"
    [ -n "$REINDEX_TARGETS" ] && log "  [DRY-RUN] 대상 rule_seq: ${REINDEX_TARGETS}"
else
    ES_IP="localhost"
    ES_PORT="9200"
    INDEX_RULE="kbregulation_policy_rule"
    INDEX_ARTICLE="kbregulation_policy_article"
    INDEX_APPENDIX="kbregulation_policy_appendix"

    source "${VENV_DIR}/bin/activate" 2>/dev/null || true
    cd "${BASE_DIR}/fastapi"

    if [ "$REINDEX_MODE" = "full" ]; then
        log "  전체 재색인 실행 중..."
        "${BASE_DIR}/reindex_es.sh" --es-ip "$ES_IP" --es-port "$ES_PORT" || warn "전체 재색인 중 오류 발생"

    elif [ "$REINDEX_MODE" = "selective" ]; then
        # 규정 목록 전체 재색인 (빠름)
        log "  규정 목록 재색인..."
        python3 index_sev.py --cmd=CRM --index="$INDEX_RULE" --es_ip="$ES_IP" --es_port="$ES_PORT" 2>&1 || true
        python3 index_sev.py --cmd=CRI --index="$INDEX_RULE" --es_ip="$ES_IP" --es_port="$ES_PORT" 2>&1 || true

        # 변경된 규정만 조문 재색인
        log "  변경된 조문 선택적 재색인: ${REINDEX_TARGETS}"
        IFS=',' read -ra SEQS <<< "$REINDEX_TARGETS"
        for seq in "${SEQS[@]}"; do
            [ -z "$seq" ] && continue
            info "    rule_seq=${seq} 재색인..."
            python3 index_sev.py \
                --cmd=CAI \
                --rule_seq="$seq" \
                --index="$INDEX_ARTICLE" \
                --es_ip="$ES_IP" \
                --es_port="$ES_PORT" \
                --reindex=REINDEX 2>&1 || warn "rule_seq=${seq} 재색인 실패"
        done
    fi

    # 부록 재색인 (PDF 텍스트 변경 시)
    if [ "$REINDEX_APPENDIX" = "True" ] || [ "$REINDEX_APPENDIX" = "true" ]; then
        log "  부록 재색인 실행 중..."
        python3 index_sev.py --cmd=CPAM --index="$INDEX_APPENDIX" --es_ip="$ES_IP" --es_port="$ES_PORT" 2>&1 || true
        python3 index_sev.py --cmd=CPAI --index="$INDEX_APPENDIX" --es_ip="$ES_IP" --es_port="$ES_PORT" 2>&1 || true
        log "  부록 재색인 완료"
    fi

    cd "$SCRIPT_DIR"
    log "  ES 재색인 완료"
fi

# ─── 9. 검증 ─────────────────────────────────────────────────────────────────
log "[9/9] 검증..."
VERIFY_OK=true

if [ "$DRY_RUN" = false ]; then
    # 서비스 상태 확인
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        log "  서비스 상태: 정상"
    else
        warn "  서비스 상태: 비활성"
        VERIFY_OK=false
    fi

    # ES 인덱스 건수 확인
    ES_URL="http://localhost:9200"
    for idx in kbregulation_policy_rule kbregulation_policy_article kbregulation_policy_appendix; do
        CNT=$(curl -s "${ES_URL}/${idx}/_count" 2>/dev/null \
            | python3 -c "import sys,json; print(json.load(sys.stdin).get('count','?'))" 2>/dev/null \
            || echo "?")
        log "  ES ${idx}: ${CNT}건"
    done

    # FastAPI 헬스체크
    sleep 2
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8800/api/health" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        log "  앱 헬스체크: 정상 (HTTP 200)"
    else
        warn "  앱 헬스체크: HTTP ${HTTP_CODE}"
    fi
fi

# ─── 배포 기록 ────────────────────────────────────────────────────────────────
if [ "$DRY_RUN" = false ]; then
    HISTORY_FILE="${STATE_DIR}/apply_history.json"
    ENTRY=$(cat << HIST_EOF
{
    "timestamp": "$(date -Iseconds)",
    "mode": "${MODE}",
    "files_applied": ${APPLIED},
    "files_deleted": ${DELETED_COUNT},
    "db_restored": $([ "$DB_INCLUDED" = "True" ] || [ "$DB_INCLUDED" = "true" ] && echo "true" || echo "false"),
    "reindex_mode": "${REINDEX_MODE}",
    "backup_dir": "${BACKUP_DIR}",
    "verify_ok": ${VERIFY_OK}
}
HIST_EOF
)
    if [ -f "$HISTORY_FILE" ]; then
        # 기존 배열에 추가
        python3 -c "
import json
with open('${HISTORY_FILE}') as f:
    history = json.load(f)
history.append(json.loads('''${ENTRY}'''))
# 최근 50개만 유지
history = history[-50:]
with open('${HISTORY_FILE}', 'w') as f:
    json.dump(history, f, indent=2, ensure_ascii=False)
" 2>/dev/null || echo "[$ENTRY]" > "$HISTORY_FILE"
    else
        echo "[$ENTRY]" > "$HISTORY_FILE"
    fi
fi

# ─── 완료 ────────────────────────────────────────────────────────────────────
echo ""
log "====================================================="
log "  업데이트 적용 완료"
log "  모드: ${MODE}"
log "  파일: ${APPLIED}개 적용, ${DELETED_COUNT}개 삭제"
if [ "$DRY_RUN" = true ]; then
    log "  *** DRY-RUN 모드였습니다 (실제 변경 없음) ***"
fi
log "  시간: $(date '+%Y-%m-%d %H:%M:%S')"
log "  로그: ${LOG_FILE}"
log "====================================================="
APPLY_EOF

    chmod +x "${output_dir}/apply_update.sh"
    log "  apply_update.sh 생성 완료"
}

# 파일 수집 (변경/신규 파일을 패키지 디렉토리로 복사)
collect_files() {
    local output_dir="$1"
    local changed_file="$2"
    local added_file="$3"
    local count=0

    mkdir -p "${output_dir}/files"

    for listfile in "$changed_file" "$added_file"; do
        [ -f "$listfile" ] || continue
        while IFS= read -r relpath; do
            [ -z "$relpath" ] && continue
            local src="${BASE_DIR}/${relpath}"
            local dst="${output_dir}/files/${relpath}"
            if [ -f "$src" ]; then
                mkdir -p "$(dirname "$dst")"
                cp -f "$src" "$dst"
                count=$((count + 1))
            fi
        done < "$listfile"
    done

    log "  ${count}개 파일 수집 완료"
}

# venv 수집
collect_venv() {
    local output_dir="$1"
    if [ -d "$VENV_DIR" ]; then
        log "  venv 수집 중 (시간이 소요됩니다)..."
        mkdir -p "${output_dir}/venv"
        # site-packages만 복사 (실행파일은 재생성 가능)
        cp -r "${VENV_DIR}/lib" "${output_dir}/venv/" 2>/dev/null || true
        cp -r "${VENV_DIR}/bin" "${output_dir}/venv/" 2>/dev/null || true
        local size
        size=$(du -sh "${output_dir}/venv" | awk '{print $1}')
        log "  venv 수집 완료: ${size}"
    else
        warn "  venv를 찾을 수 없습니다: ${VENV_DIR}"
    fi
}

# RPM 수집
collect_rpms() {
    local output_dir="$1"
    if [ -d "${BASE_DIR}/pip_file" ]; then
        mkdir -p "${output_dir}/rpms"
        find "${BASE_DIR}/pip_file" -name "*.rpm" -exec cp {} "${output_dir}/rpms/" \; 2>/dev/null || true
        local count
        count=$(find "${output_dir}/rpms" -name "*.rpm" 2>/dev/null | wc -l)
        log "  RPM ${count}개 수집"
    fi
}

# ─── 메인 ────────────────────────────────────────────────────────────────────

# 인자 파싱
MODE=""
INCLUDE_MEDIA="false"
INCLUDE_VENV="false"
INCLUDE_RPMS="false"
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        init|update|code|db|data|full)
            MODE="$1"; shift ;;
        --include-media)  INCLUDE_MEDIA="true";  shift ;;
        --include-venv)   INCLUDE_VENV="true";   shift ;;
        --include-rpms)   INCLUDE_RPMS="true";   shift ;;
        --dry-run)        DRY_RUN="true";        shift ;;
        -h|--help)        usage; exit 0 ;;
        *) err "알 수 없는 옵션: $1"; usage; exit 1 ;;
    esac
done

if [ -z "$MODE" ]; then
    usage
    exit 1
fi

echo ""
echo -e "${BOLD}====================================================${NC}"
echo -e "${BOLD}  deploy.sh - 반복 배포 패키지 생성${NC}"
echo -e "${BOLD}====================================================${NC}"
echo -e "  모드:     ${CYAN}${MODE}${NC}"
echo -e "  미디어:   ${INCLUDE_MEDIA}"
echo -e "  venv:     ${INCLUDE_VENV}"
echo -e "  RPM:      ${INCLUDE_RPMS}"
echo -e "  시간:     $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "${BOLD}====================================================${NC}"
echo ""

# .deploy_state 디렉토리 생성
mkdir -p "$DEPLOY_STATE"

# ─── init 모드 ────────────────────────────────────────────────────────────────
if [ "$MODE" = "init" ]; then
    log "초기 스냅샷 생성..."

    # 전체 추적 대상 파일 목록 생성
    FULL_LIST=$(mktemp)
    build_file_list "full" "true" > "$FULL_LIST"
    TOTAL=$(wc -l < "$FULL_LIST")
    log "  추적 대상: ${TOTAL}개 파일"

    create_snapshot "$FULL_LIST" "$SNAPSHOT_FILE"
    rm -f "$FULL_LIST"

    # 배포 이력 초기화
    if [ ! -f "$HISTORY_FILE" ]; then
        echo "[]" > "$HISTORY_FILE"
    fi

    log ""
    log "초기 스냅샷 생성 완료!"
    log "  스냅샷: ${SNAPSHOT_FILE}"
    log "  파일 수: ${TOTAL}"
    log ""
    log "이제 'deploy.sh update' 로 업데이트 패키지를 생성할 수 있습니다."
    exit 0
fi

# ─── db 모드 (스냅샷 비교 불필요) ────────────────────────────────────────────
if [ "$MODE" = "db" ]; then
    PKG_NAME="kbreg_db_$(date '+%Y%m%d_%H%M')"
    PKG_DIR="${BASE_DIR}/${PKG_NAME}"

    mkdir -p "$PKG_DIR"

    log "DB 덤프 패키지 생성..."
    dump_database "$PKG_DIR"
    collect_migrations "$PKG_DIR"

    # 빈 변경 목록으로 manifest 생성
    EMPTY_FILE=$(mktemp)
    > "$EMPTY_FILE"
    create_manifest "$PKG_DIR" "$MODE" "$EMPTY_FILE" "$EMPTY_FILE" "$EMPTY_FILE" \
        "$INCLUDE_MEDIA" "$INCLUDE_VENV" "$INCLUDE_RPMS"
    rm -f "$EMPTY_FILE"

    generate_apply_script "$PKG_DIR"

    # tar.gz 생성
    log "패키지 압축..."
    cd "${BASE_DIR}"
    tar czf "${PKG_NAME}.tar.gz" "$PKG_NAME"
    rm -rf "$PKG_DIR"

    PKG_SIZE=$(du -sh "${BASE_DIR}/${PKG_NAME}.tar.gz" | awk '{print $1}')
    echo ""
    log "====================================================="
    log "  패키지 생성 완료!"
    log "  파일: ${BASE_DIR}/${PKG_NAME}.tar.gz"
    log "  크기: ${PKG_SIZE}"
    log "====================================================="
    exit 0
fi

# ─── 스냅샷 비교 기반 모드 (code, update, data, full) ────────────────────────

# 이전 스냅샷 확인
if [ ! -f "$SNAPSHOT_FILE" ]; then
    warn "이전 스냅샷이 없습니다. 먼저 'deploy.sh init'을 실행하세요."
    warn "전체 파일을 신규로 간주하여 계속합니다..."
fi

# 현재 모드에 따른 파일 목록 생성
log "파일 목록 생성 (모드: ${MODE})..."
CURRENT_LIST=$(mktemp)
build_file_list "$MODE" "$INCLUDE_MEDIA" > "$CURRENT_LIST"
FILE_COUNT=$(wc -l < "$CURRENT_LIST")
log "  추적 대상: ${FILE_COUNT}개 파일"

# 새 스냅샷 생성
log "스냅샷 생성..."
NEW_SNAPSHOT=$(mktemp)
create_snapshot "$CURRENT_LIST" "$NEW_SNAPSHOT"
rm -f "$CURRENT_LIST"

# 스냅샷 비교 (현재 모드의 범위 내에서만)
log "변경 감지..."
CHANGED_FILE=$(mktemp)
ADDED_FILE=$(mktemp)
DELETED_FILE=$(mktemp)

# 이전 스냅샷을 현재 모드 범위로 필터링
FILTERED_OLD_SNAPSHOT=$(mktemp)
if [ -f "$SNAPSHOT_FILE" ]; then
    # 새 스냅샷의 파일 경로 목록 추출
    NEW_PATHS=$(mktemp)
    awk -F'  ' '{print $2}' "$NEW_SNAPSHOT" > "$NEW_PATHS"
    # 이전 스냅샷에서 새 스냅샷에 있는 파일 + 현재 모드 범위의 파일만 필터링
    while IFS= read -r line; do
        _path="${line#*  }"
        _in_scope=false
        # 새 스냅샷에도 있는 파일이면 포함
        if grep -qFx "$_path" "$NEW_PATHS" 2>/dev/null; then
            _in_scope=true
        else
            # 현재 모드의 추적 범위에 해당하는 파일인지 확인 (삭제 감지)
            case "$MODE" in
                code)
                    if is_source_file "$_path"; then
                        for _dir in "${SOURCE_DIRS[@]}"; do
                            case "$_path" in ${_dir}/*) _in_scope=true; break ;; esac
                        done
                        case "$_path" in */*) ;; *) is_source_file "$_path" && _in_scope=true ;; esac
                    fi
                    ;;
                data)
                    for _dir in "${DATA_DIRS[@]}"; do
                        case "$_path" in ${_dir}/*) _in_scope=true; break ;; esac
                    done
                    ;;
                update)
                    if is_source_file "$_path"; then
                        for _dir in "${SOURCE_DIRS[@]}"; do
                            case "$_path" in ${_dir}/*) _in_scope=true; break ;; esac
                        done
                        case "$_path" in */*) ;; *) is_source_file "$_path" && _in_scope=true ;; esac
                    fi
                    for _dir in "${DATA_DIRS[@]}"; do
                        case "$_path" in ${_dir}/*) _in_scope=true; break ;; esac
                    done
                    ;;
                full)
                    _in_scope=true
                    ;;
            esac
        fi
        [ "$_in_scope" = true ] && echo "$line"
    done < "$SNAPSHOT_FILE" > "$FILTERED_OLD_SNAPSHOT"
    rm -f "$NEW_PATHS"
else
    > "$FILTERED_OLD_SNAPSHOT"
fi

diff_snapshots "$FILTERED_OLD_SNAPSHOT" "$NEW_SNAPSHOT" "$CHANGED_FILE" "$ADDED_FILE" "$DELETED_FILE"
rm -f "$FILTERED_OLD_SNAPSHOT"

CHANGED_COUNT=$(wc -l < "$CHANGED_FILE")
ADDED_COUNT=$(wc -l < "$ADDED_FILE")
DELETED_COUNT=$(wc -l < "$DELETED_FILE")
TOTAL_CHANGES=$((CHANGED_COUNT + ADDED_COUNT + DELETED_COUNT))

log "  변경: ${CHANGED_COUNT}개"
log "  신규: ${ADDED_COUNT}개"
log "  삭제: ${DELETED_COUNT}개"

if [ "$TOTAL_CHANGES" -eq 0 ] && [ "$MODE" != "full" ]; then
    log ""
    log "변경된 파일이 없습니다. 패키지를 생성하지 않습니다."
    rm -f "$NEW_SNAPSHOT" "$CHANGED_FILE" "$ADDED_FILE" "$DELETED_FILE"
    exit 0
fi

# dry-run 모드
if [ "$DRY_RUN" = "true" ]; then
    echo ""
    echo -e "${BOLD}─── 변경된 파일 ───${NC}"
    [ -s "$CHANGED_FILE" ] && while IFS= read -r f; do echo -e "  ${YELLOW}M${NC} $f"; done < "$CHANGED_FILE"
    [ -s "$ADDED_FILE" ] && while IFS= read -r f; do echo -e "  ${GREEN}A${NC} $f"; done < "$ADDED_FILE"
    [ -s "$DELETED_FILE" ] && while IFS= read -r f; do echo -e "  ${RED}D${NC} $f"; done < "$DELETED_FILE"
    echo ""

    # ES 전략 출력
    ES_INFO=$(determine_reindex_strategy "$CHANGED_FILE" "$ADDED_FILE" "$DELETED_FILE")
    IFS='|' read -r rm rt ra jc pc <<< "$ES_INFO"
    log "ES 재색인 전략: ${rm}"
    [ -n "$rt" ] && log "  대상 rule_seq: ${rt}"

    rm -f "$NEW_SNAPSHOT" "$CHANGED_FILE" "$ADDED_FILE" "$DELETED_FILE"
    exit 0
fi

# ─── 패키지 생성 ─────────────────────────────────────────────────────────────
PKG_NAME="kbreg_${MODE}_$(date '+%Y%m%d_%H%M')"
PKG_DIR="${BASE_DIR}/${PKG_NAME}"

mkdir -p "$PKG_DIR"

# 파일 수집
log "파일 수집..."
collect_files "$PKG_DIR" "$CHANGED_FILE" "$ADDED_FILE"

# DB 덤프 (update, full 모드)
if [ "$MODE" = "update" ] || [ "$MODE" = "full" ]; then
    dump_database "$PKG_DIR" || true
    collect_migrations "$PKG_DIR"
fi

# venv 수집
if [ "$INCLUDE_VENV" = "true" ]; then
    collect_venv "$PKG_DIR"
fi

# RPM 수집
if [ "$INCLUDE_RPMS" = "true" ]; then
    collect_rpms "$PKG_DIR"
fi

# manifest.json 생성
log "manifest.json 생성..."
create_manifest "$PKG_DIR" "$MODE" "$CHANGED_FILE" "$ADDED_FILE" "$DELETED_FILE" \
    "$INCLUDE_MEDIA" "$INCLUDE_VENV" "$INCLUDE_RPMS"

# apply_update.sh 생성
log "apply_update.sh 생성..."
generate_apply_script "$PKG_DIR"

# tar.gz 패키징
log "패키지 압축..."
cd "${BASE_DIR}"
tar czf "${PKG_NAME}.tar.gz" "$PKG_NAME"
rm -rf "$PKG_DIR"

PKG_SIZE=$(du -sh "${BASE_DIR}/${PKG_NAME}.tar.gz" | awk '{print $1}')

# 스냅샷 업데이트
log "스냅샷 업데이트..."
cp -f "$NEW_SNAPSHOT" "$SNAPSHOT_FILE"

# 배포 이력 기록
DEPLOY_ENTRY=$(cat << ENTRY_EOF
{
    "timestamp": "$(date -Iseconds)",
    "mode": "${MODE}",
    "package": "${PKG_NAME}.tar.gz",
    "size": "${PKG_SIZE}",
    "changed": ${CHANGED_COUNT},
    "added": ${ADDED_COUNT},
    "deleted": ${DELETED_COUNT}
}
ENTRY_EOF
)

if [ -f "$HISTORY_FILE" ]; then
    python3 -c "
import json
with open('${HISTORY_FILE}') as f:
    history = json.load(f)
history.append(json.loads('''${DEPLOY_ENTRY}'''))
history = history[-50:]
with open('${HISTORY_FILE}', 'w') as f:
    json.dump(history, f, indent=2, ensure_ascii=False)
" 2>/dev/null || true
else
    echo "[$DEPLOY_ENTRY]" > "$HISTORY_FILE"
fi

# 정리
rm -f "$NEW_SNAPSHOT" "$CHANGED_FILE" "$ADDED_FILE" "$DELETED_FILE"

# ─── 완료 ────────────────────────────────────────────────────────────────────
echo ""
log "====================================================="
log "  패키지 생성 완료!"
log "====================================================="
log ""
log "  파일:   ${BASE_DIR}/${PKG_NAME}.tar.gz"
log "  크기:   ${PKG_SIZE}"
log "  변경:   ${CHANGED_COUNT}개 수정, ${ADDED_COUNT}개 신규, ${DELETED_COUNT}개 삭제"
log ""
log "  운영 서버 적용 방법:"
log "    1. USB로 ${PKG_NAME}.tar.gz 복사"
log "    2. tar xzf ${PKG_NAME}.tar.gz"
log "    3. cd ${PKG_NAME}"
log "    4. sudo ./apply_update.sh              # 적용"
log "    5. sudo ./apply_update.sh --dry-run    # 시뮬레이션"
log ""
log "====================================================="
