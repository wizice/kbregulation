# -*- coding: utf-8 -*-
"""
    query_mon_systems
    ~~~~~~~~~~~~~~~~~~~~~~~~

    MonSystems table query class

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

from .timescale_dbv1 import TimescaleDB
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import json

class MonSystemsTable(TimescaleDB):
    """
    MonSystems 테이블 전용 쿼리 클래스
    
    테이블 스펙:
    - mon_systems_id: BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY
    - system_name: VARCHAR(50) NOT NULL UNIQUE
    - system_type: VARCHAR(30)
    - check_interval: INTEGER DEFAULT 1440
    - system_config: JSONB
    - date_created: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    - created_by: VARCHAR(50) NOT NULL
    - date_modified: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    - modified_by: VARCHAR(50)
    - status_code: VARCHAR(20) DEFAULT 'ACTIVE'
    - is_active: BOOLEAN DEFAULT TRUE
    """
    
    TABLE_NAME = "mon_systems"
    
    # 테이블 스키마 정의
    SCHEMA = {
        "mon_systems_id": "BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY",
        "system_name": "VARCHAR(50) NOT NULL UNIQUE",
        "system_type": "VARCHAR(30)",
        "check_interval": "INTEGER DEFAULT 1440",
        "system_config": "JSONB",
        "date_created": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "created_by": "VARCHAR(50) NOT NULL",
        "date_modified": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "modified_by": "VARCHAR(50)",
        "status_code": "VARCHAR(20) DEFAULT 'ACTIVE'",
        "is_active": "BOOLEAN DEFAULT TRUE"
    }
    
    def __init__(self, database="wzdb", user='wzuser', password='wzuserpwd!', 
                 host="127.0.0.1", port=5432, logger=None):
        super().__init__(database, user, password, host, port, logger)
        self.Log.info(f"MonSystemsTable initialized for table: {self.TABLE_NAME}")
    
    def create_table_if_not_exists(self):
        """테이블이 없으면 생성"""
        columns = []
        for col, spec in self.SCHEMA.items():
            columns.append(f"{col} {spec}")
        
        create_stmt = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            {', '.join(columns)}
        );
        
        -- 인덱스 생성
        CREATE INDEX IF NOT EXISTS idx_mon_systems_status 
        ON {self.TABLE_NAME} (status_code);
        
        CREATE INDEX IF NOT EXISTS idx_mon_systems_active 
        ON {self.TABLE_NAME} (is_active);
        
        CREATE INDEX IF NOT EXISTS idx_mon_systems_type 
        ON {self.TABLE_NAME} (system_type);
        
        -- 테이블 코멘트
        COMMENT ON TABLE {self.TABLE_NAME} IS '모니터링 시스템정보';
        COMMENT ON COLUMN {self.TABLE_NAME}.mon_systems_id IS '시스템ID';
        COMMENT ON COLUMN {self.TABLE_NAME}.system_name IS '시스템명';
        COMMENT ON COLUMN {self.TABLE_NAME}.system_type IS '시스템유형';
        COMMENT ON COLUMN {self.TABLE_NAME}.check_interval IS '점검주기(분)';
        COMMENT ON COLUMN {self.TABLE_NAME}.system_config IS '시스템 설정정보 (JSON)';
        COMMENT ON COLUMN {self.TABLE_NAME}.date_created IS '생성일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.created_by IS '생성자';
        COMMENT ON COLUMN {self.TABLE_NAME}.date_modified IS '수정일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.modified_by IS '수정자';
        COMMENT ON COLUMN {self.TABLE_NAME}.status_code IS '상태코드';
        COMMENT ON COLUMN {self.TABLE_NAME}.is_active IS '활성화여부';
        """
        
        try:
            self.query(create_stmt, commit=True)
            self.Log.info(f"Table {self.TABLE_NAME} created/verified successfully")
            return True
        except Exception as e:
            self.Log.error(f"Failed to create table: {e}")
            return False
    
    def save(self, data: Dict[str, Any], user: str = None) -> Optional[int]:
        """
        데이터 저장 (INSERT 또는 UPDATE)
        mon_systems_id가 있으면 UPDATE, 없으면 INSERT
        """
        # 시간 정보 자동 설정
        if 'mon_systems_id' in data and data['mon_systems_id']:
            # UPDATE
            id_value = data.pop('mon_systems_id')
            data['date_modified'] = datetime.now()
            if user:
                data['modified_by'] = user
            return self.update(self.TABLE_NAME, data, {"mon_systems_id": id_value}, 
                             return_key="mon_systems_id")
        else:
            # INSERT
            if 'mon_systems_id' in data:
                data.pop('mon_systems_id')
            data['date_created'] = datetime.now()
            data['date_modified'] = datetime.now()
            if user and 'created_by' not in data:
                data['created_by'] = user
            return self.insert(self.TABLE_NAME, data, return_key="mon_systems_id")
    
    def get_by_id(self, mon_systems_id: int) -> Optional[Dict]:
        """ID로 단일 시스템 조회"""
        self.Log.debug(f"Getting system by id: {mon_systems_id}")
        return self.select(self.TABLE_NAME, 
                         condition={"mon_systems_id": mon_systems_id}, 
                         one=True)
    
    def get_by_name(self, system_name: str) -> Optional[Dict]:
        """시스템명으로 조회"""
        self.Log.debug(f"Getting system by name: {system_name}")
        return self.select(self.TABLE_NAME, 
                         condition={"system_name": system_name}, 
                         one=True)
    
    def get_active_systems(self, system_type: str = None) -> List[Dict]:
        """활성화된 시스템 목록 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE is_active = TRUE AND status_code = 'ACTIVE'
        """
        params = []
        
        if system_type:
            query += " AND system_type = %s"
            params.append(system_type)
            
        query += " ORDER BY system_name"
        
        self.Log.info(f"Getting active systems, type: {system_type}")
        return self.query(query, tuple(params) if params else None)
    
    def get_systems_by_type(self, system_type: str) -> List[Dict]:
        """시스템 유형별 조회"""
        self.Log.info(f"Getting systems by type: {system_type}")
        return self.select(self.TABLE_NAME, 
                         condition={"system_type": system_type},
                         orderby="system_name")
    
    def get_systems_for_check(self, check_time: datetime = None) -> List[Dict]:
        """점검이 필요한 시스템 목록 조회"""
        if not check_time:
            check_time = datetime.now()
            
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE is_active = TRUE 
          AND status_code = 'ACTIVE'
          AND date_modified + (check_interval || ' minutes')::INTERVAL <= %s
        ORDER BY date_modified
        """
        
        self.Log.info(f"Getting systems requiring check at: {check_time}")
        return self.query(query, (check_time,))
    
    def update_system_config(self, mon_systems_id: int, config: Dict, 
                           user: str = None) -> bool:
        """시스템 설정 정보 업데이트"""
        update_data = {
            'system_config': json.dumps(config) if isinstance(config, dict) else config,
            'date_modified': datetime.now()
        }
        if user:
            update_data['modified_by'] = user
            
        result = self.update(self.TABLE_NAME, update_data, 
                           {"mon_systems_id": mon_systems_id})
        return result > 0
    
    def activate_system(self, mon_systems_id: int, user: str = None) -> bool:
        """시스템 활성화"""
        update_data = {
            'is_active': True,
            'status_code': 'ACTIVE',
            'date_modified': datetime.now()
        }
        if user:
            update_data['modified_by'] = user
            
        result = self.update(self.TABLE_NAME, update_data, 
                           {"mon_systems_id": mon_systems_id})
        self.Log.info(f"Activated system: {mon_systems_id}")
        return result > 0
    
    def deactivate_system(self, mon_systems_id: int, user: str = None) -> bool:
        """시스템 비활성화"""
        update_data = {
            'is_active': False,
            'status_code': 'INACTIVE',
            'date_modified': datetime.now()
        }
        if user:
            update_data['modified_by'] = user
            
        result = self.update(self.TABLE_NAME, update_data, 
                           {"mon_systems_id": mon_systems_id})
        self.Log.info(f"Deactivated system: {mon_systems_id}")
        return result > 0
    
    def get_system_summary(self) -> Dict[str, Any]:
        """시스템 요약 정보 조회"""
        query = f"""
        SELECT 
            COUNT(*) as total_systems,
            COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_systems,
            COUNT(CASE WHEN is_active = FALSE THEN 1 END) as inactive_systems,
            system_type,
            COUNT(*) as type_count
        FROM {self.TABLE_NAME}
        GROUP BY system_type
        """
        
        type_summary = self.query(query)
        
        # 전체 요약
        total_query = f"""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active,
            COUNT(CASE WHEN is_active = FALSE THEN 1 END) as inactive
        FROM {self.TABLE_NAME}
        """
        
        totals = self.query(total_query, one=True)
        
        return {
            "total_systems": totals['total'],
            "active_systems": totals['active'],
            "inactive_systems": totals['inactive'],
            "by_type": type_summary
        }
    
    def search_systems(self, search_term: str, 
                      status_code: str = None,
                      is_active: bool = None) -> List[Dict]:
        """시스템 검색"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE (system_name ILIKE %s OR system_type ILIKE %s)
        """
        params = [f'%{search_term}%', f'%{search_term}%']
        
        if status_code is not None:
            query += " AND status_code = %s"
            params.append(status_code)
            
        if is_active is not None:
            query += " AND is_active = %s"
            params.append(is_active)
            
        query += " ORDER BY system_name"
        
        self.Log.info(f"Searching systems with term: {search_term}")
        return self.query(query, tuple(params))
    
    def bulk_update_check_interval(self, system_ids: List[int], 
                                  check_interval: int,
                                  user: str = None) -> int:
        """여러 시스템의 점검주기 일괄 업데이트"""
        if not system_ids:
            return 0
            
        query = f"""
        UPDATE {self.TABLE_NAME}
        SET check_interval = %s,
            date_modified = %s
        """
        params = [check_interval, datetime.now()]
        
        if user:
            query += ", modified_by = %s"
            params.append(user)
            
        query += f" WHERE mon_systems_id IN ({','.join(['%s'] * len(system_ids))})"
        params.extend(system_ids)
        
        self.Log.info(f"Bulk updating check interval for {len(system_ids)} systems")
        result = self.query(query, tuple(params), commit=True)
        return result


# Example Usage
if __name__ == "__main__":
    # Logger 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # MonSystemsTable 인스턴스 생성
    systems = MonSystemsTable(
        database="your_db",
        user="your_user", 
        password="your_password",
        host="127.0.0.1",
        port=5432
    )
    
    try:
        # 테이블 생성
        systems.create_table_if_not_exists()
        
        # 새 시스템 등록
        new_id = systems.save({
            "system_name": "API_SERVER_01",
            "system_type": "API_SERVER",
            "check_interval": 60,  # 60분마다 체크
            "system_config": {
                "url": "https://api.example.com",
                "timeout": 30,
                "retry": 3
            },
            "created_by": "admin"
        })
        print(f"Created new system with ID: {new_id}")
        
        # ID로 조회
        system = systems.get_by_id(new_id)
        print(f"Retrieved system: {system}")
        
        # 시스템명으로 조회
        system_by_name = systems.get_by_name("API_SERVER_01")
        print(f"System by name: {system_by_name}")
        
        # 활성 시스템 목록 조회
        active_systems = systems.get_active_systems()
        print(f"Active systems: {len(active_systems)}")
        
        # 시스템 설정 업데이트
        if new_id:
            config_updated = systems.update_system_config(
                new_id,
                {"url": "https://api-v2.example.com", "version": "2.0"},
                user="admin"
            )
            print(f"Config update successful: {config_updated}")
        
        # 점검이 필요한 시스템 조회
        systems_to_check = systems.get_systems_for_check()
        print(f"Systems requiring check: {len(systems_to_check)}")
        
        # 시스템 요약 정보
        summary = systems.get_system_summary()
        print(f"System summary: {summary}")
        
        # 시스템 검색
        search_results = systems.search_systems("API", is_active=True)
        print(f"Search results: {len(search_results)} systems found")
        
        # 시스템 비활성화
        if new_id:
            deactivated = systems.deactivate_system(new_id, user="admin")
            print(f"System deactivated: {deactivated}")
            
        # 시스템 활성화
        if new_id:
            activated = systems.activate_system(new_id, user="admin")
            print(f"System activated: {activated}")
        
        # 여러 시스템의 점검주기 일괄 업데이트
        if active_systems:
            system_ids = [s['mon_systems_id'] for s in active_systems[:3]]
            updated_count = systems.bulk_update_check_interval(
                system_ids, 
                check_interval=120,  # 120분으로 변경
                user="admin"
            )
            print(f"Updated check interval for {updated_count} systems")
            
    except Exception as e:
        systems.Log.error(f"Example failed: {e}")
    finally:
        systems.close()