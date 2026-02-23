# -*- coding: utf-8 -*-
"""
Google Analytics 4 (GA4) Data 수집 클래스
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

import numpy as np
import pandas as pd

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric,
    FilterExpression, OrderBy
)

logger = logging.getLogger("kdnews.ga4")


class GA4Collector:
    """Google Analytics 4 데이터 수집기"""
    
    def __init__(self, property_id: str, credentials_path: str):
        """
        초기화
        
        Args:
            property_id: GA4 Property ID
            credentials_path: 서비스 계정 키 파일 경로
        """
        self.property_id = property_id
        self.credentials_path = credentials_path
        
        # 인증 설정
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        
        # 클라이언트 초기화
        self.client = BetaAnalyticsDataClient()
        
        # 통계 초기화
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_days': 0,
            'total_records': 0,
            'errors': []
        }
    
    def format_report(self, response) -> pd.DataFrame:
        """GA4 응답을 DataFrame으로 변환"""
        # Row index
        row_index_names = [header.name for header in response.dimension_headers]
        row_header = []
        for i in range(len(row_index_names)):
            row_header.append([row.dimension_values[i].value for row in response.rows])
        
        row_index_named = pd.MultiIndex.from_arrays(
            np.array(row_header), 
            names=np.array(row_index_names)
        )
        
        # Row flat data
        metric_names = [header.name for header in response.metric_headers]
        data_values = []
        for i in range(len(metric_names)):
            data_values.append([row.metric_values[i].value for row in response.rows])
        
        output = pd.DataFrame(
            data=np.transpose(np.array(data_values, dtype='f')),
            index=row_index_named,
            columns=metric_names
        )
        return output
    
    def collect_data(
        self,
        dimensions: Union[str, List[str]] = None,
        metrics: Union[str, List[str]] = None,
        start_date: str = None,
        end_date: str = None,
        dimension_filter: Optional[FilterExpression] = None,
        dimension_order_bys: Optional[List[OrderBy]] = None,
        metric_order_bys: Optional[List[OrderBy]] = None,
        default_dimension: str = 'date',
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        GA4 데이터 수집
        
        Returns:
            수집된 데이터 DataFrame
        """
        self.stats['start_time'] = datetime.now()
        
        # 차원 설정
        if dimensions is None:
            dimensions = [default_dimension]
        elif isinstance(dimensions, str):
            dimensions = [dimensions]
        
        # 날짜 관련 dimension이 없으면 default_dimension 추가
        if not any(d in dimensions for d in ['date', 'month', 'year']):
            dimensions.insert(0, default_dimension)
        
        # 지표 설정
        if metrics is None:
            metrics = []
        elif isinstance(metrics, str):
            metrics = [metrics]
        
        # Dimension과 Metric 객체로 변환
        dimension_objects = [Dimension(name=d) for d in dimensions]
        metric_objects = [Metric(name=m) for m in metrics]
        
        # 정렬 설정
        order_bys = []
        if dimension_order_bys:
            order_bys.extend(dimension_order_bys)
        if metric_order_bys:
            order_bys.extend(metric_order_bys)
        
        # 일자별 정렬 추가
        order_bys.append(
            OrderBy(
                dimension=OrderBy.DimensionOrderBy(dimension_name='date'),
                desc=False
            )
        )
        
        # 날짜 리스트 생성
        date_list = pd.date_range(start=start_date, end=end_date).strftime('%Y-%m-%d').tolist()
        self.stats['total_days'] = len(date_list)
        
        df_list = []
        
        for date in date_list:
            try:
                logger.info(f"날짜별 조회중... {date}")
                
                request = RunReportRequest(
                    property=f'properties/{self.property_id}',
                    dimensions=dimension_objects,
                    metrics=metric_objects,
                    date_ranges=[DateRange(start_date=date, end_date=date)],
                    dimension_filter=dimension_filter,
                    order_bys=order_bys,
                    limit=limit
                )
                
                response = self.client.run_report(request)
                df = self.format_report(response)
                
                if not df.empty:
                    df_list.append(df)
                    logger.info(f"  수집: {len(df)}건")
                    self.stats['total_records'] += len(df)
                
            except Exception as e:
                error_msg = f"날짜 {date} 수집 실패: {str(e)}"
                logger.error(error_msg)
                self.stats['errors'].append({
                    'date': date,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # 데이터 합치기
        if df_list:
            result_df = pd.concat(df_list)
        else:
            result_df = pd.DataFrame()
        
        self.stats['end_time'] = datetime.now()
        return result_df
    
    def save_to_excel(self, df: pd.DataFrame, output_dir: str, 
                      filename: str = None, sheet_name: str = "GA4_Data") -> str:
        """데이터프레임을 엑셀 파일로 저장"""
        if filename is None:
            now = datetime.now()
            filename = f"ga4_data_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, filename)
        
        df_reset = df.reset_index()
        df_reset.to_excel(file_path, sheet_name=sheet_name, index=False)
        
        logger.info(f"엑셀 파일 저장: {file_path}")
        return file_path
    
    def save_to_json(self, df: pd.DataFrame, output_dir: str,
                     start_date: str, end_date: str, 
                     filename: str = None, orient: str = "records") -> str:
        """데이터프레임을 JSON 파일로 저장"""
        if filename is None:
            filename = f"ga4_data_{start_date}_{end_date}.json".replace("-", "")
        
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, filename)
        
        df_reset = df.reset_index()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json_data = df_reset.to_json(orient=orient, force_ascii=False)
            json_data = json.loads(json_data)
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"JSON 파일 저장: {file_path}")
        return file_path
    
    def get_stats(self) -> Dict[str, Any]:
        """수집 통계 반환"""
        if self.stats['start_time'] and self.stats['end_time']:
            duration = self.stats['end_time'] - self.stats['start_time']
            self.stats['duration_seconds'] = duration.total_seconds()
            self.stats['duration_str'] = str(duration).split('.')[0]
        
        return self.stats

