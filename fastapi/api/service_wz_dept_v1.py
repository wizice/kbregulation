# -*- coding: utf-8 -*-
"""
    service_wz_dept_v1
    ~~~~~~~~~~~~~~~~~~~~~~~~

    WZ_DEPT table API service router v1

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""
import os
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
import pandas as pd
import io
from settings import settings
from .query_wz_dept_v1 import WzDeptTable
from app_logger import setup_logging, get_logger

logger = get_logger(__name__)

# Pydantic Models for Request/Response
class WzDeptBase(BaseModel):
    dept_code: str
    dept_name: str
    parent_dept_code: Optional[str] = None
    dept_level: Optional[int] = None
    dept_order: Optional[int] = None
    is_active: Optional[bool] = True
    manager_id: Optional[str] = None
    description: Optional[str] = None

class WzDeptCreate(WzDeptBase):
    pass

class WzDeptUpdate(BaseModel):
    dept_name: Optional[str] = None
    parent_dept_code: Optional[str] = None
    dept_level: Optional[int] = None
    dept_order: Optional[int] = None
    is_active: Optional[bool] = None
    manager_id: Optional[str] = None
    description: Optional[str] = None

class WzDeptResponse(WzDeptBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SelectRequest(BaseModel):
    conditions: Optional[Dict[str, Any]] = {}
    columns: Optional[str] = "*"
    order_by: Optional[str] = "wzDeptName"
    limit: Optional[int] = 100
    one: Optional[bool] = False

class BulkInsertRequest(BaseModel):
    data: List[WzDeptCreate]

class DeptHierarchyRequest(BaseModel):
    dept_code: Optional[str] = None
    include_inactive: Optional[bool] = False

class DeleteOldDataRequest(BaseModel):
    days: int = Field(default=365, gt=0)

# API Router 생성
router = APIRouter(
    prefix="/WZ_DEPT/api/v1",
    tags=["WZ_DEPT_v1"],
    responses={404: {"description": "Not found"}},
)

# 의존성: WzDeptTable 인스턴스 생성
def get_wz_dept_table():
    """WzDeptTable 인스턴스를 생성하는 의존성"""
    # 실제 환경에서는 환경변수나 설정 파일에서 읽어오기
    return WzDeptTable(
        database=os.getenv("DB_NAME") or settings.DB_NAME,
        user=os.getenv("DB_USER") or settings.DB_USER,
        password=os.getenv("DB_PASSWORD") or settings.DB_PASSWORD,
        host=os.getenv("DB_HOST") or settings.DB_HOST,
        port=int(os.getenv("DB_PORT") or settings.DB_PORT)
    )

# 기본 CRUD 엔드포인트
@router.get("/hello")
@router.post("/hello")
async def hello():
    """check"""
    return {
        "success": True,
    }

# 기본 CRUD 엔드포인트
@router.get("/select")
@router.post("/select")
async def select_data(
    request: SelectRequest,
    wz_dept: WzDeptTable = Depends(get_wz_dept_table)
):
    """부서 데이터 조회"""
    try:
        wz_dept.connect()
        
        # 조건에 따라 다른 조회 메서드 사용
        if 'id' in request.conditions and request.one:
            result = wz_dept.get_by_id(request.conditions['id'])
        elif 'dept_code' in request.conditions and request.one:
            result = wz_dept.get_by_dept_code(request.conditions['dept_code'])
        else:
            result = wz_dept.select(
                wz_dept.TABLE_NAME,
                columns=request.columns,
                condition=request.conditions if request.conditions else None,
                one=request.one,
                order_by=request.order_by,
                limit=request.limit,
                usecon=True
            )
        
        wz_dept.close()
        
        return {
            "success": True,
            "data": result,
            "count": len(result) if isinstance(result, list) else 1 if result else 0
        }
        
    except Exception as e:
        wz_dept.close()
        logger.error(f'select_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insert")
@router.post("/insert")
async def insert_data(
    data: WzDeptCreate,
    wz_dept: WzDeptTable = Depends(get_wz_dept_table)
):
    """부서 데이터 삽입"""
    try:
        wz_dept.connect()
        
        # 부서 코드 중복 확인
        existing = wz_dept.get_by_dept_code(data.dept_code)
        if existing:
            wz_dept.close()
            raise HTTPException(status_code=409, detail="Department code already exists")
        
        insert_data = data.dict()
        result_id = wz_dept.save(insert_data)
        
        # 삽입된 데이터 조회
        new_record = wz_dept.get_by_id(result_id) if result_id else None
        
        wz_dept.close()
        
        return {
            "success": True,
            "id": result_id,
            "data": new_record,
            "message": "Department inserted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        wz_dept.close()
        logger.error(f'insert_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/update")
@router.post("/update") 
async def update_data(
    id: int,
    data: WzDeptUpdate,
    wz_dept: WzDeptTable = Depends(get_wz_dept_table)
):
    """부서 데이터 업데이트"""
    try:
        wz_dept.connect()
        
        # 기존 데이터 확인
        existing = wz_dept.get_by_id(id)
        if not existing:
            wz_dept.close()
            raise HTTPException(status_code=404, detail="Department not found")
        
        # 업데이트 실행
        update_dict = data.dict(exclude_unset=True)
        if update_dict:
            update_dict['updated_at'] = datetime.now()
            result = wz_dept.update(
                wz_dept.TABLE_NAME,
                update_dict,
                {"id": id},
                usecon=True
            )
        else:
            result = 0
            
        # 업데이트된 데이터 조회
        updated_record = wz_dept.get_by_id(id) if result > 0 else None
        
        wz_dept.close()
        
        return {
            "success": result > 0,
            "data": updated_record,
            "message": "Department updated successfully" if result > 0 else "No data to update"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        wz_dept.close()
        logger.error(f'update_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/delete")
@router.post("/delete")
async def delete_data(
    id: int,
    wz_dept: WzDeptTable = Depends(get_wz_dept_table)
):
    """부서 데이터 삭제"""
    try:
        wz_dept.connect()
        
        # 삭제 전 데이터 조회
        existing = wz_dept.get_by_id(id)
        if not existing:
            wz_dept.close()
            raise HTTPException(status_code=404, detail="Department not found")
        
        # 하위 부서 확인
        sub_depts = wz_dept.get_sub_departments(existing['dept_code'])
        if sub_depts:
            wz_dept.close()
            raise HTTPException(status_code=400, detail="Cannot delete department with sub-departments")
        
        # 삭제 실행
        result = wz_dept.delete(wz_dept.TABLE_NAME, {"id": id}, usecon=True)
        
        wz_dept.close()
        
        return {
            "success": result > 0,
            "deleted_count": result,
            "deleted_data": existing,
            "message": f"Deleted {result} department(s)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        wz_dept.close()
        logger.error(f'delete_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/save")
@router.post("/save")
async def save_data(
    data: Dict[str, Any],
    wz_dept: WzDeptTable = Depends(get_wz_dept_table)
):
    """부서 데이터 저장 (INSERT 또는 UPDATE)"""
    try:
        wz_dept.connect()
        
        # 부서 코드 중복 확인 (INSERT인 경우)
        if 'id' not in data or not data['id']:
            existing = wz_dept.get_by_dept_code(data.get('dept_code'))
            if existing:
                wz_dept.close()
                raise HTTPException(status_code=409, detail="Department code already exists")
        
        result_id = wz_dept.save(data)
        
        # 저장된 데이터 조회
        saved_record = wz_dept.get_by_id(result_id) if result_id else None
        
        wz_dept.close()
        
        is_update = 'id' in data and data['id']
        
        return {
            "success": True,
            "id": result_id,
            "data": saved_record,
            "operation": "update" if is_update else "insert",
            "message": f"Department {'updated' if is_update else 'inserted'} successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        wz_dept.close()
        logger.error(f'save_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/excel_down")
@router.post("/excel_down")
async def download_excel(
    request: SelectRequest,
    wz_dept: WzDeptTable = Depends(get_wz_dept_table)
):
    """부서 데이터 엑셀 다운로드"""
    try:
        wz_dept.connect()
        
        # 데이터 조회
        data = wz_dept.select(
            wz_dept.TABLE_NAME,
            columns=request.columns,
            condition=request.conditions if request.conditions else None,
            order_by=request.order_by,
            limit=request.limit or 10000,
            usecon=True
        )
        
        wz_dept.close()
        
        if not data:
            raise HTTPException(status_code=404, detail="No data found")
        
        # DataFrame 생성
        df = pd.DataFrame(data)
        
        # 엑셀 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Department Data', index=False)
        
        output.seek(0)
        
        # 파일명 생성
        filename = f"department_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        wz_dept.close()
        logger.error(f'download_excel error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/excel_upload")
async def upload_excel(
    file: UploadFile = File(...),
    wz_dept: WzDeptTable = Depends(get_wz_dept_table)
):
    """엑셀 업로드 및 부서 데이터 일괄 삽입"""
    try:
        # 파일 확장자 확인
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only Excel files are allowed")
        
        # 엑셀 파일 읽기
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # 필수 컬럼 확인
        required_columns = ['dept_code', 'dept_name']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {missing_columns}"
            )
        
        # 데이터 타입 변환 및 기본값 설정
        df['is_active'] = df.get('is_active', True).fillna(True)
        df['dept_level'] = pd.to_numeric(df.get('dept_level', 0), errors='coerce').fillna(0).astype(int)
        df['dept_order'] = pd.to_numeric(df.get('dept_order', 0), errors='coerce').fillna(0).astype(int)
        
        # NaN 값을 None으로 변환
        df = df.where(pd.notnull(df), None)
        
        # 데이터 준비
        data_list = df.to_dict('records')
        
        if not data_list:
            raise HTTPException(status_code=400, detail="No valid data found in file")
        
        # 일괄 삽입
        wz_dept.connect()
        inserted_count = wz_dept.bulk_insert(data_list)
        wz_dept.close()
        
        return {
            "success": True,
            "inserted_count": inserted_count,
            "total_rows": len(df),
            "message": f"Successfully inserted {inserted_count} departments"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if 'wz_dept' in locals():
            wz_dept.close()
        logger.error(f'upload_excel error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

# 추가 고급 엔드포인트
@router.post("/hierarchy")
async def get_department_hierarchy(
    request: DeptHierarchyRequest,
    wz_dept: WzDeptTable = Depends(get_wz_dept_table)
):
    """부서 계층 구조 조회"""
    try:
        wz_dept.connect()
        
        if request.dept_code:
            # 특정 부서의 하위 부서 조회
            hierarchy = wz_dept.get_department_tree(
                request.dept_code,
                include_inactive=request.include_inactive
            )
        else:
            # 전체 부서 계층 구조 조회
            hierarchy = wz_dept.get_full_hierarchy(
                include_inactive=request.include_inactive
            )
        
        wz_dept.close()
        
        return {
            "success": True,
            "data": hierarchy,
            "count": len(hierarchy) if isinstance(hierarchy, list) else 1
        }
        
    except Exception as e:
        wz_dept.close()
        logger.error(f'get_department_hierarchy error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk_insert")
async def bulk_insert_data(
    request: BulkInsertRequest,
    wz_dept: WzDeptTable = Depends(get_wz_dept_table)
):
    """대량 부서 데이터 삽입"""
    try:
        data_list = [item.dict() for item in request.data]
        
        wz_dept.connect()
        
        # 부서 코드 중복 확인
        dept_codes = [item['dept_code'] for item in data_list]
        existing_codes = wz_dept.check_existing_dept_codes(dept_codes)
        
        if existing_codes:
            wz_dept.close()
            raise HTTPException(
                status_code=409, 
                detail=f"Department codes already exist: {', '.join(existing_codes)}"
            )
        
        inserted_count = wz_dept.bulk_insert(data_list)
        wz_dept.close()
        
        return {
            "success": True,
            "inserted_count": inserted_count,
            "message": f"Successfully inserted {inserted_count} departments"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        wz_dept.close()
        logger.error(f'bulk_insert_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_old_data")
async def delete_old_data(
    request: DeleteOldDataRequest,
    wz_dept: WzDeptTable = Depends(get_wz_dept_table)
):
    """오래된 비활성 부서 데이터 삭제"""
    try:
        wz_dept.connect()
        deleted_count = wz_dept.delete_old_inactive_departments(days=request.days)
        wz_dept.close()
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Successfully deleted {deleted_count} inactive departments older than {request.days} days"
        }
        
    except Exception as e:
        wz_dept.close()
        logger.error(f'delete_old_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active_departments")
async def get_active_departments(
    wz_dept: WzDeptTable = Depends(get_wz_dept_table)
):
    """활성 부서 목록 조회"""
    try:
        wz_dept.connect()
        departments = wz_dept.get_active_departments()
        wz_dept.close()
        
        return {
            "success": True,
            "data": departments,
            "count": len(departments)
        }
        
    except Exception as e:
        wz_dept.close()
        logger.error(f'get_active_departments error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/department/{dept_code}/path")
async def get_department_path(
    dept_code: str,
    wz_dept: WzDeptTable = Depends(get_wz_dept_table)
):
    """부서 경로 조회 (루트부터 해당 부서까지)"""
    try:
        wz_dept.connect()
        
        # 부서 존재 확인
        dept = wz_dept.get_by_dept_code(dept_code)
        if not dept:
            wz_dept.close()
            raise HTTPException(status_code=404, detail="Department not found")
        
        path = wz_dept.get_department_path(dept_code)
        wz_dept.close()
        
        return {
            "success": True,
            "dept_code": dept_code,
            "path": path,
            "depth": len(path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        wz_dept.close()
        logger.error(f'get_department_path error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

# 헬스체크
@router.get("/health")
async def health_check(wz_dept: WzDeptTable = Depends(get_wz_dept_table)):
    """API 헬스체크"""
    try:
        con = wz_dept.connect()
        # 간단한 쿼리로 DB 연결 확인
        result = wz_dept.query("SELECT 1", con=con)
        wz_dept.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f'health_check error:{str(e)}')
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# FastAPI 앱에 라우터 등록 예시
# from fastapi import FastAPI
# app = FastAPI()
# app.include_router(router)