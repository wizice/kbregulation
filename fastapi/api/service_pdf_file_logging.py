# -*- coding: utf-8 -*-
"""
    service_pdf_file_logging.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    부록 PDF 파일 서빙 + 조회 로깅

    기능:
    - /static/pdf/{file_name} 요청을 가로채기
    - PDF 파일 내용 반환
    - regulation_view_logs 테이블에 자동 로깅
    - 파일명에서 규정 정보 파싱

    :copyright: (c) 2025 by wizice.
    :license: wizice.com
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pathlib import Path
import re
from datetime import datetime

from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/pdf-file",
    tags=["pdf-file"],
)


def parse_appendix_filename(file_name: str):
    """
    부록 PDF 파일명에서 정보 추출

    파일명 형식:
    - 1.2.1._부록1._구두처방_의약품_목록_20250723개정.pdf
    - 10.2.1._부록2._임상권한 관리절차 가이드라인_2022503검토.pdf

    Returns:
        dict: {
            'rule_pubno': '1.2.1.',
            'appendix_no': '1',
            'appendix_name': '부록1. 구두처방 의약품 목록',
            'full_name': '1.2.1. 부록1. 구두처방 의약품 목록'
        }
    """
    try:
        # 패턴 1: {규정코드}._부록{번호}._{부록명}_{날짜}{상태}.pdf
        pattern = r'^([0-9.]+)\.?_부록(\d+)\._(.+?)(?:_\d{8})?(?:개정|검토)?\.pdf$'
        match = re.match(pattern, file_name)

        if match:
            rule_pubno_raw = match.group(1)     # "1.2.1"
            # 이미 점으로 끝나면 그대로, 아니면 점 추가
            rule_pubno = rule_pubno_raw if rule_pubno_raw.endswith('.') else rule_pubno_raw + '.'
            appendix_no = match.group(2)        # "1"
            appendix_name_raw = match.group(3)  # "구두처방_의약품_목록"

            # 언더스코어를 공백으로 변환
            appendix_name_clean = appendix_name_raw.replace('_', ' ')

            # 전체 이름 조합
            appendix_name = f"부록{appendix_no}. {appendix_name_clean}"
            full_name = f"{rule_pubno} {appendix_name}"

            return {
                'rule_pubno': rule_pubno,
                'appendix_no': appendix_no,
                'appendix_name': appendix_name,
                'full_name': full_name
            }
        else:
            # 파싱 실패 시 기본값
            logger.warning(f"Failed to parse appendix filename: {file_name}")
            return {
                'rule_pubno': '',
                'appendix_no': '',
                'appendix_name': file_name.replace('.pdf', '').replace('_', ' '),
                'full_name': file_name.replace('.pdf', '').replace('_', ' ')
            }

    except Exception as e:
        logger.error(f"Error parsing appendix filename: {e}")
        return {
            'rule_pubno': '',
            'appendix_no': '',
            'appendix_name': file_name,
            'full_name': file_name
        }


@router.get("/{file_name}")
async def serve_pdf_with_logging(file_name: str, request: Request):
    """
    부록 PDF 파일 서빙 + 자동 조회 로깅

    Args:
        file_name: PDF 파일명 (예: "1.2.1._부록1._구두처방_의약품_목록.pdf")

    Returns:
        PDF 파일
    """
    try:
        # PDF 파일 경로
        pdf_file_path = Path(f"{settings.WWW_STATIC_PDF_DIR}/{file_name}")

        if not pdf_file_path.exists():
            logger.warning(f"PDF file not found: {file_name}")
            raise HTTPException(status_code=404, detail="PDF file not found")

        # 파일명에서 규정 정보 파싱
        parsed_info = parse_appendix_filename(file_name)

        # 🆕 조회 로그 기록 (비동기, 실패해도 무시)
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
                        None,  # 부록은 rule_id 없음
                        parsed_info['appendix_name'],
                        parsed_info['rule_pubno']
                    ))
                    conn.commit()

            logger.info(f"✅ PDF view logged: {parsed_info['full_name']}")

        except Exception as log_error:
            # 로깅 실패해도 PDF는 정상 반환
            logger.warning(f"⚠️ View log failed (ignored): {log_error}")

        # PDF 파일 반환 (FileResponse)
        # 한글 파일명 인코딩 처리
        from urllib.parse import quote
        encoded_filename = quote(file_name)

        return FileResponse(
            path=pdf_file_path,
            media_type="application/pdf",
            headers={
                "Cache-Control": "public, max-age=3600",  # 1시간 캐시
                "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving PDF file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
