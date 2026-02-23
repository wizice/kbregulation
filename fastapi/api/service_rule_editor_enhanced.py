# -*- coding: utf-8 -*-
"""
Enhanced rule editor service for preserving JSON structure and filename
기존 JSON 구조와 파일명을 유지하면서 내용만 수정하는 개선된 편집 서비스
"""

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from typing import Dict, Any, Optional
import os
import json
import logging
from datetime import datetime
from pathlib import Path
import shutil
import time
import uuid
from PIL import Image

from .auth_middleware import get_current_user
from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings

router = APIRouter(
    prefix="/api/v1/rule-enhanced",
    tags=["rule-editor-enhanced"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결 설정"""
    db_config = {
        'host': settings.DB_HOST,
        'database': settings.DB_NAME,
        'user': settings.DB_USER,
        'password': settings.DB_PASSWORD,
        'port': settings.DB_PORT
    }
    return DatabaseConnectionManager(**db_config)

@router.put("/update-content")
async def update_regulation_content(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    기존 JSON 구조와 파일명을 유지하면서 규정 내용만 수정
    """
    try:
        data = await request.json()
        rule_id = data.get('wzruleseq') or data.get('rule_id')
        new_content = data.get('content_text', '')
        title = data.get('wzname', '')
        classification = data.get('wzpubno', '')
        department = data.get('wzmgrdptnm', '')
        revision_date = data.get('wzlastrevdate', '')
        execution_date = data.get('wzexecdate', '')

        if not rule_id:
            raise HTTPException(status_code=400, detail="규정 ID가 필요합니다.")

        db_manager = get_db_connection()

        # 1. 현재 규정 정보 조회 (기존 JSON 파일 경로 확인)
        query = """
            SELECT wzruleseq, wzfilejson, wzname, wzpubno, wzmgrdptnm,
                   wzestabdate, wzlastrevdate, wzexecdate, content_text
            FROM wz_rule
            WHERE wzruleseq = %s
        """

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (rule_id,))
                result = cur.fetchall()
                # Convert to dict format
                if result:
                    columns = [desc[0] for desc in cur.description]
                    result = [dict(zip(columns, row)) for row in result]
        if not result:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        current_rule = result[0]
        existing_json_path = current_rule.get('wzfilejson')

        logger.info(f"Updating rule {rule_id}, existing JSON path: {existing_json_path}")

        # 2. 기존 JSON 파일이 있는 경우 구조 유지하며 내용 업데이트
        updated_json_path = existing_json_path

        if existing_json_path and os.path.exists(existing_json_path):
            try:
                # 기존 JSON 파일 로드
                with open(existing_json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)

                logger.info(f"Loaded existing JSON structure from {existing_json_path}")

                # 문서정보 업데이트 (메타데이터)
                if '문서정보' in json_data:
                    json_data['문서정보']['규정명'] = title or current_rule.get('wzname', '')
                    json_data['문서정보']['규정표기명'] = title or current_rule.get('wzname', '')
                    json_data['문서정보']['담당부서'] = department or current_rule.get('wzmgrdptnm', '')

                    if revision_date:
                        # yyyy-mm-dd 형식을 yyyy.mm.dd. 형식으로 변환
                        formatted_date = revision_date.replace('-', '.') + '.' if revision_date else revision_date
                        json_data['문서정보']['최종개정일'] = formatted_date
                        json_data['문서정보']['최종검토일'] = formatted_date

                # 조문내용 업데이트 (새로운 내용으로 파싱, 기존 이미지 유지)
                if new_content.strip():
                    # 기존 조문 배열 가져오기 (이미지 유지용)
                    existing_articles = json_data.get('조문내용', [])

                    # 기존 이미지를 유지하면서 새 내용 파싱
                    updated_articles = parse_content_to_articles(
                        new_content,
                        title or current_rule.get('wzname', ''),
                        existing_articles
                    )
                    json_data['조문내용'] = updated_articles

                    # 조문 갯수 업데이트
                    if '문서정보' in json_data:
                        json_data['문서정보']['조문갯수'] = len(updated_articles)

                # 기존 파일에 업데이트된 내용 저장 (파일명 유지)
                with open(existing_json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)

                logger.info(f"Updated JSON content while preserving structure and filename: {existing_json_path}")

            except Exception as json_error:
                logger.error(f"Error updating JSON file: {json_error}")
                # JSON 파일 처리 실패해도 DB는 업데이트
                pass

        # 3. 데이터베이스 업데이트 (기본 정보 + 텍스트 내용)
        update_query = """
            UPDATE wz_rule
            SET wzname = %s,
                wzpubno = %s,
                wzmgrdptnm = %s,
                wzlastrevdate = %s,
                wzexecdate = %s,
                content_text = %s,
                wzmodifiedby = %s
            WHERE wzruleseq = %s
        """

        params = (
            title or current_rule.get('wzname'),
            classification or current_rule.get('wzpubno'),
            department or current_rule.get('wzmgrdptnm'),
            revision_date or current_rule.get('wzlastrevdate'),
            execution_date or current_rule.get('wzexecdate'),
            new_content,
            user.get('username', 'admin'),
            rule_id
        )

        row_count = db_manager.execute_query(update_query, params, commit=True)

        if not row_count or row_count == 0:
            raise HTTPException(status_code=500, detail="데이터베이스 업데이트 실패")

        logger.info(f"Successfully updated rule {rule_id} - preserved JSON structure and filename")

        # 4. 이미지 동기화 (fastapi -> www)
        try:
            # wzruleid 조회
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT wzruleid FROM wz_rule WHERE wzruleseq = %s", (rule_id,))
                    result = cursor.fetchone()
                    wzruleid = result[0] if result and result[0] else None

            if wzruleid:
                source_image_dirs = [
                    Path(f"{settings.FASTAPI_DIR}/static/extracted_images/{wzruleid}"),
                    Path(f"{settings.APPLIB_DIR}/static/extracted_images/{wzruleid}")
                ]
                target_image_dir = Path(f"{settings.EXTRACTED_IMAGES_DIR}/{wzruleid}")
                target_image_dir.mkdir(parents=True, exist_ok=True)

                images_synced = 0
                for source_dir in source_image_dirs:
                    if source_dir.exists():
                        for img_file in source_dir.glob('*'):
                            if img_file.is_file() and not img_file.name.startswith('.'):
                                target_file = target_image_dir / img_file.name
                                shutil.copy2(img_file, target_file)
                                images_synced += 1
                        break

                if images_synced > 0:
                    logger.info(f"✅ Synced {images_synced} images to www/static/extracted_images/{wzruleid}")
        except Exception as img_sync_error:
            logger.warning(f"⚠️ Image sync failed (continuing): {img_sync_error}")

        # 5. 색인 작업 트리거 (백그라운드)
        try:
            import threading
            from .indexing_service import index_single_regulation

            rule_name = title or current_rule.get('wzname', f"Rule_{rule_id}")

            # 백그라운드에서 색인 실행
            threading.Thread(
                target=index_single_regulation,
                args=(db_manager, rule_id, rule_name, existing_json_path),
                daemon=True
            ).start()
            logger.info(f"Indexing triggered for rule {rule_id} (update)")
        except Exception as index_error:
            logger.warning(f"Failed to trigger indexing: {index_error}")

        # 6. summary_kbregulation.json 업데이트
        try:
            update_summary_json(rule_id, title, classification, revision_date)
            logger.info(f"✅ summary_kbregulation.json updated for rule {rule_id}")
        except Exception as summary_error:
            logger.warning(f"⚠️ Summary JSON update failed (continuing): {summary_error}")

        return {
            "success": True,
            "message": "규정이 성공적으로 업데이트되었습니다.",
            "rule_id": rule_id,
            "json_path": updated_json_path,
            "preserved_structure": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating regulation content: {e}")
        raise HTTPException(status_code=500, detail=f"규정 업데이트 중 오류 발생: {str(e)}")

def parse_content_to_articles(content: str, title: str, existing_articles: list = None) -> list:
    """
    텍스트 내용을 JSON 조문 구조로 파싱
    기존 JSON 구조와 호환되는 형태로 변환

    Args:
        content: 파싱할 텍스트 내용
        title: 규정 제목
        existing_articles: 기존 조문 배열 (이미지 유지용)
    """
    articles = []
    seq = 1

    # 기존 이미지를 조문 번호별로 매핑
    existing_images_map = {}
    if existing_articles:
        for old_article in existing_articles:
            num = old_article.get('번호', '')
            if num:
                existing_images_map[num] = old_article.get('관련이미지', [])

    # 제목 추가
    articles.append({
        "seq": seq,
        "레벨": 0,
        "내용": title,
        "번호": "",
        "관련이미지": []
    })
    seq += 1

    # 내용을 줄별로 분리하여 조문으로 변환
    lines = content.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 조문 번호 패턴 감지 (제1조, 제2조 등)
        if line.startswith('제') and '조' in line:
            article_number = line.split()[0] if ' ' in line else line
            articles.append({
                "seq": seq,
                "레벨": 1,
                "내용": line,
                "번호": article_number,
                "관련이미지": existing_images_map.get(article_number, [])  # 기존 이미지 유지!
            })
        # 번호 패턴 감지 (1., 2., ①, ② 등)
        elif any(line.startswith(prefix) for prefix in ['1.', '2.', '3.', '4.', '5.', '①', '②', '③', '④', '⑤']):
            articles.append({
                "seq": seq,
                "레벨": 2,
                "내용": line,
                "번호": line.split()[0] if ' ' in line else "",
                "관련이미지": []
            })
        # 기타 내용
        else:
            articles.append({
                "seq": seq,
                "레벨": 2,
                "내용": line,
                "번호": "",
                "관련이미지": []
            })

        seq += 1

    return articles

@router.get("/backup-list/{rule_id}")
async def get_backup_list(
    rule_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """규정의 백업 파일 목록 조회"""
    try:
        db_manager = get_db_connection()

        # 현재 규정의 JSON 파일 경로 조회
        query = "SELECT wzfilejson FROM wz_rule WHERE wzruleseq = %s"
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (rule_id,))
                result = cur.fetchall()
                if result:
                    columns = [desc[0] for desc in cur.description]
                    result = [dict(zip(columns, row)) for row in result]

        if not result:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        json_path = result[0].get('wzfilejson')
        if not json_path:
            return {"backups": []}

        # 백업 파일 검색
        json_dir = os.path.dirname(json_path)
        json_filename = os.path.basename(json_path)

        backups = []
        if os.path.exists(json_dir):
            for file in os.listdir(json_dir):
                if file.startswith(json_filename) and '.backup_' in file:
                    backup_path = os.path.join(json_dir, file)
                    backup_time = file.split('.backup_')[1].replace('.json', '')

                    backups.append({
                        "filename": file,
                        "path": backup_path,
                        "timestamp": backup_time,
                        "size": os.path.getsize(backup_path)
                    })

        # 시간순 정렬 (최신순)
        backups.sort(key=lambda x: x['timestamp'], reverse=True)

        return {"backups": backups}

    except Exception as e:
        logger.error(f"Error getting backup list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-revision")
async def save_revision_content(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    개정 규정을 새 파일명으로 저장 (wzruleid 포함)
    """
    try:
        data = await request.json()
        rule_id = data.get('wzruleseq') or data.get('rule_id')
        new_content = data.get('content_text', '')
        title = data.get('wzname', '')
        classification = data.get('wzpubno', '')
        department = data.get('wzmgrdptnm', '')
        establish_date = data.get('wzestabdate', '')
        revision_date = data.get('wzlastrevdate', '')
        execution_date = data.get('wzexecdate', '')
        merged_data = data.get('merged_data', {})
        status = data.get('wzNewFlag', '현행')

        if not rule_id:
            raise HTTPException(status_code=400, detail="규정 ID가 필요합니다.")

        db_manager = get_db_connection()

        # 1. 현재 규정 정보 조회 (wzruleid 확인)
        query = """
            SELECT wzruleseq, wzruleid, wzname, wzpubno, wzmgrdptnm,
                   wzestabdate, wzlastrevdate, wzexecdate, content_text
            FROM wz_rule
            WHERE wzruleseq = %s
        """

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (rule_id,))
                result = cur.fetchall()
                if result:
                    columns = [desc[0] for desc in cur.description]
                    result = [dict(zip(columns, row)) for row in result]

        if not result:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        current_rule = result[0]
        wzruleid = current_rule.get('wzruleid')

        if not wzruleid:
            raise HTTPException(status_code=400, detail="규정에 wzruleid가 없습니다.")

        logger.info(f"Saving revision for rule {rule_id}, wzruleid: {wzruleid}")

        # 2. 새 JSON 파일 생성 (wzruleid 포함)
        from .file_utils import get_json_service_path

        # 파일명 생성: {wzruleid}_{규정명}_{timestamp}.json (병합 파일명 패턴과 일치, merged_ 제거)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')
        new_filename = f"{wzruleid}_{safe_title}_{timestamp}.json"

        new_json_absolute, new_json_relative = get_json_service_path(new_filename)

        # 3. JSON 데이터 구성
        json_data = merged_data if merged_data else {}

        # 문서정보 업데이트
        if '문서정보' not in json_data:
            json_data['문서정보'] = {}

        json_data['문서정보']['규정명'] = title
        json_data['문서정보']['규정표기명'] = title
        json_data['문서정보']['담당부서'] = department
        json_data['문서정보']['제정일'] = establish_date
        json_data['문서정보']['최종개정일'] = revision_date
        json_data['문서정보']['최종검토일'] = revision_date
        json_data['문서정보']['시행일'] = execution_date

        # 조문내용 업데이트 (기존 이미지 유지)
        if new_content.strip():
            # 기존 조문 배열 가져오기 (merged_data에서 이미지 유지용)
            existing_articles = merged_data.get('조문내용', []) if merged_data else []

            # 기존 이미지를 유지하면서 새 내용 파싱
            updated_articles = parse_content_to_articles(new_content, title, existing_articles)
            json_data['조문내용'] = updated_articles
            json_data['문서정보']['조문갯수'] = len(updated_articles)

        # 4. 새 JSON 파일 저장
        os.makedirs(os.path.dirname(new_json_absolute), exist_ok=True)
        with open(new_json_absolute, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Created new JSON file: {new_json_relative}")

        # 5. 데이터베이스 업데이트 (새 파일 경로로)
        update_query = """
            UPDATE wz_rule
            SET wzname = %s,
                wzpubno = %s,
                wzmgrdptnm = %s,
                wzestabdate = %s,
                wzlastrevdate = %s,
                wzexecdate = %s,
                content_text = %s,
                wzfilejson = %s,
                wzNewFlag = %s,
                wzmodifiedby = %s
            WHERE wzruleseq = %s
        """

        params = (
            title,
            classification,
            department,
            establish_date,
            revision_date,
            execution_date,
            new_content,
            new_json_relative,  # 새 파일 경로 (상대경로)
            status,
            user.get('username', 'admin'),
            rule_id
        )

        row_count = db_manager.execute_query(update_query, params, commit=True)

        if not row_count or row_count == 0:
            raise HTTPException(status_code=500, detail="데이터베이스 업데이트 실패")

        logger.info(f"Successfully saved revision for rule {rule_id} with new file: {new_json_relative}")

        # 색인 작업 트리거 (백그라운드)
        try:
            import threading
            from .indexing_service import index_single_regulation

            # 백그라운드에서 색인 실행
            threading.Thread(
                target=index_single_regulation,
                args=(db_manager, rule_id, title, new_json_relative),
                daemon=True
            ).start()
            logger.info(f"Indexing triggered for rule {rule_id} (save-revision)")
        except Exception as index_error:
            logger.warning(f"Failed to trigger indexing: {index_error}")

        return {
            "success": True,
            "message": "개정 규정이 성공적으로 저장되었습니다.",
            "rule_id": rule_id,
            "json_path": new_json_relative,
            "absolute_path": new_json_absolute,
            "new_file": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving revision content: {e}")
        raise HTTPException(status_code=500, detail=f"개정 규정 저장 중 오류 발생: {str(e)}")# 이미지 관리 API 엔드포인트들
# service_rule_editor_enhanced.py 파일 끝에 추가할 코드

# ==================== 이미지 관리 API ====================

def get_json_path_from_rule_id(rule_id: int) -> Optional[str]:
    """규정 ID로부터 JSON 파일 경로 조회 (최신 개정본)"""
    try:
        db_manager = get_db_connection()
        # wzruleid로 검색하되, 개정본이 여러 개일 경우 최신 것만 가져오기
        query = """
            SELECT wzfilejson
            FROM wz_rule
            WHERE wzruleid = %s
            ORDER BY wzruleseq DESC
            LIMIT 1
        """

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (rule_id,))
                result = cur.fetchone()

                if result:
                    # wzfilejson은 상대 경로이므로 절대 경로로 변환
                    relative_path = result[0]
                    if relative_path:
                        # JSON 파일은 BASE_DIR 위치에 있음 (fastapi 제외)
                        return os.path.join(settings.BASE_DIR, relative_path)

        return None
    except Exception as e:
        logger.error(f"Error getting JSON path for rule {rule_id}: {e}")
        return None


@router.post("/upload-image")
async def upload_image(
    wzruleseq: int = Form(...),
    article_seq: int = Form(...),
    image: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    이미지 업로드 및 JSON에 추가

    Args:
        wzruleseq: 규정 ID
        article_seq: 조문 seq (고유 식별자)
        image: 업로드할 이미지 파일
    """
    try:
        # 1. 파일 타입 검증
        allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif']
        if image.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식입니다. 허용: PNG, JPG, GIF"
            )

        # 2. 파일 크기 검증 (10MB)
        content = await image.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="파일 크기는 10MB 이하여야 합니다.")

        # 3. JSON 파일 경로 조회
        json_path = get_json_path_from_rule_id(wzruleseq)
        if not json_path or not os.path.exists(json_path):
            raise HTTPException(status_code=404, detail="규정의 JSON 파일을 찾을 수 없습니다.")

        # 4. 이미지 저장 디렉토리 생성 (여러 경로에 저장)
        image_dirs = [
            f"{settings.FASTAPI_DIR}/static/extracted_images/{wzruleseq}",
            f"{settings.EXTRACTED_IMAGES_DIR}/{wzruleseq}"
        ]
        for img_dir in image_dirs:
            os.makedirs(img_dir, exist_ok=True)

        # 5. 파일명 생성 (seq 기반으로 고유하게 생성)
        timestamp = int(time.time())
        file_extension = os.path.splitext(image.filename)[1] or '.png'
        filename = f"{wzruleseq}_image_seq{article_seq}_{timestamp}{file_extension}"

        # 6. 이미지 파일 저장 (모든 경로에 저장)
        for img_dir in image_dirs:
            image_path = os.path.join(img_dir, filename)
            with open(image_path, 'wb') as f:
                f.write(content)
            logger.info(f"Image saved: {image_path}")

        # 7. JSON 파일 로드
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # 8. 해당 조문 찾기 및 이미지 추가 (seq로 검색!)
        articles = json_data.get('조문내용', [])
        image_added = False

        for article in articles:
            if article.get('seq') == article_seq:
                # 관련이미지 배열에 추가
                if '관련이미지' not in article:
                    article['관련이미지'] = []

                new_seq = len(article['관련이미지']) + 1
                image_info = {
                    "seq": new_seq,
                    "file_name": filename,
                    "file_path": f"/static/extracted_images/{wzruleseq}/{filename}",
                    "title": ""
                }

                article['관련이미지'].append(image_info)
                image_added = True
                logger.info(f"Image added to article seq {article_seq} (번호: {article.get('번호')}) in JSON")
                break

        if not image_added:
            # 조문을 찾지 못한 경우 - 파일 삭제
            os.remove(image_path)
            raise HTTPException(
                status_code=404,
                detail=f"조문 seq '{article_seq}'를 찾을 수 없습니다."
            )

        # 9. JSON 파일 저장
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        logger.info(f"JSON file updated: {json_path}")

        # 10. 응답 반환
        return {
            "success": True,
            "message": "이미지가 성공적으로 업로드되었습니다.",
            "image": {
                "seq": new_seq,
                "file_name": filename,
                "file_path": f"/static/extracted_images/{wzruleseq}/{filename}",
                "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=f"이미지 업로드 중 오류 발생: {str(e)}")


@router.delete("/delete-image")
async def delete_image(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    이미지 삭제 및 JSON에서 제거

    Request body:
        {
            "wzruleseq": 9619,
            "article_seq": 21,
            "image_file_name": "9619_image_seq21_xxx.png"
        }
    """
    try:
        data = await request.json()
        wzruleseq = data.get('wzruleseq')
        article_seq = data.get('article_seq')
        image_file_name = data.get('image_file_name')

        if not all([wzruleseq, article_seq is not None, image_file_name]):
            raise HTTPException(
                status_code=400,
                detail="wzruleseq, article_seq, image_file_name이 모두 필요합니다."
            )

        # 1. JSON 파일 경로 조회
        json_path = get_json_path_from_rule_id(wzruleseq)
        if not json_path or not os.path.exists(json_path):
            raise HTTPException(status_code=404, detail="규정의 JSON 파일을 찾을 수 없습니다.")

        # 2. JSON 파일 로드
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # 3. 해당 조문에서 이미지 제거 (seq로 검색!)
        articles = json_data.get('조문내용', [])
        image_removed = False

        for article in articles:
            if article.get('seq') == article_seq:
                images = article.get('관련이미지', [])

                # 파일명이 일치하는 이미지 찾기
                for i, img in enumerate(images):
                    if img.get('file_name') == image_file_name:
                        images.pop(i)
                        image_removed = True

                        # seq 재정렬
                        for idx, img in enumerate(images):
                            img['seq'] = idx + 1

                        logger.info(f"Image '{image_file_name}' removed from article seq {article_seq} (번호: {article.get('번호')})")
                        break

                if image_removed:
                    break

        if not image_removed:
            raise HTTPException(
                status_code=404,
                detail=f"조문 seq '{article_seq}'에서 이미지 '{image_file_name}'를 찾을 수 없습니다."
            )

        # 4. JSON 파일 저장
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        # 5. 실제 이미지 파일 삭제 (모든 경로에서 백업)
        image_paths = [
            f"{settings.FASTAPI_DIR}/static/extracted_images/{wzruleseq}/{image_file_name}",
            f"{settings.EXTRACTED_IMAGES_DIR}/{wzruleseq}/{image_file_name}"
        ]

        for image_path in image_paths:
            if os.path.exists(image_path):
                # 백업 디렉토리로 이동 (완전 삭제 대신)
                backup_dir = os.path.join(os.path.dirname(image_path), '.deleted')
                os.makedirs(backup_dir, exist_ok=True)
                backup_path = os.path.join(backup_dir, image_file_name)
                shutil.move(image_path, backup_path)
                logger.info(f"Image file moved to backup: {backup_path}")

        return {
            "success": True,
            "message": "이미지가 삭제되었습니다.",
            "deleted_file": image_file_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        raise HTTPException(status_code=500, detail=f"이미지 삭제 중 오류 발생: {str(e)}")


@router.post("/resize-image")
async def resize_image(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    이미지 크기 조정 및 저장

    Request body:
        {
            "wzruleseq": 9619,
            "article_seq": 21,
            "image_file_name": "9619_image_seq21_xxx.png",
            "width": 800,  # optional
            "height": 600  # optional
        }

    Note: width와 height 중 하나만 제공하면 비율 유지
    """
    try:
        data = await request.json()
        wzruleseq = data.get('wzruleseq')
        article_seq = data.get('article_seq')
        image_file_name = data.get('image_file_name')
        target_width = data.get('width')
        target_height = data.get('height')

        if not all([wzruleseq, article_seq is not None, image_file_name]):
            raise HTTPException(
                status_code=400,
                detail="wzruleseq, article_seq, image_file_name이 모두 필요합니다."
            )

        if not target_width and not target_height:
            raise HTTPException(
                status_code=400,
                detail="width 또는 height 중 최소 하나는 제공되어야 합니다."
            )

        # 이미지 파일 경로들
        image_paths = [
            f"{settings.FASTAPI_DIR}/static/extracted_images/{wzruleseq}/{image_file_name}",
            f"{settings.EXTRACTED_IMAGES_DIR}/{wzruleseq}/{image_file_name}"
        ]

        # 첫 번째 경로에서 이미지 로드
        primary_path = image_paths[0]
        if not os.path.exists(primary_path):
            # 첫 번째 경로에 없으면 두 번째 경로 확인
            primary_path = image_paths[1]
            if not os.path.exists(primary_path):
                raise HTTPException(
                    status_code=404,
                    detail=f"이미지 파일을 찾을 수 없습니다: {image_file_name}"
                )

        # PIL로 이미지 열기
        img = Image.open(primary_path)
        original_width, original_height = img.size
        original_format = img.format  # 원본 포맷 저장 (PNG, JPEG 등)

        # 이미지 모드 확인 (RGBA, RGB 등)
        original_mode = img.mode

        # 새로운 크기 계산 (비율 유지)
        if target_width and target_height:
            # 둘 다 제공된 경우
            new_width = int(target_width)
            new_height = int(target_height)
        elif target_width:
            # width만 제공된 경우 - 비율 유지
            new_width = int(target_width)
            aspect_ratio = original_height / original_width
            new_height = int(new_width * aspect_ratio)
        else:
            # height만 제공된 경우 - 비율 유지
            new_height = int(target_height)
            aspect_ratio = original_width / original_height
            new_width = int(new_height * aspect_ratio)

        # 이미지 리사이즈 (최고품질 리샘플링)
        # LANCZOS 대신 더 최신의 고품질 알고리즘 사용
        try:
            # Pillow 10.0.0 이상에서는 Resampling.LANCZOS 사용
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except AttributeError:
            # 이전 버전 호환성
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)

        # 모든 경로에 저장
        saved_paths = []
        for path in image_paths:
            if os.path.exists(os.path.dirname(path)):
                # 원본 백업 (선택적)
                backup_dir = os.path.join(os.path.dirname(path), '.backup')
                os.makedirs(backup_dir, exist_ok=True)
                backup_path = os.path.join(backup_dir, f"{int(time.time())}_{image_file_name}")
                try:
                    if os.path.exists(path):
                        shutil.copy2(path, backup_path)
                        logger.info(f"Original image backed up: {backup_path}")
                except Exception as backup_error:
                    logger.warning(f"Failed to backup image: {backup_error}")

                # 리사이즈된 이미지 저장 (포맷별 최적 설정)
                file_ext = os.path.splitext(path)[1].lower()

                if file_ext in ['.jpg', '.jpeg']:
                    # JPEG: quality 파라미터 사용, 최고 품질
                    resized_img.save(path, 'JPEG', quality=98, optimize=True, subsampling=0)
                elif file_ext == '.png':
                    # PNG: 무손실 압축, compress_level로 속도/크기 조절 (0-9, 기본 6)
                    # compress_level을 낮추면 더 빠르지만 파일 크기가 커짐
                    resized_img.save(path, 'PNG', optimize=True, compress_level=6)
                elif file_ext == '.gif':
                    # GIF: 원본 포맷 유지
                    resized_img.save(path, 'GIF', optimize=True)
                elif file_ext == '.webp':
                    # WebP: 고품질 설정
                    resized_img.save(path, 'WEBP', quality=95, method=6)
                else:
                    # 기타: 원본 포맷 또는 PNG로 저장
                    if original_format:
                        resized_img.save(path, original_format, quality=95 if file_ext in ['.jpg', '.jpeg', '.webp'] else None)
                    else:
                        resized_img.save(path)

                saved_paths.append(path)
                logger.info(f"Resized image saved: {path} ({new_width}x{new_height}) format={file_ext}")

        return {
            "success": True,
            "message": "이미지 크기가 성공적으로 조정되었습니다.",
            "image": {
                "file_name": image_file_name,
                "original_size": {
                    "width": original_width,
                    "height": original_height
                },
                "new_size": {
                    "width": new_width,
                    "height": new_height
                },
                "saved_paths": len(saved_paths),
                "resized_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resizing image: {e}")
        raise HTTPException(status_code=500, detail=f"이미지 크기 조정 중 오류 발생: {str(e)}")


@router.get("/images/{rule_id}")
async def get_images(
    rule_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    규정의 모든 이미지 목록 조회 (조문별 그룹화)

    Returns:
        {
            "success": true,
            "rule_id": 9619,
            "images_by_article": {
                "10": [...],  # seq를 키로 사용
                "21": [...]
            },
            "total_images": 5
        }
    """
    try:
        # 1. JSON 파일 경로 조회
        json_path = get_json_path_from_rule_id(rule_id)
        logger.info(f"[get_images] Rule {rule_id} -> JSON path: {json_path}")

        if not json_path or not os.path.exists(json_path):
            logger.error(f"[get_images] JSON file not found for rule {rule_id}: {json_path}")
            raise HTTPException(status_code=404, detail="규정의 JSON 파일을 찾을 수 없습니다.")

        # 2. JSON 파일 로드
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        logger.info(f"[get_images] Loaded JSON for rule {rule_id}, keys: {list(json_data.keys())}")

        # 3. 조문별 이미지 그룹화 및 조문 목록 추출 (seq를 키로 사용)
        images_by_article = {}
        total_images = 0
        articles_list = []

        articles = json_data.get('조문내용', [])
        for article in articles:
            article_seq = article.get('seq')
            article_number = article.get('번호')
            article_content = article.get('내용', '')
            images = article.get('관련이미지', [])

            # 조문 목록에 추가 (이미지 관리 UI용) - seq 포함!
            if article_number:
                articles_list.append({
                    'seq': article_seq,  # seq 추가!
                    '번호': article_number,
                    '내용': article_content,
                    '레벨': article.get('레벨')
                })

            # 이미지가 있는 조문만 images_by_article에 추가 (seq를 키로 사용!)
            if article_seq and images:
                # 이미지에 file_path URL 추가
                for img in images:
                    # file_name에서 경로 생성
                    file_name = img.get('file_name') or img.get('파일명', '')

                    # DEBUG: Log image filename
                    logger.info(f"[get_images] Rule {rule_id}, Article seq {article_seq} (번호: {article_number}): found image '{file_name}'")

                    # file_path가 이미 JSON에 있는지 확인
                    existing_path = img.get('file_path', '')

                    if existing_path and existing_path.startswith('/static/'):
                        # JSON에 이미 올바른 경로가 있으면 그대로 사용
                        logger.info(f"[get_images] Using existing file_path from JSON: {existing_path}")
                    elif file_name and '/' not in file_name:
                        # 상대 경로가 없으면 규정별 폴더 경로 추가
                        img['file_path'] = f"/static/extracted_images/{rule_id}/{file_name}"
                        logger.info(f"[get_images] Generated file_path: {img['file_path']}")
                    elif file_name:
                        # 이미 상대 경로가 있으면 /static 추가
                        img['file_path'] = f"/static/{file_name}"
                        logger.info(f"[get_images] Using existing path: {img['file_path']}")
                    else:
                        img['file_path'] = ""
                        logger.warning(f"[get_images] Empty file_name for image in rule {rule_id}, article seq {article_seq}")

                # seq를 문자열 키로 사용!
                images_by_article[str(article_seq)] = images
                total_images += len(images)

        return {
            "success": True,
            "rule_id": rule_id,
            "articles": articles_list,  # 전체 조문 목록 (seq 포함)
            "images_by_article": images_by_article,  # seq를 키로 사용
            "total_images": total_images
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting images for rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"이미지 목록 조회 중 오류 발생: {str(e)}")


def update_summary_json(wzruleseq: int, wzname: str = None, wzpubno: str = None, wzlastrevdate: str = None):
    """
    summary_kbregulation.json 업데이트
    규정 저장 시 메타데이터를 summary JSON에 반영

    Args:
        wzruleseq: 규정 일련번호
        wzname: 규정명 (선택)
        wzpubno: 규정 코드 (선택)
        wzlastrevdate: 최종개정일 (선택)
    """
    try:
        SUMMARY_FILE = Path(f"{settings.WWW_STATIC_FILE_DIR}/summary_kbregulation.json")

        if not SUMMARY_FILE.exists():
            logger.warning(f"summary_kbregulation.json not found at {SUMMARY_FILE}")
            return

        # summary JSON 로드
        with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)

        # wzpubno로 규정 찾기
        regulation_found = False

        for chapter_key, chapter_data in summary_data.items():
            if 'regulations' not in chapter_data:
                continue

            for regulation in chapter_data['regulations']:
                # wzRuleSeq 또는 code로 매칭
                if regulation.get('wzRuleSeq') == wzruleseq or regulation.get('code') == wzpubno:
                    regulation_found = True

                    # 메타데이터 업데이트
                    if wzname:
                        regulation['name'] = wzname

                    if wzpubno:
                        regulation['code'] = wzpubno

                    # wzRuleSeq 확인
                    if 'wzRuleSeq' not in regulation or regulation['wzRuleSeq'] is None:
                        regulation['wzRuleSeq'] = wzruleseq

                    # documentInfo 업데이트
                    if 'detail' in regulation and 'documentInfo' in regulation['detail']:
                        doc_info = regulation['detail']['documentInfo']

                        if wzname:
                            doc_info['규정명'] = wzname
                            doc_info['규정표기명'] = wzname

                        if wzlastrevdate:
                            # yyyy-mm-dd → yyyy.mm.dd. 변환
                            formatted_date = wzlastrevdate.replace('-', '.') + '.' if '-' in wzlastrevdate else wzlastrevdate
                            doc_info['최종개정일'] = formatted_date
                            doc_info['최종검토일'] = formatted_date

                    # 부록 정보 동기화 (DB에서 조회)
                    try:
                        # 이미 import된 모듈 사용
                        appendix_db_config = {
                            'database': settings.DB_NAME,
                            'user': settings.DB_USER,
                            'password': settings.DB_PASSWORD,
                            'host': settings.DB_HOST,
                            'port': settings.DB_PORT
                        }
                        appendix_db_manager = DatabaseConnectionManager(**appendix_db_config)

                        with appendix_db_manager.get_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute("""
                                    SELECT wzappendixname
                                    FROM wz_appendix
                                    WHERE wzruleseq = %s
                                    ORDER BY wzappendixno
                                """, (wzruleseq,))
                                appendices = [row[0] for row in cur.fetchall()]

                                if appendices:
                                    regulation['appendix'] = appendices
                                    logger.info(f"Synced {len(appendices)} appendices for rule {wzruleseq}")
                    except Exception as appendix_error:
                        logger.warning(f"Failed to sync appendix info: {appendix_error}")

                    logger.info(f"Updated summary for rule {wzruleseq} (code: {regulation.get('code')})")
                    break

            if regulation_found:
                break

        if not regulation_found:
            logger.warning(f"Regulation wzruleseq={wzruleseq} not found in summary_kbregulation.json")
            return

        # 백업 생성
        import time
        backup_file = str(SUMMARY_FILE) + f'.backup_{int(time.time())}'
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)

        # 업데이트된 summary 저장
        with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ summary_kbregulation.json updated successfully")

    except Exception as e:
        logger.error(f"Error updating summary_kbregulation.json: {e}")
        raise
