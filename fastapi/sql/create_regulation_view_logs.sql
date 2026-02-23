-- =====================================================
-- 내규 조회 통계 테이블
-- =====================================================
-- 목적: 각 내규별 조회 횟수 집계 (순수 유입량 측정)
-- 개인정보: 저장 안함 (IP, User-Agent, 사용자 정보 제외)
-- 생성일: 2025-01-14
-- =====================================================

-- 기존 테이블이 있으면 삭제 (개발용)
-- 운영 환경에서는 주석 처리할 것
-- DROP TABLE IF EXISTS regulation_view_logs CASCADE;

-- 테이블 생성
CREATE TABLE IF NOT EXISTS regulation_view_logs (
    log_id BIGSERIAL PRIMARY KEY,
    rule_id INTEGER NOT NULL,
    rule_name VARCHAR(500),
    rule_pubno VARCHAR(100),
    viewed_at TIMESTAMPTZ DEFAULT NOW(),

    -- 외래키 제약 (규정 삭제 시 로그도 삭제)
    CONSTRAINT fk_regulation_view_logs_rule
        FOREIGN KEY (rule_id)
        REFERENCES wz_rule(wzruleseq)
        ON DELETE CASCADE
);

-- 인덱스 생성 (통계 쿼리 성능 최적화)
CREATE INDEX IF NOT EXISTS idx_regulation_view_logs_rule_viewed
    ON regulation_view_logs(rule_id, viewed_at DESC);

CREATE INDEX IF NOT EXISTS idx_regulation_view_logs_viewed
    ON regulation_view_logs(viewed_at DESC);

CREATE INDEX IF NOT EXISTS idx_regulation_view_logs_pubno
    ON regulation_view_logs(rule_pubno);

-- 테이블 및 컬럼 설명
COMMENT ON TABLE regulation_view_logs IS '내규 조회 통계 로그 (개인정보 미포함, 순수 유입량 측정용)';
COMMENT ON COLUMN regulation_view_logs.log_id IS '로그 고유 ID (자동 증가)';
COMMENT ON COLUMN regulation_view_logs.rule_id IS '내규 ID (wz_rule.wzruleseq 참조)';
COMMENT ON COLUMN regulation_view_logs.rule_name IS '내규 명칭 (통계 조회 편의용 비정규화)';
COMMENT ON COLUMN regulation_view_logs.rule_pubno IS '공포번호 (예: 1.1.1, 통계 편의용)';
COMMENT ON COLUMN regulation_view_logs.viewed_at IS '조회 시각 (자동 기록)';

-- 테이블 권한 설정 (필요 시)
-- GRANT SELECT, INSERT ON regulation_view_logs TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE regulation_view_logs_log_id_seq TO your_app_user;

-- 테스트용 샘플 데이터 (선택)
-- INSERT INTO regulation_view_logs (rule_id, rule_name, rule_pubno)
-- VALUES (8902, '1.1.1. 정확한 환자 확인', '1.1.1');

-- 조회수 집계 뷰 (선택)
CREATE OR REPLACE VIEW v_regulation_view_stats AS
SELECT
    r.wzruleseq AS rule_id,
    r.wzname AS rule_name,
    r.wzpubno AS rule_pubno,
    COUNT(l.log_id) AS view_count,
    MAX(l.viewed_at) AS last_viewed_at
FROM wz_rule r
LEFT JOIN regulation_view_logs l ON r.wzruleseq = l.rule_id
GROUP BY r.wzruleseq, r.wzname, r.wzpubno
ORDER BY view_count DESC;

COMMENT ON VIEW v_regulation_view_stats IS '내규별 조회 통계 (조회수, 마지막 조회 시각)';

-- 완료 메시지
DO $$
BEGIN
    RAISE NOTICE '✅ regulation_view_logs 테이블 생성 완료';
    RAISE NOTICE '✅ 인덱스 3개 생성 완료';
    RAISE NOTICE '✅ v_regulation_view_stats 뷰 생성 완료';
    RAISE NOTICE '';
    RAISE NOTICE '📊 테스트 쿼리:';
    RAISE NOTICE '   SELECT * FROM regulation_view_logs LIMIT 5;';
    RAISE NOTICE '   SELECT * FROM v_regulation_view_stats LIMIT 10;';
END $$;
