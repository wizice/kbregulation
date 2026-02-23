"""
파일 경로 관리 유틸리티

BASE_DIR 기반 상대경로 <-> 절대경로 변환 및 백업 파일 관리
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from settings import settings


def get_absolute_path(relative_path: str) -> str:
    """
    상대경로를 절대경로로 변환

    Args:
        relative_path: BASE_DIR 기준 상대경로 (예: "fastapi/applib/pdf/file.pdf")

    Returns:
        절대경로 (예: "/home/wizice/regulation/fastapi/applib/pdf/file.pdf")
    """
    if not relative_path:
        return ""

    # 이미 절대경로인 경우 그대로 반환
    if os.path.isabs(relative_path):
        return relative_path

    return os.path.join(settings.BASE_DIR, relative_path)


def get_relative_path(absolute_path: str) -> str:
    """
    절대경로를 상대경로로 변환

    Args:
        absolute_path: 절대경로 (예: "/home/wizice/regulation/fastapi/applib/pdf/file.pdf")

    Returns:
        상대경로 (예: "fastapi/applib/pdf/file.pdf")
    """
    if not absolute_path:
        return ""

    # 이미 상대경로인 경우 그대로 반환
    if not os.path.isabs(absolute_path):
        return absolute_path

    return os.path.relpath(absolute_path, settings.BASE_DIR)


def get_applib_path(filename: str, subfolder: str = "") -> Tuple[str, str]:
    """
    applib 폴더 내 파일의 절대경로와 상대경로 반환

    Args:
        filename: 파일명
        subfolder: 하위 폴더 (예: "pdf", "docx", "txt_json")

    Returns:
        (절대경로, 상대경로) 튜플
    """
    if subfolder:
        relative = os.path.join(settings.APPLIB_RELATIVE_PATH, subfolder, filename)
    else:
        relative = os.path.join(settings.APPLIB_RELATIVE_PATH, filename)

    absolute = get_absolute_path(relative)
    return absolute, relative


def get_json_service_path(filename: str) -> Tuple[str, str]:
    """
    JSON 서비스 폴더 내 파일의 절대경로와 상대경로 반환

    Args:
        filename: 파일명

    Returns:
        (절대경로, 상대경로) 튜플
    """
    relative = os.path.join(settings.JSON_SERVICE_RELATIVE_PATH, filename)
    absolute = get_absolute_path(relative)
    return absolute, relative


def get_backup_path(original_relative_path: str, wzruleid: int, file_type: str) -> Tuple[str, str]:
    """
    백업 파일 경로 생성 (wzruleid별 폴더 구조)

    Args:
        original_relative_path: 원본 파일의 상대경로
        wzruleid: 규정 ID
        file_type: 파일 타입 ("pdf", "docx", "json")

    Returns:
        (백업 절대경로, 백업 상대경로) 튜플
    """
    filename = os.path.basename(original_relative_path)
    base_name, ext = os.path.splitext(filename)

    # 백업 파일명에 _backup 추가
    backup_filename = f"{base_name}_backup{ext}"

    # JSON 파일인 경우 www/static/file/file_old 사용
    if file_type == "json":
        backup_relative = os.path.join(
            settings.JSON_SERVICE_RELATIVE_PATH,
            settings.JSON_BACKUP_FOLDER,
            str(wzruleid),
            backup_filename
        )
    else:
        # PDF/DOCX는 fastapi/applib/_old 사용
        backup_relative = os.path.join(
            settings.APPLIB_RELATIVE_PATH,
            settings.FILE_BACKUP_FOLDER,
            str(wzruleid),
            file_type,
            backup_filename
        )

    backup_absolute = get_absolute_path(backup_relative)
    return backup_absolute, backup_relative


def move_to_backup(
    source_path: str,
    wzruleid: int,
    file_type: str,
    is_relative_path: bool = False
) -> Optional[str]:
    """
    파일을 백업 폴더로 이동 (레거시 함수 - 기존 호환용)
    새로운 개정 처리는 move_file_to_old 사용 권장
    """
    if not settings.FILE_BACKUP_ENABLED:
        return None

    # 절대경로 확보
    if is_relative_path:
        source_absolute = get_absolute_path(source_path)
        source_relative = source_path
    else:
        source_absolute = source_path
        source_relative = get_relative_path(source_path)

    # 원본 파일이 존재하지 않으면 스킵
    if not os.path.exists(source_absolute):
        return None

    try:
        # 백업 경로 생성
        backup_absolute, backup_relative = get_backup_path(source_relative, wzruleid, file_type)

        # 백업 폴더 생성
        backup_dir = os.path.dirname(backup_absolute)
        os.makedirs(backup_dir, exist_ok=True)

        # 파일 복사 (권한 유지)
        shutil.copy2(source_absolute, backup_absolute)

        return backup_relative

    except Exception as e:
        print(f"Backup failed for {source_path}: {e}")
        return None


# === 새로운 파일 이동 함수 (개정 처리용) ===

APPLIB_DIR = Path(settings.APPLIB_DIR)

import re

def extract_revision_date_from_filename(filename: str) -> Optional[str]:
    """
    파일명에서 개정일 추출

    파일명 형식: {wzruleid}_{분류번호}. {규정명}_{개정일}_{타임스탬프}.{ext}
    예: 7421_11.5.1. 의료기기 관리_202509개정_20251013_161717.pdf
    또는: 7421_11.5.1. 의료기기 관리_20250909개정_20251013_161717.pdf

    Returns:
        개정일 문자열 (예: "202509" 또는 "20250909") 또는 None
    """
    # 패턴: _숫자6~8자리개정_ (예: _202503개정_, _20250909개정_)
    match = re.search(r'_(\d{6,8})개정_', filename)
    if match:
        return match.group(1)
    return None


def normalize_revision_date(date_str: str) -> str:
    """
    DB의 개정일(YYYY-MM-DD)을 파일명 형식으로 변환

    Args:
        date_str: DB 개정일 (예: "2025-09-09" 또는 "2025-03-15")

    Returns:
        파일명 형식 (예: "202509" 또는 "20250909")
    """
    if not date_str:
        return ""

    # YYYY-MM-DD 형식에서 숫자만 추출
    clean = date_str.replace('-', '').replace('.', '')[:8]  # YYYYMMDD

    # 파일명에서 사용되는 두 가지 형식 반환 (6자리, 8자리)
    return clean


def find_current_file(wzruleseq: int, wzruleid: int, file_type: str, revision_date: str = '') -> Optional[Path]:
    """
    현행 파일 찾기 (applib 폴더 기준) - 개정일과 매칭되는 파일 반환

    파일명 형식:
    - PDF/DOCX: {wzruleid}_{분류번호}. {규정명}_{개정일}_{타임스탬프}.{ext}

    Args:
        wzruleseq: 규정 시퀀스 ID
        wzruleid: 규정 ID
        file_type: 파일 타입 ("pdf", "docx", "json")
        revision_date: DB의 개정일 (예: "2025-09-09") - 이 날짜와 매칭되는 파일을 찾음

    Returns:
        파일 경로 (Path) 또는 None
    """
    if file_type == "json":
        # JSON은 이동하지 않음 (사용자 요청)
        return None

    # 폴더 결정
    if file_type == "pdf":
        target_dir = APPLIB_DIR / "pdf"
    elif file_type == "docx":
        target_dir = APPLIB_DIR / "docx"
    else:
        return None

    if not target_dir.exists():
        return None

    # wzruleid로 파일 검색
    files = list(target_dir.glob(f"{wzruleid}_*.{file_type}"))
    if not files:
        return None

    # 개정일이 있으면 매칭되는 파일 찾기
    if revision_date:
        normalized_date = normalize_revision_date(revision_date)
        # YYYYMMDD (8자리)와 YYYYMM (6자리) 둘 다 시도
        date_patterns = [normalized_date, normalized_date[:6]]

        matching_files = []
        for f in files:
            file_rev_date = extract_revision_date_from_filename(f.name)
            if file_rev_date:
                # 파일의 개정일이 DB 개정일과 매칭되는지 확인
                for pattern in date_patterns:
                    if file_rev_date.startswith(pattern) or pattern.startswith(file_rev_date):
                        matching_files.append(f)
                        break

        if matching_files:
            # 매칭되는 파일 중 가장 최신 업로드된 것 선택 (타임스탬프 기준)
            return max(matching_files, key=lambda f: f.stat().st_mtime)

    # 개정일로 못 찾으면 가장 오래된 파일 반환 (fallback)
    return min(files, key=lambda f: f.stat().st_mtime)


def move_file_to_old(wzruleseq: int, wzruleid: int, file_type: str, revision_date: str = '') -> Optional[str]:
    """
    현행 파일을 _old 폴더로 이동

    Args:
        wzruleseq: 규정 시퀀스 ID
        wzruleid: 규정 ID (같은 규정의 모든 버전이 공유)
        file_type: 파일 타입 ("pdf", "docx", "json")
        revision_date: DB의 개정일 (예: "2025-09-09") - 이 날짜의 파일을 이동

    Returns:
        새 파일의 상대경로 (예: "applib/pdf_old/7421_342.pdf") 또는 None
    """
    # 원본 파일 찾기 (개정일 기준)
    source_file = find_current_file(wzruleseq, wzruleid, file_type, revision_date)
    if not source_file:
        print(f"[move_file_to_old] No file found for wzruleid={wzruleid}, type={file_type}, date={revision_date}")
        return None

    # 대상 폴더 결정
    if file_type == "json":
        target_dir = APPLIB_DIR / "merge_json_old"
    elif file_type == "pdf":
        target_dir = APPLIB_DIR / "pdf_old"
    elif file_type == "docx":
        target_dir = APPLIB_DIR / "docx_old"
    else:
        return None

    # 폴더 생성
    target_dir.mkdir(exist_ok=True)

    # 새 파일명: {wzruleid}_{wzruleseq}.{ext}
    new_filename = f"{wzruleid}_{wzruleseq}.{file_type}"
    target_path = target_dir / new_filename

    try:
        print(f"[move_file_to_old] Moving {source_file} -> {target_path}")
        # 파일 이동 (복사 후 삭제가 아닌 실제 이동)
        shutil.move(str(source_file), str(target_path))

        # 상대경로 반환 (applib 기준)
        relative_path = f"applib/{target_dir.name}/{new_filename}"
        return relative_path
    except Exception as e:
        print(f"[move_file_to_old] Error moving {source_file} to {target_path}: {e}")
        return None


def ensure_directory(path: str, is_relative: bool = False) -> str:
    """
    디렉토리 존재 확인 및 생성

    Args:
        path: 디렉토리 경로
        is_relative: 상대경로 여부

    Returns:
        절대경로
    """
    if is_relative:
        abs_path = get_absolute_path(path)
    else:
        abs_path = path

    os.makedirs(abs_path, exist_ok=True)
    return abs_path


def file_exists(path: str, is_relative: bool = False) -> bool:
    """
    파일 존재 여부 확인

    Args:
        path: 파일 경로
        is_relative: 상대경로 여부

    Returns:
        존재 여부
    """
    if is_relative:
        abs_path = get_absolute_path(path)
    else:
        abs_path = path

    return os.path.exists(abs_path) and os.path.isfile(abs_path)
