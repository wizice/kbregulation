# -*- coding: utf-8 -*-
"""
    service_regulation.py
    ~~~~~~~~~~~~~~~~~~~~

    규정 관리 API (현행/연혁 구분)

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, Optional, List
import logging
import shutil
from pathlib import Path
from .auth_middleware import get_current_user
from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings
from app_logger import get_logger
from datetime import datetime
import threading

# 파일 경로 설정
APPLIB_DIR = Path(settings.APPLIB_DIR)
DOCX_DIR = APPLIB_DIR / "docx"
PDF_DIR = APPLIB_DIR / "pdf"
JSON_DIR = APPLIB_DIR / "merge_json"
DOCX_OLD_DIR = APPLIB_DIR / "docx_old"
PDF_OLD_DIR = APPLIB_DIR / "pdf_old"
JSON_OLD_DIR = APPLIB_DIR / "merge_json_old"

# 폴더 생성 확인
DOCX_OLD_DIR.mkdir(exist_ok=True)
PDF_OLD_DIR.mkdir(exist_ok=True)
JSON_OLD_DIR.mkdir(exist_ok=True)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/regulations",
    tags=["regulations"],
    responses={404: {"description": "Not found"}},
)

def get_db_connection():
    """데이터베이스 연결 생성"""
    db_config = {
        'database': settings.DB_NAME,
        'user': settings.DB_USER,
        'password': settings.DB_PASSWORD,
        'host': settings.DB_HOST,
        'port': settings.DB_PORT
    }
    return DatabaseConnectionManager(**db_config)

@router.get("/current")
async def get_current_regulations(
    search: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    limit: int = Query(1000),
    offset: int = Query(0)
):
    """현행 규정 목록 조회"""
    try:
        db_manager = get_db_connection()

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 기본 쿼리
                query = """
                    SELECT
                        wzruleseq,
                        wzname,
                        wzpubno,
                        wzestabdate,
                        wzlastrevdate,
                        wzmgrdptnm,
                        wzedittype,
                        wzexecdate,
                        wzlkndname,
                        wzcontent_path,
                        wzNewFlag
                    FROM wz_rule
                    WHERE wzNewFlag = '현행'
                """

                params = []

                # 검색 조건 추가
                if search:
                    query += " AND (wzname ILIKE %s OR wzpubno ILIKE %s)"
                    search_pattern = f'%{search}%'
                    params.extend([search_pattern, search_pattern])

                # 분류 필터
                if classification:
                    query += " AND wzcateseq = %s"
                    params.append(int(classification))

                # 부서 필터
                if department:
                    query += " AND wzmgrdptnm = %s"
                    params.append(department)

                # 자연스러운 숫자 정렬 적용 (하이픈 기반)
                query += """ ORDER BY
                    wzcateseq,
                    CASE WHEN split_part(wzpubno, '-', 1) ~ '^\d+$'
                         THEN CAST(split_part(wzpubno, '-', 1) AS INTEGER) ELSE 9999 END,
                    CASE WHEN split_part(wzpubno, '-', 2) ~ '^\d+$'
                         THEN CAST(split_part(wzpubno, '-', 2) AS INTEGER) ELSE 9999 END,
                    wzruleseq
                """
                query += f" LIMIT {limit} OFFSET {offset}"

                cur.execute(query, params)
                results = cur.fetchall()

                regulations = []
                for row in results:
                    regulations.append({
                        "rule_id": row[0],
                        "name": row[1],
                        "publication_no": row[2],
                        "established_date": row[3],
                        "last_revised_date": row[4],
                        "department": row[5],
                        "edit_type": row[6],
                        "execution_date": row[7],
                        "large_category": row[8],
                        "content_path": row[9],
                        "status": row[10]
                    })

                # 전체 개수 조회
                count_query = """
                    SELECT COUNT(*) FROM wz_rule
                    WHERE wzNewFlag = '현행'
                """
                if search or classification or department:
                    count_params = []
                    count_query = "SELECT COUNT(*) FROM wz_rule WHERE wzNewFlag = '현행'"

                    if search:
                        count_query += " AND (wzname ILIKE %s OR wzpubno ILIKE %s)"
                        count_params.extend([search_pattern, search_pattern])
                    if classification:
                        count_query += " AND wzcateseq = %s"
                        count_params.append(int(classification))
                    if department:
                        count_query += " AND wzmgrdptnm = %s"
                        count_params.append(department)

                    cur.execute(count_query, count_params)
                else:
                    cur.execute(count_query)

                total_count = cur.fetchone()[0]

                return {
                    "success": True,
                    "data": regulations,
                    "total": total_count,
                    "limit": limit,
                    "offset": offset
                }

    except Exception as e:
        logger.error(f"Error getting current regulations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_history_regulations(
    search: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    limit: int = Query(1000),
    offset: int = Query(0)
):
    """연혁 규정 목록 조회"""
    try:
        db_manager = get_db_connection()

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 기본 쿼리
                query = """
                    SELECT
                        wzruleseq,
                        wzname,
                        wzpubno,
                        wzestabdate,
                        wzlastrevdate,
                        wzmgrdptnm,
                        wzedittype,
                        wzexecdate,
                        wzlkndname,
                        wzcontent_path,
                        wzNewFlag
                    FROM wz_rule
                    WHERE wzNewFlag = '연혁'
                """

                params = []

                # 검색 조건 추가
                if search:
                    query += " AND (wzname ILIKE %s OR wzpubno ILIKE %s)"
                    search_pattern = f'%{search}%'
                    params.extend([search_pattern, search_pattern])

                # 분류 필터
                if classification:
                    query += " AND wzcateseq = %s"
                    params.append(int(classification))

                # 부서 필터
                if department:
                    query += " AND wzmgrdptnm = %s"
                    params.append(department)

                query += " ORDER BY wzpubno, wzlastrevdate DESC"
                query += f" LIMIT {limit} OFFSET {offset}"

                cur.execute(query, params)
                results = cur.fetchall()

                regulations = []
                for row in results:
                    regulations.append({
                        "rule_id": row[0],
                        "name": row[1],
                        "publication_no": row[2],
                        "established_date": row[3],
                        "last_revised_date": row[4],
                        "department": row[5],
                        "edit_type": row[6],
                        "execution_date": row[7],
                        "large_category": row[8],
                        "content_path": row[9],
                        "status": row[10]
                    })

                # 전체 개수 조회
                count_query = """
                    SELECT COUNT(*) FROM wz_rule
                    WHERE wzNewFlag = '연혁'
                """
                if search or classification or department:
                    count_params = []
                    count_query = "SELECT COUNT(*) FROM wz_rule WHERE wzNewFlag = '연혁'"

                    if search:
                        count_query += " AND (wzname ILIKE %s OR wzpubno ILIKE %s)"
                        count_params.extend([search_pattern, search_pattern])
                    if classification:
                        count_query += " AND wzcateseq = %s"
                        count_params.append(int(classification))
                    if department:
                        count_query += " AND wzmgrdptnm = %s"
                        count_params.append(department)

                    cur.execute(count_query, count_params)
                else:
                    cur.execute(count_query)

                total_count = cur.fetchone()[0]

                return {
                    "success": True,
                    "data": regulations,
                    "total": total_count,
                    "limit": limit,
                    "offset": offset
                }

    except Exception as e:
        logger.error(f"Error getting history regulations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _find_source_file(source_path: str, ext: str, wzruleseq: int) -> Optional[Path]:
    """
    다양한 경로에서 원본 파일 찾기

    Args:
        source_path: DB에 저장된 경로
        ext: 확장자 (docx, pdf, json)
        wzruleseq: 규정 시퀀스

    Returns:
        실제 파일 경로 또는 None
    """
    possible_paths = []

    # 1. DB 경로가 있으면 먼저 시도
    if source_path:
        if source_path.startswith('/'):
            possible_paths.append(Path(source_path))
        elif source_path.startswith('applib/'):
            possible_paths.append(APPLIB_DIR.parent / source_path)
        else:
            possible_paths.append(APPLIB_DIR / source_path)
            possible_paths.append(Path(source_path))

    # 2. 기본 경로에서 찾기
    if ext == 'json':
        possible_paths.append(JSON_DIR / f"{wzruleseq}.json")
        possible_paths.append(Path(f"{settings.WWW_STATIC_FILE_DIR}/{wzruleseq}.json"))
    elif ext == 'docx':
        # docx 폴더에서 패턴으로 찾기
        for f in DOCX_DIR.glob(f"*{wzruleseq}*.docx"):
            possible_paths.append(f)
    elif ext == 'pdf':
        # pdf 폴더에서 패턴으로 찾기
        for f in PDF_DIR.glob(f"*{wzruleseq}*.pdf"):
            possible_paths.append(f)

    # 실제 존재하는 파일 찾기
    for path in possible_paths:
        if path and path.exists():
            logger.info(f"Found source file: {path}")
            return path

    logger.warning(f"Source file not found for {ext}, wzruleseq={wzruleseq}, tried paths: {possible_paths[:3]}")
    return None


def _move_file_to_old(source_path: str, target_dir: Path, wzruleid: int, wzruleseq: int, ext: str) -> Optional[str]:
    """
    파일을 _old 디렉토리로 이동

    Args:
        source_path: 원본 파일 경로
        target_dir: 대상 디렉토리 (예: docx_old)
        wzruleid: 규정 ID
        wzruleseq: 규정 시퀀스
        ext: 확장자 (docx, pdf, json)

    Returns:
        새 파일 경로 (applib/xxx_old/xxx.ext) 또는 None
    """
    try:
        # 다양한 경로에서 파일 찾기
        full_source = _find_source_file(source_path, ext, wzruleseq)

        if not full_source:
            logger.warning(f"No {ext} file found for rule {wzruleseq}")
            return None

        # 새 파일명: {wzruleid}_{wzruleseq}.{ext}
        new_filename = f"{wzruleid}_{wzruleseq}.{ext}"
        target_path = target_dir / new_filename

        # 대상 파일이 이미 존재하면 덮어쓰기
        if target_path.exists():
            logger.warning(f"Target file already exists, will overwrite: {target_path}")

        # 파일 이동
        shutil.move(str(full_source), str(target_path))
        logger.info(f"Moved file: {full_source} -> {target_path}")

        # 상대 경로 반환
        return f"applib/{target_dir.name}/{new_filename}"

    except Exception as e:
        logger.error(f"Error moving file {source_path}: {e}")
        return None


@router.post("/revise/{rule_id}")
async def revise_regulation(
    rule_id: int,
    revision_data: Dict[str, Any]
):
    """규정 개정 처리 - 기존 규정을 연혁으로, 새 버전을 현행으로, 파일을 _old로 이동"""
    try:
        db_manager = get_db_connection()
        moved_files = {}

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 1. 현재 규정 조회 (파일 경로 포함)
                cur.execute("""
                    SELECT wzruleseq, wzruleid, wzfiledocx, wzfilepdf, wzfilejson, wzcontent_path
                    FROM wz_rule
                    WHERE wzruleseq = %s AND wzNewFlag = '현행'
                """, (rule_id,))

                file_info = cur.fetchone()
                if not file_info:
                    raise HTTPException(status_code=404, detail="현행 규정을 찾을 수 없습니다.")

                wzruleseq = file_info[0]
                wzruleid = file_info[1]
                old_docx_path = file_info[2]
                old_pdf_path = file_info[3]
                old_json_path = file_info[4] or file_info[5]  # wzfilejson 또는 wzcontent_path

                # 전체 규정 조회
                cur.execute("""
                    SELECT * FROM wz_rule
                    WHERE wzruleseq = %s AND wzNewFlag = '현행'
                """, (rule_id,))

                current_rule = cur.fetchone()

                # 컬럼명 가져오기
                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'wz_rule'
                    ORDER BY ordinal_position
                """)
                columns = [row[0] for row in cur.fetchall()]

                # 2. 파일을 _old 디렉토리로 이동
                new_docx_path = _move_file_to_old(old_docx_path, DOCX_OLD_DIR, wzruleid, wzruleseq, 'docx')
                new_pdf_path = _move_file_to_old(old_pdf_path, PDF_OLD_DIR, wzruleid, wzruleseq, 'pdf')
                new_json_path = _move_file_to_old(old_json_path, JSON_OLD_DIR, wzruleid, wzruleseq, 'json')

                if new_docx_path:
                    moved_files['docx'] = new_docx_path
                if new_pdf_path:
                    moved_files['pdf'] = new_pdf_path
                if new_json_path:
                    moved_files['json'] = new_json_path

                logger.info(f"Moved files for rule {rule_id}: {moved_files}")

                # 3. 기존 규정을 연혁으로 변경 + 파일 경로 업데이트
                cur.execute("""
                    UPDATE wz_rule
                    SET wzNewFlag = '연혁',
                        wzclosedate = %s,
                        wzfiledocx = %s,
                        wzfilepdf = %s,
                        wzfilejson = %s,
                        wzcontent_path = %s
                    WHERE wzruleseq = %s
                """, (
                    datetime.now().strftime('%Y.%m.%d'),
                    new_docx_path,
                    new_pdf_path,
                    new_json_path,
                    new_json_path,
                    rule_id
                ))

                # 4. 새 버전 삽입 (현행)
                # 기존 데이터 복사하되 일부 필드 업데이트
                insert_columns = []
                insert_values = []

                for i, col in enumerate(columns):
                    if col == 'wzruleseq':
                        continue  # 자동 생성
                    elif col == 'wznewflag':
                        insert_columns.append(col)
                        insert_values.append('현행')
                    elif col == 'wzlastrevdate':
                        insert_columns.append(col)
                        insert_values.append(datetime.now().strftime('%Y.%m.%d'))
                    elif col == 'wzedittype':
                        insert_columns.append(col)
                        insert_values.append('개정')
                    elif col == 'wzclosedate':
                        insert_columns.append(col)
                        insert_values.append(None)  # 현행은 폐지일 없음
                    elif col in ['wzfiledocx', 'wzfilepdf', 'wzfilejson', 'wzcontent_path']:
                        insert_columns.append(col)
                        insert_values.append(None)  # 새 규정은 파일 경로 초기화
                    elif col in revision_data:
                        # 개정 데이터가 있으면 사용
                        insert_columns.append(col)
                        insert_values.append(revision_data[col])
                    else:
                        # 기존 값 사용
                        insert_columns.append(col)
                        insert_values.append(current_rule[i])

                # INSERT 쿼리 생성
                insert_query = f"""
                    INSERT INTO wz_rule ({', '.join(insert_columns)})
                    VALUES ({', '.join(['%s'] * len(insert_columns))})
                    RETURNING wzruleseq
                """

                cur.execute(insert_query, insert_values)
                new_rule_id = cur.fetchone()[0]

                conn.commit()

                # 새 규정 정보 조회 (색인을 위해)
                with db_manager.get_connection() as conn2:
                    with conn2.cursor() as cur2:
                        cur2.execute("""
                            SELECT wzname, wzcontent_path
                            FROM wz_rule
                            WHERE wzruleseq = %s
                        """, (new_rule_id,))
                        new_rule_info = cur2.fetchone()

                # 자동 색인 트리거 (백그라운드)
                if new_rule_info and new_rule_info[1]:
                    threading.Thread(
                        target=_trigger_auto_indexing,
                        args=(new_rule_id, new_rule_info[0], new_rule_info[1]),
                        daemon=True
                    ).start()

                return {
                    "success": True,
                    "message": f"규정이 개정되었습니다. (기존: {rule_id} → 신규: {new_rule_id})",
                    "old_rule_id": rule_id,
                    "new_rule_id": new_rule_id,
                    "moved_files": moved_files
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revising regulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update/{rule_id}")
async def update_regulation(
    rule_id: int,
    update_data: Dict[str, Any]
):
    """규정 내용 업데이트 (개정 후 편집)"""
    try:
        db_manager = get_db_connection()

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 현재 규정 확인
                cur.execute("""
                    SELECT wzruleseq FROM wz_rule
                    WHERE wzruleseq = %s AND wzNewFlag = '현행'
                """, (rule_id,))

                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="현행 규정을 찾을 수 없습니다.")

                # 업데이트할 필드들 준비
                update_fields = []
                update_values = []

                # 가능한 업데이트 필드들
                field_mapping = {
                    'title': 'wzname',
                    'department': 'wzmgrdptnm',
                    'revisionDate': 'wzlastrevdate',
                    'contentPath': 'wzcontent_path'
                }

                for key, db_field in field_mapping.items():
                    if key in update_data and update_data[key] is not None:
                        update_fields.append(f"{db_field} = %s")
                        update_values.append(update_data[key])

                if not update_fields:
                    raise HTTPException(status_code=400, detail="업데이트할 내용이 없습니다.")

                # UPDATE 쿼리 실행
                update_values.append(rule_id)
                update_query = f"""
                    UPDATE wz_rule
                    SET {', '.join(update_fields)}
                    WHERE wzruleseq = %s
                """

                cur.execute(update_query, update_values)

                # 업데이트된 데이터 조회
                cur.execute("""
                    SELECT wzruleseq, wzname, wzpubno, wzestabdate,
                           wzlastrevdate, wzmgrdptnm, wzedittype, wzexecdate,
                           wzlkndname, wzcontent_path, wzNewFlag
                    FROM wz_rule
                    WHERE wzruleseq = %s
                """, (rule_id,))

                updated_rule = cur.fetchone()

                conn.commit()

                # 자동 색인 트리거 (백그라운드) - 컨텐츠가 업데이트되면 색인 갱신
                if updated_rule and updated_rule[9]:  # wzcontent_path가 있으면
                    threading.Thread(
                        target=_trigger_auto_indexing,
                        args=(rule_id, updated_rule[1], updated_rule[9]),
                        daemon=True
                    ).start()

                return {
                    "success": True,
                    "message": "규정이 성공적으로 업데이트되었습니다.",
                    "rule_id": rule_id,
                    "data": {
                        "rule_id": updated_rule[0],
                        "name": updated_rule[1],
                        "publication_no": updated_rule[2],
                        "established_date": updated_rule[3],
                        "last_revised_date": updated_rule[4],
                        "department": updated_rule[5],
                        "edit_type": updated_rule[6],
                        "execution_date": updated_rule[7],
                        "large_category": updated_rule[8],
                        "content_path": updated_rule[9],
                        "status": updated_rule[10]
                    }
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating regulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/advanced-search")
async def advanced_search_regulations(
    search: Optional[str] = Query(None, description="검색어"),
    department: Optional[List[str]] = Query(None, description="담당부서 목록"),
    announce_start: Optional[str] = Query(None, description="공포일 시작"),
    announce_end: Optional[str] = Query(None, description="공포일 종료"),
    effective_start: Optional[str] = Query(None, description="시행일 시작"),
    effective_end: Optional[str] = Query(None, description="시행일 종료"),
    limit: int = Query(1000),
    offset: int = Query(0)
):
    """상세 검색 - 날짜 범위 및 다중 부서 검색 지원"""
    try:
        db_manager = get_db_connection()

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 기본 쿼리 (현행과 연혁 모두 검색)
                query = """
                    SELECT
                        wzruleseq,
                        wzname,
                        wzpubno,
                        wzestabdate,
                        wzlastrevdate,
                        wzmgrdptnm,
                        wzedittype,
                        wzexecdate,
                        wzlkndname,
                        wzcontent_path,
                        wzNewFlag
                    FROM wz_rule
                    WHERE 1=1
                """

                params = []

                # 검색어 조건
                if search:
                    query += " AND (wzname ILIKE %s OR wzpubno ILIKE %s)"
                    search_pattern = f'%{search}%'
                    params.extend([search_pattern, search_pattern])

                # 부서 필터 (다중 선택)
                if department and len(department) > 0:
                    dept_placeholders = ', '.join(['%s'] * len(department))
                    query += f" AND wzmgrdptnm IN ({dept_placeholders})"
                    params.extend(department)

                # 공포일자 범위
                if announce_start:
                    query += " AND wzestabdate >= %s"
                    params.append(announce_start.replace('-', '.'))
                if announce_end:
                    query += " AND wzestabdate <= %s"
                    params.append(announce_end.replace('-', '.'))

                # 시행일자 범위
                if effective_start:
                    query += " AND wzexecdate >= %s"
                    params.append(effective_start.replace('-', '.'))
                if effective_end:
                    query += " AND wzexecdate <= %s"
                    params.append(effective_end.replace('-', '.'))

                query += " ORDER BY wzNewFlag DESC, wzpubno, wzruleseq"
                query += f" LIMIT {limit} OFFSET {offset}"

                cur.execute(query, params)
                results = cur.fetchall()

                regulations = []
                for row in results:
                    regulations.append({
                        "rule_id": row[0],
                        "name": row[1],
                        "publication_no": row[2],
                        "established_date": row[3],
                        "last_revised_date": row[4],
                        "department": row[5],
                        "edit_type": row[6],
                        "execution_date": row[7],
                        "large_category": row[8],
                        "content_path": row[9],
                        "status": row[10]
                    })

                # 전체 개수 조회
                count_query = "SELECT COUNT(*) FROM wz_rule WHERE 1=1"
                count_params = []

                if search:
                    count_query += " AND (wzname ILIKE %s OR wzpubno ILIKE %s)"
                    count_params.extend([search_pattern, search_pattern])

                if department and len(department) > 0:
                    count_query += f" AND wzmgrdptnm IN ({dept_placeholders})"
                    count_params.extend(department)

                if announce_start:
                    count_query += " AND wzestabdate >= %s"
                    count_params.append(announce_start.replace('-', '.'))
                if announce_end:
                    count_query += " AND wzestabdate <= %s"
                    count_params.append(announce_end.replace('-', '.'))

                if effective_start:
                    count_query += " AND wzexecdate >= %s"
                    count_params.append(effective_start.replace('-', '.'))
                if effective_end:
                    count_query += " AND wzexecdate <= %s"
                    count_params.append(effective_end.replace('-', '.'))

                cur.execute(count_query, count_params)
                total_count = cur.fetchone()[0]

                return {
                    "success": True,
                    "data": regulations,
                    "total": total_count,
                    "limit": limit,
                    "offset": offset
                }

    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 자동 색인 트리거 함수
# ============================================================================

def _trigger_auto_indexing(rule_id: int, rule_name: str, content_path: str):
    """규정 생성/수정 시 자동 색인 트리거 (백그라운드)"""
    try:
        from .indexing_service import index_single_regulation
        db_manager = get_db_connection()
        index_single_regulation(db_manager, rule_id, rule_name, content_path)
        logger.info(f"Auto-indexing completed for: {rule_name} (ID: {rule_id})")
    except Exception as e:
        logger.error(f"Error in auto-indexing: {e}")