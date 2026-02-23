-- 알림 테이블
-- 생성일: 2025-12-26

CREATE TABLE IF NOT EXISTS wz_notifications (
    notification_id SERIAL PRIMARY KEY,

    -- 수신자 정보
    recipient_id VARCHAR(50) NOT NULL,            -- 수신자 ID
    recipient_name VARCHAR(100),                  -- 수신자명

    -- 알림 내용
    type VARCHAR(30) NOT NULL,                    -- APPROVAL_REQUEST, APPROVED, REJECTED, PUBLISHED
    title VARCHAR(200) NOT NULL,                  -- 알림 제목
    message TEXT,                                 -- 알림 내용

    -- 관련 정보
    workflow_id INTEGER,                          -- 관련 결재 워크플로우 ID
    rule_seq INTEGER,                             -- 관련 규정 ID
    rule_name VARCHAR(500),                       -- 규정명

    -- 발신자 정보
    sender_id VARCHAR(50),                        -- 발신자 ID
    sender_name VARCHAR(100),                     -- 발신자명

    -- 상태
    is_read BOOLEAN DEFAULT FALSE,                -- 읽음 여부
    read_at TIMESTAMP,                            -- 읽은 시간

    -- 메타 정보
    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_notif_recipient ON wz_notifications(recipient_id);
CREATE INDEX IF NOT EXISTS idx_notif_unread ON wz_notifications(recipient_id, is_read) WHERE is_read = FALSE;
CREATE INDEX IF NOT EXISTS idx_notif_type ON wz_notifications(type);
CREATE INDEX IF NOT EXISTS idx_notif_created ON wz_notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notif_workflow ON wz_notifications(workflow_id);

COMMENT ON TABLE wz_notifications IS '사용자 알림';
