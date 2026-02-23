# -*- coding: utf-8 -*-
"""
    query_wz_appendix
    ~~~~~~~~~~~~~~~~~~~~~~~~

    WZ_APPENDIX table query class

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

#--- query_wz_appendix_v1.py 
#-------------------------------------
from .timescale_dbv1 import TimescaleDB
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

class WzAppendixTable(TimescaleDB):
    """
    WZ_APPENDIX 테이블 전용 쿼리 클래스
    
    테이블 스펙:
    - wzAppendixSeq: SERIAL PRIMARY KEY
    - wzRuleSeq: INTEGER
    - wzAppendixNo: TEXT
    - wzAppendixName: TEXT
    - wzFileType: TEXT
    - wzCreatedBy: TEXT NOT NULL
    - wzModifiedBy: TEXT NOT NULL
    """
    
    TABLE_NAME = "WZ_APPENDIX"
    
    # 테이블 스키마 정의
    SCHEMA = {
        "wzAppendixSeq": "SERIAL PRIMARY KEY",
        "wzRuleSeq": "INTEGER",
        "wzAppendixNo": "TEXT",
        "wzAppendixName": "TEXT",
        "wzFileType": "TEXT",
        "wzCreatedBy": "TEXT NOT NULL",
        "wzModifiedBy": "TEXT NOT NULL"
    }
    
    def __init__(self, database="wzdb", user='wzuser', password='wzuserpwd!', 
                 host="127.0.0.1", port=5432, logger=None):
        super().__init__(database, user, password, host, port, logger)
        self.Log.info(f"WzAppendixTable initialized for table: {self.TABLE_NAME}")
    
    def create_table_if_not_exists(self):
        """테이블이 없으면 생성"""
        columns = []
        for col, spec in self.SCHEMA.items():
            columns.append(f'"{col}" {spec}')
        
        create_stmt = f"""
        CREATE TABLE IF NOT EXISTS "{self.TABLE_NAME}" (
            {', '.join(columns)}
        );
        
        -- 인덱스 생성
        CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME.lower()}_rule 
        ON "{self.TABLE_NAME}" ("wzRuleSeq");
        
        CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME.lower()}_appendix_no 
        ON "{self.TABLE_NAME}" ("wzAppendixNo");
        """
        
        try:
            self.query(create_stmt, commit=True)
            self.Log.info(f"Table {self.TABLE_NAME} created/verified successfully")
            return True
        except Exception as e:
            self.Log.error(f"Failed to create table: {e}")
            return False
    
    def save(self, data: Dict[str, Any], user: str = "system") -> Optional[int]:
        """
        데이터 저장 (INSERT 또는 UPDATE)
        wzAppendixSeq가 있으면 UPDATE, 없으면 INSERT
        """
        # 사용자 정보 설정
        if 'wzAppendixSeq' in data and data['wzAppendixSeq']:
            # UPDATE
            seq_value = data.pop('wzAppendixSeq')
            data['wzModifiedBy'] = user
            return self.update(self.TABLE_NAME, data, {"wzAppendixSeq": seq_value}, return_key="wzAppendixSeq")
        else:
            # INSERT
            if 'wzAppendixSeq' in data:
                data.pop('wzAppendixSeq')
            data['wzCreatedBy'] = user
            data['wzModifiedBy'] = user
            return self.insert(self.TABLE_NAME, data, return_key="wzAppendixSeq")
    
    def get_by_seq(self, appendix_seq: int) -> Optional[Dict]:
        """시퀀스로 단일 레코드 조회"""
        self.Log.debug(f"Getting appendix record by seq: {appendix_seq}")
        return self.select(self.TABLE_NAME, condition={"wzAppendixSeq": appendix_seq}, one=True)
    
    def get_by_rule_seq(self, rule_seq: int, limit: int = 100) -> List[Dict]:
        """규칙 시퀀스로 첨부 파일 목록 조회"""
        query = f"""
        SELECT * FROM "{self.TABLE_NAME}"
        WHERE "wzRuleSeq" = %s
        ORDER BY "wzAppendixSeq" DESC
        LIMIT %s
        """
        self.Log.info(f"Getting appendices for rule: {rule_seq}")
        return self.query(query, (rule_seq, limit))
    
    def get_by_appendix_no(self, appendix_no: str) -> Optional[Dict]:
        """첨부 파일 번호로 조회"""
        self.Log.debug(f"Getting appendix by no: {appendix_no}")
        return self.select(self.TABLE_NAME, condition={"wzAppendixNo": appendix_no}, one=True)
    
    def get_by_file_type(self, file_type: str, limit: int = 100) -> List[Dict]:
        """파일 타입별 조회"""
        query = f"""
        SELECT * FROM "{self.TABLE_NAME}"
        WHERE "wzFileType" = %s
        ORDER BY "wzAppendixSeq" DESC
        LIMIT %s
        """
        self.Log.info(f"Getting appendices by file type: {file_type}")
        return self.query(query, (file_type, limit))
    
    def search_by_name(self, name_pattern: str, limit: int = 100) -> List[Dict]:
        """첨부 파일 이름으로 검색 (부분 일치)"""
        query = f"""
        SELECT * FROM "{self.TABLE_NAME}"
        WHERE "wzAppendixName" ILIKE %s
        ORDER BY "wzAppendixSeq" DESC
        LIMIT %s
        """
        self.Log.info(f"Searching appendices by name pattern: {name_pattern}")
        return self.query(query, (f'%{name_pattern}%', limit))
    
    def get_file_type_statistics(self) -> List[Dict]:
        """파일 타입별 통계 조회"""
        query = f"""
        SELECT 
            "wzFileType",
            COUNT(*) as count,
            COUNT(DISTINCT "wzRuleSeq") as rule_count
        FROM "{self.TABLE_NAME}"
        GROUP BY "wzFileType"
        ORDER BY count DESC
        """
        self.Log.info("Getting file type statistics")
        return self.query(query)
    
    def get_by_created_user(self, created_by: str, limit: int = 100) -> List[Dict]:
        """생성자별 조회"""
        query = f"""
        SELECT * FROM "{self.TABLE_NAME}"
        WHERE "wzCreatedBy" = %s
        ORDER BY "wzAppendixSeq" DESC
        LIMIT %s
        """
        self.Log.info(f"Getting appendices created by: {created_by}")
        return self.query(query, (created_by, limit))
    
    def bulk_insert(self, data_list: List[Dict], user: str = "system") -> int:
        """대량 데이터 삽입"""
        if not data_list:
            return 0
        
        # 사용자 정보 추가
        for data in data_list:
            if 'wzCreatedBy' not in data:
                data['wzCreatedBy'] = user
            if 'wzModifiedBy' not in data:
                data['wzModifiedBy'] = user
        
        # 컬럼 순서 보장
        columns = list(data_list[0].keys())
        values_template = "(%s)" % ','.join(['%s'] * len(columns))
        
        # 모든 데이터의 값들을 하나의 리스트로 펼침
        all_values = []
        values_clauses = []
        for data in data_list:
            values_clauses.append(values_template)
            all_values.extend([data[col] for col in columns])
        
        # 컬럼명 이스케이프
        escaped_columns = [f'"{col}"' for col in columns]
        
        query = f"""
        INSERT INTO "{self.TABLE_NAME}" ({','.join(escaped_columns)})
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
    
    def update_file_info(self, appendix_seq: int, file_type: str = None, 
                        appendix_name: str = None, user: str = "system") -> bool:
        """파일 정보 업데이트"""
        update_data = {"wzModifiedBy": user}
        
        if file_type is not None:
            update_data['wzFileType'] = file_type
        if appendix_name is not None:
            update_data['wzAppendixName'] = appendix_name
            
        if len(update_data) == 1:  # 사용자 정보만 있는 경우
            self.Log.warning("No file info to update")
            return False
            
        result = self.update(self.TABLE_NAME, update_data, {"wzAppendixSeq": appendix_seq})
        return result > 0
    
    def delete_by_rule_seq(self, rule_seq: int) -> int:
        """규칙별 첨부 파일 삭제"""
        self.Log.info(f"Deleting appendices for rule: {rule_seq}")
        return self.delete(self.TABLE_NAME, {"wzRuleSeq": rule_seq})
    
    def get_rules_with_appendix_count(self) -> List[Dict]:
        """규칙별 첨부 파일 수 조회"""
        query = f"""
        SELECT 
            "wzRuleSeq",
            COUNT(*) as appendix_count,
            ARRAY_AGG(DISTINCT "wzFileType") as file_types
        FROM "{self.TABLE_NAME}"
        GROUP BY "wzRuleSeq"
        ORDER BY appendix_count DESC
        """
        self.Log.info("Getting rules with appendix count")
        return self.query(query)


# Example Usage
if __name__ == "__main__":
    # Logger 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # WzAppendixTable 인스턴스 생성
    appendix = WzAppendixTable(
        database="your_db",
        user="your_user", 
        password="your_password",
        host="127.0.0.1",
        port=5432
    )
    
    try:
        # 테이블 생성
        appendix.create_table_if_not_exists()
        
        # 단일 데이터 삽입
        new_seq = appendix.save({
            "wzRuleSeq": 1001,
            "wzAppendixNo": "APP001",
            "wzAppendixName": "계약서.pdf",
            "wzFileType": "PDF"
        }, user="admin")
        print(f"Inserted new record with Seq: {new_seq}")
        
        # 시퀀스로 조회
        record = appendix.get_by_seq(new_seq)
        print(f"Retrieved record: {record}")
        
        # 규칙별 첨부 파일 조회
        rule_appendices = appendix.get_by_rule_seq(1001)
        print(f"Appendices for rule 1001: {rule_appendices}")
        
        # 대량 데이터 삽입
        bulk_data = [
            {
                "wzRuleSeq": 1001,
                "wzAppendixNo": "APP002",
                "wzAppendixName": "이미지1.jpg",
                "wzFileType": "JPG"
            },
            {
                "wzRuleSeq": 1001,
                "wzAppendixNo": "APP003",
                "wzAppendixName": "문서.docx",
                "wzFileType": "DOCX"
            },
            {
                "wzRuleSeq": 1002,
                "wzAppendixNo": "APP004",
                "wzAppendixName": "스프레드시트.xlsx",
                "wzFileType": "XLSX"
            }
        ]
        
        inserted_count = appendix.bulk_insert(bulk_data, user="admin")
        print(f"Bulk inserted {inserted_count} records")
        
        # 파일 타입별 통계
        stats = appendix.get_file_type_statistics()
        print(f"File type statistics: {stats}")
        
        # 이름으로 검색
        search_results = appendix.search_by_name("문서")
        print(f"Search results for '문서': {search_results}")
        
        # 파일 타입별 조회
        pdf_files = appendix.get_by_file_type("PDF")
        print(f"PDF files: {pdf_files}")
        
        # 파일 정보 업데이트
        if new_seq:
            updated = appendix.update_file_info(
                new_seq, 
                file_type="PDF", 
                appendix_name="수정된_계약서.pdf",
                user="admin"
            )
            print(f"Update successful: {updated}")
        
        # 데이터 수정 (save 메서드 사용)
        if record:
            record['wzAppendixName'] = "최종_계약서.pdf"
            saved_seq = appendix.save(record, user="admin")
            print(f"Saved (updated) record Seq: {saved_seq}")
        
        # 규칙별 첨부 파일 수 조회
        rule_counts = appendix.get_rules_with_appendix_count()
        print(f"Rules with appendix counts: {rule_counts}")
        
        # 생성자별 조회
        user_files = appendix.get_by_created_user("admin")
        print(f"Files created by admin: {len(user_files)}")
            
    except Exception as e:
        appendix.Log.error(f"Example failed: {e}")
    finally:
        appendix.close()