"""
JSON 파일 뷰어 서비스
규정의 JSON 파일을 읽어와서 내용을 반환
"""

import os
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from app_logger import get_logger
from settings import settings
from .auth_middleware import get_current_user
from .timescaledb_manager_v2 import DatabaseConnectionManager as TimescaleDBManagerV2

logger = get_logger(__name__)
router = APIRouter(
    prefix="/api/v1/json",
    tags=["json-viewer"]
)


@router.get("/view/{rule_id}")
async def view_json_content(
    rule_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    규정 ID로 JSON 파일 내용을 조회

    Args:
        rule_id: 규정 ID
        user: 현재 사용자

    Returns:
        JSON 파일 내용 및 텍스트
    """
    try:
        # DB에서 JSON 파일 경로 조회
        db_config = {
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
        }

        db_manager = TimescaleDBManagerV2(**db_config)

        # wzFileJson 컬럼 조회
        query = """
            SELECT wzruleseq, wzname, wzFileJson, wzpubno, wzmgrdptnm,
                   wzestabdate, wzlastrevdate, wzexecdate, wznewflag
            FROM wz_rule
            WHERE wzruleseq = %s
        """

        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (rule_id,))
                rows = cursor.fetchall()
                result = [{k: v for k, v in zip([desc[0] for desc in cursor.description], row)} for row in rows] if rows else None

        if not result:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        regulation = result[0]
        json_path = regulation.get('wzfilejson')

        # 상대경로를 절대경로로 변환
        from .file_utils import get_absolute_path
        absolute_json_path = get_absolute_path(json_path) if json_path else None

        # 연혁 규정인 경우 merge_json_old 폴더에서도 확인
        wznewflag = regulation.get('wznewflag')
        if wznewflag and wznewflag != '현행' and json_path:
            # merge_json_old 경로로 변경 시도
            if 'merge_json/' in json_path:
                old_json_path = json_path.replace('merge_json/', 'merge_json_old/')
                old_absolute_path = get_absolute_path(old_json_path)
                if os.path.exists(old_absolute_path):
                    logger.info(f"Using history JSON from merge_json_old: {old_json_path}")
                    json_path = old_json_path
                    absolute_json_path = old_absolute_path

        # JSON 파일 내용 읽기
        json_content = None
        text_content = ""

        if absolute_json_path and os.path.exists(absolute_json_path):
            try:
                with open(absolute_json_path, 'r', encoding='utf-8') as f:
                    json_content = json.load(f)

                # 텍스트 내용 추출
                if json_content and '조문내용' in json_content:
                    articles = json_content['조문내용']
                    for article in articles:
                        if isinstance(article, dict):
                            number = article.get('번호', '')
                            content = article.get('내용', '')
                            if number:
                                text_content += f"{number} {content}\n"
                            else:
                                text_content += f"{content}\n"

                logger.info(f"JSON content loaded from {absolute_json_path} (relative: {json_path})")

            except Exception as e:
                logger.error(f"Failed to read JSON file {absolute_json_path}: {e}")
                json_content = None
        else:
            logger.info(f"No JSON file found for rule {rule_id} at path: {absolute_json_path} (relative: {json_path})")

        # 응답 데이터 구성
        response_data = {
            "success": True,
            "data": {
                "wzruleseq": regulation['wzruleseq'],
                "wzname": regulation['wzname'],
                "wzpubno": regulation['wzpubno'],
                "wzmgrdptnm": regulation['wzmgrdptnm'],
                "wzestabdate": regulation['wzestabdate'],
                "wzlastrevdate": regulation['wzlastrevdate'],
                "wzexecdate": regulation['wzexecdate'],
                "wznewflag": regulation['wznewflag'],
                "wzfilejson": json_path,
                "has_content": json_content is not None,
                "content_text": text_content if text_content else None,
                "json_content": json_content
            }
        }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing JSON content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-path")
async def update_json_path(
    rule_id: int,
    json_path: str,
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    규정의 JSON 파일 경로 업데이트

    Args:
        rule_id: 규정 ID
        json_path: 새로운 JSON 파일 경로
        user: 현재 사용자

    Returns:
        업데이트 결과
    """
    try:
        # 파일 존재 확인
        if not os.path.exists(json_path):
            raise HTTPException(status_code=400, detail="JSON 파일이 존재하지 않습니다.")

        # DB 업데이트
        db_config = {
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
        }

        db_manager = TimescaleDBManagerV2(**db_config)

        update_query = """
            UPDATE wz_rule
            SET wzFileJson = %s
            WHERE wzruleseq = %s
            RETURNING wzruleseq, wzname
        """

        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(update_query, (json_path, rule_id))
                rows = cursor.fetchall()
                conn.commit()
                result = [{k: v for k, v in zip([desc[0] for desc in cursor.description], row)} for row in rows] if rows else None

        if not result:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        logger.info(f"Updated JSON path for rule {rule_id}: {json_path}")

        return {
            "success": True,
            "message": "JSON 파일 경로가 업데이트되었습니다.",
            "rule_id": rule_id,
            "json_path": json_path
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating JSON path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/read-file")
async def read_json_file(
    file_path: str,
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    JSON 파일 직접 읽기 (디버깅용)

    Args:
        file_path: JSON 파일 경로
        user: 현재 사용자

    Returns:
        JSON 파일 내용
    """
    try:
        # 보안을 위해 applib 폴더 내 파일만 허용
        applib_path = settings.APPLIB_DIR
        if not file_path.startswith(applib_path):
            raise HTTPException(status_code=403, detail="허용되지 않은 경로입니다.")

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)

        return {
            "success": True,
            "file_path": file_path,
            "content": content
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading JSON file: {e}")
        raise HTTPException(status_code=500, detail=str(e))