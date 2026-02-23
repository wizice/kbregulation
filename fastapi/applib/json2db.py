#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    json2db.py
    ~~~~~~~~~~
    
    JSON 파일을 PostgreSQL 데이터베이스 wz_rule 테이블로 가져오는 도구
    applib/json 폴더의 JSON 파일들을 파싱하여 DB에 삽입
    
    :copyright: (c) 2025 by Claude Assistant
    :license: MIT
"""

import json
import os
import sys
import glob
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# 상위 디렉토리를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor
from app_logger import get_logger

# 로거 설정
logger = get_logger(__name__)

class JsonToDbImporter:
    """JSON 파일을 wz_rule 테이블로 가져오는 클래스"""
    
    def __init__(self, db_config: Optional[Dict] = None):
        """
        초기화
        
        Args:
            db_config: 데이터베이스 설정 (선택사항)
        """
        # 기본 설정
        default_config = {
            "database": "severance",
            "user": "severance",
            "password": "rkatkseverance!",
            "host": "127.0.0.1",
            "port": 35432
        }
        
        # 사용자 설정이 있으면 병합
        if db_config:
            default_config.update(db_config)
        
        self.db_config = default_config
        self.connection = None
        self.cursor = None
        self.stats = {
            "total_files": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0
        }
        
    def connect(self):
        """데이터베이스 연결"""
        try:
            self.connection = psycopg2.connect(
                database=self.db_config["database"],
                user=self.db_config["user"],
                password=self.db_config["password"],
                host=self.db_config["host"],
                port=self.db_config["port"]
            )
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            logger.info(f"Database connected: {self.db_config['database']}@{self.db_config['host']}:{self.db_config['port']}")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """데이터베이스 연결 해제"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            logger.info("Database disconnected")
    
    def parse_json_file(self, json_path: str) -> Optional[Dict]:
        """
        JSON 파일 파싱
        
        Args:
            json_path: JSON 파일 경로
            
        Returns:
            파싱된 JSON 데이터 또는 None
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Failed to parse JSON file {json_path}: {e}")
            return None
    
    def extract_rule_info_from_filename(self, filename: str) -> Dict[str, str]:
        """
        파일명에서 규정 정보 추출
        예: merged_1.1.1._정확한_환자_확인_202503개정_20250922_104723.json
        예: merged_2.1.2.2._정신건강의학과_·_소아정신과_입원환자_관리_202503개정_20250922_104723.json

        Args:
            filename: 파일명

        Returns:
            추출된 정보 딕셔너리
        """
        info = {}

        # 확장자 제거
        name_without_ext = os.path.splitext(filename)[0]

        # merged_ 접두사 제거
        if name_without_ext.startswith('merged_'):
            name_without_ext = name_without_ext[7:]  # 'merged_' 길이는 7

        # 타임스탬프 제거 (_20250922_104723 형식)
        name_without_timestamp = re.sub(r'_\d{8}_\d{6}$', '', name_without_ext)

        # 개정정보 제거 (_202503개정, _202505수정, _202503제정 등)
        name_without_revision = re.sub(r'_\d{6,8}(개정|수정|제정)$', '', name_without_timestamp)

        # 규정 번호 추출 (예: 1.1.1. 또는 2.1.2.2. 또는 10.2.1.)
        number_match = re.match(r'^([\d.]+)\._', name_without_revision)
        if number_match:
            info['rule_number'] = number_match.group(1) + '.'  # 마지막 점 유지
            # 규정명 추출 (규정번호와 ._ 제거 후 언더스코어를 공백으로 변환)
            rule_name = re.sub(r'^[\d.]+\._', '', name_without_revision)
            info['rule_name'] = rule_name.replace('_', ' ')
        else:
            # 규정번호가 없는 경우
            info['rule_name'] = name_without_revision.replace('_', ' ')

        return info
    
    def format_date(self, date_str: str) -> str:
        """
        날짜 형식 통일 (YYYY.MM.DD)
        
        Args:
            date_str: 원본 날짜 문자열
            
        Returns:
            포맷된 날짜 문자열
        """
        if not date_str:
            return ""
        
        # 이미 올바른 형식인지 확인
        if re.match(r'^\d{4}\.\d{2}\.\d{2}', date_str):
            return date_str
        
        # YYYY-MM-DD를 YYYY.MM.DD로 변환
        if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
            return date_str.replace('-', '.')
        
        # YYYY.MM 형식인 경우
        if re.match(r'^\d{4}\.\d{2}\.?$', date_str):
            return date_str.rstrip('.')
        
        return date_str
    
    def extract_dates_from_text(self, text: str) -> Dict[str, str]:
        """
        텍스트에서 날짜 정보 추출
        예: "구두/전화처방 제 정 일 2007.04. 최 종 개 정 일 2025.03.25. 최 종 검 토 일 2025.03.25."
        
        Args:
            text: 날짜가 포함된 텍스트
            
        Returns:
            추출된 날짜 정보
        """
        dates = {}
        
        # 제정일 추출
        estab_match = re.search(r'제\s*정\s*일\s*(\d{4}\.\d{2}\.)', text)
        if estab_match:
            dates['estab_date'] = estab_match.group(1).rstrip('.')
        
        # 최종개정일 추출
        rev_match = re.search(r'최\s*종\s*개\s*정\s*일\s*(\d{4}\.\d{2}\.\d{2}\.)', text)
        if rev_match:
            dates['rev_date'] = rev_match.group(1).rstrip('.')
        
        # 최종검토일 추출
        revw_match = re.search(r'최\s*종\s*검\s*토\s*일\s*(\d{4}\.\d{2}\.\d{2}\.)', text)
        if revw_match:
            dates['revw_date'] = revw_match.group(1).rstrip('.')
        
        return dates
    
    def convert_json_to_db_record(self, json_data: Dict, filename: str, json_path: str = "") -> Optional[Dict]:
        """
        JSON 데이터를 wz_rule 테이블 레코드로 변환

        Args:
            json_data: JSON 데이터
            filename: 원본 파일명

        Returns:
            DB 레코드 형식의 딕셔너리
        """
        try:
            # 문서정보 섹션
            doc_info = json_data.get("문서정보", {})

            # JSON 내부에서 규정표기명 또는 규정명 가져오기
            rule_full_name = doc_info.get("규정표기명", "") or doc_info.get("규정명", "")

            # 규정번호와 규정명 분리
            # 예: "1.1.1. 정확한 환자 확인" -> wzpubno="1.1.1.", wzname="정확한 환자 확인"
            rule_number = ""
            clean_rule_name = rule_full_name

            # 규정번호 추출 (예: 1.1.1. 또는 2.1.2.2. 또는 10.2.1.)
            number_match = re.match(r'^([\d.]+\.)\s+(.+)$', rule_full_name)
            if number_match:
                rule_number = number_match.group(1)  # 규정번호 (예: "1.1.1.")
                clean_rule_name = number_match.group(2).strip()  # 규정명 (예: "정확한 환자 확인")

            # JSON 내부에서 직접 날짜 정보 가져오기
            estab_date = doc_info.get("제정일", "")
            last_rev_date = doc_info.get("최종개정일", "")
            last_revw_date = doc_info.get("최종검토일", "")

            # 날짜 형식 정리 (마지막 점 제거)
            estab_date = estab_date.rstrip('.')
            last_rev_date = last_rev_date.rstrip('.')
            last_revw_date = last_revw_date.rstrip('.')
            
            # 조문내용을 JSON 문자열로 저장
            articles = json_data.get("조문내용", [])
            articles_json = json.dumps(articles, ensure_ascii=False, indent=2) if articles else ""
            
            # 관련기준 처리
            related_standards = doc_info.get("관련기준", [])
            if isinstance(related_standards, list):
                related_standard_str = ", ".join(related_standards)
            else:
                related_standard_str = str(related_standards) if related_standards else ""
            
            # DB 레코드 생성 (소문자 컬럼명)
            record = {
                # 기본 정보
                "wzlevel": 0,  # 레벨 (0으로 설정)
                "wzruleid": 0,  # rule id (0으로 설정)
                "wzname": clean_rule_name,  # 정제된 규정명
                "wzedittype": "규정",  # 제개정 구분
                "wzpubno": rule_number,  # 규정번호
                
                # 날짜 정보 (JSON 내부 데이터 사용)
                "wzestabdate": estab_date,  # 제정일
                "wzlastrevdate": last_rev_date,  # 최종개정일
                "wzlastrevwdate": last_revw_date,  # 최종검토일
                "wzexecdate": last_rev_date,  # 시행일은 최종개정일과 동일
                "wzclosedate": "",  # 종료일자는 비움
                
                # 부서 정보
                "wzmgrdptnm": doc_info.get("담당부서", ""),
                "wzmgrdptorgcd": "",  # 담당부서 코드 (추후 매핑)
                "wzreldptnm": "",  # 유관부서
                "wzreldptorgcd": "",  # 유관부서 코드
                
                # 관련기준
                "wzrelstandard": related_standard_str,
                
                # 분류
                "wzcateseq": 0,  # 분류 번호 (추후 매핑)
                
                # 조문 내용 (wzcontent_path는 비움)
                "wzcontent_path": "",  # 파일 경로 저장하지 않음
                
                # 기타
                "wzlkndname": "",  # 기존 규정 구분명
                
                # 파일 정보 (절대경로 저장)
                "wzfiledocx": json_path.replace('.json', '.docx') if json_path else filename.replace('.json', '.docx'),  # docx 파일 절대경로
                "wzfilepdf": json_path.replace('.json', '.pdf') if json_path else filename.replace('.json', '.pdf'),  # pdf 파일 절대경로
                "wzfilehwp": "",  # hwp 파일명 (없으면 비움)
                "wzfilejson": json_path if json_path else filename,  # json 파일 절대경로
                
                # 생성/수정 정보
                "wzcreatedby": "json2db",
                "wzmodifiedby": "json2db",

                # 현행/연혁 구분
                "wznewflag": "현행"  # 모두 현행으로 설정
            }
            
            return record
            
        except Exception as e:
            logger.error(f"Failed to convert JSON to DB record: {e}")
            return None
    
    def get_next_wzruleseq(self) -> int:
        """
        다음 wzruleseq 값 가져오기
        
        Returns:
            다음 시퀀스 번호
        """
        try:
            self.cursor.execute("SELECT COALESCE(MAX(wzruleseq), 0) + 1 as next_seq FROM wz_rule")
            result = self.cursor.fetchone()
            return result['next_seq'] if result else 1
        except Exception as e:
            logger.error(f"Failed to get next wzruleseq: {e}")
            return 1
    
    def check_duplicate(self, wzpubno: str) -> bool:
        """
        중복 체크 (규정번호 기준)
        
        Args:
            wzpubno: 규정번호
            
        Returns:
            중복 여부
        """
        try:
            self.cursor.execute("SELECT COUNT(*) as cnt FROM wz_rule WHERE wzpubno = %s", (wzpubno,))
            result = self.cursor.fetchone()
            return result['cnt'] > 0 if result else False
        except Exception as e:
            logger.error(f"Failed to check duplicate: {e}")
            return False
    
    def insert_record(self, record: Dict) -> bool:
        """
        데이터베이스에 레코드 삽입
        
        Args:
            record: DB 레코드
            
        Returns:
            성공 여부
        """
        try:
            # 중복 체크
            if self.check_duplicate(record.get('wzpubno', '')):
                logger.warning(f"Duplicate record found for wzpubno: {record.get('wzpubno', '')}")
                return False
            
            # wzruleseq 자동 할당
            record['wzruleseq'] = self.get_next_wzruleseq()
            
            # INSERT 쿼리 생성
            columns = list(record.keys())
            values = list(record.values())
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            
            query = f"INSERT INTO wz_rule ({column_names}) VALUES ({placeholders})"
            
            # 쿼리 실행
            self.cursor.execute(query, values)
            self.connection.commit()
            
            logger.info(f"Record inserted - SEQ: {record['wzruleseq']}, 규정번호: {record['wzpubno']}, 규정명: {record['wzname']}")
            return True
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to insert record: {e}")
            return False
    
    def process_json_file(self, json_path: str) -> bool:
        """
        단일 JSON 파일 처리
        
        Args:
            json_path: JSON 파일 경로
            
        Returns:
            성공 여부
        """
        filename = os.path.basename(json_path)
        logger.info(f"Processing: {filename}")
        
        # JSON 파싱
        json_data = self.parse_json_file(json_path)
        if not json_data:
            logger.error(f"Failed to parse: {filename}")
            return False
        
        # DB 레코드로 변환 (절대경로 전달)
        absolute_path = os.path.abspath(json_path)
        record = self.convert_json_to_db_record(json_data, filename, absolute_path)
        if not record:
            logger.error(f"Failed to convert: {filename}")
            return False
        
        # DB에 삽입
        if self.insert_record(record):
            logger.info(f"Successfully imported: {filename}")
            return True
        else:
            logger.error(f"Failed to import: {filename}")
            return False
    
    def process_folder(self, folder_path: str, pattern: str = "*.json") -> Dict:
        """
        폴더 내의 모든 JSON 파일 처리
        
        Args:
            folder_path: 폴더 경로
            pattern: 파일 패턴 (기본값: *.json)
            
        Returns:
            처리 통계
        """
        # JSON 파일 목록 가져오기
        json_files = glob.glob(os.path.join(folder_path, pattern))
        
        if not json_files:
            logger.warning(f"No JSON files found in: {folder_path}")
            return self.stats
        
        self.stats["total_files"] = len(json_files)
        logger.info(f"Found {len(json_files)} JSON files")
        logger.info("-" * 50)
        
        # 데이터베이스 연결
        if not self.connect():
            logger.error("Database connection failed")
            return self.stats
        
        # 각 파일 처리
        for idx, json_path in enumerate(json_files, 1):
            logger.info(f"\n[{idx}/{len(json_files)}] Processing file...")
            
            try:
                if self.process_json_file(json_path):
                    self.stats["success"] += 1
                else:
                    self.stats["failed"] += 1
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                self.stats["failed"] += 1
            
            logger.info("-" * 50)
        
        # 연결 해제
        self.disconnect()
        
        # 결과 출력
        self.print_stats()
        
        return self.stats
    
    def print_stats(self):
        """처리 통계 출력"""
        logger.info("\n" + "=" * 50)
        logger.info("Import Summary")
        logger.info("=" * 50)
        logger.info(f"Total files: {self.stats['total_files']}")
        logger.info(f"Success: {self.stats['success']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Skipped: {self.stats['skipped']}")
        logger.info("=" * 50)

def main():
    """메인 함수"""
    # 명령줄 인자 처리
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Single file: python json2db.py <json_file_path>")
        print("  Folder: python json2db.py <json_folder_path>")
        print("  Default: python json2db.py applib/json/")
        json_path = "applib/json/"
    else:
        json_path = sys.argv[1]
    
    # 데이터베이스 설정 (settings.py에서 가져오기)
    try:
        from settings import settings
        db_config = {
            "database": settings.DB_NAME,
            "user": settings.DB_USER,
            "password": settings.DB_PASSWORD,
            "host": settings.DB_HOST,
            "port": settings.DB_PORT
        }
    except ImportError:
        # settings.py를 못 찾으면 기본값 사용
        db_config = {
            "database": "severance",
            "user": "severance",
            "password": "rkatkseverance!",
            "host": "127.0.0.1",
            "port": 35432
        }
    
    # Importer 생성
    importer = JsonToDbImporter(db_config)
    
    # 처리 실행
    if os.path.isdir(json_path):
        # 폴더 처리
        logger.info(f"Processing folder: {json_path}")
        importer.process_folder(json_path)
    elif os.path.isfile(json_path):
        # 단일 파일 처리
        if not json_path.lower().endswith('.json'):
            logger.error("Not a JSON file")
            sys.exit(1)
        
        logger.info(f"Processing file: {json_path}")
        if importer.connect():
            if importer.process_json_file(json_path):
                logger.info("Import successful")
            else:
                logger.error("Import failed")
            importer.disconnect()
    else:
        logger.error(f"Path not found: {json_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()