-- ============================================================
-- PostgreSQL 'korean' 텍스트 검색 설정 확인
-- ============================================================

-- 1. 사용 가능한 텍스트 검색 설정 확인
SELECT cfgname, cfgnamespace::regnamespace as schema
FROM pg_ts_config
WHERE cfgname IN ('korean', 'simple', 'english')
ORDER BY cfgname;

-- 2. 모든 텍스트 검색 설정 목록
SELECT cfgname FROM pg_ts_config ORDER BY cfgname;

-- ============================================================
-- 결과 해석:
-- - 'korean'이 있으면 → 한글 형태소 분석 가능
-- - 'korean'이 없으면 → 'simple' 사용 (공백 기준 분리)
-- ============================================================
