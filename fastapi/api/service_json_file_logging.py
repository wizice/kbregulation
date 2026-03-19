# -*- coding: utf-8 -*-
"""
    service_json_file_logging.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    JSON 파일 서빙 + 조회 로깅

    기능:
    - /static/file/{wzruleseq}.json 요청을 가로채기
    - JSON 파일 내용 반환
    - regulation_view_logs 테이블에 자동 로깅

    :copyright: (c) 2025 by wizice.
    :license: wizice.com
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import json
from datetime import datetime

from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/json-file",
    tags=["json-file"],
)


@router.get("/{filename:path}")
async def serve_json_with_logging(filename: str, request: Request):
    """
    JSON 파일 서빙 + 자동 조회 로깅
    정수 ID (예: 350.json) 또는 파일명 (예: (6-8)_여비규정_250305_merged.json) 모두 지원

    Args:
        filename: JSON 파일명 또는 정수ID.json

    Returns:
        JSON 파일 내용
    """
    import re

    try:
        # 보안: 경로 탐색 방지
        safe_name = Path(filename).name
        if '..' in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        # .json 확장자가 없으면 추가
        if not safe_name.endswith('.json'):
            safe_name = safe_name + '.json'

        # JSON 파일 경로
        json_file_path = Path(f"{settings.WWW_STATIC_FILE_DIR}/{safe_name}")

        if not json_file_path.exists():
            logger.warning(f"JSON file not found: {safe_name}")
            raise HTTPException(status_code=404, detail="JSON file not found")

        # JSON 파일 읽기
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # 문서정보에서 규정명 추출
        rule_name = json_data.get('문서정보', {}).get('규정명', safe_name)
        rule_pubno = json_data.get('문서정보', {}).get('규정표기명', '')

        # wzruleseq 추출: 정수 ID 또는 파일명에서
        wzruleseq = 0
        base = safe_name.replace('.json', '')
        if base.isdigit():
            wzruleseq = int(base)
        else:
            seq_match = re.search(r'_(\d+)\.json$', safe_name)
            if seq_match:
                wzruleseq = int(seq_match.group(1))

        _log_view(wzruleseq, rule_name, rule_pubno)

        return JSONResponse(content=json_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving JSON file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _log_view(wzruleseq, rule_name, rule_pubno):
    """조회 로그 기록 (실패해도 무시)"""
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
                """, (wzruleseq, rule_name, rule_pubno))
                conn.commit()

        logger.info(f"JSON view logged: {rule_name} (ID: {wzruleseq})")

    except Exception as log_error:
        logger.warning(f"View log failed (ignored): {log_error}")
