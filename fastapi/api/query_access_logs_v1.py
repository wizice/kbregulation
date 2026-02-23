"""
접속 로그 조회 쿼리 모듈 (psycopg2 기반)
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import logging

from api.timescaledb_manager_v2 import get_db_manager
from settings import settings

logger = logging.getLogger(__name__)

# DB 매니저 초기화
db_manager = get_db_manager({
    'database': settings.DB_NAME,
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD,
    'host': settings.DB_HOST,
    'port': settings.DB_PORT
})


def get_access_logs(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    path_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """접속 로그 조회"""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT id, timestamp, user_id, user_name, ip_address,
                       method, path, query_string, referrer, user_agent,
                       device_type, browser, os, status_code,
                       response_time_ms, session_id
                FROM access_logs WHERE 1=1
            """
            params = []

            if start_date:
                query += " AND timestamp >= %s"
                params.append(start_date)
            if end_date:
                query += " AND timestamp <= %s"
                params.append(end_date)
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
            if ip_address:
                query += " AND ip_address = %s"
                params.append(ip_address)
            if path_filter:
                query += " AND path LIKE %s"
                params.append(f"%{path_filter}%")

            query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            results = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                if row_dict['timestamp']:
                    row_dict['timestamp'] = row_dict['timestamp'].isoformat()
                results.append(row_dict)

            return results
        finally:
            cursor.close()


def get_access_stats_by_hour(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """시간대별 접속 통계"""
    if not start_date:
        start_date = datetime.now() - timedelta(days=7)
    if not end_date:
        end_date = datetime.now()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT date_trunc('hour', timestamp) as hour,
                       COUNT(*) as visit_count,
                       COUNT(DISTINCT ip_address) as unique_ips,
                       COUNT(DISTINCT user_id) as unique_users,
                       CAST(AVG(response_time_ms) AS INTEGER) as avg_response_time
                FROM access_logs
                WHERE timestamp >= %s AND timestamp <= %s
                GROUP BY hour
                ORDER BY hour DESC
            """
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            results = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                if row_dict['hour']:
                    row_dict['hour'] = row_dict['hour'].isoformat()
                results.append(row_dict)

            return results
        finally:
            cursor.close()


def get_access_stats_by_day(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """일별 접속 통계"""
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT date_trunc('day', timestamp) as day,
                       COUNT(*) as visit_count,
                       COUNT(DISTINCT ip_address) as unique_ips,
                       COUNT(DISTINCT user_id) as unique_users,
                       CAST(AVG(response_time_ms) AS INTEGER) as avg_response_time
                FROM access_logs
                WHERE timestamp >= %s AND timestamp <= %s
                GROUP BY day
                ORDER BY day DESC
            """
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            results = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                if row_dict['day']:
                    row_dict['day'] = row_dict['day'].strftime('%Y-%m-%d')
                results.append(row_dict)

            return results
        finally:
            cursor.close()


def get_top_pages(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """인기 페이지 통계"""
    if not start_date:
        start_date = datetime.now() - timedelta(days=7)
    if not end_date:
        end_date = datetime.now()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT path,
                       COUNT(*) as visit_count,
                       COUNT(DISTINCT ip_address) as unique_visitors
                FROM access_logs
                WHERE timestamp >= %s AND timestamp <= %s
                GROUP BY path
                ORDER BY visit_count DESC
                LIMIT %s
            """
            cursor.execute(query, (start_date, end_date, limit))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            return [dict(zip(columns, row)) for row in rows]
        finally:
            cursor.close()


def get_device_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """디바이스별 접속 통계"""
    if not start_date:
        start_date = datetime.now() - timedelta(days=7)
    if not end_date:
        end_date = datetime.now()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT device_type,
                       COUNT(*) as count,
                       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
                FROM access_logs
                WHERE timestamp >= %s AND timestamp <= %s
                GROUP BY device_type
                ORDER BY count DESC
            """
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            results = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                if row_dict.get('percentage'):
                    row_dict['percentage'] = float(row_dict['percentage'])
                results.append(row_dict)

            return results
        finally:
            cursor.close()


def get_browser_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """브라우저별 접속 통계"""
    if not start_date:
        start_date = datetime.now() - timedelta(days=7)
    if not end_date:
        end_date = datetime.now()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT browser,
                       COUNT(*) as count,
                       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
                FROM access_logs
                WHERE timestamp >= %s AND timestamp <= %s
                GROUP BY browser
                ORDER BY count DESC
            """
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            results = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                if row_dict.get('percentage'):
                    row_dict['percentage'] = float(row_dict['percentage'])
                results.append(row_dict)

            return results
        finally:
            cursor.close()
