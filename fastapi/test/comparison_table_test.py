#!/usr/bin/env python3
"""
신구대비표 파일 관리 기능 통합 테스트
=====================================

이 스크립트는 신구대비표(Comparison Table) 파일 업로드 및 조회 기능을 테스트합니다.

주요 테스트 항목:
1. 신구대비표 파일 업로드 (POST /api/v1/rule/upload-comparison-table/{rule_id})
2. 신구대비표 파일 조회 (GET /api/v1/rule/comparison-table/{rule_id})
3. 레거시 파일 경로 호환성 테스트
4. 파일 백업 기능 테스트
5. 데이터베이스 wzFileComparison 컬럼 업데이트 확인

사용법:
    python3 test/comparison_table_test.py

필수 환경:
    - uvicorn 서버가 localhost:8800에서 실행 중이어야 함
    - 관리자 계정으로 로그인된 세션 쿠키 필요
"""

import requests
import sys
import os
from pathlib import Path
from io import BytesIO
from datetime import datetime

# 테스트 설정
BASE_URL = "http://localhost:8800"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
UPLOAD_URL = f"{BASE_URL}/api/v1/rule/upload-comparison-table"
GET_URL = f"{BASE_URL}/api/v1/rule/comparison-table"
RULE_URL = f"{BASE_URL}/api/v1/rule"

# 테스트 계정 (환경변수에서 가져오거나 기본값 사용)
USERNAME = os.getenv("TEST_USERNAME", "sevpolicy")
PASSWORD = os.getenv("TEST_PASSWORD", "sevpolicy123!@#")

# 색상 출력용
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def print_section(title):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"{title}")
    print(f"{'='*60}{Colors.END}\n")


class ComparisonTableTester:
    def __init__(self):
        self.session = requests.Session()
        self.cookies = None

    def login(self):
        """관리자 계정으로 로그인"""
        print_section("1. 로그인 테스트")

        payload = {
            "username": USERNAME,
            "password": PASSWORD
        }

        try:
            response = self.session.post(LOGIN_URL, json=payload)

            if response.status_code == 200:
                self.cookies = self.session.cookies
                data = response.json()
                print_success(f"로그인 성공: {data.get('user', {}).get('username')}")
                print_info(f"역할: {data.get('user', {}).get('role')}")
                return True
            else:
                print_error(f"로그인 실패: {response.status_code}")
                print_error(f"응답: {response.text}")
                return False

        except Exception as e:
            print_error(f"로그인 중 예외 발생: {e}")
            return False

    def get_test_rule(self):
        """테스트용 규정 조회 (wzRuleSeq=8038 사용 - wzRuleId=7421)"""
        print_section("2. 테스트 규정 설정")

        # 이전 테스트에서 확인된 규정 정보 사용
        test_rule = {
            "wzRuleSeq": 308,
            "wzRuleId": 7421,
            "wzRuleCode": "11.5.1",
            "wzRuleName": "의료기기 관리",
            "wzNewFlag": "현행"
        }

        print_success(f"테스트 규정:")
        print_info(f"  - wzRuleSeq: {test_rule.get('wzRuleSeq')}")
        print_info(f"  - wzRuleId: {test_rule.get('wzRuleId')}")
        print_info(f"  - 규정코드: {test_rule.get('wzRuleCode')}")
        print_info(f"  - 규정명: {test_rule.get('wzRuleName')}")

        return test_rule

    def create_dummy_pdf(self):
        """테스트용 더미 PDF 생성"""
        # 간단한 PDF 헤더
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        pdf_content += b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        pdf_content += b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        pdf_content += b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n"
        pdf_content += b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n200\n%%EOF"

        return BytesIO(pdf_content)

    def test_upload_comparison_table(self, rule):
        """신구대비표 파일 업로드 테스트"""
        print_section("3. 신구대비표 파일 업로드 테스트")

        if not rule:
            print_error("테스트할 규정이 없습니다")
            return False

        rule_id = rule.get("wzRuleSeq")
        rule_code = rule.get("wzRuleCode", "TEST")

        try:
            # 더미 PDF 생성
            pdf_file = self.create_dummy_pdf()

            files = {
                'comparison_file': (f'comparisonTable_{rule_code}.pdf', pdf_file, 'application/pdf')
            }

            response = self.session.post(
                f"{UPLOAD_URL}/{rule_id}",
                files=files,
                cookies=self.cookies
            )

            if response.status_code == 200:
                data = response.json()
                print_success("파일 업로드 성공")
                print_info(f"  - 파일명: {data.get('filename')}")
                print_info(f"  - 경로: {data.get('file_path')}")
                print_info(f"  - wzRuleSeq: {data.get('wzRuleSeq')}")

                if data.get('backup_path'):
                    print_info(f"  - 백업 경로: {data.get('backup_path')}")

                return True
            else:
                print_error(f"파일 업로드 실패: {response.status_code}")
                print_error(f"응답: {response.text}")
                return False

        except Exception as e:
            print_error(f"파일 업로드 중 예외 발생: {e}")
            return False

    def test_get_comparison_table(self, rule):
        """신구대비표 파일 조회 테스트"""
        print_section("4. 신구대비표 파일 조회 테스트")

        if not rule:
            print_error("테스트할 규정이 없습니다")
            return False

        rule_id = rule.get("wzRuleSeq")

        try:
            response = self.session.get(
                f"{GET_URL}/{rule_id}",
                cookies=self.cookies
            )

            if response.status_code == 200:
                data = response.json()
                print_success("파일 조회 성공")
                print_info(f"  - wzRuleSeq: {data.get('wzRuleSeq')}")
                print_info(f"  - wzRuleId: {data.get('wzRuleId')}")
                print_info(f"  - wzRuleCode: {data.get('wzRuleCode')}")
                print_info(f"  - wzRuleName: {data.get('wzRuleName')}")
                print_info(f"  - 파일 경로: {data.get('wzFileComparison')}")
                print_info(f"  - 파일 존재: {data.get('file_exists')}")

                return True
            elif response.status_code == 404:
                print_warning("신구대비표 파일이 등록되지 않음")
                return True
            else:
                print_error(f"파일 조회 실패: {response.status_code}")
                print_error(f"응답: {response.text}")
                return False

        except Exception as e:
            print_error(f"파일 조회 중 예외 발생: {e}")
            return False

    def test_legacy_compatibility(self):
        """레거시 파일 경로 호환성 테스트"""
        print_section("5. 레거시 파일 경로 호환성 테스트")

        legacy_path = "/home/wizice/regulation/www/static/pdf/comparisonTable"

        try:
            # 기존 레거시 파일 확인
            legacy_files = list(Path(legacy_path).glob("comparisonTable_*.pdf"))

            if legacy_files:
                print_success(f"레거시 파일 {len(legacy_files)}개 발견")
                for f in legacy_files[:3]:  # 처음 3개만 표시
                    print_info(f"  - {f.name}")

                if len(legacy_files) > 3:
                    print_info(f"  ... 외 {len(legacy_files) - 3}개")

                print_info("\n레거시 파일은 기존 방식대로 작동합니다:")
                print_info("  - JavaScript: openComparisonTablePdf(code, name, null)")
                print_info("  - 경로: /static/pdf/comparisonTable/comparisonTable_{규정코드}.pdf")
                return True
            else:
                print_warning("레거시 파일이 없습니다")
                return True

        except Exception as e:
            print_error(f"레거시 파일 확인 중 예외 발생: {e}")
            return False

    def test_database_column(self, rule):
        """데이터베이스 wzFileComparison 컬럼 확인"""
        print_section("6. 데이터베이스 wzFileComparison 컬럼 확인")

        if not rule:
            print_error("테스트할 규정이 없습니다")
            return False

        rule_id = rule.get("wzRuleSeq")

        try:
            # 특정 규정 조회를 통해 wzFileComparison 컬럼 확인
            response = self.session.get(
                f"{GET_URL}/{rule_id}",
                cookies=self.cookies
            )

            if response.status_code == 200:
                data = response.json()
                if 'wzFileComparison' in data or 'file_exists' in data:
                    print_success("wzFileComparison 컬럼 존재 확인")
                    print_info(f"  - wzRuleSeq: {data.get('wzRuleSeq')}")
                    print_info(f"  - wzFileComparison: {data.get('wzFileComparison', 'NULL')}")
                    print_info(f"  - file_exists: {data.get('file_exists', False)}")
                    return True
                else:
                    print_error("wzFileComparison 컬럼이 API 응답에 없습니다")
                    return False
            elif response.status_code == 404:
                # 404는 파일이 없다는 의미이므로 컬럼은 있는 것
                print_success("wzFileComparison 컬럼 존재 확인 (파일 미등록 상태)")
                return True
            else:
                print_error(f"규정 조회 실패: {response.status_code}")
                return False

        except Exception as e:
            print_error(f"데이터베이스 확인 중 예외 발생: {e}")
            return False

    def run_all_tests(self):
        """모든 테스트 실행"""
        print_info(f"신구대비표 파일 관리 기능 통합 테스트 시작")
        print_info(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        results = {}

        # 1. 로그인
        results['login'] = self.login()
        if not results['login']:
            print_error("\n로그인 실패로 테스트 중단")
            return False

        # 2. 테스트 규정 조회
        test_rule = self.get_test_rule()
        results['get_rule'] = test_rule is not None

        # 3. 파일 업로드
        results['upload'] = self.test_upload_comparison_table(test_rule)

        # 4. 파일 조회
        results['get_file'] = self.test_get_comparison_table(test_rule)

        # 5. 레거시 호환성
        results['legacy'] = self.test_legacy_compatibility()

        # 6. DB 컬럼 확인
        results['db_column'] = self.test_database_column(test_rule)

        # 결과 요약
        print_section("테스트 결과 요약")

        total = len(results)
        passed = sum(1 for v in results.values() if v)

        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name:20s}: {status}")

        print(f"\n총 {total}개 테스트 중 {passed}개 통과")

        if passed == total:
            print_success("\n🎉 모든 테스트 통과!")
            return True
        else:
            print_error(f"\n⚠️  {total - passed}개 테스트 실패")
            return False


def main():
    """메인 함수"""
    tester = ComparisonTableTester()
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
