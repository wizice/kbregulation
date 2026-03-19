// department-manager.js - 부서 관리 모듈

const DepartmentManager = {
    // 부서 데이터
    departments: [],
    allDepartments: [],  // 전체 부서 데이터 (검색용)
    searchQuery: '',     // 현재 검색어
    selectedDeptName: null, // 현재 선택된 부서명

    // 정렬 상태
    sortState: {
        column: null,
        direction: 'asc'
    },

    // 부서코드별 상위부서 분류
    getParentDepartment(deptCode) {
        const code = parseInt(deptCode);
        if (code >= 1000 && code <= 2600) return '위원회';
        if (code >= 2700 && code <= 4600) return '위원회 및 진료과';
        if (code >= 4700 && code <= 6200) return '센터 및 실';
        if (code >= 6300 && code <= 8400) return '집중치료실 및 팀';
        if (code >= 8500 && code <= 10200) return '팀 및 부서';
        return '기타';
    },

    // 상위 부서 목록
    parentDepartments: ['위원회', '위원회 및 진료과', '센터 및 실', '집중치료실 및 팀', '팀 및 부서', '기타'],

    // 카테고리 목록 (임시 주석처리)
    // categories: ['인사', '재무', '의료', 'IT', '품질', '교육', '연구', '기타'],

    // 초기화
    init() {
        this.loadDepartments();
    },

    // 부서 목록 로드
    async loadDepartments() {
        try {
            const response = await fetch('/WZ_DEPT/api/v1/select', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    conditions: {},
                    columns: "*",
                    order_by: "wzDeptOrgCd ASC",
                    limit: 1000,
                    one: false
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success && data.data) {
                    // DB 데이터를 프론트엔드 형식으로 변환
                    this.allDepartments = data.data.map(dept => ({
                        code: dept.wzdeptorgcd || dept.wzDeptOrgCd,
                        name: dept.wzdeptname || dept.wzDeptName,
                        parent: this.getParentDepartment(dept.wzdeptorgcd || dept.wzDeptOrgCd),
                        // category: '',  // 카테고리는 추후 구현
                        count: 0  // 규정 수는 추후 wz_rule과 연계
                    }));

                    // 각 부서별 규정 수 가져오기
                    await this.loadRegulationCounts();

                    // 처음에는 모든 부서 표시
                    this.departments = [...this.allDepartments];
                }
            }
        } catch (error) {
            console.error('Error loading departments:', error);
        }

        this.renderDepartmentTable();
    },

    // 부서별 규정 수 로드
    async loadRegulationCounts() {
        try {
            const response = await fetch('/api/v1/dept/regulation-counts', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success && data.counts) {
                    // 부서별 규정 수 업데이트 (전체 데이터에 적용)
                    data.counts.forEach(item => {
                        const dept = this.allDepartments.find(d => d.name === item.dept_name);
                        if (dept) {
                            dept.count = item.count;
                        }
                    });

                    // 현재 표시 중인 부서에도 적용
                    this.departments.forEach(dept => {
                        const allDept = this.allDepartments.find(d => d.code === dept.code);
                        if (allDept) {
                            dept.count = allDept.count;
                        }
                    });
                }
            }
        } catch (error) {
            console.error('Error loading regulation counts:', error);
        }
    },

    // 부서 검색
    searchDepartments() {
        const searchInput = document.getElementById('departmentSearchInput');
        if (!searchInput) return;

        this.searchQuery = searchInput.value.toLowerCase().trim();

        if (this.searchQuery === '') {
            // 검색어가 없으면 전체 표시
            this.departments = [...this.allDepartments];
        } else {
            // 검색 수행
            this.departments = this.allDepartments.filter(dept => {
                return dept.code.toLowerCase().includes(this.searchQuery) ||
                       dept.name.toLowerCase().includes(this.searchQuery) ||
                       dept.parent.toLowerCase().includes(this.searchQuery);
            });
        }

        this.renderDepartmentTable();
    },

    // 검색 초기화
    clearSearch() {
        const searchInput = document.getElementById('departmentSearchInput');
        if (searchInput) {
            searchInput.value = '';
        }
        this.searchQuery = '';
        this.departments = [...this.allDepartments];
        this.renderDepartmentTable();
    },

    // 부서 테이블 렌더링
    renderDepartmentTable() {
        const tbody = document.getElementById('departmentList');
        if (!tbody) return;

        tbody.innerHTML = '';

        // 정렬된 부서 목록 가져오기
        const sortedDepts = this.getSortedDepartments();

        if (sortedDepts.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align: center; padding: 40px; color: #999;">
                        부서 데이터가 없습니다.
                    </td>
                </tr>
            `;
            this.updateStats();
            return;
        }

        sortedDepts.forEach(dept => {
            const row = document.createElement('tr');
            row.classList.add('department-row');
            row.setAttribute('data-dept-name', dept.name);

            // 선택된 부서 하이라이트
            if (dept.name === this.selectedDeptName) {
                row.classList.add('selected');
            }

            row.innerHTML = `
                <td class="clickable-dept" onclick="DepartmentManager.selectDepartment('${dept.name}')" style="display: none;">${dept.code}</td>
                <td class="clickable-dept" onclick="DepartmentManager.selectDepartment('${dept.name}')">${dept.name}</td>
                <td>${dept.count}</td>
                <td>
                    <button class="action-btn btn-primary" onclick="DepartmentManager.editDepartment('${dept.code}')">편집</button>
                    <button class="action-btn btn-danger btn-sm" onclick="DepartmentManager.deleteDepartment('${dept.code}')">삭제</button>
                </td>
            `;
            tbody.appendChild(row);
        });

        this.updateStats();
    },

    // 부서 추가
    addDepartment() {
        // 현재 부서 코드 중 최댓값 찾기
        let maxCode = 0;
        this.allDepartments.forEach(dept => {
            const code = parseInt(dept.code);
            if (!isNaN(code) && code > maxCode) {
                maxCode = code;
            }
        });
        const newCode = maxCode + 100;

        // 모달 HTML 생성
        const modalHtml = `
            <div class="modal active" id="departmentModal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>부서 추가</h2>
                        <button class="modal-close" onclick="DepartmentManager.closeModal()">✕</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group" style="display: none;">
                            <label class="form-label">부서코드 <span class="required" style="color: #dc3545; font-size: 0.75em; vertical-align: super;">*필수</span></label>
                            <input type="text" class="form-input" id="deptCode" placeholder="예: 1100" value="${newCode}">
                        </div>
                        <div class="form-group">
                            <label class="form-label">부서명 <span class="required" style="color: #dc3545; font-size: 0.75em; vertical-align: super;">*필수</span></label>
                            <input type="text" class="form-input" id="deptName" placeholder="부서명 입력">
                        </div>
                        <!-- 상위부서 필드 삭제 -->
                        <input type="hidden" id="deptParent" value="기타">
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="DepartmentManager.closeModal()">취소</button>
                        <button class="btn btn-primary" onclick="DepartmentManager.saveDepartment()">저장</button>
                    </div>
                </div>
            </div>
        `;

        // 기존 모달 제거 후 새 모달 추가
        const existingModal = document.getElementById('departmentModal');
        if (existingModal) existingModal.remove();

        document.body.insertAdjacentHTML('beforeend', modalHtml);
    },

    // 부서 편집
    editDepartment(deptCode) {
        const dept = this.departments.find(d => d.code === deptCode);
        if (!dept) return;

        // 편집 모달 HTML 생성
        const modalHtml = `
            <div class="modal active" id="departmentModal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>부서 편집</h2>
                        <button class="modal-close" onclick="DepartmentManager.closeModal()">✕</button>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" id="editMode" value="true">
                        <input type="hidden" id="originalCode" value="${dept.code}">
                        <div class="form-group" style="display: none;">
                            <label class="form-label">부서코드</label>
                            <input type="text" class="form-input" id="deptCode" value="${dept.code}" readonly style="background: #f8f9fa;">
                        </div>
                        <div class="form-group">
                            <label class="form-label">부서명 <span class="required" style="color: #dc3545; font-size: 0.75em; vertical-align: super;">*필수</span></label>
                            <input type="text" class="form-input" id="deptName" value="${dept.name}">
                        </div>
                        <!-- 상위부서 필드 삭제 -->
                        <input type="hidden" id="deptParent" value="${dept.parent || '기타'}">
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="DepartmentManager.closeModal()">취소</button>
                        <button class="btn btn-primary" onclick="DepartmentManager.saveDepartment()">저장</button>
                    </div>
                </div>
            </div>
        `;

        // 기존 모달 제거 후 새 모달 추가
        const existingModal = document.getElementById('departmentModal');
        if (existingModal) existingModal.remove();
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    },

    // 부서 저장
    async saveDepartment() {
        const isEditMode = document.getElementById('editMode')?.value === 'true';
        const code = document.getElementById('deptCode').value.trim();
        const name = document.getElementById('deptName').value.trim();
        const parent = document.getElementById('deptParent').value.trim();

        // 유효성 검사
        if (!code || !name || !parent) {
            alert('모든 필수 항목을 입력해주세요.');
            return;
        }

        try {
            if (isEditMode) {
                // 편집 모드 - 부서명 수정
                const originalCode = document.getElementById('originalCode').value.trim();

                const response = await fetch(`/api/v1/dept/update/${originalCode}?new_name=${encodeURIComponent(name)}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include'
                });

                const data = await response.json();

                if (data.success) {
                    // DB 저장 성공 - 전체 부서 목록 다시 로드
                    this.showNotification(data.message, 'success');
                    this.closeModal();
                    // DB에서 최신 데이터 다시 로드
                    await this.loadDepartments();
                } else {
                    alert(data.message || '부서 수정 실패');
                }
            } else {
                // 추가 모드 - 새 부서 생성
                const response = await fetch(`/api/v1/dept/create?dept_code=${code}&dept_name=${encodeURIComponent(name)}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include'
                });

                const data = await response.json();

                if (data.success) {
                    // DB 저장 성공 - 전체 부서 목록 다시 로드
                    this.showNotification(data.message, 'success');
                    this.closeModal();
                    // DB에서 최신 데이터 다시 로드
                    await this.loadDepartments();
                } else {
                    if (data.error === 'duplicate') {
                        alert(data.message);
                    } else {
                        alert(data.message || '부서 추가 실패');
                    }
                }
            }
        } catch (error) {
            console.error('Error saving department:', error);
            alert('부서 저장 중 오류가 발생했습니다.');
        }
    },

    // 부서 삭제
    async deleteDepartment(deptCode) {
        const dept = this.departments.find(d => d.code === deptCode);
        if (!dept) return;

        if (!confirm(`"${dept.name}" 부서를 삭제하시겠습니까?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/v1/dept/delete/${deptCode}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            const data = await response.json();

            if (data.success) {
                // DB 삭제 성공 - 전체 부서 목록 다시 로드
                this.showNotification(data.message, 'warning');
                // DB에서 최신 데이터 다시 로드
                await this.loadDepartments();
            } else {
                if (data.error === 'has_regulations') {
                    alert(data.message);
                } else {
                    alert(data.message || '부서 삭제 실패');
                }
            }
        } catch (error) {
            console.error('Error deleting department:', error);
            alert('부서 삭제 중 오류가 발생했습니다.');
        }
    },

    // 모달 닫기
    closeModal() {
        const modal = document.getElementById('departmentModal');
        if (modal) {
            modal.remove();
        }
    },

    // 통계 업데이트
    updateStats() {
        const totalDepts = this.departments.length;
        const totalRegulations = this.departments.reduce((sum, dept) => sum + dept.count, 0);
        
        // 통계 표시 영역이 있다면 업데이트
        const statsArea = document.getElementById('departmentStats');
        if (statsArea) {
            statsArea.innerHTML = `
                <div>전체 부서: <strong>${totalDepts}</strong>개</div>
            `;
        }
    },

    // 부서별 내규 목록 가져오기
    getRegulationsByDepartment(deptCode) {
        // 실제 구현시 API 호출
        // return await fetch(`/api/departments/${deptCode}/regulations`);
        
        const dept = this.departments.find(d => d.code === deptCode);
        return dept ? dept.count : 0;
    },

    // 부서 목록 가져오기 (select box용)
    getDepartmentOptions() {
        return this.departments.map(dept => ({
            value: dept.name,
            text: `${dept.name} (${dept.code})`
        }));
    },

    // 정렬 기능
    sortBy(column) {
        if (this.sortState.column === column) {
            // 같은 컬럼 클릭 시 방향 토글
            this.sortState.direction = this.sortState.direction === 'asc' ? 'desc' : 'asc';
        } else {
            // 다른 컬럼 클릭 시 오름차순으로 초기화
            this.sortState.column = column;
            this.sortState.direction = 'asc';
        }

        this.renderDepartmentTable();
        this.updateSortIndicators();
    },

    // 정렬된 부서 목록 반환
    getSortedDepartments() {
        if (!this.sortState.column) {
            return this.departments;
        }

        const sorted = [...this.departments];
        const direction = this.sortState.direction === 'asc' ? 1 : -1;

        sorted.sort((a, b) => {
            let aVal, bVal;

            switch(this.sortState.column) {
                case 'code':
                    // 부서코드는 숫자로 비교
                    aVal = parseInt(a.code) || 0;
                    bVal = parseInt(b.code) || 0;
                    return (aVal - bVal) * direction;

                case 'name':
                    aVal = a.name || '';
                    bVal = b.name || '';
                    return aVal.localeCompare(bVal, 'ko') * direction;

                case 'parent':
                    aVal = a.parent || '';
                    bVal = b.parent || '';
                    return aVal.localeCompare(bVal, 'ko') * direction;

                case 'count':
                    aVal = a.count || 0;
                    bVal = b.count || 0;
                    return (aVal - bVal) * direction;

                default:
                    return 0;
            }
        });

        return sorted;
    },

    // 정렬 화살표 업데이트
    updateSortIndicators() {
        // 모든 정렬 화살표 제거 (content 초기화)
        document.querySelectorAll('.sort-indicator').forEach(el => {
            el.classList.remove('asc', 'desc');
        });

        // 현재 정렬 컬럼에 클래스 추가 (CSS ::after로 화살표 표시)
        if (this.sortState.column) {
            const indicator = document.querySelector(`.sort-indicator[data-column="${this.sortState.column}"]`);
            if (indicator) {
                indicator.classList.add(this.sortState.direction);
            }
        }
    },

    // 부서 선택 및 내규 목록 표시
    async selectDepartment(deptName) {
        this.selectedDeptName = deptName;

        // 선택된 부서 하이라이트
        document.querySelectorAll('.department-row').forEach(row => {
            if (row.getAttribute('data-dept-name') === deptName) {
                row.classList.add('selected');
            } else {
                row.classList.remove('selected');
            }
        });

        // 내규 패널 업데이트
        const panel = document.getElementById('regulationPanel');
        panel.innerHTML = '<div style="text-align: center; padding: 20px;">로딩 중...</div>';

        try {
            // API 호출로 해당 부서의 내규 목록 가져오기
            const response = await fetch(`/api/v1/dept/${encodeURIComponent(deptName)}/regulations`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.displayRegulations(data.regulations || [], deptName);
            } else {
                panel.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">내규를 불러올 수 없습니다.</div>';
            }
        } catch (error) {
            console.error('Error loading regulations:', error);
            panel.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">내규를 불러올 수 없습니다.</div>';
        }
    },

    // 내규 목록 표시
    displayRegulations(regulations, deptName) {
        const panel = document.getElementById('regulationPanel');

        if (!regulations || regulations.length === 0) {
            panel.innerHTML = `
                <div style="padding: 20px; text-align: center; color: #999;">
                    <h5>"${deptName}" 부서</h5>
                    <p>등록된 내규가 없습니다.</p>
                </div>
            `;
            return;
        }

        // 분류번호 자연 정렬
        regulations.sort(this.naturalSort);

        let html = `
            <div style="padding: 15px;">
                <h5 style="margin-bottom: 15px;">"${deptName}" 부서 (${regulations.length}개)</h5>
                <div style="max-height: 550px; overflow-y: auto;">
        `;

        regulations.forEach(reg => {
            // 따옴표 이스케이프 처리
            const escapedName = (reg.wzname || '제목 없음').replace(/'/g, "\\'").replace(/"/g, "&quot;");
            const escapedJsonPath = (reg.wzfilejson || '').replace(/'/g, "\\'").replace(/"/g, "&quot;");
            html += `
                <div class="regulation-item" onclick="DepartmentManager.showRegulationDetail('${reg.wzruleseq}', '${escapedName}', '${escapedJsonPath}')">
                    <div class="regulation-pubno">${reg.wzpubno || '-'}</div>
                    <div class="regulation-name">${reg.wzname || '제목 없음'}</div>
                    <div class="regulation-date">
                        제정: ${this.formatDate(reg.wzestabdate)} |
                        개정: ${this.formatDate(reg.wzlastrevdate)}
                    </div>
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;

        panel.innerHTML = html;
    },

    // 날짜 포맷
    formatDate(dateStr) {
        if (!dateStr) return '-';
        if (typeof dateStr === 'string' && dateStr.includes('T')) {
            return dateStr.split('T')[0];
        }
        return dateStr;
    },

    // 자연 정렬 (분류번호용)
    naturalSort(a, b) {
        const aPubno = a.wzpubno || '';
        const bPubno = b.wzpubno || '';

        // 분류번호를 숫자 배열로 변환 (예: "1.2.3" -> [1, 2, 3])
        const aParts = aPubno.split('.').map(part => parseInt(part) || 0);
        const bParts = bPubno.split('.').map(part => parseInt(part) || 0);

        const maxLength = Math.max(aParts.length, bParts.length);

        for (let i = 0; i < maxLength; i++) {
            const aPart = aParts[i] || 0;
            const bPart = bParts[i] || 0;

            if (aPart !== bPart) {
                return aPart - bPart;
            }
        }

        return 0;
    },

    // 내규 상세 보기 - 미리보기 모달 표시
    async showRegulationDetail(ruleId, ruleName, jsonPath) {
        console.log('showRegulationDetail called with:', ruleId, ruleName, jsonPath);

        // 미리보기 모달 표시
        const modal = document.getElementById('regulationPreviewModal');
        const titleElement = document.getElementById('previewTitle');
        const contentElement = document.getElementById('previewContent');

        if (!modal) {
            console.error('Modal element not found');
            return;
        }

        // 모달 표시 및 로딩 상태
        modal.style.display = 'flex';
        titleElement.textContent = ruleName || '내규 미리보기';
        contentElement.innerHTML = '<div style="text-align: center; padding: 40px;">로딩 중...</div>';

        try {
            // wzfilejson 경로가 있으면 JSON 파일 읽기
            if (jsonPath && jsonPath.trim()) {
                await this.loadRegulationContent(jsonPath, contentElement);
            } else {
                // wzfilejson이 없는 경우 테스트용 JSON 파일 사용
                const testJsonPath = 'applib/merge_json/merged_1.1.1._정확한_환자_확인_20250924_122329.json';
                console.log('Using test JSON path:', testJsonPath);
                await this.loadRegulationContent(testJsonPath, contentElement);
            }
        } catch (error) {
            console.error('Error loading regulation detail:', error);
            contentElement.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">오류가 발생했습니다.</div>';
        }
    },

    // JSON 파일에서 내규 내용 로드
    async loadRegulationContent(jsonPath, contentElement) {
        try {
            // JSON 파일 경로 정리
            const cleanPath = jsonPath.replace(/^\//, '');
            const response = await fetch(`/${cleanPath}`);

            if (response.ok) {
                const jsonData = await response.json();

                // JSON 데이터를 HTML로 변환하여 표시
                let html = '<div style="padding: 20px;">';

                if (jsonData.title) {
                    html += `<h3>${jsonData.title}</h3>`;
                }

                if (jsonData.chapters && Array.isArray(jsonData.chapters)) {
                    jsonData.chapters.forEach(chapter => {
                        if (chapter.title) {
                            html += `<h4 style="margin-top: 20px; color: #333;">${chapter.title}</h4>`;
                        }

                        if (chapter.articles && Array.isArray(chapter.articles)) {
                            chapter.articles.forEach(article => {
                                if (article.title) {
                                    html += `<h5 style="margin-top: 15px; color: #555;">${article.title}</h5>`;
                                }
                                if (article.content) {
                                    html += `<p style="margin-left: 20px; line-height: 1.6;">${article.content}</p>`;
                                }

                                // 항 처리
                                if (article.items && Array.isArray(article.items)) {
                                    html += '<ol style="margin-left: 40px;">';
                                    article.items.forEach(item => {
                                        html += `<li style="margin: 5px 0;">${item}</li>`;
                                    });
                                    html += '</ol>';
                                }
                            });
                        }
                    });
                } else if (jsonData.content) {
                    // 단순 텍스트 콘텐츠
                    const lines = jsonData.content.split('\n');
                    lines.forEach(line => {
                        if (line.trim()) {
                            if (line.startsWith('제') && (line.includes('조') || line.includes('장'))) {
                                html += `<h5 style="margin-top: 15px; color: #555;">${line}</h5>`;
                            } else if (line.startsWith('①') || line.startsWith('②') || line.startsWith('③')) {
                                html += `<p style="margin-left: 20px; line-height: 1.6;">${line}</p>`;
                            } else {
                                html += `<p style="line-height: 1.6;">${line}</p>`;
                            }
                        }
                    });
                } else {
                    // JSON 데이터를 그대로 표시
                    html += '<pre style="white-space: pre-wrap; font-family: inherit;">';
                    html += JSON.stringify(jsonData, null, 2);
                    html += '</pre>';
                }

                html += '</div>';
                contentElement.innerHTML = html;
            } else {
                contentElement.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #999;">
                        내규 내용을 불러올 수 없습니다.<br>
                        <small>경로: ${jsonPath}</small>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading regulation content:', error);
            contentElement.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">내규 내용을 불러오는 중 오류가 발생했습니다.</div>';
        }
    },

    // 미리보기 모달 닫기
    closePreview() {
        const modal = document.getElementById('regulationPreviewModal');
        if (modal) {
            modal.style.display = 'none';
        }
    },

    // 알림 표시
    showNotification(message, type = 'success') {
        if (typeof RegulationEditor !== 'undefined' && RegulationEditor.showNotification) {
            RegulationEditor.showNotification(message, type);
        } else {
            alert(message);
        }
    },

    // API 호출 메서드 (실제 구현시 백엔드 연동)
    async saveDepartmentToServer(dept) {
        console.log('부서 저장:', dept);
        // const response = await fetch('/api/departments', {
        //     method: 'POST',
        //     headers: {'Content-Type': 'application/json'},
        //     body: JSON.stringify(dept)
        // });
    },

    async deleteDepartmentFromServer(deptCode) {
        console.log('부서 삭제:', deptCode);
        // await fetch(`/api/departments/${deptCode}`, {
        //     method: 'DELETE'
        // });
    }
};
