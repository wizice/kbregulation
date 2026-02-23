#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
병합된 JSON 파일 검증 스크립트
각 병합된 파일의 품질을 검사하고 보고서를 생성합니다.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import re
from datetime import datetime

# fastapi 경로를 sys.path에 추가하여 settings 사용 가능하게 함
sys.path.insert(0, str(Path(__file__).parent.parent))
from settings import settings

class MergeVerifier:
    """병합된 JSON 파일을 검증하는 클래스"""

    def __init__(self, merged_dir: str, pdf_dir: str, docx_json_path: str):
        self.merged_dir = Path(merged_dir)
        self.pdf_dir = Path(pdf_dir)
        self.docx_json_path = Path(docx_json_path)
        self.verification_results = []
        self.statistics = {
            'total_files': 0,
            'perfect_match': 0,
            'partial_match': 0,
            'no_docx_match': 0,
            'error_files': 0,
            'warnings': []
        }

    def load_json(self, filepath: Path) -> Dict:
        """JSON 파일 로드"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ JSON 로드 실패 ({filepath.name}): {e}")
            return None

    def verify_single_file(self, merged_file: Path) -> Dict:
        """단일 병합 파일 검증"""
        result = {
            'filename': merged_file.name,
            'status': 'unknown',
            'issues': [],
            'stats': {},
            'warnings': []
        }

        # 병합된 JSON 로드
        merged_data = self.load_json(merged_file)
        if not merged_data:
            result['status'] = 'error'
            result['issues'].append('파일 로드 실패')
            return result

        # 원본 PDF JSON 파일명 추출
        original_filename = merged_file.name.replace('merged_', '')
        pdf_file = self.pdf_dir / original_filename

        # PDF JSON 로드
        pdf_data = self.load_json(pdf_file)
        if not pdf_data:
            result['warnings'].append('원본 PDF JSON 파일을 찾을 수 없음')

        # 검증 항목들
        doc_info = merged_data.get('문서정보', {})
        articles = merged_data.get('조문내용', [])

        # 1. 문서 정보 검증
        if doc_info:
            result['stats']['regulation_name'] = doc_info.get('규정명', '')
            result['stats']['department'] = doc_info.get('담당부서', '')
            result['stats']['last_revision'] = doc_info.get('최종개정일', '')
            result['stats']['article_count'] = doc_info.get('조문갯수', 0)

            # 필수 필드 확인
            required_fields = ['규정명', '담당부서', '제정일']
            for field in required_fields:
                if not doc_info.get(field):
                    result['warnings'].append(f'문서정보: {field} 누락')

        # 2. 조문 내용 검증
        if articles:
            result['stats']['actual_article_count'] = len(articles)

            # 번호와 내용 검증
            empty_numbers = 0
            empty_contents = 0
            level_distribution = {}
            number_patterns = {
                '제X조': 0,
                'X.': 0,
                'X)': 0,
                '(X)': 0,
                '①': 0,
                '기타': 0
            }

            for article in articles:
                # 레벨 분포
                level = article.get('레벨', 0)
                level_distribution[level] = level_distribution.get(level, 0) + 1

                # 번호 검증
                number = article.get('번호', '')
                if not number:
                    empty_numbers += 1
                else:
                    # 번호 패턴 분류
                    if re.match(r'제\d+조', number):
                        number_patterns['제X조'] += 1
                    elif re.match(r'\d+\.', number):
                        number_patterns['X.'] += 1
                    elif re.match(r'\d+\)', number):
                        number_patterns['X)'] += 1
                    elif re.match(r'\(\d+\)', number):
                        number_patterns['(X)'] += 1
                    elif re.match(r'[①-⑩]', number):
                        number_patterns['①'] += 1
                    else:
                        number_patterns['기타'] += 1

                # 내용 검증
                content = article.get('내용', '')
                if not content:
                    empty_contents += 1

            result['stats']['level_distribution'] = level_distribution
            result['stats']['number_patterns'] = number_patterns
            result['stats']['empty_numbers'] = empty_numbers
            result['stats']['empty_contents'] = empty_contents

            # 문제 판단
            if empty_numbers > 0:
                result['issues'].append(f'번호 누락: {empty_numbers}개')
            if empty_contents > 0:
                result['issues'].append(f'내용 누락: {empty_contents}개')

            # 조문 개수 불일치 확인
            if doc_info.get('조문갯수', 0) != len(articles):
                result['warnings'].append(
                    f"조문 개수 불일치: 문서정보({doc_info.get('조문갯수', 0)}) != 실제({len(articles)})"
                )

        # 3. PDF와 비교 (선택적)
        if pdf_data:
            pdf_articles = pdf_data.get('조문내용', [])
            pdf_count = len(pdf_articles)
            merged_count = len(articles)

            if abs(pdf_count - merged_count) > 5:  # 5개 이상 차이
                result['warnings'].append(
                    f"PDF와 조문 수 차이: PDF({pdf_count}) vs 병합({merged_count})"
                )

        # 상태 판정
        if not result['issues']:
            if not result['warnings']:
                result['status'] = 'perfect'
            else:
                result['status'] = 'good'
        elif len(result['issues']) <= 2:
            result['status'] = 'acceptable'
        else:
            result['status'] = 'poor'

        return result

    def verify_all_files(self):
        """모든 병합 파일 검증"""
        merged_files = list(self.merged_dir.glob('merged_*.json'))
        self.statistics['total_files'] = len(merged_files)

        print(f"\n총 {len(merged_files)}개 파일 검증 시작")
        print("="*80)

        for i, merged_file in enumerate(merged_files, 1):
            print(f"\n[{i}/{len(merged_files)}] {merged_file.name}")

            result = self.verify_single_file(merged_file)
            self.verification_results.append(result)

            # 통계 업데이트
            if result['status'] == 'perfect':
                self.statistics['perfect_match'] += 1
                print(f"  ✅ 완벽한 병합")
            elif result['status'] == 'good':
                self.statistics['partial_match'] += 1
                print(f"  ✓ 양호한 병합 (경고 {len(result['warnings'])}개)")
            elif result['status'] == 'acceptable':
                self.statistics['partial_match'] += 1
                print(f"  ⚠️  허용 가능 (문제 {len(result['issues'])}개)")
            elif result['status'] == 'poor':
                self.statistics['no_docx_match'] += 1
                print(f"  ❌ 불량한 병합 (문제 {len(result['issues'])}개)")
            else:
                self.statistics['error_files'] += 1
                print(f"  ❌ 오류")

            # 상세 정보 출력
            if result['stats']:
                print(f"    규정명: {result['stats'].get('regulation_name', 'N/A')}")
                print(f"    조문수: {result['stats'].get('actual_article_count', 0)}개")

                if result['stats'].get('empty_contents', 0) > 0:
                    print(f"    ⚠️  내용 누락: {result['stats']['empty_contents']}개")
                if result['stats'].get('empty_numbers', 0) > 0:
                    print(f"    ⚠️  번호 누락: {result['stats']['empty_numbers']}개")

            # 경고 출력
            for warning in result.get('warnings', []):
                print(f"    ⚠️  {warning}")

    def generate_report(self):
        """검증 보고서 생성"""
        report_path = self.merged_dir / f"verification_report_{datetime.now():%Y%m%d_%H%M%S}.txt"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("병합 JSON 검증 보고서\n")
            f.write(f"생성 시간: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write("="*80 + "\n\n")

            # 요약 통계
            f.write("【요약 통계】\n")
            f.write(f"  총 파일 수: {self.statistics['total_files']}\n")
            f.write(f"  완벽한 병합: {self.statistics['perfect_match']} "
                   f"({self.statistics['perfect_match']/max(1,self.statistics['total_files'])*100:.1f}%)\n")
            f.write(f"  양호/허용: {self.statistics['partial_match']} "
                   f"({self.statistics['partial_match']/max(1,self.statistics['total_files'])*100:.1f}%)\n")
            f.write(f"  불량: {self.statistics['no_docx_match']} "
                   f"({self.statistics['no_docx_match']/max(1,self.statistics['total_files'])*100:.1f}%)\n")
            f.write(f"  오류: {self.statistics['error_files']}\n\n")

            # 상세 결과
            f.write("【상세 검증 결과】\n")
            f.write("-"*80 + "\n")

            # 상태별로 그룹화
            for status in ['perfect', 'good', 'acceptable', 'poor', 'error']:
                files_with_status = [r for r in self.verification_results if r['status'] == status]

                if files_with_status:
                    status_names = {
                        'perfect': '✅ 완벽한 병합',
                        'good': '✓ 양호한 병합',
                        'acceptable': '⚠️ 허용 가능',
                        'poor': '❌ 불량한 병합',
                        'error': '❌ 오류'
                    }

                    f.write(f"\n{status_names[status]} ({len(files_with_status)}개)\n")
                    f.write("-"*40 + "\n")

                    for result in files_with_status:
                        f.write(f"\n파일: {result['filename']}\n")

                        if result['stats']:
                            f.write(f"  규정명: {result['stats'].get('regulation_name', 'N/A')}\n")
                            f.write(f"  조문수: {result['stats'].get('actual_article_count', 0)}\n")

                            if result['stats'].get('empty_contents', 0) > 0:
                                f.write(f"  내용누락: {result['stats']['empty_contents']}개\n")
                            if result['stats'].get('empty_numbers', 0) > 0:
                                f.write(f"  번호누락: {result['stats']['empty_numbers']}개\n")

                        for issue in result.get('issues', []):
                            f.write(f"  ❌ {issue}\n")

                        for warning in result.get('warnings', []):
                            f.write(f"  ⚠️ {warning}\n")

            # 레벨 분포 통계
            f.write("\n" + "="*80 + "\n")
            f.write("【레벨 분포 통계】\n")
            all_levels = {}
            for result in self.verification_results:
                if result['stats'] and 'level_distribution' in result['stats']:
                    for level, count in result['stats']['level_distribution'].items():
                        all_levels[level] = all_levels.get(level, 0) + count

            for level in sorted(all_levels.keys()):
                f.write(f"  레벨 {level}: {all_levels[level]}개 조문\n")

            # 번호 패턴 통계
            f.write("\n【번호 패턴 통계】\n")
            all_patterns = {
                '제X조': 0,
                'X.': 0,
                'X)': 0,
                '(X)': 0,
                '①': 0,
                '기타': 0
            }
            for result in self.verification_results:
                if result['stats'] and 'number_patterns' in result['stats']:
                    for pattern, count in result['stats']['number_patterns'].items():
                        all_patterns[pattern] += count

            for pattern, count in all_patterns.items():
                if count > 0:
                    f.write(f"  {pattern}: {count}개\n")

        print(f"\n📊 보고서 생성 완료: {report_path}")
        return report_path

def main():
    """메인 함수"""
    # 경로 설정
    merged_dir = f'{settings.APPLIB_DIR}/merged'
    pdf_dir = f'{settings.APPLIB_DIR}/json'
    docx_json_path = f'{settings.BASE_DIR}/static/json/severance.json'

    # 검증기 생성 및 실행
    verifier = MergeVerifier(merged_dir, pdf_dir, docx_json_path)

    # 모든 파일 검증
    verifier.verify_all_files()

    # 보고서 생성
    report_path = verifier.generate_report()

    # 요약 출력
    print("\n" + "="*80)
    print("검증 완료!")
    print(f"  총 파일: {verifier.statistics['total_files']}")
    print(f"  완벽한 병합: {verifier.statistics['perfect_match']}")
    print(f"  양호/허용: {verifier.statistics['partial_match']}")
    print(f"  불량: {verifier.statistics['no_docx_match']}")
    print(f"  오류: {verifier.statistics['error_files']}")

if __name__ == '__main__':
    main()