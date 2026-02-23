# -*- coding: utf-8 -*-
"""
    query_wz_cate
    ~~~~~~~~~~~~~~~~~~~~~~~~

    WZ_CATE table query class

    :copyright: (c) 2024 by wizice.
    :license:  wizice.com
"""

#--- query_wz_cate_v1.py 
#-------------------------------------
from .timescale_dbv1 import TimescaleDB
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

class WzCateTable(TimescaleDB):
    """
    WZ_CATE 테이블 전용 쿼리 클래스
    
    테이블 스펙:
    - wzCateSeq: INTEGER PRIMARY KEY
    - wzCateName: CHAR(40) NOT NULL
    - wzParentSeq: INTEGER
    - wzOrder: INTEGER
    - wzVisible: CHAR(1) DEFAULT 'Y'
    - wzCreatedBy: TEXT NOT NULL
    - wzModifiedBy: TEXT NOT NULL
    """
    
    TABLE_NAME = "WZ_CATE"
    
    # 테이블 스키마 정의
    SCHEMA = {
        "wzCateSeq": "INTEGER PRIMARY KEY",
        "wzCateName": "CHAR(40) NOT NULL",
        "wzParentSeq": "INTEGER",
        "wzOrder": "INTEGER",
        "wzVisible": "CHAR(1) DEFAULT 'Y'",
        "wzCreatedBy": "TEXT NOT NULL",
        "wzModifiedBy": "TEXT NOT NULL"
    }
    
    def __init__(self, database="wzdb", user='wzuser', password='wzuserpwd!', 
                 host="127.0.0.1", port=5432, logger=None):
        super().__init__(database, user, password, host, port, logger)
        self.Log.info(f"WzCateTable initialized for table: {self.TABLE_NAME}")
    
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
        CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_parent 
        ON {self.TABLE_NAME} (wzParentSeq);
        
        CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_visible 
        ON {self.TABLE_NAME} (wzVisible);
        
        CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_order 
        ON {self.TABLE_NAME} (wzOrder);
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
        wzCateSeq가 있으면 UPDATE, 없으면 INSERT
        """
        if 'wzCateSeq' in data and data['wzCateSeq']:
            # UPDATE
            seq_value = data.pop('wzCateSeq')
            return self.update(self.TABLE_NAME, data, {"wzCateSeq": seq_value}, return_key="wzCateSeq")
        else:
            # INSERT
            if 'wzCateSeq' in data:
                data.pop('wzCateSeq')
            return self.insert(self.TABLE_NAME, data, return_key="wzCateSeq")
    
    def get_by_seq(self, wz_cate_seq: int) -> Optional[Dict]:
        """시퀀스로 단일 카테고리 조회"""
        self.Log.debug(f"Getting category by seq: {wz_cate_seq}")
        return self.select(self.TABLE_NAME, condition={"wzCateSeq": wz_cate_seq}, one=True)
    
    def get_by_name(self, cate_name: str) -> Optional[Dict]:
        """이름으로 카테고리 조회"""
        self.Log.debug(f"Getting category by name: {cate_name}")
        query = f"SELECT * FROM {self.TABLE_NAME} WHERE wzCateName = %s"
        return self.query(query, (cate_name,), one=True)
    
    def get_by_parent(self, parent_seq: Optional[int] = None, 
                      visible_only: bool = True) -> List[Dict]:
        """부모 시퀀스별 자식 카테고리 목록 조회"""
        query = f"SELECT * FROM {self.TABLE_NAME} WHERE "
        params = []
        
        if parent_seq is None:
            query += "wzParentSeq IS NULL"
        else:
            query += "wzParentSeq = %s"
            params.append(parent_seq)
        
        if visible_only:
            query += " AND wzVisible = 'Y'"
        
        query += " ORDER BY wzOrder, wzCateSeq"
        
        self.Log.info(f"Getting categories by parent: {parent_seq}")
        return self.query(query, tuple(params) if params else None)
    
    def get_all_categories(self, visible_only: bool = True) -> List[Dict]:
        """모든 카테고리 조회"""
        query = f"SELECT * FROM {self.TABLE_NAME}"
        params = []
        
        if visible_only:
            query += " WHERE wzVisible = 'Y'"
        
        query += " ORDER BY wzParentSeq NULLS FIRST, wzOrder, wzCateSeq"
        
        self.Log.info("Getting all categories")
        return self.query(query)
    
    def get_category_tree(self, root_seq: Optional[int] = None, 
                         visible_only: bool = True) -> List[Dict]:
        """카테고리 트리 구조 조회 (재귀)"""
        query = f"""
        WITH RECURSIVE category_tree AS (
            -- Base case: root categories
            SELECT 
                wzCateSeq,
                wzCateName,
                wzParentSeq,
                wzOrder,
                wzVisible,
                0 as level,
                ARRAY[wzCateSeq] as path,
                ARRAY[wzCateName::text] as path_names
            FROM {self.TABLE_NAME}
            WHERE """
        
        params = []
        if root_seq is None:
            query += "wzParentSeq IS NULL"
        else:
            query += "wzCateSeq = %s"
            params.append(root_seq)
        
        if visible_only:
            query += " AND wzVisible = 'Y'"
        
        query += """
            
            UNION ALL
            
            -- Recursive case: child categories
            SELECT 
                c.wzCateSeq,
                c.wzCateName,
                c.wzParentSeq,
                c.wzOrder,
                c.wzVisible,
                ct.level + 1,
                ct.path || c.wzCateSeq,
                ct.path_names || c.wzCateName::text
            FROM {table_name} c
            INNER JOIN category_tree ct ON c.wzParentSeq = ct.wzCateSeq
        """.format(table_name=self.TABLE_NAME)
        
        if visible_only:
            query += " WHERE c.wzVisible = 'Y'"
        
        query += """
        )
        SELECT * FROM category_tree
        ORDER BY path
        """
        
        self.Log.info(f"Getting category tree from root: {root_seq}")
        return self.query(query, tuple(params) if params else None)
    
    def get_breadcrumb(self, wz_cate_seq: int) -> List[Dict]:
        """카테고리 경로 (빵부스러기) 조회"""
        query = f"""
        WITH RECURSIVE category_path AS (
            SELECT 
                wzCateSeq,
                wzCateName,
                wzParentSeq,
                1 as level
            FROM {self.TABLE_NAME}
            WHERE wzCateSeq = %s
            
            UNION ALL
            
            SELECT 
                c.wzCateSeq,
                c.wzCateName,
                c.wzParentSeq,
                cp.level + 1
            FROM {self.TABLE_NAME} c
            INNER JOIN category_path cp ON c.wzCateSeq = cp.wzParentSeq
        )
        SELECT * FROM category_path
        ORDER BY level DESC
        """
        
        self.Log.info(f"Getting breadcrumb for category: {wz_cate_seq}")
        return self.query(query, (wz_cate_seq,))
    
    def update_visibility(self, wz_cate_seq: int, visible: str, 
                         modified_by: str, cascade: bool = False) -> bool:
        """카테고리 표시 여부 업데이트"""
        if visible not in ('Y', 'N'):
            self.Log.error(f"Invalid visible value: {visible}")
            return False
        
        update_data = {
            'wzVisible': visible,
            'wzModifiedBy': modified_by
        }
        
        if cascade:
            # 하위 카테고리도 함께 업데이트
            query = f"""
            WITH RECURSIVE sub_categories AS (
                SELECT wzCateSeq FROM {self.TABLE_NAME} WHERE wzCateSeq = %s
                UNION ALL
                SELECT c.wzCateSeq 
                FROM {self.TABLE_NAME} c
                INNER JOIN sub_categories sc ON c.wzParentSeq = sc.wzCateSeq
            )
            UPDATE {self.TABLE_NAME}
            SET wzVisible = %s, wzModifiedBy = %s
            WHERE wzCateSeq IN (SELECT wzCateSeq FROM sub_categories)
            """
            result = self.query(query, (wz_cate_seq, visible, modified_by), commit=True)
            self.Log.info(f"Updated visibility for category {wz_cate_seq} and its children")
            return result > 0
        else:
            result = self.update(self.TABLE_NAME, update_data, {"wzCateSeq": wz_cate_seq})
            return result > 0
    
    def update_order(self, category_orders: List[Dict[str, int]], modified_by: str) -> bool:
        """카테고리 순서 일괄 업데이트"""
        try:
            for item in category_orders:
                update_data = {
                    'wzOrder': item['order'],
                    'wzModifiedBy': modified_by
                }
                self.update(self.TABLE_NAME, update_data, {"wzCateSeq": item['seq']})
            
            self.Log.info(f"Updated order for {len(category_orders)} categories")
            return True
        except Exception as e:
            self.Log.error(f"Failed to update category orders: {e}")
            return False
    
    def move_category(self, wz_cate_seq: int, new_parent_seq: Optional[int], 
                     modified_by: str) -> bool:
        """카테고리를 다른 부모로 이동"""
        # 순환 참조 검사
        if new_parent_seq:
            if self._would_create_cycle(wz_cate_seq, new_parent_seq):
                self.Log.error("Moving category would create a cycle")
                return False
        
        update_data = {
            'wzParentSeq': new_parent_seq,
            'wzModifiedBy': modified_by
        }
        
        result = self.update(self.TABLE_NAME, update_data, {"wzCateSeq": wz_cate_seq})
        return result > 0
    
    def _would_create_cycle(self, child_seq: int, new_parent_seq: int) -> bool:
        """순환 참조 검사"""
        query = f"""
        WITH RECURSIVE parent_chain AS (
            SELECT wzCateSeq, wzParentSeq FROM {self.TABLE_NAME} WHERE wzCateSeq = %s
            UNION ALL
            SELECT c.wzCateSeq, c.wzParentSeq 
            FROM {self.TABLE_NAME} c
            INNER JOIN parent_chain pc ON c.wzCateSeq = pc.wzParentSeq
        )
        SELECT EXISTS(SELECT 1 FROM parent_chain WHERE wzCateSeq = %s)
        """
        result = self.query(query, (new_parent_seq, child_seq), one=True)
        return result['exists'] if result else False
    
    def delete_category(self, wz_cate_seq: int, cascade: bool = False) -> bool:
        """카테고리 삭제"""
        if cascade:
            # 하위 카테고리도 함께 삭제
            query = f"""
            WITH RECURSIVE sub_categories AS (
                SELECT wzCateSeq FROM {self.TABLE_NAME} WHERE wzCateSeq = %s
                UNION ALL
                SELECT c.wzCateSeq 
                FROM {self.TABLE_NAME} c
                INNER JOIN sub_categories sc ON c.wzParentSeq = sc.wzCateSeq
            )
            DELETE FROM {self.TABLE_NAME}
            WHERE wzCateSeq IN (SELECT wzCateSeq FROM sub_categories)
            """
            result = self.query(query, (wz_cate_seq,), commit=True)
            self.Log.info(f"Deleted category {wz_cate_seq} and its children")
            return result > 0
        else:
            # 자식이 있는지 확인
            children = self.get_by_parent(wz_cate_seq)
            if children:
                self.Log.error(f"Cannot delete category {wz_cate_seq}: has {len(children)} children")
                return False
            
            return self.delete(self.TABLE_NAME, {"wzCateSeq": wz_cate_seq})
    
    def get_category_stats(self) -> Dict[str, Any]:
        """카테고리 통계 정보 조회"""
        query = f"""
        SELECT 
            COUNT(*) as total_categories,
            COUNT(CASE WHEN wzVisible = 'Y' THEN 1 END) as visible_categories,
            COUNT(CASE WHEN wzParentSeq IS NULL THEN 1 END) as root_categories,
            COUNT(DISTINCT wzParentSeq) as parent_count,
            MAX(level) as max_depth
        FROM (
            WITH RECURSIVE category_depth AS (
                SELECT wzCateSeq, 0 as level
                FROM {self.TABLE_NAME}
                WHERE wzParentSeq IS NULL
                
                UNION ALL
                
                SELECT c.wzCateSeq, cd.level + 1
                FROM {self.TABLE_NAME} c
                INNER JOIN category_depth cd ON c.wzParentSeq = cd.wzCateSeq
            )
            SELECT * FROM category_depth
        ) depth_calc
        CROSS JOIN {self.TABLE_NAME}
        """
        
        self.Log.info("Getting category statistics")
        return self.query(query, one=True)


# Example Usage
if __name__ == "__main__":
    # Logger 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # WzCateTable 인스턴스 생성
    cate_table = WzCateTable(
        database="your_db",
        user="your_user", 
        password="your_password",
        host="127.0.0.1",
        port=5432
    )
    
    try:
        # 테이블 생성
        cate_table.create_table_if_not_exists()
        
        # 루트 카테고리 생성
        root_id = cate_table.save({
            "wzCateName": "전체 카테고리",
            "wzParentSeq": None,
            "wzOrder": 1,
            "wzVisible": "Y",
            "wzCreatedBy": "admin",
            "wzModifiedBy": "admin"
        })
        print(f"Created root category with ID: {root_id}")
        
        # 하위 카테고리 생성
        sub_id1 = cate_table.save({
            "wzCateName": "전자제품",
            "wzParentSeq": root_id,
            "wzOrder": 1,
            "wzVisible": "Y",
            "wzCreatedBy": "admin",
            "wzModifiedBy": "admin"
        })
        
        sub_id2 = cate_table.save({
            "wzCateName": "가전제품",
            "wzParentSeq": root_id,
            "wzOrder": 2,
            "wzVisible": "Y",
            "wzCreatedBy": "admin",
            "wzModifiedBy": "admin"
        })
        print(f"Created sub categories: {sub_id1}, {sub_id2}")
        
        # 카테고리 조회
        category = cate_table.get_by_seq(root_id)
        print(f"Retrieved category: {category}")
        
        # 자식 카테고리 목록 조회
        children = cate_table.get_by_parent(root_id)
        print(f"Children of root category: {children}")
        
        # 카테고리 트리 조회
        tree = cate_table.get_category_tree()
        print(f"Category tree: {tree}")
        
        # 빵부스러기 조회
        if sub_id1:
            breadcrumb = cate_table.get_breadcrumb(sub_id1)
            print(f"Breadcrumb for subcategory: {breadcrumb}")
        
        # 카테고리 순서 업데이트
        order_updates = [
            {"seq": sub_id1, "order": 2},
            {"seq": sub_id2, "order": 1}
        ]
        cate_table.update_order(order_updates, "admin")
        print("Updated category orders")
        
        # 표시 여부 업데이트
        if sub_id1:
            cate_table.update_visibility(sub_id1, "N", "admin")
            print(f"Updated visibility for category {sub_id1}")
        
        # 카테고리 이동
        if sub_id2 and sub_id1:
            moved = cate_table.move_category(sub_id2, sub_id1, "admin")
            print(f"Moved category: {moved}")
        
        # 통계 정보 조회
        stats = cate_table.get_category_stats()
        print(f"Category statistics: {stats}")
        
        # 카테고리 삭제
        # deleted = cate_table.delete_category(sub_id2, cascade=True)
        # print(f"Deleted category: {deleted}")
        
    except Exception as e:
        cate_table.Log.error(f"Example failed: {e}")
    finally:
        cate_table.close()