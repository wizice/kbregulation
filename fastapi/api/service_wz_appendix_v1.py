# -*- coding: utf-8 -*-
"""
    service_wz_appendix_v1
    ~~~~~~~~~~~~~~~~~~~~~~~~

    WZ_APPENDIX table API service router v1

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
from .query_wz_appendix_v1 import WzAppendixTable
from app_logger import setup_logging, get_logger

logger = get_logger(__name__)

# Pydantic Models for Request/Response
class WzAppendixBase(BaseModel):
    account_seq: int
    device_seq: int
    timestamp: datetime
    dg: Optional[float] = None
    dn: Optional[float] = None

class WzAppendixCreate(WzAppendixBase):
    pass

class WzAppendixUpdate(BaseModel):
    dg: Optional[float] = None
    dn: Optional[float] = None

class WzAppendixResponse(WzAppendixBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SelectRequest(BaseModel):
    conditions: Optional[Dict[str, Any]] = {}
    columns: Optional[str] = "*"
    order_by: Optional[str] = "timestamp DESC"
    limit: Optional[int] = 100
    one: Optional[bool] = False

class BulkInsertRequest(BaseModel):
    data: List[WzAppendixCreate]

class AggregateRequest(BaseModel):
    account_seq: int
    device_seq: int
    interval: str = "1 hour"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class DeleteOldDataRequest(BaseModel):
    days: int = Field(default=30, gt=0)

# API Router 생성
router = APIRouter(
    prefix="/WZ_APPENDIX/api/v1",
    tags=["wz_appendix_v1"],
    responses={404: {"description": "Not found"}},
)

# 의존성: WzAppendixTable 인스턴스 생성
def get_wz_appendix_table():
    """WzAppendixTable 인스턴스를 생성하는 의존성"""
    # 실제 환경에서는 환경변수나 설정 파일에서 읽어오기
    return WzAppendixTable(
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
    wz_appendix: WzAppendixTable = Depends(get_wz_appendix_table)
):
    """데이터 조회"""
    try:
        wz_appendix.connect()
        
        # 조건에 따라 다른 조회 메서드 사용
        if 'id' in request.conditions and request.one:
            result = wz_appendix.get_by_id(request.conditions['id'])
        elif 'account_seq' in request.conditions and 'device_seq' in request.conditions:
            result = wz_appendix.get_by_device(
                request.conditions['account_seq'],
                request.conditions['device_seq'],
                limit=request.limit
            )
            if request.one and result:
                result = result[0]
        else:
            result = wz_appendix.select(
                wz_appendix.TABLE_NAME,
                columns=request.columns,
                condition=request.conditions if request.conditions else None,
                one=request.one,
                order_by=request.order_by,
                limit=request.limit,
                usecon=True
            )
        
        wz_appendix.close()
        
        return {
            "success": True,
            "data": result,
            "count": len(result) if isinstance(result, list) else 1 if result else 0
        }
        
    except Exception as e:
        wz_appendix.close()
        logger.error(f'select_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insert")
@router.post("/insert")
async def insert_data(
    data: WzAppendixCreate,
    wz_appendix: WzAppendixTable = Depends(get_wz_appendix_table)
):
    """데이터 삽입"""
    try:
        wz_appendix.connect()
        
        insert_data = data.dict()
        result_id = wz_appendix.save(insert_data)
        
        # 삽입된 데이터 조회
        new_record = wz_appendix.get_by_id(result_id) if result_id else None
        
        wz_appendix.close()
        
        return {
            "success": True,
            "id": result_id,
            "data": new_record,
            "message": "Data inserted successfully"
        }
        
    except Exception as e:
        wz_appendix.close()
        logger.error(f'insert_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/update")
@router.post("/update") 
async def update_data(
    id: int,
    data: WzAppendixUpdate,
    wz_appendix: WzAppendixTable = Depends(get_wz_appendix_table)
):
    """데이터 업데이트"""
    try:
        wz_appendix.connect()
        
        # 기존 데이터 확인
        existing = wz_appendix.get_by_id(id)
        if not existing:
            wz_appendix.close()
            raise HTTPException(status_code=404, detail="Record not found")
        
        # 업데이트 실행
        update_dict = data.dict(exclude_unset=True)
        if update_dict:
            result = wz_appendix.update_device_data(id, **update_dict)
        else:
            result = False
            
        # 업데이트된 데이터 조회
        updated_record = wz_appendix.get_by_id(id) if result else None
        
        wz_appendix.close()
        
        return {
            "success": result,
            "data": updated_record,
            "message": "Data updated successfully" if result else "No data to update"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        wz_appendix.close()
        logger.error(f'update_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/delete")
@router.post("/delete")
async def delete_data(
    id: int,
    wz_appendix: WzAppendixTable = Depends(get_wz_appendix_table)
):
    """데이터 삭제"""
    try:
        wz_appendix.connect()
        
        # 삭제 전 데이터 조회
        existing = wz_appendix.get_by_id(id)
        if not existing:
            wz_appendix.close()
            raise HTTPException(status_code=404, detail="Record not found")
        
        # 삭제 실행
        result = wz_appendix.delete(wz_appendix.TABLE_NAME, {"id": id}, usecon=True)
        
        wz_appendix.close()
        
        return {
            "success": result > 0,
            "deleted_count": result,
            "deleted_data": existing,
            "message": f"Deleted {result} record(s)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        wz_appendix.close()
        logger.error(f'delete_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/save")
@router.post("/save")
async def save_data(
    data: Dict[str, Any],
    wz_appendix: WzAppendixTable = Depends(get_wz_appendix_table)
):
    """데이터 저장 (INSERT 또는 UPDATE)"""
    try:
        wz_appendix.connect()
        
        result_id = wz_appendix.save(data)
        
        # 저장된 데이터 조회
        saved_record = wz_appendix.get_by_id(result_id) if result_id else None
        
        wz_appendix.close()
        
        is_update = 'id' in data and data['id']
        
        return {
            "success": True,
            "id": result_id,
            "data": saved_record,
            "operation": "update" if is_update else "insert",
            "message": f"Data {'updated' if is_update else 'inserted'} successfully"
        }
        
    except Exception as e:
        wz_appendix.close()
        logger.error(f'save_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/excel_down")
@router.post("/excel_down")
async def download_excel(
    request: SelectRequest,
    wz_appendix: WzAppendixTable = Depends(get_wz_appendix_table)
):
    """엑셀 다운로드"""
    try:
        wz_appendix.connect()
        
        # 데이터 조회
        if 'account_seq' in request.conditions and 'device_seq' in request.conditions:
            data = wz_appendix.get_by_device(
                request.conditions['account_seq'],
                request.conditions['device_seq'],
                limit=request.limit or 10000
            )
        else:
            data = wz_appendix.select(
                wz_appendix.TABLE_NAME,
                columns=request.columns,
                condition=request.conditions if request.conditions else None,
                order_by=request.order_by,
                limit=request.limit or 10000,
                usecon=True
            )
        
        wz_appendix.close()
        
        if not data:
            raise HTTPException(status_code=404, detail="No data found")
        
        # DataFrame 생성
        df = pd.DataFrame(data)
        
        # 엑셀 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='WZ_APPENDIX Data', index=False)
        
        output.seek(0)
        
        # 파일명 생성
        filename = f"wz_appendix_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        wz_appendix.close()
        logger.error(f'download_excel error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/excel_upload")
async def upload_excel(
    file: UploadFile = File(...),
    wz_appendix: WzAppendixTable = Depends(get_wz_appendix_table)
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
        required_columns = ['account_seq', 'device_seq', 'timestamp', 'dg', 'dn']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {missing_columns}"
            )
        
        # 데이터 타입 변환
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['account_seq'] = df['account_seq'].astype(int)
        df['device_seq'] = df['device_seq'].astype(int)
        df['dg'] = pd.to_numeric(df['dg'], errors='coerce')
        df['dn'] = pd.to_numeric(df['dn'], errors='coerce')
        
        # NaN 값 제거
        df = df.dropna(subset=required_columns)
        
        # 데이터 준비
        data_list = df.to_dict('records')
        
        if not data_list:
            raise HTTPException(status_code=400, detail="No valid data found in file")
        
        # 일괄 삽입
        wz_appendix.connect()
        inserted_count = wz_appendix.bulk_insert(data_list)
        wz_appendix.close()
        
        return {
            "success": True,
            "inserted_count": inserted_count,
            "total_rows": len(df),
            "message": f"Successfully inserted {inserted_count} records"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if 'wz_appendix' in locals():
            wz_appendix.close()
        logger.error(f'upload_excel error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

# 추가 고급 엔드포인트
@router.post("/aggregate")
async def get_aggregated_data(
    request: AggregateRequest,
    wz_appendix: WzAppendixTable = Depends(get_wz_appendix_table)
):
    """집계 데이터 조회"""
    try:
        wz_appendix.connect()
        
        data = wz_appendix.get_aggregated_data(
            account_seq=request.account_seq,
            device_seq=request.device_seq,
            interval=request.interval,
            start_time=request.start_time,
            end_time=request.end_time
        )
        
        wz_appendix.close()
        
        return {
            "success": True,
            "data": data,
            "count": len(data),
            "interval": request.interval
        }
        
    except Exception as e:
        wz_appendix.close()
        logger.error(f'get_aggregated_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk_insert")
async def bulk_insert_data(
    request: BulkInsertRequest,
    wz_appendix: WzAppendixTable = Depends(get_wz_appendix_table)
):
    """대량 데이터 삽입"""
    try:
        data_list = [item.dict() for item in request.data]
        
        wz_appendix.connect()
        inserted_count = wz_appendix.bulk_insert(data_list)
        wz_appendix.close()
        
        return {
            "success": True,
            "inserted_count": inserted_count,
            "message": f"Successfully inserted {inserted_count} records"
        }
        
    except Exception as e:
        wz_appendix.close()
        logger.error(f'bulk_insert_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_old_data")
async def delete_old_data(
    request: DeleteOldDataRequest,
    wz_appendix: WzAppendixTable = Depends(get_wz_appendix_table)
):
    """오래된 데이터 삭제"""
    try:
        wz_appendix.connect()
        deleted_count = wz_appendix.delete_old_data(days=request.days)
        wz_appendix.close()
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Successfully deleted {deleted_count} records older than {request.days} days"
        }
        
    except Exception as e:
        wz_appendix.close()
        logger.error(f'delete_old_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/device_list/{account_seq}")
async def get_device_list(
    account_seq: int,
    wz_appendix: WzAppendixTable = Depends(get_wz_appendix_table)
):
    """계정별 디바이스 목록 조회"""
    try:
        wz_appendix.connect()
        devices = wz_appendix.get_device_list_by_account(account_seq)
        wz_appendix.close()
        
        return {
            "success": True,
            "account_seq": account_seq,
            "devices": devices,
            "device_count": len(devices)
        }
        
    except Exception as e:
        wz_appendix.close()
        logger.error(f'get_device_list error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

# 헬스체크
@router.get("/health")
async def health_check(wz_appendix: WzAppendixTable = Depends(get_wz_appendix_table)):
    """API 헬스체크"""
    try:
        con = wz_appendix.connect()
        # 간단한 쿼리로 DB 연결 확인
        result = wz_appendix.query("SELECT 1", con=con)
        wz_appendix.close()
        
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