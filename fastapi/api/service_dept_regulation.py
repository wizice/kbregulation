# -*- coding: utf-8 -*-
"""
    service_dept_regulation.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    부서별 규정 수 조회 API

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging
from .auth_middleware import get_current_user
from .timescaledb_manager_v2 import DatabaseConnectionManager
from settings import settings
from app_logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/dept",
    tags=["department"],
    responses={404: {"description": "Not found"}},
)

@router.get("/regulation-counts")
async def get_regulation_counts(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """각 부서별 규정 수 조회"""
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
                # 부서별 규정 수 계산 쿼리
                # wzmgrdptnm(부서명) 기준으로 카운트
                cur.execute("""
                    SELECT
                        wzmgrdptnm as dept_name,
                        COUNT(*) as count
                    FROM wz_rule
                    WHERE wzNewFlag = '현행'
                        AND wzmgrdptnm IS NOT NULL
                        AND wzmgrdptnm != ''
                    GROUP BY wzmgrdptnm
                    ORDER BY wzmgrdptnm
                """)

                results = cur.fetchall()

                counts = []
                for row in results:
                    counts.append({
                        "dept_name": row[0].strip() if row[0] else '',
                        "count": row[1]
                    })

                return {
                    "success": True,
                    "counts": counts,
                    "total": len(counts)
                }

    except Exception as e:
        logger.error(f"Error getting regulation counts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/department/{dept_code}/regulations")
async def get_department_regulations(
    dept_code: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """특정 부서의 규정 목록 조회"""
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
                # 해당 부서의 규정 목록 조회
                # wzmgrdptorgcd에 해당 부서코드가 포함된 경우 모두 조회
                cur.execute("""
                    SELECT
                        wzruleid,
                        wzname,
                        wzmgrdptnm,
                        wzmgrdptorgcd,
                        wzestabdate,
                        wzlastrevdate
                    FROM wz_rule
                    WHERE wzmgrdptorgcd LIKE %s
                    OR wzmgrdptorgcd LIKE %s
                    OR wzmgrdptorgcd = %s
                    ORDER BY wzname
                """, (f'%{dept_code}, %', f'%, {dept_code}%', dept_code))

                results = cur.fetchall()

                regulations = [
                    {
                        "rule_id": row[0],
                        "name": row[1],
                        "dept_name": row[2],
                        "dept_code": row[3],
                        "established_date": row[4],
                        "last_revised_date": row[5]
                    }
                    for row in results
                ]

                return {
                    "success": True,
                    "dept_code": dept_code,
                    "regulations": regulations,
                    "count": len(regulations)
                }

    except Exception as e:
        logger.error(f"Error getting department regulations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def get_departments_list(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """부서 목록 조회 (검색 필터용)"""
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
                # 부서 목록 조회
                cur.execute("""
                    SELECT
                        wzdeptorgcd,
                        wzdeptname
                    FROM wz_dept
                    ORDER BY wzdeptname
                """)

                results = cur.fetchall()

                departments = [
                    {
                        "code": row[0],
                        "name": row[1]
                    }
                    for row in results
                ]

                return {
                    "success": True,
                    "data": departments,
                    "departments": departments,  # 하위 호환성 유지
                    "total": len(departments)
                }

    except Exception as e:
        logger.error(f"Error getting departments list: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create")
async def create_department(
    dept_code: str,
    dept_name: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """새 부서 생성"""
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
                # 부서 코드 중복 확인
                cur.execute("""
                    SELECT COUNT(*) FROM wz_dept
                    WHERE wzdeptorgcd = %s
                """, (dept_code,))

                if cur.fetchone()[0] > 0:
                    return {
                        "success": False,
                        "error": "duplicate",
                        "message": f"부서코드 '{dept_code}'가 이미 존재합니다."
                    }

                # 새 부서 삽입
                cur.execute("""
                    INSERT INTO wz_dept (wzdeptorgcd, wzdeptname, wzcreatedby, wzmodifiedby)
                    VALUES (%s, %s, %s, %s)
                """, (dept_code, dept_name, user['username'], user['username']))

                conn.commit()

                return {
                    "success": True,
                    "message": f"부서 '{dept_name}'가 추가되었습니다."
                }

    except Exception as e:
        logger.error(f"Error creating department: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{dept_name}/regulations")
async def get_department_regulations(
    dept_name: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """특정 부서의 규정 목록 조회"""
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
                # 해당 부서의 규정 목록 조회
                cur.execute("""
                    SELECT
                        wzruleseq,
                        wzname,
                        wzpubno,
                        wzestabdate,
                        wzlastrevdate,
                        wzexecdate,
                        wzNewFlag,
                        wzfilejson
                    FROM wz_rule
                    WHERE wzmgrdptnm = %s
                    AND (wzNewFlag = '현행' OR wzNewFlag IS NULL)
                    ORDER BY wzpubno
                """, (dept_name,))

                results = cur.fetchall()

                regulations = []
                for row in results:
                    regulations.append({
                        "wzruleseq": row[0],
                        "wzname": row[1].strip() if row[1] else '',
                        "wzpubno": row[2].strip() if row[2] else '',
                        "wzestabdate": row[3] if row[3] else None,
                        "wzlastrevdate": row[4] if row[4] else None,
                        "wzexecdate": row[5] if row[5] else None,
                        "wzNewFlag": row[6] if row[6] else '현행',
                        "wzfilejson": row[7].strip() if row[7] else None
                    })

                return {
                    "success": True,
                    "department": dept_name,
                    "regulations": regulations,
                    "total": len(regulations)
                }

    except Exception as e:
        logger.error(f"Error getting department regulations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update/{dept_code}")
async def update_department(
    dept_code: str,
    new_name: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """부서명 수정"""
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
                # 부서 존재 확인
                cur.execute("""
                    SELECT wzdeptname FROM wz_dept
                    WHERE wzdeptorgcd = %s
                """, (dept_code,))

                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="부서를 찾을 수 없습니다.")

                old_name = result[0]

                # 부서명 업데이트
                cur.execute("""
                    UPDATE wz_dept
                    SET wzdeptname = %s, wzmodifiedby = %s
                    WHERE wzdeptorgcd = %s
                """, (new_name, user['username'], dept_code))

                # wz_rule 테이블의 부서명도 업데이트
                cur.execute("""
                    UPDATE wz_rule
                    SET wzmgrdptnm = REPLACE(wzmgrdptnm, %s, %s)
                    WHERE wzmgrdptnm LIKE %s
                """, (old_name, new_name, f'%{old_name}%'))

                conn.commit()

                return {
                    "success": True,
                    "message": f"부서명이 '{old_name}'에서 '{new_name}'로 변경되었습니다."
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating department: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{dept_code}")
async def delete_department(
    dept_code: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """부서 삭제"""
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
                # 부서 존재 확인
                cur.execute("""
                    SELECT wzdeptname FROM wz_dept
                    WHERE wzdeptorgcd = %s
                """, (dept_code,))

                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="부서를 찾을 수 없습니다.")

                dept_name = result[0]

                # 해당 부서에 연결된 규정이 있는지 확인
                cur.execute("""
                    SELECT COUNT(*) FROM wz_rule
                    WHERE wzmgrdptorgcd LIKE %s
                    OR wzmgrdptorgcd LIKE %s
                    OR wzmgrdptorgcd = %s
                """, (f'%{dept_code},%', f'%,{dept_code}%', dept_code))

                regulation_count = cur.fetchone()[0]
                if regulation_count > 0:
                    return {
                        "success": False,
                        "error": "has_regulations",
                        "message": f"'{dept_name}' 부서에 {regulation_count}개의 규정이 연결되어 있어 삭제할 수 없습니다."
                    }

                # 부서 삭제
                cur.execute("""
                    DELETE FROM wz_dept
                    WHERE wzdeptorgcd = %s
                """, (dept_code,))

                conn.commit()

                return {
                    "success": True,
                    "message": f"부서 '{dept_name}'가 삭제되었습니다."
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting department: {e}")
        raise HTTPException(status_code=500, detail=str(e))