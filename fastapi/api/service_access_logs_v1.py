"""
접속 로그 API 라우터 (psycopg2 기반)
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from api.auth_middleware import require_role
from api import query_access_logs_v1 as query

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/access-logs",
    tags=["access-logs"]
)


@router.get("/logs")
def get_access_logs_endpoint(
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    user_id: Optional[str] = Query(None, description="사용자 ID"),
    ip_address: Optional[str] = Query(None, description="IP 주소"),
    path_filter: Optional[str] = Query(None, description="경로 필터"),
    limit: int = Query(100, description="조회 개수"),
    offset: int = Query(0, description="오프셋"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """접속 로그 조회 (관리자 전용)"""
    try:
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        logs = query.get_access_logs(
            start_date=start,
            end_date=end,
            user_id=user_id,
            ip_address=ip_address,
            path_filter=path_filter,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "data": logs,
            "count": len(logs)
        }
    except Exception as e:
        logger.error(f"Failed to get access logs: {e}")
        raise HTTPException(status_code=500, detail="접속 로그 조회 실패")


@router.get("/stats/hourly")
def get_hourly_stats(
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """시간대별 접속 통계 (관리자 전용)"""
    try:
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        stats = query.get_access_stats_by_hour(start_date=start, end_date=end)

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get hourly stats: {e}")
        raise HTTPException(status_code=500, detail="시간대별 통계 조회 실패")


@router.get("/stats/daily")
def get_daily_stats(
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """일별 접속 통계 (관리자 전용)"""
    try:
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        stats = query.get_access_stats_by_day(start_date=start, end_date=end)

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get daily stats: {e}")
        raise HTTPException(status_code=500, detail="일별 통계 조회 실패")


@router.get("/stats/pages")
def get_top_pages(
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    limit: int = Query(10, description="조회 개수"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """인기 페이지 통계 (관리자 전용)"""
    try:
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        stats = query.get_top_pages(start_date=start, end_date=end, limit=limit)

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get top pages: {e}")
        raise HTTPException(status_code=500, detail="인기 페이지 통계 조회 실패")


@router.get("/stats/devices")
def get_device_stats(
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """디바이스별 통계 (관리자 전용)"""
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
    """브라우저별 통계 (관리자 전용)"""
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
    days: int = Query(7, description="조회 기간 (일)"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """접속 통계 요약 (관리자 전용)"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 통계 조회
        daily_stats = query.get_access_stats_by_day(start_date, end_date)
        device_stats = query.get_device_stats(start_date, end_date)
        browser_stats = query.get_browser_stats(start_date, end_date)
        top_pages = query.get_top_pages(start_date, end_date, limit=5)

        # 총 방문자 수 계산
        total_visits = sum(day['visit_count'] for day in daily_stats)
        total_unique_ips = sum(day['unique_ips'] for day in daily_stats)

        return {
            "success": True,
            "data": {
                "period": {
                    "start": start_date.strftime('%Y-%m-%d'),
                    "end": end_date.strftime('%Y-%m-%d'),
                    "days": days
                },
                "summary": {
                    "total_visits": total_visits,
                    "total_unique_ips": total_unique_ips,
                    "avg_daily_visits": total_visits // days if days > 0 else 0
                },
                "daily_stats": daily_stats,
                "device_stats": device_stats,
                "browser_stats": browser_stats,
                "top_pages": top_pages
            }
        }
    except Exception as e:
        logger.error(f"Failed to get stats summary: {e}")
        raise HTTPException(status_code=500, detail="통계 요약 조회 실패")
