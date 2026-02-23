# -*- coding: utf-8 -*-
"""
    service_mon_systems_v1
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Mon Systems table API service router v1

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
from .query_mon_systems_v1 import MonSystemsTable

# Pydantic Models for Request/Response
class MonSystemsBase(BaseModel):
    account_seq: int
    system_name: str
    system_type: Optional[str] = None
    status: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    description: Optional[str] = None
    monitor_interval: Optional[int] = None
    last_check_time: Optional[datetime] = None
    is_active: Optional[bool] = True

class MonSystemsCreate(MonSystemsBase):
    pass

class MonSystemsUpdate(BaseModel):
    system_name: Optional[str] = None
    system_type: Optional[str] = None
    status: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    description: Optional[str] = None
    monitor_interval: Optional[int] = None
    last_check_time: Optional[datetime] = None
    is_active: Optional[bool] = None

class MonSystemsResponse(MonSystemsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SelectRequest(BaseModel):
    conditions: Optional[Dict[str, Any]] = {}
    columns: Optional[str] = "*"
    order_by: Optional[str] = "id DESC"
    limit: Optional[int] = 100
    one: Optional[bool] = False

class BulkInsertRequest(BaseModel):
    data: List[MonSystemsCreate]

class SystemStatusRequest(BaseModel):
    account_seq: int
    status: Optional[str] = None
    is_active: Optional[bool] = None

class DeleteInactiveRequest(BaseModel):
    days: int = Field(default=30, gt=0)

# API Router 생성
router = APIRouter(
    prefix="/mon_systems/api/v1",
    tags=["mon_systems_v1"],
    responses={404: {"description": "Not found"}},
)

# 의존성: MonSystemsTable 인스턴스 생성
def get_mon_systems_table():
    """MonSystemsTable 인스턴스를 생성하는 의존성"""
    # 실제 환경에서는 환경변수나 설정 파일에서 읽어오기
    return MonSystemsTable(
            database=os.getenv("DB_NAME") or settings.DB_NAME,
            user=os.getenv("DB_USER") or settings.DB_USER,
            password=os.getenv("DB_PASSWORD") or settings.DB_PASSWORD,
            host=os.getenv("DB_HOST") or settings.DB_HOST,
            port=int(os.getenv("DB_PORT") or settings.DB_PORT )
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
    mon_systems: MonSystemsTable = Depends(get_mon_systems_table)
):
    """데이터 조회"""
    try:
        mon_systems.connect()
        
        # 조건에 따라 다른 조회 메서드 사용
        if 'id' in request.conditions and request.one:
            result = mon_systems.get_by_id(request.conditions['id'])
        elif 'account_seq' in request.conditions:
            result = mon_systems.get_by_account(
                request.conditions['account_seq'],
                limit=request.limit
            )
            if request.one and result:
                result = result[0]
        else:
            result = mon_systems.select(
                mon_systems.TABLE_NAME,
                columns=request.columns,
                condition=request.conditions if request.conditions else None,
                one=request.one,
                order_by=request.order_by,
                limit=request.limit,
                usecon=True
            )
        
        mon_systems.close()
        
        return {
            "success": True,
            "data": result,
            "count": len(result) if isinstance(result, list) else 1 if result else 0
        }
        
    except Exception as e:
        mon_systems.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insert")
@router.post("/insert")
async def insert_data(
    data: MonSystemsCreate,
    mon_systems: MonSystemsTable = Depends(get_mon_systems_table)
):
    """데이터 삽입"""
    try:
        mon_systems.connect()
        
        insert_data = data.dict()
        result_id = mon_systems.save(insert_data)
        
        # 삽입된 데이터 조회
        new_record = mon_systems.get_by_id(result_id) if result_id else None
        
        mon_systems.close()
        
        return {
            "success": True,
            "id": result_id,
            "data": new_record,
            "message": "Data inserted successfully"
        }
        
    except Exception as e:
        mon_systems.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/update")
@router.post("/update") 
async def update_data(
    id: int,
    data: MonSystemsUpdate,
    mon_systems: MonSystemsTable = Depends(get_mon_systems_table)
):
    """데이터 업데이트"""
    try:
        mon_systems.connect()
        
        # 기존 데이터 확인
        existing = mon_systems.get_by_id(id)
        if not existing:
            mon_systems.close()
            raise HTTPException(status_code=404, detail="Record not found")
        
        # 업데이트 실행
        update_dict = data.dict(exclude_unset=True)
        if update_dict:
            result = mon_systems.update_system(id, **update_dict)
        else:
            result = False
            
        # 업데이트된 데이터 조회
        updated_record = mon_systems.get_by_id(id) if result else None
        
        mon_systems.close()
        
        return {
            "success": result,
            "data": updated_record,
            "message": "Data updated successfully" if result else "No data to update"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        mon_systems.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/delete")
@router.post("/delete")
async def delete_data(
    id: int,
    mon_systems: MonSystemsTable = Depends(get_mon_systems_table)
):
    """데이터 삭제"""
    try:
        mon_systems.connect()
        
        # 삭제 전 데이터 조회
        existing = mon_systems.get_by_id(id)
        if not existing:
            mon_systems.close()
            raise HTTPException(status_code=404, detail="Record not found")
        
        # 삭제 실행
        result = mon_systems.delete(mon_systems.TABLE_NAME, {"id": id}, usecon=True)
        
        mon_systems.close()
        
        return {
            "success": result > 0,
            "deleted_count": result,
            "deleted_data": existing,
            "message": f"Deleted {result} record(s)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        mon_systems.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/save")
@router.post("/save")
async def save_data(
    data: Dict[str, Any],
    mon_systems: MonSystemsTable = Depends(get_mon_systems_table)
):
    """데이터 저장 (INSERT 또는 UPDATE)"""
    try:
        mon_systems.connect()
        
        result_id = mon_systems.save(data)
        
        # 저장된 데이터 조회
        saved_record = mon_systems.get_by_id(result_id) if result_id else None
        
        mon_systems.close()
        
        is_update = 'id' in data and data['id']
        
        return {
            "success": True,
            "id": result_id,
            "data": saved_record,
            "operation": "update" if is_update else "insert",
            "message": f"Data {'updated' if is_update else 'inserted'} successfully"
        }
        
    except Exception as e:
        mon_systems.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/excel_down")
@router.post("/excel_down")
async def download_excel(
    request: SelectRequest,
    mon_systems: MonSystemsTable = Depends(get_mon_systems_table)
):
    """엑셀 다운로드"""
    try:
        mon_systems.connect()
        
        # 데이터 조회
        if 'account_seq' in request.conditions:
            data = mon_systems.get_by_account(
                request.conditions['account_seq'],
                limit=request.limit or 10000
            )
        else:
            data = mon_systems.select(
                mon_systems.TABLE_NAME,
                columns=request.columns,
                condition=request.conditions if request.conditions else None,
                order_by=request.order_by,
                limit=request.limit or 10000,
                usecon=True
            )
        
        mon_systems.close()
        
        if not data:
            raise HTTPException(status_code=404, detail="No data found")
        
        # DataFrame 생성
        df = pd.DataFrame(data)
        
        # 엑셀 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Mon Systems Data', index=False)
        
        output.seek(0)
        
        # 파일명 생성
        filename = f"mon_systems_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        mon_systems.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/excel_upload")
async def upload_excel(
    file: UploadFile = File(...),
    mon_systems: MonSystemsTable = Depends(get_mon_systems_table)
):
    """엑셀 업로드 및 데이터 일괄 삽입"""
    try:
        # 파일 확장자 확인
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only Excel files are allowed")
        
        # 엑셀 파일 읽기
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # 필수 컬럼 확인
        required_columns = ['account_seq', 'system_name']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {missing_columns}"
            )
        
        # 데이터 타입 변환
        df['account_seq'] = df['account_seq'].astype(int)
        if 'port' in df.columns:
            df['port'] = pd.to_numeric(df['port'], errors='coerce')
        if 'monitor_interval' in df.columns:
            df['monitor_interval'] = pd.to_numeric(df['monitor_interval'], errors='coerce')
        if 'last_check_time' in df.columns:
            df['last_check_time'] = pd.to_datetime(df['last_check_time'], errors='coerce')
        if 'is_active' in df.columns:
            df['is_active'] = df['is_active'].astype(bool)
        
        # NaN 값을 None으로 변환
        df = df.where(pd.notnull(df), None)
        
        # 데이터 준비
        data_list = df.to_dict('records')
        
        if not data_list:
            raise HTTPException(status_code=400, detail="No valid data found in file")
        
        # 일괄 삽입
        mon_systems.connect()
        inserted_count = mon_systems.bulk_insert(data_list)
        mon_systems.close()
        
        return {
            "success": True,
            "inserted_count": inserted_count,
            "total_rows": len(df),
            "message": f"Successfully inserted {inserted_count} records"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if 'mon_systems' in locals():
            mon_systems.close()
        raise HTTPException(status_code=500, detail=str(e))

# 추가 고급 엔드포인트
@router.post("/system_status")
async def get_system_status(
    request: SystemStatusRequest,
    mon_systems: MonSystemsTable = Depends(get_mon_systems_table)
):
    """시스템 상태별 조회"""
    try:
        mon_systems.connect()
        
        data = mon_systems.get_by_status(
            account_seq=request.account_seq,
            status=request.status,
            is_active=request.is_active
        )
        
        mon_systems.close()
        
        return {
            "success": True,
            "data": data,
            "count": len(data),
            "filters": {
                "account_seq": request.account_seq,
                "status": request.status,
                "is_active": request.is_active
            }
        }
        
    except Exception as e:
        mon_systems.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk_insert")
async def bulk_insert_data(
    request: BulkInsertRequest,
    mon_systems: MonSystemsTable = Depends(get_mon_systems_table)
):
    """대량 데이터 삽입"""
    try:
        data_list = [item.dict() for item in request.data]
        
        mon_systems.connect()
        inserted_count = mon_systems.bulk_insert(data_list)
        mon_systems.close()
        
        return {
            "success": True,
            "inserted_count": inserted_count,
            "message": f"Successfully inserted {inserted_count} records"
        }
        
    except Exception as e:
        mon_systems.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_inactive")
async def delete_inactive_systems(
    request: DeleteInactiveRequest,
    mon_systems: MonSystemsTable = Depends(get_mon_systems_table)
):
    """비활성 시스템 삭제"""
    try:
        mon_systems.connect()
        deleted_count = mon_systems.delete_inactive_systems(days=request.days)
        mon_systems.close()
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Successfully deleted {deleted_count} inactive systems older than {request.days} days"
        }
        
    except Exception as e:
        mon_systems.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/account/{account_seq}/summary")
async def get_account_summary(
    account_seq: int,
    mon_systems: MonSystemsTable = Depends(get_mon_systems_table)
):
    """계정별 시스템 요약 정보"""
    try:
        mon_systems.connect()
        
        # 전체 시스템 조회
        all_systems = mon_systems.get_by_account(account_seq)
        
        # 상태별 집계
        summary = {
            "total": len(all_systems),
            "active": sum(1 for s in all_systems if s.get('is_active', False)),
            "inactive": sum(1 for s in all_systems if not s.get('is_active', True)),
            "by_status": {},
            "by_type": {}
        }
        
        # 상태별 카운트
        for system in all_systems:
            status = system.get('status', 'unknown')
            system_type = system.get('system_type', 'unknown')
            
            summary['by_status'][status] = summary['by_status'].get(status, 0) + 1
            summary['by_type'][system_type] = summary['by_type'].get(system_type, 0) + 1
        
        mon_systems.close()
        
        return {
            "success": True,
            "account_seq": account_seq,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        mon_systems.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update_status/{id}")
async def update_system_status(
    id: int,
    status: str,
    mon_systems: MonSystemsTable = Depends(get_mon_systems_table)
):
    """시스템 상태 업데이트"""
    try:
        mon_systems.connect()
        
        # 시스템 존재 확인
        existing = mon_systems.get_by_id(id)
        if not existing:
            mon_systems.close()
            raise HTTPException(status_code=404, detail="System not found")
        
        # 상태 업데이트
        result = mon_systems.update_system(
            id, 
            status=status, 
            last_check_time=datetime.now()
        )
        
        # 업데이트된 데이터 조회
        updated_system = mon_systems.get_by_id(id)
        
        mon_systems.close()
        
        return {
            "success": result,
            "data": updated_system,
            "previous_status": existing.get('status'),
            "new_status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        mon_systems.close()
        raise HTTPException(status_code=500, detail=str(e))

# 헬스체크
@router.get("/health")
async def health_check(mon_systems: MonSystemsTable = Depends(get_mon_systems_table)):
    """API 헬스체크"""
    try:
        con = mon_systems.connect()
        # 간단한 쿼리로 DB 연결 확인
        result = mon_systems.query("SELECT 1", con=con)
        mon_systems.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
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