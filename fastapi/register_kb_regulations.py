#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KB신용정보 사규 91개를 데이터베이스에 일괄 등록하는 스크립트

- 4a: 여비규정(wzruleseq=350) wzcateseq/wzpubno 업데이트
- 4b: 파싱 완료 7개 규정 등록 (docx_json/에서 JSON 읽기)
- 4c: 나머지 83개 규정 플레이스홀더 등록 (Excel 데이터 기반)
"""

import os
import sys
import json
import shutil
import re
from pathlib import Path
from datetime import datetime

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'applib'))

from api.timescale_dbv1 import TimescaleDB
from settings import settings

# 디렉토리 설정
DOCX_JSON_DIR = Path(settings.APPLIB_DIR) / "docx_json"
MERGE_JSON_DIR = Path(settings.APPLIB_DIR) / "merge_json"
WWW_STATIC_FILE_DIR = Path(settings.WWW_STATIC_FILE_DIR)

# 파싱 완료 7개 규정 (여비규정 제외 - 이미 등록됨)
PARSED_REGULATIONS = [
    {"file": "(10-1)_브랜드관리규정_230630.json",  "wzpubno": "10-1",  "wzcateseq": 10, "fallback_name": "브랜드관리규정"},
    {"file": "(11-10)_자점검사업무지침_230627.json", "wzpubno": "11-10", "wzcateseq": 11, "fallback_name": "자점검사업무지침"},
    {"file": "(11-16)_이용자보호기준_250409.json",   "wzpubno": "11-16", "wzcateseq": 11, "fallback_name": "이용자보호기준"},
    {"file": "(5-5)_운영리스크관리지침_230630.json",  "wzpubno": "5-5",   "wzcateseq": 5,  "fallback_name": "운영리스크관리지침"},
    {"file": "(6-16)_연수규정_251224.json",          "wzpubno": "6-16",  "wzcateseq": 6,  "fallback_name": "연수규정"},
    {"file": "(7-2)_문서관리규정_250305.json",       "wzpubno": "7-2",   "wzcateseq": 7,  "fallback_name": "문서관리규정"},
    {"file": "(7-6)_열쇠관리지침_250730.json",       "wzpubno": "7-6",   "wzcateseq": 7,  "fallback_name": "열쇠관리지침"},
]

# 나머지 83개 플레이스홀더 규정 (별표제1호 기반)
# 여비규정(6-8)과 파싱 완료 7개 제외
PLACEHOLDER_REGULATIONS = [
    # 1. 정관·이사회
    {"wzpubno": "1-1",  "wzname": "정관",                     "wzcateseq": 1, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2025.01.03", "wzestabdate": "1999.10.09"},
    {"wzpubno": "1-2",  "wzname": "이사회규정",               "wzcateseq": 1, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2024.07.01", "wzestabdate": "1999.10.09"},
    # 2. 직제·윤리
    {"wzpubno": "2-1",  "wzname": "직제규정",                 "wzcateseq": 2, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2025.06.30", "wzestabdate": "1999.10.09"},
    {"wzpubno": "2-2",  "wzname": "직무전결규정",             "wzcateseq": 2, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2024.12.20", "wzestabdate": "1999.10.09"},
    {"wzpubno": "2-3",  "wzname": "윤리강령",                 "wzcateseq": 2, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2016.09.28", "wzestabdate": "2015.12.24"},
    {"wzpubno": "2-4",  "wzname": "임직원법규준수행동기준",    "wzcateseq": 2, "wzmgrdptnm": "감사부",              "wzlastrevdate": "2023.08.09", "wzestabdate": "2016.10.11"},
    # 3. 협의회(위원회)
    {"wzpubno": "3-1",  "wzname": "경영협의회규정",           "wzcateseq": 3, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2021.09.07", "wzestabdate": "2000.03.17"},
    {"wzpubno": "3-2",  "wzname": "리스크관리협의회규정",     "wzcateseq": 3, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2018.03.26", "wzestabdate": "2006.03.10"},
    {"wzpubno": "3-3",  "wzname": "IT투자협의회운영지침",     "wzcateseq": 3, "wzmgrdptnm": "IT지원부",            "wzlastrevdate": "2022.07.28", "wzestabdate": "2022.01.07"},
    {"wzpubno": "3-4",  "wzname": "정보보호위원회지침",       "wzcateseq": 3, "wzmgrdptnm": "IT지원부(정보보호팀)", "wzlastrevdate": "2024.03.01", "wzestabdate": "2023.06.01"},
    {"wzpubno": "3-5",  "wzname": "ESG추진협의회운영기준",    "wzcateseq": 3, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2022.02.10", "wzestabdate": "2021.08.12"},
    {"wzpubno": "3-6",  "wzname": "채권책임심의회운영지침",    "wzcateseq": 3, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2025.03.05", "wzestabdate": "2019.03.04"},
    {"wzpubno": "3-7",  "wzname": "재무전략협의회규정",       "wzcateseq": 3, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2024.12.03", "wzestabdate": "2024.12.03"},
    {"wzpubno": "3-8",  "wzname": "AI윤리위원회운영지침",     "wzcateseq": 3, "wzmgrdptnm": "IT지원부",            "wzlastrevdate": "",            "wzestabdate": "2025.10.01"},
    # 4. 재무·회계
    {"wzpubno": "4-1",  "wzname": "예산규정",                 "wzcateseq": 4, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2023.05.03", "wzestabdate": "1999.10.09"},
    {"wzpubno": "4-2",  "wzname": "내부회계관리규정",         "wzcateseq": 4, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2024.12.30", "wzestabdate": "2003.02.26"},
    {"wzpubno": "4-3",  "wzname": "회계규정",                 "wzcateseq": 4, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2023.06.30", "wzestabdate": "1999.10.09"},
    {"wzpubno": "4-4",  "wzname": "세무업무처리지침",         "wzcateseq": 4, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2010.06.04", "wzestabdate": "2005.12.19"},
    {"wzpubno": "4-5",  "wzname": "내부회계관리운영지침",     "wzcateseq": 4, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2024.12.30", "wzestabdate": "2003.02.26"},
    {"wzpubno": "4-6",  "wzname": "회계업무처리규정",         "wzcateseq": 4, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2003.02.26", "wzestabdate": "2003.02.26"},
    {"wzpubno": "4-7",  "wzname": "통장관리지침",             "wzcateseq": 4, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2025.08.07", "wzestabdate": "2010.09.10"},
    {"wzpubno": "4-8",  "wzname": "재무관리규정",             "wzcateseq": 4, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2024.12.03", "wzestabdate": "2024.12.03"},
    # 5. 기획·리스크관리
    {"wzpubno": "5-1",  "wzname": "성과관리규정",             "wzcateseq": 5, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2025.04.01", "wzestabdate": "2000.06.12"},
    {"wzpubno": "5-2",  "wzname": "업무제안운영지침",         "wzcateseq": 5, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2023.06.08", "wzestabdate": "2001.07.01"},
    {"wzpubno": "5-3",  "wzname": "리스크관리규정",           "wzcateseq": 5, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2023.06.30", "wzestabdate": "2006.03.10"},
    {"wzpubno": "5-4",  "wzname": "리스크관리지침",           "wzcateseq": 5, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2023.06.30", "wzestabdate": "2006.03.31"},
    # 5-5 운영리스크관리지침 - 파싱 완료
    {"wzpubno": "5-6",  "wzname": "모회사와의사전협의관리규정","wzcateseq": 5, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2024.10.24", "wzestabdate": "2016.10.28"},
    # 6. 인사·복지
    {"wzpubno": "6-1",  "wzname": "경영자문역운영규정",       "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2021.01.01", "wzestabdate": "2013.12.03"},
    {"wzpubno": "6-2",  "wzname": "보수및퇴직금규정",         "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2025.01.22", "wzestabdate": "1999.10.09"},
    {"wzpubno": "6-3",  "wzname": "이사보수규정",             "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2021.02.24", "wzestabdate": "2009.04.28"},
    {"wzpubno": "6-4",  "wzname": "임원퇴직금규정",           "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2010.01.29", "wzestabdate": "1999.10.09"},
    {"wzpubno": "6-5",  "wzname": "인사규정",                 "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2025.04.01", "wzestabdate": "1999.10.09"},
    {"wzpubno": "6-6",  "wzname": "집행임원운영규정",         "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2019.06.02", "wzestabdate": "2009.04.28"},
    {"wzpubno": "6-7",  "wzname": "복지후생규정",             "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2025.01.22", "wzestabdate": "1999.10.09"},
    # 6-8 여비규정 - 이미 등록됨
    {"wzpubno": "6-9",  "wzname": "복무규정",                 "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2022.07.26", "wzestabdate": "1999.10.09"},
    {"wzpubno": "6-10", "wzname": "인사규정시행지침",         "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2025.03.05", "wzestabdate": "1999.10.09"},
    {"wzpubno": "6-11", "wzname": "복지후생규정시행지침",     "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2025.01.22", "wzestabdate": "2000.06.12"},
    {"wzpubno": "6-12", "wzname": "복무규정시행지침",         "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2025.04.21", "wzestabdate": "1999.10.09"},
    {"wzpubno": "6-13", "wzname": "선임직원운영지침",         "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2018.06.28", "wzestabdate": "2016.04.29"},
    {"wzpubno": "6-14", "wzname": "계약인력관리지침",         "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2024.09.01", "wzestabdate": "2003.04.03"},
    {"wzpubno": "6-15", "wzname": "촉탁직관리지침",           "wzcateseq": 6, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2024.09.01", "wzestabdate": "2012.08.01"},
    # 6-16 연수규정 - 파싱 완료
    # 7. 총무·경영지원
    {"wzpubno": "7-1",  "wzname": "계약규정",                 "wzcateseq": 7, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2024.12.03", "wzestabdate": "1999.10.09"},
    # 7-2 문서관리규정 - 파싱 완료
    {"wzpubno": "7-3",  "wzname": "자산관리규정",             "wzcateseq": 7, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2022.08.23", "wzestabdate": "1999.10.09"},
    {"wzpubno": "7-4",  "wzname": "전자문서관리지침",         "wzcateseq": 7, "wzmgrdptnm": "IT지원부",            "wzlastrevdate": "2005.12.19", "wzestabdate": "2005.12.19"},
    {"wzpubno": "7-5",  "wzname": "차량관리지침",             "wzcateseq": 7, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2023.06.08", "wzestabdate": "2001.06.05"},
    # 7-6 열쇠관리지침 - 파싱 완료
    {"wzpubno": "7-7",  "wzname": "외부용역·컨설팅운영지침",  "wzcateseq": 7, "wzmgrdptnm": "경영전략부",          "wzlastrevdate": "2024.12.19", "wzestabdate": "2020.12.24"},
    # 8. IT·정보보호
    {"wzpubno": "8-1",  "wzname": "전산업무규정",             "wzcateseq": 8, "wzmgrdptnm": "IT지원부",            "wzlastrevdate": "2023.06.09", "wzestabdate": "1999.10.09"},
    {"wzpubno": "8-2",  "wzname": "고객정보의제공및이용에관한규정","wzcateseq": 8, "wzmgrdptnm": "IT지원부(정보보호팀)", "wzlastrevdate": "2023.01.01", "wzestabdate": "2010.03.29"},
    {"wzpubno": "8-3",  "wzname": "정보보호규정",             "wzcateseq": 8, "wzmgrdptnm": "IT지원부(정보보호팀)", "wzlastrevdate": "2025.06.01", "wzestabdate": "2024.02.01"},
    {"wzpubno": "8-4",  "wzname": "전산업무지침",             "wzcateseq": 8, "wzmgrdptnm": "IT지원부",            "wzlastrevdate": "2019.12.20", "wzestabdate": "2000.06.12"},
    {"wzpubno": "8-5",  "wzname": "고객정보관리지침",         "wzcateseq": 8, "wzmgrdptnm": "IT지원부(정보보호팀)", "wzlastrevdate": "2025.03.20", "wzestabdate": "2009.11.27"},
    {"wzpubno": "8-6",  "wzname": "신용정보관리지침",         "wzcateseq": 8, "wzmgrdptnm": "IT지원부(정보보호팀)", "wzlastrevdate": "2025.03.20", "wzestabdate": "2021.10.08"},
    {"wzpubno": "8-7",  "wzname": "정보보호관리지침",         "wzcateseq": 8, "wzmgrdptnm": "IT지원부(정보보호팀)", "wzlastrevdate": "2025.07.14", "wzestabdate": "2024.03.01"},
    {"wzpubno": "8-8",  "wzname": "IT인프라보안지침",         "wzcateseq": 8, "wzmgrdptnm": "IT지원부(정보보호팀)", "wzlastrevdate": "2024.03.01", "wzestabdate": "2024.03.01"},
    {"wzpubno": "8-9",  "wzname": "물리보안지침",             "wzcateseq": 8, "wzmgrdptnm": "IT지원부(정보보호팀)", "wzlastrevdate": "2025.04.01", "wzestabdate": "2024.03.01"},
    {"wzpubno": "8-10", "wzname": "그룹IT협력지침",           "wzcateseq": 8, "wzmgrdptnm": "IT지원부(정보보호팀)", "wzlastrevdate": "2022.07.28", "wzestabdate": "2016.10.31"},
    {"wzpubno": "8-11", "wzname": "개인정보보호내부관리계획",  "wzcateseq": 8, "wzmgrdptnm": "IT지원부(정보보호팀)", "wzlastrevdate": "2025.08.01", "wzestabdate": "2013.02.26"},
    {"wzpubno": "8-12", "wzname": "AI업무규정",               "wzcateseq": 8, "wzmgrdptnm": "IT지원부",            "wzlastrevdate": "",            "wzestabdate": "2025.10.01"},
    # 9. 영업
    {"wzpubno": "9-1",  "wzname": "신용정보업무규정",         "wzcateseq": 9, "wzmgrdptnm": "IT지원부(정보보호팀)", "wzlastrevdate": "2025.04.01", "wzestabdate": "1999.10.09"},
    {"wzpubno": "9-2",  "wzname": "채권추심업무처리지침",     "wzcateseq": 9, "wzmgrdptnm": "영업추진부",          "wzlastrevdate": "2016.11.07", "wzestabdate": "2007.05.08"},
    {"wzpubno": "9-3",  "wzname": "공인전자문서센터운영규정",  "wzcateseq": 9, "wzmgrdptnm": "전자문서사업부",      "wzlastrevdate": "2025.10.02", "wzestabdate": "2023.06.01"},
    {"wzpubno": "9-4",  "wzname": "전자화문서관리규정",       "wzcateseq": 9, "wzmgrdptnm": "전자문서사업부",      "wzlastrevdate": "2022.10.14", "wzestabdate": "2022.10.14"},
    {"wzpubno": "9-5",  "wzname": "임대차조사업무처리지침",    "wzcateseq": 9, "wzmgrdptnm": "특수사업부",          "wzlastrevdate": "2024.06.11", "wzestabdate": "2006.12.14"},
    {"wzpubno": "9-6",  "wzname": "주민등록정보관리지침",     "wzcateseq": 9, "wzmgrdptnm": "영업추진부",          "wzlastrevdate": "2025.01.10", "wzestabdate": "2003.05.12"},
    {"wzpubno": "9-7",  "wzname": "민원서류발급업무처리지침",  "wzcateseq": 9, "wzmgrdptnm": "영업추진부",          "wzlastrevdate": "2022.07.27", "wzestabdate": "2008.09.19"},
    {"wzpubno": "9-8",  "wzname": "채권추심내부기준",         "wzcateseq": 9, "wzmgrdptnm": "영업추진부",          "wzlastrevdate": "2025.04.23", "wzestabdate": "2024.10.14"},
    # 10. 브랜드·ESG
    # 10-1 브랜드관리규정 - 파싱 완료
    {"wzpubno": "10-2", "wzname": "기부금운영규정",           "wzcateseq": 10, "wzmgrdptnm": "경영전략부",         "wzlastrevdate": "2010.11.30", "wzestabdate": "2010.11.30"},
    {"wzpubno": "10-3", "wzname": "소셜미디어사용및운영에관한지침","wzcateseq": 10, "wzmgrdptnm": "경영전략부",     "wzlastrevdate": "2023.06.30", "wzestabdate": "2013.11.12"},
    # 11. 감사·준법·법무
    {"wzpubno": "11-1",  "wzname": "감사규정",                "wzcateseq": 11, "wzmgrdptnm": "감사부",             "wzlastrevdate": "2024.02.16", "wzestabdate": "1999.10.09"},
    {"wzpubno": "11-2",  "wzname": "사규관리규정",            "wzcateseq": 11, "wzmgrdptnm": "경영전략부",         "wzlastrevdate": "2025.10.15", "wzestabdate": "1999.10.09"},
    {"wzpubno": "11-3",  "wzname": "그룹내부거래운영규정",     "wzcateseq": 11, "wzmgrdptnm": "감사부",             "wzlastrevdate": "2023.08.09", "wzestabdate": "2013.06.17"},
    {"wzpubno": "11-4",  "wzname": "내부통제규정",            "wzcateseq": 11, "wzmgrdptnm": "감사부",             "wzlastrevdate": "2023.08.09", "wzestabdate": "2009.02.20"},
    {"wzpubno": "11-5",  "wzname": "소송업무처리규정",        "wzcateseq": 11, "wzmgrdptnm": "경영전략부",         "wzlastrevdate": "2019.12.20", "wzestabdate": "2005.12.19"},
    {"wzpubno": "11-6",  "wzname": "볼커룰(VolckerRule)업무규정","wzcateseq": 11, "wzmgrdptnm": "경영전략부",      "wzlastrevdate": "2015.07.21", "wzestabdate": "2015.07.21"},
    {"wzpubno": "11-7",  "wzname": "사고금정리규정",          "wzcateseq": 11, "wzmgrdptnm": "감사부",             "wzlastrevdate": "2023.06.27", "wzestabdate": "2000.06.12"},
    {"wzpubno": "11-8",  "wzname": "민원업무처리규정",        "wzcateseq": 11, "wzmgrdptnm": "감사부",             "wzlastrevdate": "2025.01.09", "wzestabdate": "1999.10.09"},
    {"wzpubno": "11-9",  "wzname": "감사규정시행지침",        "wzcateseq": 11, "wzmgrdptnm": "감사부",             "wzlastrevdate": "2023.08.09", "wzestabdate": "2000.06.12"},
    # 11-10 자점검사업무지침 - 파싱 완료
    {"wzpubno": "11-11", "wzname": "부점장업무인계인수지침",   "wzcateseq": 11, "wzmgrdptnm": "감사부",             "wzlastrevdate": "2025.06.10", "wzestabdate": "2006.04.04"},
    {"wzpubno": "11-12", "wzname": "업무위탁운용에관한지침",   "wzcateseq": 11, "wzmgrdptnm": "감사부",             "wzlastrevdate": "2024.10.23", "wzestabdate": "2010.03.26"},
    {"wzpubno": "11-13", "wzname": "금융범죄행위에대한고발지침","wzcateseq": 11, "wzmgrdptnm": "감사부",             "wzlastrevdate": "2019.12.20", "wzestabdate": "2004.09.14"},
    {"wzpubno": "11-14", "wzname": "직장내성희롱예방지침",     "wzcateseq": 11, "wzmgrdptnm": "경영전략부",         "wzlastrevdate": "2003.12.03", "wzestabdate": "2003.12.03"},
    {"wzpubno": "11-15", "wzname": "내부자신고제도운영지침",   "wzcateseq": 11, "wzmgrdptnm": "감사부",             "wzlastrevdate": "2018.12.26", "wzestabdate": "2011.03.31"},
    # 11-16 이용자보호기준 - 파싱 완료
    {"wzpubno": "11-17", "wzname": "내부통제정책",            "wzcateseq": 11, "wzmgrdptnm": "감사부",             "wzlastrevdate": "2025.07.21", "wzestabdate": "2025.07.21"},
]


def get_db():
    """DB 연결"""
    return TimescaleDB(
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )


def get_next_rule_id(db):
    """다음 wzruleid 조회"""
    result = db.query("SELECT COALESCE(MAX(wzruleid), 0) + 1 as next_id FROM wz_rule", one=True)
    return result['next_id']


def register_parsed_regulation(db, reg_info, next_rule_id):
    """파싱 완료 규정 등록 (JSON 데이터 포함)"""
    json_path = DOCX_JSON_DIR / reg_info["file"]
    if not json_path.exists():
        print(f"  [SKIP] JSON 파일 없음: {json_path}")
        return None

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    doc_info = data.get("문서정보", {})

    # 규정명: JSON에서 추출, 없으면 fallback
    wzname = doc_info.get("규정명") or doc_info.get("규정표기명") or reg_info["fallback_name"]
    wzname = wzname.strip().replace(" ", "") if wzname else reg_info["fallback_name"]
    if not wzname:
        wzname = reg_info["fallback_name"]

    # 소관부서
    wzmgrdptnm = doc_info.get("소관부서", "") or ""

    # 날짜 정보
    wzestabdate = doc_info.get("제정일", "") or ""
    wzlastrevdate = doc_info.get("최종개정일", "") or ""

    # 조문 내용을 텍스트로 변환
    content_text = wzname
    sections = data.get("조문내용", [])
    for section in sections:
        if isinstance(section, dict):
            content_text += " " + section.get("내용", "")

    # DOCX 파일명 매칭
    docx_pattern = reg_info["file"].replace(".json", ".docx")
    docx_files = list(Path(settings.DOCX_DIR).glob(docx_pattern.replace("_", "*")))
    docx_filename = docx_files[0].name if docx_files else ""

    insert_query = """
    INSERT INTO wz_rule (
        wzlevel, wzruleid, wzname, wzedittype, wzpubno,
        wzestabdate, wzlastrevdate,
        wzmgrdptnm, wzcateseq,
        wzfiledocx, wzfilejson, wzfilepdf,
        wzcreatedby, wzmodifiedby, wznewflag,
        content_text, index_status
    ) VALUES (
        %s, %s, %s, %s, %s,
        %s, %s,
        %s, %s,
        %s, %s, %s,
        %s, %s, %s,
        %s, %s
    ) RETURNING wzruleseq
    """

    params = (
        1,                            # wzlevel
        next_rule_id,                 # wzruleid
        wzname,                       # wzname
        '현행',                       # wzedittype
        reg_info["wzpubno"],          # wzpubno
        wzestabdate,                  # wzestabdate
        wzlastrevdate,                # wzlastrevdate
        wzmgrdptnm,                   # wzmgrdptnm
        reg_info["wzcateseq"],        # wzcateseq
        docx_filename,                # wzfiledocx
        reg_info["file"],             # wzfilejson
        '',                           # wzfilepdf
        'migration',                  # wzcreatedby
        'migration',                  # wzmodifiedby
        '현행',                       # wznewflag
        content_text[:5000],          # content_text (제한)
        'pending',                    # index_status
    )

    result = db.query(insert_query, params, one=True, commit=True)
    if isinstance(result, dict):
        return result['wzruleseq']
    return result


def register_placeholder_regulation(db, reg_info, next_rule_id):
    """플레이스홀더 규정 등록 (파일 없이 기본정보만)"""
    insert_query = """
    INSERT INTO wz_rule (
        wzlevel, wzruleid, wzname, wzedittype, wzpubno,
        wzestabdate, wzlastrevdate,
        wzmgrdptnm, wzcateseq,
        wzfiledocx, wzfilejson, wzfilepdf,
        wzcreatedby, wzmodifiedby, wznewflag,
        content_text, index_status
    ) VALUES (
        %s, %s, %s, %s, %s,
        %s, %s,
        %s, %s,
        %s, %s, %s,
        %s, %s, %s,
        %s, %s
    ) RETURNING wzruleseq
    """

    params = (
        1,                            # wzlevel
        next_rule_id,                 # wzruleid
        reg_info["wzname"],           # wzname
        '현행',                       # wzedittype
        reg_info["wzpubno"],          # wzpubno
        reg_info.get("wzestabdate", ""),  # wzestabdate
        reg_info.get("wzlastrevdate", ""), # wzlastrevdate
        reg_info["wzmgrdptnm"],       # wzmgrdptnm
        reg_info["wzcateseq"],        # wzcateseq
        '',                           # wzfiledocx
        '',                           # wzfilejson
        '',                           # wzfilepdf
        'migration',                  # wzcreatedby
        'migration',                  # wzmodifiedby
        '현행',                       # wznewflag
        reg_info["wzname"],           # content_text
        'pending',                    # index_status
    )

    result = db.query(insert_query, params, one=True, commit=True)
    if isinstance(result, dict):
        return result['wzruleseq']
    return result


def main():
    print("=" * 70)
    print("KB신용정보 사규 91개 일괄 등록 스크립트")
    print("=" * 70)

    db = get_db()
    try:
        db.connect()

        # 현재 상태 확인
        count = db.query("SELECT COUNT(*) as cnt FROM wz_rule", one=True)
        print(f"\n현재 wz_rule 테이블: {count['cnt']}개 규정")

        # ---- 4b: 파싱 완료 7개 규정 등록 ----
        print(f"\n[4b] 파싱 완료 7개 규정 등록")
        print("-" * 50)

        parsed_count = 0
        for reg in PARSED_REGULATIONS:
            # 이미 등록된 규정인지 확인
            existing = db.query(
                "SELECT wzruleseq FROM wz_rule WHERE wzpubno = %s AND wznewflag = '현행'",
                (reg["wzpubno"],), one=True
            )
            if existing:
                print(f"  [SKIP] {reg['wzpubno']} - 이미 등록됨 (seq={existing['wzruleseq']})")
                continue

            next_id = get_next_rule_id(db)
            wzruleseq = register_parsed_regulation(db, reg, next_id)
            if wzruleseq:
                print(f"  [OK] {reg['wzpubno']} {reg['fallback_name']} → wzruleseq={wzruleseq}, wzruleid={next_id}")
                parsed_count += 1

        print(f"  파싱 완료 규정 {parsed_count}개 등록 완료")

        # ---- 4c: 나머지 83개 플레이스홀더 등록 ----
        print(f"\n[4c] 플레이스홀더 규정 {len(PLACEHOLDER_REGULATIONS)}개 등록")
        print("-" * 50)

        placeholder_count = 0
        for reg in PLACEHOLDER_REGULATIONS:
            # 이미 등록된 규정인지 확인
            existing = db.query(
                "SELECT wzruleseq FROM wz_rule WHERE wzpubno = %s AND wznewflag = '현행'",
                (reg["wzpubno"],), one=True
            )
            if existing:
                print(f"  [SKIP] {reg['wzpubno']} {reg['wzname']} - 이미 등록됨")
                continue

            next_id = get_next_rule_id(db)
            wzruleseq = register_placeholder_regulation(db, reg, next_id)
            if wzruleseq:
                placeholder_count += 1
                if placeholder_count <= 5 or placeholder_count % 20 == 0:
                    print(f"  [OK] {reg['wzpubno']} {reg['wzname']} → seq={wzruleseq}")

        print(f"  플레이스홀더 규정 {placeholder_count}개 등록 완료")

        # ---- 최종 확인 ----
        print(f"\n{'=' * 70}")
        print("등록 결과 확인")
        print("-" * 50)

        total = db.query("SELECT COUNT(*) as cnt FROM wz_rule WHERE wznewflag = '현행'", one=True)
        print(f"현행 규정 총 {total['cnt']}개")

        # 분류별 확인
        results = db.query("""
            SELECT c.wzcateseq, c.wzcatename, COUNT(r.wzruleseq) as cnt
            FROM wz_cate c
            LEFT JOIN wz_rule r ON r.wzcateseq = c.wzcateseq AND r.wznewflag = '현행'
            GROUP BY c.wzcateseq, c.wzcatename
            ORDER BY c.wzcateseq
        """)
        for row in results:
            print(f"  제{row['wzcateseq']}편 {row['wzcatename']}: {row['cnt']}개")

        print(f"\n{'=' * 70}")
        print("KB신용정보 사규 등록 완료!")
        print("=" * 70)

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
