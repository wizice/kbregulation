# -*- coding: utf-8 -*-
"""
    query_wz_dept
    ~~~~~~~~~~~~~~~~~~~~~~~~

    WZ_DEPT table query class

    :copyright: (c) 2024 by wizice.
    :license: wizice.com
"""

#--- query_wz_dept.py 
#-------------------------------------
from .timescale_dbv1 import TimescaleDB
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

class WzDeptTable(TimescaleDB):
    """
    WZ_DEPT 테이블 전용 쿼리 클래스
    
    테이블 스펙:
    - wzDeptOrgCd: TEXT PRIMARY KEY
    - wzDeptName: TEXT NOT NULL
    - wzDeptTelNo: TEXT
    - wzMgrNm: TEXT
    - wzMgrTelNo: TEXT
    - wzCreatedBy: TEXT NOT NULL
    - wzModifiedBy: TEXT NOT NULL
    """
    
    TABLE_NAME = "WZ_DEPT"
    
    # 테이블 스키마 정의
    SCHEMA = {
        "wzDeptOrgCd": "TEXT PRIMARY KEY",
        "wzDeptName": "TEXT NOT NULL",
        "wzDeptTelNo": "TEXT",
        "wzMgrNm": "TEXT",
        "wzMgrTelNo": "TEXT",
        "wzCreatedBy": "TEXT NOT NULL",
        "wzModifiedBy": "TEXT NOT NULL"
    }
    
    def __init__(self, database="wzdb", user='wzuser', password='wzuserpwd!', 
                 host="127.0.0.1", port=5432, logger=None):
        super().__init__(database, user, password, host, port, logger)
        self.Log.info(f"WzDeptTable initialized for table: {self.TABLE_NAME}")
    
    def create_table_if_not_exists(self):
        """테이블이 없으면 생성"""
        columns = []
        for col, spec in self.SCHEMA.items():
            columns.append(f"{col} {spec}")
        
        create_stmt = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            {', '.join(columns)}
        );
        """
        
        try:
            self.query(create_stmt, commit=True)
            self.Log.info(f"Table {self.TABLE_NAME} created/verified successfully")
            return True
        except Exception as e:
            self.Log.error(f"Failed to create table: {e}")
            return False
    
    def save(self, data: Dict[str, Any], modified_by: str = None) -> Optional[str]:
        """
        부서 데이터 저장 (INSERT 또는 UPDATE)
        wzDeptOrgCd가 존재하면 UPDATE, 없으면 INSERT
        """
        # modified_by 자동 설정
        if modified_by:
            data['wzModifiedBy'] = modified_by
        
        if 'wzDeptOrgCd' in data and data['wzDeptOrgCd']:
            # 기존 레코드 확인
            existing = self.get_by_org_code(data['wzDeptOrgCd'])
            if existing:
                # UPDATE
                org_cd = data.pop('wzDeptOrgCd')
                # created_by는 업데이트하지 않음
                if 'wzCreatedBy' in data:
                    data.pop('wzCreatedBy')
                return self.update(self.TABLE_NAME, data, {"wzDeptOrgCd": org_cd}, return_key="wzDeptOrgCd")
            else:
                # INSERT - created_by 설정
                if 'wzCreatedBy' not in data and modified_by:
                    data['wzCreatedBy'] = modified_by
                return self.insert(self.TABLE_NAME, data, return_key="wzDeptOrgCd")
        else:
            self.Log.error("wzDeptOrgCd is required for save operation")
            return None
    
    def get_by_org_code(self, org_code: str) -> Optional[Dict]:
        """조직코드로 부서 조회"""
        self.Log.debug(f"Getting department by org code: {org_code}")
        return self.select(self.TABLE_NAME, condition={"wzDeptOrgCd": org_code}, one=True)
    
    def get_all_departments(self, order_by: str = "wzDeptOrgCd") -> List[Dict]:
        """모든 부서 목록 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        ORDER BY {order_by}
        """
        self.Log.info("Getting all departments")
        return self.query(query)
    
    def get_by_name_pattern(self, name_pattern: str) -> List[Dict]:
        """부서명 패턴으로 검색"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE wzDeptName LIKE %s
        ORDER BY wzDeptOrgCd
        """
        self.Log.info(f"Searching departments by name pattern: {name_pattern}")
        return self.query(query, (f'%{name_pattern}%',))
    
    def get_by_manager_name(self, manager_name: str) -> List[Dict]:
        """관리자명으로 부서 검색"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE wzMgrNm = %s OR wzMgrNm LIKE %s
        ORDER BY wzDeptOrgCd
        """
        self.Log.info(f"Getting departments by manager: {manager_name}")
        return self.query(query, (manager_name, f'%{manager_name}%'))
    
    def update_department_info(self, org_code: str, data: Dict[str, Any], 
                             modified_by: str = None) -> bool:
        """부서 정보 업데이트"""
        if modified_by:
            data['wzModifiedBy'] = modified_by
            
        # wzDeptOrgCd는 업데이트하지 않음
        if 'wzDeptOrgCd' in data:
            data.pop('wzDeptOrgCd')
        # wzCreatedBy는 업데이트하지 않음
        if 'wzCreatedBy' in data:
            data.pop('wzCreatedBy')
            
        if not data:
            self.Log.warning("No data to update")
            return False
            
        result = self.update(self.TABLE_NAME, data, {"wzDeptOrgCd": org_code})
        return result > 0
    
    def update_manager(self, org_code: str, manager_name: str = None, 
                      manager_tel: str = None, modified_by: str = None) -> bool:
        """부서 관리자 정보 업데이트"""
        update_data = {}
        if manager_name is not None:
            update_data['wzMgrNm'] = manager_name
        if manager_tel is not None:
            update_data['wzMgrTelNo'] = manager_tel
        if modified_by:
            update_data['wzModifiedBy'] = modified_by
            
        if not update_data:
            self.Log.warning("No manager data to update")
            return False
            
        result = self.update(self.TABLE_NAME, update_data, {"wzDeptOrgCd": org_code})
        return result > 0
    
    def delete_department(self, org_code: str) -> bool:
        """부서 삭제"""
        self.Log.info(f"Deleting department: {org_code}")
        deleted = self.delete(self.TABLE_NAME, {"wzDeptOrgCd": org_code})
        return deleted > 0
    
    def bulk_insert(self, dept_list: List[Dict], created_by: str = None) -> int:
        """대량 부서 데이터 삽입"""
        if not dept_list:
            return 0
            
        # created_by, modified_by 자동 설정
        for dept in dept_list:
            if created_by:
                if 'wzCreatedBy' not in dept:
                    dept['wzCreatedBy'] = created_by
                if 'wzModifiedBy' not in dept:
                    dept['wzModifiedBy'] = created_by
            
        # 컬럼 순서 보장
        columns = list(dept_list[0].keys())
        values_template = "(%s)" % ','.join(['%s'] * len(columns))
        
        # 모든 데이터의 값들을 하나의 리스트로 펼침
        all_values = []
        values_clauses = []
        for dept in dept_list:
            values_clauses.append(values_template)
            all_values.extend([dept[col] for col in columns])
        
        query = f"""
        INSERT INTO {self.TABLE_NAME} ({','.join(columns)})
        VALUES {','.join(values_clauses)}
        ON CONFLICT (wzDeptOrgCd) DO NOTHING
        """
        
        self.Log.info(f"Bulk inserting {len(dept_list)} departments")
        try:
            result = self.query(query, tuple(all_values), commit=True)
            self.Log.info(f"Successfully inserted departments")
            return len(dept_list)
        except Exception as e:
            self.Log.error(f"Bulk insert failed: {e}")
            raise
    
    def get_department_stats(self) -> Dict[str, Any]:
        """부서 통계 정보 조회"""
        query = f"""
        SELECT 
            COUNT(*) as total_departments,
            COUNT(DISTINCT wzMgrNm) as total_managers,
            COUNT(wzMgrNm) as departments_with_manager,
            COUNT(wzMgrTelNo) as departments_with_manager_tel
        FROM {self.TABLE_NAME}
        """
        
        self.Log.info("Getting department statistics")
        result = self.query(query, one=True)
        return result if result else {}
    
    def get_departments_without_manager(self) -> List[Dict]:
        """관리자가 없는 부서 목록 조회"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE wzMgrNm IS NULL OR wzMgrNm = ''
        ORDER BY wzDeptOrgCd
        """
        
        self.Log.info("Getting departments without manager")
        return self.query(query)
    
    def search_departments(self, search_term: str) -> List[Dict]:
        """통합 검색 (부서코드, 부서명, 관리자명, 전화번호)"""
        query = f"""
        SELECT * FROM {self.TABLE_NAME}
        WHERE wzDeptOrgCd LIKE %s
           OR wzDeptName LIKE %s
           OR wzMgrNm LIKE %s
           OR wzDeptTelNo LIKE %s
           OR wzMgrTelNo LIKE %s
        ORDER BY wzDeptOrgCd
        """
        
        search_pattern = f'%{search_term}%'
        self.Log.info(f"Searching departments with term: {search_term}")
        return self.query(query, (search_pattern,) * 5)


# Example Usage
if __name__ == "__main__":
    # Logger 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # WzDeptTable 인스턴스 생성
    dept = WzDeptTable(
        database="your_db",
        user="your_user", 
        password="your_password",
        host="127.0.0.1",
        port=5432
    )
    
    try:
        # 테이블 생성
        dept.create_table_if_not_exists()
        
        # 단일 부서 삽입
        new_dept_code = dept.save({
            "wzDeptOrgCd": "D001",
            "wzDeptName": "개발팀",
            "wzDeptTelNo": "02-1234-5678",
            "wzMgrNm": "김철수",
            "wzMgrTelNo": "010-1234-5678"
        }, modified_by="admin")
        print(f"Inserted new department: {new_dept_code}")
        
        # 조직코드로 조회
        dept_info = dept.get_by_org_code("D001")
        print(f"Retrieved department: {dept_info}")
        
        # 부서 정보 업데이트
        updated = dept.update_department_info(
            "D001",
            {"wzDeptName": "개발1팀", "wzDeptTelNo": "02-1234-5679"},
            modified_by="admin"
        )
        print(f"Update successful: {updated}")
        
        # 관리자 정보 업데이트
        mgr_updated = dept.update_manager(
            "D001",
            manager_name="이영희",
            manager_tel="010-9876-5432",
            modified_by="admin"
        )
        print(f"Manager update successful: {mgr_updated}")
        
        # 대량 부서 데이터 삽입
        bulk_depts = [
            {
                "wzDeptOrgCd": "D002",
                "wzDeptName": "영업팀",
                "wzDeptTelNo": "02-2345-6789",
                "wzMgrNm": "박영수",
                "wzMgrTelNo": "010-2345-6789"
            },
            {
                "wzDeptOrgCd": "D003",
                "wzDeptName": "마케팅팀",
                "wzDeptTelNo": "02-3456-7890",
                "wzMgrNm": "최민정",
                "wzMgrTelNo": "010-3456-7890"
            },
            {
                "wzDeptOrgCd": "D004",
                "wzDeptName": "인사팀",
                "wzDeptTelNo": "02-4567-8901"
            }
        ]
        
        inserted_count = dept.bulk_insert(bulk_depts, created_by="admin")
        print(f"Bulk inserted {inserted_count} departments")
        
        # 모든 부서 조회
        all_depts = dept.get_all_departments()
        print(f"Total departments: {len(all_depts)}")
        for d in all_depts:
            print(f"  - {d['wzDeptOrgCd']}: {d['wzDeptName']}")
        
        # 부서명으로 검색
        dev_depts = dept.get_by_name_pattern("개발")
        print(f"Departments with '개발': {len(dev_depts)}")
        
        # 관리자명으로 검색
        mgr_depts = dept.get_by_manager_name("박영수")
        print(f"Departments managed by 박영수: {len(mgr_depts)}")
        
        # 관리자가 없는 부서 조회
        no_mgr_depts = dept.get_departments_without_manager()
        print(f"Departments without manager: {len(no_mgr_depts)}")
        
        # 부서 통계 조회
        stats = dept.get_department_stats()
        print(f"Department statistics: {stats}")
        
        # 통합 검색
        search_results = dept.search_departments("02-")
        print(f"Search results for '02-': {len(search_results)} departments")
        
        # 부서 수정 (save 메서드 사용)
        if dept_info:
            dept_info['wzDeptName'] = "개발본부"
            saved_code = dept.save(dept_info, modified_by="admin")
            print(f"Saved (updated) department: {saved_code}")
            
    except Exception as e:
        dept.Log.error(f"Example failed: {e}")
    finally:
        dept.close()