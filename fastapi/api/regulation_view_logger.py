# -*- coding: utf-8 -*-
"""
    regulation_view_logger.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    내규 조회 통계 로깅 모듈

    특징:
    - 개인정보 저장 안함 (IP, User-Agent, 사용자 정보 제외)
    - 순수 유입량 집계용
    - 비동기 처리로 메인 로직 무영향
    - 실패해도 예외 발생 안함 (silent fail)

    :copyright: (c) 2025 by wizice.
    :license: wizice.com
"""

import asyncio
from typing import Optional
from datetime import datetime
import logging

from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)


async def log_regulation_view(
    rule_id: int,
    rule_name: str,
    rule_pubno: str
) -> None:
    """
    내규 조회 로그 기록 (비동기)

    Args:
        rule_id: 내규 ID (wz_rule.wzruleseq)
        rule_name: 내규 명칭
        rule_pubno: 공포번호 (예: 1.1.1)

    Returns:
        None (실패해도 예외 발생 안함)

    Example:
        await log_regulation_view(
            rule_id=8902,
            rule_name="1.1.1. 정확한 환자 확인",
            rule_pubno="1.1.1"
        )
    """
    try:
        # DB 설정
        db_config = {
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'host': settings.DB_HOST,
            'port': settings.DB_PORT
        }

        # 비동기 DB 연결 (백그라운드 처리)
        db_manager = DatabaseConnectionManager(**db_config)

        # 로그 INSERT
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO regulation_view_logs
                        (rule_id, rule_name, rule_pubno, viewed_at)
                    VALUES
                        (%s, %s, %s, NOW())
                """, (rule_id, rule_name, rule_pubno))

                conn.commit()

        # 디버그 로그 (개발 환경에서만)
        if settings.debug:
            logger.debug(
                f"✅ View logged: rule_id={rule_id}, "
                f"name={rule_name}, pubno={rule_pubno}"
            )

    except Exception as e:
        # 로깅 실패해도 메인 로직에 영향 없음
        # 경고 로그만 남기고 조용히 실패
        logger.warning(f"⚠️ View log failed (ignored): {e}")
        # 예외를 다시 발생시키지 않음 (silent fail)
        pass


def log_regulation_view_sync(
    rule_id: int,
    rule_name: str,
    rule_pubno: str
) -> None:
    """
    내규 조회 로그 기록 (동기 버전)

    Args:
        rule_id: 내규 ID
        rule_name: 내규 명칭
        rule_pubno: 공포번호

    Note:
        동기 환경에서 사용 시 (비추천, 성능 이슈)
        가능하면 비동기 버전 사용 권장
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
                cur.execute("""
                    INSERT INTO regulation_view_logs
                        (rule_id, rule_name, rule_pubno, viewed_at)
                    VALUES
                        (%s, %s, %s, NOW())
                """, (rule_id, rule_name, rule_pubno))

                conn.commit()

        if settings.debug:
            logger.debug(f"✅ View logged (sync): rule_id={rule_id}")

    except Exception as e:
        logger.warning(f"⚠️ View log failed (sync, ignored): {e}")
        pass


async def get_view_count(rule_id: int) -> Optional[int]:
    """
    특정 내규의 조회수 조회

    Args:
        rule_id: 내규 ID

    Returns:
        조회수 (실패 시 None)

    Example:
        count = await get_view_count(8902)
        print(f"조회수: {count}")
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
                cur.execute("""
                    SELECT COUNT(*) AS view_count
                    FROM regulation_view_logs
                    WHERE rule_id = %s
                """, (rule_id,))

                result = cur.fetchone()
                return result[0] if result else 0

    except Exception as e:
        logger.error(f"Error getting view count: {e}")
        return None


async def get_total_views() -> Optional[int]:
    """
    전체 내규 조회수 합계

    Returns:
        전체 조회수 (실패 시 None)
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
                cur.execute("SELECT COUNT(*) FROM regulation_view_logs")
                result = cur.fetchone()
                return result[0] if result else 0

    except Exception as e:
        logger.error(f"Error getting total views: {e}")
        return None


# 모듈 테스트용 (직접 실행 시)
if __name__ == "__main__":
    import asyncio

    async def test():
        print("🧪 Testing regulation_view_logger module...")

        # 테스트 로그 기록
        await log_regulation_view(
            rule_id=8902,
            rule_name="1.1.1. 정확한 환자 확인",
            rule_pubno="1.1.1"
        )

        # 조회수 확인
        count = await get_view_count(8902)
        print(f"✅ Test log recorded. View count: {count}")

        # 전체 조회수
        total = await get_total_views()
        print(f"✅ Total views: {total}")

    # 테스트 실행
    asyncio.run(test())
