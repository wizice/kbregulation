-- 부서 테이블 (WZ_DEPT)
CREATE TABLE WZ_DEPT (
    wzDeptOrgCd TEXT PRIMARY KEY,
    wzDeptName TEXT NOT NULL,
    wzDeptTelNo TEXT,
    wzMgrNm TEXT,
    wzMgrTelNo TEXT,
    wzCreatedBy TEXT NOT NULL,
    wzModifiedBy TEXT NOT NULL
);
