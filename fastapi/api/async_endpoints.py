#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
비동기 작업 API 엔드포인트
파일 파싱 등 장시간 실행되는 작업을 위한 비동기 처리
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Dict, Any, Optional
import os
import tempfile
import sys
import importlib.util
import queue
from datetime import datetime

from .auth_middleware import get_current_user
from .task_manager import get_task_manager, TaskManager, Task
from .thread_workers import sync_pdf_parsing_worker, sync_docx_parsing_worker
from app_logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# 파싱 도구는 thread_workers.py에서 처리하므로 여기서는 불필요

def pdf_parsing_handler(task: Task, progress_queue: queue.Queue) -> Dict[str, Any]:
    """PDF 파싱 작업 핸들러 (ThreadPoolExecutor에서 실행)"""
    file_path = task.params.get('file_path')
    filename = task.params.get('filename', 'unknown.pdf')

    logger.info(f"[THREAD_PDF] Starting PDF parsing for {filename}")

    # ThreadPoolExecutor에서 실행되는 동기 워커 호출
    return sync_pdf_parsing_worker(task.task_id, file_path, filename, progress_queue)

def docx_parsing_handler(task: Task, progress_queue: queue.Queue) -> Dict[str, Any]:
    """DOCX 파싱 작업 핸들러 (ThreadPoolExecutor에서 실행)"""
    file_path = task.params.get('file_path')
    filename = task.params.get('filename', 'unknown.docx')
    wzruleid = task.params.get('wzruleid')  # wzruleid 추가

    logger.info(f"[THREAD_DOCX] Starting DOCX parsing for {filename}, wzruleid={wzruleid}")

    # ThreadPoolExecutor에서 실행되는 동기 워커 호출
    return sync_docx_parsing_worker(task.task_id, file_path, filename, progress_queue, wzruleid)

@router.post("/upload-pdf-async")
async def upload_pdf_async(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """PDF 파일 비동기 업로드 및 파싱"""
    try:
        task_manager = get_task_manager()

        # 파일 검증
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")

        # 임시 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # 작업 생성
        task_id = task_manager.create_task(
            task_type="pdf_parsing",
            params={
                'file_path': temp_file_path,
                'filename': filename,
                'user_id': user.get('user_id'),
                'uploaded_at': datetime.now().isoformat()
            }
        )

        # 작업 시작
        await task_manager.start_task(task_id)

        logger.info(f"Started async PDF parsing task {task_id} for {filename}")

        return {
            'success': True,
            'task_id': task_id,
            'message': 'PDF 파싱 작업이 시작되었습니다',
            'filename': filename
        }

    except Exception as e:
        logger.error(f"PDF async upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF 업로드 실패: {str(e)}")

@router.post("/upload-docx-async")
async def upload_docx_async(
    file: UploadFile = File(...),
    wzruleid: Optional[int] = Form(None),  # wzruleid 파라미터 추가
    user: Dict[str, Any] = Depends(get_current_user)
):
    """DOCX 파일 비동기 업로드 및 파싱"""
    try:
        task_manager = get_task_manager()

        # 파일 검증
        if not file.filename.lower().endswith('.docx'):
            raise HTTPException(status_code=400, detail="DOCX 파일만 업로드 가능합니다")

        # 임시 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"

        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # 작업 생성
        task_id = task_manager.create_task(
            task_type="docx_parsing",
            params={
                'file_path': temp_file_path,
                'filename': filename,
                'wzruleid': wzruleid,  # wzruleid 추가
                'user_id': user.get('user_id'),
                'uploaded_at': datetime.now().isoformat()
            }
        )

        # 작업 시작
        await task_manager.start_task(task_id)

        logger.info(f"Started async DOCX parsing task {task_id} for {filename}")

        return {
            'success': True,
            'task_id': task_id,
            'message': 'DOCX 파싱 작업이 시작되었습니다',
            'filename': filename
        }

    except Exception as e:
        logger.error(f"DOCX async upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"DOCX 업로드 실패: {str(e)}")

@router.get("/task-status/{task_id}")
async def get_task_status(
    task_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """작업 상태 조회"""
    try:
        task_manager = get_task_manager()
        status = task_manager.get_task_status(task_id)

        if not status:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

        return {
            'success': True,
            'task': status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task status query failed: {e}")
        raise HTTPException(status_code=500, detail=f"작업 상태 조회 실패: {str(e)}")

@router.get("/task-result/{task_id}")
async def get_task_result(
    task_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """작업 결과 조회"""
    try:
        task_manager = get_task_manager()
        task = task_manager.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

        if task.status.value != "completed":
            raise HTTPException(status_code=400, detail="작업이 아직 완료되지 않았습니다")

        return {
            'success': True,
            'task_id': task_id,
            'result': task.result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task result query failed: {e}")
        raise HTTPException(status_code=500, detail=f"작업 결과 조회 실패: {str(e)}")

@router.delete("/task/{task_id}")
async def cancel_task(
    task_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """작업 취소"""
    try:
        task_manager = get_task_manager()
        task = task_manager.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

        if task_id in task_manager.running_tasks:
            # 실행 중인 작업 취소
            task_manager.running_tasks[task_id].cancel()
            del task_manager.running_tasks[task_id]

        # 작업 상태 업데이트
        task.status = task_manager.TaskStatus.FAILED
        task.error = "작업이 사용자에 의해 취소되었습니다"
        task.message = "취소됨"

        logger.info(f"Task {task_id} cancelled by user")

        return {
            'success': True,
            'message': '작업이 취소되었습니다'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task cancellation failed: {e}")
        raise HTTPException(status_code=500, detail=f"작업 취소 실패: {str(e)}")

@router.post("/cleanup-tasks")
async def cleanup_tasks(
    max_age_hours: int = 24,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """완료된 작업 정리"""
    try:
        task_manager = get_task_manager()
        cleaned_count = task_manager.cleanup_completed_tasks(max_age_hours)

        return {
            'success': True,
            'cleaned_count': cleaned_count,
            'message': f'{cleaned_count}개의 오래된 작업이 정리되었습니다'
        }

    except Exception as e:
        logger.error(f"Task cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"작업 정리 실패: {str(e)}")

# 작업 핸들러 등록
def register_handlers():
    """작업 핸들러 등록"""
    task_manager = get_task_manager()
    task_manager.register_handler("pdf_parsing", pdf_parsing_handler)
    task_manager.register_handler("docx_parsing", docx_parsing_handler)