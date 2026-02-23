# -*- coding: utf-8 -*-
"""
    query_wz_rule
    ~~~~~~~~~~~~~~~~~~~~~~~~

    WZ_RULE table query class

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

#--- query_wz_rule_v1.py 
#-------------------------------------
from .timescale_dbv1 import TimescaleDB
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

class WzRuleTable(TimescaleDB):
    """
    WZ_RULE 테이블 전용 쿼리 클래스
    
    테이블 스펙:
    - wzRuleSeq: INTEGER PRIMARY KEY
    - wzLevel: INTEGER
    - wzRuleId: INTEGER
    - wzName: TEXT
    - wzEditType: TEXT
    - wzPubNo: TEXT
    - wzEstabDate: TEXT
    - wzLastRevDate: TEXT
    - wzLastRevwDate: TEXT
    - wzMgrDptNm: TEXT
    - wzMgrDptOrgCd: TEXT
    - wzRelDptNm: TEXT
    - wzRelDptOrgCd: TEXT
    - wzRelStandard: TEXT
    - wzCateSeq: INTEGER
    - wzExecDate: TEXT
    - wzLKndName: TEXT
    - wzCloseDate: TEXT
    - wzFileDocx: TEXT NOT NULL
    - wzFilePdf: TEXT NOT NULL
    - wzFileHwp: TEXT
    - wzCreatedBy: TEXT NOT NULL
    - wzModifiedBy: TEXT NOT NULL
    """
    
    TABLE_NAME = "WZ_RULE"
    
    # 테이블 스키마 정의
    SCHEMA = {
        "wzRuleSeq": "INTEGER PRIMARY KEY",
        "wzLevel": "INTEGER",
        "wzRuleId": "INTEGER",
        "wzName": "TEXT",
        "wzEditType": "TEXT",
        "wzPubNo": "TEXT",
        "wzEstabDate": "TEXT",
        "wzLastRevDate": "TEXT",
        "wzLastRevwDate": "TEXT",
        "wzMgrDptNm": "TEXT",
        "wzMgrDptOrgCd": "TEXT",
        "wzRelDptNm": "TEXT",
        "wzRelDptOrgCd": "TEXT",
        "wzRelStandard": "TEXT",
        "wzCateSeq": "INTEGER",
        "wzExecDate": "TEXT",
        "wzLKndName": "TEXT",
        "wzCloseDate": "TEXT",
        "wzFileDocx": "TEXT NOT NULL",
        "wzFilePdf": "TEXT NOT NULL",
        "wzFileHwp": "TEXT",
        "wzCreatedBy": "TEXT NOT NULL",
        "wzModifiedBy": "TEXT NOT NULL"
    }
    
    def __init__(self, database="wzdb", user='wzuser', password='wzuserpwd!', 
                 host="127.0.0.1", port=5432, logger=None):
        super().__init__(database, user, password, host, port, logger)
        self.Log.info(f"WzRuleTable initialized for table: {self.TABLE_NAME}")
    
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
        CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_level 
        ON {self.TABLE_NAME} (wzLevel);
        
        CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_rule_id 
        ON {self.TABLE_NAME} (wzRuleId);
        
        CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_cate_seq 
        ON {self.TABLE_NAME} (wzCateSeq);
        
        CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_mgr_org_cd 
        ON {self.TABLE_NAME} (wzMgrDptOrgCd);
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
        wzRuleSeq가 있으면 UPDATE, 없으면 INSERT
        """
        if 'wzRuleSeq' in data and data['wzRuleSeq']:
            # UPDATE
            rule_seq = data.pop('wzRuleSeq')
            return self.update(self.TABLE_NAME, data, {"wzRuleSeq": rule_seq}, return_key="wzRuleSeq")
        else:
            # INSERT
            if 'wzRuleSeq' in data:
                data.pop('wzRuleSeq')
            return self.insert(self.TABLE_NAME, data, return_key="wzRuleSeq")
    
    def get_by_seq(self, wz_rule_seq: int) -> Optional[Dict]:
        """시퀀스로 단일 레코드 조회"""
        self.Log.debug(f"Getting rule record by seq: {wz_rule_seq}")
        return self.select(self.TABLE_NAME, condition={"wzRuleSeq": wz_rule_seq}, one=True)
    
    def get_by_rule_id(self, wz_rule_id: int) -> List[Dict]:
        """Rule ID로 레코드 조회"""
        self.Log.debug(f"Getting rule records by rule_id: {wz_rule_id}")
        return self.select(self.TABLE_NAME, condition={"wzRuleId": wz_rule_id})
    
    def get_by_level(self, wz_level: int, limit: int = 100) -> List[Dict]:
        """레벨별 규정 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE wzLevel = %s
        ORDER BY wzRuleSeq DESC
        LIMIT %s
        """
        self.Log.info(f"Getting rules by level: {wz_level}")
        return self.query(query, (wz_level, limit))
    
    def get_by_category(self, wz_cate_seq: int, limit: int = 100) -> List[Dict]:
        """카테고리별 규정 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE wzCateSeq = %s
        ORDER BY wzRuleSeq DESC
        LIMIT %s
        """
        self.Log.info(f"Getting rules by category: {wz_cate_seq}")
        return self.query(query, (wz_cate_seq, limit))
    
    def get_by_department(self, dept_org_cd: str, dept_type: str = 'mgr') -> List[Dict]:
        """부서별 규정 조회 (관리부서 또는 관련부서)"""
        if dept_type == 'mgr':
            column = 'wzMgrDptOrgCd'
        elif dept_type == 'rel':
            column = 'wzRelDptOrgCd'
        else:
            raise ValueError("dept_type must be 'mgr' or 'rel'")
        
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE {column} = %s
        ORDER BY wzRuleSeq DESC
        """
        self.Log.info(f"Getting rules by {dept_type} department: {dept_org_cd}")
        return self.query(query, (dept_org_cd,))
    
    def search_by_name(self, search_text: str, limit: int = 100) -> List[Dict]:
        """규정명으로 검색"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE wzName ILIKE %s
        ORDER BY wzRuleSeq DESC
        LIMIT %s
        """
        search_pattern = f"%{search_text}%"
        self.Log.info(f"Searching rules by name: {search_text}")
        return self.query(query, (search_pattern, limit))
    
    def get_by_date_range(self, date_type: str, start_date: str, end_date: str) -> List[Dict]:
        """날짜 범위로 규정 조회"""
        date_columns = {
            'estab': 'wzEstabDate',
            'rev': 'wzLastRevDate',
            'revw': 'wzLastRevwDate',
            'exec': 'wzExecDate',
            'close': 'wzCloseDate'
        }
        
        if date_type not in date_columns:
            raise ValueError(f"date_type must be one of {list(date_columns.keys())}")
        
        column = date_columns[date_type]
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE {column} >= %s AND {column} <= %s
        ORDER BY {column} DESC
        """
        
        self.Log.info(f"Getting rules by {date_type} date range: {start_date} to {end_date}")
        return self.query(query, (start_date, end_date))
    
    def get_active_rules(self, as_of_date: Optional[str] = None) -> List[Dict]:
        """활성 규정 조회 (종료되지 않은 규정)"""
        if not as_of_date:
            as_of_date = datetime.now().strftime('%Y-%m-%d')
        
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE (wzCloseDate IS NULL OR wzCloseDate = '' OR wzCloseDate > %s)
        AND (wzExecDate IS NOT NULL AND wzExecDate != '' AND wzExecDate <= %s)
        ORDER BY wzRuleSeq DESC
        """
        
        self.Log.info(f"Getting active rules as of: {as_of_date}")
        return self.query(query, (as_of_date, as_of_date))
    
    def get_rules_with_files(self, file_type: Optional[str] = None) -> List[Dict]:
        """파일이 있는 규정 조회"""
        if file_type:
            file_columns = {
                'docx': 'wzFileDocx',
                'pdf': 'wzFilePdf',
                'hwp': 'wzFileHwp'
            }
            if file_type not in file_columns:
                raise ValueError(f"file_type must be one of {list(file_columns.keys())}")
            
            column = file_columns[file_type]
            query = f"""
            SELECT * FROM {self.TABLE_NAME}
            WHERE {column} IS NOT NULL AND {column} != ''
            ORDER BY wzRuleSeq DESC
            """
        else:
            query = f"""
            SELECT * FROM {self.TABLE_NAME}
            WHERE (wzFileDocx IS NOT NULL AND wzFileDocx != '')
               OR (wzFilePdf IS NOT NULL AND wzFilePdf != '')
               OR (wzFileHwp IS NOT NULL AND wzFileHwp != '')
            ORDER BY wzRuleSeq DESC
            """
        
        self.Log.info(f"Getting rules with files: {file_type or 'all'}")
        return self.query(query)
    
    def update_file_info(self, wz_rule_seq: int, file_type: str, file_path: str, modified_by: str) -> bool:
        """파일 정보 업데이트"""
        file_columns = {
            'docx': 'wzFileDocx',
            'pdf': 'wzFilePdf',
            'hwp': 'wzFileHwp'
        }
        
        if file_type not in file_columns:
            raise ValueError(f"file_type must be one of {list(file_columns.keys())}")
        
        update_data = {
            file_columns[file_type]: file_path,
            'wzModifiedBy': modified_by
        }
        
        result = self.update(self.TABLE_NAME, update_data, {"wzRuleSeq": wz_rule_seq})
        self.Log.info(f"Updated {file_type} file for rule {wz_rule_seq}: {result > 0}")
        return result > 0
    
    def bulk_insert(self, data_list: List[Dict]) -> int:
        """대량 데이터 삽입"""
        if not data_list:
            return 0
        
        # wzRuleSeq 제거 (자동 생성되는 경우)
        for data in data_list:
            if 'wzRuleSeq' in data:
                data.pop('wzRuleSeq')
        
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """규정 통계 정보 조회"""
        query = f"""
        SELECT 
            COUNT(*) as total_rules,
            COUNT(DISTINCT wzLevel) as level_count,
            COUNT(DISTINCT wzCateSeq) as category_count,
            COUNT(DISTINCT wzMgrDptOrgCd) as mgr_dept_count,
            COUNT(CASE WHEN wzFileDocx IS NOT NULL AND wzFileDocx != '' THEN 1 END) as docx_count,
            COUNT(CASE WHEN wzFilePdf IS NOT NULL AND wzFilePdf != '' THEN 1 END) as pdf_count,
            COUNT(CASE WHEN wzFileHwp IS NOT NULL AND wzFileHwp != '' THEN 1 END) as hwp_count,
            COUNT(CASE WHEN wzCloseDate IS NULL OR wzCloseDate = '' THEN 1 END) as active_count
        FROM {self.TABLE_NAME}
        """
        
        self.Log.info("Getting rule statistics")
        return self.query(query, one=True)


# Example Usage
if __name__ == "__main__":
    # Logger 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # WzRuleTable 인스턴스 생성
    wz_rule = WzRuleTable(
        database="your_db",
        user="your_user", 
        password="your_password",
        host="127.0.0.1",
        port=5432
    )
    
    try:
        # 테이블 생성
        wz_rule.create_table_if_not_exists()
        
        # 단일 데이터 삽입
        new_seq = wz_rule.save({
            "wzLevel": 1,
            "wzRuleId": 1001,
            "wzName": "정보보안 규정",
            "wzEditType": "제정",
            "wzPubNo": "규정-001",
            "wzEstabDate": "2024-01-01",
            "wzMgrDptNm": "정보보안팀",
            "wzMgrDptOrgCd": "IT001",
            "wzCateSeq": 1,
            "wzExecDate": "2024-01-15",
            "wzFileDocx": "/files/rules/rule001.docx",
            "wzFilePdf": "/files/rules/rule001.pdf",
            "wzCreatedBy": "admin",
            "wzModifiedBy": "admin"
        })
        print(f"Inserted new record with SEQ: {new_seq}")
        
        # 시퀀스로 조회
        record = wz_rule.get_by_seq(new_seq)
        print(f"Retrieved record: {record}")
        
        # 레벨별 조회
        level_rules = wz_rule.get_by_level(1, limit=10)
        print(f"Level 1 rules: {len(level_rules)} found")
        
        # 이름으로 검색
        search_results = wz_rule.search_by_name("보안")
        print(f"Search results for '보안': {len(search_results)} found")
        
        # 활성 규정 조회
        active_rules = wz_rule.get_active_rules()
        print(f"Active rules: {len(active_rules)} found")
        
        # 파일이 있는 규정 조회
        rules_with_pdf = wz_rule.get_rules_with_files('pdf')
        print(f"Rules with PDF files: {len(rules_with_pdf)} found")
        
        # 부서별 규정 조회
        dept_rules = wz_rule.get_by_department('IT001', 'mgr')
        print(f"Rules managed by IT001: {len(dept_rules)} found")
        
        # 날짜 범위 조회
        date_range_rules = wz_rule.get_by_date_range(
            'estab', 
            '2024-01-01', 
            '2024-12-31'
        )
        print(f"Rules established in 2024: {len(date_range_rules)} found")
        
        # 파일 정보 업데이트
        if new_seq:
            updated = wz_rule.update_file_info(
                new_seq, 
                'hwp', 
                '/files/rules/rule001.hwp',
                'admin'
            )
            print(f"File update successful: {updated}")
        
        # 통계 정보 조회
        stats = wz_rule.get_statistics()
        print(f"Rule statistics: {stats}")
        
        # 대량 데이터 삽입 예제
        bulk_data = []
        for i in range(5):
            bulk_data.append({
                "wzLevel": 2,
                "wzRuleId": 2000 + i,
                "wzName": f"테스트 규정 {i+1}",
                "wzEditType": "제정",
                "wzPubNo": f"규정-{2000+i}",
                "wzEstabDate": "2024-01-01",
                "wzMgrDptNm": "관리팀",
                "wzMgrDptOrgCd": "ADM001",
                "wzCateSeq": 2,
                "wzExecDate": "2024-02-01",
                "wzFileDocx": f"/files/rules/test{i+1}.docx",
                "wzFilePdf": f"/files/rules/test{i+1}.pdf",
                "wzCreatedBy": "batch",
                "wzModifiedBy": "batch"
            })
        
        inserted_count = wz_rule.bulk_insert(bulk_data)
        print(f"Bulk inserted {inserted_count} records")
        
        # 데이터 수정 (save 메서드 사용)
        if record:
            record['wzName'] = "정보보안 규정 (개정)"
            record['wzEditType'] = "개정"
            saved_seq = wz_rule.save(record)
            print(f"Saved (updated) record SEQ: {saved_seq}")
            
    except Exception as e:
        wz_rule.Log.error(f"Example failed: {e}")
    finally:
        wz_rule.close()