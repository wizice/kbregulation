// rule-editor.js - 새로운 내규 편집기 모듈

const RuleEditor = {
    // 상태 관리
    currentRule: null,
    uploadedFiles: {
        pdf: null,
        docx: null
    },
    parsingResults: {
        pdf: null,
        docx: null
    },
    currentModal: null,
    mode: 'edit', // 'new', 'edit', 'revision'
    departments: [], // 부서 목록 캐시

    // 정렬 상태 관리
    sortField: null,
    sortDirection: 'asc', // 'asc' 또는 'desc'
    regulations: [], // 원본 규정 목록 저장

    // 초기화
    init() {
        console.log('[RuleEditor] Initializing...');
        this.bindEvents();
        this.loadRegulations();
        this.loadFilters(); // 필터 옵션 로드
    },

    // 이벤트 바인딩
    bindEvents() {
        // 탭 전환 이벤트는 HTML onclick에서 직접 처리
        // 로그아웃 버튼은 이미 HTML에 onclick이 있으므로 추가 바인딩 불필요
    },

    // 규정 목록 로드
    async loadRegulations() {
        console.log('[RuleEditor] Loading regulations...');
        try {
            // ⭐ CommonUtils.apiCall 사용 (sessionStorage 토큰 + Authorization 헤더)
            const data = await CommonUtils.apiCall('/api/v1/regulations/current', {
                method: 'GET'
            });

            console.log('[RuleEditor] Loaded regulations:', data);

            if (data.success && data.data) {
                this.regulations = data.data; // 규정 목록 저장

                // ===== 디버깅: API 응답 순서 =====
                console.log('[DEBUG] API 응답 순서:', data.data.map(r => ({
                    id: r.rule_id || r.wzruleseq,
                    pubno: r.publication_no,
                    name: r.name
                })));

                // 초기 로드 시 내규번호 기준으로 자동 정렬
                const sorted = [...data.data].sort((a, b) => {
                    const aNo = a.publication_no || '';
                    const bNo = b.publication_no || '';
                    const result = this.naturalSort(aNo, bNo, 'asc');

                    // 정렬 비교 로그
                    if (aNo.includes('1.1.1') && bNo.includes('1.1.1')) {
                        console.log(`[DEBUG] Comparing: "${aNo}" vs "${bNo}" => ${result}`);
                    }

                    return result;
                });

                // ===== 디버깅: 정렬 후 순서 =====
                console.log('[DEBUG] 정렬 후 순서:', sorted.map(r => ({
                    id: r.rule_id || r.wzruleseq,
                    pubno: r.publication_no,
                    name: r.name
                })));

                this.displayRegulations(sorted);

                // 정렬 상태 설정
                this.sortField = 'classification';
                this.sortDirection = 'asc';
                this.updateSortIndicators('classification');
            }
        } catch (error) {
            console.error('[RuleEditor] Error loading regulations:', error);
        }
    },

    // 검색 초기화
    resetSearch() {
        console.log('[RuleEditor] Resetting search filters...');

        // 모든 검색 필터 초기화
        const searchInput = document.getElementById('searchInput');
        const classificationFilter = document.getElementById('classificationFilter');
        const departmentFilter = document.getElementById('departmentFilter');

        if (searchInput) searchInput.value = '';
        if (classificationFilter) classificationFilter.value = '';
        if (departmentFilter) departmentFilter.value = '';

        // 상태와 기간 필터도 나중에 활성화되면 초기화
        // const statusFilter = document.getElementById('statusFilter');
        // const periodFilter = document.getElementById('periodFilter');
        // if (statusFilter) statusFilter.value = '';
        // if (periodFilter) periodFilter.value = '';

        // 전체 목록 다시 로드
        this.loadRegulations();
    },

    // 규정 검색
    async searchRegulations() {
        console.log('[RuleEditor] Searching regulations...');

        // HTML과 일치하는 ID 사용
        const searchInput = document.getElementById('searchInput')?.value?.trim() || '';
        const classificationFilter = document.getElementById('classificationFilter')?.value || '';
        const departmentFilter = document.getElementById('departmentFilter')?.value || '';
        // 상태와 기간 필터는 임시로 주석처리
        // const statusFilter = document.getElementById('statusFilter')?.value || '';
        // const periodFilter = document.getElementById('periodFilter')?.value || '';

        // 모든 필터가 비어있으면 전체 목록 표시
        if (!searchInput && !classificationFilter && !departmentFilter) {
            this.loadRegulations();
            return;
        }

        // 기간 필터를 위한 날짜 계산 (임시 주석처리)
        /*
        let dateThreshold = null;
        if (periodFilter) {
            const now = new Date();
            switch(periodFilter) {
                case '1m':
                    dateThreshold = new Date(now.setMonth(now.getMonth() - 1));
                    break;
                case '3m':
                    dateThreshold = new Date(now.setMonth(now.getMonth() - 3));
                    break;
                case '6m':
                    dateThreshold = new Date(now.setMonth(now.getMonth() - 6));
                    break;
                case '1y':
                    dateThreshold = new Date(now.setFullYear(now.getFullYear() - 1));
                    break;
            }
        }
        */

        // 클라이언트 사이드 필터링
        const filtered = this.regulations.filter(rule => {
            // 키워드 검색 (제목, 내용, 공포번호)
            const matchKeyword = !searchInput ||
                rule.name?.toLowerCase().includes(searchInput.toLowerCase()) ||
                rule.publication_no?.toLowerCase().includes(searchInput.toLowerCase()) ||
                rule.content?.toLowerCase().includes(searchInput.toLowerCase());

            // 분류 필터 - 정확한 분류 번호만 매칭
            const matchClassification = !classificationFilter ||
                (rule.publication_no && rule.publication_no.split('.')[0] === classificationFilter);

            // 부서 필터
            const matchDepartment = !departmentFilter ||
                rule.department === departmentFilter;

            // 상태 필터 (임시 주석처리)
            // const matchStatus = !statusFilter ||
            //     (statusFilter === 'active' && rule.status === '현행') ||
            //     (statusFilter === 'draft' && rule.status === '작성중') ||
            //     (statusFilter === 'review' && rule.status === '검토중') ||
            //     (statusFilter === 'revision' && rule.status === '개정중');

            // 기간 필터 (임시 주석처리)
            // let matchPeriod = !periodFilter;
            // if (periodFilter && dateThreshold) {
            //     const ruleDate = new Date(rule.last_revised_date || rule.established_date);
            //     matchPeriod = ruleDate >= dateThreshold;
            // }

            // return matchKeyword && matchClassification && matchDepartment && matchStatus && matchPeriod;
            return matchKeyword && matchClassification && matchDepartment;
        });

        console.log(`[RuleEditor] Found ${filtered.length} matching regulations`);
        this.displayRegulations(filtered);
    },

    // 전체 선택/해제 토글
    toggleSelectAll() {
        const selectAllCheckbox = document.getElementById('selectAll');
        const checkboxes = document.querySelectorAll('input[name="regulationCheckbox"]');

        if (selectAllCheckbox) {
            checkboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
        }
    },

    // 선택된 항목 내보내기
    async exportSelected() {
        console.log('[RuleEditor] Exporting selected regulations...');

        const checkboxes = document.querySelectorAll('input[name="regulationCheckbox"]:checked');
        const selectedIds = Array.from(checkboxes).map(cb => cb.value);

        if (selectedIds.length === 0) {
            alert('내보낼 항목을 선택해주세요.');
            return;
        }

        try {
            const response = await fetch('/api/v1/rule/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({ rule_ids: selectedIds })
            });

            if (!response.ok) {
                throw new Error('내보내기 실패');
            }

            // 파일 다운로드 처리
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `regulations_export_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.showNotification('내보내기가 완료되었습니다.', 'success');
        } catch (error) {
            console.error('[RuleEditor] Export error:', error);
            this.showNotification(`내보내기 실패: ${error.message}`, 'error');
        }
    },

    // 규정 목록 표시
    displayRegulations(regulations) {
        const tbody = document.getElementById('regulationList');
        if (!tbody) return;

        tbody.innerHTML = '';

        regulations.forEach(rule => {
            const row = document.createElement('tr');
            const ruleName = (rule.name || '제목 없음').replace(/'/g, "\\'");
            row.innerHTML = `
                <td width="50" style="display: none;">
                    <input type="checkbox" name="regulationCheckbox" value="${rule.rule_id || rule.wzruleseq}">
                </td>
                <td width="80">${rule.publication_no || '-'}</td>
                <td width="440">
                    <span class="regulation-name"
                          onclick="RuleEditor.openEditModal(${rule.rule_id || rule.wzruleseq})"
                          title="클릭하여 편집"
                          style="cursor: pointer; color: #2196F3;">
                        ${rule.name || '제목 없음'}
                    </span>
                </td>
                <td width="140">${rule.department || '-'}</td>
                <td width="140">${rule.related_department || rule.wzreldptnm || '-'}</td>
                <td width="80">${this.formatDate(rule.established_date)}</td>
                <td width="80">${this.formatDate(rule.last_revised_date)}</td>
                <td width="80">${this.formatDate(rule.execution_date)}</td>
                <td width="200">
                    <button class="action-btn btn-primary" onclick="RuleEditor.openEditModal(${rule.rule_id || rule.wzruleseq})" style="padding: 6px 12px; font-size: 14px; min-width: 60px;">
                        수정
                    </button>
                    <button class="action-btn btn-warning" onclick="RuleEditor.openRevisionModal(${rule.rule_id || rule.wzruleseq})" style="padding: 6px 12px; font-size: 14px; min-width: 60px;">
                        개정
                    </button>
                    <button class="action-btn" onclick="RuleEditor.openComparisonForRule(${rule.rule_id || rule.wzruleseq})" style="padding: 6px 8px; font-size: 12px; min-width: 50px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer;" title="신구대비표 생성">
                        비교
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    },

    // 자연스러운 숫자 정렬 함수
    naturalSort(a, b, direction) {
        // 분류번호를 숫자 배열로 변환 (예: "1.2.3" -> [1, 2, 3])
        const aParts = a.split('.').map(part => parseInt(part) || 0);
        const bParts = b.split('.').map(part => parseInt(part) || 0);

        // 각 파트를 순서대로 비교
        const maxLength = Math.max(aParts.length, bParts.length);
        for (let i = 0; i < maxLength; i++) {
            const aPart = aParts[i] || 0;
            const bPart = bParts[i] || 0;

            if (aPart !== bPart) {
                const result = aPart - bPart;
                return direction === 'asc' ? result : -result;
            }
        }

        return 0;
    },

    // 정렬 기능
    sortBy(field) {
        console.log('[RuleEditor] Sorting by field:', field);

        // 같은 필드를 다시 클릭하면 정렬 방향 토글
        if (this.sortField === field) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortField = field;
            this.sortDirection = 'asc';
        }

        // 정렬 실행
        const sortedRegulations = [...this.regulations].sort((a, b) => {
            let aValue, bValue;

            switch(field) {
                case 'classification':
                    aValue = a.publication_no || '';
                    bValue = b.publication_no || '';
                    // 자연스러운 숫자 정렬을 위한 특별 처리
                    return this.naturalSort(aValue, bValue, this.sortDirection);
                    break;
                case 'title':
                    aValue = a.name || '';
                    bValue = b.name || '';
                    break;
                case 'announceDate':
                    aValue = a.established_date || '';
                    bValue = b.established_date || '';
                    break;
                case 'revisionDate':
                    aValue = a.last_revised_date || '';
                    bValue = b.last_revised_date || '';
                    break;
                case 'department':
                    aValue = a.department || '';
                    bValue = b.department || '';
                    break;
                case 'effectiveDate':
                    aValue = a.execution_date || '';
                    bValue = b.execution_date || '';
                    break;
                case 'status':
                    aValue = a.status || '시행중';
                    bValue = b.status || '시행중';
                    break;
                default:
                    return 0;
            }

            // 날짜 타입 필드는 날짜로 비교
            if (field.includes('Date') || field.includes('date')) {
                aValue = new Date(aValue || '1900-01-01').getTime();
                bValue = new Date(bValue || '1900-01-01').getTime();
            }

            // 숫자 비교
            if (typeof aValue === 'number' && typeof bValue === 'number') {
                return this.sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
            }

            // 문자열 비교
            const comparison = aValue.toString().localeCompare(bValue.toString(), 'ko');
            return this.sortDirection === 'asc' ? comparison : -comparison;
        });

        // 정렬된 목록 표시
        this.displayRegulations(sortedRegulations);

        // 정렬 표시 업데이트
        this.updateSortIndicators(field);
    },

    // 정렬 인디케이터 업데이트
    updateSortIndicators(field) {
        // 모든 정렬 인디케이터 제거
        document.querySelectorAll('.sort-indicator').forEach(indicator => {
            indicator.textContent = '';
        });

        // 현재 정렬 필드의 인디케이터 업데이트
        const indicator = document.querySelector(`.sort-indicator[data-column="${field}"]`);
        if (indicator) {
            indicator.textContent = this.sortDirection === 'asc' ? ' ▲' : ' ▼';
        }
    },

    // 편집 모달 열기
    async openEditModal(ruleId) {
        console.log('[RuleEditor] Opening edit modal for rule:', ruleId);
        this.mode = 'edit';
        this.currentRule = { id: ruleId };
        // 파일 업로드 객체 초기화
        this.uploadedFiles = { pdf: null, docx: null };
        this.parsingResults = { pdf: null, docx: null };
        this.hasExistingJson = false;
        this.existingJsonContent = null;
        this.isNewUpload = false;

        try {
            // 규정 정보 가져오기
            const response = await fetch(`/api/v1/rule/get/${ruleId}`, {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('규정 정보를 가져올 수 없습니다.');
            }

            const result = await response.json();
            if (!result.success) {
                throw new Error(result.error || '규정 정보를 가져올 수 없습니다.');
            }

            this.currentRule = result.data;

            // 기존 JSON 파일 내용 로드 시도
            try {
                const jsonResponse = await fetch(`/api/v1/json/view/${ruleId}`, {
                    credentials: 'include'
                });

                if (jsonResponse.ok) {
                    const jsonResult = await jsonResponse.json();
                    if (jsonResult.success && jsonResult.data.has_content) {
                        this.hasExistingJson = true;
                        this.existingJsonContent = jsonResult.data.json_content;

                        // JSON 내용을 편집 가능한 텍스트로 변환
                        if (this.existingJsonContent && this.existingJsonContent.조문내용) {
                            this.currentRule.content_text = this.convertJsonToEditableText(this.existingJsonContent);
                            console.log('[RuleEditor] Loaded existing JSON content');
                        }
                    }
                }
            } catch (jsonError) {
                console.warn('[RuleEditor] Could not load JSON content:', jsonError);
                // JSON 로드 실패해도 계속 진행
            }

            this.showEditTabbedModal();

        } catch (error) {
            console.error('[RuleEditor] Error loading rule:', error);
            this.showNotification(`오류: ${error.message}`, 'error');
        }
    },

    // 탭 기반 편집 모달 표시
    showEditTabbedModal() {
        // 기존 모달 제거
        if (this.currentModal) {
            this.currentModal.remove();
        }

        // 모달 생성
        const modalDiv = document.createElement('div');
        modalDiv.className = 'modal active';
        modalDiv.id = 'editTabbedModal';
        modalDiv.style.cssText = 'z-index: 2000;';

        // 모드에 따라 제목 변경
        const modalTitle = this.mode === 'revision' ? '내규 개정' : '내규 편집';

        modalDiv.innerHTML = `
            <div class="modal-content" style="max-width: 800px; width: 85%; height: 80vh;">
                <div class="modal-header">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <button onclick="RuleEditor.closeModal()" style="background: #f0f0f0; border: 1px solid #ccc; border-radius: 6px; padding: 6px 14px; cursor: pointer; font-size: 13px; font-weight: 600; color: #555; display: inline-flex; align-items: center; gap: 4px; transition: background 0.2s;" onmouseover="this.style.background='#e0e0e0'" onmouseout="this.style.background='#f0f0f0'">&#8592; 목록으로</button>
                        <h2 style="margin: 0;">${modalTitle} - ${this.currentRule.wzname || ''}</h2>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <button onclick="RuleEditor.deleteRegulation()"
                                style="background: white; border: 1px solid #dc3545; color: #dc3545; cursor: pointer; padding: 6px 14px; font-size: 13px; font-weight: 600; border-radius: 6px; transition: all 0.2s; display: inline-flex; align-items: center; gap: 4px;"
                                onmouseover="this.style.background='#dc3545'; this.style.color='white'"
                                onmouseout="this.style.background='white'; this.style.color='#dc3545'">
                            내규 삭제
                        </button>
                        <button class="modal-close" onclick="RuleEditor.closeModal()">✕</button>
                    </div>
                </div>
                <div class="modal-body" style="padding: 0; height: calc(100% - 60px); display: flex; flex-direction: column;">
                    <!-- 탭 메뉴 -->
                    <div class="tab-menu" style="display: flex; border-bottom: 2px solid #e5e5e5; background: #f8f9fa;">
                        <button class="edit-tab-btn active" onclick="RuleEditor.switchEditTab('basic')"
                                style="padding: 12px 24px; border: none; background: transparent; cursor: pointer; font-weight: 500;">
                            기본정보
                        </button>
                        <button class="edit-tab-btn" onclick="RuleEditor.switchEditTab('files')"
                                style="padding: 12px 24px; border: none; background: transparent; cursor: pointer; font-weight: 500;">
                            파일업로드
                        </button>
                        <button class="edit-tab-btn" id="contentEditTabBtn" onclick="RuleEditor.switchEditTab('content')"
                                style="padding: 12px 24px; border: none; background: transparent; cursor: pointer; font-weight: 500;"
                                ${this.currentRule.content_text || this.hasExistingJson ? '' : 'disabled'}>
                            내용편집 ${this.hasExistingJson ? '(기존 내용)' : (this.currentRule.content_text ? '' : '(파일 업로드 필요)')}
                        </button>
                        <button class="edit-tab-btn" onclick="RuleEditor.switchEditTab('images')"
                                style="padding: 12px 24px; border: none; background: transparent; cursor: pointer; font-weight: 500;">
                            이미지 관리
                        </button>
                        <button class="edit-tab-btn" onclick="RuleEditor.switchEditTab('appendix')"
                                style="padding: 12px 24px; border: none; background: transparent; cursor: pointer; font-weight: 500;">
                            부록 관리
                        </button>
                        <button class="edit-tab-btn" onclick="RuleEditor.switchEditTab('regNotice')"
                                style="padding: 12px 24px; border: none; background: transparent; cursor: pointer; font-weight: 500;">
                            안내사항
                        </button>
                    </div>

                    <!-- 탭 컨텐츠 -->
                    <div class="tab-contents" style="flex: 1; overflow-y: auto; padding: 20px;">
                        <!-- 기본정보 탭 -->
                        <div id="basicInfoTab" class="edit-tab-content" style="display: block;">
                            ${this.renderBasicInfoTab()}
                        </div>

                        <!-- 파일업로드 탭 -->
                        <div id="filesUploadTab" class="edit-tab-content" style="display: none;">
                            ${this.renderFileUploadTab()}
                        </div>

                        <!-- 내용편집 탭 -->
                        <div id="contentEditTab" class="edit-tab-content" style="display: none;">
                            ${this.renderContentEditTab()}
                        </div>

                        <!-- 이미지 관리 탭 -->
                        <div id="imagesTab" class="edit-tab-content" style="display: none;">
                            ${this.renderImagesTab()}
                        </div>

                        <!-- 부록 관리 탭 -->
                        <div id="appendixTab" class="edit-tab-content" style="display: none;">
                            <div style="padding: 20px;">
                                <!-- 부록 파일 업로드 영역 -->
                                <div style="background: white; padding: 24px; border-radius: 8px; margin-bottom: 24px; border: 1px solid #e0e0e0;">
                                    <h3 style="margin: 0 0 16px 0; color: #333; font-size: 16px; font-weight: 600;">
                                        📎 부록 파일 업로드
                                    </h3>
                                    <div style="margin-bottom: 16px;">
                                        <input type="file"
                                               id="appendixFileInput"
                                               multiple
                                               accept=".docx,.xlsx"
                                               style="display: none;">
                                        <div id="appendixDropZone"
                                             style="border: 2px dashed #ccc; border-radius: 8px; padding: 30px 20px; text-align: center; cursor: pointer; transition: all 0.3s; background: #fafafa;">
                                            <div style="font-size: 32px; margin-bottom: 8px;">📂</div>
                                            <div style="font-size: 14px; color: #555; font-weight: 500;">파일을 드래그하여 놓거나 클릭하여 선택</div>
                                            <div style="font-size: 12px; color: #999; margin-top: 6px;">허용 형식: DOCX, XLSX (서버에서 PDF로 자동 변환) | 여러 파일 가능</div>
                                        </div>
                                        <div id="appendixFileList" style="margin-top: 10px;"></div>
                                        <div id="appendixUploadStatus" style="margin-top: 8px; font-size: 13px; color: #28a745;"></div>
                                    </div>
                                    <button id="uploadAppendixBtn"
                                            style="background: #2196F3; color: white; border: none; padding: 10px 24px; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: 500;">
                                        업로드
                                    </button>
                                </div>

                                <!-- 등록된 부록 파일 목록 -->
                                <div style="background: white; padding: 24px; border-radius: 8px; border: 1px solid #e0e0e0;">
                                    <h3 style="margin: 0 0 16px 0; color: #333; font-size: 16px; font-weight: 600;">
                                        📋 등록된 부록 파일
                                    </h3>
                                    <div id="appendixFilesList" style="min-height: 100px;">
                                        <div style="text-align: center; padding: 40px; color: #999;">
                                            로딩 중...
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 안내사항 탭 -->
                        <div id="regNoticeTab" class="edit-tab-content" style="display: none;">
                            <div style="padding: 20px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                                    <h3 style="margin: 0; color: #333; font-size: 16px; font-weight: 600;">📢 안내사항 관리</h3>
                                    <button onclick="RuleEditor.showRegNoticeForm()"
                                            style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500;">
                                        + 안내사항 추가
                                    </button>
                                </div>
                                <div id="regNoticeFormArea"></div>
                                <div id="regNoticeList" style="min-height: 100px;">
                                    <div style="text-align: center; padding: 40px; color: #999;">
                                        탭을 선택하면 안내사항을 불러옵니다.
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modalDiv);
        this.currentModal = modalDiv;

        // 부서 검색 기능 초기화
        this.initEditDepartmentSearch();

        // 부록 파일 선택 이벤트 바인딩
        this.initAppendixFileHandlers();

        // 탭 버튼 스타일 추가
        const style = document.createElement('style');
        style.textContent = `
            .edit-tab-btn.active {
                background: white !important;
                border-bottom: 2px solid #2196F3 !important;
                color: #2196F3;
            }
            .edit-tab-btn:hover:not(.active):not(:disabled) {
                background: #e9ecef !important;
            }
            .edit-tab-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            /* 모든 입력 필드 크기 통일 */
            .form-control, .form-input, .form-select {
                height: 38px !important;
                padding: 6px 12px !important;
                font-size: 14px !important;
                line-height: 1.42857143 !important;
                border: 1px solid #ddd !important;
                border-radius: 4px !important;
                box-sizing: border-box !important;
            }

            /* 소관부서 input에 드롭다운 화살표 추가 */
            #editDeptSearchInput {
                background-image: url('data:image/svg+xml;charset=UTF-8,%3Csvg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12"%3E%3Cpath fill="%23333" d="M6 9L1 4h10z"/%3E%3C/svg%3E') !important;
                background-repeat: no-repeat !important;
                background-position: right 10px center !important;
                padding-right: 30px !important;
                cursor: pointer !important;
            }

            /* select box에도 동일한 화살표 적용 */
            select.form-control {
                appearance: none !important;
                -webkit-appearance: none !important;
                -moz-appearance: none !important;
                background-image: url('data:image/svg+xml;charset=UTF-8,%3Csvg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12"%3E%3Cpath fill="%23333" d="M6 9L1 4h10z"/%3E%3C/svg%3E') !important;
                background-repeat: no-repeat !important;
                background-position: right 10px center !important;
                padding-right: 30px !important;
                cursor: pointer !important;
            }
        `;
        document.head.appendChild(style);
    },

    // 기본정보 탭 렌더링
    renderBasicInfoTab() {
        const rule = this.currentRule;
        return `
            <div class="form-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 3px;">
                <div class="form-group">
                    <label class="form-label">분류번호 <span style="color: #dc3545; font-size: 0.75em; vertical-align: super;">*필수</span></label>
                    <input type="text" id="editPubNo" class="form-control"
                           value="${rule.wzpubno || ''}" required />
                </div>

                <div class="form-group">
                    <label class="form-label">내규명 <span style="color: #dc3545; font-size: 0.75em; vertical-align: super;">*필수</span></label>
                    <input type="text" id="editRuleName" class="form-control"
                           value="${rule.wzname || ''}" required />
                </div>

                <div class="form-group">
                    <label class="form-label">소관부서 <span style="color: #dc3545; font-size: 0.75em; vertical-align: super;">*필수</span></label>
                    <div class="searchable-select-wrapper">
                        <input type="text" class="form-control" id="editDeptSearchInput"
                               placeholder="부서명 검색..." autocomplete="off"
                               value="${rule.wzmgrdptnm || ''}" style="width: 100%;" />
                        <select id="editDepartment" style="display: none;">
                            <option value="${rule.wzmgrdptorgcd || ''}">${rule.wzmgrdptnm || ''}</option>
                        </select>
                        <div id="editDeptDropdown" class="dept-dropdown" style="display: none;">
                        </div>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label">제정일</label>
                    <input type="date" id="editEstabDate" class="form-control"
                           value="${this.formatDateForInput(rule.wzestabdate)}" style="width: 100%;" />
                </div>

                <div class="form-group">
                    <label class="form-label">개정일</label>
                    <input type="date" id="editLastRevDate" class="form-control"
                           value="${this.formatDateForInput(rule.wzlastrevdate)}" style="width: 100%;" />
                </div>

                <div class="form-group">
                    <label class="form-label">시행일</label>
                    <input type="date" id="editExecDate" class="form-control"
                           value="${this.formatDateForInput(rule.wzexecdate)}" style="width: 100%;" />
                </div>

                <div class="form-group">
                    <label class="form-label">유관부서</label>
                    <select id="editRelDept" class="form-control" style="width: 100%;">
                        <option value="">선택하세요</option>
                        <option value="${rule.wzreldptorgcd || ''}" selected>${rule.wzreldptnm || '선택하세요'}</option>
                    </select>
                </div>

                <div class="form-group">
                    <label class="form-label">상태 <span style="color: #dc3545; font-size: 0.75em; vertical-align: super;">*필수</span></label>
                    <select id="editNewFlag" class="form-control" style="width: 100%;">
                        <option value="현행" ${rule.wznewflag === '현행' ? 'selected' : ''}>현행</option>
                        <option value="연혁" ${rule.wznewflag === '연혁' ? 'selected' : ''}>연혁</option>
                    </select>
                </div>
            </div>

            <div class="form-actions" style="margin-top: 30px; text-align: center;">
                <button class="btn btn-primary" onclick="RuleEditor.saveBasicInfo()"
                        style="padding: 10px 30px;">저장</button>
            </div>
        `;
    },

    // 파일업로드 탭 렌더링
    renderFileUploadTab() {
        return `
            <div class="upload-section" style="height: 100%; display: flex; flex-direction: column;">
                <div style="flex: 1; overflow-y: auto; padding-bottom: 20px;">
                    <p class="info-text" style="background: linear-gradient(135deg, #FFBC00 0%, #60584C 100%); color: white; padding: 15px; border-radius: 8px; margin-bottom: 25px;">
                        DOCX 파일을 업로드해주세요.
                    </p>

                <!-- DOCX 업로드 -->
                <div class="form-group" style="margin-bottom: 25px;">
                    <label class="form-label" style="font-weight: 600; margin-bottom: 10px; display: block;">
                        DOCX 파일 <span class="required" style="color: #dc3545; font-size: 0.75em; vertical-align: super;">*필수</span>
                    </label>
                    <!-- 등록된 DOCX 파일 표시 -->
                    <div id="registeredDocxFile" style="margin-bottom: 10px; padding: 10px; background: #eff6ff; border-radius: 6px; border: 1px solid #bfdbfe; display: none;">
                    </div>
                    <div class="file-upload-wrapper" style="position: relative; overflow: hidden; display: inline-block; width: 100%;">
                        <input type="file" id="editDocxFile" accept=".docx"
                               onchange="RuleEditor.handleFileSelect('docx', this.files[0])"
                               style="position: absolute; left: -9999px;">
                        <label for="editDocxFile" style="display: block; padding: 12px; background: #f8f9fa; border: 2px dashed #dee2e6; border-radius: 8px; cursor: pointer; text-align: center; transition: all 0.3s;">
                            <div id="docxFileName" class="file-name-display" style="color: #6c757d;">
                                📄 클릭하여 DOCX 파일을 선택하세요
                            </div>
                        </label>
                    </div>
                    <div id="docxStatus" class="upload-status" style="margin-top: 8px; font-size: 14px;"></div>
                </div>

                <!-- 신구대비표 업로드 섹션 -->
                <div style="margin-top: 30px; padding-top: 25px; border-top: 2px solid #e5e5e5;">
                    <h4 style="margin: 0 0 15px 0; color: #333; font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                        📊 신구대비표 <span style="font-size: 11px; font-weight: normal; color: #666;">(선택사항)</span>
                    </h4>
                    <!-- 등록된 신구대비표 파일 표시 -->
                    <div id="registeredComparisonFile" style="margin-bottom: 10px; padding: 10px; background: #fffbeb; border-radius: 6px; border: 1px solid #fde68a; display: none;">
                    </div>
                    <div class="form-group">
                        <div class="file-upload-wrapper" style="position: relative; overflow: hidden; display: inline-block; width: 100%;">
                            <input type="file" id="editComparisonFile" accept=".pdf,.docx,.doc,.hwp,.hwpx,.xlsx,.xls"
                                   onchange="RuleEditor.handleComparisonFileSelect(this.files[0])"
                                   style="position: absolute; left: -9999px;">
                            <label for="editComparisonFile" style="display: block; padding: 12px; background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%); border: 2px dashed #ffc107; border-radius: 8px; cursor: pointer; text-align: center; transition: all 0.3s;">
                                <div id="comparisonFileName" class="file-name-display" style="color: #856404;">
                                    📊 클릭하여 신구대비표 파일 업로드 (PDF, DOCX, HWP 등)
                                </div>
                            </label>
                        </div>
                        <div id="comparisonFileStatus" class="upload-status" style="margin-top: 8px; font-size: 14px;"></div>
                    </div>
                </div>

                <!-- 수정 이력파일 섹션 -->
                <div style="margin-top: 30px; padding-top: 25px; border-top: 2px solid #e5e5e5;">
                    <h4 style="margin: 0 0 15px 0; color: #333; font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                        📋 수정 이력파일 <span style="font-size: 11px; font-weight: normal; color: #666;">(선택사항)</span>
                    </h4>

                    <!-- 등록된 파일 목록 -->
                    <div id="editHistoryFilesList" style="margin-bottom: 15px; padding: 12px; background: #f8f9fa; border-radius: 8px; min-height: 40px;">
                        <span style="color: #999; font-size: 13px;">로딩 중...</span>
                    </div>

                    <!-- 새 파일 업로드 -->
                    <div class="form-group">
                        <div class="file-upload-wrapper" style="position: relative; overflow: hidden; display: inline-block; width: 100%;">
                            <input type="file" id="editHistoryFile"
                                   onchange="RuleEditor.handleHistoryFileSelect(this.files[0])"
                                   style="position: absolute; left: -9999px;">
                            <label for="editHistoryFile" style="display: block; padding: 12px; background: linear-gradient(135deg, #e8f4f8 0%, #d4edda 100%); border: 2px dashed #17a2b8; border-radius: 8px; cursor: pointer; text-align: center; transition: all 0.3s;">
                                <div id="historyFileName" class="file-name-display" style="color: #17a2b8;">
                                    📤 클릭하여 수정 이력파일 추가
                                </div>
                            </label>
                        </div>
                        <div id="historyFileStatus" class="upload-status" style="margin-top: 8px; font-size: 14px;"></div>
                    </div>
                </div>

                    <!-- 진행 상황 표시 -->
                    <div id="uploadProgress" class="progress-section" style="display: none; margin: 25px 0; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                        <div class="progress-bar" style="width: 100%; height: 24px; background: #e9ecef; border-radius: 12px; overflow: hidden;">
                            <div class="progress-fill" id="progressBar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #FFBC00 0%, #60584C 100%); transition: width 0.3s; display: flex; align-items: center; justify-content: center;">
                                <span style="color: white; font-size: 12px; font-weight: 600;"></span>
                            </div>
                        </div>
                        <div id="progressText" class="progress-text" style="margin-top: 10px; text-align: center; color: #6c757d; font-size: 14px;">준비 중...</div>
                    </div>
                </div>

                <!-- 버튼 영역 - Sticky 푸터 -->
                <div class="modal-footer" style="position: sticky; bottom: -20px; padding: 15px 20px; text-align: center; border-top: 2px solid #e2e8f0; background: #f8f9fa; z-index: 100; box-shadow: 0 -2px 10px rgba(0,0,0,0.05);">
                    <button class="btn btn-primary" id="processFilesBtn" onclick="RuleEditor.processFiles()" disabled
                            style="padding: 12px 35px; background: linear-gradient(135deg, #FFBC00 0%, #60584C 100%); color: white; border: none; border-radius: 6px; cursor: pointer; opacity: 0.5; box-shadow: 0 4px 15px rgba(255, 188, 0, 0.3);">
                        📤 업로드 및 파싱
                    </button>
                </div>
            </div>

            <style>
                .file-upload-wrapper label:hover {
                    background: #e9ecef !important;
                    border-color: #60584C !important;
                }
                .btn:hover:not(:disabled) {
                    opacity: 0.9;
                    transform: translateY(-1px);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                }
                .btn:disabled {
                    cursor: not-allowed;
                }
            </style>
        `;
    },

    // 내용편집 탭 렌더링
    renderContentEditTab() {
        if (!this.existingJsonContent && !this.hasExistingJson) {
            return `
                <div style="text-align: center; padding: 50px;">
                    <p style="color: #999; font-size: 18px;">📄 파일을 먼저 업로드해주세요</p>
                    <button class="btn btn-primary" onclick="RuleEditor.switchEditTab('files')"
                            style="margin-top: 20px;">파일 업로드하기</button>
                </div>
            `;
        }

        // 상태 메시지 설정
        let statusMessage = '';
        let statusColor = '';
        if (this.isNewUpload) {
            statusMessage = '✨ 새 파일에서 내용을 파싱했습니다';
            statusColor = 'linear-gradient(135deg, #10b981, #059669)';
        } else if (this.hasExistingJson) {
            statusMessage = '📄 기존 내용을 불러왔습니다';
            statusColor = 'linear-gradient(135deg, #3b82f6, #2563eb)';
        }

        // seq별 테이블 생성
        const tableHtml = this.renderEditableTable(this.existingJsonContent);

        // 모드에 따라 저장 함수 선택
        const saveFunction = (this.mode === 'new' || this.mode === 'revision') ? 'saveEditedContent' : 'saveContent';
        const saveButtonText = (this.mode === 'new' || this.mode === 'revision') ? '💾 저장 및 완료' : '💾 전체 저장';

        return `
            <div style="height: 100%; display: flex; flex-direction: column;">
                ${statusMessage ? `
                    <div style="padding: 12px 20px; background: ${statusColor}; color: white; font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 10px;">
                        ${statusMessage}
                    </div>
                ` : ''}

                <div style="flex: 1; padding: 20px; overflow-y: auto; background: #ffffff;" id="contentEditor">
                    ${tableHtml}
                </div>

                <div class="form-actions" style="position: sticky; bottom: -20px; padding: 15px 20px; text-align: center; border-top: 2px solid #e2e8f0; background: #f8f9fa; z-index: 100; box-shadow: 0 -2px 10px rgba(0,0,0,0.05);">
                    <button class="btn btn-primary" onclick="RuleEditor.${saveFunction}()"
                            style="padding: 12px 35px; background: linear-gradient(135deg, #6366f1, #8b5cf6); box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);"
                            title="Ctrl+S 또는 Cmd+S로도 저장할 수 있습니다">
                        ${saveButtonText} <span style="font-size: 11px; opacity: 0.8;">(Ctrl+S)</span>
                    </button>
                </div>
            </div>
        `;
    },

    // 편집 탭 전환
    switchEditTab(tabName) {
        // 모든 탭 버튼과 컨텐츠 비활성화
        const tabButtons = document.querySelectorAll('.edit-tab-btn');
        tabButtons.forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelectorAll('.edit-tab-content').forEach(content => {
            content.style.display = 'none';
            content.classList.remove('active');
        });
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.style.display = 'none';
            panel.classList.remove('active');
        });

        // 선택된 탭 버튼 활성화
        const tabButton = Array.from(document.querySelectorAll('.edit-tab-btn'))
            .find(btn => btn.onclick && btn.onclick.toString().includes(`'${tabName}'`));

        // 탭 컨텐츠 ID 매핑
        let tabContentId;
        switch(tabName) {
            case 'basic':
                tabContentId = 'basicInfoTab';
                break;
            case 'files':
                tabContentId = 'filesUploadTab';
                // 등록된 파일 목록 및 수정 이력파일 목록 로드
                setTimeout(() => {
                    this.loadRegisteredFiles();
                    this.loadEditHistoryFiles();
                }, 100);
                break;
            case 'content':
                tabContentId = 'contentEditTab';
                break;
            case 'images':
                tabContentId = 'imagesTab';
                // ImageManager 초기화 (wzruleid 사용!)
                if (window.ImageManager && this.currentRule) {
                    // wzruleid를 우선 사용 (이미지 폴더명), 없으면 wzruleseq
                    const ruleId = this.currentRule.wzruleid || this.currentRule.wzruleseq || this.currentRule.rule_id;
                    console.log('[RuleEditor] ImageManager.init with ruleId:', ruleId, 'from currentRule:', this.currentRule);
                    if (ruleId) {
                        setTimeout(() => {
                            ImageManager.init(ruleId).catch(err => {
                                console.error('[RuleEditor] Failed to initialize ImageManager:', err);
                            });
                        }, 100);
                    }
                }
                break;
            case 'appendix':
                tabContentId = 'appendixTab';
                // 부록 파일 목록 로드
                if (this.currentRule) {
                    console.log('[DEBUG] currentRule:', this.currentRule);
                    // 부록 API는 wzruleseq를 사용 (wzruleid가 아님!)
                    const ruleSeq = this.currentRule.wzruleseq || this.currentRule.rule_id;
                    const wzpubno = this.currentRule.wzpubno || '';
                    console.log('[DEBUG] ruleSeq:', ruleSeq, 'wzpubno:', wzpubno);
                    if (ruleSeq) {
                        setTimeout(() => {
                            this.loadAppendixFilesList(ruleSeq, wzpubno);
                        }, 100);
                    }
                }
                break;
            case 'regNotice':
                tabContentId = 'regNoticeTab';
                setTimeout(() => this.loadRegNotices(), 100);
                break;
            default:
                console.error('[RuleEditor] Unknown tab name:', tabName);
                return;
        }

        const tabContent = document.getElementById(tabContentId);

        if (tabButton) {
            tabButton.classList.add('active');
        }

        if (tabContent) {
            tabContent.style.display = 'block';
            tabContent.classList.add('active');

            // 내용편집 탭에서만 Ctrl+S 단축키 활성화
            if (tabName === 'content') {
                this.enableSaveShortcut();
            } else {
                this.disableSaveShortcut();
            }
        } else {
            console.error('[RuleEditor] Tab content not found:', tabContentId);
        }
    },

    // 저장 단축키 활성화 (Ctrl+S)
    enableSaveShortcut() {
        // 기존 리스너 제거 (중복 방지)
        this.disableSaveShortcut();

        this.saveShortcutHandler = (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                console.log('[RuleEditor] Ctrl+S pressed - saving content');
                this.saveContent();
            }
        };

        document.addEventListener('keydown', this.saveShortcutHandler);
        console.log('[RuleEditor] Save shortcut (Ctrl+S) enabled');
    },

    // 저장 단축키 비활성화
    disableSaveShortcut() {
        if (this.saveShortcutHandler) {
            document.removeEventListener('keydown', this.saveShortcutHandler);
            this.saveShortcutHandler = null;
            console.log('[RuleEditor] Save shortcut disabled');
        }
    },

    // 기본정보 저장
    async saveBasicInfo() {
        try {
            // 유관부서 select에서 선택된 옵션 가져오기
            const relDeptSelect = document.getElementById('editRelDept');
            const relDeptCode = relDeptSelect ? relDeptSelect.value.trim() : '';
            const relDeptName = (relDeptSelect && relDeptSelect.selectedIndex > 0)
                ? relDeptSelect.options[relDeptSelect.selectedIndex].text
                : '';

            const data = {
                wzname: document.getElementById('editRuleName').value.trim(),
                wzpubno: document.getElementById('editPubNo').value.trim(),
                wzmgrdptnm: document.getElementById('editDeptSearchInput').value.trim(),
                wzmgrdptorgcd: document.getElementById('editDepartment').value.trim(),
                wzreldptnm: relDeptName,
                wzreldptorgcd: relDeptCode,
                // 날짜는 DB 형식(YYYY.MM.DD)으로 변환하여 저장
                wzestabdate: this.formatDateForSave(document.getElementById('editEstabDate').value.trim()),
                wzlastrevdate: this.formatDateForSave(document.getElementById('editLastRevDate').value.trim()),
                wzexecdate: this.formatDateForSave(document.getElementById('editExecDate').value.trim()),
                wznewflag: document.getElementById('editNewFlag').value.trim()
            };

            const response = await fetch(`/api/v1/rule/update-basic/${this.currentRule.wzruleseq}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error('저장에 실패했습니다.');
            }

            const result = await response.json();
            if (result.success) {
                // 백엔드에서 반환한 메시지 사용 (백그라운드 병합 안내 포함)
                this.showNotification(result.message || '기본정보가 저장되었습니다.', 'success');
                // 현재 규정 정보 업데이트
                Object.assign(this.currentRule, data);
            } else {
                throw new Error(result.error || '저장에 실패했습니다.');
            }

        } catch (error) {
            console.error('[RuleEditor] Save error:', error);
            this.showNotification(`저장 실패: ${error.message}`, 'error');
        }
    },

    // 편집 모달용 파일 선택 처리 (신규)
    handleFileSelect(type, file) {
        if (!file) return;

        // uploadedFiles 객체가 없으면 초기화
        if (!this.uploadedFiles) {
            this.uploadedFiles = { docx: null };
        }

        this.uploadedFiles[type] = file;
        const fileNameDiv = document.getElementById(`${type}FileName`);
        const statusDiv = document.getElementById(`${type}Status`);

        if (fileNameDiv) {
            fileNameDiv.innerHTML = `<span style="color: #4CAF50;">✅ ${file.name}</span> <button onclick="event.preventDefault(); event.stopPropagation(); RuleEditor.clearFileSelect('${type}')" style="background: none; border: none; color: #dc3545; cursor: pointer; font-size: 16px; font-weight: bold; padding: 0 4px; vertical-align: middle;" title="파일 삭제">&times;</button>`;
            fileNameDiv.style.color = '#4CAF50';
        }

        if (statusDiv) {
            statusDiv.innerHTML = '<span style="color: #4CAF50;">파일이 선택되었습니다.</span>';
        }

        // DOCX 파일이 선택되면 처리 버튼 활성화
        if (this.uploadedFiles.docx) {
            const processBtn = document.getElementById('processFilesBtn');
            if (processBtn) {
                processBtn.disabled = false;
                processBtn.style.opacity = '1';
            }
        }
    },

    // 파일 선택 초기화
    clearFileSelect(type) {
        if (this.uploadedFiles) {
            this.uploadedFiles[type] = null;
        }

        const fileInput = document.getElementById(type === 'docx' ? 'editDocxFile' : `edit${type.charAt(0).toUpperCase() + type.slice(1)}File`);
        if (fileInput) fileInput.value = '';

        const fileNameDiv = document.getElementById(`${type}FileName`);
        if (fileNameDiv) {
            fileNameDiv.innerHTML = type === 'docx' ? '📄 클릭하여 DOCX 파일을 선택하세요' : '파일을 선택하세요';
            fileNameDiv.style.color = '#6c757d';
        }

        const statusDiv = document.getElementById(`${type}Status`);
        if (statusDiv) statusDiv.innerHTML = '';

        // DOCX 파일이 삭제되면 처리 버튼 비활성화
        if (type === 'docx') {
            const processBtn = document.getElementById('processFilesBtn');
            if (processBtn) {
                processBtn.disabled = true;
                processBtn.style.opacity = '0.5';
            }
        }
    },

    // 기존 파일 업로드 모달용 (구버전 호환)
    handleFileSelectOld(type, input) {
        const file = input.files[0];
        if (!file) return;

        console.log(`[RuleEditor] Selected ${type} file:`, file.name);

        // uploadedFiles 객체가 없으면 초기화
        if (!this.uploadedFiles) {
            this.uploadedFiles = { docx: null };
        }

        // 파일 저장
        this.uploadedFiles[type] = file;

        // 파일명 표시 (X 버튼 포함)
        const fileNameElement = document.getElementById(`${type}FileName`);
        if (fileNameElement) {
            fileNameElement.innerHTML = `${file.name} <button onclick="event.preventDefault(); event.stopPropagation(); RuleEditor.clearFileSelectOld('${type}')" style="background: none; border: none; color: #dc3545; cursor: pointer; font-size: 16px; font-weight: bold; padding: 0 4px; vertical-align: middle;" title="파일 삭제">&times;</button>`;
        }

        // 상태 업데이트
        const statusElement = document.getElementById(`${type}Status`);
        if (statusElement) {
            statusElement.innerHTML = '<span style="color: green;">✓ 파일 선택됨</span>';
        }

        // 두 파일이 모두 선택되면 업로드 버튼 활성화
        if (this.uploadedFiles.pdf && this.uploadedFiles.docx) {
            const uploadBtn = document.getElementById('uploadBtn');
            if (uploadBtn) {
                uploadBtn.disabled = false;
            }
        }
    },

    // 기존 업로드 모달 파일 선택 초기화
    clearFileSelectOld(type) {
        if (this.uploadedFiles) {
            this.uploadedFiles[type] = null;
        }

        const fileInput = document.getElementById(`${type}File`);
        if (fileInput) fileInput.value = '';

        const fileNameElement = document.getElementById(`${type}FileName`);
        if (fileNameElement) {
            fileNameElement.textContent = '파일을 선택하세요';
        }

        const statusElement = document.getElementById(`${type}Status`);
        if (statusElement) statusElement.innerHTML = '';

        // 업로드 버튼 비활성화
        const uploadBtn = document.getElementById('uploadBtn');
        if (uploadBtn) uploadBtn.disabled = true;
    },

    // 수정 이력파일 선택 처리
    handleHistoryFileSelect(file) {
        if (!file) return;

        console.log('[RuleEditor] Selected history file:', file.name);

        // 선택된 파일 표시
        const fileNameDiv = document.getElementById('historyFileName');
        const statusDiv = document.getElementById('historyFileStatus');

        if (fileNameDiv) {
            fileNameDiv.innerHTML = `<span style="color: #17a2b8;">✅ ${file.name}</span>`;
        }

        if (statusDiv) {
            statusDiv.innerHTML = '<span style="color: #17a2b8;">파일이 선택되었습니다. 업로드 중...</span>';
        }

        // 즉시 업로드
        this.uploadHistoryFile(file);
    },

    // 등록된 파일 목록 로드 (PDF, DOCX, 신구대비표)
    async loadRegisteredFiles() {
        const ruleId = this.currentRule?.wzruleseq || this.currentRule?.rule_id;
        if (!ruleId) return;

        try {
            // PDF 파일 표시
            const pdfContainer = document.getElementById('registeredPdfFile');
            if (pdfContainer) {
                if (this.currentRule.wzfilepdf) {
                    const fileName = this.currentRule.wzfilepdf.split('/').pop();
                    pdfContainer.style.display = 'block';
                    pdfContainer.innerHTML = `
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <span style="display: flex; align-items: center; gap: 8px;">
                                <span style="color: #28a745;">✓</span>
                                <span style="font-size: 13px; color: #333;">${fileName}</span>
                            </span>
                            <button onclick="RuleEditor.downloadRegisteredFile('/api/v1/rule-public/rule-file/${ruleId}/download/pdf')"
                                    style="padding: 4px 12px; font-size: 11px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
                                다운로드
                            </button>
                        </div>
                    `;
                } else {
                    pdfContainer.style.display = 'none';
                }
            }

            // DOCX 파일 표시
            const docxContainer = document.getElementById('registeredDocxFile');
            if (docxContainer) {
                if (this.currentRule.wzfiledocx) {
                    const fileName = this.currentRule.wzfiledocx.split('/').pop();
                    docxContainer.style.display = 'block';
                    docxContainer.innerHTML = `
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <span style="display: flex; align-items: center; gap: 8px;">
                                <span style="color: #28a745;">✓</span>
                                <span style="font-size: 13px; color: #333;">${fileName}</span>
                            </span>
                            <button onclick="RuleEditor.downloadRegisteredFile('/api/v1/rule-public/rule-file/${ruleId}/download/docx')"
                                    style="padding: 4px 12px; font-size: 11px; background: #2563eb; color: white; border: none; border-radius: 4px; cursor: pointer;">
                                다운로드
                            </button>
                        </div>
                    `;
                } else {
                    docxContainer.style.display = 'none';
                }
            }

            // 신구대비표 확인
            const compContainer = document.getElementById('registeredComparisonFile');
            if (compContainer) {
                try {
                    const compResponse = await fetch(`/api/v1/rule-public/comparison-table/${ruleId}`, {
                        credentials: 'include'
                    });
                    const compResult = await compResponse.json();

                    if (compResult.success && compResult.file_exists) {
                        const fileName = compResult.file_path.split('/').pop();
                        compContainer.style.display = 'block';
                        compContainer.innerHTML = `
                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                <span style="display: flex; align-items: center; gap: 8px;">
                                    <span style="color: #28a745;">✓</span>
                                    <span style="font-size: 13px; color: #333;">${fileName}</span>
                                </span>
                                <button onclick="RuleEditor.downloadRegisteredFile('/api/v1/rule-public/comparison-table/${ruleId}/download')"
                                        style="padding: 4px 12px; font-size: 11px; background: #856404; color: white; border: none; border-radius: 4px; cursor: pointer;">
                                    다운로드
                                </button>
                            </div>
                        `;
                    } else {
                        compContainer.style.display = 'none';
                    }
                } catch (e) {
                    compContainer.style.display = 'none';
                }
            }

        } catch (error) {
            console.error('[RuleEditor] Error loading registered files:', error);
        }
    },

    // 등록된 파일 다운로드
    downloadRegisteredFile(url) {
        window.open(url, '_blank');
    },

    // 신구대비표 파일 선택 핸들러
    handleComparisonFileSelect(file) {
        if (!file) return;

        const fileNameDiv = document.getElementById('comparisonFileName');
        const statusDiv = document.getElementById('comparisonFileStatus');

        if (fileNameDiv) {
            fileNameDiv.innerHTML = `📊 ${file.name}`;
            fileNameDiv.style.color = '#28a745';
        }

        // 즉시 업로드
        this.uploadComparisonFile(file);
    },

    // 신구대비표 파일 업로드
    async uploadComparisonFile(file) {
        const ruleId = this.currentRule?.wzruleseq || this.currentRule?.rule_id;
        if (!ruleId) {
            this.showNotification('규정 정보가 없습니다.', 'error');
            return;
        }

        const statusDiv = document.getElementById('comparisonFileStatus');

        try {
            const formData = new FormData();
            formData.append('comparison_file', file);

            const response = await fetch(`/api/v1/rule/upload-comparison-table/${ruleId}`, {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                if (statusDiv) {
                    statusDiv.innerHTML = '<span style="color: #28a745;">✅ 업로드 완료!</span>';
                }

                // 파일 선택 초기화
                const fileInput = document.getElementById('editComparisonFile');
                if (fileInput) fileInput.value = '';

                const fileNameDiv = document.getElementById('comparisonFileName');
                if (fileNameDiv) {
                    fileNameDiv.innerHTML = '📊 클릭하여 신구대비표 파일 업로드 (PDF, DOCX, HWP 등)';
                    fileNameDiv.style.color = '#856404';
                }

                // 등록된 파일 목록 새로고침
                this.loadRegisteredFiles();

                this.showNotification('신구대비표가 업로드되었습니다.', 'success');
            } else {
                throw new Error(result.detail || result.message || '업로드 실패');
            }
        } catch (error) {
            console.error('[RuleEditor] Error uploading comparison file:', error);
            if (statusDiv) {
                statusDiv.innerHTML = `<span style="color: #dc3545;">❌ 업로드 실패: ${error.message}</span>`;
            }
            this.showNotification(`업로드 실패: ${error.message}`, 'error');
        }
    },

    // 수정 이력파일 목록 로드
    async loadEditHistoryFiles() {
        const container = document.getElementById('editHistoryFilesList');
        if (!container) return;

        const ruleId = this.currentRule?.wzruleseq || this.currentRule?.rule_id;
        if (!ruleId) {
            container.innerHTML = '<span style="color: #999; font-size: 13px;">규정 정보가 없습니다.</span>';
            return;
        }

        try {
            const response = await fetch(`/api/v1/rule-public/history-file/${ruleId}`, {
                method: 'GET',
                credentials: 'include'
            });
            const result = await response.json();

            if (result.success && result.has_file && result.files && result.files.length > 0) {
                container.innerHTML = result.files.map((file, index) => `
                    <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 0; ${index > 0 ? 'border-top: 1px solid #e0e0e0;' : ''}">
                        <span style="flex: 1; display: flex; align-items: center; gap: 6px;">
                            <span style="color: #28a745;">✓</span>
                            <span style="font-size: 13px;">${file.filename}</span>
                            <span style="color: #888; font-size: 11px;">(${file.size_str})</span>
                        </span>
                        <div style="display: flex; gap: 5px;">
                            <button onclick="RuleEditor.downloadEditHistoryFile('${file.filename}')"
                                    style="padding: 4px 10px; font-size: 11px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                                다운로드
                            </button>
                            <button onclick="RuleEditor.deleteEditHistoryFile('${file.filename}')"
                                    style="padding: 4px 10px; font-size: 11px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
                                삭제
                            </button>
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<span style="color: #999; font-size: 13px;">등록된 수정 이력파일이 없습니다.</span>';
            }
        } catch (error) {
            console.error('[RuleEditor] Error loading history files:', error);
            container.innerHTML = '<span style="color: #dc3545; font-size: 13px;">파일 목록을 불러올 수 없습니다.</span>';
        }
    },

    // 수정 이력파일 업로드
    async uploadHistoryFile(file) {
        const ruleId = this.currentRule?.wzruleseq || this.currentRule?.rule_id;
        if (!ruleId) {
            this.showNotification('규정 정보가 없습니다.', 'error');
            return;
        }

        const statusDiv = document.getElementById('historyFileStatus');

        try {
            const formData = new FormData();
            formData.append('history_file', file);

            const response = await fetch(`/api/v1/rule/upload-history-file/${ruleId}`, {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                if (statusDiv) {
                    statusDiv.innerHTML = '<span style="color: #28a745;">✅ 업로드 완료!</span>';
                }

                // 파일 선택 초기화
                const fileInput = document.getElementById('editHistoryFile');
                if (fileInput) fileInput.value = '';

                const fileNameDiv = document.getElementById('historyFileName');
                if (fileNameDiv) {
                    fileNameDiv.innerHTML = '📤 클릭하여 수정 이력파일 추가';
                    fileNameDiv.style.color = '#17a2b8';
                }

                // 파일 목록 새로고침
                this.loadEditHistoryFiles();

                this.showNotification('수정 이력파일이 업로드되었습니다.', 'success');
            } else {
                throw new Error(result.detail || result.message || '업로드 실패');
            }
        } catch (error) {
            console.error('[RuleEditor] Error uploading history file:', error);
            if (statusDiv) {
                statusDiv.innerHTML = `<span style="color: #dc3545;">❌ 업로드 실패: ${error.message}</span>`;
            }
            this.showNotification(`업로드 실패: ${error.message}`, 'error');
        }
    },

    // 수정 이력파일 다운로드
    downloadEditHistoryFile(filename) {
        const ruleId = this.currentRule?.wzruleseq || this.currentRule?.rule_id;
        if (!ruleId) {
            this.showNotification('규정 정보가 없습니다.', 'error');
            return;
        }

        const url = `/api/v1/rule-public/history-file/${ruleId}/download?filename=${encodeURIComponent(filename)}`;
        window.open(url, '_blank');
    },

    // 수정 이력파일 삭제
    async deleteEditHistoryFile(filename) {
        if (!confirm(`'${filename}' 파일을 삭제하시겠습니까?`)) return;

        const ruleId = this.currentRule?.wzruleseq || this.currentRule?.rule_id;
        if (!ruleId) {
            this.showNotification('규정 정보가 없습니다.', 'error');
            return;
        }

        try {
            const response = await fetch(`/api/v1/rule/history-file/${ruleId}?filename=${encodeURIComponent(filename)}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(result.message || '삭제되었습니다.', 'success');
                this.loadEditHistoryFiles(); // 목록 새로고침
            } else {
                throw new Error(result.detail || result.message || '삭제 실패');
            }
        } catch (error) {
            console.error('[RuleEditor] Error deleting history file:', error);
            this.showNotification(`삭제 실패: ${error.message}`, 'error');
        }
    },

    // 파일 처리 및 파싱
    async processFiles() {
        if (!this.uploadedFiles.docx) {
            this.showNotification('DOCX 파일을 선택해주세요.', 'warning');
            return;
        }

        try {
            // 새 파일 업로드 플래그 설정
            this.isNewUpload = true;
            this.hasExistingJson = false;  // 기존 JSON 플래그 비활성화

            this.showProgress('파일 업로드 중...');

            // DOCX 업로드 및 파싱
            const docxResult = await this.uploadAndParseDOCX();

            this.showProgress('파일 병합 중... 📊');

            // JSON 병합 (PDF 없이)
            const mergeResult = await this.mergeJSONFiles(null, docxResult);

            console.log('[RuleEditor] Merge completed, checking result:', {
                success: mergeResult.success,
                hasContent: !!mergeResult.content,
                hasTextContent: !!mergeResult.text_content
            });

            if (mergeResult.success && (mergeResult.content || mergeResult.text_content)) {
                // content_text 업데이트 (새 업로드이므로 기존 내용 덮어쓰기)
                this.currentRule.content_text = mergeResult.content || mergeResult.text_content;
                this.isNewUpload = true;  // 새 업로드 플래그 유지

                // 병합된 JSON 데이터 저장 (편집 저장 시 사용)
                this.mergedJsonData = mergeResult.merged_data;
                this.mergedJsonPath = mergeResult.json_path || mergeResult.filepath;

                // RuleEditor 상태 업데이트 (내용편집 탭에서 사용)
                this.existingJsonContent = mergeResult.merged_data;
                this.hasExistingJson = true;

                // 내용편집 탭 활성화 및 전환
                const contentTabBtn = document.getElementById('contentEditTabBtn');
                if (contentTabBtn) {
                    contentTabBtn.disabled = false;
                    contentTabBtn.textContent = '내용편집 ✅';
                    contentTabBtn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
                    contentTabBtn.style.color = 'white';
                }


                this.showProgress('파싱 완료! 내용편집 탭으로 이동합니다... ✨');

                // 성공 애니메이션
                const progressBar = document.querySelector('.progress-fill');
                if (progressBar) {
                    progressBar.style.width = '100%';
                    progressBar.style.background = 'linear-gradient(90deg, #10b981, #059669)';
                }

                // 1.5초 후 자동 저장 실행
                setTimeout(async () => {
                    console.log('[RuleEditor] Auto-saving after file processing...');
                    this.hideProgress();

                    // ===== 파싱 완료 후 자동 저장 =====
                    try {
                        this.showProgress('자동 저장 중...');

                        const formData = new FormData();
                        formData.append('rule_id', this.currentRule.wzruleseq || this.currentRule.id || this.currentRule.rule_id);
                        formData.append('mode', this.mode);
                        formData.append('is_revision', this.mode === 'revision');

                        // 병합된 JSON 데이터 전송
                        if (this.mergedJsonData) {
                            formData.append('merged_json_data', JSON.stringify(this.mergedJsonData));
                            // 텍스트 내용도 생성
                            const textContent = this.convertJsonToText(this.mergedJsonData);
                            formData.append('content', textContent);
                        }

                        // 병합 JSON 경로
                        if (this.mergedJsonPath) {
                            formData.append('merged_json_path', this.mergedJsonPath);
                            formData.append('use_merged_json', 'true');
                        }

                        // 개정 모드인 경우 날짜 정보 추가
                        if (this.mode === 'revision' && this.revisionInfo) {
                            formData.append('revision_date', this.revisionInfo.revisionDate);
                            formData.append('execution_date', this.revisionInfo.executionDate);
                        }

                        console.log('[RuleEditor] Auto-saving with mode:', this.mode);

                        const response = await fetch('/api/v1/rule/save-edited-content', {
                            method: 'POST',
                            credentials: 'include',
                            body: formData
                        });

                        if (!response.ok) {
                            throw new Error('자동 저장 실패');
                        }

                        const result = await response.json();
                        console.log('[RuleEditor] Auto-save result:', result);

                        this.hideProgress();
                        this.showNotification('✅ 파싱 및 저장이 완료되었습니다!', 'success');

                        // 모달 닫고 목록 새로고침
                        setTimeout(() => {
                            this.closeModal();
                            this.loadRegulations();

                            if (this.mode === 'new') {
                                this.showNotification('신규 내규가 성공적으로 제정되었습니다.', 'success');
                            } else if (this.mode === 'revision') {
                                this.showNotification('규정이 성공적으로 개정되었습니다.', 'success');
                            }
                        }, 1500);

                    } catch (error) {
                        console.error('[RuleEditor] Auto-save error:', error);
                        this.hideProgress();
                        this.showNotification(`자동 저장 실패: ${error.message}`, 'error');

                        // 실패 시 수동 편집 모드로 전환
                        this.showNotification('수동으로 저장해주세요.', 'warning');
                        this.switchEditTab('content');
                        const contentTabDiv = document.getElementById('contentEditTab');
                        if (contentTabDiv) {
                            contentTabDiv.innerHTML = this.renderContentEditTab();
                        }
                    }
                }, 1500);
            }

        } catch (error) {
            console.error('[RuleEditor] Process files error:', error);
            this.showNotification(`파일 처리 실패: ${error.message}`, 'error');
            this.hideProgress();
        }
    },

    // 내용 저장
    async saveContent() {
        try {
            if (!this.existingJsonContent) {
                this.showNotification('기존 JSON이 없습니다', 'error');
                return;
            }

            // seq별 테이블에서 수정된 내용 수집
            const updatedJson = this.collectArticleUpdates(this.existingJsonContent);

            if (!updatedJson) {
                this.showNotification('수정 내용을 수집할 수 없습니다', 'error');
                return;
            }

            const response = await fetch(`/api/v1/rule/update-json/${this.currentRule.wzruleseq}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ json_data: updatedJson })
            });

            if (!response.ok) {
                throw new Error('내용 저장에 실패했습니다.');
            }

            const result = await response.json();
            if (result.success) {
                this.existingJsonContent = updatedJson; // 메모리 동기화
                this.showNotification('✅ 저장 완료 (백그라운드에서 병합 중)', 'success');
                // 모달 닫고 목록 새로고침
                setTimeout(() => {
                    this.closeModal();
                    this.loadRegulations();
                }, 1500);
            } else {
                throw new Error(result.error || '저장에 실패했습니다.');
            }

        } catch (error) {
            console.error('[RuleEditor] Save content error:', error);
            this.showNotification(`❌ 저장 실패: ${error.message}`, 'error');
        }
    },

    // 날짜 포맷 변환 (input용)
    formatDateForInput(dateString) {
        if (!dateString) return '';

        // 날짜 문자열 정리 (공백 제거)
        let cleaned = dateString.replace(/\s+/g, '').trim();

        // 이미 YYYY-MM-DD 형식인 경우 그대로 반환
        if (/^\d{4}-\d{2}-\d{2}/.test(cleaned)) {
            return cleaned.substring(0, 10);
        }

        // YYYY.M.D 또는 YYYY.MM.DD (끝에 점 있을 수도) 형식을 파싱
        const dotMatch = cleaned.match(/^(\d{4})\.(\d{1,2})\.(\d{1,2})\.?$/);
        if (dotMatch) {
            const y = dotMatch[1];
            const m = dotMatch[2].padStart(2, '0');
            const d = dotMatch[3].padStart(2, '0');
            return `${y}-${m}-${d}`;
        }

        // YYYY.MM 형식 (일자 없음) -> YYYY-MM-01로 변환
        if (/^\d{4}\.\d{1,2}$/.test(cleaned)) {
            const parts = cleaned.split('.');
            return `${parts[0]}-${parts[1].padStart(2, '0')}-01`;
        }

        // 기타 형식은 빈 문자열 반환
        console.warn('[RuleEditor] Unsupported date format:', dateString);
        return '';
    },

    // 날짜 포맷 변환 (표시용 - yyyy.mm.dd.)
    formatDateDisplay(dateString) {
        if (!dateString) return '';
        // YYYY-MM-DD -> YYYY.MM.DD. 형식으로 변환
        const match = dateString.match(/(\d{4})-(\d{2})-(\d{2})/);
        if (match) {
            return `${match[1]}.${match[2]}.${match[3]}.`;
        }
        return dateString;
    },

    // 날짜 포맷 변환 (저장용 - YYYY-MM-DD -> YYYY.MM.DD)
    formatDateForSave(dateString) {
        if (!dateString) return '';

        // 날짜 문자열 정리 (공백 제거)
        let cleaned = dateString.trim();

        // YYYY-MM-DD 형식을 YYYY.MM.DD로 변환 (DB 저장 형식)
        const match = cleaned.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (match) {
            return `${match[1]}.${match[2]}.${match[3]}`;
        }

        // 이미 YYYY.MM.DD 형식이면 그대로 반환
        if (/^\d{4}\.\d{2}\.\d{2}/.test(cleaned)) {
            return cleaned.substring(0, 10);
        }

        // 기타 형식은 그대로 반환
        return cleaned;
    },

    // 날짜 선택 시 표시 필드 업데이트 (yyyy-mm-dd -> yyyy.mm.dd.)
    updateDateDisplay(dateInputId, displayInputId) {
        const dateInput = document.getElementById(dateInputId);
        const displayInput = document.getElementById(displayInputId);

        if (dateInput && displayInput && dateInput.value) {
            // yyyy-mm-dd -> yyyy.mm.dd. 형식으로 변환
            const dateValue = dateInput.value;
            const match = dateValue.match(/(\d{4})-(\d{2})-(\d{2})/);
            if (match) {
                displayInput.value = `${match[1]}.${match[2]}.${match[3]}.`;
            }
        }
    },

    // JSON 내용을 seq별 테이블로 변환
    renderEditableTable(jsonContent) {
        if (!jsonContent || !jsonContent.조문내용) {
            return '<p>편집할 내용이 없습니다.</p>';
        }

        let html = `
            <div class="article-edit-container">
                <div class="edit-info">
                    <span>※ 레벨/번호/내용을 수정할 수 있습니다.</span>
                </div>
                <table class="article-edit-table">
                    <thead>
                        <tr>
                            <th style="width: 70px;">레벨</th>
                            <th style="width: 70px;">번호</th>
                            <th>내용</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        jsonContent.조문내용.forEach((article, index) => {
            // 레벨이 0인 조문은 표시하지 않음
            if (article.레벨 === 0) {
                return;
            }

            const levelIndent = '　'.repeat(article.레벨 || 0); // 레벨별 들여쓰기
            html += `
                <tr data-seq="${article.seq}">
                    <td class="level-cell">
                        <input type="number"
                               class="article-level-input"
                               data-seq="${article.seq}"
                               value="${article.레벨 !== undefined ? article.레벨 : 0}"
                               min="0"
                               max="10"
                               step="1"
                               style="width: 60px; padding: 4px; text-align: center;"
                               title="0=제목, 1=조문, 2=항, 3=호...">
                    </td>
                    <td class="number-cell">
                        <input type="text"
                               class="article-number-input"
                               data-seq="${article.seq}"
                               value="${article.번호 || ''}"
                               maxlength="50"
                               style="width: 100%; padding: 4px;"
                               placeholder="">
                    </td>
                    <td class="content-cell">
                        <textarea
                            class="article-content-input"
                            data-seq="${article.seq}"
                            rows="${Math.max(2, Math.ceil(article.내용.length / 80))}"
                        >${article.내용}</textarea>
                    </td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        return html;
    },

    // seq별 테이블에서 수정된 내용 수집
    collectArticleUpdates(originalJson) {
        const updatedJson = JSON.parse(JSON.stringify(originalJson));

        // 레벨 수집
        const levelInputs = document.querySelectorAll('.article-level-input');
        levelInputs.forEach((input) => {
            const seq = parseInt(input.dataset.seq);
            const newLevel = parseInt(input.value);

            const article = updatedJson.조문내용.find(a => a.seq === seq);
            if (article) {
                article.레벨 = isNaN(newLevel) ? 0 : newLevel;
            }
        });

        // 번호 수집
        const numberInputs = document.querySelectorAll('.article-number-input');
        numberInputs.forEach((input) => {
            const seq = parseInt(input.dataset.seq);
            const newNumber = input.value.trim();

            const article = updatedJson.조문내용.find(a => a.seq === seq);
            if (article) {
                article.번호 = newNumber;
            }
        });

        // 내용 수집
        const textareas = document.querySelectorAll('.article-content-input');
        textareas.forEach((textarea) => {
            const seq = parseInt(textarea.dataset.seq);
            const newContent = textarea.value.trim();

            const article = updatedJson.조문내용.find(a => a.seq === seq);
            if (article) {
                article.내용 = newContent;
            }
        });

        return updatedJson;
    },

    // JSON 데이터를 텍스트로 변환 (백엔드 호환성)
    convertJsonToText(jsonData) {
        if (!jsonData || !jsonData.조문내용) {
            return '';
        }

        let text = '';
        for (const article of jsonData.조문내용) {
            const number = article.번호 || '';
            const content = article.내용 || '';

            if (number) {
                text += `${number} ${content}\n`;
            } else {
                text += `${content}\n`;
            }
        }

        return text;
    },

    // 편집 모달용 부서 검색 초기화
    initEditDepartmentSearch() {
        const searchInput = document.getElementById('editDeptSearchInput');
        const dropdown = document.getElementById('editDeptDropdown');
        const selectElement = document.getElementById('editDepartment');

        if (!searchInput || !dropdown) return;

        // 부서 목록이 없으면 로드
        if (!this.departments || this.departments.length === 0) {
            this.loadDepartmentsForEdit();
        }

        // 포커스 시 드롭다운 표시
        searchInput.addEventListener('focus', () => {
            dropdown.style.display = 'block';
            this.renderEditDepartmentDropdown(searchInput.value);
        });

        // 입력 시 필터링
        searchInput.addEventListener('input', (e) => {
            this.renderEditDepartmentDropdown(e.target.value);
        });

        // 외부 클릭 시 드롭다운 숨기기
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.searchable-select-wrapper')) {
                dropdown.style.display = 'none';
            }
        });
    },

    // 편집 모달용 부서 목록 로드
    async loadDepartmentsForEdit() {
        try {
            const response = await fetch('/api/v1/dept/list', {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('부서 목록을 가져올 수 없습니다.');
            }

            const result = await response.json();
            if (result.success) {
                this.departments = result.departments || result.data || [];
                console.log('[RuleEditor] Loaded departments for edit:', this.departments.length);

                // 유관부서 select box 채우기
                this.populateRelDeptSelect();
            }
        } catch (error) {
            console.error('[RuleEditor] Error loading departments:', error);
            this.departments = [];
        }
    },

    // 유관부서 select box 채우기
    populateRelDeptSelect() {
        const selectElement = document.getElementById('editRelDept');
        if (!selectElement) return;

        // 현재 선택된 값 저장
        const currentValue = this.currentRule ? this.currentRule.wzreldptorgcd : '';

        // 기존 옵션 제거하고 "선택하세요" 옵션 추가
        selectElement.innerHTML = '<option value="">선택하세요</option>';

        // 부서 목록 추가
        this.departments.forEach(dept => {
            const name = dept.name || dept.wzdeptnm || '';
            const code = dept.code || dept.wzdeptcd || '';
            const option = document.createElement('option');
            option.value = code;
            option.textContent = name;

            // 현재 규정의 유관부서가 있으면 선택
            if (code === currentValue) {
                option.selected = true;
            }

            selectElement.appendChild(option);
        });

        console.log('[RuleEditor] Populated rel dept select with', this.departments.length, 'departments');
    },

    // 편집 모달용 부서 드롭다운 렌더링
    renderEditDepartmentDropdown(searchTerm = '') {
        const dropdown = document.getElementById('editDeptDropdown');
        if (!dropdown) return;

        const filteredDepts = this.departments.filter(dept => {
            const name = dept.name || dept.wzdeptnm || '';
            return name.toLowerCase().includes(searchTerm.toLowerCase());
        });

        if (filteredDepts.length === 0) {
            dropdown.innerHTML = '<div style="padding: 10px; color: #999;">검색 결과가 없습니다</div>';
            return;
        }

        dropdown.innerHTML = filteredDepts.map(dept => {
            const name = dept.name || dept.wzdeptnm || '이름 없음';
            const code = dept.code || dept.wzdeptcd || '';
            return `
                <div class="dept-item" onclick="RuleEditor.selectEditDepartment('${code}', '${name}')"
                     style="padding: 10px; cursor: pointer; border-bottom: 1px solid #eee;">
                    ${name}
                </div>
            `;
        }).join('');

        // 호버 효과
        dropdown.querySelectorAll('.dept-item').forEach(item => {
            item.addEventListener('mouseenter', () => {
                item.style.backgroundColor = '#f0f0f0';
            });
            item.addEventListener('mouseleave', () => {
                item.style.backgroundColor = 'white';
            });
        });
    },

    // 편집 모달용 부서 선택
    selectEditDepartment(code, name) {
        const searchInput = document.getElementById('editDeptSearchInput');
        const selectElement = document.getElementById('editDepartment');
        const dropdown = document.getElementById('editDeptDropdown');

        if (searchInput) searchInput.value = name;
        if (selectElement) {
            selectElement.innerHTML = `<option value="${code}" selected>${name}</option>`;
            selectElement.value = code;
        }
        if (dropdown) dropdown.style.display = 'none';
    },

    // 개정 모달 열기
    async openRevisionModal(ruleId) {
        console.log('[RuleEditor] Opening revision modal for rule:', ruleId);
        this.mode = 'revision';

        try {
            // regulations 배열에서 해당 규정 정보 찾기
            const existingRule = this.regulations.find(rule =>
                (rule.rule_id || rule.wzruleseq) == ruleId
            );

            if (existingRule) {
                this.currentRule = {
                    id: ruleId,
                    wzruleseq: ruleId,
                    wzpubno: existingRule.publication_no || existingRule.wzpubno || '',
                    wzname: existingRule.name || existingRule.wzname || '',
                    wzmgrdptnm: existingRule.department || existingRule.wzmgrdptnm || '',
                    wzmgrdptorgcd: existingRule.wzmgrdptorgcd || ''
                };
                console.log('[RuleEditor] 개정 시작 - 기존 내규 정보 보존:', this.currentRule);
            } else {
                // regulations 배열에서 찾을 수 없는 경우 기본 설정
                this.currentRule = { id: ruleId, wzruleseq: ruleId };
                console.warn('[RuleEditor] regulations 배열에서 규정 정보를 찾을 수 없음');
            }

            // 먼저 날짜 선택 모달 표시
            this.showDateSelectionModal();
        } catch (error) {
            console.error('[RuleEditor] 개정 모달 열기 오류:', error);
            this.currentRule = { id: ruleId, wzruleseq: ruleId };
            this.showDateSelectionModal();
        }
    },

    // 날짜 선택 모달 표시
    showDateSelectionModal() {
        // 기존 모달 제거
        if (this.currentModal) {
            this.currentModal.remove();
        }

        const today = new Date().toISOString().split('T')[0];
        console.log('[RuleEditor] Today date:', today);

        // 모달 생성
        const modalDiv = document.createElement('div');
        modalDiv.className = 'modal active';
        modalDiv.id = 'dateSelectionModal';

        modalDiv.innerHTML = `
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <h2>개정 정보 입력</h2>
                    <button class="modal-close" onclick="RuleEditor.closeDateModal()">✕</button>
                </div>
                <div class="modal-body">
                    <p class="info-text" style="background-color: #e8f4fd; padding: 10px; border-radius: 4px; margin-bottom: 20px;">
                        개정일과 시행일자를 반드시 입력해주세요.
                    </p>

                    <div class="form-group" style="margin-bottom: 20px;">
                        <label class="form-label">개정일 <span style="color: #dc3545; font-size: 0.75em; vertical-align: super;">*필수</span></label>
                        <input type="date" id="revisionDate" name="revisionDate" class="form-control"
                               value="${today}"
                               style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;" />
                    </div>

                    <div class="form-group" style="margin-bottom: 20px;">
                        <label class="form-label">시행일자 <span style="color: #dc3545; font-size: 0.75em; vertical-align: super;">*필수</span></label>
                        <input type="date" id="executionDate" name="executionDate" class="form-control"
                               value="${today}"
                               style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;" />
                    </div>

                    <div class="form-group" style="margin-bottom: 20px;">
                        <label class="form-label">신구대비표 PDF <span style="color: #dc3545; font-size: 0.75em; vertical-align: super;">*필수</span></label>
                        <input type="file" id="revisionComparisonFile" name="revisionComparisonFile"
                               class="form-control" accept=".pdf"
                               style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;" />
                        <p style="color: #6c757d; font-size: 12px; margin-top: 5px;">개정 전후 비교표 PDF 파일을 업로드하거나, 아래에서 자동 생성하세요</p>
                    </div>

                    <!-- 신구대비표 자동 생성 -->
                    <div style="border: 1px solid #667eea; border-radius: 8px; padding: 15px; background: #f8f9ff; margin-bottom: 20px;">
                        <div style="font-weight: 600; color: #667eea; margin-bottom: 10px; font-size: 14px;">
                            📊 또는 신구대비표 자동 생성
                        </div>
                        <p style="color: #6c757d; font-size: 12px; margin-bottom: 12px;">
                            새 버전의 DOCX 파일을 업로드하면 현행 규정과 비교하여 신구대비표를 자동 생성합니다. (PDF는 선택사항)
                        </p>
                        <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                            <div style="flex: 1;">
                                <label style="font-size: 12px; color: #555; display: block; margin-bottom: 4px;">새 버전 DOCX <span style="color: #dc3545;">*필수</span></label>
                                <input type="file" id="autoGenDocxFile" accept=".docx"
                                       style="width: 100%; padding: 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 12px;" />
                            </div>
                            <div style="flex: 1;">
                                <label style="font-size: 12px; color: #555; display: block; margin-bottom: 4px;">새 버전 PDF <span style="color: #999;">(선택)</span></label>
                                <input type="file" id="autoGenPdfFile" accept=".pdf"
                                       style="width: 100%; padding: 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 12px;" />
                            </div>
                        </div>
                        <button id="btnAutoGenerate" class="btn btn-primary btn-sm"
                                onclick="RuleEditor.autoGenerateComparison()"
                                style="width: 100%; padding: 8px; font-size: 13px;">
                            신구대비표 자동 생성
                        </button>
                        <div id="autoGenStatus" style="margin-top: 8px; font-size: 12px;"></div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="RuleEditor.closeDateModal()">취소</button>
                    <button class="btn btn-primary" onclick="RuleEditor.proceedToFileUpload()">다음</button>
                </div>
            </div>
        `;

        document.body.appendChild(modalDiv);
        this.currentModal = modalDiv;

        // 날짜 input 요소에 오늘 날짜 설정 - 즉시 실행
        requestAnimationFrame(() => {
            const revisionDateInput = document.getElementById('revisionDate');
            const executionDateInput = document.getElementById('executionDate');

            if (revisionDateInput && !revisionDateInput.value) {
                revisionDateInput.value = today;
                console.log('[RuleEditor] Set revisionDate to:', today);
            }

            if (executionDateInput && !executionDateInput.value) {
                executionDateInput.value = today;
                console.log('[RuleEditor] Set executionDate to:', today);
            }

            // 값이 제대로 설정되었는지 재확인
            console.log('[RuleEditor] Final date values:', {
                revisionDate: revisionDateInput?.value,
                executionDate: executionDateInput?.value
            });
        });
    },

    // 날짜 모달 닫기
    closeDateModal() {
        if (this.currentModal) {
            this.currentModal.remove();
            this.currentModal = null;
        }
    },

    // 날짜 선택 후 파일 업로드로 진행
    async proceedToFileUpload() {
        console.log('[RuleEditor] proceedToFileUpload called');

        // 요소 존재 확인
        const revisionDateElement = document.getElementById('revisionDate');
        const executionDateElement = document.getElementById('executionDate');
        const comparisonFileElement = document.getElementById('revisionComparisonFile');

        console.log('[RuleEditor] Date elements found:', {
            revisionDate: revisionDateElement ? 'found' : 'not found',
            executionDate: executionDateElement ? 'found' : 'not found',
            comparisonFile: comparisonFileElement ? 'found' : 'not found'
        });

        const revisionDate = revisionDateElement ? revisionDateElement.value : null;
        const executionDate = executionDateElement ? executionDateElement.value : null;
        const comparisonFile = comparisonFileElement ? comparisonFileElement.files[0] : null;

        console.log('[RuleEditor] Date values:', {
            revisionDate,
            executionDate,
            comparisonFile: comparisonFile ? comparisonFile.name : 'none'
        });

        // 필수 항목 검증
        if (!revisionDate || !executionDate) {
            console.error('[RuleEditor] Missing required dates:', {
                revisionDate: revisionDate || 'empty',
                executionDate: executionDate || 'empty'
            });
            alert('개정일과 시행일자는 필수 입력사항입니다.');
            return;
        }

        // 수동 업로드 파일 또는 자동 생성 파일 확인
        if (!comparisonFile && !this.pendingComparisonFile) {
            alert('신구대비표 PDF 파일을 업로드하거나 자동 생성해주세요.');
            return;
        }

        // 수동 업로드 파일이 있으면 우선 사용
        if (comparisonFile) {
            this.pendingComparisonFile = comparisonFile;
        }
        console.log('[RuleEditor] 신구대비표 파일 준비됨:', comparisonFile.name);

        // 날짜 정보 저장 (DB 형식으로 변환: YYYY-MM-DD -> YYYY.MM.DD)
        this.revisionInfo = {
            revisionDate: this.formatDateForSave(revisionDate),
            executionDate: this.formatDateForSave(executionDate)
        };

        console.log('[RuleEditor] Revision info saved:', this.revisionInfo);

        // 개정판 생성 API 호출
        try {
            const response = await fetch(`/api/v1/rule/create-revision/${this.currentRule.id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    revision_date: this.formatDateForSave(revisionDate),
                    execution_date: this.formatDateForSave(executionDate)
                })
            });

            if (!response.ok) {
                throw new Error(`개정판 생성 실패: ${response.status}`);
            }

            const result = await response.json();
            console.log('[RuleEditor] Revision created:', result);

            if (result.success && result.rule_id) {
                // 새로 생성된 개정판의 ID로 currentRule 업데이트 (wzpubno는 기존 값 유지)
                const originalWzpubno = this.currentRule.wzpubno;
                const originalWzname = this.currentRule.wzname;
                this.currentRule.id = result.rule_id;
                this.currentRule.wzruleseq = result.rule_id;

                // 기존 wzpubno 정보가 있다면 유지
                if (originalWzpubno) {
                    this.currentRule.wzpubno = originalWzpubno;
                }
                if (originalWzname) {
                    this.currentRule.wzname = originalWzname;
                }

                console.log('[RuleEditor] 개정 모달 - 업데이트된 currentRule:', this.currentRule);

                // 신구대비표 파일이 있으면 업로드
                if (this.pendingComparisonFile) {
                    await this.uploadComparisonTable(result.rule_id, this.pendingComparisonFile);
                    this.pendingComparisonFile = null; // 업로드 후 초기화
                }

                this.showNotification('개정판이 생성되었습니다. 파일을 업로드해주세요.', 'success');

                // 날짜 모달 닫고 파일 업로드 모달 열기
                this.closeDateModal();
                this.showFileUploadModal('개정');
            } else {
                throw new Error('개정판 ID를 받지 못했습니다.');
            }

        } catch (error) {
            console.error('[RuleEditor] Error creating revision:', error);
            this.showNotification(`개정판 생성 실패: ${error.message}`, 'error');
        }
    },

    // 파일 업로드 모달 표시
    showFileUploadModal(mode) {
        // 기존 동적 모달 제거
        if (this.currentModal) {
            this.currentModal.remove();
            this.currentModal = null;
        }

        // HTML에 정적으로 존재하는 모든 모달 닫기
        const newModal = document.getElementById('newModal');
        if (newModal) {
            newModal.style.display = 'none';
        }

        // 기존 파일 업로드 모달 제거 (중복 방지)
        const existingFileUploadModal = document.getElementById('fileUploadModal');
        if (existingFileUploadModal) {
            existingFileUploadModal.remove();
        }

        // 모달 HTML 생성
        const modalHtml = `
            <div class="modal active" id="fileUploadModal">
                <div class="modal-content" style="max-width: 600px;">
                    <div class="modal-header">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <button onclick="RuleEditor.backToNewModal()" style="background: #f0f0f0; border: 1px solid #ccc; border-radius: 6px; padding: 6px 14px; cursor: pointer; font-size: 13px; font-weight: 600; color: #555; display: inline-flex; align-items: center; gap: 4px; transition: background 0.2s;" onmouseover="this.style.background='#e0e0e0'" onmouseout="this.style.background='#f0f0f0'">&larr; 제정</button>
                            <h2 style="margin: 0;">내규 ${mode} - 파일 업로드</h2>
                        </div>
                        <button class="modal-close" onclick="RuleEditor.closeModal()">✕</button>
                    </div>
                    <div class="modal-body">
                        <div class="upload-section">
                            <p class="info-text">DOCX 파일을 업로드해주세요.</p>

                            <!-- DOCX 업로드 -->
                            <div class="form-group">
                                <label class="form-label">DOCX 파일 <span class="required">*</span></label>
                                <div class="file-upload-wrapper">
                                    <input type="file" id="docxFile" accept=".docx" onchange="RuleEditor.handleFileSelectOld('docx', this)">
                                    <div id="docxFileName" class="file-name-display">파일을 선택하세요</div>
                                </div>
                                <div id="docxStatus" class="upload-status"></div>
                            </div>

                            <!-- 진행 상황 표시 -->
                            <div id="uploadProgress" class="progress-section" style="display: none;">
                                <div class="progress-bar">
                                    <div class="progress-fill" id="progressBar"></div>
                                </div>
                                <div id="progressText" class="progress-text"></div>
                            </div>

                            <!-- 버튼 영역 -->
                            <div class="modal-footer">
                                <button class="btn btn-secondary" onclick="RuleEditor.closeModal()">취소</button>
                                <button class="btn btn-primary" id="uploadBtn" onclick="RuleEditor.uploadFiles()" disabled>
                                    업로드 및 파싱
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 모달 추가
        const modalDiv = document.createElement('div');
        modalDiv.innerHTML = modalHtml;
        document.body.appendChild(modalDiv.firstElementChild);
        this.currentModal = document.getElementById('fileUploadModal');

        // 스타일 추가
        this.addModalStyles();
    },

    // 파일 업로드에서 제정 모달로 돌아가기
    backToNewModal() {
        // 파일 업로드 모달 닫기
        const fileUploadModal = document.getElementById('fileUploadModal');
        if (fileUploadModal) {
            fileUploadModal.remove();
        }
        this.currentModal = null;

        // 제정 모달 다시 열기
        const newModal = document.getElementById('newModal');
        if (newModal) {
            newModal.style.display = 'flex';
            newModal.classList.add('active');
        }
    },

    // 기존 파일 업로드 모달용 파일 선택 처리 (주석처리 - 중복 정의 제거)
    /*handleFileSelect_old(type, input) {
        const file = input.files[0];
        if (!file) return;

        console.log(`[RuleEditor] Selected ${type} file:`, file.name);

        // 파일 저장
        this.uploadedFiles[type] = file;

        // 파일명 표시
        document.getElementById(`${type}FileName`).textContent = file.name;

        // 상태 업데이트
        document.getElementById(`${type}Status`).innerHTML =
            '<span style="color: green;">✓ 파일 선택됨</span>';

        // 두 파일 모두 선택되었는지 확인
        this.checkUploadReady();
    },*/

    // 업로드 준비 확인
    checkUploadReady() {
        const uploadBtn = document.getElementById('uploadBtn');
        if (this.uploadedFiles.docx) {
            uploadBtn.disabled = false;
            uploadBtn.classList.add('btn-ready');
        } else {
            uploadBtn.disabled = true;
            uploadBtn.classList.remove('btn-ready');
        }
    },

    // 파일 업로드 및 파싱
    async uploadFiles() {
        if (!this.uploadedFiles.docx) {
            alert('DOCX 파일을 선택해주세요.');
            return;
        }

        console.log('[RuleEditor] Starting file upload and parsing...');

        // 진행 상황 표시
        this.showProgress('업로드 중...');

        try {
            // 1. DOCX 업로드 및 파싱
            const docxResult = await this.uploadAndParseDOCX();

            // 2. JSON 파일 병합
            this.showProgress('JSON 병합 중...');
            const mergeResult = await this.mergeJSONFiles(null, docxResult);

            // 4. RuleEditor 상태 업데이트 (내용편집 탭에서 사용)
            if (mergeResult && mergeResult.merged_data) {
                console.log('[RuleEditor] Updating RuleEditor state with merged data');
                this.existingJsonContent = mergeResult.merged_data;
                this.mergedJsonData = mergeResult.merged_data;
                this.mergedJsonPath = mergeResult.json_path || mergeResult.filepath;
                this.hasExistingJson = true;
                this.isNewUpload = true;  // 새 업로드 플래그
            }

            // 5. 파싱 완료 처리
            this.showProgress('파싱 완료!');

            // 성공 메시지
            this.showNotification('파일 업로드 및 파싱이 완료되었습니다.', 'success');

            // 업로드 모달 즉시 닫기
            this.closeModal();

            // 약간의 지연 후 자동 저장 실행
            setTimeout(async () => {
                // 병합된 데이터를 임시 저장
                this.mergedRevisionData = mergeResult;

                console.log('[RuleEditor] Auto-saving after upload and parsing...');

                // 개정 모드일 때 개정일/시행일 정보를 currentRule에 추가
                if (this.mode === 'revision' && this.revisionInfo) {
                    this.currentRule.wzlastrevdate = this.revisionInfo.revisionDate;
                    this.currentRule.wzexecdate = this.revisionInfo.executionDate;
                    console.log('[RuleEditor] Added revision dates to currentRule:', {
                        wzlastrevdate: this.currentRule.wzlastrevdate,
                        wzexecdate: this.currentRule.wzexecdate
                    });
                }

                // ===== 파싱 완료 후 자동 저장 =====
                try {
                    this.showProgress('자동 저장 중...');

                    const formData = new FormData();
                    formData.append('rule_id', this.currentRule.wzruleseq || this.currentRule.id || this.currentRule.rule_id);
                    formData.append('mode', this.mode);
                    formData.append('is_revision', this.mode === 'revision');

                    // 병합된 JSON 데이터 전송
                    if (this.mergedJsonData) {
                        formData.append('merged_json_data', JSON.stringify(this.mergedJsonData));
                        // 텍스트 내용도 생성
                        const textContent = this.convertJsonToText(this.mergedJsonData);
                        formData.append('content', textContent);
                    }

                    // 병합 JSON 경로
                    if (this.mergedJsonPath) {
                        formData.append('merged_json_path', this.mergedJsonPath);
                        formData.append('use_merged_json', 'true');
                    }

                    // 개정 모드인 경우 날짜 정보 추가
                    if (this.mode === 'revision' && this.revisionInfo) {
                        formData.append('revision_date', this.revisionInfo.revisionDate);
                        formData.append('execution_date', this.revisionInfo.executionDate);
                    }

                    console.log('[RuleEditor] Auto-saving with mode:', this.mode);

                    const response = await fetch('/api/v1/rule/save-edited-content', {
                        method: 'POST',
                        credentials: 'include',
                        body: formData
                    });

                    if (!response.ok) {
                        throw new Error('자동 저장 실패');
                    }

                    const result = await response.json();
                    console.log('[RuleEditor] Auto-save result:', result);

                    this.hideProgress();
                    this.showNotification('✅ 파싱 및 저장이 완료되었습니다!', 'success');

                    // 목록 새로고침
                    setTimeout(() => {
                        this.loadRegulations();

                        if (this.mode === 'new') {
                            this.showNotification('신규 내규가 성공적으로 제정되었습니다.', 'success');
                        } else if (this.mode === 'revision') {
                            this.showNotification('규정이 성공적으로 개정되었습니다.', 'success');
                        }
                    }, 1500);

                } catch (error) {
                    console.error('[RuleEditor] Auto-save error:', error);
                    this.hideProgress();
                    this.showNotification(`자동 저장 실패: ${error.message}`, 'error');

                    // 실패 시 수동 편집 모드로 전환
                    this.showNotification('수동으로 저장해주세요.', 'warning');

                    // 편집 모달창 열기
                    this.showEditTabbedModal();
                    setTimeout(() => {
                        this.switchEditTab('content');
                    }, 300);
                }
            }, 500);

        } catch (error) {
            console.error('[RuleEditor] Upload error:', error);
            this.showNotification(`업로드 실패: ${error.message}`, 'error');
            this.hideProgress();
        }
    },

    // 신구대비표 파일 업로드
    async uploadComparisonTable(ruleId, file) {
        console.log(`[RuleEditor] Uploading comparison table for rule ${ruleId}:`, file.name);

        try {
            const formData = new FormData();
            formData.append('comparison_file', file);

            const response = await fetch(`/api/v1/rule/upload-comparison-table/${ruleId}`, {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`신구대비표 업로드 실패: ${response.status}`);
            }

            const result = await response.json();
            console.log('[RuleEditor] Comparison table uploaded:', result);

            if (result.success) {
                this.showNotification('신구대비표가 업로드되었습니다.', 'success');
            }

            return result;

        } catch (error) {
            console.error('[RuleEditor] Comparison table upload error:', error);
            this.showNotification(`신구대비표 업로드 실패: ${error.message}`, 'error');
            throw error;
        }
    },

    // JSON 파일 병합
    async mergeJSONFiles(pdfResult, docxResult) {
        console.log('[RuleEditor] Merging JSON files...');
        console.log('[RuleEditor] PDF Result:', pdfResult);
        console.log('[RuleEditor] DOCX Result:', docxResult);

        // PDF와 DOCX 결과에서 JSON 파일 경로 추출
        const pdfJsonPath = pdfResult ? (pdfResult.json_path || pdfResult.filepath || pdfResult.path) : '';
        const docxJsonPath = docxResult.json_path || docxResult.filepath || docxResult.path;

        console.log('[RuleEditor] PDF JSON Path:', pdfJsonPath);
        console.log('[RuleEditor] DOCX JSON Path:', docxJsonPath);

        if (!docxJsonPath) {
            console.error('[RuleEditor] Missing DOCX JSON path');
            throw new Error('DOCX JSON 파일 경로를 찾을 수 없습니다');
        }

        const formData = new FormData();
        if (pdfJsonPath) {
            formData.append('pdf_json_path', pdfJsonPath);
        }
        formData.append('docx_json_path', docxJsonPath);
        // rule_id 확인 및 설정
        const ruleId = this.currentRule.wzruleseq || this.currentRule.rule_id || this.currentRule.id;
        console.log('[RuleEditor] Merging with rule_id:', ruleId);
        formData.append('rule_id', ruleId);

        console.log('[RuleEditor] Sending merge request with:', {
            pdf_json_path: pdfJsonPath,
            docx_json_path: docxJsonPath,
            rule_id: this.currentRule.id
        });

        try {
            const response = await fetch('/api/v1/rule/merge-json', {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            console.log('[RuleEditor] Merge response status:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[RuleEditor] Merge error response:', errorText);

                let errorDetail = 'JSON 병합 실패';
                try {
                    const errorJson = JSON.parse(errorText);
                    errorDetail = errorJson.detail || errorDetail;
                } catch (e) {
                    errorDetail = errorText || errorDetail;
                }

                throw new Error(errorDetail);
            }

            const result = await response.json();
            console.log('[RuleEditor] Merge result:', result);

            return result;
        } catch (error) {
            console.error('[RuleEditor] Merge request failed:', error);
            throw error;
        }
    },

    // 병합된 내용으로 편집 모달 열기
    openEditModalWithContent(mergeResult) {
        console.log('[RuleEditor] Opening edit modal with merged content');
        console.log('[RuleEditor] Current active tab:', document.querySelector('.nav-tab.active')?.textContent);

        // 모든 기존 모달 닫기 (classification, department 등)
        const existingModals = document.querySelectorAll('.modal.active');
        existingModals.forEach(modal => {
            console.log('[RuleEditor] Closing existing modal:', modal.id);
            modal.classList.remove('active');
        });

        // 기존 편집 모달 제거
        if (this.currentModal) {
            this.currentModal.remove();
        }

        // regulation 탭이 활성화되어 있는지 확인
        const regulationTab = document.querySelector('.nav-tab.active');
        const isRegulationTabActive = regulationTab && regulationTab.onclick &&
                                      regulationTab.onclick.toString().includes("'regulation'");

        // regulation 탭이 아니면 활성화
        if (!isRegulationTabActive) {
            console.log('[RuleEditor] Ensuring regulation tab is active');
            // regulation 탭 버튼 찾기
            const regulationButton = Array.from(document.querySelectorAll('.nav-tab'))
                .find(btn => btn.onclick && btn.onclick.toString().includes("'regulation'"));

            if (regulationButton) {
                // 모든 탭 비활성화
                document.querySelectorAll('.nav-tab').forEach(btn => btn.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

                // regulation 탭 활성화
                regulationButton.classList.add('active');
                const regulationContent = document.getElementById('regulationTab');
                if (regulationContent) regulationContent.classList.add('active');
            }
        }

        // 편집 모달 생성 (z-index를 높게 설정)
        const modalHtml = `
            <div class="modal active" id="editContentModal" style="z-index: 2000;">
                <div class="modal-content" style="max-width: 90%; height: 90%;">
                    <div class="modal-header">
                        <h2>내규 ${this.mode === 'new' ? '제정' : this.mode === 'edit' ? '편집' : '개정'} - 내용 편집</h2>
                        <button class="modal-close" onclick="RuleEditor.closeEditContentModal()">✕</button>
                    </div>
                    <div class="modal-body" style="display: flex; height: calc(100% - 120px);">
                        <!-- 미리보기 영역 -->
                        <div class="preview-section" style="flex: 1; padding: 20px; overflow-y: auto; border-right: 1px solid #ddd;">
                            <h3>미리보기</h3>
                            <div id="previewContent" style="white-space: pre-wrap; line-height: 1.8;">
                                ${this.formatPreviewContent(mergeResult.merged_data)}
                            </div>
                        </div>

                        <!-- 편집 영역 -->
                        <div class="edit-section" style="flex: 1; padding: 20px; overflow-y: auto;">
                            <h3>편집</h3>
                            <textarea id="editContentArea" style="width: 100%; height: calc(100% - 40px); padding: 10px; font-size: 14px; line-height: 1.8; border: 1px solid #ddd; border-radius: 4px;">
${mergeResult.text_content || ''}
                            </textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="RuleEditor.closeEditContentModal()">취소</button>
                        <button class="btn btn-warning" onclick="RuleEditor.refreshPreview()">미리보기 새로고침</button>
                        <button class="btn btn-primary" onclick="RuleEditor.saveEditedContent()">저장</button>
                    </div>
                </div>
            </div>
        `;

        // 모달 추가
        const modalDiv = document.createElement('div');
        modalDiv.innerHTML = modalHtml;
        document.body.appendChild(modalDiv.firstElementChild);
        this.currentModal = document.getElementById('editContentModal');

        // 병합 결과 저장
        this.mergedData = mergeResult;

        // 실시간 편집 이벤트 추가
        const editArea = document.getElementById('editContentArea');
        if (editArea) {
            editArea.addEventListener('input', () => {
                this.updatePreviewInRealtime();
            });
        }
    },

    // 미리보기 내용 포맷팅
    formatPreviewContent(mergedData) {
        let html = '';

        if (mergedData && mergedData['조문내용']) {
            mergedData['조문내용'].forEach(article => {
                if (typeof article === 'object') {
                    const number = article['번호'] || '';
                    const content = article['내용'] || '';
                    const level = article['레벨'] || 1;

                    const indent = '  '.repeat(level - 1);

                    if (number && content) {
                        html += `<div style="margin: 10px 0; padding-left: ${level * 20}px;">
                                   <strong>${number}</strong> ${content}
                                 </div>`;
                    } else if (content) {
                        html += `<div style="margin: 5px 0; padding-left: ${level * 20}px;">${content}</div>`;
                    }
                }
            });
        }

        return html || '<p>미리보기 내용이 없습니다.</p>';
    },

    // 실시간 미리보기 업데이트
    updatePreviewInRealtime() {
        const editArea = document.getElementById('editContentArea');
        const previewContent = document.getElementById('previewContent');

        if (editArea && previewContent) {
            const lines = editArea.value.split('\n');
            let html = '';

            lines.forEach(line => {
                if (line.trim()) {
                    // 조문 번호 패턴 감지
                    if (line.match(/^제\d+조/)) {
                        html += `<div style="margin: 15px 0;"><strong>${line}</strong></div>`;
                    } else if (line.match(/^[①-⑩]/)) {
                        html += `<div style="margin: 8px 0; padding-left: 20px;">${line}</div>`;
                    } else if (line.match(/^\d+\./)) {
                        html += `<div style="margin: 5px 0; padding-left: 40px;">${line}</div>`;
                    } else {
                        html += `<div style="margin: 5px 0;">${line}</div>`;
                    }
                }
            });

            previewContent.innerHTML = html || '<p>내용을 입력하세요.</p>';
        }
    },

    // 미리보기 새로고침
    refreshPreview() {
        this.updatePreviewInRealtime();
        this.showNotification('미리보기가 새로고침되었습니다.', 'info');
    },

    // 편집된 내용 저장
    async saveEditedContent() {
        // 두 가지 ID 모두 체크 (editContentArea는 파일 업로드 후, contentEditor는 탭에서 사용)
        let editArea = document.getElementById('contentEditor');
        let isTableEditor = false;

        if (editArea && !editArea.value) {
            // contentEditor가 div(테이블 형식)인 경우
            isTableEditor = true;
        } else if (!editArea) {
            // contentEditor가 없으면 editContentArea(textarea) 찾기
            editArea = document.getElementById('editContentArea');
        }

        if (!editArea) {
            console.error('[RuleEditor] Content editor not found (tried contentEditor and editContentArea)');
            this.showNotification('편집 영역을 찾을 수 없습니다.', 'error');
            return;
        }

        let editedContent = '';
        let updatedJsonData = null;

        if (isTableEditor) {
            // 테이블 형식: JSON 데이터 수집
            console.log('[RuleEditor] Using table editor mode - collecting JSON data');
            if (!this.existingJsonContent) {
                this.showNotification('편집할 내용이 없습니다.', 'error');
                return;
            }
            updatedJsonData = this.collectArticleUpdates(this.existingJsonContent);
            if (!updatedJsonData) {
                this.showNotification('수정 내용을 수집할 수 없습니다.', 'error');
                return;
            }
            // 텍스트 내용도 생성 (백엔드 호환성)
            editedContent = this.convertJsonToText(updatedJsonData);
        } else {
            // textarea 형식: 텍스트 직접 사용
            console.log('[RuleEditor] Using textarea editor mode');
            editedContent = editArea.value;
            if (!editedContent.trim()) {
                this.showNotification('내용을 입력해주세요.', 'warning');
                return;
            }
        }

        try {
            // 편집된 내용을 서버에 저장
            const formData = new FormData();
            // wzruleseq 사용 (올바른 필드명)
            formData.append('rule_id', this.currentRule.wzruleseq || this.currentRule.id || this.currentRule.rule_id);
            formData.append('content', editedContent);
            formData.append('mode', this.mode);
            formData.append('is_revision', this.mode === 'revision');

            // 파일 업로드를 통해 생성된 병합 JSON이 있는 경우, 해당 경로 전송
            if (this.mergedJsonPath) {
                formData.append('merged_json_path', this.mergedJsonPath);
                formData.append('use_merged_json', 'true');
                console.log('[RuleEditor] Using merged JSON from file upload:', this.mergedJsonPath);
            }

            // 병합된 JSON 데이터가 있는 경우 전송
            // 테이블 편집기에서 업데이트된 JSON이 있으면 우선 사용
            if (updatedJsonData) {
                formData.append('merged_json_data', JSON.stringify(updatedJsonData));
                console.log('[RuleEditor] Sending updated JSON from table editor');
            } else if (this.mergedJsonData) {
                formData.append('merged_json_data', JSON.stringify(this.mergedJsonData));
            }

            // 개정 모드인 경우 날짜 정보 추가
            if (this.mode === 'revision' && this.revisionInfo) {
                formData.append('revision_date', this.revisionInfo.revisionDate);
                formData.append('execution_date', this.revisionInfo.executionDate);
                console.log('[RuleEditor] Sending revision dates:', this.revisionInfo);
            }

            console.log('[RuleEditor] Saving content for rule:', this.currentRule.id);
            console.log('[RuleEditor] Mode:', this.mode);
            console.log('[RuleEditor] Is revision:', this.mode === 'revision');

            const response = await fetch('/api/v1/rule/save-edited-content', {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            console.log('[RuleEditor] Save response status:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[RuleEditor] Save error response:', errorText);

                let errorDetail = '저장 실패';
                try {
                    const errorJson = JSON.parse(errorText);
                    errorDetail = errorJson.detail || errorDetail;
                } catch (e) {
                    errorDetail = errorText || errorDetail;
                }

                throw new Error(errorDetail);
            }

            const result = await response.json();
            console.log('[RuleEditor] Save result:', result);

            // 백엔드에서 반환한 메시지 사용 (백그라운드 병합 안내 포함)
            let message = result.message || '✅ 저장 완료 (백그라운드에서 병합 중)';
            if (result.files && result.files.json_filepath) {
                console.log('[RuleEditor] JSON file saved:', result.files.json_filepath);
            }

            this.showNotification(message, 'success');

            // 모든 모드에서 목록 새로고침
            setTimeout(() => {
                this.closeEditContentModal();
                this.loadRegulations();

                // 제정 모드인 경우 추가 메시지
                if (this.mode === 'new') {
                    this.showNotification('신규 내규가 성공적으로 제정되었습니다.', 'success');
                }
            }, 1500);

        } catch (error) {
            console.error('[RuleEditor] Save error:', error);
            this.showNotification(`저장 실패: ${error.message}`, 'error');
        }
    },

    // 편집 모달 닫기
    closeEditContentModal() {
        if (this.currentModal) {
            this.currentModal.remove();
            this.currentModal = null;
        }
        this.mergedData = null;
    },

    // PDF 업로드 및 파싱
    async uploadAndParsePDF() {
        const formData = new FormData();
        formData.append('pdf_file', this.uploadedFiles.pdf);
        // rule_id 확인 및 로그
        const ruleId = this.currentRule.wzruleseq || this.currentRule.rule_id || this.currentRule.id;
        console.log('[RuleEditor] Uploading PDF for rule:', ruleId);
        console.log('[RuleEditor] Current rule object:', this.currentRule);
        formData.append('rule_id', ruleId);

        this.showProgress('PDF 파일 업로드 중...');

        const response = await fetch('/api/v1/rule/upload-parse-pdf', {
            method: 'POST',
            credentials: 'include',
            body: formData
        });

        if (!response.ok) {
            throw new Error('PDF 업로드 실패');
        }

        const result = await response.json();
        console.log('[RuleEditor] PDF parsing result:', result);

        this.parsingResults.pdf = result;
        this.showProgress('PDF 파싱 완료');

        return result;
    },

    // DOCX 업로드 및 파싱
    async uploadAndParseDOCX() {
        const formData = new FormData();
        formData.append('docx_file', this.uploadedFiles.docx);
        // rule_id 확인 및 로그
        const ruleId = this.currentRule.wzruleseq || this.currentRule.rule_id || this.currentRule.id;
        console.log('[RuleEditor] Uploading DOCX for rule:', ruleId);
        formData.append('rule_id', ruleId);

        this.showProgress('DOCX 파일 업로드 중...');

        const response = await fetch('/api/v1/rule/upload-parse-docx', {
            method: 'POST',
            credentials: 'include',
            body: formData
        });

        if (!response.ok) {
            throw new Error('DOCX 업로드 실패');
        }

        const result = await response.json();
        console.log('[RuleEditor] DOCX parsing result:', result);

        this.parsingResults.docx = result;
        this.showProgress('DOCX 파싱 완료');

        return result;
    },

    // 진행 상황 표시
    showProgress(message) {
        const progressSection = document.getElementById('uploadProgress');
        const progressText = document.getElementById('progressText');

        if (progressSection) {
            progressSection.style.display = 'block';
            progressText.textContent = message;
        }
    },

    // 진행 상황 숨기기
    hideProgress() {
        const progressSection = document.getElementById('uploadProgress');
        if (progressSection) {
            progressSection.style.display = 'none';
        }
    },

    // 알림 표시
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 4px;
            z-index: 10000;
            animation: slideIn 0.3s;
        `;

        // 타입별 색상
        const colors = {
            success: '#4CAF50',
            error: '#f44336',
            info: '#2196F3',
            warning: '#ff9800'
        };

        notification.style.backgroundColor = colors[type] || colors.info;
        notification.style.color = 'white';

        document.body.appendChild(notification);

        // 3초 후 제거
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    },

    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;')
            .replace(/`/g, '&#096;');
    },

    // 모달 닫기
    closeModal() {
        if (this.currentModal) {
            this.currentModal.remove();
            this.currentModal = null;
        }

        // 상태 초기화
        this.uploadedFiles = { pdf: null, docx: null };
        this.parsingResults = { pdf: null, docx: null };

        // 단축키 제거
        this.disableSaveShortcut();
    },

    // 날짜 포맷
    formatDate(dateString) {
        if (!dateString) return '-';

        try {
            const date = new Date(dateString);
            // 날짜 끝에 마침표 포함: 예) 2007.4.1. 또는 2025.3.25.
            return date.toLocaleDateString('ko-KR').replace(/\. /g, '.');
        } catch {
            return dateString;
        }
    },

    // 탭 전환
    switchTab(tabName) {
        console.log('[RuleEditor] Switching to tab:', tabName);

        // 모든 탭 버튼과 컨텐츠 비활성화
        document.querySelectorAll('.nav-tab').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        // 클릭된 버튼 찾기 - onclick 속성에서 탭 이름 매칭
        const allNavTabs = document.querySelectorAll('.nav-tab');
        let selectedButton = null;
        allNavTabs.forEach(btn => {
            if (btn.onclick && btn.onclick.toString().includes(`'${tabName}'`)) {
                selectedButton = btn;
            }
        });

        // 선택된 탭 컨텐츠 찾기
        const selectedContent = document.getElementById(`${tabName}Tab`);

        if (selectedButton) selectedButton.classList.add('active');
        if (selectedContent) {
            selectedContent.classList.add('active');

            // 스크롤을 맨 위로 리셋
            // 1. 전체 페이지 스크롤 리셋
            window.scrollTo(0, 0);
            document.documentElement.scrollTop = 0;
            document.body.scrollTop = 0;

            // 2. content-area 스크롤 리셋
            const contentArea = document.querySelector('.content-area');
            if (contentArea) {
                contentArea.scrollTop = 0;
            }

            // 3. 선택된 탭 컨텐츠 스크롤 리셋
            selectedContent.scrollTop = 0;

            // 4. main-container 스크롤 리셋
            const mainContainer = document.querySelector('.main-container');
            if (mainContainer) {
                mainContainer.scrollTop = 0;
            }

            // 디버깅용 로그
            console.log('[RuleEditor] Scroll reset attempted for:', tabName);
            console.log('Window scrollY:', window.scrollY);
            console.log('Document scrollTop:', document.documentElement.scrollTop);
            console.log('Body scrollTop:', document.body.scrollTop);
            if (contentArea) console.log('Content-area scrollTop:', contentArea.scrollTop);
            if (selectedContent) console.log('Selected content scrollTop:', selectedContent.scrollTop);

            // DOM 업데이트 후 다시 스크롤 리셋 (비동기 처리)
            setTimeout(() => {
                window.scrollTo(0, 0);
                document.documentElement.scrollTop = 0;
                document.body.scrollTop = 0;

                if (contentArea) {
                    contentArea.scrollTop = 0;
                }
                if (selectedContent) {
                    selectedContent.scrollTop = 0;
                }
                if (mainContainer) {
                    mainContainer.scrollTop = 0;
                }

                // 모든 스크롤 가능한 요소 찾아서 리셋
                document.querySelectorAll('*').forEach(element => {
                    if (element.scrollTop > 0) {
                        console.log('[RuleEditor] Found scrolled element:', element.className || element.tagName, 'scrollTop:', element.scrollTop);
                        element.scrollTop = 0;
                    }
                });

                console.log('[RuleEditor] Async scroll reset completed');
            }, 100);
        }

        // 각 탭별 초기화
        switch(tabName) {
            case 'department':
                if (typeof DepartmentManager !== 'undefined') {
                    DepartmentManager.init();
                }
                break;
            case 'classification':
                if (typeof ClassificationManager !== 'undefined') {
                    ClassificationManager.loadData();
                }
                break;
            case 'elasticsearch':
                if (typeof SearchEngine !== 'undefined') {
                    SearchEngine.init();
                }
                break;
            case 'service':
                if (typeof ServiceManager !== 'undefined') {
                    ServiceManager.loadStatus();
                }
                break;
            case 'notices':
                if (typeof NoticeManager !== 'undefined') NoticeManager.init();
                break;
            case 'faq':
                if (typeof FAQManager !== 'undefined') FAQManager.init();
                break;
            case 'support':
                if (typeof SupportTabManager !== 'undefined') SupportTabManager.init();
                break;
            case 'synonyms':
                if (typeof SynonymTabManager !== 'undefined') SynonymTabManager.init();
                break;
            case 'comparison':
                this.initComparisonTab();
                break;
            case 'users':
                if (typeof UserManager !== 'undefined') UserManager.init();
                break;
            case 'search':
                // 상세 검색 탭 초기화
                this.initAdvancedSearch();
                break;
        }
    },

    // 신구대비표 탭 초기화
    initComparisonTab(ruleId) {
        const iframe = document.getElementById('comparisonIframe');
        if (!iframe) return;

        let url = '/regulations/comparison-generator?embed=1';
        if (ruleId) {
            url += `&rule_id=${ruleId}`;
        }

        // iframe이 아직 로드되지 않았거나 다른 rule_id로 요청된 경우만 로드
        if (!iframe.src || iframe.src === '' || iframe.src === 'about:blank' || (ruleId && !iframe.src.includes(`rule_id=${ruleId}`))) {
            iframe.src = url;
        }
    },

    // 신구대비표 새 탭에서 열기
    openComparisonInNewTab() {
        window.open('/regulations/comparison-generator', '_blank');
    },

    // 버전 비교 뷰어 열기
    openVersionCompare() {
        window.open('/regulations/compare', '_blank');
    },

    // 특정 규정의 신구대비표 탭으로 이동
    openComparisonForRule(ruleId) {
        this.switchTab('comparison');
        // iframe에 rule_id 전달
        this.initComparisonTab(ruleId);
    },

    // 개정 모달에서 신구대비표 자동 생성
    async autoGenerateComparison() {
        const ruleId = this.currentRule?.id;
        if (!ruleId) {
            alert('규정이 선택되지 않았습니다.');
            return;
        }

        const pdfFile = document.getElementById('autoGenPdfFile')?.files[0];
        const docxFile = document.getElementById('autoGenDocxFile')?.files[0];

        if (!docxFile) {
            alert('신구대비표 자동 생성에는 새 버전의 DOCX 파일이 필요합니다.');
            return;
        }

        const statusDiv = document.getElementById('autoGenStatus');
        const btn = document.getElementById('btnAutoGenerate');
        if (statusDiv) statusDiv.innerHTML = '<span style="color: #667eea;">신구대비표 생성 중...</span>';
        if (btn) btn.disabled = true;

        try {
            const formData = new FormData();
            formData.append('rule_id', ruleId);
            formData.append('output_format', 'pdf');
            formData.append('remarks', '개정 시 자동 생성');
            if (pdfFile) formData.append('pdf_file', pdfFile);
            if (docxFile) formData.append('docx_file', docxFile);

            const response = await fetch('/api/v1/compare/generate-download', {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `생성 실패 (${response.status})`);
            }

            // 생성된 PDF를 Blob으로 받아서 File 객체로 변환
            const blob = await response.blob();
            const ruleName = this.currentRule?.name || '규정';
            const generatedFile = new File([blob], `신구대비표_${ruleName}.pdf`, { type: 'application/pdf' });

            // 수동 업로드 필드에 자동 설정
            const comparisonInput = document.getElementById('revisionComparisonFile');
            if (comparisonInput) {
                // File input은 직접 설정 불가하므로 pendingComparisonFile에 저장
                this.pendingComparisonFile = generatedFile;
            }

            if (statusDiv) {
                statusDiv.innerHTML = `<span style="color: #28a745;">✅ 신구대비표 생성 완료: ${generatedFile.name} (${(generatedFile.size / 1024).toFixed(1)}KB)</span>`;
            }

            // 수동 업로드 필드의 필수 해제 (자동 생성으로 대체)
            if (comparisonInput) {
                comparisonInput.removeAttribute('required');
            }

            this.showNotification('신구대비표가 자동 생성되었습니다.', 'success');
        } catch (error) {
            console.error('[RuleEditor] Auto-generate comparison failed:', error);
            if (statusDiv) {
                statusDiv.innerHTML = `<span style="color: #dc3545;">❌ 생성 실패: ${error.message}</span>`;
            }
            this.showNotification(`신구대비표 생성 실패: ${error.message}`, 'error');
        } finally {
            if (btn) btn.disabled = false;
        }
    },

    // 상세 검색 초기화
    initAdvancedSearch() {
        // 부서 목록 로드
        this.loadDepartmentForSearch();

        // 검색 버튼에 이벤트 연결
        const searchBtn = document.querySelector('#searchTab .btn-primary');
        if (searchBtn && !searchBtn.hasAttribute('data-listener')) {
            searchBtn.setAttribute('data-listener', 'true');
            searchBtn.onclick = () => this.performAdvancedSearch();
        }

        // 초기화 버튼에 이벤트 연결
        const resetBtn = document.querySelector('#searchTab .btn-secondary');
        if (resetBtn && !resetBtn.hasAttribute('data-listener')) {
            resetBtn.setAttribute('data-listener', 'true');
            resetBtn.onclick = () => this.resetAdvancedSearch();
        }
    },

    // 상세 검색용 부서 목록 로드
    async loadDepartmentForSearch() {
        try {
            const response = await fetch('/api/v1/dept/list', {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch departments');
            }

            const result = await response.json();
            console.log('[RuleEditor] Loaded departments for search:', result);

            const select = document.getElementById('searchDepartment');
            if (select) {
                select.innerHTML = '<option value="">전체</option>';
                if (result.data && Array.isArray(result.data)) {
                    result.data.forEach(dept => {
                        const option = document.createElement('option');
                        option.value = dept.name || dept.wzdeptnm;
                        option.textContent = dept.name || dept.wzdeptnm;
                        select.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.error('[RuleEditor] Error loading departments for search:', error);
        }
    },

    // 상세 검색 수행
    async performAdvancedSearch() {
        console.log('[RuleEditor] Performing advanced search...');

        const searchData = {
            search: document.getElementById('searchKeyword')?.value || '',
            department: document.getElementById('searchDepartment')?.value || '',
            announce_start: document.getElementById('searchDateFrom')?.value || '',
            announce_end: document.getElementById('searchDateTo')?.value || '',
            status: document.getElementById('searchStatus')?.value || ''
        };

        console.log('[RuleEditor] Search criteria:', searchData);

        try {
            const queryParams = new URLSearchParams();
            for (const [key, value] of Object.entries(searchData)) {
                if (value) queryParams.append(key, value);
            }

            const response = await fetch(`/api/v1/regulations/advanced-search?${queryParams}`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Search failed');
            }

            const result = await response.json();
            console.log('[RuleEditor] Search results:', result);

            // 검색 결과 표시
            if (result.data) {
                this.displaySearchResults(result.data);
            }
        } catch (error) {
            console.error('[RuleEditor] Search error:', error);
            alert('검색 중 오류가 발생했습니다.');
        }
    },

    // 검색 결과 표시
    displaySearchResults(results) {
        const resultsContainer = document.getElementById('searchResults');
        if (!resultsContainer) return;

        if (results.length === 0) {
            resultsContainer.innerHTML = '<p>검색 결과가 없습니다.</p>';
            return;
        }

        let html = '<table class="search-results-table"><thead><tr>';
        html += '<th>분류번호</th><th>제목</th><th>부서</th><th>제정일</th><th>상태</th>';
        html += '</tr></thead><tbody>';

        results.forEach(item => {
            html += '<tr>';
            html += `<td>${item.publication_no || '-'}</td>`;
            html += `<td>${item.name || '-'}</td>`;
            html += `<td>${item.department || '-'}</td>`;
            html += `<td>${this.formatDate(item.established_date)}</td>`;
            html += `<td>${item.status || '현행'}</td>`;
            html += '</tr>';
        });

        html += '</tbody></table>';
        resultsContainer.innerHTML = html;
    },

    // 상세 검색 초기화
    resetAdvancedSearch() {
        console.log('[RuleEditor] Resetting advanced search...');

        document.getElementById('searchKeyword').value = '';
        document.getElementById('searchDepartment').value = '';
        document.getElementById('searchDateFrom').value = '';
        document.getElementById('searchDateTo').value = '';
        document.getElementById('searchStatus').value = '';

        const resultsContainer = document.getElementById('searchResults');
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
        }
    },

    // 신규 내규 모달 열기
    async openNewModal() {
        console.log('[RuleEditor] Opening new regulation modal');
        const modal = document.getElementById('newModal');
        if (modal) {
            modal.style.display = 'block';

            // 부서 목록 초기화
            this.departments = [];

            // 분류 선택 드롭다운 로드
            await this.loadClassificationsForNew();

            // 부서 목록 로드
            await this.loadDepartmentsForNew();

            // 검색 이벤트 바인딩 (이미 바인딩되어 있는지 확인)
            const searchInput = document.getElementById('deptSearchInput');
            if (searchInput && !searchInput.hasAttribute('data-initialized')) {
                this.initDepartmentSearch();
                searchInput.setAttribute('data-initialized', 'true');
            }
        }
    },

    // 분류 목록 로드 (제정 모달용)
    async loadClassificationsForNew() {
        try {
            const response = await fetch('/api/v1/classification/list', {
                method: 'GET',
                credentials: 'include'
            });
            if (response.ok) {
                const result = await response.json();
                const select = document.getElementById('newClassification');
                if (select && result.success && result.classifications) {
                    while (select.options.length > 1) select.remove(1);
                    result.classifications.forEach(c => {
                        const option = document.createElement('option');
                        option.value = c.id;
                        option.textContent = `${c.id}. ${c.name}`;
                        select.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.error('[RuleEditor] Error loading classifications for new:', error);
        }
    },

    // 분류 선택 시 분류번호 자동 생성
    async autoGeneratePublicationNo() {
        const select = document.getElementById('newClassification');
        const pubNoInput = document.getElementById('newPublicationNo');
        if (!select || !pubNoInput) return;

        const cateId = select.value;
        if (!cateId) {
            pubNoInput.value = '';
            return;
        }

        // 해당 분류의 기존 내규 번호 중 최대값을 찾아 +1
        try {
            const response = await fetch('/api/v1/classification/list', {
                method: 'GET',
                credentials: 'include'
            });
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.classifications) {
                    const cate = result.classifications.find(c => String(c.id) === String(cateId));
                    const nextNum = cate ? (cate.count || 0) + 1 : 1;
                    pubNoInput.value = `${cateId}-${nextNum}`;
                }
            }
        } catch (error) {
            pubNoInput.value = `${cateId}-1`;
        }
    },

    // 부서 목록 로드 (제정 모달용)
    async loadDepartmentsForNew() {
        try {
            const response = await fetch('/api/v1/dept/list', {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch departments');
            }

            const result = await response.json();
            console.log('[RuleEditor] Loaded departments:', result);

            if (result.success) {
                // departments 배열을 정확히 가져옴
                this.departments = result.departments || result.data || [];
                console.log('[RuleEditor] Departments array:', this.departments);
                this.renderDepartmentDropdown();
            }
        } catch (error) {
            console.error('[RuleEditor] Error loading departments:', error);
        }
    },

    // 부서 드롭다운 렌더링
    renderDepartmentDropdown(filterText = '') {
        const dropdown = document.getElementById('deptDropdown');
        if (!dropdown) return;

        // 부서 배열이 없으면 빈 배열 사용
        if (!this.departments || this.departments.length === 0) {
            dropdown.innerHTML = '<div class="no-results">부서 목록을 불러오는 중...</div>';
            return;
        }

        const filtered = this.departments.filter(dept => {
            // API 응답 구조에 맞게 필드명 수정
            const name = dept.name || dept.wzdeptnm || dept.wzdeptname || '';
            const code = dept.code || dept.wzdeptorgcd || '';
            const searchText = filterText.toLowerCase();
            return name.toLowerCase().includes(searchText) ||
                   code.toLowerCase().includes(searchText);
        });

        if (filtered.length === 0) {
            dropdown.innerHTML = '<div class="no-results">검색 결과가 없습니다</div>';
            return;
        }

        dropdown.innerHTML = filtered.map(dept => {
            // API 응답 구조에 맞게 필드명 수정
            const name = dept.name || dept.wzdeptnm || dept.wzdeptname || '';
            const code = dept.code || dept.wzdeptorgcd || '';
            return `
                <div class="dept-item" data-code="${code}" data-name="${name}">
                    <span class="dept-name">${name}</span>
                    <span class="dept-code">${code}</span>
                </div>
            `;
        }).join('');

        // 클릭 이벤트 바인딩
        dropdown.querySelectorAll('.dept-item').forEach(item => {
            item.addEventListener('click', () => {
                const code = item.dataset.code;
                const name = item.dataset.name;
                this.selectDepartment(code, name);
            });
        });
    },

    // 부서 선택
    selectDepartment(code, name) {
        const searchInput = document.getElementById('deptSearchInput');
        const hiddenInput = document.getElementById('selectedDeptCode');
        const dropdown = document.getElementById('deptDropdown');
        const selectElement = document.getElementById('newDepartment');

        if (searchInput) searchInput.value = name;
        if (hiddenInput) hiddenInput.value = code;
        if (selectElement) {
            // hidden select에도 값 설정 (폼 제출용)
            selectElement.innerHTML = `<option value="${name}" selected>${name}</option>`;
            selectElement.value = name;
        }
        if (dropdown) dropdown.style.display = 'none';
    },

    // 부서 검색 초기화
    initDepartmentSearch() {
        const searchInput = document.getElementById('deptSearchInput');
        const dropdown = document.getElementById('deptDropdown');

        if (!searchInput || !dropdown) return;

        // 포커스 시 드롭다운 표시
        searchInput.addEventListener('focus', () => {
            console.log('[RuleEditor] Search input focused, departments:', this.departments);
            dropdown.style.display = 'block';
            this.renderDepartmentDropdown(searchInput.value);
        });

        // 입력 시 필터링
        searchInput.addEventListener('input', (e) => {
            console.log('[RuleEditor] Search input changed:', e.target.value);
            dropdown.style.display = 'block'; // 드롭다운 표시 유지
            this.renderDepartmentDropdown(e.target.value);
        });

        // 외부 클릭 시 드롭다운 숨기기
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.searchable-select-wrapper')) {
                dropdown.style.display = 'none';
            }
        });
    },

    // 신규 내규 모달 닫기
    closeNewModal() {
        console.log('[RuleEditor] Closing new regulation modal');
        const modal = document.getElementById('newModal');
        if (modal) {
            modal.style.display = 'none';
        }
    },

    // 신규 내규 생성
    async createNew() {
        console.log('[RuleEditor] Creating new regulation');

        // 폼 데이터 수집
        const formData = {
            name: document.getElementById('newRegulationName')?.value,
            publication_no: document.getElementById('newPublicationNo')?.value,
            department: document.getElementById('newDepartment')?.value,
            department_code: document.getElementById('selectedDeptCode')?.value,
            // 날짜는 DB 형식(YYYY.MM.DD)으로 변환하여 저장
            established_date: this.formatDateForSave(document.getElementById('newEstablishedDate')?.value || ''),
            execution_date: this.formatDateForSave(document.getElementById('newExecutionDate')?.value || ''),
            status: document.getElementById('newStatus')?.value || '현행'  // 현행/연혁 구분
        };

        // 수정 이력파일 가져오기
        const historyFileInput = document.getElementById('newHistoryFile');
        const historyFile = historyFileInput ? historyFileInput.files[0] : null;

        // 필수 필드 확인
        if (!formData.name || !formData.publication_no || !formData.department) {
            alert('제목, 분류번호, 소관부서는 필수 입력사항입니다.');
            return;
        }

        // ===== 분류번호 중복 체크 =====
        const publicationNo = formData.publication_no.trim();
        const isDuplicate = this.regulations.some(reg => {
            const existingNo = (reg.publication_no || '').trim();
            return existingNo === publicationNo;
        });

        if (isDuplicate) {
            alert(`⚠️ 중복 등록 불가\n\n분류번호 "${publicationNo}"는 이미 등록되어 있습니다.\n다른 분류번호를 사용해주세요.`);
            return;
        }

        try {
            const response = await fetch('/api/v1/rule/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                // 백엔드 에러 메시지 추출
                const errorData = await response.json().catch(() => null);
                const errorMessage = errorData?.detail || '신규 내규 생성 실패';
                throw new Error(errorMessage);
            }

            const result = await response.json();
            console.log('[RuleEditor] New regulation created:', result);

            if (result.rule_id) {
                // 신규 생성된 규정의 ID와 wzpubno 저장
                this.currentRule = {
                    id: result.rule_id,
                    wzpubno: formData.publication_no,
                    wzname: formData.name
                };
                this.mode = 'new';
                console.log('[RuleEditor] 제정 모달 - 저장된 currentRule:', this.currentRule);

                // 수정 이력파일 업로드 (파일이 있는 경우)
                if (historyFile) {
                    try {
                        await this.uploadHistoryFileForRule(result.rule_id, historyFile);
                        console.log('[RuleEditor] 수정 이력파일 업로드 성공');
                    } catch (histError) {
                        console.error('[RuleEditor] 수정 이력파일 업로드 실패:', histError);
                        this.showNotification('기본 정보는 등록되었으나 수정 이력파일 업로드에 실패했습니다.', 'warning');
                    }
                }

                this.showNotification('기본 정보가 등록되었습니다. 이제 파일을 업로드해주세요.', 'success');

                // 제정 모달 닫기
                this.closeNewModal();

                // 자동으로 파일 업로드 모달 열기
                setTimeout(() => {
                    this.showFileUploadModal('제정');
                }, 500);
            } else {
                throw new Error('규정 ID를 받지 못했습니다.');
            }

        } catch (error) {
            console.error('[RuleEditor] Create new error:', error);
            this.showNotification(`생성 실패: ${error.message}`, 'error');
        }
    },

    // 편집 메뉴 토글
    toggleEditMenu() {
        const menu = document.getElementById('editDropdownMenu');
        if (menu) {
            menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
        }

        // 외부 클릭 시 메뉴 닫기
        document.addEventListener('click', (e) => {
            const menu = document.getElementById('editDropdownMenu');
            const menuButton = e.target.closest('.menu-dots');
            if (menu && !menuButton && !menu.contains(e.target)) {
                menu.style.display = 'none';
            }
        }, { once: true });
    },

    // 내규 삭제
    async deleteRegulation() {
        if (!this.currentRule || !this.currentRule.wzruleseq) {
            this.showNotification('삭제할 규정을 찾을 수 없습니다.', 'error');
            return;
        }

        // 삭제 확인 다이얼로그
        const confirmModal = document.createElement('div');
        confirmModal.className = 'modal active';
        confirmModal.style.cssText = 'z-index: 3000;';
        confirmModal.innerHTML = `
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header" style="background: linear-gradient(135deg, #dc3545, #c82333); color: white;">
                    <h2>⚠️ 내규 삭제 확인</h2>
                </div>
                <div class="modal-body" style="padding: 30px;">
                    <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                        <p style="margin: 0; color: #856404; font-weight: 500;">
                            <strong>경고:</strong> 이 작업은 되돌릴 수 없습니다!
                        </p>
                    </div>
                    <p style="font-size: 16px; margin-bottom: 10px;">
                        다음 내규를 정말로 삭제하시겠습니까?
                    </p>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <p style="margin: 5px 0;"><strong>내규번호:</strong> ${this.currentRule.wzpubno || '-'}</p>
                        <p style="margin: 5px 0;"><strong>내규명:</strong> ${this.currentRule.wzname || '-'}</p>
                        <p style="margin: 5px 0;"><strong>소관부서:</strong> ${this.currentRule.wzmgrdptnm || '-'}</p>
                    </div>
                    <p style="color: #dc3545; font-size: 14px; margin-top: 20px;">
                        ※ JSON 파일과 데이터베이스 기록이 모두 삭제됩니다.
                    </p>
                </div>
                <div class="modal-footer" style="display: flex; justify-content: flex-end; gap: 10px; padding: 20px; border-top: 1px solid #e5e5e5;">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()"
                            style="padding: 10px 20px;">취소</button>
                    <button class="btn btn-danger" onclick="RuleEditor.confirmDelete()"
                            style="padding: 10px 20px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        삭제 확인
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(confirmModal);
    },

    // 삭제 확인 처리
    async confirmDelete() {
        try {
            const ruleId = this.currentRule.wzruleseq;
            const ruleName = this.currentRule.wzname;

            // 확인 모달 닫기
            const confirmModal = document.querySelector('.modal.active[style*="z-index: 3000"]');
            if (confirmModal) confirmModal.remove();

            // 로딩 표시
            this.showProgress('내규 삭제 중...');

            const response = await fetch(`/api/v1/rule/delete/${ruleId}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '삭제에 실패했습니다.');
            }

            const result = await response.json();

            if (result.success) {
                this.showNotification(`✅ ${ruleName} 내규가 삭제되었습니다 (백그라운드에서 병합 중)`, 'success');

                // 편집 모달 닫기
                this.closeModal();

                // 목록 새로고침
                await this.loadRegulations();

                // 현재 탭이 현행이면 다시 로드
                const activeTab = document.querySelector('.tab-button.active');
                if (activeTab && activeTab.textContent.includes('현행')) {
                    await this.loadCurrentRegulations();
                }
            } else {
                throw new Error(result.error || '삭제에 실패했습니다.');
            }
        } catch (error) {
            console.error('[RuleEditor] Delete error:', error);
            this.showNotification(`삭제 실패: ${error.message}`, 'error');
        } finally {
            this.hideProgress();
        }
    },

    // 필터 옵션 로드
    async loadFilters() {
        console.log('[RuleEditor] Loading filter options...');

        // 부서 목록 로드
        await this.loadDepartmentFilter();

        // 분류 목록 로드
        await this.loadClassificationFilter();
    },

    // 부서 필터 옵션 로드
    async loadDepartmentFilter() {
        try {
            // WZ_DEPT API 사용 - 실제 컬럼명 사용
            const response = await fetch('/WZ_DEPT/api/v1/select', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    conditions: {},
                    columns: "wzDeptOrgCd, wzDeptName",
                    order_by: "wzDeptName",
                    limit: 1000
                })
            });

            if (response.ok) {
                const result = await response.json();
                const departmentFilter = document.getElementById('departmentFilter');

                if (departmentFilter && result.success && result.data) {
                    // 기존 옵션 제거 (첫 번째 '모든 부서' 옵션 제외)
                    while (departmentFilter.options.length > 1) {
                        departmentFilter.remove(1);
                    }

                    // 부서 옵션 추가
                    result.data.forEach(dept => {
                        const option = document.createElement('option');
                        option.value = dept.wzDeptName || dept.wzdeptname;
                        option.textContent = dept.wzDeptName || dept.wzdeptname;
                        departmentFilter.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.error('[RuleEditor] Error loading departments:', error);
        }
    },

    // 분류 필터 옵션 로드
    async loadClassificationFilter() {
        try {
            // WZ_CATE 테이블에서 분류 목록 가져오기
            const response = await fetch('/api/v1/classification/list', {
                method: 'GET',
                credentials: 'include'
            });

            if (response.ok) {
                const result = await response.json();
                const classificationFilter = document.getElementById('classificationFilter');

                if (classificationFilter && result.success && result.classifications) {
                    // 기존 옵션 제거 (첫 번째 '모든 분류' 옵션 제외)
                    while (classificationFilter.options.length > 1) {
                        classificationFilter.remove(1);
                    }

                    // 분류 옵션 추가 (DB에서 가져온 순서대로)
                    result.classifications.forEach(classification => {
                        const option = document.createElement('option');
                        option.value = classification.id;
                        option.textContent = `${classification.id}. ${classification.name}`;
                        classificationFilter.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.error('[RuleEditor] Error loading classifications from DB:', error);
        }
    },

    // 로그아웃
    async logout() {
        try {
            const response = await fetch('/api/v1/auth/logout', {
                method: 'POST',
                credentials: 'include'
            });

            if (response.ok) {
                window.location.href = '/login';
            }
        } catch (error) {
            console.error('[RuleEditor] Logout error:', error);
        }
    },

    // 모달 스타일 추가
    addModalStyles() {
        if (!document.getElementById('ruleEditorStyles')) {
            const style = document.createElement('style');
            style.id = 'ruleEditorStyles';
            style.textContent = `
                .modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0, 0, 0, 0.5);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 1000;
                }

                .modal.active {
                    display: flex;
                }

                .modal-content {
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    max-height: 90vh;
                    overflow-y: auto;
                }

                .modal-header {
                    padding: 20px;
                    border-bottom: 1px solid #e5e5e5;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .modal-header h2 {
                    margin: 0;
                    font-size: 20px;
                    color: #333;
                }

                .modal-close {
                    background: none;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: #999;
                }

                .modal-close:hover {
                    color: #333;
                }

                .modal-body {
                    padding: 20px;
                }

                .modal-footer {
                    padding: 20px;
                    border-top: 1px solid #e5e5e5;
                    display: flex;
                    justify-content: flex-end;
                    gap: 10px;
                }

                .form-group {
                    margin-bottom: 15px;
                }

                .form-label {
                    display: block;
                    margin-bottom: 5px;
                    font-weight: 600;
                    color: #333;
                }

                .form-control {
                    width: 100%;
                    padding: 8px 12px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 14px;
                }

                .form-control:focus {
                    outline: none;
                    border-color: #60584C;
                    box-shadow: 0 0 0 3px rgba(255, 188, 0, 0.1);
                }
                .file-upload-wrapper {
                    position: relative;
                    margin: 10px 0;
                }

                .file-upload-wrapper input[type="file"] {
                    width: 100%;
                    padding: 10px;
                    border: 2px dashed #ddd;
                    border-radius: 4px;
                    cursor: pointer;
                }

                .file-upload-wrapper input[type="file"]:hover {
                    border-color: #60584C;
                }

                .file-name-display {
                    margin-top: 5px;
                    color: #666;
                    font-size: 14px;
                }

                .upload-status {
                    margin-top: 5px;
                    font-size: 14px;
                }

                .progress-section {
                    margin: 20px 0;
                }

                .progress-bar {
                    width: 100%;
                    height: 20px;
                    background-color: #f0f0f0;
                    border-radius: 10px;
                    overflow: hidden;
                }

                .progress-fill {
                    height: 100%;
                    background-color: #60584C;
                    width: 0%;
                    transition: width 0.3s;
                }

                .progress-text {
                    text-align: center;
                    margin-top: 10px;
                    color: #666;
                }

                .btn-ready {
                    background-color: #4CAF50 !important;
                }

                .required {
                    color: red;
                }

                .info-text {
                    background-color: #e8f4fd;
                    padding: 10px;
                    border-radius: 4px;
                    margin-bottom: 20px;
                    color: #0066cc;
                }

                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }

                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    },

    // 부록 파일 관련 속성 추가
    selectedAppendixFiles: [],

    // 부록 파일 선택 처리
    handleAppendixSelect(files) {
        console.log('[RuleEditor] Appendix files selected:', files.length);

        // 기존 선택된 파일에 새로운 파일 추가 (누적)
        const newFiles = Array.from(files);

        // PDF 파일만 필터링
        const pdfFiles = newFiles.filter(file => {
            const isPdf = file.name.toLowerCase().endsWith('.pdf');
            if (!isPdf) {
                this.showNotification(`${file.name}은(는) PDF 파일이 아닙니다. PDF만 업로드 가능합니다.`, 'warning');
            }
            return isPdf;
        });

        // 중복 파일 체크 (파일명과 크기로 비교)
        pdfFiles.forEach(newFile => {
            const isDuplicate = this.selectedAppendixFiles.some(existingFile =>
                existingFile.name === newFile.name &&
                existingFile.size === newFile.size
            );

            if (!isDuplicate) {
                this.selectedAppendixFiles.push(newFile);
            } else {
                console.log(`[RuleEditor] Duplicate file skipped: ${newFile.name}`);
            }
        });

        // 파일 목록 표시
        const fileListDiv = document.getElementById('appendixFileList');
        const uploadSection = document.getElementById('appendixUploadSection');

        if (fileListDiv && this.selectedAppendixFiles.length > 0) {
            let listHtml = '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">';
            listHtml += '<h4 style="font-size: 14px; margin-bottom: 10px;">선택된 파일들:</h4>';
            listHtml += '<ul style="margin: 0; padding-left: 20px; list-style: none;">';

            this.selectedAppendixFiles.forEach((file, index) => {
                const sizeKB = (file.size / 1024).toFixed(2);
                listHtml += `
                    <li style="margin: 5px 0; font-size: 13px; display: flex; align-items: center; justify-content: space-between; padding: 5px; background: white; border-radius: 4px;">
                        <span style="flex: 1;">
                            📄 ${file.name} (${sizeKB} KB)
                        </span>
                        <button onclick="RuleEditor.removeAppendixFile(${index})"
                                style="background: #dc3545; color: white; border: none; padding: 2px 8px; border-radius: 3px; cursor: pointer; font-size: 11px;">
                            삭제
                        </button>
                    </li>
                `;
            });

            listHtml += '</ul>';
            listHtml += `<p style="margin-top: 10px; font-size: 12px; color: #28a745;">
                총 ${this.selectedAppendixFiles.length}개 파일 선택됨
            </p>`;
            listHtml += '</div>';

            fileListDiv.innerHTML = listHtml;

            // 업로드 버튼 표시
            if (uploadSection) {
                uploadSection.style.display = 'block';
            }
        } else if (fileListDiv) {
            fileListDiv.innerHTML = '';
            // 업로드 섹션은 숨기지 않음 - 연속 업로드 가능하도록 유지
            // if (uploadSection) {
            //     uploadSection.style.display = 'none';
            // }
        }
    },

    // 개별 부록 파일 삭제
    removeAppendixFile(index) {
        console.log('[RuleEditor] Removing appendix file at index:', index);

        // 배열에서 파일 제거
        this.selectedAppendixFiles.splice(index, 1);

        // 파일 목록 다시 표시
        this.updateAppendixFileList();
    },

    // 부록 파일 목록 업데이트
    updateAppendixFileList() {
        const fileListDiv = document.getElementById('appendixFileList');
        const uploadSection = document.getElementById('appendixUploadSection');

        if (this.selectedAppendixFiles.length > 0) {
            let listHtml = '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">';
            listHtml += '<h4 style="font-size: 14px; margin-bottom: 10px;">선택된 파일들:</h4>';
            listHtml += '<ul style="margin: 0; padding-left: 20px; list-style: none;">';

            this.selectedAppendixFiles.forEach((file, index) => {
                const sizeKB = (file.size / 1024).toFixed(2);
                listHtml += `
                    <li style="margin: 5px 0; font-size: 13px; display: flex; align-items: center; justify-content: space-between; padding: 5px; background: white; border-radius: 4px;">
                        <span style="flex: 1;">
                            📄 ${file.name} (${sizeKB} KB)
                        </span>
                        <button onclick="RuleEditor.removeAppendixFile(${index})"
                                style="background: #dc3545; color: white; border: none; padding: 2px 8px; border-radius: 3px; cursor: pointer; font-size: 11px;">
                            삭제
                        </button>
                    </li>
                `;
            });

            listHtml += '</ul>';
            listHtml += `<p style="margin-top: 10px; font-size: 12px; color: #28a745;">
                총 ${this.selectedAppendixFiles.length}개 파일 선택됨
            </p>`;
            listHtml += '</div>';

            if (fileListDiv) fileListDiv.innerHTML = listHtml;
            if (uploadSection) uploadSection.style.display = 'block';
        } else {
            if (fileListDiv) fileListDiv.innerHTML = '';
            // 업로드 섹션은 숨기지 않음 - 연속 업로드 가능하도록 유지
            // if (uploadSection) uploadSection.style.display = 'none';
        }
    },

    // 부록 파일 선택 초기화
    clearAppendixSelection() {
        this.selectedAppendixFiles = [];

        const fileInput = document.getElementById('editAppendixFiles');
        if (fileInput) {
            fileInput.value = '';
        }

        const fileListDiv = document.getElementById('appendixFileList');
        if (fileListDiv) {
            fileListDiv.innerHTML = '';
        }

        // 업로드 섹션은 숨기지 않음 - 연속 업로드 가능하도록 유지
        // const uploadSection = document.getElementById('appendixUploadSection');
        // if (uploadSection) {
        //     uploadSection.style.display = 'none';
        // }
    },

    // 부록 파일 업로드
    async uploadAppendixFiles() {
        if (!this.selectedAppendixFiles || this.selectedAppendixFiles.length === 0) {
            alert('업로드할 부록 파일을 선택해주세요.');
            return;
        }

        if (!this.currentRule || !this.currentRule.wzruleseq) {
            alert('내규 정보가 없습니다. 먼저 기본정보를 저장해주세요.');
            return;
        }

        console.log('[RuleEditor] Uploading appendix files...');
        console.log('[RuleEditor] Current rule wzpubno:', this.currentRule.wzpubno);

        try {
            const formData = new FormData();

            // 모든 선택된 파일 추가
            this.selectedAppendixFiles.forEach(file => {
                formData.append('files', file);
            });

            // wzpubno 추가
            formData.append('wzpubno', this.currentRule.wzpubno || '');

            const response = await fetch(`/api/v1/appendix/upload/${this.currentRule.wzruleseq}`, {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                // 성공 메시지 표시
                this.showAppendixUploadResult(result);

                // 선택 초기화
                this.clearAppendixSelection();

                // 부록 목록 새로고침 (만약 표시되고 있다면)
                if (typeof this.loadAppendixList === 'function') {
                    this.loadAppendixList(this.currentRule.wzruleseq, this.currentRule.wzpubno);
                }
            } else {
                throw new Error(result.error || '업로드에 실패했습니다.');
            }

        } catch (error) {
            console.error('[RuleEditor] Appendix upload error:', error);
            alert(`부록 파일 업로드 실패: ${error.message}`);
        }
    },

    // 부록 업로드 결과 메시지 박스 표시
    showAppendixUploadResult(result) {
        // 메시지 박스 HTML 생성
        const messageHtml = `
            <div id="appendixResultModal" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;">

                <div style="
                    background: white;
                    border-radius: 12px;
                    padding: 30px;
                    max-width: 500px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    animation: slideDown 0.3s ease;">

                    <h2 style="margin: 0 0 20px 0; color: #28a745; font-size: 24px;">
                        ✅ 부록 업로드 완료!
                    </h2>

                    <div style="margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                        <p style="margin: 5px 0; font-size: 16px;">
                            <strong>성공:</strong> ${result.uploaded_count}개 파일
                        </p>
                        ${result.failed_count > 0 ? `
                            <p style="margin: 5px 0; font-size: 16px; color: #dc3545;">
                                <strong>실패:</strong> ${result.failed_count}개 파일
                            </p>
                        ` : ''}
                    </div>

                    ${result.uploaded_files && result.uploaded_files.length > 0 ? `
                        <div style="margin-bottom: 20px;">
                            <h4 style="font-size: 14px; margin-bottom: 10px;">업로드된 파일:</h4>
                            <ul style="margin: 0; padding-left: 20px; max-height: 200px; overflow-y: auto;">
                                ${result.uploaded_files.map(file => `
                                    <li style="margin: 5px 0; font-size: 13px;">
                                        ${file.filename}
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    ` : ''}

                    ${result.failed_files && result.failed_files.length > 0 ? `
                        <div style="margin-bottom: 20px;">
                            <h4 style="font-size: 14px; margin-bottom: 10px; color: #dc3545;">실패한 파일:</h4>
                            <ul style="margin: 0; padding-left: 20px;">
                                ${result.failed_files.map(file => `
                                    <li style="margin: 5px 0; font-size: 13px; color: #dc3545;">
                                        ${file.filename}: ${file.error}
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    ` : ''}

                    <button onclick="RuleEditor.closeAppendixResultModal()" style="
                        padding: 10px 30px;
                        background: #28a745;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        font-size: 16px;
                        cursor: pointer;
                        width: 100%;">
                        확인
                    </button>
                </div>
            </div>
        `;

        // 기존 모달이 있으면 제거
        const existingModal = document.getElementById('appendixResultModal');
        if (existingModal) {
            existingModal.remove();
        }

        // 모달 추가
        const modalDiv = document.createElement('div');
        modalDiv.innerHTML = messageHtml;
        document.body.appendChild(modalDiv.firstElementChild);

        // 스타일 추가 (한 번만)
        if (!document.getElementById('appendixModalStyles')) {
            const style = document.createElement('style');
            style.id = 'appendixModalStyles';
            style.textContent = `
                @keyframes slideDown {
                    from {
                        transform: translateY(-20px);
                        opacity: 0;
                    }
                    to {
                        transform: translateY(0);
                        opacity: 1;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    },

    // 부록 결과 모달 닫기
    closeAppendixResultModal() {
        const modal = document.getElementById('appendixResultModal');
        if (modal) {
            modal.remove();
        }
    },

    // 부록 파일 목록 조회
    async loadAppendixList(ruleId, wzpubno) {
        try {
            let url = `/api/v1/appendix/list/${ruleId}`;
            if (wzpubno) {
                url += `?wzpubno=${encodeURIComponent(wzpubno)}`;
            }

            const response = await fetch(url, {
                method: 'GET',
                credentials: 'include'
            });

            if (response.ok) {
                const result = await response.json();
                console.log('[RuleEditor] Appendix list:', result);
                return result;
            }
        } catch (error) {
            console.error('[RuleEditor] Failed to load appendix list:', error);
        }
    },

    // 드래그앤드롭 이벤트 핸들러
    handleAppendixDragOver(event) {
        event.preventDefault();
        event.stopPropagation();

        // 드래그 오버시 시각적 피드백
        const dropZone = document.getElementById('appendixDropZone');
        if (dropZone) {
            dropZone.style.background = 'linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%)';
            dropZone.style.borderColor = '#28a745';
            dropZone.style.borderWidth = '3px';
        }
    },

    handleAppendixDragLeave(event) {
        event.preventDefault();
        event.stopPropagation();

        // 드래그 리브시 원래 스타일로 복원
        const dropZone = document.getElementById('appendixDropZone');
        if (dropZone) {
            dropZone.style.background = 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)';
            dropZone.style.borderColor = '#28a745';
            dropZone.style.borderWidth = '2px';
        }
    },

    handleAppendixDrop(event) {
        event.preventDefault();
        event.stopPropagation();

        // 드롭시 원래 스타일로 복원
        const dropZone = document.getElementById('appendixDropZone');
        if (dropZone) {
            dropZone.style.background = 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)';
            dropZone.style.borderColor = '#28a745';
            dropZone.style.borderWidth = '2px';
        }

        // 드롭된 파일 처리
        const files = event.dataTransfer.files;
        if (files && files.length > 0) {
            console.log('[RuleEditor] Files dropped:', files.length);
            this.handleAppendixSelect(files);
        }
    },

    // 모달용 부록 파일 선택 (제정/개정)
    modalSelectedAppendixFiles: [],

    handleModalAppendixSelect(files) {
        console.log('[RuleEditor] Modal appendix files selected:', files.length);

        // modalSelectedAppendixFiles 초기화 (필요시)
        if (!this.modalSelectedAppendixFiles) {
            this.modalSelectedAppendixFiles = [];
        }

        // 새로운 파일들을 기존 목록에 누적 (중복 제거)
        const newFiles = Array.from(files);
        newFiles.forEach(newFile => {
            const isDuplicate = this.modalSelectedAppendixFiles.some(existingFile =>
                existingFile.name === newFile.name &&
                existingFile.size === newFile.size
            );

            if (!isDuplicate) {
                this.modalSelectedAppendixFiles.push(newFile);
            }
        });

        // 파일 목록 표시
        const fileListDiv = document.getElementById('modalAppendixList');

        if (fileListDiv && this.modalSelectedAppendixFiles.length > 0) {
            let listHtml = '<div style="background: #f0fff4; padding: 10px; border-radius: 4px; margin-top: 10px;">';
            listHtml += '<strong>선택된 부록 파일:</strong>';
            listHtml += '<ul style="margin: 5px 0; padding-left: 20px; font-size: 13px;">';

            this.modalSelectedAppendixFiles.forEach((file, index) => {
                const sizeKB = (file.size / 1024).toFixed(2);
                listHtml += `
                    <li style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                        <span>${file.name} (${sizeKB} KB)</span>
                        <button onclick="RuleEditor.removeModalAppendixFile(${index})"
                                style="color: #dc3545; border: none; background: none; cursor: pointer; font-size: 16px; padding: 0 4px;"
                                title="파일 제거">×</button>
                    </li>`;
            });

            listHtml += '</ul>';
            listHtml += `<small style="color: #28a745;">총 ${this.modalSelectedAppendixFiles.length}개 파일</small>`;
            listHtml += '</div>';

            fileListDiv.innerHTML = listHtml;

            // 업로드 버튼 영역 표시
            const uploadSection = document.getElementById('modalAppendixUploadSection');
            if (uploadSection) {
                uploadSection.style.display = 'block';
            }
        } else if (fileListDiv) {
            fileListDiv.innerHTML = '';

            // 업로드 버튼 영역은 숨기지 않음 - 연속 업로드 가능하도록 유지
            // const uploadSection = document.getElementById('modalAppendixUploadSection');
            // if (uploadSection) {
            //     uploadSection.style.display = 'none';
            // }
        }
    },

    // 모달 부록 파일 개별 제거
    removeModalAppendixFile(index) {
        if (this.modalSelectedAppendixFiles && index >= 0 && index < this.modalSelectedAppendixFiles.length) {
            this.modalSelectedAppendixFiles.splice(index, 1);

            // 파일 목록 다시 표시
            const files = new FileList();  // 빈 FileList로 업데이트 트리거
            this.handleModalAppendixSelect([]);

            // 실제 파일 목록 다시 렌더링
            const fileListDiv = document.getElementById('modalAppendixList');
            if (fileListDiv && this.modalSelectedAppendixFiles.length > 0) {
                let listHtml = '<div style="background: #f0fff4; padding: 10px; border-radius: 4px; margin-top: 10px;">';
                listHtml += '<strong>선택된 부록 파일:</strong>';
                listHtml += '<ul style="margin: 5px 0; padding-left: 20px; font-size: 13px;">';

                this.modalSelectedAppendixFiles.forEach((file, index) => {
                    const sizeKB = (file.size / 1024).toFixed(2);
                    listHtml += `
                        <li style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                            <span>${file.name} (${sizeKB} KB)</span>
                            <button onclick="RuleEditor.removeModalAppendixFile(${index})"
                                    style="color: #dc3545; border: none; background: none; cursor: pointer; font-size: 16px; padding: 0 4px;"
                                    title="파일 제거">×</button>
                        </li>`;
                });

                listHtml += '</ul>';
                listHtml += `<small style="color: #28a745;">총 ${this.modalSelectedAppendixFiles.length}개 파일</small>`;
                listHtml += '</div>';

                fileListDiv.innerHTML = listHtml;

                // 업로드 버튼 영역 표시
                const uploadSection = document.getElementById('modalAppendixUploadSection');
                if (uploadSection) {
                    uploadSection.style.display = 'block';
                }
            } else if (fileListDiv) {
                fileListDiv.innerHTML = '';

                // 업로드 버튼 영역은 숨기지 않음 - 연속 업로드 가능하도록 유지
                // const uploadSection = document.getElementById('modalAppendixUploadSection');
                // if (uploadSection) {
                //     uploadSection.style.display = 'none';
                // }
            }
        }
    },

    // 모달용 드래그 앤 드롭 핸들러 함수들
    handleModalAppendixDrop(e) {
        e.preventDefault();
        e.stopPropagation();

        const dropZone = document.getElementById('modalAppendixDropZone');
        if (dropZone) {
            dropZone.style.background = 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)';
            dropZone.style.borderColor = '#28a745';
        }

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.handleModalAppendixSelect(files);
        }
    },

    handleModalAppendixDragOver(e) {
        e.preventDefault();
        e.stopPropagation();

        const dropZone = document.getElementById('modalAppendixDropZone');
        if (dropZone) {
            dropZone.style.background = 'linear-gradient(135deg, #e8f5e8 0%, #d4e9d4 100%)';
            dropZone.style.borderColor = '#20c997';
        }
    },

    handleModalAppendixDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();

        const dropZone = document.getElementById('modalAppendixDropZone');
        if (dropZone) {
            dropZone.style.background = 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)';
            dropZone.style.borderColor = '#28a745';
        }
    },

    // 모달 부록 파일 업로드 (제정/개정 모달용)
    async uploadModalAppendixFiles() {
        if (!this.modalSelectedAppendixFiles || this.modalSelectedAppendixFiles.length === 0) {
            alert('업로드할 부록 파일을 선택해주세요.');
            return;
        }

        console.log('[RuleEditor] Uploading modal appendix files...');

        try {
            const formData = new FormData();

            // 모든 선택된 부록 파일 추가
            this.modalSelectedAppendixFiles.forEach(file => {
                formData.append('files', file);
            });

            let wzpubno = '';
            let ruleId = 0;

            // 모달 타입에 따라 규정번호 결정
            const modalTitle = document.querySelector('#fileUploadModal h2')?.textContent || '';
            console.log('[RuleEditor] 현재 모달 제목:', modalTitle);

            if (modalTitle.includes('개정')) {
                // 개정 모달: 현재 규정의 wzpubno 사용
                if (this.currentRule && this.currentRule.wzpubno) {
                    wzpubno = this.currentRule.wzpubno;
                    ruleId = this.currentRule.wzruleseq || this.currentRule.id || 0;
                    console.log('[RuleEditor] 개정 모달 - 기존 wzpubno 사용:', wzpubno);
                } else {
                    alert('개정할 내규 정보를 찾을 수 없습니다.');
                    return;
                }
            } else if (modalTitle.includes('제정')) {
                // 제정 모달: currentRule에서 wzpubno 사용
                if (this.currentRule && this.currentRule.wzpubno) {
                    wzpubno = this.currentRule.wzpubno;
                    ruleId = this.currentRule.id || 0;
                    console.log('[RuleEditor] 제정 모달 - currentRule wzpubno 사용:', wzpubno);
                } else {
                    alert('내규번호 정보를 찾을 수 없습니다. 먼저 기본정보를 저장해주세요.');
                    return;
                }
            } else {
                alert('모달 타입을 확인할 수 없습니다.');
                return;
            }

            // wzpubno 추가
            formData.append('wzpubno', wzpubno);

            const response = await fetch(`/api/v1/appendix/upload/${ruleId}`, {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                console.log('[RuleEditor] Modal appendix upload result:', result);

                // 성공 메시지 표시
                this.showAppendixUploadResult(result);

                // 부록 파일 목록 초기화
                this.clearModalAppendixSelection();
            } else {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

        } catch (error) {
            console.error('[RuleEditor] Modal appendix upload error:', error);
            alert(`부록 파일 업로드 실패: ${error.message}`);
        }
    },

    // 모달 부록 파일 선택 초기화
    clearModalAppendixSelection() {
        this.modalSelectedAppendixFiles = [];

        // 파일 입력 초기화
        const fileInput = document.getElementById('modalAppendixFiles');
        if (fileInput) {
            fileInput.value = '';
        }

        // 파일 목록 표시 영역 초기화
        const fileListDiv = document.getElementById('modalAppendixList');
        if (fileListDiv) {
            fileListDiv.innerHTML = '';
        }

        // 업로드 버튼 영역은 숨기지 않음 - 연속 업로드 가능하도록 유지
        // const uploadSection = document.getElementById('modalAppendixUploadSection');
        // if (uploadSection) {
        //     uploadSection.style.display = 'none';
        // }

        console.log('[RuleEditor] Modal appendix selection cleared');
    },

    // uploadFiles 함수 수정 - 부록 파일도 함께 업로드
    async uploadFilesWithAppendix() {
        // 기존 uploadFiles 로직 후에 부록 파일 업로드 추가
        if (this.modalSelectedAppendixFiles && this.modalSelectedAppendixFiles.length > 0) {
            try {
                const formData = new FormData();
                this.modalSelectedAppendixFiles.forEach(file => {
                    formData.append('files', file);
                });

                // wzpubno 추가 (currentRule에 있으면 사용)
                if (this.currentRule && this.currentRule.wzpubno) {
                    formData.append('wzpubno', this.currentRule.wzpubno);
                }

                const response = await fetch(`/api/v1/appendix/upload/${this.currentRule.id}`, {
                    method: 'POST',
                    credentials: 'include',
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();
                    console.log('[RuleEditor] Appendix upload result:', result);
                }
            } catch (error) {
                console.error('[RuleEditor] Appendix upload error:', error);
            }
        }
    },

    // 이미지 관리 탭 렌더링
    renderImagesTab() {
        return `
            <div style="max-width: 1200px; margin: 0 auto;">
                <h3 style="margin-bottom: 20px; color: #333;">이미지 관리</h3>
                <p style="margin-bottom: 30px; color: #6c757d;">조문별로 이미지를 업로드하고 관리할 수 있습니다.</p>

                <!-- 조문 선택 -->
                <div style="margin-bottom: 30px;">
                    <label style="display: block; margin-bottom: 10px; font-weight: 600; color: #333;">
                        조문 선택
                    </label>
                    <select id="imageArticleSelector"
                            style="width: 100%; padding: 10px; border: 1px solid #dee2e6; border-radius: 6px; font-size: 14px;">
                        <option value="">조문을 선택하세요...</option>
                    </select>
                </div>

                <!-- 조문 미선택 시 메시지 -->
                <div id="noArticleMessage" style="padding: 60px 20px; text-align: center; background: #f8f9fa; border-radius: 8px; color: #6c757d;">
                    <p style="font-size: 16px; margin-bottom: 10px;">👆 먼저 조문을 선택하세요</p>
                    <p style="font-size: 13px;">이미지를 추가할 조문을 선택하면 업로드 영역이 표시됩니다.</p>
                </div>

                <!-- 업로드 영역 (조문 선택 시 표시) -->
                <div id="imageUploadArea" style="display: none;">
                    <!-- 드래그 앤 드롭 영역 -->
                    <div id="imageDropZone"
                         style="border: 2px dashed #dee2e6; border-radius: 8px; padding: 40px; text-align: center; background: #f8f9fa; margin-bottom: 30px; cursor: pointer; transition: all 0.3s;">
                        <p style="font-size: 16px; margin-bottom: 10px; color: #60584C;">📤 이미지를 여기에 드래그하세요</p>
                        <p style="font-size: 13px; color: #6c757d; margin-bottom: 20px;">또는 아래 버튼을 클릭하여 파일을 선택하세요</p>
                        <input type="file" id="imageFileInput" accept="image/*" multiple style="display: none;">
                        <button onclick="document.getElementById('imageFileInput').click()"
                                style="padding: 10px 24px; background: #FFBC00; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600;">
                            📁 파일 선택
                        </button>
                        <p style="font-size: 12px; color: #6c757d; margin-top: 15px;">지원 형식: PNG, JPG, GIF (최대 10MB)</p>
                    </div>

                    <!-- 이미지 목록 -->
                    <div>
                        <h4 style="margin-bottom: 15px; color: #333;">현재 이미지 목록</h4>
                        <div id="imagesList"
                             style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px;">
                            <!-- 이미지 카드가 여기에 동적으로 추가됨 -->
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    renderAppendixTab() {
        console.log('[RuleEditor] renderAppendixTab called - START');
        return `
            <div style="padding: 20px; background: white; min-height: 400px;">
                <h3 style="color: #333; margin-bottom: 20px;">📎 부록 관리 TEST</h3>
                <p style="color: #6c757d; margin-bottom: 20px;">부록 파일을 관리할 수 있습니다.</p>
                <div id="appendixFilesList" style="border: 1px solid #ddd; padding: 20px; background: #f8f9fa;">
                    부록 파일 목록을 불러오는 중...
                </div>
            </div>
        `;
    },

    // 부록 파일 핸들러 초기화
    initAppendixFileHandlers() {
        console.log('[RuleEditor] initAppendixFileHandlers called');

        const fileInput = document.getElementById('appendixFileInput');
        const uploadBtn = document.getElementById('uploadAppendixBtn');
        const statusEl = document.getElementById('appendixUploadStatus');
        const dropZone = document.getElementById('appendixDropZone');
        const fileListEl = document.getElementById('appendixFileList');

        if (!fileInput) {
            console.warn('[RuleEditor] appendixFiles input not found');
            return;
        }

        // 드래그앤드롭으로 추가된 파일을 보관
        this.appendixPendingFiles = [];

        const allowedExts = ['.docx', '.xlsx'];

        // 선택된 파일 목록 표시 함수
        const updateFileList = () => {
            if (!fileListEl) return;
            const files = this.appendixPendingFiles;
            if (files.length === 0) {
                fileListEl.innerHTML = '';
                return;
            }
            fileListEl.innerHTML = files.map((f, i) => `
                <div style="display: flex; align-items: center; gap: 8px; padding: 6px 10px; background: #f0f7ff; border-radius: 4px; margin-bottom: 4px; font-size: 13px;">
                    <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">📄 ${f.name} <span style="color: #999;">(${(f.size / 1024).toFixed(1)} KB)</span></span>
                    <button onclick="RuleEditor.removeAppendixFile(${i})" style="background: none; border: none; color: #dc3545; cursor: pointer; font-size: 16px; padding: 0 4px;" title="제거">&times;</button>
                </div>
            `).join('');
        };

        // 파일 추가 (유효성 검사 포함)
        const addFiles = (newFiles) => {
            let rejected = [];
            for (const f of newFiles) {
                const ext = '.' + f.name.split('.').pop().toLowerCase();
                if (allowedExts.includes(ext)) {
                    this.appendixPendingFiles.push(f);
                } else {
                    rejected.push(f.name);
                }
            }
            if (rejected.length > 0) {
                if (statusEl) {
                    statusEl.textContent = `허용되지 않는 파일: ${rejected.join(', ')} (DOCX, XLSX만 가능)`;
                    statusEl.style.color = '#dc3545';
                }
            } else if (statusEl) {
                statusEl.textContent = `${this.appendixPendingFiles.length}개 파일 선택됨`;
                statusEl.style.color = '#28a745';
            }
            updateFileList();
        };

        // 파일 선택 이벤트 (input)
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                addFiles(Array.from(e.target.files));
                fileInput.value = '';  // reset so same file can be re-selected
            }
        });

        // 드롭존 클릭 → 파일 선택 다이얼로그
        if (dropZone) {
            dropZone.addEventListener('click', () => fileInput.click());

            // 드래그 이벤트
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.style.borderColor = '#2196F3';
                dropZone.style.background = '#e3f2fd';
            });
            dropZone.addEventListener('dragleave', (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.style.borderColor = '#ccc';
                dropZone.style.background = '#fafafa';
            });
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.style.borderColor = '#ccc';
                dropZone.style.background = '#fafafa';

                const droppedFiles = e.dataTransfer.files;
                if (droppedFiles && droppedFiles.length > 0) {
                    addFiles(Array.from(droppedFiles));
                }
            });
        }

        // 업로드 버튼 클릭 이벤트
        if (uploadBtn) {
            uploadBtn.addEventListener('click', async () => {
                await this.uploadAppendixFiles();
            });
        }
    },

    // 드래그앤드롭 파일 목록에서 개별 파일 제거
    removeAppendixFile(index) {
        if (!this.appendixPendingFiles) return;
        this.appendixPendingFiles.splice(index, 1);
        // 목록 갱신
        const fileListEl = document.getElementById('appendixFileList');
        const statusEl = document.getElementById('appendixUploadStatus');
        if (fileListEl) {
            if (this.appendixPendingFiles.length === 0) {
                fileListEl.innerHTML = '';
                if (statusEl) statusEl.textContent = '';
            } else {
                fileListEl.innerHTML = this.appendixPendingFiles.map((f, i) => `
                    <div style="display: flex; align-items: center; gap: 8px; padding: 6px 10px; background: #f0f7ff; border-radius: 4px; margin-bottom: 4px; font-size: 13px;">
                        <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">📄 ${f.name} <span style="color: #999;">(${(f.size / 1024).toFixed(1)} KB)</span></span>
                        <button onclick="RuleEditor.removeAppendixFile(${i})" style="background: none; border: none; color: #dc3545; cursor: pointer; font-size: 16px; padding: 0 4px;" title="제거">&times;</button>
                    </div>
                `).join('');
                if (statusEl) {
                    statusEl.textContent = `${this.appendixPendingFiles.length}개 파일 선택됨`;
                    statusEl.style.color = '#28a745';
                }
            }
        }
    },

    // 부록 파일 업로드
    async uploadAppendixFiles() {
        console.log('[RuleEditor] uploadAppendixFiles called');

        const statusEl = document.getElementById('appendixUploadStatus');
        const uploadBtn = document.getElementById('uploadAppendixBtn');

        // 드래그앤드롭 파일 목록 사용
        const pendingFiles = this.appendixPendingFiles || [];
        if (pendingFiles.length === 0) {
            alert('파일을 선택해주세요.');
            return;
        }

        if (!this.currentRule) {
            alert('내규 정보를 찾을 수 없습니다.');
            return;
        }

        const ruleSeq = this.currentRule.wzruleseq || this.currentRule.rule_id;
        const wzruleid = this.currentRule.wzruleid || this.currentRule.id || '';
        const wzpubno = this.currentRule.wzpubno || '';

        console.log('[RuleEditor] Uploading for ruleSeq:', ruleSeq, 'wzruleid:', wzruleid, 'wzpubno:', wzpubno);

        // FormData 생성
        const formData = new FormData();
        formData.append('wzpubno', wzpubno);
        formData.append('wzruleid', wzruleid);

        // 파일 추가
        for (const f of pendingFiles) {
            formData.append('files', f);
        }

        // 업로드 시작
        statusEl.textContent = '업로드 중...';
        statusEl.style.color = '#007bff';
        uploadBtn.disabled = true;

        try {
            const response = await fetch(`/api/v1/appendix/upload/${ruleSeq}`, {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || '업로드 실패');
            }

            const data = await response.json();

            // 성공/실패 메시지
            if (data.uploaded_count > 0 && data.failed_count === 0) {
                statusEl.textContent = `✓ ${data.uploaded_count}개 파일 업로드 완료! (PDF 자동 변환)`;
                statusEl.style.color = '#28a745';
            } else if (data.uploaded_count > 0 && data.failed_count > 0) {
                statusEl.textContent = `✓ ${data.uploaded_count}개 성공, ✗ ${data.failed_count}개 실패`;
                statusEl.style.color = '#ff9800';
            } else {
                const failDetails = data.failed_files ? data.failed_files.map(f => `${f.filename}: ${f.error}`).join('\n') : '';
                statusEl.textContent = `✗ 업로드 실패: ${failDetails || '변환 오류'}`;
                statusEl.style.color = '#dc3545';
                console.error('[RuleEditor] All files failed:', data.failed_files);
            }

            // 파일 목록 초기화
            this.appendixPendingFiles = [];
            const fileListEl = document.getElementById('appendixFileList');
            if (fileListEl) fileListEl.innerHTML = '';

            // 5초 후 상태 메시지 초기화
            setTimeout(() => {
                statusEl.textContent = '';
            }, 5000);

            // 부록 파일 목록 새로고침
            this.loadAppendixFilesList(ruleSeq, wzpubno);

        } catch (error) {
            console.error('[RuleEditor] Upload failed:', error);
            statusEl.textContent = `✗ 업로드 실패: ${error.message}`;
            statusEl.style.color = '#dc3545';
        } finally {
            uploadBtn.disabled = false;
        }
    },

    // 부록 파일 목록 로드
    async loadAppendixFilesList(ruleId, wzpubno) {
        const filesList = document.getElementById('appendixFilesList');
        if (!filesList) {
            console.error('[DEBUG] appendixFilesList element not found!');
            return;
        }

        try {
            const url = wzpubno
                ? `/api/v1/appendix/list/${ruleId}?wzpubno=${encodeURIComponent(wzpubno)}`
                : `/api/v1/appendix/list/${ruleId}`;

            console.log('[DEBUG] Fetching appendix list from:', url);
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`목록 조회 실패: ${response.status}`);
            }

            const data = await response.json();
            console.log('[DEBUG] API Response:', data);

            // 응답 형식 처리: 배열 또는 {files: []} 형식 모두 지원
            let files = Array.isArray(data) ? data : (data.files || []);
            const totalCount = Array.isArray(data) ? data.length : (data.total_count || files.length);

            // wzfilepath에서 실제 파일명 추출
            files = files.map(f => {
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
                                            크기: ${this.formatFileSize(file.size)} |
                                            수정일: ${new Date(file.modified).toLocaleDateString('ko-KR')}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div style="display: flex; gap: 6px;">
                                <!-- 미리보기 버튼 (임시 숨김 - 나중에 다시 활성화 예정) -->
                                <button class="btn btn-sm" onclick="RuleEditor.previewAppendixFile(${ruleId}, '${file.filename}')"
                                        style="display: none; align-items: center; justify-content: center; padding: 6px 12px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 500; font-size: 13px; gap: 4px;" title="미리보기">
                                    <i class="fas fa-eye"></i><span>미리보기</span>
                                </button>
                                <button class="btn btn-sm" onclick="RuleEditor.deleteAppendixFile(${ruleId}, '${file.filename}')"
                                        style="display: inline-flex; align-items: center; justify-content: center; padding: 6px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 500; font-size: 13px; gap: 4px;" title="삭제">
                                    <i class="fas fa-trash"></i><span>삭제</span>
                                </button>
                            </div>
                        </div>
                    `).join('')}
                `;
            } else {
                filesList.innerHTML = `
                    <div style="text-align: center; color: #6c757d; padding: 30px;">
                        <p style="margin-bottom: 10px;">등록된 부록 파일이 없습니다.</p>
                        <p style="font-size: 13px;">위의 업로드 버튼을 클릭하여 부록 파일을 추가하세요.</p>
                    </div>
                `;
            }

        } catch (error) {
            console.error('[RuleEditor] Failed to load files:', error);
            filesList.innerHTML = `
                <div style="text-align: center; color: #dc3545; padding: 20px;">
                    <p>부록 파일 목록을 불러오는데 실패했습니다.</p>
                    <p style="font-size: 13px;">${error.message}</p>
                </div>
            `;
        }
    },

    // 파일 크기 포맷팅
    formatFileSize(bytes) {
        if (!bytes || bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    },

    // 부록 파일 미리보기 (사용자 화면과 동일한 PDF 뷰어 사용)
    previewAppendixFile(ruleId, filename) {
        console.log('[RuleEditor] Previewing:', filename, 'for rule:', ruleId);

        try {
            // 캐시 무효화를 위해 파일명에 타임스탬프 추가
            const timestamp = Date.now();
            const fileNameWithTimestamp = `${filename}.${timestamp}`;

            // API 다운로드 URL 생성
            const downloadUrl = `/api/v1/appendix/download/${ruleId}/${encodeURIComponent(fileNameWithTimestamp)}`;

            // 사용자 화면과 동일한 PDF 뷰어 사용
            const currentDomain = window.location.origin;
            const viewerUrl = `${currentDomain}/static/viewer/web/viewer.html?file=${encodeURIComponent(downloadUrl)}`;

            console.log('[RuleEditor] Opening PDF viewer:', viewerUrl);
            console.log('[Cache Busting] Added timestamp to filename:', filename, '→', fileNameWithTimestamp);

            // 새 창으로 PDF 뷰어 열기
            const newWindow = window.open(viewerUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');

            if (!newWindow) {
                alert('팝업이 차단되었습니다. 브라우저 설정에서 팝업을 허용해주세요.');
                return;
            }
        } catch (error) {
            console.error('[RuleEditor] Preview failed:', error);
            alert('부록 파일 미리보기 중 오류가 발생했습니다.');
        }
    },

    // 부록 파일 다운로드
    downloadAppendixFile(filePath, filename) {
        console.log('[RuleEditor] Downloading:', filePath);
        const downloadUrl = `/${filePath}`;
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    },

    // 부록 파일 삭제
    async deleteAppendixFile(ruleId, filename) {
        if (!confirm(`"${filename}" 파일을 삭제하시겠습니까?`)) {
            return;
        }

        try {
            const wzpubno = this.currentRule?.wzpubno || '';
            const wzruleid = this.currentRule?.wzruleid || this.currentRule?.id || '';

            // URL에 쿼리 파라미터 추가
            const url = new URL(`/api/v1/appendix/delete/${ruleId}/${encodeURIComponent(filename)}`, window.location.origin);
            if (wzpubno) url.searchParams.append('wzpubno', wzpubno);
            if (wzruleid) url.searchParams.append('wzruleid', wzruleid);

            const response = await fetch(url, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('삭제 실패');
            }

            const data = await response.json();
            alert(data.message || '부록 파일이 삭제되었습니다.');

            // 목록 새로고침
            this.loadAppendixFilesList(ruleId, wzpubno);

        } catch (error) {
            console.error('[RuleEditor] Delete failed:', error);
            alert('부록 파일 삭제 중 오류가 발생했습니다.');
        }
    },

    // ==================== 안내사항 CRUD ====================

    async loadRegNotices() {
        const listEl = document.getElementById('regNoticeList');
        if (!listEl) return;

        const regCode = this.currentRule?.wzpubno;
        if (!regCode) {
            listEl.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">규정을 먼저 선택해주세요.</div>';
            return;
        }

        listEl.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">불러오는 중...</div>';

        try {
            const response = await fetch(`/api/regulation-notices/${encodeURIComponent(regCode)}`);
            if (!response.ok) throw new Error('API 오류');
            const notices = await response.json();

            if (!notices || notices.length === 0) {
                listEl.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">등록된 안내사항이 없습니다.</div>';
                return;
            }

            // 데이터를 캐시해서 수정 시 참조
            this._regNoticesCache = {};
            notices.forEach(n => { this._regNoticesCache[n.id] = n; });

            listEl.innerHTML = notices.map(n => `
                <div style="background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="flex: 1;">
                            <div style="font-weight: 600; font-size: 15px; color: #333; margin-bottom: 6px;">
                                ${this.escapeHtml(n.title || '(제목 없음)')}
                            </div>
                            <div style="font-size: 12px; color: #888; margin-bottom: 8px;">
                                ${this.escapeHtml(n.created_by || '관리자')} | ${n.created_at ? new Date(n.created_at).toLocaleDateString('ko-KR') : '-'}
                            </div>
                            <div style="font-size: 14px; color: #555; white-space: pre-wrap; line-height: 1.6;">
                                ${this.escapeHtml(n.content || '')}
                            </div>
                        </div>
                        <div style="display: flex; gap: 6px; margin-left: 12px; flex-shrink: 0;">
                            <button onclick="RuleEditor.editRegNotice(${n.id})"
                                    style="background: #f0f0f0; border: 1px solid #ddd; border-radius: 4px; padding: 4px 10px; cursor: pointer; font-size: 12px; color: #555;">
                                수정
                            </button>
                            <button onclick="RuleEditor.deleteRegNotice(${n.id})"
                                    style="background: #fff0f0; border: 1px solid #ffcccc; border-radius: 4px; padding: 4px 10px; cursor: pointer; font-size: 12px; color: #dc3545;">
                                삭제
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('[RuleEditor] loadRegNotices error:', error);
            listEl.innerHTML = '<div style="text-align: center; padding: 40px; color: #dc3545;">안내사항 로드 실패</div>';
        }
    },

    editRegNotice(noticeId) {
        const n = this._regNoticesCache?.[noticeId];
        if (!n) return;
        this.showRegNoticeForm(noticeId, n.title || '', n.created_by || '', n.content || '');
    },

    showRegNoticeForm(noticeId, title, createdBy, content) {
        const formArea = document.getElementById('regNoticeFormArea');
        if (!formArea) return;

        const isEdit = noticeId != null;
        formArea.innerHTML = `
            <div style="background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 16px;">
                <h4 style="margin: 0 0 14px 0; font-size: 14px; color: #333;">${isEdit ? '안내사항 수정' : '새 안내사항'}</h4>
                <div style="margin-bottom: 10px;">
                    <label style="display: block; font-size: 13px; font-weight: 500; color: #555; margin-bottom: 4px;">제목</label>
                    <input type="text" id="regNoticeTitle" value="${isEdit ? this.escapeHtml(title || '') : ''}"
                           placeholder="안내사항 제목"
                           style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;">
                </div>
                <div style="margin-bottom: 10px;">
                    <label style="display: block; font-size: 13px; font-weight: 500; color: #555; margin-bottom: 4px;">작성자</label>
                    <input type="text" id="regNoticeCreatedBy" value="${isEdit ? this.escapeHtml(createdBy || '') : this.escapeHtml(window.__currentUser?.full_name || '관리자')}"
                           placeholder="작성자"
                           style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;">
                </div>
                <div style="margin-bottom: 14px;">
                    <label style="display: block; font-size: 13px; font-weight: 500; color: #555; margin-bottom: 4px;">내용</label>
                    <textarea id="regNoticeContent" rows="5" placeholder="안내사항 내용을 입력하세요..."
                              style="width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; resize: vertical; box-sizing: border-box;">${isEdit ? this.escapeHtml(content || '') : ''}</textarea>
                </div>
                <div style="display: flex; gap: 8px; justify-content: flex-end;">
                    <button onclick="RuleEditor.cancelRegNoticeForm()"
                            style="background: #f0f0f0; border: 1px solid #ddd; border-radius: 4px; padding: 8px 16px; cursor: pointer; font-size: 13px;">
                        취소
                    </button>
                    <button onclick="RuleEditor.saveRegNotice(${isEdit ? noticeId : 'null'})"
                            style="background: #2196F3; color: white; border: none; border-radius: 4px; padding: 8px 16px; cursor: pointer; font-size: 13px; font-weight: 500;">
                        저장
                    </button>
                </div>
            </div>
        `;
        document.getElementById('regNoticeTitle')?.focus();
    },

    cancelRegNoticeForm() {
        const formArea = document.getElementById('regNoticeFormArea');
        if (formArea) formArea.innerHTML = '';
    },

    async saveRegNotice(noticeId) {
        const title = document.getElementById('regNoticeTitle')?.value?.trim() || '';
        const createdBy = document.getElementById('regNoticeCreatedBy')?.value?.trim() || '';
        const content = document.getElementById('regNoticeContent')?.value?.trim() || '';

        if (!content) {
            alert('내용을 입력해주세요.');
            return;
        }

        const regCode = this.currentRule?.wzpubno;
        if (!regCode) return;

        try {
            const isEdit = noticeId != null;
            const url = isEdit
                ? `/api/regulation-notices/${encodeURIComponent(regCode)}/${noticeId}`
                : `/api/regulation-notices/${encodeURIComponent(regCode)}`;

            const body = isEdit
                ? { title, content }
                : { title, content, created_by: createdBy };

            const response = await fetch(url, {
                method: isEdit ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            if (!response.ok) throw new Error('저장 실패');

            this.cancelRegNoticeForm();
            this.loadRegNotices();
            this.showNotification(isEdit ? '안내사항이 수정되었습니다.' : '안내사항이 등록되었습니다.', 'success');
        } catch (error) {
            console.error('[RuleEditor] saveRegNotice error:', error);
            alert('안내사항 저장에 실패했습니다.');
        }
    },

    async deleteRegNotice(noticeId) {
        if (!confirm('이 안내사항을 삭제하시겠습니까?')) return;

        const regCode = this.currentRule?.wzpubno;
        if (!regCode) return;

        try {
            const response = await fetch(
                `/api/regulation-notices/${encodeURIComponent(regCode)}/${noticeId}`,
                { method: 'DELETE' }
            );

            if (!response.ok) throw new Error('삭제 실패');

            this.loadRegNotices();
            this.showNotification('안내사항이 삭제되었습니다.', 'success');
        } catch (error) {
            console.error('[RuleEditor] deleteRegNotice error:', error);
            alert('안내사항 삭제에 실패했습니다.');
        }
    },

    // ==================== 수정 이력파일 ====================

    // 수정 이력파일 업로드
    async uploadHistoryFileForRule(ruleId, file) {
        if (!file) {
            throw new Error('업로드할 파일이 없습니다');
        }

        if (!file.name.toLowerCase().endsWith('.pdf')) {
            throw new Error('수정 이력파일은 PDF 파일만 업로드 가능합니다');
        }

        const formData = new FormData();
        formData.append('history_file', file);

        const response = await fetch(`/api/v1/rule/upload-history-file/${ruleId}`, {
            method: 'POST',
            credentials: 'include',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '수정 이력파일 업로드 실패');
        }

        const result = await response.json();
        console.log('[RuleEditor] 수정 이력파일 업로드 성공:', result);
        return result;
    }
};

// DOM이 로드되면 초기화
document.addEventListener('DOMContentLoaded', () => {
    console.log('[RuleEditor] DOM loaded, initializing...');
    RuleEditor.init();
});
