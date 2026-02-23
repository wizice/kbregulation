--부록 테이블 (WZ_APPENDIX)
CREATE TABLE WZ_APPENDIX (
    wzAppendixSeq SERIAL PRIMARY KEY,
    wzRuleSeq INTEGER,
    wzAppendixNo TEXT,
    wzAppendixName TEXT,
    wzFileType TEXT,
    wzCreatedBy TEXT NOT NULL,
    wzModifiedBy TEXT NOT NULL
);
