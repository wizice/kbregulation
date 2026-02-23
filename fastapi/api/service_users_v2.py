# -*- coding: utf-8 -*-
"""
    service_users_v2
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Users table API service router v1

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""
import os
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Response, Query
from fastapi.responses import StreamingResponse
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
import pandas as pd
import io
from settings import settings
from app_logger import setup_logging, get_logger
from .timescaledb_manager_v2 import get_db_manager
from .query_users_v2 import UsersTable
from fastapi import Request

logger = get_logger(__name__)

# Pydantic Models for Request/Response
# 또는 Pydantic 설정으로 추가 필드 허용:
class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    departments: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = True
    last_login: Optional[datetime] = None
    created_by: Optional[str] = None
    
    # Pydantic 모델은 정의된 필드 외의 추가적인 필드가 들어온 경우 이를 허용하지 않습니다. 
    # 이런 경우, Pydantic은 검증을 실패하게 되고, FastAPI는 해당 요청을 처리하지 못하고 에러를 발생시킵니다.
    class Config:
        extra = "allow"  # 추가 필드 허용

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    departments: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SelectRequest(BaseModel):
    conditions: Optional[Dict[str, Any]] = {}
    columns: Optional[str] = "*"
    order_by: Optional[str] = "created_at DESC"
    limit: Optional[int] = 100
    one: Optional[bool] = False

class BulkInsertRequest(BaseModel):
    data: List[UserCreate]

class UserActivityRequest(BaseModel):
    user_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    activity_type: Optional[str] = None

class DeleteInactiveUsersRequest(BaseModel):
    days: int = Field(default=90, gt=0)

# API Router 생성
router = APIRouter(
    prefix="/api/v1/users",
    tags=["users_v2"],
    responses={404: {"description": "Not found"}},
)

# ===== 의존성 관리 =====
_users_table: Optional[UsersTable] = None

def get_users_table() -> UsersTable:
    """UsersTable 싱글톤 인스턴스"""
    global _users_table
    if _users_table is None:
        # 환경변수나 설정에서 DB 설정을 가져옴
        db_config = {
            "database": settings.DB_NAME or os.getenv("DB_NAME", "wzdb"),
            "user": settings.DB_USER or os.getenv("DB_USER", "wzuser"),
            "password": settings.DB_PASSWORD or os.getenv("DB_PASSWORD", "wzuserpwd!"),
            "host": settings.DB_HOST or os.getenv("DB_HOST", "127.0.0.1"),
            "port": int(settings.DB_PORT or os.getenv("DB_PORT", 5432))
        }
        db_manager = get_db_manager(db_config)
        _users_table = UsersTable(db_manager=db_manager, logger=logger)
        
        # 테이블 생성 확인
        #_users_table.create_table_if_not_exists()
    
    return _users_table


# 기본 CRUD 엔드포인트
@router.get("/hello")
@router.post("/hello")
async def hello():
    """check"""
    return {
        "success": True,
    }

# 기본 CRUD 엔드포인트
@router.post("/select")
async def select_data(
    request: SelectRequest,
    users: UsersTable = Depends(get_users_table)
):
    """데이터 조회"""
    try:
        users.connect()
        
        # 조건에 따라 다른 조회 메서드 사용
        if 'id' in request.conditions and request.one:
            result = users.get_by_id(request.conditions['id'])
        elif 'username' in request.conditions:
            result = users.get_by_username(request.conditions['username'])
            if not request.one and result:
                result = [result]
        elif 'email' in request.conditions:
            result = users.get_by_email(request.conditions['email'])
            if not request.one and result:
                result = [result]
        else:
            result = users.select(
                users.TABLE_NAME,
                columns=request.columns,
                condition=request.conditions if request.conditions else None,
                one=request.one,
                order_by=request.order_by,
                limit=request.limit
            )
        
        users.close()
        
        return {
            "success": True,
            "data": result,
            "count": len(result) if isinstance(result, list) else 1 if result else 0
        }
        
    except Exception as e:
        users.close()
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/select")
async def select_data_get(
    # 개별 조건 파라미터
    id: Optional[int] = Query(None, description="User ID"),
    username: Optional[str] = Query(None, description="Username"),
    email: Optional[str] = Query(None, description="Email"),
    full_name: Optional[str] = Query(None, description="Full name (partial match)"),
    departments: Optional[str] = Query(None, description="departments"),
    role: Optional[str] = Query(None, description="Role"),
    is_active: Optional[bool] = Query(None, description="Active status"),
    search_text: Optional[str] = Query(None, alias="searchText", description="통합 검색어 (여러 필드 검색)"),
    # 페이징 및 정렬
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, le=1000, description="select offset"),
    one: Optional[bool] = Query(False, description="one row"),
    order_by: str = Query("date_created DESC", description="Order by clause"),
    # 응답 옵션
    columns: str = Query("*", description="Columns to select"),
    users: UsersTable = Depends(get_users_table)
):
    """
    데이터 조회 (GET) - 개선된 통합 검색 기능
    
    Examples:
    - /api/v1/users/select?username=test01
    - /api/v1/users/select?email=test@example.com&is_active=true
    - /api/v1/users/select?searchText=홍길동 admin  (여러 키워드로 검색)
    - /api/v1/users/select?departments=IT&limit=50&offset=0
    """
    try:
        users.connect()
        
        logger.debug(f"users_select - search_text: {search_text}, id: {id}")
        
        # 통합 검색이 있는 경우 우선 처리
        if search_text is not None and search_text.strip():
            keywords = search_text.strip().split()
            if keywords:
                # 기본 쿼리 구성
                query = f"SELECT {columns} FROM {users.TABLE_NAME} WHERE 1=1"
                params = []
                
                # 다른 개별 조건들 먼저 추가
                if id is not None:
                    query += " AND users_id = %s"
                    params.append(id)
                if username is not None:
                    query += " AND username = %s"
                    params.append(username)
                if email is not None:
                    query += " AND email = %s"
                    params.append(email)
                if departments is not None:
                    query += " AND departments = %s"
                    params.append(departments)
                if role is not None:
                    query += " AND role = %s"
                    params.append(role)
                if is_active is not None:
                    query += " AND is_active = %s"
                    params.append(is_active)
                
                # 통합 검색 조건 추가 (각 키워드를 OR로 연결)
                query += " AND ("
                or_clauses = []
                for kw in keywords:
                    # 여러 필드에서 키워드 검색
                    or_clauses.append("(full_name ILIKE %s OR email ILIKE %s OR username ILIKE %s OR role ILIKE %s)")
                    params.extend([f"%{kw}%"] * 4)
                
                query += " OR ".join(or_clauses) + ")"
                
                # 정렬 및 페이징
                query += f" ORDER BY {order_by} LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                logger.debug(f"Search query: {query}")
                logger.debug(f"Search params: {params}")
                
                result = users.query(query, tuple(params))
        
        # full_name 개별 검색 (기존 로직)
        elif full_name is not None:
            # ILIKE를 사용한 부분 검색
            query = f"""
            SELECT {columns} FROM {users.TABLE_NAME}
            WHERE full_name ILIKE %s
            """
            params = [f"%{full_name}%"]
            
            # 다른 조건들 추가
            conditions = {}
            if id is not None:
                conditions["users_id"] = id
            if username is not None:
                conditions["username"] = username
            if email is not None:
                conditions["email"] = email
            if departments is not None:
                conditions["departments"] = departments
            if role is not None:
                conditions["role"] = role
            if is_active is not None:
                conditions["is_active"] = is_active
            
            # 다른 조건 추가
            for key, value in conditions.items():
                query += f" AND {key} = %s"
                params.append(value)
            
            query += f" ORDER BY {order_by} LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            result = users.query(query, tuple(params))
            
        # 일반 조회 (조건별 검색)
        else:
            conditions = {}
            if id is not None:
                conditions["users_id"] = id
            if username is not None:
                conditions["username"] = username
            if email is not None:
                conditions["email"] = email
            if departments is not None:
                conditions["departments"] = departments
            if role is not None:
                conditions["role"] = role
            if is_active is not None:
                conditions["is_active"] = is_active
            
            result = users.select(
                users.TABLE_NAME,
                columns=columns,
                condition=conditions if conditions else None,
                one=one,
                order_by=order_by,
                limit=limit,
                offset=offset
            )
        
        users.close()
        
        return {
            "success": True,
            "data": result,
            "count": len(result) if result else 0,
            "limit": limit,
            "offset": offset,
            "search_text": search_text
        }
        
    except Exception as e:
        logger.error(f"select_data_get error: {str(e)}")
        users.close()
        raise HTTPException(status_code=500, detail=str(e))


# @router.get("/insert")
@router.post("/insert")
async def insert_data(
    # request: Request,  # 원본 요청 데이터 확인용
    data: UserBase,
    users: UsersTable = Depends(get_users_table)
):
    """데이터 삽입"""
    try:

        # 원본 요청 body 확인
        # body = await request.body()
        # logger.debug(f"Raw request body: {body.decode()}")
        
        # # 원본 JSON 파싱
        # try:
        #     raw_json = json.loads(body.decode())
        #     logger.debug(f"Raw JSON parsed: {raw_json}")
        #     logger.debug(f"Password in raw JSON: {'password' in raw_json}")
        #     if 'password' in raw_json:
        #         logger.debug(f"Password value in raw JSON: {raw_json['password']}")
        # except:
        #     logger.debug("Could not parse raw JSON")        

        users.connect()
        logger.debug(f".............. insert_data - insert_data: {data.username}")

        created_by = "system"  # 또는 현재 로그인한 사용자 ID
        
        # create_user 메서드를 사용하여 사용자 생성
        result_id = users.create_user(
            username=data.username,
            email=data.email,
            password=data.password,  # 평문 비밀번호 전달
            full_name=data.full_name or "", 
            created_by=created_by,
            departments=data.departments or "",  
            role=data.role or 'user',  
            phone=data.phone
        )
        
        # 삽입된 데이터 조회
        new_record = users.get_by_id(result_id) if result_id else None        
        
        if False:
            # 중복 체크
            existing_user = users.get_by_username(data.username)
            if existing_user:
                users.close()
                raise HTTPException(status_code=400, detail="Username already exists")
            
            existing_email = users.get_by_email(data.email)
            if existing_email:
                users.close()
                raise HTTPException(status_code=400, detail="Email already exists")
            
            insert_data = data.dict()
            logger.debug(f".............. insert_data - insert_data: {insert_data}")
            result_id = users.save(insert_data)
            
            # 삽입된 데이터 조회
            new_record = users.get_by_id(result_id) if result_id else None
        
        users.close()
        
        return {
            "success": True,
            "id": result_id,
            "data": new_record,
            "message": "User created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        users.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/update")
@router.post("/update") 
async def update_data(
    id: int,
    data: UserUpdate,
    users: UsersTable = Depends(get_users_table)
):
    """데이터 업데이트"""
    try:
        users.connect()
        
        # 기존 데이터 확인
        existing = users.get_by_id(id)
        if not existing:
            users.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        # 업데이트 실행
        update_dict = data.dict(exclude_unset=True)
        
        # 중복 체크 (username 변경 시)
        if 'username' in update_dict and update_dict['username'] != existing.get('username'):
            duplicate = users.get_by_username(update_dict['username'])
            if duplicate:
                users.close()
                raise HTTPException(status_code=400, detail="Username already exists")
        
        # 중복 체크 (email 변경 시)
        if 'email' in update_dict and update_dict['email'] != existing.get('email'):
            duplicate = users.get_by_email(update_dict['email'])
            if duplicate:
                users.close()
                raise HTTPException(status_code=400, detail="Email already exists")
        
        if update_dict:
            update_dict['id'] = id
            result = users.save(update_dict)
        else:
            result = False
            
        # 업데이트된 데이터 조회
        updated_record = users.get_by_id(id) if result else None
        
        users.close()
        
        return {
            "success": bool(result),
            "data": updated_record,
            "message": "User updated successfully" if result else "No data to update"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        users.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/delete")
@router.post("/delete")
async def delete_data(
    id: int,
    users: UsersTable = Depends(get_users_table)
):
    """데이터 삭제"""
    try:
        users.connect()
        
        # 삭제 전 데이터 조회
        existing = users.get_by_id(id)
        if not existing:
            users.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        # 삭제 실행
        result = users.delete(users.TABLE_NAME, {"id": id} )
        
        users.close()
        
        return {
            "success": result > 0,
            "deleted_count": result,
            "deleted_data": existing,
            "message": f"Deleted {result} user(s)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        users.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/save")
@router.post("/save")
async def save_data(
    data: Dict[str, Any],
    users: UsersTable = Depends(get_users_table)
):
    """데이터 저장 (INSERT 또는 UPDATE)"""
    try:
        users.connect()
        
        # 중복 체크 (신규 생성 시)
        if 'id' not in data or not data['id']:
            if 'username' in data:
                existing = users.get_by_username(data['username'])
                if existing:
                    users.close()
                    raise HTTPException(status_code=400, detail="Username already exists")
            
            if 'email' in data:
                existing = users.get_by_email(data['email'])
                if existing:
                    users.close()
                    raise HTTPException(status_code=400, detail="Email already exists")
        
        result_id = users.save(data)
        
        # 저장된 데이터 조회
        saved_record = users.get_by_id(result_id) if result_id else None
        
        users.close()
        
        is_update = 'id' in data and data['id']
        
        return {
            "success": True,
            "id": result_id,
            "data": saved_record,
            "operation": "update" if is_update else "insert",
            "message": f"User {'updated' if is_update else 'created'} successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        users.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/excel_down")
@router.post("/excel_down")
async def download_excel(
    request: SelectRequest,
    users: UsersTable = Depends(get_users_table)
):
    """엑셀 다운로드"""
    try:
        users.connect()
        
        # 데이터 조회
        if 'departments' in request.conditions:
            data = users.get_by_departments(request.conditions['departments'])
        elif 'role' in request.conditions:
            data = users.get_by_role(request.conditions['role'])
        else:
            data = users.select(
                users.TABLE_NAME,
                columns=request.columns,
                condition=request.conditions if request.conditions else None,
                order_by=request.order_by,
                limit=request.limit or 10000
            )
        
        users.close()
        
        if not data:
            raise HTTPException(status_code=404, detail="No data found")
        
        # DataFrame 생성
        df = pd.DataFrame(data)
        
        # 민감한 정보 제거
        if 'password' in df.columns:
            df = df.drop('password', axis=1)
        
        # 엑셀 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Users Data', index=False)
        
        output.seek(0)
        
        # 파일명 생성
        filename = f"users_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        users.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/excel_upload")
async def upload_excel(
    file: UploadFile = File(...),
    users: UsersTable = Depends(get_users_table)
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
        required_columns = ['username', 'email', 'password']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {missing_columns}"
            )
        
        # 데이터 타입 변환 및 기본값 설정
        df['is_active'] = df.get('is_active', True).fillna(True)
        if 'last_login' in df.columns:
            df['last_login'] = pd.to_datetime(df['last_login'], errors='coerce')
        
        # NaN 값을 None으로 변환
        df = df.where(pd.notnull(df), None)
        
        # 데이터 준비
        data_list = df.to_dict('records')
        
        if not data_list:
            raise HTTPException(status_code=400, detail="No valid data found in file")
        
        # 중복 체크
        users.connect()
        
        usernames = [d['username'] for d in data_list]
        emails = [d['email'] for d in data_list]
        
        # 중복 username 체크
        if len(usernames) != len(set(usernames)):
            users.close()
            raise HTTPException(status_code=400, detail="Duplicate usernames in file")
        
        # 중복 email 체크
        if len(emails) != len(set(emails)):
            users.close()
            raise HTTPException(status_code=400, detail="Duplicate emails in file")
        
        # 기존 데이터와 중복 체크
        existing_usernames = users.check_existing_usernames(usernames)
        if existing_usernames:
            users.close()
            raise HTTPException(
                status_code=400, 
                detail=f"Following usernames already exist: {', '.join(existing_usernames)}"
            )
        
        existing_emails = users.check_existing_emails(emails)
        if existing_emails:
            users.close()
            raise HTTPException(
                status_code=400, 
                detail=f"Following emails already exist: {', '.join(existing_emails)}"
            )
        
        # 일괄 삽입
        inserted_count = users.bulk_insert(data_list)
        users.close()
        
        return {
            "success": True,
            "inserted_count": inserted_count,
            "total_rows": len(df),
            "message": f"Successfully inserted {inserted_count} users"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if 'users' in locals():
            users.close()
        raise HTTPException(status_code=500, detail=str(e))

# 추가 고급 엔드포인트
@router.post("/bulk_insert")
async def bulk_insert_data(
    request: BulkInsertRequest,
    users: UsersTable = Depends(get_users_table)
):
    """대량 데이터 삽입"""
    try:
        data_list = [item.dict() for item in request.data]
        
        # 중복 체크
        usernames = [d['username'] for d in data_list]
        emails = [d['email'] for d in data_list]
        
        if len(usernames) != len(set(usernames)):
            raise HTTPException(status_code=400, detail="Duplicate usernames in request")
        
        if len(emails) != len(set(emails)):
            raise HTTPException(status_code=400, detail="Duplicate emails in request")
        
        users.connect()
        
        # 기존 데이터와 중복 체크
        existing_usernames = users.check_existing_usernames(usernames)
        if existing_usernames:
            users.close()
            raise HTTPException(
                status_code=400, 
                detail=f"Following usernames already exist: {', '.join(existing_usernames)}"
            )
        
        existing_emails = users.check_existing_emails(emails)
        if existing_emails:
            users.close()
            raise HTTPException(
                status_code=400, 
                detail=f"Following emails already exist: {', '.join(existing_emails)}"
            )
        
        inserted_count = users.bulk_insert(data_list)
        users.close()
        
        return {
            "success": True,
            "inserted_count": inserted_count,
            "message": f"Successfully inserted {inserted_count} users"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        users.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_inactive_users")
async def delete_inactive_users(
    request: DeleteInactiveUsersRequest,
    users: UsersTable = Depends(get_users_table)
):
    """비활성 사용자 삭제"""
    try:
        users.connect()
        deleted_count = users.delete_inactive_users(days=request.days)
        users.close()
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Successfully deleted {deleted_count} inactive users (no login for {request.days} days)"
        }
        
    except Exception as e:
        users.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/departments_list")
async def get_departments_list(
    users: UsersTable = Depends(get_users_table)
):
    """부서 목록 조회"""
    try:
        users.connect()
        departments = users.get_departments_list()
        users.close()
        
        return {
            "success": True,
            "departments": departments,
            "count": len(departments)
        }
        
    except Exception as e:
        users.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/role_list")
async def get_role_list(
    users: UsersTable = Depends(get_users_table)
):
    """역할 목록 조회"""
    try:
        users.connect()
        roles = users.get_role_list()
        users.close()
        
        return {
            "success": True,
            "roles": roles,
            "count": len(roles)
        }
        
    except Exception as e:
        users.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active_users")
async def get_active_users(
    limit: int = 100,
    users: UsersTable = Depends(get_users_table)
):
    """활성 사용자 목록 조회"""
    try:
        users.connect()
        active_users = users.get_active_users(limit=limit)
        users.close()
        
        # 민감한 정보 제거
        for user in active_users:
            if 'password' in user:
                del user['password']
        
        return {
            "success": True,
            "users": active_users,
            "count": len(active_users)
        }
        
    except Exception as e:
        users.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update_last_login")
async def update_last_login(
    user_id: int,
    users: UsersTable = Depends(get_users_table)
):
    """마지막 로그인 시간 업데이트"""
    try:
        users.connect()
        
        # 사용자 확인
        user = users.get_by_id(user_id)
        if not user:
            users.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        # 로그인 시간 업데이트
        result = users.update_last_login(user_id)
        
        # 업데이트된 사용자 정보 조회
        updated_user = users.get_by_id(user_id)
        
        users.close()
        
        # 민감한 정보 제거
        if updated_user and 'password' in updated_user:
            del updated_user['password']
        
        return {
            "success": result,
            "user": updated_user,
            "message": "Last login time updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        users.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/user_activity")
async def get_user_activity(
    request: UserActivityRequest,
    users: UsersTable = Depends(get_users_table)
):
    """사용자 활동 내역 조회"""
    try:
        users.connect()
        
        activities = users.get_user_activity(
            user_id=request.user_id,
            start_date=request.start_date,
            end_date=request.end_date,
            activity_type=request.activity_type
        )
        
        users.close()
        
        return {
            "success": True,
            "activities": activities,
            "count": len(activities)
        }
        
    except Exception as e:
        users.close()
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/check_duplicate", response_class=PlainTextResponse)
async def get_check_duplicate(
    email: Optional[str] = Query(None, description="Email"),
    users: UsersTable = Depends(get_users_table)
):
    try:
        users.connect()

        result = users.get_by_email(email)
        logger.debug(f"service_user.py ---->>> check_duplicate: {result} ")
        users.close()
        
        if result:
            return "Duplicate"
        else:
            return "New"

    except Exception as e:
        users.close()
        logger.error(f"check_duplicate error: {str(e)}")
        return "Error"
    
# 헬스체크
@router.get("/health")
async def health_check(users: UsersTable = Depends(get_users_table)):
    """API 헬스체크"""
    try:
        con     = users.connect()
        # 간단한 쿼리로 DB 연결 확인
        result = users.query("SELECT 1", con=con)
        users.close()
        
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
