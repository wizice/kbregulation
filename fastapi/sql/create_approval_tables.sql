-- 다단계 결재 시스템 테이블
-- 생성일: 2025-12-26

-- =============================================
-- 1. 결재 워크플로우 테이블 (규정별 결재 진행 상태)
-- =============================================
CREATE TABLE IF NOT EXISTS wz_approval_workflow (
    workflow_id SERIAL PRIMARY KEY,
    rule_seq INTEGER NOT NULL,                    -- WZ_RULE.wzRuleSeq 참조
    rule_name VARCHAR(500),                       -- 규정명 (편의용)
    rule_pubno VARCHAR(50),                       -- 공포번호

    -- 워크플로우 정보
    total_steps INTEGER NOT NULL DEFAULT 2,       -- 총 결재 단계 (2 또는 3)
    current_step INTEGER NOT NULL DEFAULT 0,      -- 현재 결재 단계 (0: 기안, 1: 1차, 2: 2차, 3: 3차)
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT', -- DRAFT, PENDING, IN_PROGRESS, APPROVED, REJECTED, PUBLISHED

    -- 기안 정보
    drafter_id VARCHAR(50) NOT NULL,              -- 기안자 ID
    drafter_name VARCHAR(100),                    -- 기안자명
    drafter_dept VARCHAR(200),                    -- 기안자 부서
    draft_comment TEXT,                           -- 기안 의견
    drafted_at TIMESTAMP DEFAULT NOW(),           -- 기안 일시

    -- 완료 정보
    completed_at TIMESTAMP,                       -- 최종 완료 일시
    published_at TIMESTAMP,                       -- 발행 일시

    -- 메타 정보
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_workflow_rule_seq ON wz_approval_workflow(rule_seq);
CREATE INDEX IF NOT EXISTS idx_workflow_status ON wz_approval_workflow(status);
CREATE INDEX IF NOT EXISTS idx_workflow_drafter ON wz_approval_workflow(drafter_id);
CREATE INDEX IF NOT EXISTS idx_workflow_created ON wz_approval_workflow(created_at DESC);

-- =============================================
-- 2. 결재 단계 테이블 (각 단계별 결재자 정보)
-- =============================================
CREATE TABLE IF NOT EXISTS wz_approval_step (
    step_id SERIAL PRIMARY KEY,
    workflow_id INTEGER NOT NULL REFERENCES wz_approval_workflow(workflow_id) ON DELETE CASCADE,

    -- 단계 정보
    step_order INTEGER NOT NULL,                  -- 결재 순서 (1: 1차, 2: 2차, 3: 3차)
    step_name VARCHAR(50),                        -- 단계명 (1차 결재, 2차 결재, 최종 결재)

    -- 결재자 정보
    approver_id VARCHAR(50) NOT NULL,             -- 결재자 ID
    approver_name VARCHAR(100),                   -- 결재자명
    approver_dept VARCHAR(200),                   -- 결재자 부서
    approver_position VARCHAR(100),               -- 결재자 직위

    -- 결재 결과
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED
    comment TEXT,                                 -- 결재 의견
    acted_at TIMESTAMP,                           -- 결재/반려 일시

    -- 메타 정보
    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_step_workflow ON wz_approval_step(workflow_id);
CREATE INDEX IF NOT EXISTS idx_step_approver ON wz_approval_step(approver_id);
CREATE INDEX IF NOT EXISTS idx_step_status ON wz_approval_step(status);

-- 유니크 제약조건 (한 워크플로우에 같은 순서의 단계는 하나만)
CREATE UNIQUE INDEX IF NOT EXISTS idx_step_unique ON wz_approval_step(workflow_id, step_order);

-- =============================================
-- 3. 결재 이력 테이블 (모든 결재 활동 기록)
-- =============================================
CREATE TABLE IF NOT EXISTS wz_approval_history (
    history_id SERIAL PRIMARY KEY,
    workflow_id INTEGER NOT NULL REFERENCES wz_approval_workflow(workflow_id) ON DELETE CASCADE,
    step_id INTEGER REFERENCES wz_approval_step(step_id),

    -- 이력 정보
    action VARCHAR(20) NOT NULL,                  -- DRAFT, SUBMIT, APPROVE, REJECT, CANCEL, PUBLISH
    actor_id VARCHAR(50) NOT NULL,                -- 수행자 ID
    actor_name VARCHAR(100),                      -- 수행자명
    actor_dept VARCHAR(200),                      -- 수행자 부서

    -- 상세 정보
    from_status VARCHAR(20),                      -- 이전 상태
    to_status VARCHAR(20),                        -- 변경된 상태
    comment TEXT,                                 -- 의견

    -- 메타 정보
    created_at TIMESTAMP DEFAULT NOW(),
    ip_address VARCHAR(45),                       -- IP 주소
    user_agent TEXT                               -- 브라우저 정보
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_history_workflow ON wz_approval_history(workflow_id);
CREATE INDEX IF NOT EXISTS idx_history_actor ON wz_approval_history(actor_id);
CREATE INDEX IF NOT EXISTS idx_history_action ON wz_approval_history(action);
CREATE INDEX IF NOT EXISTS idx_history_created ON wz_approval_history(created_at DESC);

-- =============================================
-- 4. 뷰: 대기 중인 결재 목록
-- =============================================
CREATE OR REPLACE VIEW v_pending_approvals AS
SELECT
    w.workflow_id,
    w.rule_seq,
    w.rule_name,
    w.rule_pubno,
    w.total_steps,
    w.current_step,
    w.status AS workflow_status,
    w.drafter_id,
    w.drafter_name,
    w.drafter_dept,
    w.drafted_at,
    s.step_id,
    s.step_order,
    s.step_name,
    s.approver_id,
    s.approver_name,
    s.approver_dept,
    s.status AS step_status
FROM wz_approval_workflow w
JOIN wz_approval_step s ON w.workflow_id = s.workflow_id
WHERE w.status IN ('PENDING', 'IN_PROGRESS')
  AND s.status = 'PENDING'
  AND s.step_order = w.current_step + 1
ORDER BY w.drafted_at DESC;

-- =============================================
-- 5. 뷰: 결재 진행 현황
-- =============================================
CREATE OR REPLACE VIEW v_approval_status AS
SELECT
    w.workflow_id,
    w.rule_seq,
    w.rule_name,
    w.rule_pubno,
    w.total_steps,
    w.current_step,
    w.status,
    w.drafter_id,
    w.drafter_name,
    w.drafted_at,
    w.completed_at,
    w.published_at,
    (
        SELECT json_agg(
            json_build_object(
                'step_order', s.step_order,
                'step_name', s.step_name,
                'approver_name', s.approver_name,
                'approver_dept', s.approver_dept,
                'status', s.status,
                'comment', s.comment,
                'acted_at', s.acted_at
            ) ORDER BY s.step_order
        )
        FROM wz_approval_step s
        WHERE s.workflow_id = w.workflow_id
    ) AS steps
FROM wz_approval_workflow w
ORDER BY w.created_at DESC;

-- 코멘트
COMMENT ON TABLE wz_approval_workflow IS '규정 결재 워크플로우';
COMMENT ON TABLE wz_approval_step IS '결재 단계별 결재자 정보';
COMMENT ON TABLE wz_approval_history IS '결재 활동 이력';
COMMENT ON VIEW v_pending_approvals IS '대기 중인 결재 목록';
COMMENT ON VIEW v_approval_status IS '결재 진행 현황';
