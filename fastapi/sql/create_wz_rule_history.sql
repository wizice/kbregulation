-- wz_rule_history: 규정 개정 이력 추적 테이블
-- Phase 3: EDITOR_SPEC 2.4 스키마

CREATE TABLE IF NOT EXISTS wz_rule_history (
    wzhistoryseq         SERIAL PRIMARY KEY,
    wzruleseq            INTEGER,
    wzruleid             INTEGER,
    wzpubno              TEXT,
    wzname               TEXT,
    wzversion            INTEGER,
    wzactiontype         TEXT,
    wzrevisiondate       TEXT,
    wzmodificationdate   TEXT,
    wzfiledocx           TEXT,
    wzfilepdf            TEXT,
    wzfilecomparison     TEXT,
    wzfilecomparisondocx TEXT,
    wznote               TEXT,
    wzchangedby          TEXT,
    wzchangeddate        TIMESTAMP DEFAULT NOW(),
    wzorigdocxname       TEXT,
    wzorigpdfname        TEXT
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_wz_rule_history_ruleseq ON wz_rule_history(wzruleseq);
CREATE INDEX IF NOT EXISTS idx_wz_rule_history_ruleid ON wz_rule_history(wzruleid);
CREATE INDEX IF NOT EXISTS idx_wz_rule_history_actiontype ON wz_rule_history(wzactiontype);

COMMENT ON TABLE wz_rule_history IS '규정 개정 이력 추적 테이블';
COMMENT ON COLUMN wz_rule_history.wzhistoryseq IS '이력 시퀀스 (PK)';
COMMENT ON COLUMN wz_rule_history.wzruleseq IS '규정 시퀀스 (wz_rule FK)';
COMMENT ON COLUMN wz_rule_history.wzruleid IS '규정 ID';
COMMENT ON COLUMN wz_rule_history.wzpubno IS '분류번호';
COMMENT ON COLUMN wz_rule_history.wzname IS '규정명';
COMMENT ON COLUMN wz_rule_history.wzversion IS '버전';
COMMENT ON COLUMN wz_rule_history.wzactiontype IS '액션 유형 (제정/개정/폐지)';
COMMENT ON COLUMN wz_rule_history.wzrevisiondate IS '개정일';
COMMENT ON COLUMN wz_rule_history.wzmodificationdate IS '수정일';
COMMENT ON COLUMN wz_rule_history.wzfiledocx IS 'DOCX 파일 경로';
COMMENT ON COLUMN wz_rule_history.wzfilepdf IS 'PDF 파일 경로';
COMMENT ON COLUMN wz_rule_history.wzfilecomparison IS '신구대비표 경로';
COMMENT ON COLUMN wz_rule_history.wzfilecomparisondocx IS '신구대비표 DOCX 경로';
COMMENT ON COLUMN wz_rule_history.wznote IS '비고';
COMMENT ON COLUMN wz_rule_history.wzchangedby IS '변경자';
COMMENT ON COLUMN wz_rule_history.wzchangeddate IS '변경 일시';
COMMENT ON COLUMN wz_rule_history.wzorigdocxname IS '원본 DOCX 파일명';
COMMENT ON COLUMN wz_rule_history.wzorigpdfname IS '원본 PDF 파일명';
