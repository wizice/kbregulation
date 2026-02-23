#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스레드에서 실행될 동기 작업 함수들
ThreadPoolExecutor에서 안전하게 실행되는 순수 동기 함수들
"""

import os
import sys
import importlib.util
import tempfile
from datetime import datetime
from typing import Dict, Any, Callable, Optional
import traceback
import queue
import threading

# 로거 추가
from app_logger import get_logger
logger = get_logger(__name__)

# applib 모듈 로드
applib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'applib')

# pdf2txt.py 로드
pdf2txt_spec = importlib.util.spec_from_file_location(
    "pdf2txt_local",
    os.path.join(applib_path, "pdf2txt.py")
)
pdf2txt_local = importlib.util.module_from_spec(pdf2txt_spec)
pdf2txt_spec.loader.exec_module(pdf2txt_local)

# docx2json.py 로드
docx2json_spec = importlib.util.spec_from_file_location(
    "docx2json_local",
    os.path.join(applib_path, "docx2json.py")
)
docx2json_local = importlib.util.module_from_spec(docx2json_spec)
docx2json_spec.loader.exec_module(docx2json_local)

# txt2json.py 로드
txt2json_spec = importlib.util.spec_from_file_location(
    "txt2json_local",
    os.path.join(applib_path, "txt2json.py")
)
txt2json_local = importlib.util.module_from_spec(txt2json_spec)
txt2json_spec.loader.exec_module(txt2json_local)

def sync_pdf_parsing_worker(
    task_id: str,
    file_path: str,
    filename: str,
    progress_queue: queue.Queue
) -> Dict[str, Any]:
    """
    PDF 파싱을 수행하는 동기 워커 함수
    ThreadPoolExecutor에서 안전하게 실행됨
    """
    try:
        logger.info(f"PDF 파싱 시작: {filename}")

        # 진행률 업데이트: 파일 로딩
        progress_queue.put((task_id, 10, "PDF 파일 로딩 중..."))

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {file_path}")

        # 진행률 업데이트: 텍스트 추출 시작
        progress_queue.put((task_id, 30, "PDF 텍스트 추출 중..."))

        # 진행률 업데이트: TXT 파일 생성
        progress_queue.put((task_id, 40, "TXT 파일 생성 중..."))

        # PDF에서 텍스트 추출하여 TXT 파일 생성
        txt_file_path = file_path.replace('.pdf', '.txt')
        pdf_text = pdf2txt_local.extract_text_from_pdf(file_path, txt_file_path)

        if not os.path.exists(txt_file_path):
            raise Exception("PDF에서 TXT 파일 생성에 실패했습니다")

        logger.debug(f"PDF 텍스트 추출 완료: {txt_file_path}")

        # 진행률 업데이트: JSON 변환
        progress_queue.put((task_id, 60, "JSON 변환 중..."))

        # TXT 파일 내용 읽기
        with open(txt_file_path, 'r', encoding='utf-8') as f:
            txt_content = f.read()

        # TXT 내용을 JSON으로 변환 (올바른 함수명 사용)
        json_result = txt2json_local.convert_txt_to_json(txt_content)

        logger.debug(f"JSON 변환 완료: {filename}")

        # 진행률 업데이트: 결과 정리
        progress_queue.put((task_id, 90, "결과 정리 중..."))

        # 임시 파일 정리 (PDF와 TXT 파일 모두)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(txt_file_path):
                os.remove(txt_file_path)
            logger.debug(f"임시 파일 정리 완료: {filename}")
        except Exception as cleanup_error:
            logger.warning(f"임시 파일 정리 실패: {cleanup_error}")

        # 최종 결과
        result = {
            'success': True,
            'filename': filename,
            'file_type': 'pdf',
            'json': json_result,
            'parsed_at': datetime.now().isoformat(),
            'worker_thread': threading.current_thread().name
        }

        # 완료 진행률
        progress_queue.put((task_id, 100, "PDF 파싱 완료"))

        logger.info(f"PDF 파싱 완료: {filename}")
        return result

    except Exception as e:
        error_msg = f"PDF 파싱 실패: {str(e)}"
        logger.error(f"{error_msg} (파일: {filename})")
        logger.debug(f"에러 상세:\n{traceback.format_exc()}")

        # 임시 파일 정리 (에러 시에도)
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            if 'txt_file_path' in locals() and os.path.exists(txt_file_path):
                os.remove(txt_file_path)
        except:
            pass

        # 에러 진행률 업데이트
        progress_queue.put((task_id, -1, error_msg))

        raise Exception(error_msg)

def sync_docx_parsing_worker(
    task_id: str,
    file_path: str,
    filename: str,
    progress_queue: queue.Queue,
    wzruleid: int = None  # wzruleid 파라미터 추가
) -> Dict[str, Any]:
    """
    DOCX 파싱을 수행하는 동기 워커 함수
    ThreadPoolExecutor에서 실행됨
    """
    try:
        logger.info(f"DOCX 파싱 시작: {filename} (규정ID: {wzruleid})")

        # 진행률 업데이트: 파일 로딩
        progress_queue.put((task_id, 10, "DOCX 파일 로딩 중..."))

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"DOCX 파일을 찾을 수 없습니다: {file_path}")

        # 진행률 업데이트: DOCX 파싱 시작
        progress_queue.put((task_id, 50, "DOCX 파싱 중..."))

        # DOCX 파싱 (CPU 집약적 작업) - wzruleid 전달
        docx_result = docx2json_local.process_docx_file(
            file_path=file_path,
            filename=filename,
            wzruleid=wzruleid  # wzruleid 전달
        )

        if not docx_result or not docx_result.get('success'):
            raise Exception("DOCX 파싱에 실패했습니다")

        logger.debug(f"DOCX 파싱 처리 완료: {filename}")

        # 진행률 업데이트: 결과 정리
        progress_queue.put((task_id, 90, "결과 정리 중..."))

        # 임시 파일 정리
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.debug(f"임시 파일 정리 완료: {filename}")
        except Exception as cleanup_error:
            logger.warning(f"임시 파일 정리 실패 ({filename}): {cleanup_error}")

        # 최종 결과 - docx2json.py의 실제 반환 구조 사용
        # preview_data가 전체 문서 구조를 포함
        result = {
            'success': True,
            'filename': filename,
            'file_type': 'docx',
            'json': docx_result.get('preview_data', {}),  # 전체 문서 구조
            'document_info': docx_result.get('document_info', {}),
            'sections': docx_result.get('sections', []),
            'parsed_at': datetime.now().isoformat(),
            'worker_thread': threading.current_thread().name
        }

        # 완료 진행률
        progress_queue.put((task_id, 100, "DOCX 파싱 완료"))

        logger.info(f"DOCX 파싱 완료: {filename}")
        return result

    except Exception as e:
        error_msg = f"DOCX 파싱 실패: {str(e)}"
        logger.error(f"{error_msg} (파일: {filename})")
        logger.debug(f"에러 상세:\n{traceback.format_exc()}")

        # 임시 파일 정리 (에러 시에도)
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

        # 에러 진행률 업데이트
        progress_queue.put((task_id, -1, error_msg))

        raise Exception(error_msg)