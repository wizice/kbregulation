# article_processor.py
import os
import json
import glob
from typing import List, Tuple, Dict, Optional, Callable
from pathlib import Path
from app_logger import setup_logging, get_logger
logger = get_logger(__name__)

class ArticleProcessor:
    """기사 분석과 DB 저장을 처리하는 통합 클래스"""
    
    def __init__(self, analyzer=None, db_manager=None, logger=None):
        self.analyzer = analyzer
        self.db_manager = db_manager
        self.logger = logger
    
    def find_files(self, directory: str, pattern: str = "*.json", 
                   recursive: bool = False) -> List[str]:
        """디렉토리에서 파일 찾기"""
        import fnmatch
        
        json_files = []
        if recursive:
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    if fnmatch.fnmatch(filename, pattern):
                        json_files.append(os.path.join(root, filename))
        else:
            json_files = glob.glob(os.path.join(directory, pattern))
        
        # 분석 결과 파일 제외
        json_files = [f for f in json_files if 'analysis' not in f]
        return json_files
    
    def find_file_pairs(self, directory: str, pattern: str = "*.json",
                       recursive: bool = False) -> List[Tuple[str, Optional[str]]]:
        """기사 파일과 분석 파일 쌍 찾기"""
        article_files = self.find_files(directory, pattern, recursive)
        file_pairs = []
        
        for article_file in article_files:
            # 대응하는 분석 파일 찾기
            base = os.path.splitext(article_file)[0]
            analysis_patterns = [
                f"{base}_analysis.json",
                f"{base}.analysis.json",
                article_file.replace('.json', '_analysis.json')
            ]
            
            analysis_file = None
            for pattern in analysis_patterns:
                if os.path.exists(pattern):
                    analysis_file = pattern
                    break
            
            file_pairs.append((article_file, analysis_file))
        
        return file_pairs
    
    def process_single(self, article_file: str, 
                      analysis_file: Optional[str] = None,
                      do_analyze: bool = True, 
                      do_save_db: bool = True,
                      force: bool = False,
                      use_cache: bool = True,
                      output_dir: Optional[str] = None,
                      skip_if_analyzed: bool = False) -> Dict:
        """단일 기사 처리
        
        Returns:
            {
                'success': bool,
                'article_file': str,
                'analysis': {
                    'success': bool,
                    'output_path': str,
                    'result': dict,
                    'error': str or None
                },
                'db': {
                    'success': bool,
                    'knews_id': int,
                    'error': str or None
                }
            }
        """
        result = {
            'success': False,
            'article_file': article_file,
            'analysis': None,
            'db': None
        }
        
        try:
            # 기사 데이터 읽기
            with open(article_file, 'r', encoding='utf-8') as f:
                article_data = json.load(f)
            
            article_id = article_data.get('idxno', 'unknown')
            
            # 1. 분석 단계
            if do_analyze and self.analyzer:
                # skip_if_analyzed 옵션이 활성화되고 분석 파일이 이미 있는 경우
                if skip_if_analyzed and analysis_file and os.path.exists(analysis_file):
                    if self.logger:
                        self.logger.info(f"분석 파일이 이미 존재하여 건너뜀: {analysis_file}")
                    
                    # 기존 분석 결과 읽기
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        existing_analysis = json.load(f)
                    
                    result['analysis'] = {
                        'success': True,
                        'output_path': analysis_file,
                        'result': existing_analysis,
                        'error': None,
                        'skipped': True
                    }
                else:
                    if self.logger:
                        self.logger.info(f"분석 시작: {article_file}")
                    
                    analysis_result = self.analyzer.analyze_article(
                        article_data, 
                        use_cache=use_cache
                    )
                    
                    # 분석 결과 저장
                    if output_dir:
                        base_name = os.path.basename(article_file).replace('.json', '')
                        output_path = os.path.join(output_dir, f"{base_name}_analysis.json")
                    else:
                        output_path = None
                    
                    saved_path = self.analyzer.save_analysis_result(
                        analysis_result,
                        output_path=output_path,
                        original_file_path=article_file
                    )
                    
                    result['analysis'] = {
                        'success': analysis_result['success'],
                        'output_path': saved_path,
                        'result': analysis_result,
                        'error': analysis_result.get('error'),
                        'skipped': False
                    }
                    
                    # 분석 성공 시 분석 파일 경로 업데이트
                    if analysis_result['success']:
                        analysis_file = saved_path
            
            # 2. DB 저장 단계
            if do_save_db and self.db_manager and analysis_file:
                if self.logger:
                    self.logger.info(f"DB 저장 시작: {article_id}")
                
                # 중복 확인
                if not force:
                    existing = self.db_manager.get_article_info(article_id)
                    if existing:
                        result['db'] = {
                            'success': False,
                            'error': 'Article already exists in DB',
                            'exists': True
                        }
                        logger.debug(f'이미 존재하는 기사이고 not force이므로 저장안함. existing:{existing}')
                        return result
                
                # DB 저장
                db_result = self.db_manager.save_article_with_analysis(
                    article_file,
                    analysis_file,
                    force
                )
                
                result['db'] = db_result
            
            # 전체 성공 여부
            result['success'] = (
                (not do_analyze or (result['analysis'] and result['analysis']['success'])) and
                (not do_save_db or (result['db'] and result['db']['success']))
            )
            
        except Exception as e:
            result['error'] = str(e)
            if self.logger:
                self.logger.error(f"처리 중 오류 {article_file}: {e}")
        
        return result
    
    def process_batch(self, file_pairs: List[Tuple[str, Optional[str]]],
                     do_analyze: bool = True,
                     do_save_db: bool = True,
                     force: bool = False,
                     use_cache: bool = True,
                     output_dir: Optional[str] = None,
                     skip_if_analyzed: bool = False,
                     progress_callback: Optional[Callable] = None) -> Dict:
        """배치 처리
        
        Returns:
            {
                'total': int,
                'success': int,
                'failed': int,
                'skipped': int,
                'analyzed': int,
                'saved_db': int,
                'errors': List[str]
            }
        """
        stats = {
            'total': len(file_pairs),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'analyzed': 0,
            'analysis_skipped': 0,
            'saved_db': 0,
            'errors': []
        }
        
        for idx, (article_file, analysis_file) in enumerate(file_pairs):
            try:
                result = self.process_single(
                    article_file=article_file,
                    analysis_file=analysis_file,
                    do_analyze=do_analyze,
                    do_save_db=do_save_db,
                    force=force,
                    use_cache=use_cache,
                    output_dir=output_dir,
                    skip_if_analyzed=skip_if_analyzed
                )
                
                if result['success']:
                    stats['success'] += 1
                    if result.get('analysis', {}).get('success'):
                        if result['analysis'].get('skipped'):
                            stats['analysis_skipped'] += 1
                        else:
                            stats['analyzed'] += 1
                    if result.get('db', {}).get('success'):
                        stats['saved_db'] += 1
                else:
                    if result.get('db', {}).get('exists'):
                        stats['skipped'] += 1
                    else:
                        stats['failed'] += 1
                        error_msg = f"{os.path.basename(article_file)}: "
                        if result.get('analysis', {}).get('error'):
                            error_msg += f"분석-{result['analysis']['error']}"
                        if result.get('db', {}).get('error'):
                            error_msg += f"DB-{result['db']['error']}"
                        stats['errors'].append(error_msg)
                
            except Exception as e:
                stats['failed'] += 1
                stats['errors'].append(f"{os.path.basename(article_file)}: {str(e)}")
            
            if progress_callback:
                progress_callback(idx + 1, len(file_pairs))
        
        return stats

