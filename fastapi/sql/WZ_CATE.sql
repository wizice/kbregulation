--분류 테이블 (WZ_CATE)
CREATE TABLE WZ_CATE (
    wzCateSeq INTEGER PRIMARY KEY,
    wzCateName CHAR(40) NOT NULL,
    wzParentSeq INTEGER,
    wzOrder INTEGER,
    wzVisible CHAR(1) DEFAULT 'Y',
    wzCreatedBy TEXT NOT NULL,
    wzModifiedBy TEXT NOT NULL
);
