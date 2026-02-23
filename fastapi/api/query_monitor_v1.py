# -*- coding: utf-8 -*-
"""
    query_monitor
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Monitor table query class using TimescaleDB

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

#--- query_monitor_v1.py 
#-------------------------------------
from .timescaledb_manager_v2 import BaseTable, DatabaseConnectionManager
import logging
from app_logger import setup_logging, get_logger
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

class MonitorTable():
    """
    Monitor 테이블 전용 쿼리 클래스
    
    테이블 스펙:
    - id: SERIAL PRIMARY KEY
    - account_seq: INTEGER NOT NULL
    - device_seq: INTEGER NOT NULL
    - timestamp: TIMESTAMPTZ NOT NULL
    - dg: FLOAT
    - dn: FLOAT
    - created_at: TIMESTAMPTZ DEFAULT NOW()
    """
    
    TABLE_NAME = "monitor"
    
    # 테이블 스키마 정의
    SCHEMA = {
        "id": "SERIAL PRIMARY KEY",
        "account_seq": "INTEGER NOT NULL",
        "device_seq": "INTEGER NOT NULL", 
        "timestamp": "TIMESTAMPTZ NOT NULL",
        "dg": "FLOAT",
        "dn": "FLOAT",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()"
    }
    
    def __init__(self, db_manager: Optional[DatabaseConnectionManager] = None, logger: Optional[logging.Logger] = None):
        """
        Args:
            db_manager: 공유할 DatabaseConnectionManager 인스턴스
            logger: 로거 인스턴스
        """
        super().__init__(db_manager, logger)
        self.Log     = logger if logger else get_logger(__name__)
     
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
        
        -- TimescaleDB 하이퍼테이블로 변환
        SELECT create_hypertable('{self.TABLE_NAME}', 'timestamp', if_not_exists => TRUE);
        
        -- 인덱스 생성
        CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_account_device 
        ON {self.TABLE_NAME} (account_seq, device_seq, timestamp DESC);
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
        id가 있으면 UPDATE, 없으면 INSERT
        """
        if 'id' in data and data['id']:
            # UPDATE
            id_value = data.pop('id')
            return self.update(self.TABLE_NAME, data, {"id": id_value}, return_key="id")
        else:
            # INSERT
            if 'id' in data:
                data.pop('id')
            return self.insert(self.TABLE_NAME, data, return_key="id")
    
    def get_by_id(self, id: int) -> Optional[Dict]:
        """ID로 단일 레코드 조회"""
        self.Log.debug(f"Getting monitor record by id: {id}")
        return self.select(self.TABLE_NAME, condition={"id": id}, one=True)
    
    def get_by_device(self, account_seq: int, device_seq: int, 
                      start_time: Optional[datetime] = None, 
                      end_time: Optional[datetime] = None,
                      limit: int = 100) -> List[Dict]:
        """디바이스별 데이터 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE account_seq = %s AND device_seq = %s
        """
        params = [account_seq, device_seq]
        
        if start_time:
            query += " AND timestamp >= %s"
            params.append(start_time)
            
        if end_time:
            query += " AND timestamp <= %s"
            params.append(end_time)
            
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        self.Log.info(f"Getting device data: account={account_seq}, device={device_seq}")
        return self.query(query, tuple(params))
    
    def get_latest_by_device(self, account_seq: int, device_seq: int) -> Optional[Dict]:
        """디바이스의 최신 데이터 1개 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE account_seq = %s AND device_seq = %s
        ORDER BY timestamp DESC
        LIMIT 1
        """
        self.Log.debug(f"Getting latest data for device: {device_seq}")
        return self.query(query, (account_seq, device_seq), one=True)
    
    def get_aggregated_data(self, account_seq: int, device_seq: int,
                           interval: str = '1 hour',
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None) -> List[Dict]:
        """시간 간격별 집계 데이터 조회"""
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(days=1)
            
        query = f"""
        SELECT 
            time_bucket(%s, timestamp) AS bucket,
            account_seq,
            device_seq,
            AVG(dg) as avg_dg,
            AVG(dn) as avg_dn,
            MIN(dg) as min_dg,
            MAX(dg) as max_dg,
            MIN(dn) as min_dn,
            MAX(dn) as max_dn,
            COUNT(*) as data_count
        FROM {self.TABLE_NAME}
        WHERE account_seq = %s AND device_seq = %s
            AND timestamp >= %s AND timestamp <= %s
        GROUP BY bucket, account_seq, device_seq
        ORDER BY bucket DESC
        """
        
        self.Log.info(f"Getting aggregated data: interval={interval}")
        return self.query(query, (interval, account_seq, device_seq, start_time, end_time))
    
    def bulk_insert(self, data_list: List[Dict]) -> int:
        """대량 데이터 삽입"""
        if not data_list:
            return 0
            
        # 컬럼 순서 보장
        columns = list(data_list[0].keys())
        values_template = "(%s)" % ','.join(['%s'] * len(columns))
        
        # 모든 데이터의 값들을 하나의 리스트로 펼침
        all_values = []
        values_clauses = []
        for data in data_list:
            values_clauses.append(values_template)
            all_values.extend([data[col] for col in columns])
        
        query = f"""
        INSERT INTO {self.TABLE_NAME} ({','.join(columns)})
        VALUES {','.join(values_clauses)}
        """
        
        self.Log.info(f"Bulk inserting {len(data_list)} records")
        try:
            result = self.query(query, tuple(all_values), commit=True)
            self.Log.info(f"Successfully inserted {len(data_list)} records")
            return len(data_list)
        except Exception as e:
            self.Log.error(f"Bulk insert failed: {e}")
            raise
    
    def delete_old_data(self, days: int = 30) -> int:
        """오래된 데이터 삭제"""
        cutoff_date = datetime.now() - timedelta(days=days)
        query = f"DELETE FROM {self.TABLE_NAME} WHERE timestamp < %s"
        
        self.Log.info(f"Deleting data older than {days} days (before {cutoff_date})")
        deleted = self.query(query, (cutoff_date,), commit=True)
        self.Log.info(f"Deleted {deleted} old records")
        return deleted
    
    def get_device_list_by_account(self, account_seq: int) -> List[Dict]:
        """계정별 디바이스 목록 조회"""
        query = f"""
        SELECT DISTINCT 
            device_seq,
            MIN(timestamp) as first_seen,
            MAX(timestamp) as last_seen,
            COUNT(*) as data_count
        FROM {self.TABLE_NAME}
        WHERE account_seq = %s
        GROUP BY device_seq
        ORDER BY device_seq
        """
        
        self.Log.info(f"Getting device list for account: {account_seq}")
        return self.query(query, (account_seq,))
    
    def update_device_data(self, id: int, dg: float = None, dn: float = None) -> bool:
        """디바이스 데이터 업데이트"""
        update_data = {}
        if dg is not None:
            update_data['dg'] = dg
        if dn is not None:
            update_data['dn'] = dn
            
        if not update_data:
            self.Log.warning("No data to update")
            return False
            
        result = self.update(self.TABLE_NAME, update_data, {"id": id})
        return result > 0


# Example Usage
if __name__ == "__main__":
    # Logger 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # MonitorTable 인스턴스 생성
    monitor = MonitorTable(
        database="your_db",
        user="your_user", 
        password="your_password",
        host="127.0.0.1",
        port=5432
    )
    
    try:
        # 테이블 생성
        monitor.create_table_if_not_exists()
        
        # 단일 데이터 삽입
        new_id = monitor.save({
            "account_seq": 1,
            "device_seq": 101,
            "timestamp": datetime.now(),
            "dg": 50.25,
            "dn": 30.75
        })
        print(f"Inserted new record with ID: {new_id}")
        
        # ID로 조회
        record = monitor.get_by_id(new_id)
        print(f"Retrieved record: {record}")
        
        # 디바이스별 최신 데이터 조회
        latest = monitor.get_latest_by_device(1, 101)
        print(f"Latest data: {latest}")
        
        # 대량 데이터 삽입
        bulk_data = []
        base_time = datetime.now()
        for i in range(10):
            bulk_data.append({
                "account_seq": 1,
                "device_seq": 101,
                "timestamp": base_time - timedelta(minutes=i*10),
                "dg": 50.0 + i * 0.5,
                "dn": 30.0 + i * 0.3
            })
        
        inserted_count = monitor.bulk_insert(bulk_data)
        print(f"Bulk inserted {inserted_count} records")
        
        # 집계 데이터 조회
        aggregated = monitor.get_aggregated_data(
            account_seq=1,
            device_seq=101,
            interval='30 minutes',
            start_time=datetime.now() - timedelta(hours=2)
        )
        print(f"Aggregated data: {aggregated}")
        
        # 디바이스 목록 조회
        devices = monitor.get_device_list_by_account(1)
        print(f"Devices for account 1: {devices}")
        
        # 데이터 업데이트
        if new_id:
            updated = monitor.update_device_data(new_id, dg=55.5, dn=35.5)
            print(f"Update successful: {updated}")
        
        # 데이터 수정 (save 메서드 사용)
        if record:
            record['dg'] = 60.0
            saved_id = monitor.save(record)
            print(f"Saved (updated) record ID: {saved_id}")
            
    except Exception as e:
        monitor.Log.error(f"Example failed: {e}")
    finally:
        monitor.close()
