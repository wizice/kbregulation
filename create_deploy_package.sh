#!/bin/bash

# 배포 패키지 생성 스크립트
# Git 변경 이력을 확인하여 변경된 파일들을 tgz로 패키징

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 설정
BACKUP_DIR="/home/wizice/backup_src"
DEPLOY_LOG="${BACKUP_DIR}/.deploy"
REPO_ROOT=$(git rev-parse --show-toplevel)

# 함수: 배너 출력
print_banner() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}  배포 패키지 생성 스크립트${NC}"
    echo -e "${BLUE}================================================${NC}"
}

# 함수: 에러 메시지 출력
error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
    exit 1
}

# 함수: 정보 메시지 출력
info() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

# 함수: 경고 메시지 출력
warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

# 함수: 배포 기록 디렉토리 초기화
init_deploy_log() {
    mkdir -p "${BACKUP_DIR}"
    if [ ! -f "${DEPLOY_LOG}" ]; then
        info "배포 기록 파일 생성: ${DEPLOY_LOG}"
        echo "# 배포 기록" > "${DEPLOY_LOG}"
        echo "# 형식: [날짜시간] [커밋해시] [커밋메시지]" >> "${DEPLOY_LOG}"
    fi
}

# 함수: 이전 배포 기록 표시
show_deploy_history() {
    if [ ! -s "${DEPLOY_LOG}" ] || [ $(grep -v '^#' "${DEPLOY_LOG}" | wc -l) -eq 0 ]; then
        warn "배포 기록이 없습니다."
        return 1
    fi

    echo ""
    echo -e "${BLUE}=== 배포 기록 ===${NC}"
    local idx=1
    while IFS= read -r line; do
        if [[ ! "$line" =~ ^# ]]; then
            echo -e "${GREEN}${idx}.${NC} ${line}"
            ((idx++))
        fi
    done < "${DEPLOY_LOG}"
    echo ""
    return 0
}

# 함수: 배포 제외 파일 필터링
filter_excluded_files() {
    # 제외 패턴:
    # - docs/ 폴더
    # - *.md 파일 (마크다운 문서만)
    # - .env* 파일 (환경 설정 - 민감 정보)
    # - __pycache__/ 폴더 (Python 캐시)
    # - *.pyc 파일 (Python 바이트코드)
    # - *.log 파일 (로그 파일)
    # - logs/ 폴더 (로그 디렉토리)
    # - *.db, *.sqlite 파일 (로컬 DB)
    # - .vscode/, .idea/ 폴더 (IDE 설정)
    # - venv/, .venv/ 폴더 (가상환경)
    # - node_modules/ 폴더 (Node.js 패키지)
    # - .git/ 폴더 (Git 저장소)
    # - *.tmp, *.cache 파일 (임시/캐시 파일)
    #
    # 포함: .txt, .pdf, .docx, .doc, .hwp, .hwpx, .xlsx, .xls 등은 배포에 포함
    grep -v -E '(^docs/|\.md$|\.env|__pycache__|\.pyc$|\.log$|/logs/|^logs/|\.db$|\.sqlite$|\.vscode/|\.idea/|/venv/|/\.venv/|node_modules/|\.git/|\.tmp$|\.cache$)' || true
}

# 함수: 특정 커밋 이후 변경된 파일 목록 가져오기
get_changed_files() {
    local from_commit=$1
    local to_commit=${2:-HEAD}

    if [ -z "$from_commit" ]; then
        # 첫 배포: 모든 추적된 파일 포함 (docs 폴더 및 .md 파일 제외)
        git -c core.quotePath=false ls-files | filter_excluded_files
    else
        # 특정 커밋 이후 변경/추가/수정된 파일 (docs 폴더 및 .md 파일 제외)
        # --name-only: 파일명만, --diff-filter=ACMR: Added, Copied, Modified, Renamed
        git -c core.quotePath=false diff --name-only --diff-filter=ACMR "${from_commit}..${to_commit}" | filter_excluded_files
    fi
}

# 함수: 특정 날짜 이후 변경된 파일 목록 가져오기 (중복 제거)
get_changed_files_by_date() {
    local since_date=$1

    info "날짜 ${since_date} 이후 변경된 파일 검색 중..."

    # 해당 날짜 이후의 모든 커밋에서 변경된 파일을 중복 없이 가져오기
    # --since: 지정한 날짜 이후
    # --name-only: 파일명만
    # --pretty=format:: 커밋 메시지는 제외
    # --diff-filter=ACMR: Added, Copied, Modified, Renamed 파일만
    # sort -u: 정렬 후 중복 제거
    # grep -v '^$': 빈 줄 제거
    # filter_excluded_files: docs 폴더 및 .md 파일 제외
    git -c core.quotePath=false log --since="$since_date" --name-only --pretty=format: --diff-filter=ACMR | \
        sort -u | \
        { grep -v '^$' || true; } | \
        filter_excluded_files
}

# 함수: 날짜 형식 검증
validate_date() {
    local date_input=$1

    # date 명령어로 날짜 형식 검증
    if date -d "$date_input" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 함수: 백업 디렉토리 초기화
clean_backup_dir() {
    info "이전 백업 파일 삭제 중..."
    if [ -d "${BACKUP_DIR}" ]; then
        # .deploy 파일은 보존
        find "${BACKUP_DIR}" -mindepth 1 ! -name '.deploy' -delete
    else
        mkdir -p "${BACKUP_DIR}"
    fi
}

# 함수: 파일 복사 (폴더 구조 유지)
copy_files() {
    local file_list=("$@")
    local copied_count=0
    local failed_count=0
    local total_count=${#file_list[@]}

    info "총 ${total_count}개 파일 복사 중..."
    echo "[DEBUG] 배열 크기: ${#file_list[@]}" >&2
    echo "[DEBUG] 첫 파일: ${file_list[0]}" >&2
    echo "[DEBUG] 마지막 파일: ${file_list[-1]}" >&2
    echo "[DEBUG] REPO_ROOT: ${REPO_ROOT}" >&2
    echo "[DEBUG] BACKUP_DIR: ${BACKUP_DIR}" >&2

    local start_time=$(date +%s)
    for file in "${file_list[@]}"; do
        if [ $((copied_count + failed_count)) -eq 0 ]; then
            echo "[DEBUG] 첫 루프 시작: $file" >&2
        fi

        if [ -f "${REPO_ROOT}/${file}" ]; then
            # 대상 디렉토리 생성
            local target_dir="${BACKUP_DIR}/$(dirname "${file}")"
            if mkdir -p "${target_dir}" 2>/dev/null; then
                # 파일 복사
                if cp "${REPO_ROOT}/${file}" "${BACKUP_DIR}/${file}" 2>/dev/null; then
                    copied_count=$((copied_count + 1))

                    if [ $((copied_count % 100)) -eq 0 ]; then
                        echo -ne "\r진행: ${copied_count}/${total_count} 파일"
                    fi
                else
                    failed_count=$((failed_count + 1))
                    # 상세한 에러는 로그로만 기록
                fi
            else
                failed_count=$((failed_count + 1))
            fi
        else
            # 파일이 존재하지 않는 경우는 경고만 출력
            failed_count=$((failed_count + 1))
        fi

        if [ $((copied_count + failed_count)) -eq 1 ]; then
            echo "[DEBUG] 첫 루프 완료" >&2
        fi
    done

    echo -ne "\r${GREEN}완료: ${copied_count}/${total_count} 파일 복사됨${NC}"
    if [ $failed_count -gt 0 ]; then
        echo -e " ${YELLOW}(실패: ${failed_count}개)${NC}"
    else
        echo ""
    fi
}

# 함수: tgz 패키지 생성
create_package() {
    local package_name=$1
    local package_path="${REPO_ROOT}/${package_name}"

    info "압축 파일 생성 중: ${package_name}"

    # backup_src 디렉토리로 이동하여 상대 경로로 압축
    cd "${BACKUP_DIR}/.."

    # .deploy 파일 포함하여 압축
    tar -czf "${package_path}" -C "$(basename ${BACKUP_DIR})" .

    cd "${REPO_ROOT}"

    if [ -f "${package_path}" ]; then
        local size=$(du -h "${package_path}" | cut -f1)
        info "패키지 생성 완료: ${package_path} (${size})"
        return 0
    else
        error "패키지 생성 실패"
        return 1
    fi
}

# 함수: 배포 기록 저장
save_deploy_record() {
    local commit_hash=$1
    local date_filter=$2
    local commit_msg=$(git log -1 --pretty=format:"%s" "${commit_hash}")
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    if [ -n "$date_filter" ]; then
        echo "[${timestamp}] ${commit_hash} ${commit_msg} (날짜기준: ${date_filter})" >> "${DEPLOY_LOG}"
    else
        echo "[${timestamp}] ${commit_hash} ${commit_msg}" >> "${DEPLOY_LOG}"
    fi
    info "배포 기록 저장 완료"
}

# 함수: 파일 목록 표시
show_file_list() {
    local file_list=("$@")
    local count=${#file_list[@]}

    echo ""
    echo -e "${BLUE}=== 변경된 파일 목록 (총 ${count}개) ===${NC}"

    if [ $count -le 20 ]; then
        # 20개 이하면 전체 표시
        for file in "${file_list[@]}"; do
            echo "  - ${file}"
        done
    else
        # 20개 초과시 처음 10개와 마지막 10개만 표시
        for i in {0..9}; do
            echo "  - ${file_list[$i]}"
        done
        echo "  ... ($(($count - 20))개 생략) ..."
        for i in $(seq $(($count - 10)) $(($count - 1))); do
            echo "  - ${file_list[$i]}"
        done
    fi
    echo ""
}

# 메인 로직
main() {
    print_banner

    # Git 저장소 확인
    if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
        error "Git 저장소가 아닙니다."
    fi

    # 배포 기록 초기화
    init_deploy_log

    # 배포 기록 표시
    local from_commit=""
    local use_date_filter=false
    local since_date=""

    if show_deploy_history; then
        echo -n "기준 커밋 선택 (번호 입력, Enter=전체 배포): "
        read selection

        if [ -n "$selection" ]; then
            # 선택한 번호에 해당하는 커밋 해시 추출
            from_commit=$(grep -v '^#' "${DEPLOY_LOG}" | sed -n "${selection}p" | awk '{print $2}')

            if [ -z "$from_commit" ]; then
                error "잘못된 선택입니다."
            fi

            info "기준 커밋: ${from_commit}"
        else
            info "전체 파일을 패키징합니다."
        fi
    else
        # 배포 기록이 없는 경우: 날짜 입력 옵션 제공
        echo ""
        echo -e "${YELLOW}배포 기록이 없습니다. 다음 중 선택하세요:${NC}"
        echo "  1. 전체 파일 패키징"
        echo "  2. 특정 날짜 이후 변경된 파일만 패키징"
        echo -n "선택 (1 또는 2, Enter=1): "
        read option

        if [ "$option" = "2" ]; then
            use_date_filter=true

            # 날짜 입력 받기
            while true; do
                echo ""
                echo "날짜 형식 예시:"
                echo "  - 2025-01-15"
                echo "  - 2025-01-15 14:30:00"
                echo "  - '7 days ago'"
                echo "  - '2 weeks ago'"
                echo "  - 'yesterday'"
                echo ""
                echo -n "기준 날짜 입력: "
                read since_date

                if [ -z "$since_date" ]; then
                    warn "날짜를 입력해주세요."
                    continue
                fi

                # 날짜 형식 검증
                if validate_date "$since_date"; then
                    info "기준 날짜: ${since_date}"
                    break
                else
                    warn "올바르지 않은 날짜 형식입니다. 다시 입력해주세요."
                fi
            done
        else
            info "전체 파일을 패키징합니다."
        fi
    fi

    # 현재 커밋 정보
    local current_commit=$(git rev-parse HEAD)
    info "현재 커밋: ${current_commit}"

    # 변경된 파일 목록 가져오기
    info "변경된 파일 목록 수집 중..."
    if [ "$use_date_filter" = true ]; then
        # 날짜 기반 파일 목록
        mapfile -t changed_files < <(get_changed_files_by_date "$since_date")
    else
        # 커밋 기반 파일 목록
        mapfile -t changed_files < <(get_changed_files "$from_commit" "$current_commit")
    fi

    if [ ${#changed_files[@]} -eq 0 ]; then
        warn "변경된 파일이 없습니다."
        exit 0
    fi

    # 파일 목록 표시
    show_file_list "${changed_files[@]}"

    # 사용자 확인
    echo -n "계속 진행하시겠습니까? (y/N): "
    read confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        info "취소되었습니다."
        exit 0
    fi

    # 백업 디렉토리 초기화
    clean_backup_dir

    # 파일 복사
    copy_files "${changed_files[@]}"

    # 패키지 이름 생성
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local package_name="deploy_${timestamp}.tgz"

    # tgz 패키지 생성
    create_package "${package_name}"

    # 배포 기록 저장 (날짜 필터 정보 포함)
    if [ "$use_date_filter" = true ]; then
        save_deploy_record "${current_commit}" "${since_date}"
    else
        save_deploy_record "${current_commit}"
    fi

    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  배포 패키지 생성 완료!${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo -e "패키지: ${BLUE}${package_name}${NC}"
    echo -e "파일 수: ${BLUE}${#changed_files[@]}${NC}"
    echo ""
    echo "내부망 서버 배포 방법:"
    echo "  1. ${package_name} 파일을 서버로 전송"
    echo "  2. 서버에서 압축 해제: tar -xzf ${package_name}"
    echo ""
}

# 스크립트 실행
main
