# 테스트 가이드

## 테스트 스크립트 목록

### auth/ - 인증 관련 테스트
- `login_test.sh` - 로그인 기능 테스트
- `login_error_test.sh` - 로그인 에러 메시지 테스트 (2025-10-28 추가)
- `login_redirect_test.sh` - 로그인 후 리다이렉트 및 로그아웃 테스트 (2025-10-28 추가)
- `sevpolicy_login_test.sh` - 보안 강화 계정 로그인 테스트 (2025-10-28 추가) 🔒

### integration/ - 통합 테스트
- `test_sessionstorage_auth.sh` - **sessionStorage 인증 시스템 테스트 (2025-10-28 추가)** ⭐
- `test_edit_modal_tabs.sh` - 편집 모달 탭 전환 및 파싱 자동화 테스트
- `test_json_path_system.sh` - JSON 파일 경로 시스템 통합 테스트
- `test_json_content_edit.sh` - 기존 JSON 내용 편집 모달 로드 테스트
- `test_auto_merge.sh` - 저장 시 JSON_ALL.py와 create_summary.py 자동 실행 테스트
- `test_revision_workflow.sh` - 개정/제정 기능 통합 테스트 (기존)
- `test_revision_single_file.sh` - 개정 시 단일 파일 업데이트 검증 (신규)
- `test_manual_revision.py` - 수동 개정 워크플로우 테스트 (신규)

### comparison_table/ - 신구대비표 관련 테스트 ⭐ NEW (2025-11-13)
- `comparison_table_test.sh` - 신구대비표 파일 관리 통합 테스트 (Shell)
- `comparison_table_test.py` - 신구대비표 파일 관리 통합 테스트 (Python)
- `README.md` - 신구대비표 기능 사용 가이드 및 API 문서

### synonyms/ - 유사어 관리 테스트 ⭐ NEW (2025-12-09)
- `test_synonyms_api.py` - 유사어 API CRUD 테스트 (Python)
  - 목록/상세 조회, 등록/수정/삭제
  - JSON 내보내기, 유사어 확장
  - JSON 검증

### scripts/ - 유틸리티 스크립트
- `update_wzfilejson.py` - merge_json 폴더의 파일을 DB wzFileJson 컬럼에 업데이트

## 주요 테스트 시나리오

### 1. JSON 파일 경로 시스템 테스트
```bash
# JSON 파일 경로 업데이트
python3 scripts/update_wzfilejson.py --show-mapping  # 매핑 확인
python3 scripts/update_wzfilejson.py                  # Dry-run
python3 scripts/update_wzfilejson.py --execute        # 실제 실행
```

### 2. 편집 모달 워크플로우 테스트
```bash
./test/integration/test_edit_modal_tabs.sh
```
- 파일 업로드 → 파싱 → 자동 탭 전환
- 편집 저장 시 JSON 경로 업데이트
- 미리보기 시 JSON 파일 읽기

### 3. 인증 테스트
```bash
./test/auth/login_test.sh
```
- 로그인/로그아웃
- 세션 관리
- 권한 확인

### 4. 신구대비표 테스트 ⭐ NEW
```bash
./test/comparison_table_test.sh
```
- 신구대비표 파일 업로드/조회 API 테스트
- 데이터베이스 wzFileComparison 컬럼 확인
- 레거시 파일 호환성 테스트
- 자세한 문서: `test/comparison_table/README.md` 참고

### 5. 유사어 관리 테스트 ⭐ NEW (2025-12-09)
```bash
cd /home/wizice/regulation/fastapi
python3 test/synonyms/test_synonyms_api.py
```
- 유사어 CRUD API 테스트
- JSON 내보내기/검증 테스트
- 유사어 확장 기능 테스트
- 관리자 페이지: `/admin/synonyms`
- 자세한 문서: `docs/SYNONYM_MANAGEMENT.md` 참고

## 성공 기준

### JSON 파일 시스템
- ✅ wzFileJson 컬럼에 JSON 파일 경로 저장
- ✅ 미리보기 시 JSON 파일에서 내용 읽기
- ✅ 편집 저장 시 새 JSON 파일 생성 및 경로 업데이트
- ✅ 제정/개정 시 JSON 경로 올바르게 저장
- ✅ 170개 규정에 대한 JSON 경로 자동 매핑 완료

### 편집 모달
- ✅ 편집 모달 크기: 1200px x 90vh
- ✅ 파싱 완료 후 자동 탭 전환
- ✅ 내용 편집 영역 600px 이상
- ✅ 진행 상태 표시

### 미리보기
- ✅ 그라디언트 헤더 바
- ✅ 3열 그리드 레이아웃
- ✅ JSON 파일 우선 표시

## 최신 업데이트

### 2025-11-13
- **신구대비표 버전별 파일 관리 기능 추가** ⭐ 중요!
  - 문제: 규정 개정 시 신구대비표 파일이 규정코드로만 관리되어 버전별 구분 불가
  - 해결:
    - ✅ DB에 `wzFileComparison` TEXT 컬럼 추가 (wz_rule 테이블)
    - ✅ POST `/api/v1/rule/upload-comparison-table/{rule_id}` 엔드포인트 추가
    - ✅ GET `/api/v1/rule/comparison-table/{rule_id}` 엔드포인트 추가
    - ✅ 파일명 형식: `{wzRuleId}_{wzRuleSeq}_{개정일자}.pdf`
    - ✅ 자동 백업 기능 (comparisonTable_backup/ 폴더)
    - ✅ 레거시 파일 하위 호환성 유지 (`comparisonTable_{규정코드}.pdf`)
  - 변경 파일:
    - `api/service_rule_editor.py:1935-2102`: 업로드/조회 API 추가
    - `www/static/js/severance.js:5707-5774`: openComparisonTablePdf() 함수 수정
    - `test/comparison_table_test.sh`: Shell 기반 통합 테스트
    - `test/comparison_table_test.py`: Python 기반 통합 테스트
    - `test/comparison_table/README.md`: 사용 가이드 및 API 문서
  - 테스트 결과:
    - ✅ 파일 업로드 API 정상 작동
    - ✅ 파일 조회 API 정상 작동
    - ✅ wzFileComparison 컬럼 데이터 저장 확인
    - ✅ 레거시 파일 8개 호환성 유지
    - ✅ 기존 기능 회귀 테스트 통과 (172 현행 + 6 연혁 규정)
  - 향후 개선사항:
    - 관리자 UI에 업로드 버튼 추가 예정
    - JSON_ALL.py에 신구대비표 정보 포함 예정
  - 자세한 문서: `test/comparison_table/README.md` 참고

### 2025-10-28 (4)
- **관리자 계정 보안 강화 완료** 🔒 중요!
  - 문제: 취약한 admin/admin123!@# 계정으로 인한 권한 탈취 위험
  - 해결:
    - ✅ 새로운 관리자 계정 생성: sevpolicy / sevpolicy123!@#
    - ✅ 유추 어려운 사용자명 사용 (admin → sevpolicy)
    - ✅ 복잡한 비밀번호 적용 (대소문자, 숫자, 특수문자 포함)
    - ✅ 기존 admin 계정 비활성화 완료
    - ✅ 인증 로직에 is_active 체크 추가
  - 변경 파일:
    - `create_sevpolicy_admin.py`: 보안 강화 계정 생성 스크립트
    - `disable_admin_account.py`: admin 계정 비활성화 스크립트
    - `api/auth_middleware.py:131-135`: is_active 체크 로직 추가
    - `CLAUDE.md`: 관리자 계정 정보 업데이트
    - `test/auth/sevpolicy_login_test.sh`: 보안 계정 로그인 테스트
  - 테스트 결과:
    - ✅ sevpolicy 계정 로그인 성공
    - ✅ admin 계정 로그인 차단 확인
    - ✅ 잘못된 비밀번호 차단 확인
  - 보안 권고사항:
    - 첫 로그인 후 비밀번호 변경 권장
    - 정기적인 비밀번호 변경 필요 (90일)

### 2025-10-28 (3)
- **중복 로그인 방지 시스템 구현 완료** ⭐ 중요!
  - 문제: 같은 계정으로 여러 곳에서 동시 로그인 가능
  - 해결:
    - 새 로그인 시 기존 세션 자동 종료 (Redis 세션 관리)
    - 쿠키 기반 인증으로 단순화 (HttpOnly, Secure)
    - 401 에러 시 자동 로그인 페이지 리다이렉트
  - 변경 파일:
    - `api/auth_router.py`: terminate_user_sessions() 호출 추가, 세션 쿠키 설정
    - `api/auth_middleware.py`: 기존 인증 로직 유지
    - `templates/login.html`: 단순화 (sessionStorage 로직 제거)
    - `static/js/common.js`: 쿠키 기반 인증으로 통일, 401 에러 처리
    - `static/js/rule-editor.js`: CommonUtils.apiCall() 사용
  - 효과:
    - **다른 브라우저/기기**: 중복 로그인 시 기존 세션 종료 ✓
    - **같은 브라우저 내 탭**: 세션 공유 (정상 동작) ✓
    - Chrome 로그인 → Firefox 로그인 → Chrome 자동 로그아웃
  - 보안: HttpOnly 쿠키 (XSS 방지), Secure (HTTPS 전용), SameSite=Lax
  - 커밋: `9b3d1d6`

### 2025-10-28 (2)
- **로그인 에러 메시지 통일**
  - 문제: admin 아이디로 잘못된 비밀번호 입력 시 `[object Object]` 표시
  - 원인: 서버 에러 응답을 파싱하지 않고 객체 자체를 문자열로 표시
  - 해결: 모든 로그인 실패 시 "입력하신 로그인 정보가 올바르지 않습니다." 메시지 통일
  - 변경 파일: `templates/login.html` (242-302줄)
  - 추가 테스트: `test/auth/login_error_test.sh` - API 응답 및 브라우저 테스트 가이드

- **로그인 후 리다이렉트 경로 수정 및 로그아웃 버튼 추가**
  - 문제 1: 로그인 페이지 접속 시 `/admin/dashboard`로 리다이렉트되며 500 에러 발생
  - 문제 2: `/regulations/current` 페이지에 로그아웃 버튼 없음
  - 해결:
    - `app.py:354`: 로그인 성공 시 `/regulations/current`로 리다이렉트 변경
    - `app.py:843-851`: `/admin/dashboard`에서 파일 없을 때 에러 처리 추가
    - `templates/common/base.html:31-39`: 네비게이션 바에 로그아웃 버튼 추가
    - `static/css/layout.css:64-87`: 로그아웃 버튼 스타일 추가
    - `static/js/common.js:140-154`: 로그아웃 함수 이미 구현됨 (확인)
  - 추가 테스트: `test/auth/login_redirect_test.sh` - 리다이렉트 및 로그아웃 플로우 테스트

### 2025-10-31
- **개정 시 파일명 형식 통일**
  - 문제: 개정 시 `merged_11.5.1._의료기기_관리_20251031_164702.json` 형식으로 저장됨
  - 원인: `service_rule_editor.py:2737`에서 `merged_{rule_pubno}_{safe_name}_{timestamp}.json` 형식 사용
  - 해결: 제정/편집과 동일하게 `{wzruleid}.json` 형식으로 통일
  - 변경 파일: `api/service_rule_editor.py:2643-2655, 2661-2719, 2738`
  - 적용:
    - 1순위: 기존 `{wzruleid}.json` 파일 사용 (있을 경우)
    - 2순위: 파라미터로 전달된 merged JSON 사용
    - 3순위: 최근 5분 내 생성된 merged_ 파일 자동 검색 (이전 방식 호환)
    - merged_ 파일 발견 시 자동으로 {wzruleid}.json으로 rename
  - 기존 파일 정리:
    - `merged_11.5.1._의료기기_관리_20251031_164702.json` → `7421.json`
    - `merged_6.4.1_의료사회복지체계_20251028_100643.json` → `5745.json`
    - `summary_severance.json`도 함께 업데이트됨

### 2025-09-29
- **개정 시 중복 파일 생성 문제 해결**
  - 문제: 개정 모달에서 저장 시 2개의 JSON 파일이 생성됨 (하나는 완전한 구조, 하나는 seq/level 없는 구조)
  - 원인: 첫 번째는 merge_json.py에서, 두 번째는 save_edited_content에서 생성
  - 해결: `service_rule_editor.py`의 revision mode를 수정하여 기존 파일 업데이트 방식으로 변경
  - 추가: `update_articles_content()` 헬퍼 함수로 JSON 구조 보존하면서 내용만 업데이트
- **테스트 스크립트 추가**
  - `test_revision_single_file.sh`: API 기반 개정 워크플로우 테스트
  - `test_manual_revision.py`: Python 기반 수동 테스트로 파일 업데이트 검증
  - 4가지 검증: 단일 파일 유지, seq/level 보존, 내용 업데이트, 같은 파일명 유지

### 2025-09-24 (2)
- `test_auto_merge.sh` 테스트 추가
- 편집/개정/제정 저장 시 JSON_ALL.py와 create_summary.py 자동 실행
- 백그라운드 작업으로 비동기 처리 (2초 지연)
- 연혁 규정 자동 이동 시스템 구현 (merge_json_old 폴더)

### 2025-09-24 (1)
- `test_json_content_edit.sh` 테스트 추가
- 기존 JSON 내용을 편집 모달에 자동 로드 기능 구현
- 파일 업로드 없이도 내용편집 탭 활성화
- 기존 내용과 새 업로드 구분 상태 메시지 표시

### 2025-09-23
- `update_wzfilejson.py` 스크립트 추가
- 170개 규정에 JSON 파일 경로 매핑 완료
- 중복 업데이트 방지 로직 구현 (1.1.1과 1.1.1.1 구분)

### 2025-09-22
- 편집 모달 탭 자동 전환 구현
- JSON 뷰어 API 추가 (`/api/v1/json/view/{rule_id}`)
- wzFileJson 컬럼 추가

## 디버깅 팁

### 로그 확인
```bash
tail -f /home/wizice/regulation/fastapi/logs/app.log
```

### DB 확인
```sql
-- JSON 경로가 설정된 규정 확인
SELECT wzruleseq, wzname, wzFileJson
FROM wz_rule
WHERE wzFileJson IS NOT NULL;

-- 특정 규정 번호로 검색
SELECT * FROM wz_rule
WHERE wzpubno LIKE '1.1.1.%';
```

### JSON 파일 확인
```bash
# 최신 merge_json 파일 확인
ls -lt /home/wizice/regulation/fastapi/applib/merge_json/*.json | head -10

# 특정 규정 번호의 JSON 파일 찾기
ls /home/wizice/regulation/fastapi/applib/merge_json/*1.1.1.*json
```

## 문제 해결

### ImportError: cannot import name 'TimescaleDBManagerV2'
- 해결: `DatabaseConnectionManager as TimescaleDBManagerV2` 사용

### 페이지 무한 로딩
- 원인: import 에러로 서버 시작 실패
- 해결: import 문 수정 후 서버 재시작

### JSON 파일 매핑 실패
- 원인: 파일명 패턴이 일치하지 않음
- 해결: 정규식 패턴 확인 및 수정

---

### 2025-12-09
- **유사어(Synonym) 관리 기능 추가** ⭐ 검색 엔진 기능 강화!
  - 목적: 검색 엔진에서 유사어 확장 검색 지원
  - 구현:
    - ✅ DB 테이블 생성 (`search_synonyms`)
    - ✅ REST API 개발 (CRUD + JSON 내보내기 + 검증)
    - ✅ 관리자 화면 개발 (`/admin/synonyms`)
    - ✅ Elasticsearch 형식 JSON 내보내기 지원
  - 신규 파일:
    - `sql/create_synonyms_table.sql` - 테이블 생성 SQL
    - `api/router_synonyms.py` - API 라우터
    - `templates/admin_synonyms.html` - 관리 화면
    - `static/js/admin-synonyms.js` - 프론트엔드 JS
    - `test/synonyms/test_synonyms_api.py` - API 테스트
    - `docs/SYNONYM_MANAGEMENT.md` - 기능 문서
  - 수정 파일:
    - `app.py` - 라우터 등록, 페이지 라우트 추가
  - 샘플 데이터: 12개 의료 용어 그룹 (환자, 의약품, 입원 등)
  - 테스트: `python3 test/synonyms/test_synonyms_api.py`
  - 자세한 문서: `docs/SYNONYM_MANAGEMENT.md` 참고

---

작성일: 2025-09-23
최종 수정: 2025-12-09