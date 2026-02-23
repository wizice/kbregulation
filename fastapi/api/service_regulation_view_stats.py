# -*- coding: utf-8 -*-
"""
    service_regulation_view_stats.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    내규 조회 통계 API

    기능:
    - 조회수 TOP 10
    - 일별 조회 통계
    - 시간대별 조회 분포
    - 특정 내규 조회 추이

    :copyright: (c) 2025 by wizice.
    :license: wizice.com
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from .auth_middleware import get_current_user, require_role
from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/admin/view-stats",
    tags=["view-stats"],
    responses={404: {"description": "Not found"}},
)


@router.get("/top")
async def get_top_viewed_regulations(
    limit: int = Query(default=10, ge=1, le=100, description="조회 건수"),
    start_date: Optional[str] = Query(default=None, description="시작일 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="종료일 (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    조회수 TOP N 내규 목록

    Args:
        limit: 조회 건수 (기본 10, 최대 100)
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)

    Returns:
        조회수 상위 내규 목록
    """
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
                # 날짜 범위 조건 추가
                if start_date and end_date:
                    cur.execute("""
                        SELECT
                            rule_id,
                            rule_name,
                            rule_pubno,
                            COUNT(*) as view_count,
                            MAX(viewed_at) as last_viewed_at
                        FROM regulation_view_logs
                        WHERE DATE(viewed_at) >= %s AND DATE(viewed_at) <= %s
                        GROUP BY rule_id, rule_name, rule_pubno
                        ORDER BY view_count DESC, last_viewed_at DESC
                        LIMIT %s
                    """, (start_date, end_date, limit))
                else:
                    cur.execute("""
                        SELECT
                            rule_id,
                            rule_name,
                            rule_pubno,
                            COUNT(*) as view_count,
                            MAX(viewed_at) as last_viewed_at
                        FROM regulation_view_logs
                        GROUP BY rule_id, rule_name, rule_pubno
                        ORDER BY view_count DESC, last_viewed_at DESC
                        LIMIT %s
                    """, (limit,))

                results = cur.fetchall()

                data = []
                for i, row in enumerate(results, 1):
                    data.append({
                        "rank": i,
                        "rule_id": row[0],
                        "rule_name": row[1],
                        "rule_pubno": row[2],
                        "view_count": row[3],
                        "last_viewed_at": row[4].isoformat() if row[4] else None
                    })

                return {
                    "success": True,
                    "data": data,
                    "total": len(data)
                }

    except Exception as e:
        logger.error(f"Error getting top viewed regulations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily")
async def get_daily_view_stats(
    days: int = Query(default=30, ge=1, le=365, description="조회 기간 (일)"),
    start_date: Optional[str] = Query(default=None, description="시작일 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="종료일 (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    일별 조회 통계

    Args:
        days: 조회 기간 (기본 30일, 최대 365일) - start_date/end_date 없을 때 사용
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)

    Returns:
        일별 조회수 집계
    """
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
                # 날짜 범위 조건 추가
                if start_date and end_date:
                    cur.execute("""
                        SELECT
                            DATE(viewed_at) as view_date,
                            COUNT(*) as total_views,
                            COUNT(DISTINCT rule_id) as unique_regulations
                        FROM regulation_view_logs
                        WHERE DATE(viewed_at) >= %s AND DATE(viewed_at) <= %s
                        GROUP BY DATE(viewed_at)
                        ORDER BY view_date DESC
                    """, (start_date, end_date))
                else:
                    cur.execute("""
                        SELECT
                            DATE(viewed_at) as view_date,
                            COUNT(*) as total_views,
                            COUNT(DISTINCT rule_id) as unique_regulations
                        FROM regulation_view_logs
                        WHERE viewed_at >= NOW() - INTERVAL '%s days'
                        GROUP BY DATE(viewed_at)
                        ORDER BY view_date DESC
                    """, (days,))

                results = cur.fetchall()

                data = []
                for row in results:
                    data.append({
                        "date": row[0].isoformat(),
                        "total_views": row[1],
                        "unique_regulations": row[2]
                    })

                return {
                    "success": True,
                    "data": data,
                    "period_days": days,
                    "total_days": len(data)
                }

    except Exception as e:
        logger.error(f"Error getting daily view stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hourly")
async def get_hourly_view_distribution(
    start_date: Optional[str] = Query(default=None, description="시작일 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="종료일 (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    시간대별 조회 분포 (0~23시)

    Args:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)

    Returns:
        시간대별 조회수
    """
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
                # 날짜 범위 조건 추가
                if start_date and end_date:
                    cur.execute("""
                        SELECT
                            EXTRACT(HOUR FROM viewed_at) as hour,
                            COUNT(*) as views
                        FROM regulation_view_logs
                        WHERE DATE(viewed_at) >= %s AND DATE(viewed_at) <= %s
                        GROUP BY EXTRACT(HOUR FROM viewed_at)
                        ORDER BY hour
                    """, (start_date, end_date))
                else:
                    cur.execute("""
                        SELECT
                            EXTRACT(HOUR FROM viewed_at) as hour,
                            COUNT(*) as views
                        FROM regulation_view_logs
                        GROUP BY EXTRACT(HOUR FROM viewed_at)
                        ORDER BY hour
                    """)

                results = cur.fetchall()

                data = []
                for row in results:
                    data.append({
                        "hour": int(row[0]),
                        "views": row[1]
                    })

                return {
                    "success": True,
                    "data": data
                }

    except Exception as e:
        logger.error(f"Error getting hourly view distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detail/{rule_id}")
async def get_regulation_view_detail(
    rule_id: int,
    days: int = Query(default=30, ge=1, le=365, description="조회 기간 (일)"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    특정 내규 조회 상세 통계

    Args:
        rule_id: 내규 ID
        days: 조회 기간 (기본 30일)

    Returns:
        특정 내규의 조회 추이 및 통계
    """
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
                # 내규 정보 및 총 조회수
                cur.execute("""
                    SELECT
                        rule_name,
                        rule_pubno,
                        COUNT(*) as total_views,
                        MIN(viewed_at) as first_viewed_at,
                        MAX(viewed_at) as last_viewed_at
                    FROM regulation_view_logs
                    WHERE rule_id = %s
                    GROUP BY rule_name, rule_pubno
                """, (rule_id,))

                summary = cur.fetchone()

                if not summary:
                    return {
                        "success": False,
                        "error": "조회 기록이 없습니다."
                    }

                # 일별 조회 추이
                cur.execute("""
                    SELECT
                        DATE(viewed_at) as view_date,
                        COUNT(*) as views
                    FROM regulation_view_logs
                    WHERE rule_id = %s
                      AND viewed_at >= NOW() - INTERVAL '%s days'
                    GROUP BY DATE(viewed_at)
                    ORDER BY view_date DESC
                """, (rule_id, days))

                daily_trend = []
                for row in cur.fetchall():
                    daily_trend.append({
                        "date": row[0].isoformat(),
                        "views": row[1]
                    })

                return {
                    "success": True,
                    "rule_id": rule_id,
                    "rule_name": summary[0],
                    "rule_pubno": summary[1],
                    "total_views": summary[2],
                    "first_viewed_at": summary[3].isoformat() if summary[3] else None,
                    "last_viewed_at": summary[4].isoformat() if summary[4] else None,
                    "daily_trend": daily_trend
                }

    except Exception as e:
        logger.error(f"Error getting regulation view detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_view_stats_summary(
    start_date: Optional[str] = Query(default=None, description="시작일 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="종료일 (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    전체 통계 요약

    Args:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)

    Returns:
        전체 조회수, 내규 수, 평균 조회수 등
    """
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
                # 날짜 범위 조건
                date_condition = ""
                date_params = ()
                if start_date and end_date:
                    date_condition = "WHERE DATE(viewed_at) >= %s AND DATE(viewed_at) <= %s"
                    date_params = (start_date, end_date)

                # 전체 통계 (선택한 기간)
                if date_condition:
                    cur.execute(f"""
                        SELECT
                            COUNT(*) as total_views,
                            COUNT(DISTINCT rule_id) as unique_regulations,
                            MIN(viewed_at) as first_view,
                            MAX(viewed_at) as last_view
                        FROM regulation_view_logs
                        {date_condition}
                    """, date_params)
                else:
                    cur.execute("""
                        SELECT
                            COUNT(*) as total_views,
                            COUNT(DISTINCT rule_id) as unique_regulations,
                            MIN(viewed_at) as first_view,
                            MAX(viewed_at) as last_view
                        FROM regulation_view_logs
                    """)

                stats = cur.fetchone()

                # 오늘 조회수
                cur.execute("""
                    SELECT COUNT(*) FROM regulation_view_logs
                    WHERE DATE(viewed_at) = CURRENT_DATE
                """)

                today_views = cur.fetchone()[0]

                # 이번 주 조회수
                cur.execute("""
                    SELECT COUNT(*) FROM regulation_view_logs
                    WHERE viewed_at >= DATE_TRUNC('week', CURRENT_DATE)
                """)

                week_views = cur.fetchone()[0]

                return {
                    "success": True,
                    "summary": {
                        "total_views": stats[0] if stats[0] else 0,
                        "unique_regulations": stats[1] if stats[1] else 0,
                        "first_view": stats[2].isoformat() if stats[2] else None,
                        "last_view": stats[3].isoformat() if stats[3] else None,
                        "today_views": today_views,
                        "week_views": week_views,
                        "avg_views_per_regulation": round(stats[0] / stats[1], 2) if stats[1] and stats[1] > 0 else 0
                    }
                }

    except Exception as e:
        logger.error(f"Error getting view stats summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_view_logs(
    confirm: bool = Query(default=False, description="삭제 확인"),
    user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    조회 로그 전체 삭제 (관리자 전용, 위험)

    Args:
        confirm: true로 설정해야 삭제됨

    Returns:
        삭제된 로그 수
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="confirm=true 파라미터가 필요합니다."
        )

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
                # 삭제 전 개수 확인
                cur.execute("SELECT COUNT(*) FROM regulation_view_logs")
                count_before = cur.fetchone()[0]

                # 전체 삭제
                cur.execute("DELETE FROM regulation_view_logs")
                conn.commit()

                logger.warning(f"⚠️  View logs cleared by admin: {count_before} records deleted")

                return {
                    "success": True,
                    "deleted_count": count_before,
                    "message": f"{count_before}건의 로그가 삭제되었습니다."
                }

    except Exception as e:
        logger.error(f"Error clearing view logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# 공개 API (인증 불필요)
# ========================================

@router.post("/public/log-view")
async def log_regulation_view_public(data: Dict[str, Any]):
    """
    서비스 페이지용 조회 로깅 API (공개)

    Args:
        data: {
            "rule_id": int,
            "rule_name": str,
            "rule_pubno": str
        }

    Returns:
        성공 여부
    """
    try:
        rule_id = data.get("rule_id")
        rule_name = data.get("rule_name")
        rule_pubno = data.get("rule_pubno")

        # 필수 파라미터 검증
        if not rule_id:
            raise HTTPException(status_code=400, detail="rule_id is required")
        if not rule_name:
            raise HTTPException(status_code=400, detail="rule_name is required")

        # DB 연결 설정
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
                cur.execute("""
                    INSERT INTO regulation_view_logs
                        (rule_id, rule_name, rule_pubno, viewed_at)
                    VALUES
                        (%s, %s, %s, NOW())
                """, (rule_id, rule_name, rule_pubno))
                conn.commit()

        logger.info(f"✅ View logged (public): {rule_name} (ID: {rule_id})")

        return {
            "success": True,
            "message": "Logged successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        # 로깅 실패해도 500 에러 대신 200으로 응답 (서비스에 영향 없도록)
        logger.warning(f"⚠️ Public view log failed (ignored): {e}")
        return {
            "success": False,
            "message": "Logging failed but ignored"
        }
