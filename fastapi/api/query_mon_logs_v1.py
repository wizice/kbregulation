# -*- coding: utf-8 -*-
"""
    query_mon_logs
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Mon_logs table query class for monitoring logs

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

#--- query_mon_logs_v1.py 
#-------------------------------------
from .timescale_dbv1 import TimescaleDB
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import json

class MonLogsTable(TimescaleDB):
    """
    Mon_logs 테이블 전용 쿼리 클래스
    
    테이블 스펙:
    - mon_logs_id: BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY
    - system_name: VARCHAR(50) NOT NULL
    - log_datetime: TIMESTAMP NOT NULL
    - status_code: VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
    - log_status: VARCHAR(20) NOT NULL
    - alert_level: VARCHAR(20) NOT NULL
    - issue_summary: VARCHAR(200)
    - data_summary: VARCHAR(500)
    - raw_log: TEXT NOT NULL
    - metadata: JSONB
    - previous_log_status: VARCHAR(20)
    - status_change: VARCHAR(50)
    - consecutive_days: INTEGER DEFAULT 0
    - week_over_week: VARCHAR(20)
    - date_created: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    - created_by: VARCHAR(50) NOT NULL
    - date_modified: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    - modified_by: VARCHAR(50)
    """
    
    TABLE_NAME = "mon_logs"
    
    # 테이블 스키마 정의
    SCHEMA = {
        "mon_logs_id": "BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY",
        "system_name": "VARCHAR(50) NOT NULL",
        "log_datetime": "TIMESTAMP NOT NULL",
        "status_code": "VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'",
        "log_status": "VARCHAR(20) NOT NULL",
        "alert_level": "VARCHAR(20) NOT NULL",
        "issue_summary": "VARCHAR(200)",
        "data_summary": "VARCHAR(500)",
        "raw_log": "TEXT NOT NULL",
        "metadata": "JSONB",
        "previous_log_status": "VARCHAR(20)",
        "status_change": "VARCHAR(50)",
        "consecutive_days": "INTEGER DEFAULT 0",
        "week_over_week": "VARCHAR(20)",
        "date_created": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "created_by": "VARCHAR(50) NOT NULL",
        "date_modified": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "modified_by": "VARCHAR(50)"
    }
    
    # 알림 레벨 상수
    ALERT_LEVELS = {
        'CRITICAL': 'CRITICAL',
        'WARNING': 'WARNING',
        'INFO': 'INFO',
        'DEBUG': 'DEBUG'
    }
    
    # 로그 상태 상수
    LOG_STATUS = {
        'ERROR': 'ERROR',
        'SUCCESS': 'SUCCESS',
        'PENDING': 'PENDING',
        'FAILED': 'FAILED'
    }
    
    def __init__(self, database="wzdb", user='wzuser', password='wzuserpwd!', 
                 host="127.0.0.1", port=5432, logger=None):
        super().__init__(database, user, password, host, port, logger)
        self.Log.info(f"MonLogsTable initialized for table: {self.TABLE_NAME}")
    
    def create_table_if_not_exists(self):
        """테이블이 없으면 생성"""
        return
        columns = []
        for col, spec in self.SCHEMA.items():
            columns.append(f"{col} {spec}")
        
        create_stmt = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            {', '.join(columns)}
        );
        
        -- 인덱스 생성
        CREATE INDEX IF NOT EXISTS idx_mon_logs_system_datetime 
        ON {self.TABLE_NAME} (system_name, log_datetime);
        
        CREATE INDEX IF NOT EXISTS idx_mon_logs_status_alert 
        ON {self.TABLE_NAME} (log_status, alert_level);
        
        CREATE INDEX IF NOT EXISTS idx_mon_logs_datetime 
        ON {self.TABLE_NAME} (log_datetime);
        
        CREATE INDEX IF NOT EXISTS idx_mon_logs_status 
        ON {self.TABLE_NAME} (status_code);
        
        CREATE INDEX IF NOT EXISTS idx_mon_logs_metadata_gin 
        ON {self.TABLE_NAME} USING gin (metadata);
        
        CREATE INDEX IF NOT EXISTS idx_mon_logs_metadata_service 
        ON {self.TABLE_NAME} ((metadata->>'service'));
        
        CREATE INDEX IF NOT EXISTS idx_mon_logs_metadata_type 
        ON {self.TABLE_NAME} ((metadata->>'type'));
        
        CREATE INDEX IF NOT EXISTS idx_mon_logs_metadata_status 
        ON {self.TABLE_NAME} ((metadata->>'status'));
        
        -- 테이블 코멘트
        COMMENT ON TABLE {self.TABLE_NAME} IS '모니터링 로그';
        COMMENT ON COLUMN {self.TABLE_NAME}.mon_logs_id IS '로그ID';
        COMMENT ON COLUMN {self.TABLE_NAME}.system_name IS '시스템명';
        COMMENT ON COLUMN {self.TABLE_NAME}.log_datetime IS '로그일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.status_code IS '상태코드';
        COMMENT ON COLUMN {self.TABLE_NAME}.log_status IS '로그상태';
        COMMENT ON COLUMN {self.TABLE_NAME}.alert_level IS '알림레벨';
        COMMENT ON COLUMN {self.TABLE_NAME}.issue_summary IS '이슈요약';
        COMMENT ON COLUMN {self.TABLE_NAME}.data_summary IS '데이터요약';
        COMMENT ON COLUMN {self.TABLE_NAME}.raw_log IS '원본로그';
        COMMENT ON COLUMN {self.TABLE_NAME}.metadata IS '구조화된 메타데이터 (JSON)';
        COMMENT ON COLUMN {self.TABLE_NAME}.previous_log_status IS '이전로그상태';
        COMMENT ON COLUMN {self.TABLE_NAME}.status_change IS '상태변경내역';
        COMMENT ON COLUMN {self.TABLE_NAME}.consecutive_days IS '연속일수';
        COMMENT ON COLUMN {self.TABLE_NAME}.week_over_week IS '주간증감률';
        COMMENT ON COLUMN {self.TABLE_NAME}.date_created IS '생성일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.created_by IS '생성자';
        COMMENT ON COLUMN {self.TABLE_NAME}.date_modified IS '수정일시';
        COMMENT ON COLUMN {self.TABLE_NAME}.modified_by IS '수정자';
        """
        
        try:
            self.query(create_stmt, commit=True)
            self.Log.info(f"Table {self.TABLE_NAME} created/verified successfully")
            return True
        except Exception as e:
            self.Log.error(f"Failed to create table: {e}")
            return False
    
    def save(self, data: Dict[str, Any]) -> Optional[int]:
        """
        데이터 저장 (INSERT 또는 UPDATE)
        mon_logs_id가 있으면 UPDATE, 없으면 INSERT
        """
        # 수정 시 date_modified 자동 업데이트
        if 'mon_logs_id' in data and data['mon_logs_id']:
            # UPDATE
            id_value = data.pop('mon_logs_id')
            data['date_modified'] = datetime.now()
            return self.update(self.TABLE_NAME, data, {"mon_logs_id": id_value}, return_key="mon_logs_id")
        else:
            # INSERT
            if 'mon_logs_id' in data:
                data.pop('mon_logs_id')
            return self.insert(self.TABLE_NAME, data, return_key="mon_logs_id")
    
    def get_by_id(self, mon_logs_id: int) -> Optional[Dict]:
        """ID로 단일 레코드 조회"""
        self.Log.debug(f"Getting monitor log record by id: {mon_logs_id}")
        return self.select(self.TABLE_NAME, condition={"mon_logs_id": mon_logs_id}, one=True)
    
    def get_by_system(self, system_name: str, 
                      start_time: Optional[datetime] = None, 
                      end_time: Optional[datetime] = None,
                      limit: int = 100) -> List[Dict]:
        """시스템별 로그 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE system_name = %s
        """
        params = [system_name]
        
        if start_time:
            query += " AND log_datetime >= %s"
            params.append(start_time)
            
        if end_time:
            query += " AND log_datetime <= %s"
            params.append(end_time)
            
        query += " ORDER BY log_datetime DESC LIMIT %s"
        params.append(limit)
        
        self.Log.info(f"Getting logs for system: {system_name}")
        return self.query(query, tuple(params))
    
    def get_latest_by_system(self, system_name: str) -> Optional[Dict]:
        """시스템의 최신 로그 1개 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE system_name = %s
        ORDER BY log_datetime DESC
        LIMIT 1
        """
        self.Log.debug(f"Getting latest log for system: {system_name}")
        return self.query(query, (system_name,), one=True)
    
    def get_by_alert_level(self, alert_level: str, 
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           limit: int = 100) -> List[Dict]:
        """알림 레벨별 로그 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE alert_level = %s
        """
        params = [alert_level]
        
        if start_time:
            query += " AND log_datetime >= %s"
            params.append(start_time)
            
        if end_time:
            query += " AND log_datetime <= %s"
            params.append(end_time)
            
        query += " ORDER BY log_datetime DESC LIMIT %s"
        params.append(limit)
        
        self.Log.info(f"Getting logs by alert level: {alert_level}")
        return self.query(query, tuple(params))
    
    def get_by_metadata(self, metadata_key: str, metadata_value: str,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        limit: int = 100) -> List[Dict]:
        """메타데이터 조건으로 로그 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE metadata->>'{metadata_key}' = %s
        """
        params = [ metadata_value]
        
        if start_time:
            query += " AND log_datetime >= %s"
            params.append(start_time)
            
        if end_time:
            query += " AND log_datetime <= %s"
            params.append(end_time)
            
        query += " ORDER BY log_datetime DESC LIMIT %s"
        params.append(limit)
        
        self.Log.info(f"Getting logs by metadata: {metadata_key}={metadata_value}")
        return self.query(query, tuple(params))
    
    def get_status_summary(self, system_name: Optional[str] = None,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[Dict]:
        """상태별 로그 집계"""
        query = f"""
        SELECT 
            system_name,
            log_status,
            alert_level,
            COUNT(*) as count,
            MIN(log_datetime) as first_occurrence,
            MAX(log_datetime) as last_occurrence
        FROM {self.TABLE_NAME}
        WHERE 1=1
        """
        params = []
        
        if system_name:
            query += " AND system_name = %s"
            params.append(system_name)
            
        if start_time:
            query += " AND log_datetime >= %s"
            params.append(start_time)
            
        if end_time:
            query += " AND log_datetime <= %s"
            params.append(end_time)
            
        query += " GROUP BY system_name, log_status, alert_level ORDER BY count DESC"
        
        self.Log.info("Getting status summary")
        return self.query(query, tuple(params) if params else None)
    
    def get_error_logs(self, system_name: Optional[str] = None,
                       hours: int = 24) -> List[Dict]:
        """최근 에러 로그 조회"""
        start_time = datetime.now() - timedelta(hours=hours)
        
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE log_status = 'ERROR'
            AND log_datetime >= %s
        """
        params = [start_time]
        
        if system_name:
            query += " AND system_name = %s"
            params.append(system_name)
            
        query += " ORDER BY log_datetime DESC"
        
        self.Log.info(f"Getting error logs for last {hours} hours")
        return self.query(query, tuple(params))
    
    def get_consecutive_errors(self, system_name: str, days: int = 3) -> List[Dict]:
        """연속 에러 발생 로그 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE system_name = %s
            AND log_status = 'ERROR'
            AND consecutive_days >= %s
        ORDER BY log_datetime DESC
        """
        
        self.Log.info(f"Getting consecutive errors for {system_name} >= {days} days")
        return self.query(query, (system_name, days))
    
    def bulk_insert(self, data_list: List[Dict]) -> int:
        """대량 로그 삽입"""
        if not data_list:
            return 0
            
        # 필수 필드 확인 및 기본값 설정
        for data in data_list:
            if 'status_code' not in data:
                data['status_code'] = 'ACTIVE'
            if 'consecutive_days' not in data:
                data['consecutive_days'] = 0
            if 'date_created' not in data:
                data['date_created'] = datetime.now()
                
        # 컬럼 순서 보장
        columns = list(data_list[0].keys())
        if 'mon_logs_id' in columns:
            columns.remove('mon_logs_id')
            
        values_template = "(%s)" % ','.join(['%s'] * len(columns))
        
        # 모든 데이터의 값들을 하나의 리스트로 펼침
        all_values = []
        values_clauses = []
        for data in data_list:
            values_clauses.append(values_template)
            for col in columns:
                value = data.get(col)
                # JSONB 타입 처리
                if col == 'metadata' and isinstance(value, dict):
                    value = json.dumps(value)
                all_values.append(value)
        
        query = f"""
        INSERT INTO {self.TABLE_NAME} ({','.join(columns)})
        VALUES {','.join(values_clauses)}
        """
        
        self.Log.info(f"Bulk inserting {len(data_list)} log records")
        try:
            result = self.query(query, tuple(all_values), commit=True)
            self.Log.info(f"Successfully inserted {len(data_list)} log records")
            return len(data_list)
        except Exception as e:
            self.Log.error(f"Bulk insert failed: {e}")
            raise
    
    def update_status_change(self, mon_logs_id: int, new_status: str, 
                           previous_status: str, modified_by: str) -> bool:
        """로그 상태 변경"""
        update_data = {
            'log_status': new_status,
            'previous_log_status': previous_status,
            'status_change': f"{previous_status}->{new_status}",
            'date_modified': datetime.now(),
            'modified_by': modified_by
        }
        
        result = self.update(self.TABLE_NAME, update_data, {"mon_logs_id": mon_logs_id})
        return result > 0
    
    def delete_old_logs(self, days: int = 90) -> int:
        """오래된 로그 삭제"""
        cutoff_date = datetime.now() - timedelta(days=days)
        query = f"DELETE FROM {self.TABLE_NAME} WHERE log_datetime < %s"
        
        self.Log.info(f"Deleting logs older than {days} days (before {cutoff_date})")
        deleted = self.query(query, (cutoff_date,), commit=True)
        self.Log.info(f"Deleted {deleted} old log records")
        return deleted
    
    def get_system_list(self) -> List[Dict]:
        """시스템 목록 조회"""
        query = f"""
        SELECT DISTINCT 
            system_name,
            COUNT(*) as total_logs,
            MIN(log_datetime) as first_log,
            MAX(log_datetime) as last_log,
            SUM(CASE WHEN log_status = 'ERROR' THEN 1 ELSE 0 END) as error_count
        FROM {self.TABLE_NAME}
        GROUP BY system_name
        ORDER BY system_name
        """
        
        self.Log.info("Getting system list")
        return self.query(query)
    
    def search_logs(self, search_text: str, 
                   system_name: Optional[str] = None,
                   limit: int = 100) -> List[Dict]:
        """로그 텍스트 검색"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE (issue_summary ILIKE %s 
            OR data_summary ILIKE %s 
            OR raw_log ILIKE %s)
        """
        search_pattern = f"%{search_text}%"
        params = [search_pattern, search_pattern, search_pattern]
        
        if system_name:
            query += " AND system_name = %s"
            params.append(system_name)
            
        query += " ORDER BY log_datetime DESC LIMIT %s"
        params.append(limit)
        
        self.Log.info(f"Searching logs for: {search_text}")
        return self.query(query, tuple(params))


# Example Usage
if __name__ == "__main__":
    # Logger 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # MonLogsTable 인스턴스 생성
    mon_logs = MonLogsTable(
        database="your_db",
        user="your_user", 
        password="your_password",
        host="127.0.0.1",
        port=5432
    )
    
    try:
        # 테이블 생성
        mon_logs.create_table_if_not_exists()
        
        # 단일 로그 삽입
        new_id = mon_logs.save({
            "system_name": "web-server-01",
            "log_datetime": datetime.now(),
            "log_status": "ERROR",
            "alert_level": "CRITICAL",
            "issue_summary": "Database connection failed",
            "data_summary": "Connection timeout after 30s",
            "raw_log": "2024-01-15 10:30:45 ERROR: Database connection timeout",
            "metadata": {
                "service": "database",
                "type": "connection",
                "status": "failed",
                "error_code": "DB001"
            },
            "created_by": "system"
        })
        print(f"Inserted new log with ID: {new_id}")
        
        # ID로 조회
        log_record = mon_logs.get_by_id(new_id)
        print(f"Retrieved log: {log_record}")
        
        # 시스템별 최신 로그 조회
        latest = mon_logs.get_latest_by_system("web-server-01")
        print(f"Latest log: {latest}")
        
        # 대량 로그 삽입
        bulk_logs = []
        base_time = datetime.now()
        for i in range(10):
            bulk_logs.append({
                "system_name": "web-server-01",
                "log_datetime": base_time - timedelta(minutes=i*10),
                "log_status": "SUCCESS" if i % 3 == 0 else "ERROR",
                "alert_level": "INFO" if i % 3 == 0 else "WARNING",
                "issue_summary": f"Test log {i}",
                "data_summary": f"Test data summary {i}",
                "raw_log": f"Test raw log content {i}",
                "metadata": {
                    "service": "web",
                    "type": "test",
                    "index": i
                },
                "created_by": "test_script"
            })
        
        inserted_count = mon_logs.bulk_insert(bulk_logs)
        print(f"Bulk inserted {inserted_count} logs")
        
        # 알림 레벨별 로그 조회
        critical_logs = mon_logs.get_by_alert_level(
            "CRITICAL",
            start_time=datetime.now() - timedelta(hours=24)
        )
        print(f"Critical logs: {len(critical_logs)}")
        
        # 상태 요약 조회
        summary = mon_logs.get_status_summary(
            system_name="web-server-01",
            start_time=datetime.now() - timedelta(days=7)
        )
        print(f"Status summary: {summary}")
        
        # 에러 로그 조회
        error_logs = mon_logs.get_error_logs(hours=24)
        print(f"Error logs in last 24h: {len(error_logs)}")
        
        # 시스템 목록 조회
        systems = mon_logs.get_system_list()
        print(f"Systems: {systems}")
        
        # 로그 검색
        search_results = mon_logs.search_logs("connection", limit=10)
        print(f"Search results: {len(search_results)}")
        
        # 상태 변경
        if new_id:
            updated = mon_logs.update_status_change(
                new_id, 
                new_status="RESOLVED",
                previous_status="ERROR",
                modified_by="admin"
            )
            print(f"Status update successful: {updated}")
        
        # 메타데이터로 조회
        metadata_logs = mon_logs.get_by_metadata(
            "service", 
            "database",
            limit=5
        )
        print(f"Logs with metadata service=database: {len(metadata_logs)}")
            
    except Exception as e:
        mon_logs.Log.error(f"Example failed: {e}")
    finally:
        mon_logs.close()
