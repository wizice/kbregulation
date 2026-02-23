"""
접속 로그 미들웨어
- 비동기 처리로 응답 속도에 영향 없음
- 선택적 로깅 (정적 파일 제외)
- User-Agent 파싱
"""

import time
import re
from datetime import datetime
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
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

# 로깅 제외할 경로 패턴
EXCLUDE_PATHS = [
    '/static/',
    '/favicon.ico',
    '/health',
    '/api/v1/monitor/health',
    '/_health',
]

# 로깅 제외할 파일 확장자
EXCLUDE_EXTENSIONS = [
    '.js', '.css', '.png', '.jpg', '.jpeg',
    '.gif', '.ico', '.svg', '.woff', '.woff2', '.ttf'
]


def should_log_request(path: str) -> bool:
    """
    로깅 대상인지 판단
    - 정적 파일 제외
    - 헬스체크 제외
    """
    # 제외 경로 체크
    for exclude_path in EXCLUDE_PATHS:
        if path.startswith(exclude_path):
            return False

    # 제외 확장자 체크
    for ext in EXCLUDE_EXTENSIONS:
        if path.endswith(ext):
            return False

    return True


def parse_user_agent(user_agent: str) -> dict:
    """
    User-Agent 문자열 파싱
    간단한 정규식 기반 파싱 (외부 라이브러리 불필요)
    """
    if not user_agent:
        return {
            'device_type': 'Unknown',
            'browser': 'Unknown',
            'os': 'Unknown'
        }

    ua_lower = user_agent.lower()

    # 디바이스 타입 감지
    if 'mobile' in ua_lower or 'android' in ua_lower or 'iphone' in ua_lower:
        device_type = 'Mobile'
    elif 'tablet' in ua_lower or 'ipad' in ua_lower:
        device_type = 'Tablet'
    else:
        device_type = 'PC'

    # 브라우저 감지
    if 'edg' in ua_lower:
        browser = 'Edge'
    elif 'chrome' in ua_lower and 'edg' not in ua_lower:
        browser = 'Chrome'
    elif 'firefox' in ua_lower:
        browser = 'Firefox'
    elif 'safari' in ua_lower and 'chrome' not in ua_lower:
        browser = 'Safari'
    elif 'msie' in ua_lower or 'trident' in ua_lower:
        browser = 'IE'
    else:
        browser = 'Other'

    # OS 감지
    if 'windows' in ua_lower:
        os = 'Windows'
    elif 'mac os' in ua_lower or 'macos' in ua_lower:
        os = 'macOS'
    elif 'linux' in ua_lower:
        os = 'Linux'
    elif 'android' in ua_lower:
        os = 'Android'
    elif 'ios' in ua_lower or 'iphone' in ua_lower or 'ipad' in ua_lower:
        os = 'iOS'
    else:
        os = 'Other'

    return {
        'device_type': device_type,
        'browser': browser,
        'os': os
    }


async def save_access_log(log_data: dict):
    """
    접속 로그를 DB에 저장 (비동기)
    """
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                INSERT INTO access_logs (
                    timestamp, user_id, user_name, ip_address,
                    method, path, query_string, referrer,
                    user_agent, device_type, browser, os,
                    status_code, response_time_ms, session_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """

            cursor.execute(
                query,
                (
                    log_data['timestamp'],
                    log_data.get('user_id'),
                    log_data.get('user_name'),
                    log_data['ip_address'],
                    log_data['method'],
                    log_data['path'],
                    log_data.get('query_string'),
                    log_data.get('referrer'),
                    log_data.get('user_agent'),
                    log_data['device_type'],
                    log_data['browser'],
                    log_data['os'],
                    log_data['status_code'],
                    log_data['response_time_ms'],
                    log_data.get('session_id')
                )
            )

            conn.commit()
            cursor.close()

    except Exception as e:
        logger.error(f"Failed to save access log: {e}")
        # 로그 저장 실패해도 요청 처리는 계속됨


class AccessLoggerMiddleware(BaseHTTPMiddleware):
    """
    접속 로그 미들웨어
    - 비동기 처리로 응답 지연 없음
    - 선택적 로깅
    """

    async def dispatch(self, request: Request, call_next):
        # 시작 시간 기록
        start_time = time.time()

        # 요청 처리
        response: Response = await call_next(request)

        # 응답 시간 계산
        response_time_ms = int((time.time() - start_time) * 1000)

        # 로깅 대상 체크
        if not should_log_request(request.url.path):
            return response

        # 로그 데이터 수집
        try:
            # IP 주소 추출 (프록시 환경 고려)
            ip_address = request.headers.get('X-Forwarded-For',
                                            request.headers.get('X-Real-IP',
                                            request.client.host if request.client else 'Unknown'))
            if ',' in ip_address:
                ip_address = ip_address.split(',')[0].strip()

            # User-Agent 파싱
            user_agent = request.headers.get('User-Agent', '')
            ua_info = parse_user_agent(user_agent)

            # 사용자 정보 (세션에서 추출)
            user_id = None
            user_name = None
            session_id = None

            if hasattr(request.state, 'user') and request.state.user:
                user_id = request.state.user.get('user_id')
                user_name = request.state.user.get('name')

            # 세션 ID (쿠키에서 추출)
            session_cookie = request.cookies.get('session_token')
            if session_cookie:
                session_id = session_cookie[:50]  # 길이 제한

            # 쿼리 문자열
            query_string = str(request.url.query) if request.url.query else None

            # Referer
            referrer = request.headers.get('Referer')

            # 로그 데이터 구성
            log_data = {
                'timestamp': datetime.now(),
                'user_id': user_id,
                'user_name': user_name,
                'ip_address': ip_address,
                'method': request.method,
                'path': request.url.path,
                'query_string': query_string,
                'referrer': referrer,
                'user_agent': user_agent[:500] if user_agent else None,  # 길이 제한
                'device_type': ua_info['device_type'],
                'browser': ua_info['browser'],
                'os': ua_info['os'],
                'status_code': response.status_code,
                'response_time_ms': response_time_ms,
                'session_id': session_id
            }

            # 비동기로 로그 저장 (응답에 영향 없음)
            import asyncio
            asyncio.create_task(save_access_log(log_data))

        except Exception as e:
            logger.error(f"Error in access logger middleware: {e}")

        return response
