-- wz_rule 테이블에 JSON 파일 경로를 저장하는 컬럼 추가
-- 실행: psql -U severance -h localhost -p 35432 -d severance -f add_wzfilejson_column.sql

-- wzFileJson 컬럼이 없으면 추가
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'wz_rule'
        AND column_name = 'wzfilejson'
    ) THEN
        ALTER TABLE wz_rule ADD COLUMN wzFileJson TEXT;
        COMMENT ON COLUMN wz_rule.wzFileJson IS 'JSON 파일 경로 (파싱된 규정 내용)';

        -- 인덱스 추가 (선택사항)
        CREATE INDEX idx_wz_rule_filejson ON wz_rule(wzFileJson);

        RAISE NOTICE 'wzFileJson column added successfully';
    ELSE
        RAISE NOTICE 'wzFileJson column already exists';
    END IF;
END $$;

-- 컬럼 확인
SELECT
    column_name,
    data_type,
    is_nullable
FROM
    information_schema.columns
WHERE
    table_name = 'wz_rule'
    AND column_name = 'wzfilejson';