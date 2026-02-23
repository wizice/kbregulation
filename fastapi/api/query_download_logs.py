"""
다운로드 이력 조회/저장 쿼리 모듈 (psycopg2 기반)
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import logging
import re

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


def parse_user_agent(user_agent: str) -> Dict[str, str]:
    """User-Agent 문자열에서 디바이스, 브라우저, OS 정보 추출"""
    if not user_agent:
        return {'device_type': 'Unknown', 'browser': 'Unknown', 'os': 'Unknown'}

    # 디바이스 타입 판별
    device_type = 'PC'
    if 'Mobile' in user_agent or 'Android' in user_agent:
        if 'Tablet' in user_agent or 'iPad' in user_agent:
            device_type = 'Tablet'
        else:
            device_type = 'Mobile'
    elif 'iPad' in user_agent:
        device_type = 'Tablet'

    # 브라우저 판별
    browser = 'Unknown'
    if 'Edg/' in user_agent:
        browser = 'Edge'
    elif 'Chrome/' in user_agent:
        browser = 'Chrome'
    elif 'Safari/' in user_agent and 'Chrome' not in user_agent:
        browser = 'Safari'
    elif 'Firefox/' in user_agent:
        browser = 'Firefox'
    elif 'MSIE' in user_agent or 'Trident/' in user_agent:
        browser = 'Internet Explorer'

    # OS 판별
    os_name = 'Unknown'
    if 'Windows NT 10' in user_agent:
        os_name = 'Windows 10/11'
    elif 'Windows NT' in user_agent:
        os_name = 'Windows'
    elif 'Mac OS X' in user_agent:
        os_name = 'macOS'
    elif 'Linux' in user_agent:
        os_name = 'Linux'
    elif 'Android' in user_agent:
        os_name = 'Android'
    elif 'iPhone' in user_agent or 'iPad' in user_agent:
        os_name = 'iOS'

    return {
        'device_type': device_type,
        'browser': browser,
        'os': os_name
    }


def insert_download_log(
    rule_id: Optional[int],
    rule_name: Optional[str],
    rule_pubno: Optional[str],
    file_type: str,
    file_name: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    referer: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> int:
    """다운로드 이력 저장"""
    try:
        # User-Agent 파싱
        ua_info = parse_user_agent(user_agent or '')

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            try:
                query = """
                    INSERT INTO regulation_download_logs
                        (rule_id, rule_name, rule_pubno, file_type, file_name,
                         ip_address, user_agent, device_type, browser, os,
                         referer, session_id, user_id, downloaded_at)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    RETURNING log_id
                """
                cursor.execute(query, (
                    rule_id, rule_name, rule_pubno, file_type, file_name,
                    ip_address, user_agent, ua_info['device_type'],
                    ua_info['browser'], ua_info['os'],
                    referer, session_id, user_id
                ))
                conn.commit()
                result = cursor.fetchone()
                log_id = result[0] if result else 0
                logger.info(f"Download log inserted: log_id={log_id}, rule_id={rule_id}, file={file_name}")
                return log_id
            finally:
                cursor.close()
    except Exception as e:
        logger.error(f"Failed to insert download log: {e}")
        return 0


def get_download_logs(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    rule_id: Optional[int] = None,
    file_type: Optional[str] = None,
    ip_address: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """다운로드 이력 조회"""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT log_id, rule_id, rule_name, rule_pubno, file_type, file_name,
                       ip_address, user_agent, device_type, browser, os,
                       referer, session_id, user_id, downloaded_at
                FROM regulation_download_logs WHERE 1=1
            """
            params = []

            if start_date:
                query += " AND downloaded_at >= %s"
                params.append(start_date)
            if end_date:
                query += " AND downloaded_at <= %s"
                params.append(end_date)
            if rule_id:
                query += " AND rule_id = %s"
                params.append(rule_id)
            if file_type:
                query += " AND file_type = %s"
                params.append(file_type)
            if ip_address:
                query += " AND ip_address = %s"
                params.append(ip_address)

            query += " ORDER BY downloaded_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            results = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                if row_dict['downloaded_at']:
                    row_dict['downloaded_at'] = row_dict['downloaded_at'].isoformat()
                results.append(row_dict)

            return results
        finally:
            cursor.close()


def get_download_count(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    rule_id: Optional[int] = None,
    file_type: Optional[str] = None,
    ip_address: Optional[str] = None
) -> int:
    """다운로드 이력 총 개수 조회"""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT COUNT(*) FROM regulation_download_logs WHERE 1=1
            """
            params = []

            if start_date:
                query += " AND downloaded_at >= %s"
                params.append(start_date)
            if end_date:
                query += " AND downloaded_at <= %s"
                params.append(end_date)
            if rule_id:
                query += " AND rule_id = %s"
                params.append(rule_id)
            if file_type:
                query += " AND file_type = %s"
                params.append(file_type)
            if ip_address:
                query += " AND ip_address = %s"
                params.append(ip_address)

            cursor.execute(query, tuple(params))
            result = cursor.fetchone()
            return result[0] if result else 0
        finally:
            cursor.close()


def get_download_stats_by_day(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """일별 다운로드 통계"""
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT date_trunc('day', downloaded_at) as day,
                       COUNT(*) as download_count,
                       COUNT(DISTINCT ip_address) as unique_visitors,
                       COUNT(DISTINCT rule_id) as rule_count
                FROM regulation_download_logs
                WHERE downloaded_at >= %s AND downloaded_at <= %s
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


def get_download_stats_by_type(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """파일 종류별 다운로드 통계"""
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT file_type,
                       COUNT(*) as download_count,
                       COUNT(DISTINCT ip_address) as unique_visitors,
                       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
                FROM regulation_download_logs
                WHERE downloaded_at >= %s AND downloaded_at <= %s
                GROUP BY file_type
                ORDER BY download_count DESC
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


def get_top_downloaded_rules(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """인기 다운로드 규정 Top N"""
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT rule_id, rule_name, rule_pubno,
                       COUNT(*) as download_count,
                       COUNT(DISTINCT ip_address) as unique_visitors,
                       MAX(downloaded_at) as last_downloaded_at
                FROM regulation_download_logs
                WHERE downloaded_at >= %s AND downloaded_at <= %s
                  AND rule_id IS NOT NULL
                GROUP BY rule_id, rule_name, rule_pubno
                ORDER BY download_count DESC
                LIMIT %s
            """
            cursor.execute(query, (start_date, end_date, limit))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            results = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                if row_dict['last_downloaded_at']:
                    row_dict['last_downloaded_at'] = row_dict['last_downloaded_at'].isoformat()
                results.append(row_dict)

            return results
        finally:
            cursor.close()


def get_device_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """디바이스별 다운로드 통계"""
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT device_type,
                       COUNT(*) as download_count,
                       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
                FROM regulation_download_logs
                WHERE downloaded_at >= %s AND downloaded_at <= %s
                GROUP BY device_type
                ORDER BY download_count DESC
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
    """브라우저별 다운로드 통계"""
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT browser,
                       COUNT(*) as download_count,
                       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
                FROM regulation_download_logs
                WHERE downloaded_at >= %s AND downloaded_at <= %s
                GROUP BY browser
                ORDER BY download_count DESC
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


def get_download_summary(days: int = 7) -> Dict[str, Any]:
    """다운로드 통계 요약"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    daily_stats = get_download_stats_by_day(start_date, end_date)
    type_stats = get_download_stats_by_type(start_date, end_date)
    top_rules = get_top_downloaded_rules(start_date, end_date, limit=10)
    device_stats = get_device_stats(start_date, end_date)
    browser_stats = get_browser_stats(start_date, end_date)

    total_downloads = sum(day['download_count'] for day in daily_stats)
    total_unique_visitors = sum(day['unique_visitors'] for day in daily_stats)

    return {
        "period": {
            "start": start_date.strftime('%Y-%m-%d'),
            "end": end_date.strftime('%Y-%m-%d'),
            "days": days
        },
        "summary": {
            "total_downloads": total_downloads,
            "total_unique_visitors": total_unique_visitors,
            "avg_daily_downloads": total_downloads // days if days > 0 else 0
        },
        "daily_stats": daily_stats,
        "type_stats": type_stats,
        "top_rules": top_rules,
        "device_stats": device_stats,
        "browser_stats": browser_stats
    }
