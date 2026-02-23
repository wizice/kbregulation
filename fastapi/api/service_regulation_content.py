# -*- coding: utf-8 -*-
"""
    service_regulation_content.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    규정 조문 내용 조회 API

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import json
import os
import logging
from .auth_middleware import get_current_user
from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings
from app_logger import get_logger
from .regulation_view_logger import log_regulation_view

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/regulation",
    tags=["regulation"],
    responses={404: {"description": "Not found"}},
)

@router.get("/content/{rule_id}")
async def get_regulation_content(
    rule_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """규정 조문 전체 내용 조회"""
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
                # 규정 정보 및 content_path 조회
                # wzruleid가 0인 경우가 많으므로 wzruleseq를 사용
                cur.execute("""
                    SELECT
                        wzruleseq,
                        wzname,
                        wzcontent_path,
                        wzmgrdptnm,
                        wzestabdate,
                        wzlastrevdate,
                        wzpubno
                    FROM wz_rule
                    WHERE wzruleseq = %s
                """, (int(rule_id),))

                result = cur.fetchone()

                if not result:
                    raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

                rule_info = {
                    "rule_id": result[0],
                    "name": result[1],
                    "content_path": result[2],
                    "department": result[3],
                    "established_date": result[4],
                    "last_revised_date": result[5],
                    "publication_no": result[6]
                }

                # content_path가 있는 경우 JSON 파일 읽기
                content_data = None
                if rule_info["content_path"]:
                    json_path = os.path.join(settings.FASTAPI_DIR, rule_info["content_path"])

                    if os.path.exists(json_path):
                        try:
                            with open(json_path, 'r', encoding='utf-8') as f:
                                json_data = json.load(f)

                            # JSON 데이터 파싱
                            content_data = {
                                "document_info": json_data.get("문서정보", {}),
                                "articles": json_data.get("조문내용", []),
                                "full_text": format_articles_to_html(json_data.get("조문내용", []))
                            }
                        except Exception as e:
                            logger.error(f"Error reading JSON file {json_path}: {e}")
                            content_data = {
                                "error": "조문 파일을 읽을 수 없습니다.",
                                "path": rule_info["content_path"]
                            }
                    else:
                        content_data = {
                            "error": "조문 파일이 존재하지 않습니다.",
                            "path": rule_info["content_path"]
                        }

                # 🆕 조회 로그 기록 (비동기, 실패해도 무시)
                try:
                    await log_regulation_view(
                        rule_id=rule_info["rule_id"],
                        rule_name=rule_info["name"],
                        rule_pubno=rule_info["publication_no"]
                    )
                except Exception as log_error:
                    # 로그 실패해도 메인 기능은 정상 작동
                    logger.warning(f"View log failed (ignored): {log_error}")

                return {
                    "success": True,
                    "rule": rule_info,
                    "content": content_data
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting regulation content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def format_articles_to_html(articles):
    """조문 리스트를 HTML 형식으로 변환"""
    if not articles:
        return "<p>조문 내용이 없습니다.</p>"

    html = []

    for article in articles:
        if isinstance(article, dict):
            level = article.get('레벨', 0)
            content = article.get('내용', '')
            number = article.get('번호', '')
            images = article.get('관련이미지', [])

            # 레벨에 따른 들여쓰기 스타일
            padding_left = level * 20

            # 제목인 경우 (레벨 0이고 번호가 없는 경우)
            if level == 0 and not number:
                html.append(f'<h3 style="margin-top: 20px; margin-bottom: 10px;">{content}</h3>')
            else:
                # 번호가 있는 경우 번호 포함
                if number:
                    full_content = f"{number} {content}"
                else:
                    full_content = content

                # 레벨에 따른 스타일 적용
                if level == 1:
                    html.append(f'<p style="margin-left: {padding_left}px; margin-top: 10px; font-weight: bold;">{full_content}</p>')
                else:
                    html.append(f'<p style="margin-left: {padding_left}px; margin-top: 5px;">{full_content}</p>')

            # 이미지가 있는 경우 추가
            if images:
                for img in images:
                    if isinstance(img, dict) and 'url' in img:
                        html.append(f'<img src="{img["url"]}" style="max-width: 100%; margin: 10px {padding_left}px;" />')
                    elif isinstance(img, str):
                        html.append(f'<img src="{img}" style="max-width: 100%; margin: 10px {padding_left}px;" />')

        elif isinstance(article, str):
            # 단순 문자열인 경우
            html.append(f'<p>{article}</p>')

    return '\n'.join(html)


@router.get("/content-preview/{rule_id}")
async def get_regulation_preview(
    rule_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """규정 조문 미리보기 (요약)"""
    try:
        # 전체 내용 가져오기
        full_content = await get_regulation_content(rule_id, user)

        if full_content["success"] and full_content["content"]:
            content = full_content["content"]

            # 미리보기용 요약 생성
            preview = {
                "rule": full_content["rule"],
                "summary": {
                    "total_articles": len(content.get("articles", [])) if "articles" in content else 0,
                    "document_info": content.get("document_info", {}),
                    "first_articles": content.get("articles", [])[:5] if "articles" in content else [],  # 처음 5개 조문만
                    "has_more": len(content.get("articles", [])) > 5 if "articles" in content else False
                }
            }

            return {
                "success": True,
                "preview": preview
            }

        return full_content

    except Exception as e:
        logger.error(f"Error getting regulation preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-classification/{chapter_id}")
async def get_regulations_by_classification(
    chapter_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """특정 분류(장)의 규정 목록 조회"""
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
                # 해당 장의 규정 목록 조회
                cur.execute("""
                    SELECT
                        wzruleseq,
                        wzname,
                        wzpubno,
                        wzmgrdptnm,
                        wzestabdate,
                        wzlastrevdate,
                        wzcontent_path
                    FROM wz_rule
                    WHERE wzpubno LIKE %s
                    ORDER BY wzpubno
                """, (f'{chapter_id}.%',))

                results = cur.fetchall()

                regulations = []
                for row in results:
                    regulations.append({
                        "rule_id": row[0],
                        "name": row[1],
                        "publication_no": row[2],
                        "department": row[3],
                        "established_date": row[4],
                        "last_revised_date": row[5],
                        "content_path": row[6]
                    })

                return {
                    "success": True,
                    "chapter_id": chapter_id,
                    "regulations": regulations,
                    "count": len(regulations)
                }

    except Exception as e:
        logger.error(f"Error getting regulations by classification: {e}")
        raise HTTPException(status_code=500, detail=str(e))