# -*- coding: utf-8 -*-
"""
    service_wz_rule_v1
    ~~~~~~~~~~~~~~~~~~~~~~~~

    WZ_RULE table API service router v1

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
from .query_wz_rule_v1 import WzRuleTable
from app_logger import setup_logging, get_logger

logger = get_logger(__name__)

# Pydantic Models for Request/Response
class WzRuleBase(BaseModel):
    rule_name: str
    rule_type: str
    rule_condition: str
    rule_action: str
    priority: Optional[int] = 0
    is_active: Optional[bool] = True
    description: Optional[str] = None
    created_by: Optional[str] = None
    
class WzRuleCreate(WzRuleBase):
    pass

class WzRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    rule_type: Optional[str] = None
    rule_condition: Optional[str] = None
    rule_action: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    updated_by: Optional[str] = None

class WzRuleResponse(WzRuleBase):
    rule_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True

class SelectRequest(BaseModel):
    conditions: Optional[Dict[str, Any]] = {}
    columns: Optional[str] = "*"
    order_by: Optional[str] = "priority ASC, rule_id DESC"
    limit: Optional[int] = 100
    one: Optional[bool] = False

class BulkInsertRequest(BaseModel):
    data: List[WzRuleCreate]

class RuleTypeRequest(BaseModel):
    rule_type: str
    is_active: Optional[bool] = True

class PriorityUpdateRequest(BaseModel):
    rule_id: int
    new_priority: int = Field(ge=0)

# API Router 생성
router = APIRouter(
    prefix="/WZ_RULE/api/v1",
    tags=["wz_rule_v1"],
    responses={404: {"description": "Not found"}},
)

# 의존성: WzRuleTable 인스턴스 생성
def get_wz_rule_table():
    """WzRuleTable 인스턴스를 생성하는 의존성"""
    return WzRuleTable(
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
    wz_rule: WzRuleTable = Depends(get_wz_rule_table)
):
    """데이터 조회"""
    try:
        wz_rule.connect()
        
        # 조건에 따라 다른 조회 메서드 사용
        if 'rule_id' in request.conditions and request.one:
            result = wz_rule.get_by_id(request.conditions['rule_id'])
        elif 'rule_type' in request.conditions:
            result = wz_rule.get_rules_by_type(
                request.conditions['rule_type'],
                is_active=request.conditions.get('is_active', True)
            )
            if request.one and result:
                result = result[0]
        else:
            result = wz_rule.select(
                wz_rule.TABLE_NAME,
                columns=request.columns,
                condition=request.conditions if request.conditions else None,
                one=request.one,
                order_by=request.order_by,
                limit=request.limit,
                usecon=True
            )
        
        wz_rule.close()
        
        return {
            "success": True,
            "data": result,
            "count": len(result) if isinstance(result, list) else 1 if result else 0
        }
        
    except Exception as e:
        wz_rule.close()
        logger.error(f'select_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insert")
@router.post("/insert")
async def insert_data(
    data: WzRuleCreate,
    wz_rule: WzRuleTable = Depends(get_wz_rule_table)
):
    """데이터 삽입"""
    try:
        wz_rule.connect()
        
        insert_data = data.dict()
        insert_data['created_at'] = datetime.now()
        result_id = wz_rule.save(insert_data)
        
        # 삽입된 데이터 조회
        new_record = wz_rule.get_by_id(result_id) if result_id else None
        
        wz_rule.close()
        
        return {
            "success": True,
            "rule_id": result_id,
            "data": new_record,
            "message": "Rule inserted successfully"
        }
        
    except Exception as e:
        wz_rule.close()
        logger.error(f'insert_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/update")
@router.post("/update") 
async def update_data(
    rule_id: int,
    data: WzRuleUpdate,
    wz_rule: WzRuleTable = Depends(get_wz_rule_table)
):
    """데이터 업데이트"""
    try:
        wz_rule.connect()
        
        # 기존 데이터 확인
        existing = wz_rule.get_by_id(rule_id)
        if not existing:
            wz_rule.close()
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # 업데이트 실행
        update_dict = data.dict(exclude_unset=True)
        if update_dict:
            update_dict['updated_at'] = datetime.now()
            result = wz_rule.update_rule(rule_id, **update_dict)
        else:
            result = False
            
        # 업데이트된 데이터 조회
        updated_record = wz_rule.get_by_id(rule_id) if result else None
        
        wz_rule.close()
        
        return {
            "success": result,
            "data": updated_record,
            "message": "Rule updated successfully" if result else "No data to update"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        wz_rule.close()
        logger.error(f'update_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/delete")
@router.post("/delete")
async def delete_data(
    rule_id: int,
    wz_rule: WzRuleTable = Depends(get_wz_rule_table)
):
    """데이터 삭제"""
    try:
        wz_rule.connect()
        
        # 삭제 전 데이터 조회
        existing = wz_rule.get_by_id(rule_id)
        if not existing:
            wz_rule.close()
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # 삭제 실행
        result = wz_rule.delete(wz_rule.TABLE_NAME, {"rule_id": rule_id}, usecon=True)
        
        wz_rule.close()
        
        return {
            "success": result > 0,
            "deleted_count": result,
            "deleted_data": existing,
            "message": f"Deleted {result} record(s)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        wz_rule.close()
        logger.error(f'delete_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/save")
@router.post("/save")
async def save_data(
    data: Dict[str, Any],
    wz_rule: WzRuleTable = Depends(get_wz_rule_table)
):
    """데이터 저장 (INSERT 또는 UPDATE)"""
    try:
        wz_rule.connect()
        
        if 'rule_id' in data and data['rule_id']:
            data['updated_at'] = datetime.now()
        else:
            data['created_at'] = datetime.now()
            
        result_id = wz_rule.save(data)
        
        # 저장된 데이터 조회
        saved_record = wz_rule.get_by_id(result_id) if result_id else None
        
        wz_rule.close()
        
        is_update = 'rule_id' in data and data['rule_id']
        
        return {
            "success": True,
            "rule_id": result_id,
            "data": saved_record,
            "operation": "update" if is_update else "insert",
            "message": f"Rule {'updated' if is_update else 'inserted'} successfully"
        }
        
    except Exception as e:
        wz_rule.close()
        logger.error(f'save_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/excel_down")
@router.post("/excel_down")
async def download_excel(
    request: SelectRequest,
    wz_rule: WzRuleTable = Depends(get_wz_rule_table)
):
    """엑셀 다운로드"""
    try:
        wz_rule.connect()
        
        # 데이터 조회
        if 'rule_type' in request.conditions:
            data = wz_rule.get_rules_by_type(
                request.conditions['rule_type'],
                is_active=request.conditions.get('is_active', True)
            )
        else:
            data = wz_rule.select(
                wz_rule.TABLE_NAME,
                columns=request.columns,
                condition=request.conditions if request.conditions else None,
                order_by=request.order_by,
                limit=request.limit or 10000,
                usecon=True
            )
        
        wz_rule.close()
        
        if not data:
            raise HTTPException(status_code=404, detail="No data found")
        
        # DataFrame 생성
        df = pd.DataFrame(data)
        
        # 엑셀 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='WZ Rule Data', index=False)
        
        output.seek(0)
        
        # 파일명 생성
        filename = f"wz_rule_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        wz_rule.close()
        logger.error(f'download_excel error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/excel_upload")
async def upload_excel(
    file: UploadFile = File(...),
    wz_rule: WzRuleTable = Depends(get_wz_rule_table)
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
        required_columns = ['rule_name', 'rule_type', 'rule_condition', 'rule_action']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {missing_columns}"
            )
        
        # 기본값 설정
        if 'priority' not in df.columns:
            df['priority'] = 0
        if 'is_active' not in df.columns:
            df['is_active'] = True
        
        # 데이터 타입 변환
        df['priority'] = pd.to_numeric(df['priority'], errors='coerce').fillna(0).astype(int)
        df['is_active'] = df['is_active'].astype(bool)
        
        # 타임스탬프 추가
        df['created_at'] = datetime.now()
        
        # NaN 값을 None으로 변환
        df = df.where(pd.notnull(df), None)
        
        # 데이터 준비
        data_list = df.to_dict('records')
        
        if not data_list:
            raise HTTPException(status_code=400, detail="No valid data found in file")
        
        # 일괄 삽입
        wz_rule.connect()
        inserted_count = wz_rule.bulk_insert(data_list)
        wz_rule.close()
        
        return {
            "success": True,
            "inserted_count": inserted_count,
            "total_rows": len(df),
            "message": f"Successfully inserted {inserted_count} records"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if 'wz_rule' in locals():
            wz_rule.close()
        logger.error(f'upload_excel error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

# 추가 고급 엔드포인트
@router.post("/bulk_insert")
async def bulk_insert_data(
    request: BulkInsertRequest,
    wz_rule: WzRuleTable = Depends(get_wz_rule_table)
):
    """대량 데이터 삽입"""
    try:
        data_list = []
        for item in request.data:
            data_dict = item.dict()
            data_dict['created_at'] = datetime.now()
            data_list.append(data_dict)
        
        wz_rule.connect()
        inserted_count = wz_rule.bulk_insert(data_list)
        wz_rule.close()
        
        return {
            "success": True,
            "inserted_count": inserted_count,
            "message": f"Successfully inserted {inserted_count} records"
        }
        
    except Exception as e:
        wz_rule.close()
        logger.error(f'bulk_insert_data error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rules/type/{rule_type}")
async def get_rules_by_type(
    rule_type: str,
    is_active: Optional[bool] = True,
    wz_rule: WzRuleTable = Depends(get_wz_rule_table)
):
    """룰 타입별 조회"""
    try:
        wz_rule.connect()
        rules = wz_rule.get_rules_by_type(rule_type, is_active=is_active)
        wz_rule.close()
        
        return {
            "success": True,
            "rule_type": rule_type,
            "is_active": is_active,
            "data": rules,
            "count": len(rules)
        }
        
    except Exception as e:
        wz_rule.close()
        logger.error(f'get_rules_by_type error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rules/activate/{rule_id}")
async def activate_rule(
    rule_id: int,
    wz_rule: WzRuleTable = Depends(get_wz_rule_table)
):
    """룰 활성화"""
    try:
        wz_rule.connect()
        
        # 룰 존재 확인
        existing = wz_rule.get_by_id(rule_id)
        if not existing:
            wz_rule.close()
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # 활성화
        result = wz_rule.update_rule(rule_id, is_active=True, updated_at=datetime.now())
        
        # 업데이트된 데이터 조회
        updated_record = wz_rule.get_by_id(rule_id) if result else None
        
        wz_rule.close()
        
        return {
            "success": result,
            "data": updated_record,
            "message": "Rule activated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        wz_rule.close()
        logger.error(f'activate_rule error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rules/deactivate/{rule_id}")
async def deactivate_rule(
    rule_id: int,
    wz_rule: WzRuleTable = Depends(get_wz_rule_table)
):
    """룰 비활성화"""
    try:
        wz_rule.connect()
        
        # 룰 존재 확인
        existing = wz_rule.get_by_id(rule_id)
        if not existing:
            wz_rule.close()
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # 비활성화
        result = wz_rule.update_rule(rule_id, is_active=False, updated_at=datetime.now())
        
        # 업데이트된 데이터 조회
        updated_record = wz_rule.get_by_id(rule_id) if result else None
        
        wz_rule.close()
        
        return {
            "success": result,
            "data": updated_record,
            "message": "Rule deactivated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        wz_rule.close()
        logger.error(f'deactivate_rule error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rules/update_priority")
async def update_priority(
    request: PriorityUpdateRequest,
    wz_rule: WzRuleTable = Depends(get_wz_rule_table)
):
    """룰 우선순위 업데이트"""
    try:
        wz_rule.connect()
        
        # 룰 존재 확인
        existing = wz_rule.get_by_id(request.rule_id)
        if not existing:
            wz_rule.close()
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # 우선순위 업데이트
        result = wz_rule.update_rule(
            request.rule_id, 
            priority=request.new_priority, 
            updated_at=datetime.now()
        )
        
        # 업데이트된 데이터 조회
        updated_record = wz_rule.get_by_id(request.rule_id) if result else None
        
        wz_rule.close()
        
        return {
            "success": result,
            "data": updated_record,
            "old_priority": existing.get('priority'),
            "new_priority": request.new_priority,
            "message": "Priority updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        wz_rule.close()
        logger.error(f'update_priority error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rules/types")
async def get_rule_types(
    wz_rule: WzRuleTable = Depends(get_wz_rule_table)
):
    """모든 룰 타입 목록 조회"""
    try:
        wz_rule.connect()
        
        # DISTINCT rule_type 조회
        query = f"SELECT DISTINCT rule_type FROM {wz_rule.TABLE_NAME} ORDER BY rule_type"
        result = wz_rule.query(query)
        
        rule_types = [row['rule_type'] for row in result] if result else []
        
        wz_rule.close()
        
        return {
            "success": True,
            "data": rule_types,
            "count": len(rule_types)
        }
        
    except Exception as e:
        wz_rule.close()
        logger.error(f'get_rule_types error:{str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

# 헬스체크
@router.get("/health")
async def health_check(wz_rule: WzRuleTable = Depends(get_wz_rule_table)):
    """API 헬스체크"""
    try:
        con = wz_rule.connect()
        # 간단한 쿼리로 DB 연결 확인
        result = wz_rule.query("SELECT 1", con=con)
        wz_rule.close()
        
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