"""
다운로드 이력 관리 API 라우터
"""

from fastapi import APIRouter, Query, Depends, HTTPException, Request
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from api.auth_middleware import require_role
from api import query_download_logs as query

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/download-logs",
    tags=["download-logs"]
)


@router.get("/logs")
def get_download_logs_endpoint(
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    rule_id: Optional[int] = Query(None, description="규정 ID"),
    file_type: Optional[str] = Query(None, description="파일 종류 (pdf, docx, appendix 등)"),
    ip_address: Optional[str] = Query(None, description="IP 주소"),
    limit: int = Query(100, description="조회 개수", ge=1, le=1000),
    offset: int = Query(0, description="오프셋", ge=0),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """다운로드 이력 조회 (관리자 전용)"""
    try:
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        logs = query.get_download_logs(
            start_date=start,
            end_date=end,
            rule_id=rule_id,
            file_type=file_type,
            ip_address=ip_address,
            limit=limit,
            offset=offset
        )

        total_count = query.get_download_count(
            start_date=start,
            end_date=end,
            rule_id=rule_id,
            file_type=file_type,
            ip_address=ip_address
        )

        return {
            "success": True,
            "data": logs,
            "count": len(logs),
            "total_count": total_count
        }
    except Exception as e:
        logger.error(f"Failed to get download logs: {e}")
        raise HTTPException(status_code=500, detail="다운로드 이력 조회 실패")


@router.get("/stats/daily")
def get_daily_stats(
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """일별 다운로드 통계 (관리자 전용)"""
    try:
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        stats = query.get_download_stats_by_day(start_date=start, end_date=end)

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get daily stats: {e}")
        raise HTTPException(status_code=500, detail="일별 통계 조회 실패")


@router.get("/stats/types")
def get_type_stats(
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """파일 종류별 다운로드 통계 (관리자 전용)"""
    try:
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        stats = query.get_download_stats_by_type(start_date=start, end_date=end)

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get type stats: {e}")
        raise HTTPException(status_code=500, detail="파일 종류별 통계 조회 실패")


@router.get("/stats/top-rules")
def get_top_rules(
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    limit: int = Query(10, description="조회 개수", ge=1, le=100),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """인기 다운로드 규정 Top N (관리자 전용)"""
    try:
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        stats = query.get_top_downloaded_rules(start_date=start, end_date=end, limit=limit)

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get top rules: {e}")
        raise HTTPException(status_code=500, detail="인기 규정 통계 조회 실패")


@router.get("/stats/devices")
def get_device_stats(
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """디바이스별 다운로드 통계 (관리자 전용)"""
    try:
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        stats = query.get_device_stats(start_date=start, end_date=end)

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get device stats: {e}")
        raise HTTPException(status_code=500, detail="디바이스별 통계 조회 실패")


@router.get("/stats/browsers")
def get_browser_stats(
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """브라우저별 다운로드 통계 (관리자 전용)"""
    try:
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        stats = query.get_browser_stats(start_date=start, end_date=end)

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get browser stats: {e}")
        raise HTTPException(status_code=500, detail="브라우저별 통계 조회 실패")


@router.get("/stats/summary")
def get_stats_summary(
    days: int = Query(7, description="조회 기간 (일)", ge=1, le=365),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """다운로드 통계 요약 (관리자 전용)"""
    try:
        summary = query.get_download_summary(days=days)

        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        logger.error(f"Failed to get stats summary: {e}")
        raise HTTPException(status_code=500, detail="통계 요약 조회 실패")


# ========== 공개 API (인증 불필요) ==========

from pydantic import BaseModel

class DownloadLogRequest(BaseModel):
    """다운로드 로그 요청 모델"""
    rule_id: Optional[int] = None
    rule_name: str
    rule_pubno: Optional[str] = None
    file_type: str  # pdf, docx, appendix, viewer 등
    file_name: str


@router.post("/log")
async def log_download_public(
    log_request: DownloadLogRequest,
    request: Request
):
    """
    다운로드 이력 기록 (공개 API - 인증 불필요)

    PDF 뷰어 등 프론트엔드에서 다운로드 시 호출합니다.
    """
    try:
        # 요청에서 정보 추출
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent', '')
        referer = request.headers.get('referer', '')
        session_id = request.cookies.get('session_id', '')

        log_id = query.insert_download_log(
            rule_id=log_request.rule_id or 0,
            rule_name=log_request.rule_name,
            rule_pubno=log_request.rule_pubno or '',
            file_type=log_request.file_type,
            file_name=log_request.file_name,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
            session_id=session_id,
            user_id=None
        )

        logger.info(f"[Download Log] Logged: {log_request.file_name} (type={log_request.file_type}, id={log_id})")

        return {
            "success": True,
            "log_id": log_id,
            "message": "다운로드 이력이 기록되었습니다."
        }
    except Exception as e:
        logger.error(f"Failed to log download: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# 다운로드 로깅 헬퍼 함수 (다른 모듈에서 사용)
def log_download(request: Request, rule_id: int, rule_name: str, rule_pubno: str,
                 file_type: str, file_name: str, user_id: Optional[str] = None) -> int:
    """
    다운로드 이력 기록 헬퍼 함수

    다른 다운로드 API에서 호출하여 다운로드 이력을 기록합니다.

    Args:
        request: FastAPI Request 객체
        rule_id: 규정 ID
        rule_name: 규정명
        rule_pubno: 공포번호
        file_type: 파일 종류 (pdf, docx, appendix, comparison, history)
        file_name: 파일명
        user_id: 로그인 사용자 ID (선택)

    Returns:
        생성된 로그 ID
    """
    try:
        # 요청에서 정보 추출
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent', '')
        referer = request.headers.get('referer', '')

        # 세션 ID 추출 (쿠키에서)
        session_id = request.cookies.get('session_id', '')

        return query.insert_download_log(
            rule_id=rule_id,
            rule_name=rule_name,
            rule_pubno=rule_pubno,
            file_type=file_type,
            file_name=file_name,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
            session_id=session_id,
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"Failed to log download: {e}")
        return 0
