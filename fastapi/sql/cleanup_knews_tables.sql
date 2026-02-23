-- knews 관련 테이블 삭제 스크립트
-- 실행 전 백업을 권장합니다

-- knews 관련 테이블 확인
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'severance'
-- AND table_name LIKE '%knews%';

-- knews 관련 테이블 삭제
DROP TABLE IF EXISTS knews CASCADE;
DROP TABLE IF EXISTS knews_sends CASCADE;
DROP TABLE IF EXISTS knews_galogs CASCADE;
DROP TABLE IF EXISTS s_knews CASCADE;
DROP TABLE IF EXISTS s_knews_id CASCADE;
DROP TABLE IF EXISTS knews_backup CASCADE;

-- bigkinds, festival, webtoon 관련 테이블 (뉴스레터 관련)
DROP TABLE IF EXISTS bigkinds CASCADE;
DROP TABLE IF EXISTS festival CASCADE;
DROP TABLE IF EXISTS webtoon CASCADE;
DROP TABLE IF EXISTS top10knews CASCADE;

-- cloudflare/upload 관련 테이블 (뉴스레터 파일 업로드 관련)
DROP TABLE IF EXISTS cloudflare_uploads CASCADE;
DROP TABLE IF EXISTS mail_attachments CASCADE;

-- 시퀀스 삭제
DROP SEQUENCE IF EXISTS knews_seq;
DROP SEQUENCE IF EXISTS knews_sends_seq;

-- 인덱스 정리 (남아있을 수 있는 인덱스)
DROP INDEX IF EXISTS idx_knews_date;
DROP INDEX IF EXISTS idx_knews_sends_status;

-- 완료 메시지
SELECT 'knews 관련 테이블 정리 완료' as result;