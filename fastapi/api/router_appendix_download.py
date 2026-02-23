# -*- coding: utf-8 -*-
"""
    router_appendix_download.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    부록 PDF 다운로드 + 조회 로깅 API

    기존 JavaScript 코드가 호출하는 엔드포인트:
    /api/v1/appendix/download/{rule_seq}/{file_name}

    기능:
    - PDF 파일 서빙
    - 자동 조회 로그 기록
    - 기존 코드와 호환

    :copyright: (c) 2025 by wizice.
    :license: wizice.com
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import re
from datetime import datetime
from urllib.parse import unquote
from typing import List, Dict, Any

from .timescaledb_manager_v2 import DatabaseConnectionManager
from . import query_download_logs
from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/appendix",
    tags=["appendix"],
)

# DB 연결 설정
db_config = {
    'database': settings.DB_NAME,
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD,
    'host': settings.DB_HOST,
    'port': settings.DB_PORT
}


def parse_appendix_filename(file_name: str):
    """
    부록 PDF 파일명에서 정보 추출

    파일명 형식:
    - 12.1.1._부록1._세브란스병원_의무기록위원회_운영내규_202003개정.pdf
    - 1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf

    타임스탬프가 포함된 경우도 처리:
    - 파일명.pdf.1763351842257 → 파일명.pdf
    """
    try:
        # 타임스탬프 제거 (캐시 버스팅용)
        # 예: "파일명.pdf.1763351842257" → "파일명.pdf"
        clean_file_name = re.sub(r'\.\d{13}$', '', file_name)

        # 패턴: {규정코드}._부록{번호}._{부록명}_{날짜}{상태}.pdf
        pattern = r'^([0-9.]+)\.?_부록(\d+)\._(.+?)(?:_\d{6,8})?(?:개정|검토)?\.pdf$'
        match = re.match(pattern, clean_file_name)

        if match:
            rule_pubno_raw = match.group(1)
            rule_pubno = rule_pubno_raw if rule_pubno_raw.endswith('.') else rule_pubno_raw + '.'
            appendix_no = match.group(2)
            appendix_name_raw = match.group(3)
            appendix_name_clean = appendix_name_raw.replace('_', ' ')
            appendix_name = f"부록{appendix_no}. {appendix_name_clean}"
            full_name = f"{rule_pubno} {appendix_name}"

            return {
                'rule_pubno': rule_pubno,
                'appendix_no': appendix_no,
                'appendix_name': appendix_name,
                'full_name': full_name,
                'clean_file_name': clean_file_name
            }
        else:
            logger.warning(f"Failed to parse appendix filename: {clean_file_name}")
            return {
                'rule_pubno': '',
                'appendix_no': '',
                'appendix_name': clean_file_name.replace('.pdf', '').replace('_', ' '),
                'full_name': clean_file_name.replace('.pdf', '').replace('_', ' '),
                'clean_file_name': clean_file_name
            }

    except Exception as e:
        logger.error(f"Error parsing appendix filename: {e}")
        return {
            'rule_pubno': '',
            'appendix_no': '',
            'appendix_name': file_name,
            'full_name': file_name,
            'clean_file_name': file_name
        }


@router.get("/download/{rule_seq}/{file_name:path}")
async def download_appendix_with_logging(rule_seq: int, file_name: str, request: Request):
    """
    부록 PDF 다운로드 + 자동 조회 로깅

    기존 JavaScript 코드가 호출하는 엔드포인트:
    /api/v1/appendix/download/{rule_seq}/{file_name}

    Args:
        rule_seq: 내규 ID (wzRuleSeq)
        file_name: PDF 파일명 (URL 인코딩됨, 타임스탬프 포함 가능)

    Returns:
        PDF 파일
    """
    try:
        # URL 디코딩
        decoded_file_name = unquote(file_name)

        # 파일명 파싱 (타임스탬프 제거 포함)
        parsed_info = parse_appendix_filename(decoded_file_name)
        clean_file_name = parsed_info['clean_file_name']

        # PDF 파일 경로 찾기 (여러 변형 시도)
        pdf_dir = Path(settings.WWW_STATIC_PDF_DIR)
        pdf_file_path = None

        # 1. 원본 파일명 그대로 시도
        candidate = pdf_dir / clean_file_name
        if candidate.exists():
            pdf_file_path = candidate
        else:
            # 2. 언더스코어를 공백으로 변환하여 시도
            candidate_space = pdf_dir / clean_file_name.replace('_', ' ')
            if candidate_space.exists():
                pdf_file_path = candidate_space
            else:
                # 3. glob 패턴으로 유사한 파일 찾기
                import glob
                pattern = clean_file_name.replace('_', '*')
                matches = list(pdf_dir.glob(pattern))
                if matches:
                    pdf_file_path = matches[0]

        if not pdf_file_path or not pdf_file_path.exists():
            logger.warning(f"PDF file not found: {clean_file_name}")
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {clean_file_name}")

        # 조회 로그 기록 (비동기, 실패해도 무시)
        try:
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
                        rule_seq,  # rule_seq를 rule_id로 사용
                        parsed_info['appendix_name'],
                        parsed_info['rule_pubno']
                    ))
                    conn.commit()

            logger.info(f"✅ Appendix view logged: rule_seq={rule_seq}, {parsed_info['full_name']}")

        except Exception as log_error:
            # 로깅 실패해도 PDF는 정상 반환
            logger.warning(f"⚠️ View log failed (ignored): {log_error}")

        # 다운로드 이력 기록 (방문자 정보 포함)
        try:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent', '')
            referer = request.headers.get('referer', '')
            session_id = request.cookies.get('session_id', '')

            query_download_logs.insert_download_log(
                rule_id=rule_seq,
                rule_name=parsed_info['appendix_name'],
                rule_pubno=parsed_info['rule_pubno'],
                file_type='appendix',
                file_name=clean_file_name,
                ip_address=ip_address,
                user_agent=user_agent,
                referer=referer,
                session_id=session_id,
                user_id=None
            )
            logger.info(f"Download logged: rule_seq={rule_seq}, file={clean_file_name}")
        except Exception as download_log_error:
            logger.warning(f"Download log failed (ignored): {download_log_error}")

        # PDF 파일 반환
        from urllib.parse import quote
        encoded_filename = quote(clean_file_name)

        return FileResponse(
            path=pdf_file_path,
            media_type="application/pdf",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving appendix PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/{rule_seq}")
async def list_appendix_files_public(rule_seq: int):
    """
    특정 규정의 부록 파일 목록 조회 (인증 불필요 - 공개 API)

    프론트엔드에서 부록 PDF를 열 때 사용하는 API입니다.
    wz_appendix 테이블에서 해당 규정의 부록 목록을 조회합니다.

    Args:
        rule_seq: 규정 ID (wzruleseq)

    Returns:
        부록 파일 목록 (wzappendixfilename, wzfilepath 등)
    """
    try:
        logger.info(f"[Appendix Public] Listing appendix files for rule_seq: {rule_seq}")

        db_manager = DatabaseConnectionManager(**db_config)

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # wz_appendix 테이블에서 부록 목록 조회
                cur.execute("""
                    SELECT
                        wzappendixseq,
                        wzappendixno,
                        wzappendixname,
                        wzfiletype,
                        wzfilepath
                    FROM wz_appendix
                    WHERE wzruleseq = %s
                    ORDER BY CAST(wzappendixno AS INTEGER)
                """, (rule_seq,))

                rows = cur.fetchall()
                columns = ['wzappendixseq', 'wzappendixno', 'wzappendixname', 'wzfiletype', 'wzfilepath']

                appendix_list = []
                for row in rows:
                    record = dict(zip(columns, row))

                    # wzappendixfilename 생성 (파일 경로에서 파일명만 추출)
                    filepath = record.get('wzfilepath', '')
                    if filepath:
                        # 파일 경로에서 파일명 추출
                        filename = Path(filepath).name
                        record['wzappendixfilename'] = filename
                    else:
                        record['wzappendixfilename'] = ''

                    appendix_list.append(record)

                logger.info(f"[Appendix Public] Found {len(appendix_list)} appendix files for rule_seq {rule_seq}")

                return appendix_list

    except Exception as e:
        logger.error(f"[Appendix Public] Error listing appendix files: {e}")
        raise HTTPException(status_code=500, detail=str(e))
