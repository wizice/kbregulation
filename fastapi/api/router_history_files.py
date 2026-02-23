"""
연혁 규정 파일 관리 라우터
- 연혁 파일 목록 조회
- 연혁 파일 다운로드
- 연혁 JSON 미리보기/수정
- 연혁 삭제
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from typing import Dict, Any, Optional
from api.auth_middleware import get_current_user, require_role
from api.timescaledb_manager_v2 import DatabaseConnectionManager
from pathlib import Path
from pydantic import BaseModel
import os
import json
import shutil
import logging
from datetime import datetime
from urllib.parse import quote


class HistoryBasicInfoUpdate(BaseModel):
    """연혁 기본정보 수정 모델"""
    wzpubno: Optional[str] = None
    wzname: Optional[str] = None
    wzestabdate: Optional[str] = None
    wzlastrevdate: Optional[str] = None
    wzexecdate: Optional[str] = None
    wznewflag: Optional[str] = None

from settings import settings

router = APIRouter(prefix="/api/v1/regulations/history", tags=["history-files"])
logger = logging.getLogger(__name__)

# 경로 설정
APPLIB_DIR = Path(settings.APPLIB_DIR)
DOCX_OLD_DIR = APPLIB_DIR / "docx_old"
PDF_OLD_DIR = APPLIB_DIR / "pdf_old"
JSON_OLD_DIR = APPLIB_DIR / "merge_json_old"

# 폴더 생성 확인
DOCX_OLD_DIR.mkdir(exist_ok=True)
PDF_OLD_DIR.mkdir(exist_ok=True)
JSON_OLD_DIR.mkdir(exist_ok=True)

# DB 연결
db_manager = DatabaseConnectionManager()


def get_history_rule(rule_id: int) -> Optional[Dict]:
    """연혁 규정 정보 조회"""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT wzruleseq, wzruleid, wzname, wzpubno,
                           wzfiledocx, wzfilepdf, wzfilejson, wzcontent_path,
                           wznewflag, wzlastrevdate, wzclosedate, wzmgrdptnm
                    FROM wz_rule
                    WHERE wzruleseq = %s
                """, (rule_id,))
                row = cur.fetchone()

                if row:
                    return {
                        'wzruleseq': row[0],
                        'wzruleid': row[1],
                        'wzname': row[2],
                        'wzpubno': row[3],
                        'wzfiledocx': row[4],
                        'wzfilepdf': row[5],
                        'wzfilejson': row[6],
                        'wzcontent_path': row[7],
                        'wznewflag': row[8],
                        'wzlastrevdate': row[9],
                        'wzclosedate': row[10],
                        'wzmgrdptnm': row[11]
                    }
                return None
    except Exception as e:
        logger.error(f"Error getting history rule: {e}")
        return None


def get_file_info(file_path: str, wzruleseq: int = None, file_type: str = None) -> Dict:
    """
    파일 정보 조회

    DB에 저장된 경로 형식: applib/{type}_old/{wzruleid}_{wzruleseq}.{ext}
    예: applib/pdf_old/7421_342.pdf
    """
    if not file_path:
        return {'exists': False, 'path': None, 'filename': None, 'size': 0}

    # 절대 경로로 변환
    if file_path.startswith('/'):
        full_path = Path(file_path)
    elif file_path.startswith('applib/'):
        # applib/pdf_old/7421_342.pdf -> /home/wizice/regulation/fastapi/applib/pdf_old/7421_342.pdf
        full_path = APPLIB_DIR.parent / file_path
    else:
        full_path = Path(file_path)

    # 파일 존재 확인
    if full_path.exists():
        stat = full_path.stat()
        return {
            'exists': True,
            'path': str(full_path),
            'filename': full_path.name,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
        }

    return {'exists': False, 'path': file_path, 'filename': None, 'size': 0}


@router.get("/{rule_id}/files")
async def get_history_files(
    rule_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    연혁 규정의 파일 목록 조회

    Args:
        rule_id: 연혁 규정 시퀀스 (wzruleseq)

    Returns:
        연혁 파일 목록 (docx, pdf, json)
    """
    try:
        rule = get_history_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        wzruleseq = rule['wzruleseq']

        return JSONResponse(content={
            "success": True,
            "rule_id": rule_id,
            "wzruleid": rule['wzruleid'],
            "rule_name": rule['wzname'],
            "wzpubno": rule['wzpubno'],
            "wznewflag": rule['wznewflag'],
            "files": {
                "docx": get_file_info(rule['wzfiledocx'], wzruleseq, 'docx'),
                "pdf": get_file_info(rule['wzfilepdf'], wzruleseq, 'pdf'),
                "json": get_file_info(rule['wzfilejson'] or rule['wzcontent_path'], wzruleseq, 'json')
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{rule_id}/download/{file_type}")
async def download_history_file(
    rule_id: int,
    file_type: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    연혁 규정 파일 다운로드

    Args:
        rule_id: 연혁 규정 시퀀스 (wzruleseq)
        file_type: 파일 종류 (docx, pdf, json)

    Returns:
        FileResponse
    """
    try:
        if file_type not in ['docx', 'pdf', 'json']:
            raise HTTPException(status_code=400, detail="잘못된 파일 타입입니다. (docx, pdf, json)")

        rule = get_history_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        wzruleseq = rule['wzruleseq']

        # 파일 경로 결정
        if file_type == 'docx':
            db_path = rule['wzfiledocx']
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif file_type == 'pdf':
            db_path = rule['wzfilepdf']
            media_type = "application/pdf"
        else:  # json
            db_path = rule['wzfilejson'] or rule['wzcontent_path']
            media_type = "application/json"

        # 다양한 경로에서 파일 찾기
        file_info = get_file_info(db_path, wzruleseq, file_type)

        if not file_info['exists']:
            raise HTTPException(status_code=404, detail=f"{file_type.upper()} 파일을 찾을 수 없습니다.")

        full_path = Path(file_info['path'])

        # 다운로드 파일명 생성
        pubno = (rule['wzpubno'] or '').replace('.', '_').rstrip('_')
        name = (rule['wzname'] or 'regulation').replace(' ', '_').replace('/', '_')
        date = (rule['wzlastrevdate'] or rule['wzclosedate'] or '').replace('.', '').replace('-', '')[:8]

        download_name = f"{pubno}_{name}_{date}.{file_type}" if date else f"{pubno}_{name}.{file_type}"

        # 파일명 인코딩
        encoded_filename = quote(download_name)

        return FileResponse(
            path=str(full_path),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading history file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{rule_id}/preview")
async def preview_history_json(
    rule_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    연혁 규정 JSON 미리보기

    Args:
        rule_id: 연혁 규정 시퀀스 (wzruleseq)

    Returns:
        JSON 데이터 (readonly)
    """
    try:
        rule = get_history_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        wzruleseq = rule['wzruleseq']
        db_path = rule['wzfilejson'] or rule['wzcontent_path']

        # 다양한 경로에서 파일 찾기
        file_info = get_file_info(db_path, wzruleseq, 'json')

        if not file_info['exists']:
            raise HTTPException(status_code=404, detail="JSON 파일을 찾을 수 없습니다.")

        full_path = Path(file_info['path'])

        # JSON 읽기
        with open(full_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        return JSONResponse(content={
            "success": True,
            "rule_id": rule_id,
            "rule_name": rule['wzname'],
            "wzpubno": rule['wzpubno'],
            "wznewflag": rule['wznewflag'],
            "readonly": rule['wznewflag'] == '연혁',
            "data": json_data
        })

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        raise HTTPException(status_code=500, detail="JSON 파일 형식 오류")
    except Exception as e:
        logger.error(f"Error previewing history JSON: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{rule_id}/content")
async def update_history_content(
    rule_id: int,
    update_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    연혁 규정 JSON 수정 (관리자 전용)

    Args:
        rule_id: 연혁 규정 시퀀스 (wzruleseq)
        update_data: {"content": {...}, "reason": "수정사유"}

    Returns:
        수정 결과
    """
    try:
        rule = get_history_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        if rule['wznewflag'] != '연혁':
            raise HTTPException(status_code=400, detail="연혁 규정만 이 API로 수정할 수 있습니다.")

        file_path = rule['wzfilejson'] or rule['wzcontent_path']

        if not file_path:
            raise HTTPException(status_code=404, detail="JSON 파일이 없습니다.")

        # 절대 경로 변환
        if file_path.startswith('applib/'):
            full_path = APPLIB_DIR.parent / file_path
        else:
            full_path = Path(file_path)

        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")

        content = update_data.get('content')
        reason = update_data.get('reason', '')

        if not content:
            raise HTTPException(status_code=400, detail="수정할 내용(content)이 없습니다.")

        # 백업 생성
        backup_path = full_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        shutil.copy2(full_path, backup_path)
        logger.info(f"Created backup: {backup_path}")

        # JSON 저장
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

        logger.info(f"Updated history JSON: {full_path}, reason: {reason}, by: {user.get('username')}")

        return JSONResponse(content={
            "success": True,
            "message": "연혁 규정이 수정되었습니다.",
            "rule_id": rule_id,
            "backup_path": str(backup_path)
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating history content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{rule_id}")
async def delete_history_regulation(
    rule_id: int,
    delete_files: bool = Query(default=True, description="파일도 함께 삭제할지 여부"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    연혁 규정 삭제 (관리자 전용)

    Args:
        rule_id: 연혁 규정 시퀀스 (wzruleseq)
        delete_files: 파일도 함께 삭제할지 여부 (기본값: True)

    Returns:
        삭제 결과
    """
    try:
        rule = get_history_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        if rule['wznewflag'] != '연혁':
            raise HTTPException(status_code=400, detail="연혁 규정만 삭제할 수 있습니다. 현행 규정은 삭제할 수 없습니다.")

        deleted_files = []
        failed_files = []

        # 파일 삭제 (옵션)
        if delete_files:
            file_paths = [
                rule['wzfiledocx'],
                rule['wzfilepdf'],
                rule['wzfilejson'] or rule['wzcontent_path']
            ]

            for file_path in file_paths:
                if file_path:
                    try:
                        if file_path.startswith('applib/'):
                            full_path = APPLIB_DIR.parent / file_path
                        else:
                            full_path = Path(file_path)

                        if full_path.exists():
                            full_path.unlink()
                            deleted_files.append(str(full_path))
                            logger.info(f"Deleted file: {full_path}")
                        else:
                            logger.warning(f"File not found (skip): {full_path}")
                    except Exception as e:
                        failed_files.append({'path': file_path, 'error': str(e)})
                        logger.error(f"Failed to delete file {file_path}: {e}")

        # DB에서 삭제
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM wz_rule
                    WHERE wzruleseq = %s AND wznewflag = '연혁'
                """, (rule_id,))

                deleted_count = cur.rowcount
                conn.commit()

        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="삭제할 연혁 규정이 없습니다.")

        logger.info(f"Deleted history regulation: {rule_id} ({rule['wzname']}), by: {user.get('username')}")

        return JSONResponse(content={
            "success": True,
            "message": f"연혁 규정이 삭제되었습니다: {rule['wzname']}",
            "rule_id": rule_id,
            "rule_name": rule['wzname'],
            "wzpubno": rule['wzpubno'],
            "deleted_files": deleted_files,
            "failed_files": failed_files
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting history regulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{rule_id}/files/{file_type}")
async def delete_history_file(
    rule_id: int,
    file_type: str,
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    연혁 규정의 특정 파일만 삭제 (관리자 전용)

    Args:
        rule_id: 연혁 규정 시퀀스 (wzruleseq)
        file_type: 파일 종류 (docx, pdf, json)

    Returns:
        삭제 결과
    """
    try:
        if file_type not in ['docx', 'pdf', 'json']:
            raise HTTPException(status_code=400, detail="잘못된 파일 타입입니다. (docx, pdf, json)")

        rule = get_history_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        if rule['wznewflag'] != '연혁':
            raise HTTPException(status_code=400, detail="연혁 규정의 파일만 삭제할 수 있습니다.")

        # 파일 경로 결정
        if file_type == 'docx':
            file_path = rule['wzfiledocx']
            db_column = 'wzfiledocx'
        elif file_type == 'pdf':
            file_path = rule['wzfilepdf']
            db_column = 'wzfilepdf'
        else:  # json
            file_path = rule['wzfilejson'] or rule['wzcontent_path']
            db_column = 'wzfilejson'

        if not file_path:
            raise HTTPException(status_code=404, detail=f"{file_type.upper()} 파일이 없습니다.")

        # 절대 경로 변환
        if file_path.startswith('applib/'):
            full_path = APPLIB_DIR.parent / file_path
        else:
            full_path = Path(file_path)

        # 파일 삭제
        if full_path.exists():
            full_path.unlink()
            logger.info(f"Deleted file: {full_path}")

        # DB 경로 NULL로 업데이트
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                if file_type == 'json':
                    cur.execute("""
                        UPDATE wz_rule
                        SET wzfilejson = NULL, wzcontent_path = NULL
                        WHERE wzruleseq = %s
                    """, (rule_id,))
                else:
                    cur.execute(f"""
                        UPDATE wz_rule
                        SET {db_column} = NULL
                        WHERE wzruleseq = %s
                    """, (rule_id,))
                conn.commit()

        logger.info(f"Deleted history file: {file_type} for rule {rule_id}, by: {user.get('username')}")

        return JSONResponse(content={
            "success": True,
            "message": f"{file_type.upper()} 파일이 삭제되었습니다.",
            "rule_id": rule_id,
            "file_type": file_type,
            "deleted_path": str(full_path)
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting history file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{rule_id}")
async def update_history_basic_info(
    rule_id: int,
    update_data: HistoryBasicInfoUpdate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    연혁 규정 기본정보 수정

    Args:
        rule_id: 연혁 규정 시퀀스 (wzruleseq)
        update_data: 수정할 기본정보

    Returns:
        수정 결과
    """
    try:
        rule = get_history_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        # 업데이트할 필드 구성
        update_fields = []
        params = []

        if update_data.wzpubno is not None:
            update_fields.append("wzpubno = %s")
            params.append(update_data.wzpubno)

        if update_data.wzname is not None:
            update_fields.append("wzname = %s")
            params.append(update_data.wzname)

        if update_data.wzestabdate is not None:
            update_fields.append("wzestabdate = %s")
            params.append(update_data.wzestabdate)

        if update_data.wzlastrevdate is not None:
            update_fields.append("wzlastrevdate = %s")
            params.append(update_data.wzlastrevdate)

        if update_data.wzexecdate is not None:
            update_fields.append("wzexecdate = %s")
            params.append(update_data.wzexecdate)

        if update_data.wznewflag is not None:
            update_fields.append("wznewflag = %s")
            params.append(update_data.wznewflag)

        if not update_fields:
            return JSONResponse(content={
                "success": True,
                "message": "변경된 내용이 없습니다.",
                "rule_id": rule_id
            })

        # 수정자 정보 추가
        update_fields.append("wzmodifiedby = %s")
        params.append(user.get('username'))

        params.append(rule_id)

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                query = f"""
                    UPDATE wz_rule
                    SET {', '.join(update_fields)}
                    WHERE wzruleseq = %s
                """
                cur.execute(query, params)
                conn.commit()

        logger.info(f"Updated history basic info: {rule_id}, by: {user.get('username')}")

        return JSONResponse(content={
            "success": True,
            "message": "저장되었습니다.",
            "rule_id": rule_id
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating history basic info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{rule_id}/upload/{file_type}")
async def upload_history_file(
    rule_id: int,
    file_type: str,
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    연혁 규정 파일 업로드/교체

    Args:
        rule_id: 연혁 규정 시퀀스 (wzruleseq)
        file_type: 파일 종류 (docx, pdf)
        file: 업로드할 파일

    Returns:
        업로드 결과
    """
    try:
        if file_type not in ['docx', 'pdf']:
            raise HTTPException(status_code=400, detail="잘못된 파일 타입입니다. (docx, pdf)")

        rule = get_history_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="규정을 찾을 수 없습니다.")

        wzruleid = rule['wzruleid']
        wzruleseq = rule['wzruleseq']

        # 파일 확장자 검증
        file_ext = file.filename.split('.')[-1].lower() if file.filename else ''
        if file_ext != file_type:
            raise HTTPException(status_code=400, detail=f"{file_type.upper()} 파일만 업로드할 수 있습니다.")

        # 대상 폴더 결정
        if file_type == 'pdf':
            target_dir = PDF_OLD_DIR
            db_column = 'wzfilepdf'
        else:  # docx
            target_dir = DOCX_OLD_DIR
            db_column = 'wzfiledocx'

        # 새 파일명: {wzruleid}_{wzruleseq}.{ext}
        new_filename = f"{wzruleid}_{wzruleseq}.{file_type}"
        target_path = target_dir / new_filename

        # 기존 파일이 있으면 백업
        if target_path.exists():
            backup_name = f"{wzruleid}_{wzruleseq}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_type}"
            backup_path = target_dir / backup_name
            shutil.move(str(target_path), str(backup_path))
            logger.info(f"Backed up existing file: {target_path} -> {backup_path}")

        # 파일 저장
        with open(target_path, 'wb') as f:
            content = await file.read()
            f.write(content)

        # DB 경로 업데이트
        relative_path = f"applib/{target_dir.name}/{new_filename}"

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE wz_rule
                    SET {db_column} = %s, wzmodifiedby = %s
                    WHERE wzruleseq = %s
                """, (relative_path, user.get('username'), rule_id))
                conn.commit()

        logger.info(f"Uploaded history file: {file_type} for rule {rule_id}, path: {target_path}, by: {user.get('username')}")

        return JSONResponse(content={
            "success": True,
            "message": f"{file_type.upper()} 파일이 업로드되었습니다.",
            "rule_id": rule_id,
            "file_type": file_type,
            "file_path": relative_path,
            "filename": new_filename
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading history file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
