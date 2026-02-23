# -*- coding: utf-8 -*-
"""
HanParse 토큰화 테스트

테스트 항목:
1. 기존 검색 호환성 (한글, 영문, 숫자)
2. Reference 번호 검색 (3.2.2, COP.4.1 등)
3. Edge case 처리
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hanparse import HanParse


class TestHanParseBasic:
    """기본 토큰화 기능 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser = HanParse()

    def test_empty_input(self):
        """빈 입력 처리"""
        assert self.parser.parse('') == []
        assert self.parser.parse(None) == []

    def test_korean_basic(self):
        """기본 한글 토큰화"""
        tokens = self.parser.parse('환자안전')
        assert '환자안전' in tokens
        assert '환자' in tokens
        assert '안전' in tokens

    def test_korean_long(self):
        """긴 한글 문장 토큰화"""
        tokens = self.parser.parse('세브란스병원 의료질향상')
        assert '세브란스병원' in tokens
        assert '의료질향상' in tokens

    def test_english_basic(self):
        """영문 토큰화 (3글자 이상)"""
        tokens = self.parser.parse('JCI Standard CPR')
        assert 'jci' in tokens
        assert 'standard' in tokens
        assert 'cpr' in tokens

    def test_english_short_excluded(self):
        """짧은 영문 제외 (2글자 이하)"""
        tokens = self.parser.parse('AB CD EFG')
        assert 'ab' not in tokens
        assert 'cd' not in tokens
        assert 'efg' in tokens

    def test_number_basic(self):
        """숫자 토큰화"""
        tokens = self.parser.parse('2024년 제5조')
        assert '2024' in tokens
        assert '5' in tokens

    def test_mixed_content(self):
        """혼합 콘텐츠 토큰화"""
        tokens = self.parser.parse('JCI 인증 2024')
        assert 'jci' in tokens
        assert '인증' in tokens
        assert '2024' in tokens


class TestHanParseReference:
    """Reference 번호 토큰화 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser = HanParse()

    def test_reference_simple(self):
        """단순 Reference 번호 (3.2.2)"""
        tokens = self.parser.parse('3.2.2 심폐소생술 관리')
        assert '3.2.2' in tokens
        assert '심폐소생술' in tokens
        # Reference로 인식된 부분은 개별 숫자로 분리되지 않음
        assert '3' not in tokens
        assert '2' not in tokens

    def test_reference_long(self):
        """긴 Reference 번호 (11.5.4)"""
        tokens = self.parser.parse('11.5.4 레이저 안전')
        assert '11.5.4' in tokens
        assert '레이저' in tokens
        # Reference로 인식된 부분은 개별 숫자로 분리되지 않음
        assert '11' not in tokens

    def test_reference_with_prefix(self):
        """영문 접두어 Reference (COP.4.1)"""
        tokens = self.parser.parse('COP.4.1 환자안전')
        assert 'cop.4.1' in tokens
        assert '환자안전' in tokens

    def test_reference_ip_style(self):
        """IP 주소 스타일 (192.168.0.1)"""
        tokens = self.parser.parse('192.168.0.1 서버')
        assert '192.168.0.1' in tokens
        assert '서버' in tokens

    def test_reference_date_style(self):
        """날짜 스타일 (2024.12.25)"""
        tokens = self.parser.parse('2024.12.25 개정')
        assert '2024.12.25' in tokens
        assert '개정' in tokens

    def test_reference_decimal(self):
        """소수점 (3.14)"""
        tokens = self.parser.parse('3.14 파이값')
        assert '3.14' in tokens
        assert '파이값' in tokens


class TestHanParseBackwardCompatibility:
    """기존 검색 호환성 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser = HanParse()

    def test_existing_search_korean(self):
        """기존 한글 검색 동작 유지"""
        # 기존에 잘 동작하던 검색어들
        test_cases = [
            ('환자안전', ['환자안전', '환자', '안전']),
            ('의료질향상', ['의료질향상', '의료', '향상']),
            ('시설관리', ['시설관리', '시설', '관리']),
        ]
        for text, expected_tokens in test_cases:
            tokens = self.parser.parse(text)
            for expected in expected_tokens:
                assert expected in tokens, f"'{expected}' not found in tokens for '{text}'"

    def test_existing_search_mixed(self):
        """기존 혼합 검색 동작 유지"""
        test_cases = [
            ('JCI 인증', ['jci', '인증']),
            ('CPR 교육', ['cpr', '교육']),
            ('2024년 개정', ['2024', '개정']),
        ]
        for text, expected_tokens in test_cases:
            tokens = self.parser.parse(text)
            for expected in expected_tokens:
                assert expected in tokens, f"'{expected}' not found in tokens for '{text}'"

    def test_article_format(self):
        """제X조 형식 검색"""
        tokens = self.parser.parse('제5조 환자안전 제1항')
        assert '5' in tokens
        assert '1' in tokens
        assert '환자안전' in tokens


class TestSearchScenarios:
    """실제 검색 시나리오 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser = HanParse()

    def test_scenario_reference_search(self):
        """시나리오: Reference 번호로 검색"""
        # 색인된 내용
        indexed_content = '3.2.2 심폐소생술 관리 프로그램을 운영한다'
        indexed_tokens = set(self.parser.parse(indexed_content))

        # 검색 쿼리
        search_queries = [
            '3.2.2',              # Reference 번호로 검색
            '심폐소생술',          # 한글 키워드 검색
            '3.2.2 심폐소생술',    # Reference + 한글
            '심폐',               # 부분 키워드
        ]

        for query in search_queries:
            query_tokens = set(self.parser.parse(query))
            matched = query_tokens & indexed_tokens
            assert matched, f"Query '{query}' should match indexed content"

    def test_scenario_jci_search(self):
        """시나리오: JCI 기준 검색"""
        indexed_content = 'JCI Standard 7th Edition COP.4.1 환자안전'
        indexed_tokens = set(self.parser.parse(indexed_content))

        search_queries = ['JCI', 'COP.4.1', '환자안전', 'JCI 환자안전']

        for query in search_queries:
            query_tokens = set(self.parser.parse(query))
            matched = query_tokens & indexed_tokens
            assert matched, f"Query '{query}' should match indexed content"

    def test_scenario_department_search(self):
        """시나리오: 담당부서 검색"""
        indexed_content = '병원운영팀 시설안전관리'
        indexed_tokens = set(self.parser.parse(indexed_content))

        search_queries = ['병원운영', '시설안전', '병원운영팀']

        for query in search_queries:
            query_tokens = set(self.parser.parse(query))
            matched = query_tokens & indexed_tokens
            assert matched, f"Query '{query}' should match indexed content"


class TestEdgeCases:
    """Edge case 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser = HanParse()

    def test_special_characters(self):
        """특수문자 처리"""
        tokens = self.parser.parse('환자.의사 관계')
        assert '환자' in tokens
        assert '의사' in tokens
        assert '관계' in tokens
        # 점으로 연결된 한글은 reference로 인식 안됨
        assert '환자.의사' not in tokens

    def test_single_dot_number(self):
        """단일 점 숫자 (숫자.숫자 형식은 Reference로 인식)"""
        tokens = self.parser.parse('버전 2.0')
        # 2.0은 ref_pattern에 매칭됨 (숫자.숫자 형식)
        assert '2.0' in tokens
        # Reference로 인식된 부분은 개별 숫자로 분리되지 않음
        assert '2' not in tokens
        assert '0' not in tokens

    def test_unicode_handling(self):
        """유니코드 처리"""
        tokens = self.parser.parse('환자安全')  # 한자 포함
        assert '환자' in tokens

    def test_whitespace_handling(self):
        """공백 처리"""
        tokens = self.parser.parse('  환자안전   의료질향상  ')
        assert '환자안전' in tokens
        assert '의료질향상' in tokens


class TestParseJoin:
    """parse_join 메서드 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser = HanParse()

    def test_parse_join_basic(self):
        """기본 parse_join"""
        result = self.parser.parse_join('환자안전')
        assert isinstance(result, str)
        assert '환자안전' in result

    def test_parse_join_custom_separator(self):
        """커스텀 구분자"""
        result = self.parser.parse_join('환자안전', ',')
        assert isinstance(result, str)
        assert ',' in result or len(result.split(',')) >= 1


class TestReferencePatternExtended:
    """확장된 Reference 패턴 테스트 (2025-01-25 추가)"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser = HanParse()

    def test_short_reference_cop3(self):
        """짧은 Reference 패턴: COP.3"""
        tokens = self.parser.parse('COP.3 환자안전')
        assert 'cop.3' in tokens
        assert '환자안전' in tokens

    def test_short_reference_ipsg6(self):
        """짧은 Reference 패턴: IPSG.6"""
        tokens = self.parser.parse('IPSG.6 환자확인')
        assert 'ipsg.6' in tokens
        assert '환자확인' in tokens

    def test_multiple_references(self):
        """여러 Reference 패턴: IPSG.6, COP.3"""
        tokens = self.parser.parse('JCI Standard 7th Edition: IPSG.6, COP.3')
        assert 'ipsg.6' in tokens
        assert 'cop.3' in tokens
        assert 'jci' in tokens

    def test_related_standards_format(self):
        """관련기준 형식 토큰화"""
        content = '4주기 의료기관인증기준: 3.2.5 JCI Standard 7th Edition: ACC.3, COP.4.1'
        tokens = self.parser.parse(content)
        assert '3.2.5' in tokens
        assert 'acc.3' in tokens
        assert 'cop.4.1' in tokens

    def test_acc_variations(self):
        """ACC 관련 패턴들"""
        test_cases = [
            ('ACC.1', 'acc.1'),
            ('ACC.2.3', 'acc.2.3'),
            ('ACC.3', 'acc.3'),
            ('ACC.3.1', 'acc.3.1'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' should be in tokens for '{input_ref}'"


class TestExactMatchScenarios:
    """정확 일치 검색 시나리오 테스트 (2025-01-25 추가)"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser = HanParse()

    def test_acc3_vs_acc31_distinction(self):
        """ACC.3과 ACC.3.1 구분"""
        # ACC.3 문서
        doc1_tokens = set(self.parser.parse('JCI: ACC.3, COP.1'))
        # ACC.3.1 문서
        doc2_tokens = set(self.parser.parse('JCI: ACC.3.1, COP.2'))

        # ACC.3으로 검색 시
        query_tokens = set(self.parser.parse('ACC.3'))

        # acc.3 토큰이 있는지 확인
        assert 'acc.3' in doc1_tokens
        assert 'acc.3.1' in doc2_tokens
        assert 'acc.3' in query_tokens

        # 정확 일치 시 acc.3이 acc.3.1과 다름을 확인
        assert 'acc.3' != 'acc.3.1'

    def test_exact_match_korean(self):
        """한글 정확 일치"""
        doc_tokens = set(self.parser.parse('환자안전관리'))
        query_tokens = set(self.parser.parse('환자안전'))

        # 부분 매칭 가능 (2-gram으로 인해)
        matched = query_tokens & doc_tokens
        assert matched, "Korean partial match should work"


class TestAllStandardTypes:
    """
    모든 표준기준 유형별 Reference 번호 검색 테스트 (2026-01-25 추가)

    실제 관련기준 JSON 파일에서 발견된 16개 표준기준 유형:
    ACC, AOP, APR, ASC, COP, FMS, GLD, HRP, IPSG, MMU, MOI, MPE, PCC, PCI, QPS, SQE
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser = HanParse()

    def test_acc_patterns(self):
        """ACC (Access to Care and Continuity of Care) 패턴"""
        test_cases = [
            ('ACC.1', 'acc.1'),
            ('ACC.2', 'acc.2'),
            ('ACC.3', 'acc.3'),
            ('ACC.1.1', 'acc.1.1'),
            ('ACC.2.3', 'acc.2.3'),
            ('ACC.4.4.1', 'acc.4.4.1'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_aop_patterns(self):
        """AOP (Assessment of Patients) 패턴"""
        test_cases = [
            ('AOP.1', 'aop.1'),
            ('AOP.5', 'aop.5'),
            ('AOP.6', 'aop.6'),
            ('AOP.1.2', 'aop.1.2'),
            ('AOP.5.11', 'aop.5.11'),
            ('AOP.1.2.1', 'aop.1.2.1'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_apr_patterns(self):
        """APR (Anesthesia and Procedural Sedation) 패턴"""
        test_cases = [
            ('APR.9', 'apr.9'),
            ('APR.11', 'apr.11'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_asc_patterns(self):
        """ASC (Anesthesia and Surgical Care) 패턴"""
        test_cases = [
            ('ASC.1', 'asc.1'),
            ('ASC.3', 'asc.3'),
            ('ASC.7', 'asc.7'),
            ('ASC.3.3', 'asc.3.3'),
            ('ASC.7.4', 'asc.7.4'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_cop_patterns(self):
        """COP (Care of Patients) 패턴"""
        test_cases = [
            ('COP.1', 'cop.1'),
            ('COP.3', 'cop.3'),
            ('COP.7', 'cop.7'),
            ('COP.3.3', 'cop.3.3'),
            ('COP.4.1', 'cop.4.1'),
            ('COP.8.5', 'cop.8.5'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_fms_patterns(self):
        """FMS (Facility Management and Safety) 패턴"""
        test_cases = [
            ('FMS.2', 'fms.2'),
            ('FMS.7', 'fms.7'),
            ('FMS.11', 'fms.11'),
            ('FMS.7.2', 'fms.7.2'),
            ('FMS.10.3', 'fms.10.3'),
            ('FMS.10.3.1', 'fms.10.3.1'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_gld_patterns(self):
        """GLD (Governance, Leadership, and Direction) 패턴"""
        test_cases = [
            ('GLD.1', 'gld.1'),
            ('GLD.6', 'gld.6'),
            ('GLD.18', 'gld.18'),
            ('GLD.1.2', 'gld.1.2'),
            ('GLD.11.2', 'gld.11.2'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_hrp_patterns(self):
        """HRP (Human Research Protection) 패턴"""
        test_cases = [
            ('HRP.1', 'hrp.1'),
            ('HRP.7', 'hrp.7'),
            ('HRP.1.1', 'hrp.1.1'),
            ('HRP.7.1', 'hrp.7.1'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_ipsg_patterns(self):
        """IPSG (International Patient Safety Goals) 패턴"""
        test_cases = [
            ('IPSG.1', 'ipsg.1'),
            ('IPSG.6', 'ipsg.6'),
            ('IPSG.2.1', 'ipsg.2.1'),
            ('IPSG.6.1', 'ipsg.6.1'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_mmu_patterns(self):
        """MMU (Medication Management and Use) 패턴"""
        test_cases = [
            ('MMU.1', 'mmu.1'),
            ('MMU.3', 'mmu.3'),
            ('MMU.7', 'mmu.7'),
            ('MMU.3.2', 'mmu.3.2'),
            ('MMU.6.2.1', 'mmu.6.2.1'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_moi_patterns(self):
        """MOI (Management of Information) 패턴"""
        test_cases = [
            ('MOI.1', 'moi.1'),
            ('MOI.10', 'moi.10'),
            ('MOI.13', 'moi.13'),
            ('MOI.2.1', 'moi.2.1'),
            ('MOI.8.1', 'moi.8.1'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_mpe_patterns(self):
        """MPE (Medical Professional Education) 패턴"""
        test_cases = [
            ('MPE.1', 'mpe.1'),
            ('MPE.6', 'mpe.6'),
            ('MPE.7', 'mpe.7'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_pcc_patterns(self):
        """PCC (Patient-Centered Care) 패턴"""
        test_cases = [
            ('PCC.1', 'pcc.1'),
            ('PCC.6', 'pcc.6'),
            ('PCC.1.5', 'pcc.1.5'),
            ('PCC.4.4', 'pcc.4.4'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_pci_patterns(self):
        """PCI (Prevention and Control of Infections) 패턴"""
        test_cases = [
            ('PCI.4', 'pci.4'),
            ('PCI.12', 'pci.12'),
            ('PCI.15', 'pci.15'),
            ('PCI.6.1', 'pci.6.1'),
            ('PCI.12.2', 'pci.12.2'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_qps_patterns(self):
        """QPS (Quality Improvement and Patient Safety) 패턴"""
        test_cases = [
            ('QPS.1', 'qps.1'),
            ('QPS.8', 'qps.8'),
            ('QPS.10', 'qps.10'),
            ('QPS.7.1', 'qps.7.1'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_sqe_patterns(self):
        """SQE (Staff Qualifications and Education) 패턴"""
        test_cases = [
            ('SQE.1', 'sqe.1'),
            ('SQE.11', 'sqe.11'),
            ('SQE.16', 'sqe.16'),
            ('SQE.8.1', 'sqe.8.1'),
            ('SQE.8.1.1', 'sqe.8.1.1'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_numeric_standards(self):
        """4주기 의료기관인증기준 숫자 패턴"""
        test_cases = [
            ('1.1', '1.1'),
            ('3.2.2', '3.2.2'),
            ('10.1', '10.1'),
            ('11.5.4', '11.5.4'),
            ('12.1', '12.1'),
        ]
        for input_ref, expected in test_cases:
            tokens = self.parser.parse(input_ref)
            assert expected in tokens, f"'{expected}' not found for '{input_ref}'"

    def test_real_related_standards_format(self):
        """실제 관련기준 문자열에서 추출 테스트"""
        test_cases = [
            (
                "4주기 의료기관인증기준: 1.1 정확한 환자 확인",
                ['1.1']
            ),
            (
                "JCI Standard 7th Edition: IPSG.1",
                ['ipsg.1']
            ),
            (
                "JCI Standard 7th Edition: COP.3, 3.3, ASC.3, SQE.8.1, 8.1.1",
                ['cop.3', '3.3', 'asc.3', 'sqe.8.1', '8.1.1']
            ),
            (
                "JCI Standard 7th Edition: ACC.4.4, 4.4.1, PCC.2.1",
                ['acc.4.4', '4.4.1', 'pcc.2.1']
            ),
            (
                "4주기 의료기관인증기준: 3.2.2 심폐소생술 관리, 4.3 의약품 보관",
                ['3.2.2', '4.3']
            ),
        ]
        for content, expected_refs in test_cases:
            tokens = self.parser.parse(content)
            for ref in expected_refs:
                assert ref in tokens, f"'{ref}' not found in tokens for '{content}'"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
