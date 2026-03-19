# -*- coding: utf-8 -*-
"""
    router_public_search.py
    ~~~~~~~~~~~~~~~~~~~~~~~

    사용자 화면용 공개 검색 API
    (/api/search 엔드포인트)

    :copyright: (c) 2024 by wizice.
    :license: wizice.com
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Dict, Any, List
import logging
import os
import re
from pathlib import Path
from datetime import datetime

from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["public-search"],
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


@router.get("/search")
async def search_regulations(
    q: str = Query(..., min_length=1, max_length=200, description="검색어"),
    search_type: str = Query("content", description="검색 타입: title, content, appendix, all"),
    limit: int = Query(50, ge=1, le=200, description="최대 결과 수"),
    page: int = Query(1, ge=1, description="페이지 번호")
):
    """규정 검색 (사용자 화면용 공개 API)

    Args:
        q: 검색어
        search_type: 검색 타입
            - title: 규정명 검색
            - content: 본문 검색
            - appendix: 부록 검색
            - all: 통합 검색
        limit: 최대 결과 수
        page: 페이지 번호

    Returns:
        {
            "success": true,
            "results": [...],
            "total": 123,
            "page": 1,
            "limit": 50
        }
    """
    try:
        logger.info(f"Public search: q='{q}', type='{search_type}', limit={limit}, page={page}")

        db_manager = get_db_connection()
        offset = (page - 1) * limit

        # 검색 타입 검증
        valid_types = ['title', 'content', 'appendix', 'all']
        if search_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid search_type. Must be one of {valid_types}"
            )

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 검색 쿼리 구성
                search_pattern = f'%{q}%'

                if search_type == 'title':
                    # 규정명 검색
                    query = """
                        SELECT
                            wzruleseq,
                            wzname,
                            wzpubno,
                            wzmgrdptnm,
                            wzestabdate,
                            wzexecdate,
                            wzlastrevdate,
                            wzcontent_path,
                            'title' as match_type
                        FROM wz_rule
                        WHERE wzNewFlag = '현행'
                        AND wzname ILIKE %s
                        ORDER BY wzname
                        LIMIT %s OFFSET %s
                    """
                    cur.execute(query, (search_pattern, limit, offset))

                elif search_type == 'content':
                    # 본문 검색 (PostgreSQL FTS 사용)
                    query = """
                        SELECT
                            wzruleseq,
                            wzname,
                            wzpubno,
                            wzmgrdptnm,
                            wzestabdate,
                            wzexecdate,
                            wzlastrevdate,
                            wzcontent_path,
                            'content' as match_type
                        FROM wz_rule
                        WHERE wzNewFlag = '현행'
                        AND index_status = 'completed'
                        AND content_text ILIKE %s
                        ORDER BY
                            CASE
                                WHEN wzname ILIKE %s THEN 1
                                ELSE 2
                            END,
                            wzname
                        LIMIT %s OFFSET %s
                    """
                    cur.execute(query, (search_pattern, search_pattern, limit, offset))

                elif search_type == 'appendix':
                    # 부록 검색 (미구현 - 일단 제목 검색)
                    query = """
                        SELECT
                            wzruleseq,
                            wzname,
                            wzpubno,
                            wzmgrdptnm,
                            wzestabdate,
                            wzexecdate,
                            wzlastrevdate,
                            wzcontent_path,
                            'appendix' as match_type
                        FROM wz_rule
                        WHERE wzNewFlag = '현행'
                        AND wzname ILIKE %s
                        ORDER BY wzname
                        LIMIT %s OFFSET %s
                    """
                    cur.execute(query, (search_pattern, limit, offset))

                else:  # all
                    # 통합 검색
                    query = """
                        SELECT
                            wzruleseq,
                            wzname,
                            wzpubno,
                            wzmgrdptnm,
                            wzestabdate,
                            wzexecdate,
                            wzlastrevdate,
                            wzcontent_path,
                            CASE
                                WHEN wzname ILIKE %s THEN 'title'
                                WHEN content_text ILIKE %s THEN 'content'
                                ELSE 'other'
                            END as match_type
                        FROM wz_rule
                        WHERE wzNewFlag = '현행'
                        AND (
                            wzname ILIKE %s
                            OR (index_status = 'completed' AND content_text ILIKE %s)
                        )
                        ORDER BY
                            CASE
                                WHEN wzname ILIKE %s THEN 1
                                WHEN content_text ILIKE %s THEN 2
                                ELSE 3
                            END,
                            wzname
                        LIMIT %s OFFSET %s
                    """
                    cur.execute(query, (
                        search_pattern, search_pattern,
                        search_pattern, search_pattern,
                        search_pattern, search_pattern,
                        limit, offset
                    ))

                results = cur.fetchall()

                # 전체 결과 수 조회
                if search_type == 'title':
                    count_query = """
                        SELECT COUNT(*) FROM wz_rule
                        WHERE wzNewFlag = '현행' AND wzname ILIKE %s
                    """
                    cur.execute(count_query, (search_pattern,))
                elif search_type == 'content':
                    count_query = """
                        SELECT COUNT(*) FROM wz_rule
                        WHERE wzNewFlag = '현행'
                        AND index_status = 'completed'
                        AND content_text ILIKE %s
                    """
                    cur.execute(count_query, (search_pattern,))
                elif search_type == 'appendix':
                    count_query = """
                        SELECT COUNT(*) FROM wz_rule
                        WHERE wzNewFlag = '현행' AND wzname ILIKE %s
                    """
                    cur.execute(count_query, (search_pattern,))
                else:  # all
                    count_query = """
                        SELECT COUNT(*) FROM wz_rule
                        WHERE wzNewFlag = '현행'
                        AND (wzname ILIKE %s OR (index_status = 'completed' AND content_text ILIKE %s))
                    """
                    cur.execute(count_query, (search_pattern, search_pattern))

                total_count = cur.fetchone()[0]

                # 결과 포맷팅
                search_results = []
                for row in results:
                    result = {
                        'id': row[0],
                        'name': row[1],
                        'pubno': row[2],
                        'department': row[3],
                        'establishedDate': row[4],
                        'executionDate': row[5],
                        'revisionDate': row[6],
                        'filePath': row[7],
                        'matchType': row[8]
                    }
                    search_results.append(result)

                logger.info(f"Search completed: {total_count} total, {len(search_results)} returned")

                return {
                    "success": True,
                    "results": search_results,
                    "total": total_count,
                    "page": page,
                    "limit": limit,
                    "search_type": search_type,
                    "query": q
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")


@router.get("/search/stats")
async def get_search_stats():
    """검색 통계 조회 (공개 API)"""
    try:
        db_manager = get_db_connection()

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 전체 통계
                cur.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN index_status = 'completed' THEN 1 END) as indexed
                    FROM wz_rule
                    WHERE wzNewFlag = '현행'
                """)

                stats = cur.fetchone()

                return {
                    "success": True,
                    "stats": {
                        "total_regulations": stats[0] or 0,
                        "indexed_regulations": stats[1] or 0,
                        "index_percentage": round((stats[1] or 0) / (stats[0] or 1) * 100, 1)
                    }
                }

    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 부록 파일 경로 설정
WWW_PDF_DIR = Path(settings.WWW_STATIC_PDF_DIR)


@router.get("/v1/appendix/list/{rule_id}")
async def public_list_appendix_files(rule_id: int):
    """
    특정 규정의 부록 파일 목록 조회 (공개 API - 인증 불필요)

    Args:
        rule_id: 규정 ID (wzruleseq)

    Returns:
        부록 파일 목록 (배열 형태)
    """
    try:
        logger.info(f"[Public API] Fetching appendix list for rule_id: {rule_id}")

        # wz_appendix 테이블에서 부록 정보 조회
        db_manager = get_db_connection()

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT
                        wzappendixseq,
                        wzappendixno,
                        wzappendixname as wzappendixfilename,
                        wzfiletype,
                        wzfilepath
                    FROM wz_appendix
                    WHERE wzruleseq = %s
                    ORDER BY CAST(wzappendixno AS INTEGER)
                """
                cur.execute(query, (rule_id,))
                rows = cur.fetchall()

                # 결과를 딕셔너리 배열로 변환 (파일 크기/수정일 포함)
                appendix_list = []
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                for row in rows:
                    item = {
                        'wzappendixseq': row[0],
                        'wzappendixno': row[1],
                        'wzappendixfilename': row[2],
                        'wzfiletype': row[3],
                        'wzfilepath': row[4]
                    }
                    # 실제 파일에서 크기/수정일 읽기
                    if row[4]:
                        full_path = os.path.join(base_dir, row[4])
                        if os.path.exists(full_path):
                            stat = os.stat(full_path)
                            item['size'] = stat.st_size
                            item['modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    appendix_list.append(item)

                logger.info(f"[Public API] Found {len(appendix_list)} appendix files for rule_id {rule_id}")
                return appendix_list

    except Exception as e:
        logger.error(f"[Public API] Error fetching appendix list: {e}")
        raise HTTPException(status_code=500, detail=f"부록 목록 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/v1/appendix/download/{rule_id}/{filename}")
async def public_download_appendix_file(rule_id: int, filename: str):
    """
    부록 파일 다운로드 (공개 API - 인증 불필요)

    Args:
        rule_id: 규정 ID
        filename: 파일명 (캐시 무효화를 위해 a.pdf.1234567 형식으로 올 수 있음)

    Returns:
        파일 다운로드 응답
    """
    try:
        logger.info(f"[Public API] Downloading appendix file: {filename} for rule_id: {rule_id}")

        # 캐시 무효화를 위한 타임스탬프 제거
        # 예: "a.pdf.1234567" → "a.pdf"
        # 패턴: .pdf, .doc 등의 확장자 뒤에 붙은 숫자만 제거 (순수 숫자만)
        actual_filename = re.sub(r'(\.[a-zA-Z]{3,4})\.?(\d+)$', r'\1', filename)

        if actual_filename != filename:
            logger.info(f"[Public API] Stripped timestamp from filename: {filename} → {actual_filename}")

        # www/static/pdf 경로에서 파일 찾기
        file_path = WWW_PDF_DIR / actual_filename

        if not file_path.exists():
            # 파일명에 언더스코어와 공백이 혼합되어 있을 수 있으므로
            # glob 패턴으로 유사한 파일 찾기
            # 예: "파일_이름" → "파일*이름"로 변환하여 "파일 이름" 또는 "파일_이름" 모두 매칭
            import glob

            # 부록 파일의 경우 특별 처리
            # {code}._부록{n}._{name}_{date}.pdf 형식
            # {name} 부분에 언더스코어가 공백으로 되어 있을 수 있음
            pattern_filename = actual_filename.replace('_', '*')
            matches = list(WWW_PDF_DIR.glob(pattern_filename))

            if matches:
                file_path = matches[0]
                actual_filename = file_path.name
                logger.info(f"[Public API] Found file with glob pattern: {actual_filename}")
            else:
                logger.warning(f"[Public API] File not found: {file_path}, pattern: {pattern_filename}")
                raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {actual_filename}")

        if not file_path.exists():
            logger.warning(f"[Public API] File not found: {file_path}")
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {actual_filename}")

        # 파일 확장자 확인
        file_extension = file_path.suffix.lower()

        # MIME 타입 매핑
        mime_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }

        media_type = mime_types.get(file_extension, 'application/octet-stream')

        logger.info(f"[Public API] Serving file: {file_path} with media_type: {media_type}")

        # ✂️ 중복 로깅 제거: 클라이언트 측(openAppendixPdf)에서 이미 로깅하므로 서버 측 로깅 비활성화
        # 부록 조회 로그는 JavaScript의 logRegulationView()에서 기록됨

        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=actual_filename  # 타임스탬프 제거된 원본 파일명 사용
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Public API] Error downloading appendix file: {e}")
        raise HTTPException(status_code=500, detail=f"파일 다운로드 중 오류가 발생했습니다: {str(e)}")


@router.get("/appendix/{reg_code}/{appendix_idx}")
async def get_appendix_by_index(reg_code: str, appendix_idx: int):
    """
    부록 파일 다운로드 (인덱스 기반, 파일명 독립적)

    Args:
        reg_code: 규정 코드 (예: "13.1.1")
        appendix_idx: 부록 인덱스 (0부터 시작)

    Returns:
        부록 파일 다운로드 응답 (PDF, DOC 등)
    """
    try:
        logger.info(f"[Public API] Fetching appendix: reg_code={reg_code}, idx={appendix_idx}")

        # 1. 규정 코드로 wzruleseq 조회
        db_manager = get_db_connection()

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # 규정 조회 (wzpubno로 조회)
                # 마지막 점 유무를 모두 처리 (1.2.1 또는 1.2.1.)
                reg_code_with_dot = reg_code if reg_code.endswith('.') else f"{reg_code}."
                reg_code_without_dot = reg_code.rstrip('.')

                cur.execute(
                    "SELECT wzruleseq FROM wz_rule WHERE (wzpubno = %s OR wzpubno = %s) AND (wzCloseDate IS NULL OR wzCloseDate = '')",
                    (reg_code_with_dot, reg_code_without_dot)
                )
                rule_row = cur.fetchone()

                if not rule_row:
                    logger.warning(f"[Public API] Regulation not found: {reg_code}")
                    raise HTTPException(status_code=404, detail=f"규정을 찾을 수 없습니다: {reg_code}")

                rule_id = rule_row[0]
                logger.info(f"[Public API] Found rule_id: {rule_id} for reg_code: {reg_code}")

                # 2. 부록 목록 조회 (wzappendixno 순으로 정렬)
                cur.execute(
                    """
                    SELECT
                        wzappendixseq,
                        wzappendixno,
                        wzappendixname,
                        wzfiletype,
                        wzfilepath
                    FROM wz_appendix
                    WHERE wzruleseq = %s
                    ORDER BY CAST(wzappendixno AS INTEGER)
                    """,
                    (rule_id,)
                )
                appendix_rows = cur.fetchall()

                if not appendix_rows:
                    logger.warning(f"[Public API] No appendix found for rule_id: {rule_id}")
                    raise HTTPException(status_code=404, detail=f"부록이 없습니다")

                if appendix_idx < 0 or appendix_idx >= len(appendix_rows):
                    logger.warning(f"[Public API] Invalid appendix index: {appendix_idx} (total: {len(appendix_rows)})")
                    raise HTTPException(status_code=404, detail=f"부록 인덱스가 잘못되었습니다: {appendix_idx}")

                # 3. 해당 인덱스의 부록 정보 가져오기
                appendix = appendix_rows[appendix_idx]
                appendix_seq, appendix_no, appendix_name, file_type, file_path = appendix

                logger.info(f"[Public API] Found appendix: seq={appendix_seq}, no={appendix_no}, name={appendix_name}")

                # 4. 파일 경로 결정
                # wzfilepath가 있으면 사용, 없으면 규칙 기반 파일명 생성
                if file_path and file_path.strip():
                    # DB에 저장된 경로 사용
                    # DB에 "www/static/pdf/파일명" 형식으로 저장되어 있으므로 파일명만 추출
                    if file_path.startswith('www/static/pdf/'):
                        filename = file_path.replace('www/static/pdf/', '')
                    else:
                        filename = file_path.strip()
                    logger.info(f"[Public API] Using DB file_path: {filename}")
                else:
                    # 규칙 기반 파일명 생성
                    filename = f"{reg_code_with_dot}_부록{appendix_no}._{appendix_name}"
                    if file_type and file_type.strip():
                        filename += f".{file_type.strip()}"
                    else:
                        filename += ".pdf"  # 기본값
                    logger.info(f"[Public API] Generated filename: {filename}")

                # 5. 실제 파일 경로 확인
                full_path = WWW_PDF_DIR / filename

                if not full_path.exists():
                    logger.error(f"[Public API] File not found: {full_path}")
                    raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {filename}")

                # 6. MIME 타입 결정
                file_extension = full_path.suffix.lower()
                mime_types = {
                    '.pdf': 'application/pdf',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.doc': 'application/msword',
                    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    '.xls': 'application/vnd.ms-excel',
                    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                }

                media_type = mime_types.get(file_extension, 'application/octet-stream')

                logger.info(f"[Public API] Serving file: {full_path} (type: {media_type})")

                # 7. 파일 응답
                return FileResponse(
                    path=str(full_path),
                    media_type=media_type,
                    filename=filename
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Public API] Error in get_appendix_by_index: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"부록 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/v1/log-view")
async def log_regulation_view(data: Dict[str, Any]):
    """
    규정/부록 조회 로그 기록 (공개 API - 인증 불필요)

    클라이언트에서 JSON 파일 로드 또는 부록 PDF 열람 시 호출

    Request Body:
        {
            "rule_id": 123,              # 규정 ID (옵션)
            "rule_seq": 123,             # 규정 SEQ (옵션)
            "rule_name": "규정명",        # 규정명 (필수)
            "rule_pubno": "1.2.3.",      # 규정 코드 (옵션)
            "view_type": "regulation"    # "regulation" or "appendix"
        }

    Returns:
        {"success": true}
    """
    try:
        rule_id = data.get('rule_id') or data.get('rule_seq')
        rule_name = data.get('rule_name', '')
        rule_pubno = data.get('rule_pubno', '')
        view_type = data.get('view_type', 'regulation')

        if not rule_name:
            raise HTTPException(status_code=400, detail="rule_name is required")

        # DB 로그 기록
        db_config = {
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'host': settings.DB_HOST,
            'port': settings.DB_PORT
        }

        db_manager = DatabaseConnectionManager(**db_config)

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO regulation_view_logs
                        (rule_id, rule_name, rule_pubno, viewed_at)
                    VALUES
                        (%s, %s, %s, NOW())
                """, (
                    rule_id,
                    rule_name,
                    rule_pubno
                ))
                conn.commit()

        logger.info(f"✅ View logged: type={view_type}, rule_id={rule_id}, name={rule_name}")

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Public API] Error logging view: {e}")
        # 로깅 실패해도 클라이언트에는 성공 응답 (사용자 경험 방해 금지)
        return {"success": False, "error": str(e)}
