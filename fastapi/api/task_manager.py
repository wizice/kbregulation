#!/usr/bin/env python3
"""
백그라운드 작업 관리자
파일 파싱과 같은 장시간 실행되는 작업을 비동기로 처리
"""

import asyncio
import json
import uuid
import time
import queue
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import traceback
from app_logger import get_logger

logger = get_logger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Task:
    def __init__(self, task_id: str, task_type: str, params: Dict[str, Any]):
        self.task_id = task_id
        self.task_type = task_type
        self.params = params
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.progress = 0
        self.result = None
        self.error = None
        self.message = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error
        }

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        # ThreadPoolExecutor 추가 (CPU 집약적 작업용)
        self.thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ParseWorker")
        # 진행률 업데이트용 큐
        self.progress_queues: Dict[str, queue.Queue] = {}

    def register_handler(self, task_type: str, handler: Callable):
        """작업 타입별 핸들러 등록"""
        self.task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")

    def create_task(self, task_type: str, params: Dict[str, Any]) -> str:
        """새 작업 생성"""
        task_id = str(uuid.uuid4())
        task = Task(task_id, task_type, params)
        self.tasks[task_id] = task

        # 진행률 업데이트용 큐 생성
        self.progress_queues[task_id] = queue.Queue()

        logger.info(f"Created task {task_id} of type {task_type}")
        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """작업 정보 조회"""
        return self.tasks.get(task_id)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """작업 상태 조회"""
        task = self.get_task(task_id)
        return task.to_dict() if task else None

    async def execute_task(self, task_id: str):
        """작업 실행 (ThreadPoolExecutor 사용)"""
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        if task.task_type not in self.task_handlers:
            logger.error(f"No handler for task type: {task.task_type}")
            task.status = TaskStatus.FAILED
            task.error = f"No handler for task type: {task.task_type}"
            return

        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            task.message = "작업 실행 중..."

            logger.info(f"Starting task {task_id} in ThreadPoolExecutor")

            # 진행률 모니터링을 위한 백그라운드 태스크 시작
            monitor_task = asyncio.create_task(self._monitor_progress(task_id))

            # ThreadPoolExecutor에서 핸들러 실행
            loop = asyncio.get_event_loop()
            handler = self.task_handlers[task.task_type]
            result = await loop.run_in_executor(self.thread_pool, handler, task, self.progress_queues[task_id])

            # 진행률 모니터링 중지
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 100
            task.result = result
            task.message = "작업 완료"

            logger.info(f"Task {task_id} completed successfully in thread")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = str(e)
            task.message = f"작업 실패: {str(e)}"

            logger.error(f"Task {task_id} failed: {e}")
            logger.error(traceback.format_exc())

        finally:
            # 진행률 큐 정리
            if task_id in self.progress_queues:
                del self.progress_queues[task_id]

            # 실행 중인 작업 목록에서 제거
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

    async def start_task(self, task_id: str):
        """작업 비동기 시작"""
        if task_id in self.running_tasks:
            logger.warning(f"Task {task_id} is already running")
            return

        # 백그라운드에서 실행
        task_coroutine = asyncio.create_task(self.execute_task(task_id))
        self.running_tasks[task_id] = task_coroutine

        logger.info(f"Started background task {task_id}")

    def update_task_progress(self, task_id: str, progress: int, message: str = ""):
        """작업 진행률 업데이트 (메인 스레드에서 호출)"""
        task = self.get_task(task_id)
        if task:
            task.progress = progress
            task.message = message
            logger.debug(f"Task {task_id} progress: {progress}% - {message}")

    async def _monitor_progress(self, task_id: str):
        """스레드에서 오는 진행률 업데이트를 모니터링"""
        try:
            progress_queue = self.progress_queues.get(task_id)
            if not progress_queue:
                return

            while True:
                try:
                    # 0.1초마다 큐 확인
                    await asyncio.sleep(0.1)

                    # 큐에서 진행률 업데이트 가져오기
                    while not progress_queue.empty():
                        try:
                            task_id_from_queue, progress, message = progress_queue.get_nowait()

                            # 에러 상태 처리
                            if progress == -1:
                                task = self.get_task(task_id)
                                if task:
                                    task.status = TaskStatus.FAILED
                                    task.error = message
                                    task.message = message
                                    logger.error(f"Task {task_id} failed: {message}")
                                return

                            # 정상 진행률 업데이트
                            self.update_task_progress(task_id_from_queue, progress, message)

                        except queue.Empty:
                            break

                except asyncio.CancelledError:
                    # 작업 완료시 취소됨
                    break

        except Exception as e:
            logger.error(f"Progress monitoring failed for task {task_id}: {e}")

    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """완료된 작업 정리"""
        current_time = datetime.now()
        to_remove = []

        for task_id, task in self.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                if task.completed_at:
                    age_hours = (current_time - task.completed_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        to_remove.append(task_id)

        for task_id in to_remove:
            del self.tasks[task_id]
            logger.info(f"Cleaned up old task {task_id}")

        return len(to_remove)

# 전역 작업 관리자 인스턴스
task_manager = TaskManager()

def get_task_manager() -> TaskManager:
    """작업 관리자 인스턴스 반환"""
    return task_manager