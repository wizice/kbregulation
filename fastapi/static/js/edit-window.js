// edit-window.js - 편집 창 HTML 생성

const EditWindow = {
    // 날짜 형식 변환 함수들
    formatDateForDisplay(dateString) {
        if (!dateString) return '';
        
        // YYYY-MM-DD 형식을 YYYY.MM.DD. 형식으로 변환
        if (dateString.includes('-')) {
            const parts = dateString.split('-');
            if (parts.length === 3) {
                return `${parts[0]}.${parts[1]}.${parts[2]}.`;
            }
        }
        
        // 이미 YYYY.MM.DD. 형식이면 그대로 반환
        if (dateString.includes('.')) {
            return dateString.endsWith('.') ? dateString : dateString + '.';
        }
        
        return dateString;
    },
    
    formatDateForStorage(dateString) {
        if (!dateString) return '';
        
        // YYYY.MM.DD. 형식을 YYYY-MM-DD 형식으로 변환
        const cleaned = dateString.replace(/\./g, '-').replace(/-$/, '');
        
        // 유효한 날짜 형식인지 확인
        if (/^\d{4}-\d{2}-\d{2}$/.test(cleaned)) {
            return cleaned;
        }
        
        return '';
    },

    // 편집 창 HTML 생성
    generateHTML(regulation, isNew = false, isRevision = false) {
        // 데이터를 문자열로 변환하여 전달
        const regulationJson = JSON.stringify(regulation);
        const articlesHtml = this.generateArticlesHTML(regulation.content.articles || []);
        const historyHtml = this.generateHistoryHTML(regulation.content.history || []);
        
        // 날짜 형식 변환
        const revisionDateDisplay = this.formatDateForDisplay(regulation.revisionDate);
        const reviewDateDisplay = this.formatDateForDisplay(regulation.reviewDate);
        const announceDateDisplay = this.formatDateForDisplay(regulation.announceDate);
        const effectiveDateDisplay = this.formatDateForDisplay(regulation.effectiveDate);
        
        return `
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>편집 - ${regulation.title}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'KB금융체Text', sans-serif; background: #f5f5f5; }
        
        .edit-container {
            display: flex;
            height: 100vh;
        }
        
        .sidebar {
            width: 250px;
            background: white;
            border-right: 1px solid #ddd;
            overflow-y: auto;
        }
        
        .sidebar-header {
            padding: 20px;
            background: linear-gradient(135deg, #FFBC00 0%, #60584C 100%);
            color: white;
        }
        
        .sidebar-item {
            padding: 15px 20px;
            cursor: pointer;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.3s;
        }
        
        .sidebar-item:hover {
            background: #f8f9fa;
        }
        
        .sidebar-item.active {
            background: #e7f1ff;
            color: #60584C;
            border-left: 3px solid #FFBC00;
        }
        
        .main-content {
            flex: 1;
            overflow-y: auto;
            padding: 30px;
            padding-bottom: 100px;
        }
        
        .content-header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .section {
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: none;
        }
        
        .section.active {
            display: block;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group-inline {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .form-group-inline > .form-group {
            flex: 1;
            margin-bottom: 0;
        }
        
        .form-label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #495057;
            font-size: 14px;
        }
        
        .form-input, .form-textarea, .form-select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .form-input-small {
            width: 150px;
        }
        
        .form-textarea {
            min-height: 100px;
            resize: vertical;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: #FFBC00;
            color: white;
        }
        
        .btn-success {
            background: #28a745;
            color: white;
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        
        .btn-small {
            padding: 5px 10px;
            font-size: 12px;
        }
        
        .action-bar {
            position: fixed;
            bottom: 0;
            left: 250px;
            right: 0;
            background: white;
            padding: 15px 30px;
            border-top: 1px solid #ddd;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .status-indicator {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
        }
        
        .status-new { background: #d4edda; color: #155724; }
        .status-revision { background: #fff3cd; color: #856404; }
        .status-saved { background: #d1ecf1; color: #0c5460; }
        
        .article-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .article-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        
        .article-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .upload-area {
            border: 2px dashed #ddd;
            padding: 40px;
            text-align: center;
            border-radius: 8px;
            margin: 20px 0;
            transition: all 0.3s;
        }
        
        .upload-area:hover {
            border-color: #60584C;
            background: #f8f9fa;
        }
        
        .extract-result {
            display: none;
            background: #e7f1ff;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }
        
        .json-viewer {
            background: white;
            padding: 10px;
            border-radius: 4px;
            max-height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
        }
        
        .appendix-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 30px;
        }
        
        .appendix-preview {
            background: white;
            padding: 15px;
            border-radius: 4px;
            margin-top: 10px;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .supplement-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .info-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        
        .info-table td {
            padding: 8px;
            border-bottom: 1px solid #e9ecef;
        }
        
        .info-table td:first-child {
            width: 120px;
            font-weight: 500;
            color: #6c757d;
        }
        
        .date-input {
            font-family: monospace;
            letter-spacing: 0.5px;
        }
        
        .date-input::placeholder {
            color: #adb5bd;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="edit-container">
        <div class="sidebar">
            <div class="sidebar-header">
                <h3 style="font-size: 16px; margin-bottom: 5px;">${regulation.title}</h3>
                <div style="font-size: 12px; opacity: 0.9;">
                    ${isNew ? '신규 등록' : isRevision ? '개정 작업' : '편집 모드'}
                </div>
            </div>
            <div class="sidebar-item active" data-section="basic">
                <span>📋</span> 기본정보
            </div>
            <div class="sidebar-item" data-section="articles">
                <span>📖</span> 조문 및 부칙
            </div>
            <div class="sidebar-item" data-section="images">
                <span>🖼️</span> 이미지 관리
            </div>
            <div class="sidebar-item" data-section="supplements">
                <span>📎</span> 부록
            </div>
            <div class="sidebar-item" data-section="history">
                <span>🕒</span> 연혁
            </div>
            <div class="sidebar-item" data-section="preview">
                <span>👁️</span> 미리보기
            </div>
        </div>
        
        <div class="main-content">
            <div class="content-header">
                <h2>${regulation.title}</h2>
                <p style="color: #6c757d; margin-top: 10px;">
                    부서: ${regulation.department} | 버전: ${regulation.version} | 
                    상태: <span class="status-indicator ${isNew ? 'status-new' : isRevision ? 'status-revision' : 'status-saved'}">
                        ${isNew ? '신규 등록' : isRevision ? '개정 작업중' : '저장됨'}
                    </span>
                </p>
            </div>
            
            <!-- 기본정보 섹션 -->
            <div class="section active" id="basicSection">
                <h3 style="margin-bottom: 20px;">기본정보</h3>
                
                <!-- 분류번호와 제목 -->
                <div class="form-group-inline">
                    <div class="form-group" style="flex: 0 0 250px;">
                        <label class="form-label">분류번호</label>
                        <input type="text" class="form-input" id="classificationDisplay" 
                               value="${regulation.classification || '미분류'}" readonly 
                               style="background: #f8f9fa; font-weight: 500;">
                    </div>
                    <div class="form-group">
                        <label class="form-label">제목</label>
                        <input type="text" class="form-input" id="titleInput" value="${regulation.title}">
                    </div>
                </div>
                
                <!-- 날짜 정보 테이블 -->
                <table class="info-table">
                    <tr>
                        <td>제정일</td>
                        <td>${regulation.enactmentDate || '2006.07.'}</td>
                        <td>최종개정일</td>
                        <td>
                            <input type="text" class="form-input form-input-small date-input" id="revisionDateInput" 
                                   value="${revisionDateDisplay}" 
                                   placeholder="YYYY.MM.DD." style="width: 150px;">
                        </td>
                        <td>최종검토일</td>
                        <td>
                            <input type="text" class="form-input form-input-small date-input" id="reviewDateInput" 
                                   value="${reviewDateDisplay}" 
                                   placeholder="YYYY.MM.DD." style="width: 150px;">
                        </td>
                    </tr>
                </table>
                
                <!-- 부서 정보 -->
                <div class="form-group-inline" style="margin-top: 20px;">
                    <div class="form-group">
                        <label class="form-label">소관부서</label>
                        <input type="text" class="form-input" id="departmentInput"
                               value="${regulation.department}" placeholder="예: 경영전략부">
                    </div>
                </div>
                
                <!-- 관련기준 -->
                <div class="form-group">
                    <label class="form-label">관련기준</label>
                    <textarea class="form-textarea" id="relatedStandardsInput" rows="4">${regulation.relatedStandards || ''}</textarea>
                    <small style="color: #6c757d;">예: 4주기 정신의료기관평가기준, JCI Standard 등</small>
                </div>
                
                <!-- 부록 정보 -->
                <div class="form-group">
                    <label class="form-label">부록</label>
                    <input type="text" class="form-input" id="appendixCountInput" 
                           value="${regulation.appendixCount || '4건'}" readonly style="background: #f8f9fa;">
                </div>
                
                <!-- 공포/시행일 -->
                <div class="form-group-inline">
                    <div class="form-group">
                        <label class="form-label">공포일자</label>
                        <input type="text" class="form-input date-input" id="announceDateInput" 
                               value="${announceDateDisplay}"
                               placeholder="YYYY.MM.DD.">
                    </div>
                    <div class="form-group">
                        <label class="form-label">시행일자</label>
                        <input type="text" class="form-input date-input" id="effectiveDateInput" 
                               value="${effectiveDateDisplay}"
                               placeholder="YYYY.MM.DD.">
                    </div>
                </div>
            </div>
            
            <!-- 조문 및 부칙 섹션 -->
            <div class="section" id="articlesSection">
                <h3 style="margin-bottom: 20px;">조문 관리</h3>
                
                <!-- 조문 파일 업로드 -->
                <div class="upload-area" style="border-color: #dc3545;">
                    <h4 style="color: #dc3545;">필수 업로드 파일</h4>
                    <div style="display: flex; gap: 20px; justify-content: center; margin-top: 20px;">
                        <div>
                            <input type="file" id="articlesDocx" accept=".docx" style="display: none;">
                            <button class="btn btn-primary" onclick="document.getElementById('articlesDocx').click()">
                                📄 DOCX 파일 선택
                            </button>
                            <p id="docxStatus" style="margin-top: 10px; color: #6c757d; font-size: 12px;">미업로드</p>
                        </div>
                        <div>
                            <input type="file" id="articlesPdf" accept=".pdf" style="display: none;">
                            <button class="btn btn-primary" onclick="document.getElementById('articlesPdf').click()">
                                📄 PDF 파일 선택
                            </button>
                            <p id="pdfStatus" style="margin-top: 10px; color: #6c757d; font-size: 12px;">미업로드</p>
                        </div>
                    </div>
                    <p style="margin-top: 15px; color: #dc3545; font-weight: bold;">
                        ⚠️ DOCX와 PDF 파일 모두 필수로 업로드해야 합니다.
                    </p>
                </div>
                
                <!-- Python 처리 결과 -->
                <div class="extract-result" id="articlesExtractResult">
                    <h4>추출된 조문 (Python 처리 결과)</h4>
                    <div class="json-viewer" id="extractedArticlesJson"></div>
                    <button class="btn btn-success" style="margin-top: 10px;" onclick="window.applyExtractedArticles()">추출 결과 적용</button>
                </div>
                
                <!-- 조문 목록 -->
                <div id="articlesList" style="margin-top: 20px;">
                    ${articlesHtml}
                </div>
                
                <!-- 부칙 섹션 -->
                <div class="appendix-section">
                    <h3>부칙</h3>
                    <div class="form-group">
                        <label class="form-label">부칙 내용</label>
                        <textarea class="form-textarea" id="appendixContent" rows="6">${regulation.content.appendix || ''}</textarea>
                    </div>
                    <div class="appendix-preview">
                        <strong>부칙 미리보기</strong>
                        <p id="appendixPreview">${regulation.content.appendix || '부칙 내용이 없습니다.'}</p>
                    </div>
                </div>
            </div>
            
            <!-- 부록 섹션 -->
            <div class="section" id="supplementsSection">
                <h3 style="margin-bottom: 20px;">부록 관리</h3>

                <div class="upload-area">
                    <input type="file" id="supplementFiles" accept=".docx,.pdf,.xlsx,.jpg,.png" multiple style="display: none;">
                    <button class="btn btn-primary" onclick="document.getElementById('supplementFiles').click()">
                        📎 부록 파일 업로드
                    </button>
                    <p style="margin-top: 10px; color: #6c757d;">부록 파일을 업로드하세요 (다중 선택 가능)</p>
                </div>

                <!-- 기존 부록 파일 목록 -->
                <div id="existingAppendixList" style="margin-top: 30px;">
                    <h4 style="margin-bottom: 15px; color: #495057;">📚 등록된 부록 파일</h4>
                    <div id="appendixFilesList" style="border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; background: #f8f9fa; min-height: 100px;">
                        <div style="text-align: center; color: #6c757d; padding: 20px;">
                            <i class="fas fa-spinner fa-spin"></i> 부록 파일 목록을 불러오는 중...
                        </div>
                    </div>
                </div>

                <div id="supplementsList" style="margin-top: 20px; display: none;">
                    <!-- 부록 목록 (레거시) -->
                    ${this.generateSupplementsHTML(regulation.content.supplements || [])}
                </div>

                <button class="btn btn-primary" onclick="window.previewSupplements()" style="margin-top: 20px; display: none;">
                    👁️ 부록 미리보기
                </button>
            </div>

            <!-- 이미지 관리 섹션 -->
            <div class="section" id="imagesSection">
                <h3 style="margin-bottom: 20px;">이미지 관리</h3>

                <p style="color: #6c757d; margin-bottom: 20px;">
                    조문별로 이미지를 업로드하고 관리할 수 있습니다. 업로드된 이미지는 규정 문서에 자동으로 포함됩니다.
                </p>

                <!-- 조문 선택 -->
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 10px; font-weight: 600;">📖 조문 선택</label>
                    <select id="imageArticleSelector" style="width: 100%; padding: 10px; border: 1px solid #dee2e6; border-radius: 4px; font-size: 14px;">
                        <option value="">조문을 선택하세요...</option>
                    </select>
                </div>

                <!-- 이미지 업로드 영역 -->
                <div id="imageUploadArea" style="display: none;">
                    <div style="border: 2px dashed #dee2e6; border-radius: 8px; padding: 40px; text-align: center; background: #f8f9fa; margin-bottom: 20px;" id="imageDropZone">
                        <div style="font-size: 48px; margin-bottom: 10px;">🖼️</div>
                        <p style="font-size: 16px; font-weight: 600; margin-bottom: 10px;">이미지를 드래그 앤 드롭 하세요</p>
                        <p style="color: #6c757d; margin-bottom: 20px;">또는</p>
                        <input type="file" id="imageFileInput" accept="image/png,image/jpeg,image/jpg,image/gif" multiple style="display: none;">
                        <button class="btn btn-primary" onclick="document.getElementById('imageFileInput').click()" style="padding: 12px 30px; font-size: 14px;">
                            📁 파일 선택
                        </button>
                        <p style="margin-top: 15px; color: #6c757d; font-size: 13px;">
                            지원 형식: PNG, JPG, GIF | 최대 크기: 10MB
                        </p>
                    </div>

                    <!-- 현재 이미지 목록 -->
                    <div id="currentImages">
                        <h4 style="margin-bottom: 15px; font-size: 16px;">현재 등록된 이미지</h4>
                        <div id="imagesList" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px;">
                            <!-- 이미지 목록이 여기에 표시됩니다 -->
                        </div>
                    </div>
                </div>

                <div id="noArticleMessage" style="padding: 40px; text-align: center; color: #6c757d;">
                    <p style="font-size: 16px;">👆 위에서 조문을 선택하면 이미지를 관리할 수 있습니다.</p>
                </div>
            </div>

            <!-- 연혁 섹션 -->
            <div class="section" id="historySection">
                <h3 style="margin-bottom: 20px;">연혁</h3>
                <div id="historyList">
                    ${historyHtml}
                </div>
            </div>
            
            <!-- 미리보기 섹션 -->
            <div class="section" id="previewSection">
                <h3 style="margin-bottom: 20px;">미리보기</h3>
                <div style="padding: 20px; background: #f8f9fa; border-radius: 4px; margin-bottom: 20px;">
                    <h4>${regulation.title}</h4>
                    <p>소관부서: ${regulation.department}</p>
                    <p>시행일자: ${regulation.effectiveDate || '미정'}</p>
                    <button class="btn btn-primary" onclick="window.loadFullContent()">전체 조문 불러오기</button>
                </div>
                <div id="previewContent" style="display: none; padding: 20px; background: white; border: 1px solid #dee2e6; border-radius: 4px; max-height: 600px; overflow-y: auto;">
                    <!-- 전체 조문 내용이 여기에 표시됩니다 -->
                </div>
            </div>
        </div>
        
        <div class="action-bar">
            <div>
                <button class="btn btn-secondary" onclick="window.saveDraft()">임시저장</button>
                <button class="btn btn-success" onclick="window.saveAndContinue()">저장</button>
            </div>
            <div>
                <button class="btn btn-primary" onclick="if(confirm('저장하고 닫으시겠습니까?')) { window.saveAndClose(); }">저장 후 닫기</button>
            </div>
        </div>
    </div>
    
    <script>
        // 전역 변수
        window.currentSection = 'basic';
        window.regulationData = ${regulationJson};
        window.isDirty = false;
        window.extractedData = null; // Flask 서버에서 받은 데이터 저장
        
        // EditWindow의 날짜 형식 변환 함수를 window에 복사
        window.formatDateForDisplay = function(dateString) {
            if (!dateString) return '';
            
            // YYYY-MM-DD 형식을 YYYY.MM.DD. 형식으로 변환
            if (dateString.includes('-')) {
                const parts = dateString.split('-');
                if (parts.length === 3) {
                    return parts[0] + '.' + parts[1] + '.' + parts[2] + '.';
                }
            }
            
            // 이미 YYYY.MM.DD. 형식이면 그대로 반환
            if (dateString.includes('.')) {
                return dateString.endsWith('.') ? dateString : dateString + '.';
            }
            
            return dateString;
        };
        
        // 섹션 전환
        window.switchSection = function(section) {
            document.querySelectorAll('.section').forEach(el => el.classList.remove('active'));
            document.getElementById(section + 'Section').classList.add('active');

            document.querySelectorAll('.sidebar-item').forEach(el => {
                el.classList.remove('active');
                if(el.dataset.section === section) {
                    el.classList.add('active');
                }
            });

            window.currentSection = section;

            // 이미지 관리 섹션으로 전환 시 ImageManager 초기화
            if (section === 'images' && window.ImageManager && window.regulationData) {
                const ruleId = window.regulationData.id;
                if (ruleId) {
                    ImageManager.init(ruleId).catch(err => {
                        console.error('[EditWindow] Failed to initialize ImageManager:', err);
                    });
                }
            }

            // 부록 섹션으로 전환 시 부록 파일 목록 로드
            if (section === 'supplements' && window.regulationData) {
                const ruleId = window.regulationData.id;
                const wzpubno = window.regulationData.wzpubno || window.regulationData.classification || '';
                console.log('[EditWindow] Supplements section activated, loading appendix files...');
                if (ruleId && typeof window.loadAppendixFiles === 'function') {
                    window.loadAppendixFiles(ruleId, wzpubno).catch(err => {
                        console.error('[EditWindow] Failed to load appendix files:', err);
                    });
                } else {
                    console.warn('[EditWindow] Cannot load appendix files - ruleId:', ruleId, 'function available:', typeof window.loadAppendixFiles);
                }
            }

            // 스크롤을 맨 위로 이동
            window.scrollTo(0, 0);
            // 메인 컨텐츠 영역도 맨 위로 이동
            const mainContent = document.querySelector('.main-content');
            if (mainContent) {
                mainContent.scrollTop = 0;
            }
            // 활성화된 섹션도 맨 위로 이동
            const activeSection = document.getElementById(section + 'Section');
            if (activeSection) {
                activeSection.scrollTop = 0;
            }
        };
        
        // 사이드바 클릭 이벤트
        document.querySelectorAll('.sidebar-item').forEach(item => {
            item.addEventListener('click', function() {
                window.switchSection(this.dataset.section);
            });
        });
        
        // 파일 업로드 이벤트
        const articlesDocx = document.getElementById('articlesDocx');
        const articlesPdf = document.getElementById('articlesPdf');
        const supplementFiles = document.getElementById('supplementFiles');
        
        if (articlesDocx) articlesDocx.addEventListener('change', handleArticlesDocxUpload);
        if (articlesPdf) articlesPdf.addEventListener('change', handleArticlesPdfUpload);
        if (supplementFiles) supplementFiles.addEventListener('change', handleSupplementUpload);
        
        // 조문 DOCX 파일 업로드 처리
        async function handleArticlesDocxUpload(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            document.getElementById('docxStatus').textContent = file.name;
            document.getElementById('docxStatus').style.color = '#28a745';
            
            checkArticlesFilesReady();
        }
        
        // 조문 PDF 파일 업로드 처리
        async function handleArticlesPdfUpload(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            document.getElementById('pdfStatus').textContent = file.name;
            document.getElementById('pdfStatus').style.color = '#28a745';
            
            checkArticlesFilesReady();
        }
        
        // 조문 파일 준비 상태 확인
        function checkArticlesFilesReady() {
            const docxFile = document.getElementById('articlesDocx').files[0];
            //const pdfFile = document.getElementById('articlesPdf').files[0];
            
            //if (docxFile && pdfFile) {
            if (docxFile) {
                //processArticlesFiles(docxFile, pdfFile);
                processArticlesFiles(docxFile, null);
            }
        }
        
        // Flask 서버와 연동하여 조문 파일 처리
        async function processArticlesFiles(docxFile, pdfFile) {
            const formData = new FormData();
            formData.append('file', docxFile); // Flask는 'file'이라는 이름으로 받음
            
            try {
                // 로딩 표시
                const resultDiv = document.getElementById('articlesExtractResult');
                const jsonDiv = document.getElementById('extractedArticlesJson');
                resultDiv.style.display = 'block';
                jsonDiv.textContent = '파일을 처리중입니다...';
                
                // Flask 서버로 요청
                const response = await fetch('../../../severance/editor', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(\`HTTP error! status: \${response.status}\`);
                }
                
                const result = await response.json();
                
                if (result.success) {
                    // 조문 데이터 표시
                    jsonDiv.textContent = JSON.stringify({
                        document_info: result.document_info,
                        sections: result.sections
                    }, null, 2);
                    
                    // 조문 목록 업데이트
                    window.extractedData = result; // 전역 변수에 저장
                    
                    // 상태 메시지 업데이트
                    const statusMsg = document.createElement('p');
                    statusMsg.style.color = '#28a745';
                    statusMsg.style.marginTop = '10px';
                    statusMsg.innerHTML = \`✅ 추출 완료: \${result.sections.length}개 조문, \${result.document_info.이미지개수}개 이미지\`;
                    resultDiv.appendChild(statusMsg);
                    
                } else {
                    throw new Error(result.error || '파일 처리 실패');
                }
                
            } catch (error) {
                console.error('파일 처리 중 오류:', error);
                
                const resultDiv = document.getElementById('articlesExtractResult');
                const jsonDiv = document.getElementById('extractedArticlesJson');
                
                resultDiv.style.display = 'block';
                jsonDiv.style.color = '#dc3545';
                jsonDiv.textContent = \`오류 발생: \${error.message}\\n\\nFlask 서버가 실행 중인지 확인하세요.\\n(http://localhost:5002)\`;
                
                // 서버 연결 안내 메시지
                if (error.message.includes('Failed to fetch')) {
                    jsonDiv.textContent += '\\n\\n💡 Flask 서버 실행 방법:\\n' +
                                         'cd /home/wizice/severance/editor\\n' +
                                         'python app.py';
                }
            }
        }
        
        // 부록 파일 업로드 처리
        async function handleSupplementUpload(event) {
            const files = event.target.files;
            if (!files.length) return;
            
            const supplementsList = document.getElementById('supplementsList');
            
            Array.from(files).forEach((file, index) => {
                const existingCount = supplementsList.children.length;
                const supplementDiv = document.createElement('div');
                supplementDiv.className = 'supplement-item';
                supplementDiv.innerHTML = \`
                    <div>
                        <strong>부록 \${existingCount + index + 1}</strong>: \${file.name}
                    </div>
                    <div>
                        <button class="btn btn-secondary btn-small" onclick="this.parentElement.parentElement.remove()">삭제</button>
                        <button class="btn btn-primary btn-small" onclick="window.editSupplement(this)">변경</button>
                    </div>
                \`;
                supplementsList.appendChild(supplementDiv);
            });
            
            window.isDirty = true;
        }
        
        // 추출된 조문 적용 - Flask 서버 응답 형식에 맞게 수정
        window.applyExtractedArticles = function() {
            if (!window.extractedData || !window.extractedData.sections) {
                alert('추출된 데이터가 없습니다.');
                return;
            }
            
            const sections = window.extractedData.sections;
            const articlesList = document.getElementById('articlesList');
            articlesList.innerHTML = '';
            
            sections.forEach(section => {
                // Flask에서 반환하는 형식에 맞게 수정
                const number = section.번호 ? section.번호.replace(/[^0-9]/g, '') : '';
                const title = section.제목 || '';
                const content = section.내용 || '';
                
                const html = window.createArticleHTML(number, title, content);
                articlesList.insertAdjacentHTML('beforeend', html);
            });
            
            // 문서 정보도 업데이트
            if (window.extractedData.document_info) {
                const info = window.extractedData.document_info;
                
                // 제목 업데이트
                if (info.규정명) {
                    document.getElementById('titleInput').value = info.규정명;
                }
                
                // 날짜 정보 업데이트
                if (info.최종개정일) {
                    document.getElementById('revisionDateInput').value = window.formatDateForDisplay(info.최종개정일);
                }
                if (info.최종검토일) {
                    document.getElementById('reviewDateInput').value = window.formatDateForDisplay(info.최종검토일);
                }
                
                // 소관부서 업데이트
                if (info.소관부서 || info.담당부서) {
                    document.getElementById('departmentInput').value = info.소관부서 || info.담당부서;
                }
                
                // 관련기준 업데이트
                if (info.관련기준 && Array.isArray(info.관련기준)) {
                    document.getElementById('relatedStandardsInput').value = info.관련기준.join('\\n');
                }
            }
            
            alert(\`\${sections.length}개의 조문이 적용되었습니다.\`);
            window.isDirty = true;
        };
        
        // 이미지 표시를 위한 추가 함수
        window.displayExtractedImages = function() {
            if (!window.extractedData || !window.extractedData.images) {
                return;
            }
            
            const images = window.extractedData.images;
            if (images.length > 0) {
                console.log(\`추출된 이미지 \${images.length}개:\`, images);
                // 필요시 이미지 미리보기 기능 추가
            }
        };
        
        // 조문 HTML 생성
        window.createArticleHTML = function(number, title, content) {
            return '<div class="article-item" onclick="window.previewArticle(' + number + ')">' +
                '<div class="article-header">' +
                '<strong>제' + number + '조' + (title ? ' (' + title + ')' : '') + '</strong>' +
                '</div>' +
                '<p style="color: #6c757d; margin-top: 5px;">클릭하여 미리보기</p>' +
                '</div>';
        };
        
        // 조문 미리보기
        window.previewArticle = function(articleNumber) {
            alert('제' + articleNumber + '조 미리보기 화면으로 이동합니다.');
            // 실제 구현시 미리보기 창 열기
        };
        
        // 부록 편집
        window.editSupplement = function(button) {
            const supplementDiv = button.closest('.supplement-item');
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.docx,.pdf,.xlsx,.jpg,.png';
            input.onchange = function(e) {
                if (e.target.files[0]) {
                    supplementDiv.querySelector('strong').nextSibling.textContent = ': ' + e.target.files[0].name;
                    window.isDirty = true;
                }
            };
            input.click();
        };
        
        // 부록 미리보기
        window.previewSupplements = function() {
            alert('부록 미리보기 페이지로 이동합니다.');
            // 실제 구현시 미리보기 창 열기
        };
        
        // 전체 조문 불러오기
        window.loadFullContent = async function() {
            const ruleId = window.regulationData.id || window.regulationData.ruleId || '0';
            const previewContent = document.getElementById('previewContent');

            try {
                previewContent.innerHTML = '<p>조문 내용을 불러오는 중...</p>';
                previewContent.style.display = 'block';

                const response = await fetch(\`/api/v1/regulation/content/\${ruleId}\`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include'
                });

                if (response.ok) {
                    const data = await response.json();

                    if (data.success && data.content) {
                        if (data.content.full_text) {
                            previewContent.innerHTML = data.content.full_text;
                        } else if (data.content.error) {
                            previewContent.innerHTML = \`<p style="color: #dc3545;">\${data.content.error}</p>\`;
                        } else {
                            previewContent.innerHTML = '<p>조문 내용이 없습니다.</p>';
                        }
                    } else {
                        previewContent.innerHTML = '<p>조문 내용을 불러올 수 없습니다.</p>';
                    }
                } else {
                    previewContent.innerHTML = '<p style="color: #dc3545;">조문 내용을 불러오는데 실패했습니다.</p>';
                }
            } catch (error) {
                console.error('Error loading content:', error);
                previewContent.innerHTML = '<p style="color: #dc3545;">조문 내용을 불러오는 중 오류가 발생했습니다.</p>';
            }
        };

        // 전체 미리보기 (새 창)
        window.openFullPreview = function() {
            const previewWindow = window.open('', 'preview', 'width=800,height=600');
            previewWindow.document.write(\`
                <html>
                <head>
                    <title>\${window.regulationData.title} - 미리보기</title>
                    <style>
                        body { font-family: sans-serif; padding: 20px; }
                        h1 { color: #60584C; }
                    </style>
                </head>
                <body>
                    <h1>\${window.regulationData.title}</h1>
                    <p>분류: \${window.regulationData.classification || '미분류'}</p>
                    <p>소관부서: \${window.regulationData.department}</p>
                    <p>시행일자: \${window.regulationData.effectiveDate || '미정'}</p>
                    <hr>
                    <h2>조문</h2>
                    <p>조문 내용이 여기에 표시됩니다.</p>
                </body>
                </html>
            \`);
        };
        
        // 부칙 내용 변경 감지
        const appendixContent = document.getElementById('appendixContent');
        if (appendixContent) {
            appendixContent.addEventListener('input', function() {
                document.getElementById('appendixPreview').textContent = this.value || '부칙 내용이 없습니다.';
                window.isDirty = true;
            });
        }
        
        // 임시저장
        window.saveDraft = function() {
            window.collectData();
            localStorage.setItem('draft_' + window.regulationData.id, JSON.stringify(window.regulationData));
            alert('임시저장되었습니다.');
            window.isDirty = false;
        };
        
        // 저장
        window.saveAndContinue = function() {
            window.collectData();
            console.log('저장 데이터:', window.regulationData);
            alert('저장되었습니다.');
            window.isDirty = false;
        };
        
        // 저장 후 닫기
        window.saveAndClose = function() {
            window.saveAndContinue();
            window.close();
        };
        
        // 데이터 수집
        window.collectData = function() {
            // 기본정보
            window.regulationData.title = document.getElementById('titleInput').value.trim();
            window.regulationData.department = document.getElementById('departmentInput').value.trim();
            window.regulationData.classification = document.getElementById('classificationDisplay').value.trim();
            window.regulationData.relatedDepartment = document.getElementById('relatedDepartmentInput').value.trim();
            window.regulationData.relatedStandards = document.getElementById('relatedStandardsInput').value.trim();

            // 날짜 필드들 - YYYY-MM-DD 형식으로 저장
            const revisionDateInput = document.getElementById('revisionDateInput').value.trim();
            const reviewDateInput = document.getElementById('reviewDateInput').value.trim();
            const announceDateInput = document.getElementById('announceDateInput').value.trim();
            const effectiveDateInput = document.getElementById('effectiveDateInput').value.trim();
            
            window.regulationData.revisionDate = window.formatDateForStorage(revisionDateInput);
            window.regulationData.reviewDate = window.formatDateForStorage(reviewDateInput);
            window.regulationData.announceDate = window.formatDateForStorage(announceDateInput);
            window.regulationData.effectiveDate = window.formatDateForStorage(effectiveDateInput);
            
            // 부칙
            const appendixContent = document.getElementById('appendixContent');
            if (appendixContent) {
                window.regulationData.content.appendix = appendixContent.value;
            }
        };
        
        // 페이지 나가기 경고
        window.onbeforeunload = function() {
            if (window.isDirty) {
                return '변경사항이 저장되지 않았습니다. 페이지를 나가시겠습니까?';
            }
        };
        
        // 입력 변경 감지
        document.addEventListener('input', function() {
            window.isDirty = true;
        });
        
        // 날짜 형식 변환 함수를 window 객체에 추가
        window.formatDateForStorage = function(dateString) {
            if (!dateString) return '';
            
            // YYYY.MM.DD. 형식을 YYYY-MM-DD 형식으로 변환
            const cleaned = dateString.replace(/\./g, '-').replace(/-$/, '');
            
            // 유효한 날짜 형식인지 확인
            if (/^\d{4}-\d{2}-\d{2}$/.test(cleaned)) {
                return cleaned;
            }
            
            return '';
        };
        
        // 자동 저장 (5분마다)
        setInterval(() => {
            if (window.isDirty) {
                window.saveDraft();
                console.log('자동 저장 완료');
            }
        }, 300000);
        
        // 날짜 입력 필드 포맷팅
        document.querySelectorAll('.date-input').forEach(input => {
            input.addEventListener('blur', function() {
                const value = this.value.replace(/[^0-9]/g, '');
                if (value.length === 8) {
                    const formatted = value.substring(0, 4) + '.' + 
                                    value.substring(4, 6) + '.' + 
                                    value.substring(6, 8) + '.';
                    this.value = formatted;
                }
            });
            
            input.addEventListener('input', function() {
                // 숫자와 점만 허용
                let value = this.value.replace(/[^0-9.]/g, '');
                
                // 자동으로 점 추가
                if (value.length === 4 && !value.includes('.')) {
                    value = value + '.';
                } else if (value.length === 7 && value.split('.').length === 2) {
                    value = value + '.';
                }
                
                this.value = value;
            });
        });
        
        // 분류번호 표시 (읽기 전용으로 변경)
    </script>
</body>
</html>
        `;
    },

    // 조문 HTML 생성
    generateArticlesHTML(articles) {
        if (!articles || articles.length === 0) {
            return '<p style="color: #6c757d;">업로드된 조문이 없습니다. 파일을 업로드해주세요.</p>';
        }
        
        return articles.map(article => `
            <div class="article-item" onclick="window.previewArticle(${article.number})">
                <div class="article-header">
                    <strong>제${article.number}조 (${article.title})</strong>
                </div>
                <p style="color: #6c757d; margin-top: 5px;">클릭하여 미리보기</p>
            </div>
        `).join('');
    },

    // 부록 HTML 생성
    generateSupplementsHTML(supplements) {
        if (!supplements || supplements.length === 0) {
            return '<p style="color: #6c757d;">업로드된 부록이 없습니다.</p>';
        }
        
        return supplements.map((supp, index) => `
            <div class="supplement-item">
                <div>
                    <strong>부록 ${index + 1}</strong>: ${supp.title || supp.filename || '제목 없음'}
                </div>
                <div>
                    <button class="btn btn-secondary btn-small" onclick="this.parentElement.parentElement.remove()">삭제</button>
                    <button class="btn btn-primary btn-small" onclick="window.editSupplement(this)">변경</button>
                </div>
            </div>
        `).join('');
    },

    // 연혁 HTML 생성
    generateHistoryHTML(history) {
        if (!history || history.length === 0) {
            return '<p style="color: #6c757d;">연혁이 없습니다.</p>';
        }

        return history.map(h => `
            <div style="padding: 10px; background: #f8f9fa; margin-bottom: 10px; border-radius: 4px;">
                <strong>${h.date}</strong> - ${h.type}<br>
                ${h.description}
            </div>
        `).join('');
    }
};

// ==================== 부록 파일 관리 함수 ====================

// 부록 파일 목록 로드
window.loadAppendixFiles = async function(ruleId, wzpubno) {
    console.log('[loadAppendixFiles] Called with ruleId:', ruleId, 'wzpubno:', wzpubno);

    const filesList = document.getElementById('appendixFilesList');

    if (!filesList) {
        console.warn('[loadAppendixFiles] appendixFilesList element not found');
        return;
    }

    console.log('[loadAppendixFiles] Element found, loading files...');

    try {
        // API 호출
        const url = wzpubno
            ? `/api/v1/appendix/list/${ruleId}?wzpubno=${encodeURIComponent(wzpubno)}`
            : `/api/v1/appendix/list/${ruleId}`;

        console.log('[loadAppendixFiles] API URL:', url);

        const response = await fetch(url);

        console.log('[loadAppendixFiles] Response status:', response.status);

        if (!response.ok) {
            throw new Error(`부록 목록 조회 실패: ${response.status}`);
        }

        const data = await response.json();

        console.log('[loadAppendixFiles] Data received:', data);

        // 응답 형식 처리: 배열 또는 {files: []} 형식 모두 지원
        let files = Array.isArray(data) ? data : (data.files || []);
        const totalCount = Array.isArray(data) ? data.length : (data.total_count || files.length);

        // 공개 API 응답 형식 변환 (wzappendixfilename → filename)
        files = files.map(f => {
            // wzfilepath에서 실제 파일명 추출
            let actualFilename = f.filename || f.wzappendixfilename;
            if (!f.filename && f.wzfilepath) {
                const pathParts = f.wzfilepath.split('/');
                actualFilename = pathParts[pathParts.length - 1];
            }

            return {
                filename: actualFilename,
                size: f.size || 0,
                modified: f.modified || f.wzmodifieddate || f.wzcreateddate || new Date().toISOString(),
                path: f.path || f.wzfilepath,
                wzappendixseq: f.wzappendixseq
            };
        });

        // 파일 목록 렌더링
        if (files && files.length > 0) {
            filesList.innerHTML = `
                <div style="margin-bottom: 10px; color: #495057; font-weight: 600;">
                    총 ${totalCount}개의 부록 파일
                </div>
                ${files.map((file, index) => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: white; border: 1px solid #dee2e6; border-radius: 6px; margin-bottom: 8px;">
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <i class="fas fa-file-pdf" style="color: #dc3545; font-size: 20px;"></i>
                                <div>
                                    <div style="font-weight: 600; color: #212529;">${file.filename}</div>
                                    <div style="font-size: 12px; color: #6c757d;">
                                        크기: ${formatFileSize(file.size)} |
                                        수정일: ${new Date(file.modified).toLocaleDateString('ko-KR')}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <button class="btn btn-secondary btn-small" onclick="downloadAppendixFile('${file.path}', '${file.filename}')" title="다운로드">
                                <i class="fas fa-download"></i>
                            </button>
                            <button class="btn btn-primary btn-small" onclick="viewAppendixFile('${file.path}')" title="미리보기">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn btn-danger btn-small" onclick="deleteAppendixFile(${ruleId}, '${file.filename}')" title="삭제">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `).join('')}
            `;
        } else {
            filesList.innerHTML = `
                <div style="text-align: center; color: #6c757d; padding: 30px;">
                    <i class="fas fa-inbox" style="font-size: 48px; margin-bottom: 10px; opacity: 0.5;"></i>
                    <p>등록된 부록 파일이 없습니다.</p>
                    <p style="font-size: 13px;">위의 업로드 버튼을 클릭하여 부록 파일을 추가하세요.</p>
                </div>
            `;
        }

    } catch (error) {
        console.error('부록 파일 목록 로드 실패:', error);
        filesList.innerHTML = `
            <div style="text-align: center; color: #dc3545; padding: 20px;">
                <i class="fas fa-exclamation-triangle" style="font-size: 32px; margin-bottom: 10px;"></i>
                <p>부록 파일 목록을 불러오는데 실패했습니다.</p>
                <p style="font-size: 13px;">${error.message}</p>
                <button class="btn btn-secondary" onclick="loadAppendixFiles(${ruleId}, '${wzpubno}')" style="margin-top: 10px;">
                    <i class="fas fa-redo"></i> 다시 시도
                </button>
            </div>
        `;
    }
}

// 파일 크기 포맷팅
window.formatFileSize = function(bytes) {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// 부록 파일 다운로드
window.downloadAppendixFile = function(filePath, filename) {
    const downloadUrl = `/${filePath}`;
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// 부록 파일 미리보기
window.viewAppendixFile = function(filePath) {
    const viewUrl = `/${filePath}`;
    window.open(viewUrl, '_blank', 'width=1000,height=800,scrollbars=yes,resizable=yes');
}

// 부록 파일 삭제
window.deleteAppendixFile = async function(ruleId, filename) {
    if (!confirm(`"${filename}" 파일을 삭제하시겠습니까?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/v1/appendix/delete/${ruleId}/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('삭제 실패');
        }

        const data = await response.json();
        alert(data.message || '부록 파일이 삭제되었습니다.');

        // 목록 새로고침
        const wzpubno = window.regulationData?.wzpubno || '';
        loadAppendixFiles(ruleId, wzpubno);

    } catch (error) {
        console.error('부록 파일 삭제 실패:', error);
        alert('부록 파일 삭제 중 오류가 발생했습니다.');
    }
}

// 부록 파일 선택 처리
window.handleAppendixFileSelection = function(input) {
    const files = input.files;
    const statusEl = document.getElementById('appendixUploadStatus');
    const uploadBtn = document.getElementById('uploadAppendixBtn');

    if (files && files.length > 0) {
        const fileNames = Array.from(files).map(f => f.name).join(', ');
        statusEl.textContent = `${files.length}개 파일 선택됨: ${fileNames}`;
        statusEl.style.color = '#28a745';
        uploadBtn.style.display = 'inline-block';
    } else {
        statusEl.textContent = '';
        uploadBtn.style.display = 'none';
    }
}

// 전체 화면 업로드 오버레이 (공통)
function showUploadOverlay(title) {
    hideUploadOverlay();
    const overlay = document.createElement('div');
    overlay.id = 'uploadOverlay';
    overlay.innerHTML = `
        <style>
            #uploadOverlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.7);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 99999;
            }
            .upload-modal {
                background: white;
                padding: 40px 50px;
                border-radius: 16px;
                text-align: center;
                min-width: 400px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            .upload-spinner-large {
                width: 60px;
                height: 60px;
                border: 5px solid #e0e0e0;
                border-top-color: #60584C;
                border-radius: 50%;
                animation: spinOverlay 1s linear infinite;
                margin: 0 auto 24px;
            }
            @keyframes spinOverlay {
                to { transform: rotate(360deg); }
            }
            .upload-title {
                font-size: 20px;
                font-weight: 700;
                color: #333;
                margin-bottom: 8px;
            }
            .upload-subtitle {
                font-size: 14px;
                color: #666;
                margin-bottom: 24px;
            }
            .upload-progress-wrap {
                background: #e0e0e0;
                border-radius: 10px;
                height: 16px;
                overflow: hidden;
                margin-bottom: 12px;
            }
            .upload-progress-bar {
                height: 100%;
                background: linear-gradient(90deg, #FFBC00, #60584C);
                border-radius: 10px;
                transition: width 0.3s ease;
                width: 0%;
            }
            .upload-percent {
                font-size: 28px;
                font-weight: 700;
                color: #60584C;
            }
        </style>
        <div class="upload-modal">
            <div class="upload-spinner-large"></div>
            <div class="upload-title" id="uploadOverlayTitle">${title}</div>
            <div class="upload-subtitle">잠시만 기다려주세요...</div>
            <div class="upload-progress-wrap">
                <div class="upload-progress-bar" id="uploadOverlayBar"></div>
            </div>
            <div class="upload-percent"><span id="uploadOverlayPercent">0</span>%</div>
        </div>
    `;
    document.body.appendChild(overlay);
}

function updateUploadOverlay(percent) {
    const bar = document.getElementById('uploadOverlayBar');
    const pct = document.getElementById('uploadOverlayPercent');
    if (bar) bar.style.width = percent + '%';
    if (pct) pct.textContent = percent;
}

function hideUploadOverlay() {
    const overlay = document.getElementById('uploadOverlay');
    if (overlay) overlay.remove();
}

function showUploadComplete(msg) {
    const modal = document.querySelector('.upload-modal');
    if (modal) {
        modal.innerHTML = `
            <div style="font-size: 60px; margin-bottom: 16px;">✅</div>
            <div class="upload-title" style="color: #22c55e;">${msg}</div>
        `;
        setTimeout(hideUploadOverlay, 1500);
    }
}

// 부록 파일 업로드
window.uploadAppendixFiles = async function() {
    const fileInput = document.getElementById('appendixFiles');
    const statusEl = document.getElementById('appendixUploadStatus');
    const uploadBtn = document.getElementById('uploadAppendixBtn');

    if (!fileInput.files || fileInput.files.length === 0) {
        alert('파일을 선택해주세요.');
        return;
    }

    // 현재 편집 중인 규정 정보 가져오기 (RuleEditor 또는 RegulationEditor)
    let regulation = null;
    let ruleId = null;
    let wzpubno = '';

    if (typeof RuleEditor !== 'undefined' && RuleEditor.currentRule) {
        regulation = RuleEditor.currentRule;
        ruleId = regulation.wzruleid || regulation.wzruleseq || regulation.rule_id;
        wzpubno = regulation.wzpubno || '';
    } else if (typeof RegulationEditor !== 'undefined' && RegulationEditor.currentEditingRegulation) {
        regulation = RegulationEditor.currentEditingRegulation;
        ruleId = regulation.id;
        wzpubno = regulation.wzpubno || regulation.classification || '';
    }

    if (!regulation || !ruleId) {
        alert('내규 정보를 찾을 수 없습니다.');
        return;
    }

    // FormData 생성
    const formData = new FormData();
    formData.append('wzpubno', wzpubno);

    // 파일 추가
    const totalFiles = fileInput.files.length;
    for (let i = 0; i < totalFiles; i++) {
        formData.append('files', fileInput.files[i]);
    }

    // 전체 화면 오버레이 표시
    uploadBtn.disabled = true;
    showUploadOverlay(`부록 파일 업로드 중 (${totalFiles}개)`);

    // XMLHttpRequest로 업로드 (진행률 표시)
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            updateUploadOverlay(percent);
        }
    });

    xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            try {
                const data = JSON.parse(xhr.responseText);
                showUploadComplete(`${data.uploaded_count || totalFiles}개 파일 업로드 완료!`);

                // 파일 입력 초기화
                fileInput.value = '';
                uploadBtn.style.display = 'none';
                statusEl.textContent = '';

                // 부록 파일 목록 새로고침
                if (typeof window.loadAppendixFiles === 'function') {
                    window.loadAppendixFiles(ruleId, wzpubno);
                }
            } catch (e) {
                showUploadComplete('업로드 완료!');
            }
        } else {
            hideUploadOverlay();
            try {
                const errorData = JSON.parse(xhr.responseText);
                alert('업로드 실패: ' + (errorData.detail || '서버 오류'));
            } catch (e) {
                alert('업로드 실패: 서버 오류');
            }
        }
        uploadBtn.disabled = false;
    });

    xhr.addEventListener('error', () => {
        hideUploadOverlay();
        alert('네트워크 오류');
        uploadBtn.disabled = false;
    });

    xhr.addEventListener('timeout', () => {
        hideUploadOverlay();
        alert('업로드 시간 초과');
        uploadBtn.disabled = false;
    });

    xhr.open('POST', `/api/v1/appendix/upload/${ruleId}`);
    xhr.timeout = 300000; // 5분 타임아웃
    xhr.send(formData);
}
