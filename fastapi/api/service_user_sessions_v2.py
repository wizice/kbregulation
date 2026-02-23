# -*- coding: utf-8 -*-
"""
    service_user_sessions_v2
    ~~~~~~~~~~~~~~~~~~~~~~~~

    User sessions table API service router v1

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
from app_logger import setup_logging, get_logger
from .query_user_sessions_v2 import UserSessionsTable

logger = get_logger(__name__)

# Pydantic Models for Request/Response
class UserSessionBase(BaseModel):
    user_id: int
    session_id: str
    ip_address: str
    user_agent: str
    login_time: datetime
    logout_time: Optional[datetime] = None
    is_active: bool = True
    device_type: Optional[str] = None
    location: Optional[str] = None

class UserSessionCreate(UserSessionBase):
    pass

class UserSessionUpdate(BaseModel):
    logout_time: Optional[datetime] = None
    is_active: Optional[bool] = None
    device_type: Optional[str] = None
    location: Optional[str] = None

class UserSessionResponse(UserSessionBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SelectRequest(BaseModel):
    conditions: Optional[Dict[str, Any]] = {}
    columns: Optional[str] = "*"
    order_by: Optional[str] = "login_time DESC"
    limit: Optional[int] = 100
    one: Optional[bool] = False

class BulkInsertRequest(BaseModel):
    data: List[UserSessionCreate]

class AggregateRequest(BaseModel):
    user_id: Optional[int] = None
    interval: str = "1 hour"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class DeleteOldDataRequest(BaseModel):
    days: int = Field(default=30, gt=0)

class ActiveSessionsRequest(BaseModel):
    user_id: Optional[int] = None
    device_type: Optional[str] = None
    limit: Optional[int] = 100

# API Router 생성
router = APIRouter(
    prefix="/user_sessions/api/v1",
    tags=["user_sessions_v2"],
    responses={404: {"description": "Not found"}},
)

_sessions_table: Optional[UserSessionsTable] = None
# 의존성: UserSessionsTable 인스턴스 생성
def get_user_sessions_table():
    """UsersTable 싱글톤 인스턴스"""
    global _sessions_table
    if _sessions_table is None:
        # 환경변수나 설정에서 DB 설정을 가져옴
        db_config = {
            "database": settings.DB_NAME or os.getenv("DB_NAME", "wzdb"),
            "user": settings.DB_USER or os.getenv("DB_USER", "wzuser"),
            "password": settings.DB_PASSWORD or os.getenv("DB_PASSWORD", "wzuserpwd!"),
            "host": settings.DB_HOST or os.getenv("DB_HOST", "127.0.0.1"),
            "port": int(settings.DB_PORT or os.getenv("DB_PORT", 5432))
        }
        db_manager = get_db_manager(db_config)
        _sessions_table = UserSessionsTable(db_manager=db_manager, logger=logger)
        
    return _sessions_table

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
    user_sessions: UserSessionsTable = Depends(get_user_sessions_table)
):
    """데이터 조회"""
    try:
        user_sessions.connect()
        
        # 조건에 따라 다른 조회 메서드 사용
        if 'id' in request.conditions and request.one:
            result = user_sessions.get_by_id(request.conditions['id'])
        elif 'user_id' in request.conditions:
            result = user_sessions.get_by_user(
                request.conditions['user_id'],
                limit=request.limit
            )
            if request.one and result:
                result = result[0]
        elif 'session_id' in request.conditions:
            result = user_sessions.get_by_session_id(request.conditions['session_id'])
        else:
            result = user_sessions.select(
                user_sessions.TABLE_NAME,
                columns=request.columns,
                condition=request.conditions if request.conditions else None,
                one=request.one,
                order_by=request.order_by,
                limit=request.limit
            )
        
        user_sessions.close()
        
        return {
            "success": True,
            "data": result,
            "count": len(result) if isinstance(result, list) else 1 if result else 0
        }
        
    except Exception as e:
        user_sessions.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insert")
@router.post("/insert")
async def insert_data(
    data: UserSessionCreate,
    user_sessions: UserSessionsTable = Depends(get_user_sessions_table)
):
    """데이터 삽입"""
    try:
        user_sessions.connect()
        
        insert_data = data.dict()
        result_id = user_sessions.save(insert_data)
        
        # 삽입된 데이터 조회
        new_record = user_sessions.get_by_id(result_id) if result_id else None
        
        user_sessions.close()
        
        return {
            "success": True,
            "id": result_id,
            "data": new_record,
            "message": "Data inserted successfully"
        }
        
    except Exception as e:
        user_sessions.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/update")
@router.post("/update") 
async def update_data(
    id: int,
    data: UserSessionUpdate,
    user_sessions: UserSessionsTable = Depends(get_user_sessions_table)
):
    """데이터 업데이트"""
    try:
        user_sessions.connect()
        
        # 기존 데이터 확인
        existing = user_sessions.get_by_id(id)
        if not existing:
            user_sessions.close()
            raise HTTPException(status_code=404, detail="Record not found")
        
        # 업데이트 실행
        update_dict = data.dict(exclude_unset=True)
        if update_dict:
            result = user_sessions.update_session(id, **update_dict)
        else:
            result = False
            
        # 업데이트된 데이터 조회
        updated_record = user_sessions.get_by_id(id) if result else None
        
        user_sessions.close()
        
        return {
            "success": result,
            "data": updated_record,
            "message": "Data updated successfully" if result else "No data to update"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        user_sessions.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/delete")
@router.post("/delete")
async def delete_data(
    id: int,
    user_sessions: UserSessionsTable = Depends(get_user_sessions_table)
):
    """데이터 삭제"""
    try:
        user_sessions.connect()
        
        # 삭제 전 데이터 조회
        existing = user_sessions.get_by_id(id)
        if not existing:
            user_sessions.close()
            raise HTTPException(status_code=404, detail="Record not found")
        
        # 삭제 실행
        result = user_sessions.delete(user_sessions.TABLE_NAME, {"id": id})
        
        user_sessions.close()
        
        return {
            "success": result > 0,
            "deleted_count": result,
            "deleted_data": existing,
            "message": f"Deleted {result} record(s)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        user_sessions.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/save")
@router.post("/save")
async def save_data(
    data: Dict[str, Any],
    user_sessions: UserSessionsTable = Depends(get_user_sessions_table)
):
    """데이터 저장 (INSERT 또는 UPDATE)"""
    try:
        user_sessions.connect()
        
        result_id = user_sessions.save(data)
        
        # 저장된 데이터 조회
        saved_record = user_sessions.get_by_id(result_id) if result_id else None
        
        user_sessions.close()
        
        is_update = 'id' in data and data['id']
        
        return {
            "success": True,
            "id": result_id,
            "data": saved_record,
            "operation": "update" if is_update else "insert",
            "message": f"Data {'updated' if is_update else 'inserted'} successfully"
        }
        
    except Exception as e:
        user_sessions.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/excel_down")
@router.post("/excel_down")
async def download_excel(
    request: SelectRequest,
    user_sessions: UserSessionsTable = Depends(get_user_sessions_table)
):
    """엑셀 다운로드"""
    try:
        user_sessions.connect()
        
        # 데이터 조회
        if 'user_id' in request.conditions:
            data = user_sessions.get_by_user(
                request.conditions['user_id'],
                limit=request.limit or 10000
            )
        else:
            data = user_sessions.select(
                user_sessions.TABLE_NAME,
                columns=request.columns,
                condition=request.conditions if request.conditions else None,
                order_by=request.order_by,
                limit=request.limit or 10000
            )
        
        user_sessions.close()
        
        if not data:
            raise HTTPException(status_code=404, detail="No data found")
        
        # DataFrame 생성
        df = pd.DataFrame(data)
        
        # 엑셀 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='User Sessions', index=False)
        
        output.seek(0)
        
        # 파일명 생성
        filename = f"user_sessions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        user_sessions.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/excel_upload")
async def upload_excel(
    file: UploadFile = File(...),
    user_sessions: UserSessionsTable = Depends(get_user_sessions_table)
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
        required_columns = ['user_id', 'session_id', 'ip_address', 'user_agent', 'login_time']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {missing_columns}"
            )
        
        # 데이터 타입 변환
        df['login_time'] = pd.to_datetime(df['login_time'])
        if 'logout_time' in df.columns:
            df['logout_time'] = pd.to_datetime(df['logout_time'], errors='coerce')
        df['user_id'] = df['user_id'].astype(int)
        if 'is_active' in df.columns:
            df['is_active'] = df['is_active'].astype(bool)
        else:
            df['is_active'] = True
        
        # NaN 값 처리
        df = df.where(pd.notnull(df), None)
        
        # 데이터 준비
        data_list = df.to_dict('records')
        
        if not data_list:
            raise HTTPException(status_code=400, detail="No valid data found in file")
        
        # 일괄 삽입
        user_sessions.connect()
        inserted_count = user_sessions.bulk_insert(data_list)
        user_sessions.close()
        
        return {
            "success": True,
            "inserted_count": inserted_count,
            "total_rows": len(df),
            "message": f"Successfully inserted {inserted_count} records"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if 'user_sessions' in locals():
            user_sessions.close()
        raise HTTPException(status_code=500, detail=str(e))

# 추가 고급 엔드포인트
@router.post("/aggregate")
async def get_aggregated_data(
    request: AggregateRequest,
    user_sessions: UserSessionsTable = Depends(get_user_sessions_table)
):
    """집계 데이터 조회"""
    try:
        user_sessions.connect()
        
        data = user_sessions.get_session_statistics(
            user_id=request.user_id,
            interval=request.interval,
            start_time=request.start_time,
            end_time=request.end_time
        )
        
        user_sessions.close()
        
        return {
            "success": True,
            "data": data,
            "count": len(data),
            "interval": request.interval
        }
        
    except Exception as e:
        user_sessions.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk_insert")
async def bulk_insert_data(
    request: BulkInsertRequest,
    user_sessions: UserSessionsTable = Depends(get_user_sessions_table)
):
    """대량 데이터 삽입"""
    try:
        data_list = [item.dict() for item in request.data]
        
        user_sessions.connect()
        inserted_count = user_sessions.bulk_insert(data_list)
        user_sessions.close()
        
        return {
            "success": True,
            "inserted_count": inserted_count,
            "message": f"Successfully inserted {inserted_count} records"
        }
        
    except Exception as e:
        user_sessions.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_old_data")
async def delete_old_data(
    request: DeleteOldDataRequest,
    user_sessions: UserSessionsTable = Depends(get_user_sessions_table)
):
    """오래된 데이터 삭제"""
    try:
        user_sessions.connect()
        deleted_count = user_sessions.delete_old_sessions(days=request.days)
        user_sessions.close()
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Successfully deleted {deleted_count} sessions older than {request.days} days"
        }
        
    except Exception as e:
        user_sessions.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active_sessions")
@router.post("/active_sessions")
async def get_active_sessions(
    request: ActiveSessionsRequest,
    user_sessions: UserSessionsTable = Depends(get_user_sessions_table)
):
    """활성 세션 조회"""
    try:
        user_sessions.connect()
        
        conditions = {"is_active": True}
        if request.user_id:
            conditions["user_id"] = request.user_id
        if request.device_type:
            conditions["device_type"] = request.device_type
            
        data = user_sessions.select(
            user_sessions.TABLE_NAME,
            condition=conditions,
            order_by="login_time DESC",
            limit=request.limit
        )
        
        user_sessions.close()
        
        return {
            "success": True,
            "data": data,
            "active_count": len(data),
            "filters": conditions
        }
        
    except Exception as e:
        user_sessions.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logout_session")
async def logout_session(
    session_id: str,
    user_sessions: UserSessionsTable = Depends(get_user_sessions_table)
):
    """세션 로그아웃 처리"""
    try:
        user_sessions.connect()
        
        # 세션 찾기
        session = user_sessions.get_by_session_id(session_id)
        if not session:
            user_sessions.close()
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 로그아웃 처리
        update_data = {
            "logout_time": datetime.now(),
            "is_active": False
        }
        
        result = user_sessions.update_session(session['id'], **update_data)
        
        # 업데이트된 세션 조회
        updated_session = user_sessions.get_by_id(session['id']) if result else None
        
        user_sessions.close()
        
        return {
            "success": result,
            "session_id": session_id,
            "data": updated_session,
            "message": "Session logged out successfully" if result else "Failed to logout session"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        user_sessions.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user_sessions/{user_id}")
async def get_user_sessions(
    user_id: int,
    active_only: bool = False,
    limit: int = 100,
    user_sessions: UserSessionsTable = Depends(get_user_sessions_table)
):
    """특정 사용자의 세션 목록 조회"""
    try:
        user_sessions.connect()
        
        if active_only:
            sessions = user_sessions.get_active_sessions_by_user(user_id, limit=limit)
        else:
            sessions = user_sessions.get_by_user(user_id, limit=limit)
            
        user_sessions.close()
        
        return {
            "success": True,
            "user_id": user_id,
            "sessions": sessions,
            "session_count": len(sessions),
            "active_only": active_only
        }
        
    except Exception as e:
        user_sessions.close()
        raise HTTPException(status_code=500, detail=str(e))

# 헬스체크
@router.get("/health")
async def health_check(user_sessions: UserSessionsTable = Depends(get_user_sessions_table)):
    """API 헬스체크"""
    try:
        con = user_sessions.connect()
        # 간단한 쿼리로 DB 연결 확인
        result = user_sessions.query("SELECT 1", con=con)
        user_sessions.close()
        
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
