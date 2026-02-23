#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
부서별 규정 수 테스트 스크립트

사용법: python3 test/dept_regulation_test.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings
import pandas as pd

def test_dept_regulation_counts():
    """부서별 규정 수 테스트"""

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
            print("=" * 60)
            print("부서별 규정 수 통계 테스트")
            print("=" * 60)

            # 1. 부서별 규정 수 계산
            cur.execute('''
                WITH dept_rules AS (
                    SELECT
                        unnest(string_to_array(wzmgrdptorgcd, ', ')) as dept_code
                    FROM wz_rule
                    WHERE wzmgrdptorgcd IS NOT NULL
                    AND wzmgrdptorgcd != ''
                )
                SELECT
                    dr.dept_code,
                    d.wzdeptname as dept_name,
                    COUNT(*) as count
                FROM dept_rules dr
                LEFT JOIN wz_dept d ON dr.dept_code = d.wzdeptorgcd
                GROUP BY dr.dept_code, d.wzdeptname
                ORDER BY count DESC
            ''')

            results = cur.fetchall()

            print(f"\n총 {len(results)}개 부서에 규정이 할당됨\n")

            # 상위 20개 부서 표시
            print("상위 20개 부서:")
            print("-" * 60)
            print(f"{'순위':<5} {'부서코드':<10} {'부서명':<30} {'규정 수':<10}")
            print("-" * 60)

            for i, row in enumerate(results[:20], 1):
                dept_name = row[1] if row[1] else '(미등록 부서)'
                print(f"{i:<5} {row[0]:<10} {dept_name:<30} {row[2]:<10}건")

            # 2. 전체 통계
            print("\n" + "=" * 60)
            print("전체 통계")
            print("-" * 60)

            # 전체 부서 수
            cur.execute("SELECT COUNT(*) FROM wz_dept")
            total_depts = cur.fetchone()[0]

            # 규정이 있는 부서 수
            depts_with_rules = len(results)

            # 전체 규정 수
            cur.execute("SELECT COUNT(*) FROM wz_rule WHERE wzmgrdptorgcd IS NOT NULL AND wzmgrdptorgcd != ''")
            total_rules = cur.fetchone()[0]

            print(f"전체 부서 수: {total_depts}개")
            print(f"규정이 할당된 부서: {depts_with_rules}개 ({depts_with_rules*100/total_depts:.1f}%)")
            print(f"전체 규정 수: {total_rules}개")
            print(f"부서당 평균 규정 수: {total_rules/depts_with_rules:.1f}개")

            # 3. 복수 부서 규정 분석
            print("\n" + "=" * 60)
            print("복수 부서가 관리하는 규정")
            print("-" * 60)

            cur.execute('''
                SELECT
                    wzname,
                    wzmgrdptnm,
                    wzmgrdptorgcd,
                    array_length(string_to_array(wzmgrdptorgcd, ', '), 1) as dept_count
                FROM wz_rule
                WHERE wzmgrdptorgcd LIKE '%,%'
                ORDER BY dept_count DESC
                LIMIT 10
            ''')

            multi_dept_rules = cur.fetchall()

            print(f"\n복수 부서 규정 예시 (상위 10개):")
            for row in multi_dept_rules:
                rule_name = row[0][:40] if row[0] else 'N/A'
                print(f"\n규정: {rule_name}...")
                print(f"  담당부서: {row[1]}")
                print(f"  부서코드: {row[2]}")
                print(f"  부서 수: {row[3]}개")

if __name__ == "__main__":
    try:
        test_dept_regulation_counts()
        print("\n✅ 테스트 완료")
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()