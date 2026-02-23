-- =====================================================
-- 규정 다운로드 이력 테이블
-- =====================================================
-- 목적: 방문자가 어떤 규정을 다운로드했는지 이력 관리
-- 생성일: 2025-01-14
-- 실행: psql -h localhost -p 35432 -U severance -d severance -f create_regulation_download_logs.sql
-- =====================================================

-- 기존 테이블이 있으면 삭제 (개발용, 운영 환경에서는 주석 처리)
-- DROP TABLE IF EXISTS regulation_download_logs CASCADE;

-- 테이블 생성
CREATE TABLE IF NOT EXISTS regulation_download_logs (
    log_id BIGSERIAL PRIMARY KEY,

    -- 다운로드 대상 정보
    rule_id INTEGER,                     -- 규정 ID (wzRuleSeq)
    rule_name VARCHAR(500),              -- 규정명
    rule_pubno VARCHAR(100),             -- 공포번호 (예: 1.1.1)
    file_type VARCHAR(50) NOT NULL,      -- 파일 종류 (pdf, docx, hwp, appendix, comparison, history)
    file_name VARCHAR(500),              -- 다운로드한 파일명

    -- 방문자 정보
    ip_address VARCHAR(50),              -- IP 주소
    user_agent TEXT,                     -- User-Agent 전체 문자열
    device_type VARCHAR(50),             -- PC/Mobile/Tablet
    browser VARCHAR(100),                -- 브라우저 종류
    os VARCHAR(100),                     -- 운영체제

    -- 추가 정보
    referer TEXT,                        -- 유입 경로 (Referer)
    session_id VARCHAR(200),             -- 세션 ID (있는 경우)
    user_id VARCHAR(100),                -- 로그인 사용자 ID (있는 경우)

    -- 시간 정보
    downloaded_at TIMESTAMPTZ DEFAULT NOW(),

    -- 외래키 제약 (규정 삭제 시 로그 유지 - SET NULL)
    CONSTRAINT fk_download_logs_rule
        FOREIGN KEY (rule_id)
        REFERENCES wz_rule(wzruleseq)
        ON DELETE SET NULL
);

-- 인덱스 생성 (통계 및 검색 쿼리 성능 최적화)
CREATE INDEX IF NOT EXISTS idx_download_logs_downloaded_at
    ON regulation_download_logs(downloaded_at DESC);

CREATE INDEX IF NOT EXISTS idx_download_logs_rule_id
    ON regulation_download_logs(rule_id);

CREATE INDEX IF NOT EXISTS idx_download_logs_ip_address
    ON regulation_download_logs(ip_address);

CREATE INDEX IF NOT EXISTS idx_download_logs_file_type
    ON regulation_download_logs(file_type);

CREATE INDEX IF NOT EXISTS idx_download_logs_rule_pubno
    ON regulation_download_logs(rule_pubno);

-- 복합 인덱스 (특정 규정의 다운로드 이력 조회)
CREATE INDEX IF NOT EXISTS idx_download_logs_rule_date
    ON regulation_download_logs(rule_id, downloaded_at DESC);

-- 테이블 및 컬럼 설명
COMMENT ON TABLE regulation_download_logs IS '규정 다운로드 이력 관리 테이블 (방문자 추적)';
COMMENT ON COLUMN regulation_download_logs.log_id IS '로그 고유 ID (자동 증가)';
COMMENT ON COLUMN regulation_download_logs.rule_id IS '규정 ID (wz_rule.wzruleseq 참조)';
COMMENT ON COLUMN regulation_download_logs.rule_name IS '규정명 (비정규화, 조회 편의용)';
COMMENT ON COLUMN regulation_download_logs.rule_pubno IS '공포번호 (예: 1.1.1)';
COMMENT ON COLUMN regulation_download_logs.file_type IS '파일 종류 (pdf, docx, hwp, appendix, comparison, history)';
COMMENT ON COLUMN regulation_download_logs.file_name IS '다운로드한 파일명';
COMMENT ON COLUMN regulation_download_logs.ip_address IS '방문자 IP 주소';
COMMENT ON COLUMN regulation_download_logs.user_agent IS 'User-Agent 문자열';
COMMENT ON COLUMN regulation_download_logs.device_type IS '디바이스 종류 (PC/Mobile/Tablet)';
COMMENT ON COLUMN regulation_download_logs.browser IS '브라우저 종류';
COMMENT ON COLUMN regulation_download_logs.os IS '운영체제';
COMMENT ON COLUMN regulation_download_logs.referer IS '유입 경로 (Referer)';
COMMENT ON COLUMN regulation_download_logs.session_id IS '세션 ID';
COMMENT ON COLUMN regulation_download_logs.user_id IS '로그인 사용자 ID';
COMMENT ON COLUMN regulation_download_logs.downloaded_at IS '다운로드 시각';

-- 다운로드 통계 뷰
CREATE OR REPLACE VIEW v_regulation_download_stats AS
SELECT
    r.wzruleseq AS rule_id,
    r.wzname AS rule_name,
    r.wzpubno AS rule_pubno,
    COUNT(l.log_id) AS download_count,
    COUNT(DISTINCT l.ip_address) AS unique_visitors,
    MAX(l.downloaded_at) AS last_downloaded_at
FROM wz_rule r
LEFT JOIN regulation_download_logs l ON r.wzruleseq = l.rule_id
GROUP BY r.wzruleseq, r.wzname, r.wzpubno
ORDER BY download_count DESC;

COMMENT ON VIEW v_regulation_download_stats IS '규정별 다운로드 통계 (다운로드수, 순방문자, 마지막 다운로드 시각)';

-- 파일 종류별 통계 뷰
CREATE OR REPLACE VIEW v_download_stats_by_type AS
SELECT
    file_type,
    COUNT(*) AS download_count,
    COUNT(DISTINCT ip_address) AS unique_visitors,
    COUNT(DISTINCT rule_id) AS rule_count
FROM regulation_download_logs
GROUP BY file_type
ORDER BY download_count DESC;

COMMENT ON VIEW v_download_stats_by_type IS '파일 종류별 다운로드 통계';

-- 일별 다운로드 통계 뷰
CREATE OR REPLACE VIEW v_daily_download_stats AS
SELECT
    DATE(downloaded_at) AS download_date,
    COUNT(*) AS download_count,
    COUNT(DISTINCT ip_address) AS unique_visitors,
    COUNT(DISTINCT rule_id) AS rule_count
FROM regulation_download_logs
GROUP BY DATE(downloaded_at)
ORDER BY download_date DESC;

COMMENT ON VIEW v_daily_download_stats IS '일별 다운로드 통계';

-- 완료 메시지
DO $$
BEGIN
    RAISE NOTICE '✅ regulation_download_logs 테이블 생성 완료';
    RAISE NOTICE '✅ 인덱스 6개 생성 완료';
    RAISE NOTICE '✅ v_regulation_download_stats 뷰 생성 완료';
    RAISE NOTICE '✅ v_download_stats_by_type 뷰 생성 완료';
    RAISE NOTICE '✅ v_daily_download_stats 뷰 생성 완료';
    RAISE NOTICE '';
    RAISE NOTICE '📊 테스트 쿼리:';
    RAISE NOTICE '   SELECT * FROM regulation_download_logs ORDER BY downloaded_at DESC LIMIT 10;';
    RAISE NOTICE '   SELECT * FROM v_regulation_download_stats LIMIT 10;';
    RAISE NOTICE '   SELECT * FROM v_download_stats_by_type;';
    RAISE NOTICE '   SELECT * FROM v_daily_download_stats LIMIT 7;';
END $$;
