# -*- coding: utf-8 -*-
"""
    timescaledb_manager_v2.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Database connection pool manager for PostgreSQL/TimescaleDB
    싱글톤 인스턴스 getter를 제공함.

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
import logging
from typing import Optional, Dict, Any, List, Tuple
from contextlib import contextmanager
import threading

class DatabaseConnectionManager:
    """싱글톤 패턴의 데이터베이스 연결 풀 매니저"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, 
                 database: str = "wzdb",
                 user: str = 'wzuser',
                 password: str = 'wzuserpwd!',
                 host: str = "127.0.0.1",
                 port: int = 5432,
                 minconn: int = 2,
                 maxconn: int = 20,
                 logger: Optional[logging.Logger] = None):
        
        # 이미 초기화되었으면 스킵
        if hasattr(self, 'pool'):
            return
            
        self.database = database
        self.user = user
        self.host = host
        self.port = port
        
        # 로거 설정
        self.logger = logger or logging.getLogger('DatabaseConnectionManager')
        
        try:
            # ThreadedConnectionPool은 thread-safe
            self.pool = ThreadedConnectionPool(
                minconn=minconn,
                maxconn=maxconn,
                user=user,
                password=password,
                host=host,
                port=port,
                database=database
            )
            self.logger.info(f"Connection pool created: {minconn}-{maxconn} connections to {database}@{host}:{port}")
        except Exception as e:
            self.logger.error(f"Failed to create connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """컨텍스트 매니저로 연결 관리"""
        conn = None
        try:
            conn = self.pool.getconn()
            self.logger.debug("Connection acquired from pool")
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Error during connection usage: {e}")
            raise
        finally:
            if conn:
                self.pool.putconn(conn)
                self.logger.debug("Connection returned to pool")
    
    @contextmanager
    def get_cursor(self, commit: bool = False):
        """커서를 직접 반환하는 컨텍스트 매니저"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
                if commit:
                    conn.commit()
                    self.logger.debug("Transaction committed")
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Transaction rolled back due to error: {e}")
                raise
            finally:
                cursor.close()
    
    def execute_query(self,
                     query: str,
                     params: Optional[Tuple] = None,
                     fetch_one: bool = False,
                     fetch_all: bool = True,
                     commit: bool = False) -> Any:
        """쿼리 실행 헬퍼 메서드"""
        with self.get_cursor(commit=commit) as cursor:
            self.logger.debug(f"Executing: {query[:100]}{'...' if len(query) > 100 else ''}")
            
            cursor.execute(query, params)
            
            if query.strip().upper().startswith("SELECT") and fetch_all:
                result = cursor.fetchone() if fetch_one else cursor.fetchall()
                self.logger.debug(f"Fetched {1 if fetch_one else len(result) if result else 0} rows")
                return result
            
            elif query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                if "RETURNING" in query.upper():
                    result = cursor.fetchone() if fetch_one else cursor.fetchall()
                    return result
                return cursor.rowcount
            
            return None
    
    def close_all(self):
        """모든 연결 종료"""
        if hasattr(self, 'pool') and self.pool:
            self.pool.closeall()
            self.logger.info("All connections closed")
    
    def get_pool_status(self) -> Dict[str, int]:
        """연결 풀 상태 반환"""
        if hasattr(self, 'pool') and self.pool:
            return {
                "closed": self.pool.closed,
                "minconn": self.pool.minconn,
                "maxconn": self.pool.maxconn,
                # ThreadedConnectionPool doesn't expose current connections easily
            }
        return {}


class BaseTable:
    """모든 테이블 클래스의 기본 클래스"""
    
    TABLE_NAME = None  # 하위 클래스에서 정의
    
    def __init__(self, db_manager: Optional[DatabaseConnectionManager] = None, logger: Optional[logging.Logger] = None):
        """
        Args:
            db_manager: DatabaseConnectionManager 인스턴스 (없으면 기본값으로 생성)
            logger: 로거 인스턴스
        """
        self.db_manager = db_manager or DatabaseConnectionManager()
        self.logger = logger or logging.getLogger(f'{self.__class__.__name__}')
        self.logger.info(f"Initialized {self.__class__.__name__} for table: {self.TABLE_NAME}")
    
    def query(self, stmt: str, data: Tuple = (), one: bool = False, commit: bool = False) -> Any:
        """쿼리 실행"""
        return self.db_manager.execute_query(stmt, data, fetch_one=one, commit=commit)
    
    def insert(self, table: str, data: Dict[str, Any], return_key: str = "", commit: bool = True) -> Any:
        """데이터 삽입"""
        cols = ', '.join(data.keys())
        vals = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({cols}) VALUES ({vals})"
        
        if return_key:
            query += f" RETURNING {return_key}"
        
        self.logger.info(f"Inserting into {table}: {list(data.keys())}")
        
        result = self.db_manager.execute_query(query, tuple(data.values()), fetch_one=True, commit=commit)
        
        if return_key and result:
            return result.get(return_key)
        return result
    
    def update(self, table: str, data: Dict[str, Any], condition: Dict[str, Any], 
               return_key: str = "", commit: bool = True) -> Any:
        """데이터 업데이트"""
        set_clause = ', '.join([f"{col} = %s" for col in data.keys()])
        cond_clause = ' AND '.join([f"{col} = %s" for col in condition.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {cond_clause}"
        
        if return_key:
            query += f" RETURNING {return_key}"
        
        self.logger.info(f"Updating {table}: SET {list(data.keys())} WHERE {list(condition.keys())}")
        
        params = tuple(data.values()) + tuple(condition.values())
        result = self.db_manager.execute_query(query, params, fetch_one=True, commit=commit)
        
        if return_key and result:
            return result.get(return_key)
        return result
    
    def delete(self, table: str, condition: Dict[str, Any], commit: bool = True) -> int:
        """데이터 삭제"""
        cond_clause = ' AND '.join([f"{col} = %s" for col in condition.keys()])
        query = f"DELETE FROM {table} WHERE {cond_clause}"
        
        self.logger.info(f"Deleting from {table} WHERE {list(condition.keys())}")
        
        return self.db_manager.execute_query(query, tuple(condition.values()), commit=commit)
    
    def select(self, table: str, columns: str = '*', condition: Optional[Dict[str, Any]] = None,
               one: bool = False, order_by: Optional[str] = None, limit: Optional[int] = None,
               offset: Optional[int] = None) -> Any:
        """데이터 조회"""
        query_parts = [f"SELECT {columns} FROM {table}"]
        params = []
        
        if condition:
            cond_clause = ' AND '.join([f"{col} = %s" for col in condition.keys()])
            query_parts.append(f"WHERE {cond_clause}")
            params.extend(condition.values())
        
        if order_by:
            query_parts.append(f"ORDER BY {order_by}")
        
        if limit:
            query_parts.append(f"LIMIT {limit}")
        
        if offset:
            query_parts.append(f"OFFSET {offset}")
        
        query = " ".join(query_parts)
        
        self.logger.info(f"Selecting from {table}: columns={columns}, condition={list(condition.keys()) if condition else 'None'}")
        
        return self.db_manager.execute_query(query, tuple(params), fetch_one=one)
    
    # 하위 호환성을 위한 메서드들
    def connect(self):
        """더 이상 필요하지 않음 - 하위 호환성을 위해 유지"""
        pass
    
    def close(self):
        """더 이상 필요하지 않음 - 하위 호환성을 위해 유지"""
        pass
    
    def commit(self):
        """더 이상 필요하지 않음 - 하위 호환성을 위해 유지"""
        pass
    
    def rollback(self):
        """더 이상 필요하지 않음 - 하위 호환성을 위해 유지"""
        pass


# 싱글톤 인스턴스 getter
def get_db_manager(config: Optional[Dict[str, Any]] = None) -> DatabaseConnectionManager:
    """
    데이터베이스 매니저 싱글톤 인스턴스 반환
    
    Args:
        config: 데이터베이스 설정 딕셔너리
    
    Returns:
        DatabaseConnectionManager 인스턴스
    """
    if config:
        return DatabaseConnectionManager(**config)
    return DatabaseConnectionManager()

