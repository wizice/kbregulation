"""
부록 파일 업로드 관리 라우터
"""
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
from api.auth_middleware import get_current_user
from api.timescaledb_manager_v2 import DatabaseConnectionManager
import os
import shutil
from pathlib import Path
import logging
from datetime import datetime
import asyncpg
import json

from settings import settings

router = APIRouter(prefix="/api/v1/appendix", tags=["appendix"])
logger = logging.getLogger(__name__)

# 부록 저장 경로 설정
APPENDIX_DIR = Path(f"{settings.APPLIB_DIR}/appendix")
APPENDIX_DIR.mkdir(parents=True, exist_ok=True)

# 기존 부록 파일 경로 (사용자 화면용)
WWW_PDF_DIR = Path(settings.WWW_STATIC_PDF_DIR)

# JSON 파일 경로 설정
JSON_DIR = Path(settings.WWW_STATIC_FILE_DIR)
SUMMARY_JSON = JSON_DIR / "summary_kbregulation.json"

# DB 연결 초기화
db_manager = DatabaseConnectionManager()

async def get_next_appendix_no(rule_id: int) -> str:
    """
    해당 규정의 다음 부록 번호 생성

    Args:
        rule_id: 규정 ID

    Returns:
        다음 부록 번호 (1, 2, 3...)
    """
    try:
        with db_manager.get_connection() as conn:
            # 현재 규정의 최대 부록 번호 조회 (숫자만)
            query = """
                SELECT COALESCE(MAX(CAST(wzappendixno AS INTEGER)), 0) + 1 as next_no
                FROM wz_appendix
                WHERE wzruleseq = %s AND wzappendixno ~ '^[0-9]+$'
            """
            cursor = conn.cursor()
            cursor.execute(query, (rule_id,))
            result = cursor.fetchone()
            return str(result[0]) if result else "1"
    except Exception as e:
        logger.error(f"[Appendix] Error getting next appendix number: {e}")
        return "1"  # 기본값

async def insert_appendix_record(appendix_data: Dict[str, Any]) -> int:
    """
    wz_appendix 테이블에 부록 정보 저장

    Args:
        appendix_data: 부록 정보

    Returns:
        생성된 wzappendixseq
    """
    try:
        with db_manager.get_connection() as conn:
            query = """
                INSERT INTO wz_appendix (wzruleseq, wzappendixno, wzappendixname, wzfiletype, wzcreatedby, wzmodifiedby, wzfilepath)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING wzappendixseq
            """
            cursor = conn.cursor()
            cursor.execute(
                query,
                (
                    appendix_data['wzruleseq'],
                    appendix_data['wzappendixno'],
                    appendix_data['wzappendixname'],
                    appendix_data['wzfiletype'],
                    appendix_data['wzcreatedby'],
                    appendix_data['wzmodifiedby'],
                    appendix_data['wzfilepath']
                )
            )
            result = cursor.fetchone()
            conn.commit()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"[Appendix] Error inserting appendix record: {e}")
        raise

async def update_appendix_filepath(wzappendixseq: int, filepath: str):
    """
    부록 파일 경로 업데이트

    Args:
        wzappendixseq: 부록 시퀀스 번호
        filepath: 파일 경로
    """
    try:
        with db_manager.get_connection() as conn:
            query = "UPDATE wz_appendix SET wzfilepath = %s WHERE wzappendixseq = %s"
            cursor = conn.cursor()
            cursor.execute(query, (filepath, wzappendixseq))
            conn.commit()
    except Exception as e:
        logger.error(f"[Appendix] Error updating appendix filepath: {e}")
        raise

async def get_rule_appendix_list(rule_id: int) -> List[Dict[str, Any]]:
    """
    특정 규정의 모든 부록 정보를 데이터베이스에서 조회

    Args:
        rule_id: 규정 ID

    Returns:
        부록 정보 리스트
    """
    try:
        with db_manager.get_connection() as conn:
            query = """
                SELECT wzappendixseq, wzappendixno, wzappendixname, wzfiletype, wzfilepath
                FROM wz_appendix
                WHERE wzruleseq = %s
                ORDER BY CAST(wzappendixno AS INTEGER)
            """
            cursor = conn.cursor()
            cursor.execute(query, (rule_id,))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"[Appendix] Error getting appendix list: {e}")
        return []

async def update_json_files(rule_id: int, wzruleid: str, wzpubno: str = None):
    """
    부록 정보를 JSON 파일에 반영

    Args:
        rule_id: 규정 ID (wzruleseq)
        wzruleid: 규정번호 (wzruleid, 예: 28)
        wzpubno: 규정번호 (예: 1.2.1)
    """
    try:
        # 1. www/static/pdf에서 부록 파일 직접 검색
        appendix_files_dict = {}  # {base_name: {date: str, full_name: str, appendix_no: str, file_path: Path}}
        files_to_delete = []  # 중복된 오래된 파일들

        if wzpubno:
            clean_pubno = wzpubno.rstrip('.')
            # 부록/별표/별첨/서식 패턴 모두 검색
            patterns = [
                f"{clean_pubno}._부록*",
                f"{clean_pubno}._별표제*",
                f"{clean_pubno}._별첨제*",
                f"{clean_pubno}._서식제*",
            ]

            all_files = []
            for pattern in patterns:
                all_files.extend(WWW_PDF_DIR.glob(pattern))

            for file_path in all_files:
                if file_path.is_file():
                    import re
                    filename = file_path.stem  # 확장자 제외
                    parts = filename.split('._')

                    appendix_no = None
                    full_name = None
                    display_name = None

                    if len(parts) >= 2:
                        part1 = parts[1]  # "부록1" 또는 "별표제1호" 등

                        # KB 패턴: "별표제1호", "별첨제1호", "서식제1호"
                        kb_match = re.match(r'(별표|별첨|서식)제(\d+)호', part1)
                        # 기존 패턴: "부록1", "부록2"
                        legacy_match = re.match(r'부록(\d+)', part1)

                        if kb_match:
                            appendix_type = kb_match.group(1)
                            appendix_num = kb_match.group(2)
                            appendix_no = f"{appendix_type}제{appendix_num}호"
                            full_name = '_'.join(parts[2:]) if len(parts) >= 3 else ''
                            title = full_name.replace('_', ' ').strip() if full_name else ''
                            if title:
                                display_name = f"{appendix_type} 제{appendix_num}호 {title}"
                            else:
                                display_name = f"{appendix_type} 제{appendix_num}호"
                        elif legacy_match:
                            appendix_no = part1
                            full_name = '_'.join(parts[2:]) if len(parts) >= 3 else ''
                        else:
                            continue

                    if appendix_no is None:
                        continue

                    # KB 패턴은 이미 display_name이 설정됨
                    if display_name:
                        key = f"{appendix_no}_{full_name}"
                        if key in appendix_files_dict:
                            files_to_delete.append(appendix_files_dict[key].get('file_path'))
                        appendix_files_dict[key] = {
                            'date': '',
                            'full_name': full_name,
                            'display_name': display_name,
                            'appendix_no': appendix_no,
                            'file_path': file_path
                        }
                        continue

                    # 기존 부록 패턴: 날짜 추출 및 display_name 생성
                    if full_name:
                        date_match = re.search(r'_(\d{6,9})개정', full_name)
                    else:
                        date_match = None

                    if date_match:
                        date_str = date_match.group(1)
                        base_name = re.sub(r'_\d{6,9}개정$', '', full_name)
                        display_name = re.sub(r'[_\s]*\d{6,8}(개정|검토|제정|수정)', '', full_name)
                        display_name = re.sub(r'[_\s]*\([\d._\s]*부록\d+[_\s]*동일\)', '', display_name)
                        display_name = display_name.rstrip('_ ').replace('_', ' ')
                        title_match = re.search(r'(?:\d+(?:\.\d+)*\.\s*부록\d+\.\s*)?(.+)$', display_name)
                        if title_match:
                            display_name = title_match.group(1).strip()

                        key = f"{appendix_no}_{base_name}"
                        if key in appendix_files_dict:
                            if date_str > appendix_files_dict[key]['date']:
                                files_to_delete.append(appendix_files_dict[key]['file_path'])
                                appendix_files_dict[key] = {
                                    'date': date_str, 'full_name': full_name,
                                    'display_name': display_name, 'appendix_no': appendix_no,
                                    'file_path': file_path
                                }
                            else:
                                files_to_delete.append(file_path)
                        else:
                            appendix_files_dict[key] = {
                                'date': date_str, 'full_name': full_name,
                                'display_name': display_name, 'appendix_no': appendix_no,
                                'file_path': file_path
                            }
                    else:
                        display_name = re.sub(r'[_\s]*\d{6,8}(개정|검토|제정|수정)', '', full_name) if full_name else ''
                        display_name = re.sub(r'[_\s]*\([\d._\s]*부록\d+[_\s]*동일\)', '', display_name)
                        display_name = display_name.rstrip('_ ').replace('_', ' ')
                        title_match = re.search(r'(?:\d+(?:\.\d+)*\.\s*부록\d+\.\s*)?(.+)$', display_name)
                        if title_match:
                            display_name = title_match.group(1).strip()

                        key = f"{appendix_no}_{full_name}"
                        if key in appendix_files_dict:
                            files_to_delete.append(appendix_files_dict[key].get('file_path'))
                        appendix_files_dict[key] = {
                            'date': '', 'full_name': full_name,
                            'display_name': display_name, 'appendix_no': appendix_no,
                            'file_path': file_path
                        }

        # 중복된 오래된 파일 삭제
        if files_to_delete:
            import os
            for old_file in files_to_delete:
                if old_file and old_file.exists():
                    try:
                        os.remove(old_file)
                        logger.info(f"[Appendix] Deleted old duplicate file: {old_file.name}")
                    except Exception as e:
                        logger.warning(f"[Appendix] Failed to delete old file {old_file.name}: {e}")

        # 최신 버전만 추출 (부록 번호 순서대로 정렬)
        import re
        sorted_items = sorted(
            appendix_files_dict.values(),
            key=lambda x: int(re.search(r'\d+', x['appendix_no']).group())
        )
        appendix_files = [item['display_name'] for item in sorted_items]

        # 중복 제거 (같은 display_name이 여러 개 있을 경우 1개만 유지)
        appendix_files = list(dict.fromkeys(appendix_files))  # 순서 유지하면서 중복 제거

        # 2. summary_kbregulation.json 업데이트 (문자열 배열로)
        if SUMMARY_JSON.exists():
            with open(SUMMARY_JSON, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)

            # 해당 규정을 찾아서 appendix 정보 업데이트
            # JSON 구조: {"KB규정": {"1편 ...": {"regulations": [...]}, ...}} 또는
            #            {"1장": {"regulations": [...]}, "2장": {...}, ...}
            updated = False
            def _find_and_update_regulation(data):
                nonlocal updated
                if isinstance(data, dict):
                    if 'regulations' in data:
                        for regulation in data['regulations']:
                            if regulation.get('code') == wzpubno.rstrip('.'):
                                regulation['appendix'] = appendix_files
                                updated = True
                                logger.info(f"[Appendix] Found regulation by code: {wzpubno}, updated appendix: {appendix_files}")
                                return
                    else:
                        for v in data.values():
                            _find_and_update_regulation(v)
                            if updated:
                                return
            _find_and_update_regulation(summary_data)

            if updated:
                with open(SUMMARY_JSON, 'w', encoding='utf-8') as f:
                    json.dump(summary_data, f, ensure_ascii=False, indent=2)

                logger.info(f"[Appendix] Updated summary_kbregulation.json with {len(appendix_files)} appendix files")
            else:
                logger.warning(f"[Appendix] Rule {wzpubno} not found in summary_kbregulation.json")
        else:
            logger.warning(f"[Appendix] Summary JSON file not found: {SUMMARY_JSON}")

        # 3. {wzruleid}.json 파일 업데이트
        rule_json_path = JSON_DIR / f"{wzruleid}.json"
        if rule_json_path.exists():
            try:
                with open(rule_json_path, 'r', encoding='utf-8') as f:
                    rule_data = json.load(f)

                # 부록 정보 업데이트 (문자열 배열로)
                rule_data['부록'] = appendix_files

                # 조문내용에서 "(부록)" 섹션 찾아서 업데이트
                if '조문내용' in rule_data:
                    articles = rule_data['조문내용']

                    # "(부록)" 제목을 가진 조문 찾기
                    appendix_section_index = None
                    for i, article in enumerate(articles):
                        if article.get('내용') == '(부록)':
                            appendix_section_index = i
                            break

                    if appendix_section_index is not None:
                        # 기존 부록 항목들 제거 (다음 섹션 전까지)
                        next_section_index = None
                        for i in range(appendix_section_index + 1, len(articles)):
                            if articles[i].get('레벨') == 1:  # 다음 제X조 찾기
                                next_section_index = i
                                break

                        # 기존 부록 항목 삭제
                        if next_section_index:
                            del articles[appendix_section_index + 1:next_section_index]
                        else:
                            del articles[appendix_section_index + 1:]

                        # 새 부록 항목 추가
                        insert_index = appendix_section_index + 1
                        base_seq = articles[appendix_section_index].get('seq', 28)

                        for idx, appendix_name in enumerate(appendix_files):
                            new_article = {
                                "seq": base_seq + 1 + idx,
                                "레벨": 2,
                                "내용": appendix_name,
                                "번호": f"{idx + 1}.",
                                "관련이미지": []
                            }
                            articles.insert(insert_index + idx, new_article)

                        # seq 번호 재조정 (부록 이후의 모든 조문)
                        offset = len(appendix_files)
                        for i in range(insert_index + len(appendix_files), len(articles)):
                            if 'seq' in articles[i]:
                                articles[i]['seq'] = base_seq + 1 + offset
                                offset += 1

                        logger.info(f"[Appendix] Updated 조문내용 in {wzruleid}.json with {len(appendix_files)} appendix items")

                with open(rule_json_path, 'w', encoding='utf-8') as f:
                    json.dump(rule_data, f, ensure_ascii=False, indent=2)

                logger.info(f"[Appendix] Updated {wzruleid}.json with {len(appendix_files)} appendix files: {appendix_files}")
            except Exception as e:
                logger.error(f"[Appendix] Failed to update {wzruleid}.json: {e}")
        else:
            logger.warning(f"[Appendix] Rule JSON file not found: {rule_json_path}")

    except Exception as e:
        logger.error(f"[Appendix] Error updating JSON files: {e}")
        # JSON 업데이트 실패는 에러를 발생시키지 않고 로그만 남김
        # (파일 업로드 자체는 성공했으므로)

@router.post("/upload/{rule_id}")
async def upload_appendix_files(
    rule_id: int,
    wzpubno: str = Form(...),
    wzruleid: str = Form(...),
    files: List[UploadFile] = File(...),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    규정에 대한 부록 파일들을 업로드

    Args:
        rule_id: 규정 ID (wzruleseq)
        wzpubno: 규정번호 (예: 1.1.1)
        wzruleid: 규정 ID (예: 28) - JSON 파일명에 사용
        files: 업로드할 파일 목록
        user: 현재 사용자 정보

    Returns:
        업로드 결과 정보
    """
    try:
        logger.info(f"[Appendix] Uploading {len(files)} files for rule {rule_id} (wzruleid: {wzruleid}, wzpubno: {wzpubno})")

        # www/static/pdf 경로 사용
        upload_dir = WWW_PDF_DIR
        upload_dir.mkdir(parents=True, exist_ok=True)

        uploaded_files = []
        failed_files = []

        # wzpubno에서 마지막 점 제거
        clean_pubno = wzpubno.rstrip('.') if wzpubno else str(rule_id)

        for file in files:
            try:
                # 1. 다음 부록 번호 생성
                appendix_no = await get_next_appendix_no(rule_id)

                # 2. 파일 정보 준비
                file_extension = Path(file.filename).suffix.lower()
                username = user.get('username', 'unknown')

                # 3. 파일명에서 부록 제목 및 부록 번호 추출
                original_path = Path(file.filename)
                file_stem = original_path.stem  # 확장자 제외한 이름

                import re
                appendix_no_from_filename = None
                kb_appendix_type = None  # 별표, 별첨, 서식

                # KB 파일명 패턴: "(N-M) 별표/별첨/서식 제X호_제목"
                kb_match = re.match(
                    r'^\(\d+-\d+\)\s*(별표|별첨|서식)\s*제(\d+)호[_\s]*(.*)',
                    file_stem
                )
                if kb_match:
                    kb_appendix_type = kb_match.group(1)
                    appendix_no_from_filename = kb_match.group(2)
                    cleaned_stem = kb_match.group(3).strip().rstrip('_') if kb_match.group(3) else ''
                    logger.info(f"[Appendix] KB pattern: {kb_appendix_type} 제{appendix_no_from_filename}호, title={cleaned_stem}")
                else:
                    # 기존 패턴: "1.2.1. 부록3. TEST 검사 목록_202501106개정"
                    appendix_match = re.search(r'부록(\d+)', file_stem)
                    if appendix_match:
                        appendix_no_from_filename = appendix_match.group(1)
                        logger.info(f"[Appendix] Legacy pattern: 부록{appendix_no_from_filename}")

                    # 원본 파일명에서 규정번호 및 부록 번호 패턴 제거
                    cleaned_stem = re.sub(r'^\d+(?:\.\d+)*\.[_\s]*부록\d+\.[_\s]*', '', file_stem)
                    if cleaned_stem == file_stem:
                        cleaned_stem = file_stem

                # 파일명에서 명시한 부록 번호가 있으면 사용, 없으면 자동 생성
                if appendix_no_from_filename:
                    appendix_no = appendix_no_from_filename

                # 새 파일명 생성
                if kb_appendix_type:
                    # KB 형식: {pubno}._별표제N호._{제목}.pdf
                    title_part = f"._{cleaned_stem.replace(' ', '_')}" if cleaned_stem else ""
                    new_filename = f"{clean_pubno}._{kb_appendix_type}제{appendix_no}호{title_part}{file_extension}"
                else:
                    # 기존 형식: {pubno}._부록N._{제목}.pdf
                    new_filename = f"{clean_pubno}._부록{appendix_no}._{cleaned_stem}{file_extension}"
                file_path = upload_dir / new_filename

                # 부록 제목 추출 (깔끔하게 정리)
                if kb_appendix_type:
                    # KB 형식: "별표 제N호 제목"
                    title = cleaned_stem.replace('_', ' ').strip()
                    if title:
                        appendix_title = f"{kb_appendix_type} 제{appendix_no}호 {title}"
                    else:
                        appendix_title = f"{kb_appendix_type} 제{appendix_no}호"
                else:
                    # 기존 형식
                    appendix_title = re.sub(r'[_\s]*\d{6,8}(개정|검토|제정)', '', cleaned_stem)
                    appendix_title = re.sub(r'[_\s]*\([\d._\s]*부록\d+[_\s]*동일\)', '', appendix_title)
                    appendix_title = appendix_title.rstrip('_ ').replace('_', ' ')

                appendix_data = {
                    'wzruleseq': rule_id,
                    'wzappendixno': appendix_no,
                    'wzappendixname': appendix_title,
                    'wzfiletype': file_extension,
                    'wzcreatedby': username,
                    'wzmodifiedby': username,
                    'wzfilepath': f'www/static/pdf/{new_filename}'
                }

                # 4. DB에 같은 부록 번호가 있는지 확인 (중복 체크)
                wzappendixseq = None
                existing_record = None

                try:
                    with db_manager.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT wzappendixseq, wzfilepath
                            FROM wz_appendix
                            WHERE wzruleseq = %s AND wzappendixno = %s
                        """, (rule_id, appendix_no))
                        existing_record = cursor.fetchone()
                except Exception as e:
                    logger.error(f"[Appendix] Error checking existing record: {e}")

                if existing_record:
                    # 같은 부록 번호가 이미 있음 → UPDATE
                    wzappendixseq = existing_record[0]
                    old_filepath = existing_record[1]

                    logger.info(f"[Appendix] Updating existing appendix: wzappendixseq={wzappendixseq}, no={appendix_no}")

                    try:
                        with db_manager.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE wz_appendix
                                SET wzappendixname = %s,
                                    wzfiletype = %s,
                                    wzmodifiedby = %s,
                                    wzfilepath = %s,
                                    wzmodifieddate = NOW()
                                WHERE wzappendixseq = %s
                            """, (
                                appendix_title,
                                file_extension,
                                username,
                                f'www/static/pdf/{new_filename}',
                                wzappendixseq
                            ))
                            conn.commit()
                            logger.info(f"[Appendix] Updated DB record: wzappendixseq={wzappendixseq}")
                    except Exception as e:
                        logger.error(f"[Appendix] Failed to update DB record: {e}")
                        raise

                    # 기존 파일이 다른 경로면 삭제
                    if old_filepath:
                        old_file = Path(old_filepath.replace('www/static/pdf/', str(WWW_PDF_DIR) + '/'))
                        if old_file.exists() and old_file != file_path:
                            try:
                                old_file.unlink()
                                logger.info(f"[Appendix] Deleted old file: {old_file}")
                            except Exception as e:
                                logger.warning(f"[Appendix] Failed to delete old file {old_file}: {e}")
                else:
                    # 새 부록 → INSERT
                    wzappendixseq = await insert_appendix_record(appendix_data)
                    logger.info(f"[Appendix] Created new appendix record: wzappendixseq={wzappendixseq}")

                # 5. 파일 저장 (DOCX/XLSX는 PDF로 변환)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"[Appendix] Deleted existing file for cache refresh: {file_path}")

                if file_extension in ('.docx', '.xlsx'):
                    # DOCX/XLSX → PDF 자동 변환
                    import tempfile
                    import subprocess
                    with tempfile.TemporaryDirectory() as tmpdir:
                        tmp_src = Path(tmpdir) / f"input{file_extension}"
                        with tmp_src.open("wb") as buffer:
                            shutil.copyfileobj(file.file, buffer)

                        # PDF 파일명으로 변경
                        pdf_filename = new_filename.rsplit('.', 1)[0] + '.pdf'
                        pdf_path = upload_dir / pdf_filename

                        if file_extension == '.docx':
                            cmd = ["libreoffice", "--headless", "--convert-to", "pdf",
                                   "--outdir", tmpdir, str(tmp_src)]
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                            tmp_pdf = Path(tmpdir) / "input.pdf"
                            if tmp_pdf.exists():
                                shutil.move(str(tmp_pdf), str(pdf_path))
                                logger.info(f"[Appendix] DOCX→PDF converted: {pdf_filename}")
                            else:
                                raise RuntimeError(f"LibreOffice 변환 실패: {result.stderr}")
                        else:
                            # XLSX → PDF (openpyxl + reportlab)
                            from applib.utils._xlsx_to_pdf import xlsx_to_pdf
                            xlsx_to_pdf(tmp_src, pdf_path)
                            logger.info(f"[Appendix] XLSX→PDF converted: {pdf_filename}")

                        # DB 경로도 PDF로 업데이트
                        new_filename = pdf_filename
                        file_path = pdf_path
                        appendix_data['wzfiletype'] = '.pdf'
                        appendix_data['wzfilepath'] = f'www/static/pdf/{pdf_filename}'
                else:
                    with file_path.open("wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)

                logger.info(f"[Appendix] File saved to: {file_path}")

                uploaded_files.append({
                    "wzappendixseq": wzappendixseq,
                    "filename": new_filename,
                    "original_name": file.filename,
                    "appendix_no": appendix_no,
                    "size": file_path.stat().st_size,
                    "path": f'www/static/pdf/{new_filename}'
                })

                logger.info(f"[Appendix] Successfully saved: {new_filename} (seq: {wzappendixseq})")

            except Exception as e:
                logger.error(f"[Appendix] Failed to save {file.filename}: {e}")
                failed_files.append({
                    "filename": file.filename,
                    "error": str(e)
                })

        # JSON 파일 업데이트 (성공한 파일이 1개 이상인 경우)
        if len(uploaded_files) > 0:
            try:
                await update_json_files(rule_id, wzruleid, wzpubno)
                logger.info(f"[Appendix] JSON files updated successfully for rule {wzruleid} (wzpubno: {wzpubno})")
            except Exception as e:
                logger.error(f"[Appendix] Failed to update JSON files: {e}")
                # JSON 업데이트 실패는 전체 프로세스를 실패시키지 않음

        # 결과 메시지 생성
        success_count = len(uploaded_files)
        fail_count = len(failed_files)

        message = f"부록 파일 업로드 완료!\n"
        message += f"✅ 성공: {success_count}개\n"
        if fail_count > 0:
            message += f"❌ 실패: {fail_count}개\n"
            for failed in failed_files:
                message += f"  - {failed['filename']}: {failed['error']}\n"

        return JSONResponse(
            content={
                "success": True,
                "rule_id": rule_id,
                "uploaded_count": success_count,
                "failed_count": fail_count,
                "uploaded_files": uploaded_files,
                "failed_files": failed_files,
                "message": message
            },
            headers={"Content-Type": "application/json"}
        )

    except Exception as e:
        logger.error(f"[Appendix] Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list/{rule_id}")
async def list_appendix_files(
    rule_id: int,
    wzpubno: str = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    특정 규정의 부록 파일 목록 조회

    Args:
        rule_id: 규정 ID
        wzpubno: 규정번호 (옵션)
        user: 현재 사용자 정보

    Returns:
        부록 파일 목록
    """
    try:
        logger.info(f"[Appendix Admin] list_appendix_files called - rule_id: {rule_id}, wzpubno: {wzpubno}")
        files = []

        # 1. 먼저 데이터베이스에서 부록 정보 조회
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT
                        wzappendixseq,
                        wzappendixno,
                        wzappendixname,
                        wzfiletype,
                        wzfilepath,
                        wzcreateddate,
                        wzmodifieddate
                    FROM wz_appendix
                    WHERE wzruleseq = %s
                    ORDER BY CAST(wzappendixno AS INTEGER)
                """
                cur.execute(query, (rule_id,))
                rows = cur.fetchall()

                logger.info(f"[Appendix Admin] Found {len(rows)} files in database for rule_id {rule_id}")

                for row in rows:
                    appendix_seq, appendix_no, appendix_name, file_type, file_path, created_date, modified_date = row

                    # 실제 파일 경로 확인
                    actual_file_path = WWW_PDF_DIR / appendix_name

                    if actual_file_path.exists():
                        stat = actual_file_path.stat()
                        files.append({
                            "wzappendixseq": appendix_seq,
                            "filename": appendix_name,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "path": f"www/static/pdf/{appendix_name}",
                            "source": "database"
                        })
                        logger.info(f"[Appendix Admin] Added from DB: {appendix_name}")
                    else:
                        # 파일이 없어도 DB 레코드는 표시
                        files.append({
                            "wzappendixseq": appendix_seq,
                            "filename": appendix_name,
                            "size": 0,
                            "modified": modified_date.isoformat() if modified_date else created_date.isoformat() if created_date else datetime.now().isoformat(),
                            "path": f"www/static/pdf/{appendix_name}",
                            "source": "database",
                            "missing": True
                        })
                        logger.warning(f"[Appendix Admin] File missing on disk: {appendix_name}")

        # 2. applib/appendix 경로도 확인 (레거시)
        if wzpubno:
            safe_pubno = wzpubno.replace(".", "_")
            rule_appendix_dir = APPENDIX_DIR / safe_pubno
        else:
            rule_appendix_dir = APPENDIX_DIR / str(rule_id)

        logger.info(f"[Appendix Admin] Checking applib path: {rule_appendix_dir}, exists: {rule_appendix_dir.exists()}")

        if rule_appendix_dir.exists():
            for file_path in rule_appendix_dir.iterdir():
                if file_path.is_file():
                    # DB에 없는 파일만 추가
                    if not any(f['filename'] == file_path.name for f in files):
                        stat = file_path.stat()
                        files.append({
                            "filename": file_path.name,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "path": str(file_path.relative_to(APPENDIX_DIR.parent.parent)),
                            "source": "applib"
                        })
                        logger.info(f"[Appendix Admin] Added from applib: {file_path.name}")

        logger.info(f"[Appendix Admin] Total files found: {len(files)}")
        return JSONResponse(
            content={
                "success": True,
                "rule_id": rule_id,
                "files": sorted(files, key=lambda x: x["filename"]),
                "total_count": len(files)
            },
            headers={"Content-Type": "application/json"}
        )

    except Exception as e:
        logger.error(f"[Appendix] List error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{rule_id}/{filename}")
async def delete_appendix_file(
    rule_id: int,
    filename: str,
    wzpubno: str = None,
    wzruleid: str = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    특정 부록 파일 삭제

    Args:
        rule_id: 규정 ID (wzruleseq)
        filename: 삭제할 파일명
        wzpubno: 규정번호 (옵션)
        wzruleid: 규정 ID (옵션) - JSON 파일 업데이트용
        user: 현재 사용자 정보

    Returns:
        삭제 결과
    """
    try:
        # 1. 파일 경로 찾기 (www/static/pdf에서)
        file_path = WWW_PDF_DIR / filename

        if not file_path.exists():
            # applib/appendix에서도 찾아보기 (백업)
            if wzpubno:
                safe_pubno = wzpubno.replace(".", "_")
                file_path = APPENDIX_DIR / safe_pubno / filename
            else:
                file_path = APPENDIX_DIR / str(rule_id) / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {filename}")

        # 2. 데이터베이스에서 부록 레코드 찾아서 삭제
        try:
            with db_manager.get_connection() as conn:
                # 파일명으로 레코드 찾기
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM wz_appendix WHERE wzruleseq = %s AND wzfilepath LIKE %s",
                    (rule_id, f'%{filename}%')
                )
                deleted_count = cursor.rowcount
                conn.commit()
                if deleted_count > 0:
                    logger.info(f"[Appendix] Deleted {deleted_count} DB record(s) for file: {filename}")
                else:
                    logger.warning(f"[Appendix] No DB record found for file: {filename}")
        except Exception as e:
            logger.error(f"[Appendix] Failed to delete DB record: {e}")

        # 3. 파일 삭제
        file_path.unlink()
        logger.info(f"[Appendix] Deleted file: {file_path}")

        # 4. JSON 파일 업데이트
        if wzruleid and wzpubno:
            try:
                await update_json_files(rule_id, wzruleid, wzpubno)
                logger.info(f"[Appendix] JSON files updated after deletion for rule {wzruleid}")
            except Exception as e:
                logger.error(f"[Appendix] Failed to update JSON files after deletion: {e}")

        return JSONResponse(
            content={
                "success": True,
                "message": f"부록 파일이 삭제되었습니다: {filename}",
                "deleted_file": filename
            },
            headers={"Content-Type": "application/json"}
        )

    except Exception as e:
        logger.error(f"[Appendix] Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete-all/{rule_id}")
async def delete_all_appendix_files(
    rule_id: int,
    wzpubno: str = None,
    wzruleid: str = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    특정 규정의 모든 부록 파일 삭제

    Args:
        rule_id: 규정 ID (wzruleseq)
        wzpubno: 규정번호 (옵션) - JSON 업데이트용
        wzruleid: 규정 ID (옵션) - JSON 파일명에 사용
        user: 현재 사용자 정보

    Returns:
        삭제 결과
    """
    try:
        logger.info(f"[Appendix] Delete all appendices for rule {rule_id} (wzruleid: {wzruleid}, wzpubno: {wzpubno})")

        # 1. DB에서 모든 부록 레코드 삭제
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM wz_appendix WHERE wzruleseq = %s",
                    (rule_id,)
                )
                db_deleted_count = cursor.rowcount
                conn.commit()
                logger.info(f"[Appendix] Deleted {db_deleted_count} DB records for rule {rule_id}")
        except Exception as e:
            logger.error(f"[Appendix] Failed to delete DB records: {e}")
            raise

        # 2. www/static/pdf 에서 파일 삭제
        file_deleted_count = 0
        if wzpubno:
            clean_pubno = wzpubno.rstrip('.')
            # 해당 규정의 모든 PDF 파일 찾기
            import glob
            pattern = str(WWW_PDF_DIR / f"{clean_pubno}*.pdf")
            pdf_files = glob.glob(pattern)

            for pdf_path in pdf_files:
                try:
                    Path(pdf_path).unlink()
                    file_deleted_count += 1
                    logger.info(f"[Appendix] Deleted PDF file: {pdf_path}")
                except Exception as e:
                    logger.error(f"[Appendix] Failed to delete file {pdf_path}: {e}")

        # 3. applib/appendix 디렉토리도 확인 (레거시)
        if wzpubno:
            safe_pubno = wzpubno.replace(".", "_")
            rule_appendix_dir = APPENDIX_DIR / safe_pubno
        else:
            rule_appendix_dir = APPENDIX_DIR / str(rule_id)

        if rule_appendix_dir.exists():
            for file_path in rule_appendix_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()
                    file_deleted_count += 1

            # 빈 디렉토리 삭제
            if not any(rule_appendix_dir.iterdir()):
                rule_appendix_dir.rmdir()

        logger.info(f"[Appendix] Deleted {file_deleted_count} files for rule {rule_id}")

        # 4. JSON 파일 업데이트 (빈 배열로)
        if wzruleid and wzpubno:
            try:
                await update_json_files(rule_id, wzruleid, wzpubno)
                logger.info(f"[Appendix] JSON files updated after delete-all for rule {wzruleid}")
            except Exception as e:
                logger.error(f"[Appendix] Failed to update JSON files after delete-all: {e}")

        return JSONResponse(
            content={
                "success": True,
                "message": f"모든 부록이 삭제되었습니다. (DB: {db_deleted_count}개, 파일: {file_deleted_count}개)",
                "deleted_count": db_deleted_count + file_deleted_count,
                "db_deleted": db_deleted_count,
                "file_deleted": file_deleted_count
            },
            headers={"Content-Type": "application/json"}
        )

    except Exception as e:
        logger.error(f"[Appendix] Delete all error: {e}")
        raise HTTPException(status_code=500, detail=str(e))