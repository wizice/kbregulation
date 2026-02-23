# api/ga4/pipeline.py
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .ga4_collector import GA4Collector
from .ga4_analyzer import GA4Analyzer
from .ga4_converter import GA4DBConverter
from api.query_knews_galogs_v2 import KnewsGalogsTable

class GA4Pipeline:
    """GA4 수집-분석-저장 통합 파이프라인"""
    
    def __init__(self, 
                 property_id: str,
                 credentials_path: str,
                 output_dir: str = "db/ga4",
                 db_config: Dict[str, Any] = None,
                 logger=None):
        self.property_id = property_id
        self.credentials_path = credentials_path
        self.output_dir = output_dir
        self.db_config = db_config
        self.logger = logger
        
        # 컴포넌트 초기화
        self.collector = GA4Collector(property_id, credentials_path)
        self.analyzer = GA4Analyzer()
        self.converter = GA4DBConverter()
        
        # 실행 상태
        self.current_data = None
        self.analysis_result = None
        
    def run(self,
            start_date: str,
            end_date: str,
            collect: bool = True,
            analyze: bool = True,
            save_db: bool = True) -> Dict[str, Any]:
        """파이프라인 실행"""
        
        results = {
            'success': True,
            'start_date': start_date,
            'end_date': end_date,
            'steps': {},
            'errors': []
        }
        
        try:
            # 1. 수집 단계
            if collect:
                self._log(f"[수집] {start_date} ~ {end_date}")
                collection_result = self._collect(start_date, end_date)
                results['steps']['collection'] = collection_result
                
                if collection_result['status'] == 'empty':
                    self._log("[수집] 데이터 없음")
                    return results
            else:
                # 기존 데이터 로드
                self._log("[수집] 기존 데이터 사용")
                loaded = self._load_existing_data(start_date, end_date)
                if not loaded:
                    raise ValueError(f"기존 데이터를 찾을 수 없습니다: {start_date} ~ {end_date}")
                results['steps']['collection'] = {'status': 'loaded', 'records': len(self.current_data)}
            
            # 2. 분석 단계
            if analyze and self.current_data:
                self._log(f"[분석] {len(self.current_data)}개 레코드")
                analysis_result = self._analyze()
                results['steps']['analysis'] = analysis_result
            
            # 3. DB 저장 단계
            if save_db and self.current_data:
                self._log("[DB] 저장 시작")
                db_result = self._save_to_db()
                results['steps']['database'] = db_result
                
        except Exception as e:
            results['success'] = False
            results['errors'].append(str(e))
            self._log(f"[오류] {str(e)}", error=True)
        
        return results
    
    def _collect(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """데이터 수집"""
        # 수집
        df = self.collector.collect_data(
            dimensions=['date', 'pageLocation', 'pageTitle'],
            metrics=['screenPageViews', 'activeUsers'],
            start_date=start_date,
            end_date=end_date,
            limit=100000
        )
        
        if df.empty:
            return {'status': 'empty', 'records': 0}
        
        # JSON 저장
        json_path = self.collector.save_to_json(
            df, self.output_dir, start_date, end_date
        )
        
        # 메모리 보관 (index를 reset하여 컬럼으로 변환)
        df_reset = df.reset_index() if df.index.name or isinstance(df.index, pd.MultiIndex) else df
        self.current_data = df_reset.to_dict('records')
        
        stats = self.collector.get_stats()
        
        return {
            'status': 'collected',
            'records': len(df),
            'file': json_path,
            'total_days': stats['total_days'],
            'duration': stats.get('duration_str', 'N/A')
        }
    
    def _analyze(self) -> Dict[str, Any]:
        """데이터 분석"""
        df = pd.DataFrame(self.current_data)
        
        # 컬럼명 확인 및 표준화
        # GA4 collector가 index로 저장한 경우 처리
        if 'pageLocation' not in df.columns:
            # index가 MultiIndex인 경우 reset
            df = df.reset_index()
            
        # 필수 컬럼 확인
        required_columns = ['pageLocation', 'screenPageViews', 'activeUsers']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            self._log(f"[분석] 누락된 컬럼: {missing_columns}", error=True)
            self._log(f"[분석] 실제 컬럼: {list(df.columns)}", error=True)
            raise ValueError(f"필수 컬럼 누락: {missing_columns}")
        
        # 기본 통계
        total_views = df['screenPageViews'].sum()
        total_users = df['activeUsers'].sum()
        unique_urls = df['pageLocation'].nunique()
        
        # 상위 검색어 추출
        top_sc_words = self.analyzer.analyze_sc_words(df)
        
        # 페이지 유형별 통계
        page_stats = {}
        article_views = {}
        
        for _, row in df.iterrows():
            url = row['pageLocation']
            views = float(row.get('screenPageViews', 0))
            
            # URL 분석 위한 import 추가
            from urllib.parse import urlparse, parse_qs
            type_code, norm_url, params = self.analyzer.normalize_url(url, top_sc_words)
            page_type = self.analyzer.classify_page_type(
                urlparse(url).path,
                parse_qs(urlparse(url).query)
            )
            
            # 페이지 유형별 집계
            if page_type not in page_stats:
                page_stats[page_type] = {'views': 0, 'count': 0}
            page_stats[page_type]['views'] += views
            page_stats[page_type]['count'] += 1
            
            # 기사별 집계
            if params.get('idxno'):
                idxno = params['idxno']
                if idxno not in article_views:
                    article_views[idxno] = {
                        'views': 0,
                        'title': row.get('pageTitle', '')
                    }
                article_views[idxno]['views'] += views
        
        # 상위 기사
        top_articles = sorted(
            article_views.items(),
            key=lambda x: x[1]['views'],
            reverse=True
        )[:10]
        
        self.analysis_result = {
            'total_views': total_views,
            'total_users': total_users,
            'unique_urls': unique_urls,
            'page_stats': page_stats,
            'top_articles': top_articles,
            'top_searches': list(top_sc_words)[:10]
        }
        
        return self.analysis_result
    
    def _save_to_db(self) -> Dict[str, Any]:
        """DB 저장"""
        # 데이터 변환
        converted = self.converter.convert_batch(self.current_data)
        aggregated = self.converter.aggregate_by_key(converted)
        
        # DB 연결
        ga_logs = KnewsGalogsTable(
            database=self.db_config.get('database'),
            user=self.db_config.get('user'),
            password=self.db_config.get('password'),
            host=self.db_config.get('host'),
            port=self.db_config.get('port'),
            logger=self.logger
        )
        
        saved = 0
        failed = 0
        
        try:
            for record in aggregated:
                if ga_logs.save(record):
                    saved += 1
                else:
                    failed += 1
        finally:
            ga_logs.close()
        
        return {
            'total_records': len(self.current_data),
            'converted': len(converted),
            'aggregated': len(aggregated),
            'saved': saved,
            'failed': failed
        }
    
    def _load_existing_data(self, start_date: str, end_date: str) -> bool:
        """기존 데이터 로드"""
        # 파일명 패턴: ga4_data_20240101_20240107.json
        filename = f"ga4_data_{start_date.replace('-', '')}_{end_date.replace('-', '')}.json"
        file_path = os.path.join(self.output_dir, filename)
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                self.current_data = json.load(f)
            return True
        
        return False
    
    def _log(self, message: str, error: bool = False):
        """로그 출력"""
        if self.logger:
            if error:
                self.logger.error(message)
            else:
                self.logger.info(message)
        else:
            print(f"[GA4] {message}")

