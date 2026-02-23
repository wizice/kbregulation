#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 병합 프로그램
PDF에서 추출한 JSON (글머리 기호 정확)과 DOCX에서 추출한 JSON (내용 정확)을 병합

사용법:
    python merge_json.py
    또는
    python merge_json.py --pdf-json path/to/pdf.json --docx-json path/to/docx.json --output path/to/output.json
"""

import json
import os
import sys
import re
from typing import Dict, List, Any, Tuple
from pathlib import Path
import argparse
from datetime import datetime
import logging

# fastapi 경로를 sys.path에 추가하여 settings 사용 가능하게 함
sys.path.insert(0, str(Path(__file__).parent.parent))
from settings import settings

# 로깅 설정
log_dir = Path(f'{settings.APPLIB_DIR}/logs')
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'merge_json_{datetime.now():%Y%m%d_%H%M%S}.log'

# 로그 포맷 설정
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'

# 파일과 콘솔 핸들러 설정
logging.basicConfig(
    level=logging.DEBUG,
    format=log_format,
    datefmt=date_format,
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"로그 파일: {log_file}")

class JSONMerger:
    """PDF와 DOCX에서 추출한 JSON을 병합하는 클래스"""

    def __init__(self, pdf_json_path: str, docx_json_path: str):
        """
        초기화

        Args:
            pdf_json_path: PDF에서 추출한 JSON 파일 경로
            docx_json_path: DOCX에서 추출한 JSON 파일 경로
        """
        self.pdf_json_path = Path(pdf_json_path)
        self.docx_json_path = Path(docx_json_path)
        self.pdf_data = None
        self.docx_data = None

        logger.info(f"PDF JSON: {self.pdf_json_path}")
        logger.info(f"DOCX JSON: {self.docx_json_path}")

    def load_json_files(self) -> bool:
        """JSON 파일들을 로드"""
        try:
            # PDF JSON 로드
            if self.pdf_json_path.exists():
                with open(self.pdf_json_path, 'r', encoding='utf-8') as f:
                    self.pdf_data = json.load(f)
                logger.info(f"PDF JSON 로드 완료: {len(self.pdf_data.get('조문내용', []))} 개 조문")
            else:
                logger.warning(f"PDF JSON 파일이 존재하지 않습니다: {self.pdf_json_path}")
                return False

            # DOCX JSON 로드
            if self.docx_json_path.exists():
                with open(self.docx_json_path, 'r', encoding='utf-8') as f:
                    self.docx_data = json.load(f)

                # sections를 조문내용으로 변환
                if 'sections' in self.docx_data:
                    self.docx_data['조문내용'] = self.docx_data['sections']
                    del self.docx_data['sections']

                logger.info(f"DOCX JSON 로드 완료: {len(self.docx_data.get('조문내용', []))} 개 조문")
            else:
                logger.warning(f"DOCX JSON 파일이 존재하지 않습니다: {self.docx_json_path}")
                return False

            return True

        except Exception as e:
            logger.error(f"JSON 파일 로드 중 오류: {e}")
            return False

    def merge_sections(self) -> List[Dict[str, Any]]:
        """조문 내용을 병합"""
        merged_sections = []

        pdf_sections = self.pdf_data.get('조문내용', [])
        docx_sections = self.docx_data.get('조문내용', [])

        # PDF 섹션을 seq로 매핑
        pdf_map = {section.get('seq'): section for section in pdf_sections if 'seq' in section}
        docx_map = {section.get('seq'): section for section in docx_sections if 'seq' in section}

        logger.info(f"PDF 섹션 수: {len(pdf_map)}, DOCX 섹션 수: {len(docx_map)}")

        # 모든 seq 번호 수집
        all_seqs = set(pdf_map.keys()) | set(docx_map.keys())

        for seq in sorted(all_seqs):
            pdf_section = pdf_map.get(seq, {})
            docx_section = docx_map.get(seq, {})

            # 병합된 섹션 생성
            merged_section = {
                'seq': seq,
                '레벨': max(pdf_section.get('레벨', 0), docx_section.get('레벨', 0)),
                '내용': docx_section.get('내용', '') or pdf_section.get('내용', ''),
                '번호': pdf_section.get('번호', '') or docx_section.get('번호', ''),
                '관련이미지': pdf_section.get('관련이미지', []) or docx_section.get('관련이미지', [])
            }

            merged_sections.append(merged_section)

        logger.info(f"병합된 섹션 수: {len(merged_sections)}")
        return merged_sections

    def merge_documents_info(self) -> Dict[str, Any]:
        """문서 정보를 병합"""
        pdf_info = self.pdf_data.get('문서정보', {})
        # 웹 API는 '문서정보', 폴더 실행은 'document_info' 사용
        docx_info = self.docx_data.get('문서정보', self.docx_data.get('document_info', {}))

        # DOCX의 document_info를 우선하고 PDF로 보완
        merged_info = docx_info.copy()

        for key, value in pdf_info.items():
            if key not in merged_info or not merged_info[key]:
                merged_info[key] = value

        logger.info(f"문서 정보 병합 완료")
        return merged_info

    def merge_regulation(self) -> Dict[str, Any]:
        """규정을 병합하여 최종 결과 생성"""
        if not self.pdf_data or not self.docx_data:
            logger.error("데이터가 로드되지 않았습니다")
            return None

        # 조문 내용 병합
        merged_sections = self.merge_sections()

        # 문서 정보 병합
        merged_info = self.merge_documents_info()

        # 최종 결과 구성
        result = {
            '문서정보': merged_info,
            '조문내용': merged_sections
        }

        # 추가 필드들 복사
        for field in ['preview_data', 'images']:
            if field in self.docx_data:
                result[field] = self.docx_data[field]

        # 병합 메타데이터 추가
        result['merge_info'] = {
            'merge_date': datetime.now().isoformat(),
            'source_pdf': str(self.pdf_json_path),
            'source_docx': str(self.docx_json_path),
            'merge_type': 'auto'
        }

        logger.info("규정 병합 완료")
        return result

def extract_wzruleid(filepath: str) -> str:
    """파일명에서 wzruleid 추출 (파일명 형식: {wzruleid}_{규정명}_{timestamp}.json)"""
    filename = os.path.basename(filepath)

    # 파일명 앞부분이 숫자로 시작하면 wzruleid로 간주
    match = re.match(r'^(\d+)_', filename)
    if match:
        return match.group(1)
    return ""

def extract_base_filename(filepath: str) -> str:
    """파일 경로에서 기본 파일명 추출 (확장자 및 타임스탬프 제거)"""
    # JSON 확장자 제거 (if present)
    filename = filepath
    if filename.endswith('.json'):
        filename = filename[:-5]

    # 타임스탬프 패턴 제거 (_YYYYMMDD_HHMMSS, _YYYYMMDD 등)
    patterns = [
        r'_\d{8}_\d{6}$',  # _20241201_153045
        r'_\d{8}$',        # _20241201
        r'_\d{6}$',        # _153045
    ]

    for pattern in patterns:
        filename = re.sub(pattern, '', filename)

    return filename

def normalize_filename(filename: str) -> str:
    """파일명을 정규화하여 매칭 가능하게 만듦"""
    # 기본 파일명 추출
    base = extract_base_filename(filename)

    # 1. 버전 번호 뒤의 점 제거 (6.4.1. -> 6.4.1)
    normalized = re.sub(r'(\d+\.\d+\.\d+)\.(\s|_)', r'\1\2', base)

    # 2. 언더스코어를 공백으로 변경
    normalized = normalized.replace('_', ' ')

    # 3. 연속된 공백을 하나로 합치기
    normalized = re.sub(r'\s+', ' ', normalized)

    # 4. 앞뒤 공백 제거
    normalized = normalized.strip()

    return normalized

def find_best_match(docx_base: str, pdf_files: List[Path]) -> Path:
    """DOCX 파일에 대해 가장 적합한 PDF 파일 찾기"""
    docx_normalized = normalize_filename(docx_base)

    # 정확한 매치 우선 찾기
    for pdf_file in pdf_files:
        pdf_base = extract_base_filename(pdf_file.name)
        if docx_base == pdf_base:
            return pdf_file

    # 정규화된 매치 찾기
    for pdf_file in pdf_files:
        pdf_normalized = normalize_filename(pdf_file.name)
        if docx_normalized == pdf_normalized:
            return pdf_file

    # 언더스코어/공백 변환해서 찾기
    docx_alt = docx_base.replace(' ', '_')
    for pdf_file in pdf_files:
        pdf_base = extract_base_filename(pdf_file.name)
        if docx_alt == pdf_base:
            return pdf_file

    return None

def find_matching_files(docx_dir: Path, pdf_dir: Path) -> List[Tuple[Path, Path]]:
    """매칭되는 파일 쌍 찾기 - 개선된 매칭 로직"""
    matches = []
    matched_pdf_files = set()

    docx_files = list(docx_dir.glob('*.json'))
    pdf_files = list(pdf_dir.glob('*.json'))

    logger.info(f"DOCX 파일 수: {len(docx_files)}, PDF 파일 수: {len(pdf_files)}")

    for docx_file in docx_files:
        docx_base = extract_base_filename(docx_file.name)

        # 이미 매칭된 PDF 파일들을 제외하고 최적 매치 찾기
        available_pdf_files = [f for f in pdf_files if f not in matched_pdf_files]
        best_match = find_best_match(docx_base, available_pdf_files)

        if best_match:
            matches.append((docx_file, best_match))
            matched_pdf_files.add(best_match)
            logger.info(f"매칭 발견: {docx_file.name} <-> {best_match.name}")
        else:
            logger.warning(f"매칭 실패: {docx_file.name} (매칭되는 PDF 파일 없음)")

    logger.info(f"총 {len(matches)} 개 파일 쌍 발견")
    return matches

def merge_single_pair(docx_file: Path, pdf_file: Path, output_dir: Path) -> bool:
    """단일 파일 쌍 병합"""
    try:
        merger = JSONMerger(str(pdf_file), str(docx_file))

        if not merger.load_json_files():
            logger.error(f"파일 로드 실패: {docx_file.name}, {pdf_file.name}")
            return False

        merged_result = merger.merge_regulation()

        if merged_result:
            # wzruleid 추출 (DOCX 파일명에서 우선 추출, 없으면 PDF에서 추출)
            wzruleid = extract_wzruleid(docx_file.name) or extract_wzruleid(pdf_file.name)

            # 출력 파일명 생성
            base_name = extract_base_filename(docx_file.name)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # wzruleid가 있으면 파일명에 포함
            if wzruleid:
                output_file = output_dir / f'{wzruleid}_{base_name}_{timestamp}.json'
            else:
                output_file = output_dir / f'merged_{base_name}_{timestamp}.json'

            # 결과 저장
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(merged_result, f, ensure_ascii=False, indent=2)

            logger.info(f"병합 완료: {output_file.name}")
            return True
        else:
            logger.error(f"병합 실패: {docx_file.name}, {pdf_file.name}")
            return False

    except Exception as e:
        logger.error(f"병합 중 오류 발생: {e}")
        return False

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='PDF와 DOCX JSON 파일 병합')
    parser.add_argument('--docx-dir', default='docx_json', help='DOCX JSON 디렉토리')
    parser.add_argument('--pdf-dir', default='txt_json', help='PDF JSON 디렉토리')
    parser.add_argument('--output-dir', default='merged', help='출력 디렉토리')
    parser.add_argument('--single', help='단일 파일 기본명 지정')

    args = parser.parse_args()

    # 디렉토리 경로 설정
    docx_dir = Path(args.docx_dir)
    pdf_dir = Path(args.pdf_dir)
    output_dir = Path(args.output_dir)

    # 출력 디렉토리 생성
    output_dir.mkdir(exist_ok=True)

    if args.single:
        # 단일 파일 병합
        base_name = args.single
        docx_file = None
        pdf_file = None

        # 매칭되는 파일 찾기
        for f in docx_dir.glob('*.json'):
            if extract_base_filename(f.name) == base_name:
                docx_file = f
                break

        for f in pdf_dir.glob('*.json'):
            if extract_base_filename(f.name) == base_name:
                pdf_file = f
                break

        if docx_file and pdf_file:
            success = merge_single_pair(docx_file, pdf_file, output_dir)
            if success:
                print(f"병합 완료: {base_name}")
            else:
                print(f"병합 실패: {base_name}")
        else:
            print(f"매칭되는 파일을 찾을 수 없습니다: {base_name}")

    else:
        # 모든 파일 병합
        matches = find_matching_files(docx_dir, pdf_dir)

        success_count = 0
        total_count = len(matches)

        for docx_file, pdf_file in matches:
            if merge_single_pair(docx_file, pdf_file, output_dir):
                success_count += 1

        print(f"병합 완료: {success_count}/{total_count} 파일")

if __name__ == "__main__":
    main()