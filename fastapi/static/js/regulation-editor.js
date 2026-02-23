// regulation-editor.js - 메인 편집기 기능

const RegulationEditor = {
    // 상태 관리
    regulations: [],
    selectedRegulations: new Set(),
    openEditWindows: new Map(),
    currentTab: '현행사규목록',  // 기본 탭 설정
    currentSort: {
        column: null,
        direction: 'asc' // 'asc' 또는 'desc'
    },

    // 비동기 작업 관리
    activeAsyncTasks: new Map(), // task_id => { type, filename, started_at, interval_id }
    taskPollingInterval: 2000,   // 2초마다 폴링

    // 통합 상태 관리
    currentEditingRegulation: null,
    currentRevisingRegulation: null,
    lastParsedContent: null,
    lastUploadedFiles: null,
    regulationStatus: '현행',  // 현행/연혁 상태
    
    // 샘플 데이터 (개정일과 분류 추가)
    sampleRegulations: [
        {
            id: 1,
            title: '인사관리규정',
            department: '인사팀',
            revisionDate: '2024.03.01',  // 개정일 추가
            classification: '2.1',         // 분류 추가
            announceDate: '2024.01.15',
            effectiveDate: '2024.02.01',
            status: 'active',
            version: '1.0',
            content: {
                articles: [
                    { number: 1, title: '목적', content: '이 규정은 회사의 인사관리에 관한 사항을 정함을 목적으로 한다.' },
                    { number: 2, title: '적용범위', content: '이 규정은 전 직원에게 적용된다.' }
                ],
                appendix: '이 규정은 2024년 2월 1일부터 시행한다.',
                history: []
            }
        },
        {
            id: 2,
            title: '재무관리규정',
            department: '재무팀',
            revisionDate: '2024.03.15',  // 개정일 추가
            classification: '3.1',         // 분류 추가
            announceDate: '2024.03.01',
            effectiveDate: '2024.03.15',
            status: 'review',
            version: '2.1',
            content: {
                articles: [],
                appendix: '',
                history: [
                    { date: '2023.01.01', type: '제정', description: '최초 제정' },
                    { date: '2024.03.01', type: '일부개정', description: '예산 관리 조항 수정' }
                ]
            }
        },
        {
            id: 3,
            title: '정보보안규정',
            department: 'IT팀',
            revisionDate: '2024.02.20',  // 개정일 추가
            classification: '5.2',         // 분류 추가
            announceDate: '2024.02.20',
            effectiveDate: '2024.03.01',
            status: 'draft',
            version: '1.0',
            content: {
                articles: [],
                appendix: '',
                history: []
            }
        }
    ],

    // 날짜 형식 변환 함수
    formatDateForDisplay(dateString) {
        if (!dateString) return '-';
        
        // YYYY-MM-DD 형식을 YYYY.MM.DD. 형식으로 변환
        if (dateString.includes('-')) {
            const parts = dateString.split('-');
            if (parts.length === 3) {
                return `${parts[0]}.${parts[1]}.${parts[2]}.`;
            }
        }
        
        // 이미 올바른 형식이면 그대로 반환
        return dateString;
    },

    // 초기화
    init() {
        // 초기 탭 설정
        this.currentTab = '현행사규목록';

        // 첫 번째 탭 버튼을 활성화
        const firstTab = document.querySelector('.nav-tab');
        if (firstTab) {
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            firstTab.classList.add('active');
        }

        // DB에서 현행 데이터 로드
        this.loadRegulationsFromDB();
        this.setupEventListeners();
        this.loadClassificationFilter();
        this.loadDepartmentFilter();  // 부서 필터 동적 로드
        this.setupFileChangeListeners();  // 파일 업로드 이벤트 리스너 설정
    },
    
    // DB에서 규정 목록 로드
    async loadRegulationsFromDB() {
        console.log('Loading regulations for tab:', this.currentTab);

        // 로딩 상태 표시
        const tbody = document.getElementById(this.currentTab === '연혁목록' ? 'historyList' : 'regulationList');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 40px;">데이터를 불러오는 중...</td></tr>';
        }

        try {
            // 타임아웃 설정 (10초)
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);

            // 현재 탭에 따라 다른 API 호출
            const isCurrentTab = this.currentTab === '현행사규목록';
            const apiEndpoint = isCurrentTab ? '/api/v1/regulations/current' : '/api/v1/regulations/history';

            const response = await fetch(apiEndpoint, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',  // 쿠키 포함
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                console.error('API Response Error:', response.status, response.statusText);
                throw new Error(`Failed to fetch regulations: ${response.status}`);
            }
            
            const data = await response.json();

            if (data.success && data.data) {
                // API 응답 데이터를 프론트엔드 형식으로 변환
                this.regulations = data.data.map(rule => {
                    // 상태 변환
                    let status = 'active';
                    const editType = rule.edit_type || '';
                    const isHistory = rule.status === '연혁';

                    if (isHistory) {
                        status = 'history';
                    } else if (editType && editType.includes('개정')) {
                        status = 'revision';
                    } else if (editType === '검토중') {
                        status = 'review';
                    } else if (editType === '작성중') {
                        status = 'draft';
                    }

                    // wzpubno를 분류로 사용 (전체 번호 유지)
                    let classification = rule.wzpubno || rule.publication_no || rule.classification || '';

                    // 제정일 확인용 로그
                    if (rule.established_date) {
                        console.log('[Regulation List] Rule has established_date:', rule.name, rule.established_date);
                    } else {
                        console.log('[Regulation List] Rule missing established_date:', rule.name);
                    }

                    return {
                        id: rule.wzruleseq || rule.wz_rule_id || rule.rule_id || rule.id,
                        title: rule.name || '제목 없음',
                        department: rule.department || rule.wzmgrdptnm || '',
                        wzreldptnm: rule.wzreldptnm || rule.related_department || '',
                        revisionDate: this.formatDateForDisplay(rule.last_revised_date),
                        classification: classification || '미분류',
                        wzpubno: rule.wzpubno || rule.publication_no || '', // wzpubno 추가
                        announceDate: this.formatDateForDisplay(rule.established_date),
                        effectiveDate: this.formatDateForDisplay(rule.execution_date),
                        status: status,
                        version: `1.0`,
                        publicationNo: rule.publication_no,
                        contentPath: rule.content_path,
                        content: {
                            articles: [],
                            appendix: '',
                            history: []
                        },
                        // 원본 데이터 저장 (디버깅용)
                        wzestabdate: rule.established_date,
                        wzlastrevdate: rule.last_revised_date,
                        wzexecdate: rule.execution_date
                    };
                });

                // 백엔드에서 이미 wzCateSeq로 정렬되어 옴 - 추가 정렬 불필요
                console.log('Regulations loaded and already sorted by wzCateSeq');

            } else {
                console.error('No data received from server');
                this.regulations = [];
                this.loadRegulations();
            }
        } catch (error) {
            console.error('Error loading regulations from DB:', error);
            
            // 타임아웃 에러 처리
            if (error.name === 'AbortError') {
                console.error('Request timeout - API took too long to respond');
                alert('서버 응답 시간이 초과되었습니다. 샘플 데이터를 사용합니다.');
            }
            
            // 에러 시 샘플 데이터 사용 (폴백)
            this.regulations = [...this.sampleRegulations];
            this.loadRegulations();
        }
    },
    
    // 부서 필터 동적 로드
    async loadDepartmentFilter() {
        try {
            // 부서 목록 API 호출
            const response = await fetch('/api/v1/dept/list', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include'  // 쿠키 포함
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success && data.departments) {
                    // 부서 필터 업데이트
                    const departmentFilter = document.getElementById('departmentFilter');
                    const newDepartmentSelect = document.getElementById('newDepartment');
                    const searchDepartmentSelect = document.getElementById('searchDepartmentSelect');

                    // 기존 옵션 제거 (첫 번째 "모든 부서" 제외)
                    if (departmentFilter) {
                        while (departmentFilter.options.length > 1) {
                            departmentFilter.remove(1);
                        }

                        // 새 옵션 추가
                        data.departments.forEach(dept => {
                            const option = document.createElement('option');
                            option.value = dept.name;
                            option.textContent = dept.name;
                            departmentFilter.appendChild(option);
                        });
                    }

                    // 제정 모달의 부서 선택도 업데이트
                    if (newDepartmentSelect) {
                        while (newDepartmentSelect.options.length > 1) {
                            newDepartmentSelect.remove(1);
                        }

                        data.departments.forEach(dept => {
                            const option = document.createElement('option');
                            option.value = dept.name;
                            option.textContent = dept.name;
                            newDepartmentSelect.appendChild(option);
                        });
                    }

                    // 상세 검색 탭의 부서 선택도 업데이트
                    if (searchDepartmentSelect) {
                        // 기존 옵션 모두 제거
                        searchDepartmentSelect.innerHTML = '';

                        data.departments.forEach(dept => {
                            const option = document.createElement('option');
                            option.value = dept.code;
                            option.textContent = dept.name;
                            searchDepartmentSelect.appendChild(option);
                        });
                    }
                }
            }
        } catch (error) {
            console.error('Error loading departments:', error);
        }
    },

    // 분류번호 필터 로드
    loadClassificationFilter() {
        const classificationFilter = document.getElementById('classificationFilter');
        if (!classificationFilter) return;

        // ClassificationManager에서 분류 목록 가져오기
        if (typeof ClassificationManager !== 'undefined') {
            const classifications = ClassificationManager.getAllClassifications();
            
            // 기존 옵션 제거 (첫 번째 "모든 분류" 제외)
            while (classificationFilter.options.length > 1) {
                classificationFilter.remove(1);
            }
            
            // 새 옵션 추가
            classifications.forEach(item => {
                const option = document.createElement('option');
                option.value = item.value;
                option.textContent = item.text;
                classificationFilter.appendChild(option);
            });
        }
    },

    // 정렬 기능
    sortBy(column) {
        // 같은 컬럼을 다시 클릭하면 정렬 방향 토글
        if (this.currentSort.column === column) {
            this.currentSort.direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.currentSort.column = column;
            this.currentSort.direction = 'asc';
        }

        // 정렬 수행
        this.regulations.sort((a, b) => {
            let aVal = a[column];
            let bVal = b[column];

            // null/undefined 처리
            if (aVal === null || aVal === undefined || aVal === '') aVal = '';
            if (bVal === null || bVal === undefined || bVal === '') bVal = '';

            // 날짜 형식 처리 (YYYY.MM.DD. 형식)
            if (column === 'revisionDate' || column === 'announceDate' || column === 'effectiveDate') {
                // 날짜 문자열을 비교 가능한 형식으로 변환
                aVal = aVal.replace(/\./g, '');
                bVal = bVal.replace(/\./g, '');
            }

            // 분류는 자연 정렬 (natural sort) - wzpubno 우선 사용
            if (column === 'classification') {
                // wzpubno를 우선 사용, 없으면 classification 사용
                const aStr = (a.wzpubno || a.classification || '').toString();
                const bStr = (b.wzpubno || b.classification || '').toString();

                // 자연 정렬 비교 함수 (개선된 버전)
                const naturalCompare = (a, b) => {
                    // 점(.)으로 구분하고 빈 문자열 제거
                    const aParts = a.split('.').filter(part => part.trim() !== '').map(part => {
                        const trimmed = part.trim();
                        const num = parseInt(trimmed, 10);
                        return isNaN(num) ? trimmed : num;
                    });
                    const bParts = b.split('.').filter(part => part.trim() !== '').map(part => {
                        const trimmed = part.trim();
                        const num = parseInt(trimmed, 10);
                        return isNaN(num) ? trimmed : num;
                    });

                    // 각 부분을 순차적으로 비교
                    const maxLength = Math.max(aParts.length, bParts.length);
                    for (let i = 0; i < maxLength; i++) {
                        const aPart = aParts[i] !== undefined ? aParts[i] : 0; // 기본값을 0으로 변경
                        const bPart = bParts[i] !== undefined ? bParts[i] : 0; // 기본값을 0으로 변경

                        // 둘 다 숫자인 경우
                        if (typeof aPart === 'number' && typeof bPart === 'number') {
                            if (aPart !== bPart) {
                                return aPart - bPart;
                            }
                        }
                        // 하나는 숫자, 하나는 문자인 경우 (숫자가 먼저)
                        else if (typeof aPart === 'number' && typeof bPart === 'string') {
                            return -1;
                        }
                        else if (typeof aPart === 'string' && typeof bPart === 'number') {
                            return 1;
                        }
                        // 둘 다 문자인 경우
                        else {
                            const comparison = aPart.localeCompare(bPart);
                            if (comparison !== 0) {
                                return comparison;
                            }
                        }
                    }
                    return 0;
                };

                const compareResult = naturalCompare(aStr, bStr);
                if (compareResult !== 0) {
                    return this.currentSort.direction === 'asc' ? compareResult : -compareResult;
                }
            }

            // 비교
            let result = 0;
            if (aVal < bVal) result = -1;
            else if (aVal > bVal) result = 1;

            // 정렬 방향 적용
            return this.currentSort.direction === 'asc' ? result : -result;
        });

        // 테이블 다시 렌더링
        this.loadRegulations();

        // 정렬 인디케이터 업데이트
        this.updateSortIndicators();
    },

    // 정렬 인디케이터 업데이트
    updateSortIndicators() {
        // 모든 인디케이터 초기화
        document.querySelectorAll('.sort-indicator').forEach(indicator => {
            indicator.className = 'sort-indicator';
        });

        // 현재 정렬 컬럼의 인디케이터 업데이트
        if (this.currentSort.column) {
            const indicator = document.querySelector(`.sort-indicator[data-column="${this.currentSort.column}"]`);
            if (indicator) {
                indicator.className = `sort-indicator ${this.currentSort.direction}`;
            }
        }
    },

    // 규정 목록 로드
    loadRegulations() {
        // 현재 탭에 따라 다른 tbody 사용
        const isHistory = this.currentTab === '연혁목록';
        const tbody = document.getElementById(isHistory ? 'historyList' : 'regulationList');

        if (!tbody) {
            console.error('tbody not found for:', this.currentTab);
            return;
        }

        tbody.innerHTML = '';

        // 데이터가 없는 경우
        if (!this.regulations || this.regulations.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${isHistory ? 6 : 10}" style="text-align: center; padding: 40px;">데이터가 없습니다.</td></tr>`;
            return;
        }

        this.regulations.forEach(reg => {
            const row = document.createElement('tr');

            // 연혁목록과 현행목록의 테이블 구조가 다름
            if (isHistory) {
                row.innerHTML = `
                    <td>
                        <a href="javascript:void(0)" onclick="RegulationEditor.openEditWindow(${reg.id})"
                           style="text-decoration: none; color: #333; cursor: pointer;"
                           onmouseover="this.style.color='#667eea'; this.style.textDecoration='underline'"
                           onmouseout="this.style.color='#333'; this.style.textDecoration='none'">
                            <strong>${reg.title}</strong>
                        </a>
                    </td>
                    <td>-</td>
                    <td>${reg.revisionDate ? this.formatDateForDisplay(reg.revisionDate) : '-'}</td>
                    <td style="display: none;"><span class="status-badge status-history">연혁</span></td>
                    <td style="display: none;">-</td>
                    <td>
                        <div class="action-buttons">
                            <button class="action-btn btn-info" onclick="RegulationEditor.viewRegulation(${reg.id})">
                                👁️ 보기
                            </button>
                        </div>
                    </td>
                `;
            } else {
                row.innerHTML = `
                    <td style="display: none;">
                        <input type="checkbox" class="row-checkbox" value="${reg.id}"
                               onchange="RegulationEditor.toggleSelection(${reg.id})">
                    </td>
                    <td>
                        <span class="classification-badge">${reg.wzpubno || reg.classification || '미분류'}</span>
                    </td>
                    <td>
                        <a href="javascript:void(0)" onclick="RegulationEditor.openEditWindow(${reg.id})"
                           style="text-decoration: none; color: #333; cursor: pointer;"
                           onmouseover="this.style.color='#667eea'; this.style.textDecoration='underline'"
                           onmouseout="this.style.color='#333'; this.style.textDecoration='none'">
                            <strong>${reg.title}</strong>
                        </a>
                    </td>
                    <td>${reg.department || '-'}</td>
                    <td>${reg.wzreldptnm || reg.relatedDepartment || '-'}</td>
                    <td title="제정일: ${reg.wzestabdate || '없음'}">${reg.announceDate || '-'}</td>
                    <td>${reg.revisionDate ? this.formatDateForDisplay(reg.revisionDate) : '-'}</td>
                    <td>${reg.effectiveDate ? this.formatDateForDisplay(reg.effectiveDate) : '-'}</td>
                    <td style="display: none;">
                        <span class="status-badge status-${reg.status}">
                            ${this.getStatusText(reg.status)}
                        </span>
                    </td>
                    <td style="display: none;">${reg.version}</td>
                    <td>
                        <div class="action-buttons">
                            <button class="action-btn btn-primary" onclick="RegulationEditor.openEditWindow(${reg.id})">
                                ✏️ 편집
                            </button>
                            ${this.currentTab === '현행사규목록' ?
                                `<button class="action-btn btn-warning" onclick="RegulationEditor.reviseRegulation(${reg.id})" title="개정">
                                    📝 개정
                                </button>` : ''}
                            <button class="action-btn btn-info" onclick="RegulationEditor.viewRegulation(${reg.id})">
                                👁️ 보기
                            </button>
                        </div>
                    </td>
                `;
            }
            tbody.appendChild(row);
        });
    },

    // 상태 텍스트 변환
    getStatusText(status) {
        const statusMap = {
            'active': '시행중',
            'draft': '작성중',
            'review': '검토중',
            'revision': '개정중'
        };
        return statusMap[status] || status;
    },

    // 탭 전환
    switchTab(tab) {
        // 탭 버튼 활성화
        document.querySelectorAll('.nav-tab').forEach(t => {
            t.classList.remove('active');
        });
        if (event && event.target) {
            event.target.classList.add('active');
        }

        // 탭 컨텐츠 전환
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        // 탭 ID 매핑
        let tabId = '';
        if (tab === '현행사규목록') {
            tabId = 'regulationsTab';
            this.currentTab = '현행사규목록';
            this.loadRegulationsFromDB(); // DB에서 현행 데이터 로드
        } else if (tab === '연혁목록') {
            tabId = 'historyTab';
            this.currentTab = '연혁목록';
            this.loadRegulationsFromDB(); // DB에서 연혁 데이터 로드
        } else {
            tabId = tab + 'Tab';
        }

        const tabContent = document.getElementById(tabId);
        if (tabContent) {
            tabContent.classList.add('active');
        }
        
        // 탭별 데이터 로드
        switch(tab) {
            case 'history':
                this.loadHistoryList();
                break;
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
            case 'search':
                // 상세 검색 탭 초기화
                this.initAdvancedSearch();
                break;
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
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                console.log('Department data received:', data);
                const checkboxContainer = document.getElementById('searchDepartmentCheckboxes');

                if (checkboxContainer) {
                    checkboxContainer.innerHTML = '';

                    // data.departments 또는 data.data 확인
                    const departments = data.departments || data.data || [];

                    if (departments.length === 0) {
                        checkboxContainer.innerHTML = '<p style="color: #999; text-align: center;">부서 목록을 불러올 수 없습니다.</p>';
                    } else {
                        departments.forEach(dept => {
                            const label = document.createElement('label');
                            label.style.cssText = 'display: block; padding: 5px; cursor: pointer; user-select: none;';
                            label.onmouseover = () => label.style.backgroundColor = '#f0f0f0';
                            label.onmouseout = () => label.style.backgroundColor = 'transparent';

                            const checkbox = document.createElement('input');
                            checkbox.type = 'checkbox';
                            // dept.dept_name 또는 dept.name 확인
                            checkbox.value = dept.dept_name || dept.name || dept;
                            checkbox.style.marginRight = '8px';
                            checkbox.className = 'dept-checkbox';

                            label.appendChild(checkbox);
                            label.appendChild(document.createTextNode(dept.dept_name || dept.name || dept));
                            checkboxContainer.appendChild(label);
                        });
                    }
                }
            } else {
                console.error('Failed to load departments:', response.status);
                const checkboxContainer = document.getElementById('searchDepartmentCheckboxes');
                if (checkboxContainer) {
                    checkboxContainer.innerHTML = '<p style="color: #999; text-align: center;">부서 목록을 불러올 수 없습니다.</p>';
                }
            }
        } catch (error) {
            console.error('Error loading departments for search:', error);
            const checkboxContainer = document.getElementById('searchDepartmentCheckboxes');
            if (checkboxContainer) {
                checkboxContainer.innerHTML = '<p style="color: #999; text-align: center;">부서 목록을 불러올 수 없습니다.</p>';
            }
        }
    },

    // 상세 검색 실행
    async performAdvancedSearch() {
        // 폼 데이터 수집 - 날짜 필드를 위한 더 정확한 선택자 사용
        const dateInputs = document.querySelectorAll('#searchTab .date-range input');
        const checkedDepts = Array.from(document.querySelectorAll('#searchDepartmentCheckboxes input[type="checkbox"]:checked'));
        const searchData = {
            keyword: document.querySelector('#searchTab input[type="text"]').value,
            departments: checkedDepts.map(cb => cb.value),
            announceStartDate: dateInputs[0] ? dateInputs[0].value : '',
            announceEndDate: dateInputs[1] ? dateInputs[1].value : '',
            effectiveStartDate: dateInputs[2] ? dateInputs[2].value : '',
            effectiveEndDate: dateInputs[3] ? dateInputs[3].value : ''
        };

        console.log('Advanced search data:', searchData);

        // 적용된 필터 저장 (표시용)
        this.lastSearchFilters = searchData;

        try {
            // API 호출
            let url = '/api/v1/regulations/advanced-search?';
            const params = new URLSearchParams();

            if (searchData.keyword) params.append('search', searchData.keyword);
            if (searchData.departments.length > 0) {
                searchData.departments.forEach(dept => params.append('department', dept));
            }
            if (searchData.announceStartDate) params.append('announce_start', searchData.announceStartDate);
            if (searchData.announceEndDate) params.append('announce_end', searchData.announceEndDate);
            if (searchData.effectiveStartDate) params.append('effective_start', searchData.effectiveStartDate);
            if (searchData.effectiveEndDate) params.append('effective_end', searchData.effectiveEndDate);

            console.log('API URL:', url + params.toString());

            const response = await fetch(url + params.toString(), {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                console.log('Search response:', data);
                if (data.success) {
                    this.displayAdvancedSearchResults(data.data, searchData);
                } else {
                    alert('검색 중 오류가 발생했습니다.');
                }
            } else {
                console.error('Search failed:', response.status, response.statusText);
                const errorText = await response.text();
                console.error('Error details:', errorText);
                alert('검색 요청 실패: ' + response.statusText);
            }
        } catch (error) {
            console.error('Advanced search error:', error);
            alert('검색 중 오류가 발생했습니다.');
        }
    },

    // 상세 검색 결과 표시
    displayAdvancedSearchResults(results, filters) {
        // 검색 결과 테이블이 없으면 생성
        let resultContainer = document.getElementById('advancedSearchResults');
        if (!resultContainer) {
            const searchPanel = document.querySelector('#searchTab .search-panel');
            resultContainer = document.createElement('div');
            resultContainer.id = 'advancedSearchResults';
            resultContainer.innerHTML = `
                <div id="appliedFilters" style="margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 8px; margin-bottom: 20px;">
                    <h5 style="margin: 0 0 10px 0;">적용된 필터</h5>
                    <div id="filterList" style="display: flex; flex-wrap: wrap; gap: 10px;"></div>
                </div>
                <h4 style="margin-top: 20px;">검색 결과 (<span id="resultCount">0</span>건)</h4>
                <table class="regulation-table" style="margin-top: 15px;">
                    <thead>
                        <tr>
                            <th>제목</th>
                            <th width="100">분류번호</th>
                            <th width="100">소관부서</th>
                            <th width="100">제정일</th>
                            <th width="100">시행일</th>
                            <th width="80">상태</th>
                            <th width="120">작업</th>
                        </tr>
                    </thead>
                    <tbody id="advancedSearchResultList">
                    </tbody>
                </table>
            `;
            searchPanel.appendChild(resultContainer);
        }

        // 적용된 필터 표시
        const filterList = document.getElementById('filterList');
        filterList.innerHTML = '';

        if (filters.keyword) {
            this.addFilterBadge(filterList, '검색어', filters.keyword, 'keyword', filters.keyword);
        }
        if (filters.departments && filters.departments.length > 0) {
            filters.departments.forEach(dept => {
                this.addFilterBadge(filterList, '부서', dept, 'department', dept);
            });
        }
        if (filters.announceStartDate) {
            this.addFilterBadge(filterList, '공포일 시작', filters.announceStartDate, 'announceStart', filters.announceStartDate);
        }
        if (filters.announceEndDate) {
            this.addFilterBadge(filterList, '공포일 종료', filters.announceEndDate, 'announceEnd', filters.announceEndDate);
        }
        if (filters.effectiveStartDate) {
            this.addFilterBadge(filterList, '시행일 시작', filters.effectiveStartDate, 'effectiveStart', filters.effectiveStartDate);
        }
        if (filters.effectiveEndDate) {
            this.addFilterBadge(filterList, '시행일 종료', filters.effectiveEndDate, 'effectiveEnd', filters.effectiveEndDate);
        }

        if (filterList.children.length === 0) {
            filterList.innerHTML = '<span style="color: #6c757d;">필터가 적용되지 않았습니다.</span>';
        }

        // 결과 개수 업데이트
        document.getElementById('resultCount').textContent = results.length;

        // 결과 표시
        const tbody = document.getElementById('advancedSearchResultList');
        tbody.innerHTML = '';

        if (results.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 40px;">검색 결과가 없습니다.</td></tr>';
            return;
        }

        results.forEach(rule => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${rule.name || '제목 없음'}</td>
                <td>${rule.publication_no || '-'}</td>
                <td>${rule.department || '-'}</td>
                <td>${this.formatDateForDisplay(rule.established_date)}</td>
                <td>${this.formatDateForDisplay(rule.execution_date)}</td>
                <td>
                    <span class="status-badge status-${rule.status === '현행' ? 'active' : 'history'}">
                        ${rule.status === '현행' ? '시행중' : '연혁'}
                    </span>
                </td>
                <td>
                    <button class="action-btn btn-primary" onclick="RegulationEditor.viewRegulation(${rule.wzruleseq || rule.wz_rule_id || rule.rule_id || rule.id})">보기</button>
                    <button class="action-btn btn-secondary" onclick="RegulationEditor.openEditWindow(${rule.wzruleseq || rule.wz_rule_id || rule.rule_id || rule.id})">편집</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    },

    // 필터 배지 추가
    addFilterBadge(container, label, value, filterType, filterValue) {
        const badgeWrapper = document.createElement('span');
        badgeWrapper.style.cssText = 'display: inline-flex; align-items: center; padding: 5px 10px; background: #667eea; color: white; border-radius: 15px; font-size: 13px; margin-right: 5px;';

        const badgeText = document.createElement('span');
        badgeText.innerHTML = `<strong>${label}:</strong> ${value}`;
        badgeWrapper.appendChild(badgeText);

        const removeBtn = document.createElement('span');
        removeBtn.innerHTML = '×';
        removeBtn.style.cssText = 'margin-left: 8px; cursor: pointer; font-size: 16px; font-weight: bold; opacity: 0.8;';
        removeBtn.onmouseover = () => removeBtn.style.opacity = '1';
        removeBtn.onmouseout = () => removeBtn.style.opacity = '0.8';
        removeBtn.onclick = () => this.removeFilterAndReSearch(filterType, filterValue);

        badgeWrapper.appendChild(removeBtn);
        container.appendChild(badgeWrapper);
    },

    // 필터 제거 및 재검색
    removeFilterAndReSearch(filterType, filterValue) {
        console.log('Removing filter:', filterType, filterValue);

        // 해당 필터 제거
        if (filterType === 'keyword') {
            document.querySelector('#searchTab input[type="text"]').value = '';
        } else if (filterType === 'department') {
            const checkboxes = document.querySelectorAll('#searchDepartmentCheckboxes input[type="checkbox"]');
            checkboxes.forEach(cb => {
                if (cb.value === filterValue) {
                    cb.checked = false;
                }
            });
        } else if (filterType === 'announceStart') {
            const dateInputs = document.querySelectorAll('#searchTab .date-range input');
            if (dateInputs[0]) dateInputs[0].value = '';
        } else if (filterType === 'announceEnd') {
            const dateInputs = document.querySelectorAll('#searchTab .date-range input');
            if (dateInputs[1]) dateInputs[1].value = '';
        } else if (filterType === 'effectiveStart') {
            const dateInputs = document.querySelectorAll('#searchTab .date-range input');
            if (dateInputs[2]) dateInputs[2].value = '';
        } else if (filterType === 'effectiveEnd') {
            const dateInputs = document.querySelectorAll('#searchTab .date-range input');
            if (dateInputs[3]) dateInputs[3].value = '';
        }

        // 재검색 실행
        this.performAdvancedSearch();
    },

    // 상세 검색 초기화
    resetAdvancedSearch() {
        // 입력 필드 초기화
        document.querySelector('#searchTab input[type="text"]').value = '';

        // 부서 체크박스 초기화
        const deptCheckboxes = document.querySelectorAll('#searchDepartmentCheckboxes input[type="checkbox"]');
        deptCheckboxes.forEach(checkbox => {
            checkbox.checked = false;
        })

        // 날짜 필드 초기화 (type이 text 또는 date일 수 있음)
        document.querySelectorAll('#searchTab .date-range input').forEach(input => {
            input.value = '';
            input.type = 'text'; // 초기화 시 text 타입으로 되돌림
        });

        // 검색 결과 제거
        const resultContainer = document.getElementById('advancedSearchResults');
        if (resultContainer) {
            resultContainer.remove();
        }

        // 저장된 필터 초기화
        this.lastSearchFilters = null;

        console.log('Advanced search form reset');
    },

    // 연혁 목록 로드
    loadHistoryList() {
        const historyData = [
            { regulation: '인사관리규정', revision: 3, date: '2024.03.15', type: '일부개정', reason: '승진 기준 변경' },
            { regulation: '재무관리규정', revision: 2, date: '2024.03.01', type: '일부개정', reason: '예산 관리 조항 수정' },
            { regulation: '연명의료결정 환자 진료', revision: 5, date: '2025.03.25', type: '전면개정', reason: '연명의료결정법 개정' }
        ];
        
        const tbody = document.getElementById('historyList');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        historyData.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item.regulation}</td>
                <td>${item.revision}차</td>
                <td>${item.date}</td>
                <td><span class="status-badge status-active">${item.type}</span></td>
                <td>${item.reason}</td>
                <td>
                    <button class="action-btn btn-primary">상세보기</button>
                    <button class="action-btn btn-secondary">비교</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    },

    // 제정 모달 열기
    openNewModal() {
        document.getElementById('newModal').classList.add('active');
        this.clearNewForm();
    },

    closeNewModal() {
        document.getElementById('newModal').classList.remove('active');
    },

    clearNewForm() {
        document.getElementById('newTitle').value = '';
        document.getElementById('newDepartment').value = '';
        document.getElementById('newType').value = 'new';
        document.getElementById('fileUploadSection').style.display = 'none';
    },

    // 신규 등록
    createNew() {
        const title = document.getElementById('newTitle').value.trim();
        const department = document.getElementById('newDepartment').value.trim();
        const type = document.getElementById('newType').value.trim();

        if (!title || !department) {
            alert('필수 항목을 입력해주세요.');
            return;
        }

        // 새 규정 생성
        const newRegulation = {
            id: Date.now(),
            title: title,
            department: department,
            revisionDate: new Date().toISOString().split('T')[0],  // 개정일 추가
            classification: '',  // 분류는 나중에 설정
            announceDate: new Date().toISOString().split('T')[0],
            effectiveDate: '',
            status: 'draft',
            version: '1.0',
            content: {
                articles: [],
                appendix: '',
                attachments: [],
                history: [{
                    date: new Date().toISOString().split('T')[0],
                    type: '제정',
                    description: '신규 제정'
                }]
            }
        };

        this.regulations.push(newRegulation);
        this.loadRegulations();
        this.closeNewModal();

        // 편집 창 열기
        setTimeout(() => {
            this.openEditWindow(newRegulation.id, true);
        }, 300);

        this.showNotification(`"${title}" 규정이 생성되었습니다. 편집 창을 엽니다.`, 'success');
    },

    // 개정 모달
    openRevisionModal(regId) {
        const regulation = this.regulations.find(r => r.id == regId);
        if (!regulation) return;

        // 개정 모달 HTML 생성
        const modalHtml = `
            <div class="modal active" id="revisionModal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>규정 개정</h2>
                        <button class="modal-close" onclick="RegulationEditor.closeRevisionModal()">✕</button>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" id="revisionRegId" value="${regId}">
                        
                        <div class="alert alert-info">
                            <span>ℹ️</span>
                            <span>개정할 규정: ${regulation.title}</span>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">
                                개정 유형 <span class="required">*</span>
                            </label>
                            <select class="form-select" id="revisionType">
                                <option value="partial">일부개정</option>
                                <option value="full">전면개정</option>
                                <option value="minor">경미한 수정</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">
                                공포일자 <span class="required">*</span>
                            </label>
                            <input type="date" class="form-input" id="revisionAnnounceDate" 
                                   value="${new Date().toISOString().split('T')[0]}">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">
                                시행일자 <span class="required">*</span>
                            </label>
                            <input type="date" class="form-input" id="revisionEffectiveDate" 
                                   value="${new Date().toISOString().split('T')[0]}">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">
                                개정 사유 <span class="required">*</span>
                            </label>
                            <textarea class="form-textarea" id="revisionReason" rows="3"
                                      placeholder="개정 사유를 입력하세요"></textarea>
                        </div>

                        <div class="form-group">
                            <label class="form-label">
                                신구대비표 PDF <span style="color: #6c757d;">(선택)</span>
                            </label>
                            <input type="file" class="form-input" id="revisionComparisonFile" accept=".pdf">
                            <p style="color: #6c757d; font-size: 12px; margin-top: 5px;">개정 전후 비교표 PDF 파일을 업로드하세요</p>
                        </div>

                        <div class="form-group">
                            <label class="form-label">
                                수정 이력파일 PDF <span style="color: #6c757d;">(선택)</span>
                            </label>
                            <input type="file" class="form-input" id="revisionHistoryFile" accept=".pdf">
                            <p style="color: #6c757d; font-size: 12px; margin-top: 5px;">수정 이력 문서 PDF 파일을 업로드하세요</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="RegulationEditor.closeRevisionModal()">취소</button>
                        <button class="btn btn-primary" onclick="RegulationEditor.createRevision()">개정 시작</button>
                    </div>
                </div>
            </div>
        `;

        // 기존 모달 제거 후 새 모달 추가
        const existingModal = document.getElementById('revisionModal');
        if (existingModal) existingModal.remove();
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    },

    // 개정 모달 닫기
    closeRevisionModal() {
        const modal = document.getElementById('revisionModal');
        if (modal) {
            modal.remove();
        }
    },

    // 개정 생성
    createRevision() {
        const regId = document.getElementById('revisionRegId').value.trim();
        const revisionType = document.getElementById('revisionType').value.trim();
        const announceDate = document.getElementById('revisionAnnounceDate').value.trim();
        const effectiveDate = document.getElementById('revisionEffectiveDate').value.trim();
        const revisionReason = document.getElementById('revisionReason').value.trim();
        const comparisonFileInput = document.getElementById('revisionComparisonFile');
        const comparisonFile = comparisonFileInput ? comparisonFileInput.files[0] : null;
        const historyFileInput = document.getElementById('revisionHistoryFile');
        const historyFile = historyFileInput ? historyFileInput.files[0] : null;

        if (!announceDate || !effectiveDate || !revisionReason) {
            alert('모든 필수 항목을 입력해주세요.');
            return;
        }

        // 신구대비표 파일 저장 (나중에 사용)
        if (comparisonFile) {
            this.pendingComparisonFile = comparisonFile;
            console.log('신구대비표 파일 준비됨:', comparisonFile.name);
        }

        // 수정 이력파일 저장 (나중에 사용)
        if (historyFile) {
            this.pendingHistoryFile = historyFile;
            console.log('수정 이력파일 준비됨:', historyFile.name);
        }

        const original = this.regulations.find(r => r.id == regId);
        if (!original) return;

        // 원본 복사하여 새 버전 생성
        const revision = JSON.parse(JSON.stringify(original));
        revision.id = Date.now();
        revision.title = `${original.title}`;
        revision.status = 'revision';
        revision.version = this.incrementVersion(original.version);
        revision.announceDate = announceDate;
        revision.effectiveDate = effectiveDate;
        revision.revisionDate = new Date().toISOString().split('T')[0];  // 개정일 업데이트
        
        // 개정 이력 추가
        revision.content.history.push({
            date: new Date().toISOString().split('T')[0],
            type: revisionType === 'full' ? '전면개정' : revisionType === 'partial' ? '일부개정' : '경미한 수정',
            description: revisionReason,
            previousVersion: original.version
        });

        this.regulations.push(revision);
        this.loadRegulations();
        this.closeRevisionModal();

        // 편집 창 열기
        setTimeout(() => {
            this.openEditWindow(revision.id, false, true);
        }, 300);

        this.showNotification(`"${original.title}" 규정의 개정 버전이 생성되었습니다.`, 'success');
    },

    // 버전 증가
    incrementVersion(version) {
        const parts = version.split('.');
        const minor = parseInt(parts[1] || 0) + 1;
        return `${parts[0]}.${minor}`;
    },

    // 편집 모달 열기
    openEditWindow(regId, isNew = false, isRevision = false) {
        const regulation = this.regulations.find(r => r.id == regId);
        if (!regulation) return;

        // 현재 편집 중인 규정 저장
        this.currentEditingRegulation = regulation;

        // 모달 표시
        const modal = document.getElementById('editModal');
        modal.style.display = 'block';
        modal.classList.add('active');

        // 첫 번째 탭이 활성화되면 스크롤 동기화는 나중에 설정
        // 조문 탭이 클릭될 때 setupArticleScrollSync가 호출됨

        // 제목 설정
        const titlePrefix = isNew ? '새 규정 작성' : (isRevision ? '규정 개정' : '규정 편집');
        document.getElementById('editModalTitle').textContent = `${titlePrefix} - ${regulation.title}`;

        // 기본정보 채우기
        document.getElementById('editTitle').value = regulation.title || '';
        document.getElementById('editClassification').value = regulation.classification || regulation.wzpubno || '';

        // 날짜 필드 - 개정일자와 시행일자
        const revisionDateField = document.getElementById('editRevisionDate');
        if (revisionDateField) {
            revisionDateField.value = this.formatDateForInput(regulation.revisionDate || regulation.wzlastrevdate || regulation.announceDate || regulation.wzestabdate);
        }

        const effectiveDateField = document.getElementById('editEffectiveDate');
        if (effectiveDateField) {
            effectiveDateField.value = this.formatDateForInput(regulation.effectiveDate || regulation.wzexecdate);
        }

        // 부서 선택 옵션 로드
        this.loadDepartmentsForEdit(regulation.department || regulation.wzmgrdptnm);

        // 조문 내용 로드
        this.loadArticleContent(regId);

        // 부록 파일 목록 로드
        console.log('[RegulationEditor] Checking loadAppendixFiles availability:', typeof window.loadAppendixFiles);
        if (typeof window.loadAppendixFiles === 'function') {
            const wzpubno = regulation.wzpubno || regulation.classification || '';
            console.log('[RegulationEditor] Calling loadAppendixFiles with regId:', regId, 'wzpubno:', wzpubno);
            window.loadAppendixFiles(regId, wzpubno);
        } else {
            console.warn('[RegulationEditor] loadAppendixFiles function not found on window object');
        }

        // 개정 모드일 때는 내용편집 탭으로 바로 이동, 아니면 기본정보 탭
        if (isRevision) {
            console.log('[RegulationEditor] Opening revision mode - switching to article tab');
            this.switchEditTab('article');
        } else {
            this.switchEditTab('basic');
        }
    },

    // 날짜 형식 변환
    formatDateForInput(dateStr) {
        if (!dateStr) return '';
        // YYYY.MM.DD 형식을 YYYY-MM-DD로 변환
        return dateStr.replace(/\./g, '-');
    },

    // 부서 목록 로드 for 편집
    async loadDepartmentsForEdit(currentDept) {
        try {
            const response = await fetch('/api/v1/dept/list', {
                credentials: 'include'
            });
            const data = await response.json();

            const select = document.getElementById('editDepartment');
            select.innerHTML = '<option value="">선택하세요</option>';

            if (data.success) {
                data.departments.forEach(dept => {
                    const option = document.createElement('option');
                    option.value = dept.name;
                    option.textContent = dept.name;
                    if (dept.name === currentDept) {
                        option.selected = true;
                    }
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading departments:', error);
        }
    },

    // 조문 내용 로드
    async loadArticleContent(regId) {
        try {
            // 개정 모드: regulations 배열에서 mergedData 확인
            const regulation = this.regulations.find(r => r.id == regId);
            if (regulation && regulation.isRevision && regulation.mergedData) {
                console.log('[RegulationEditor] Loading revision merged data');
                const mergedData = regulation.mergedData;

                // 병합된 텍스트 내용 사용
                if (mergedData.text_content) {
                    document.getElementById('articleContent').value = mergedData.text_content;
                    this.previewArticles();
                    return;
                }
                // 또는 merged_data의 조문내용 사용
                else if (mergedData.merged_data && mergedData.merged_data['조문내용']) {
                    const articles = mergedData.merged_data['조문내용'];
                    const articlesText = articles.map(article => {
                        const num = article['번호'] || '';
                        const content = article['내용'] || '';
                        return num ? `${num}\n${content}` : content;
                    }).join('\n\n');
                    document.getElementById('articleContent').value = articlesText;
                    this.previewArticles();
                    return;
                }
            }

            // 일반 편집 모드: API에서 기존 내용 로드
            const response = await fetch(`/api/v1/regulation/content/${regId}`, {
                credentials: 'include'
            });
            const data = await response.json();

            if (data.success && data.content) {
                // full_text가 있으면 사용
                if (data.content.full_text) {
                    document.getElementById('articleContent').value = this.htmlToText(data.content.full_text);
                    this.previewArticles();
                }
                // 또는 articles가 있으면 사용
                else if (data.content.articles) {
                    const articlesText = data.content.articles.map(a => `${a.조}\n${a.내용}`).join('\n\n');
                    document.getElementById('articleContent').value = articlesText;
                    this.previewArticles();
                }
            }
        } catch (error) {
            console.error('Error loading article content:', error);
        }
    },

    // HTML을 텍스트로 변환
    htmlToText(html) {
        const div = document.createElement('div');
        div.innerHTML = html;
        return div.textContent || div.innerText || '';
    },

    // 편집 모달 닫기
    closeEditModal() {
        const modal = document.getElementById('editModal');
        modal.style.display = 'none';
        modal.classList.remove('active');
        this.currentEditingRegulation = null;

        // 점 메뉴 닫기
        document.getElementById('editMenu').style.display = 'none';
    },

    // 편집 탭 전환
    switchEditTab(tabName) {
        console.log('[RegulationEditor] switchEditTab called with:', tabName);

        // 모든 탭과 패널 비활성화
        document.querySelectorAll('.edit-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.style.display = 'none';
        });

        // 선택된 탭 활성화
        const tabIndex = ['basic', 'articles', 'upload', 'appendix', 'attachments'].indexOf(tabName);
        console.log('[RegulationEditor] Tab index:', tabIndex);

        if (tabIndex !== -1) {
            document.querySelectorAll('.edit-tab')[tabIndex].classList.add('active');
            const targetTab = document.getElementById(`${tabName}Tab`);
            console.log('[RegulationEditor] Target tab element:', targetTab);

            if (targetTab) {
                targetTab.style.display = 'block';
                console.log('[RegulationEditor] Set display to block');
                console.log('[RegulationEditor] Computed styles:', window.getComputedStyle(targetTab));
                console.log('[RegulationEditor] offsetHeight:', targetTab.offsetHeight);
                console.log('[RegulationEditor] scrollHeight:', targetTab.scrollHeight);
                console.log('[RegulationEditor] clientHeight:', targetTab.clientHeight);
            } else {
                console.error('[RegulationEditor] Tab element not found:', `${tabName}Tab`);
            }

            // 조문 및 부칙 탭이 활성화되면 스크롤 동기화 설정
            if (tabName === 'articles') {
                this.setupArticleScrollSync();
            }

            // 부록 탭이 활성화되면 부록 파일 목록 로드
            if (tabName === 'appendix' && this.currentEditingRegulation) {
                const ruleId = this.currentEditingRegulation.id;
                const wzpubno = this.currentEditingRegulation.wzpubno || this.currentEditingRegulation.classification || '';
                console.log('[RegulationEditor] Appendix tab activated, loading files for ruleId:', ruleId, 'wzpubno:', wzpubno);
                if (ruleId && typeof window.loadAppendixFiles === 'function') {
                    window.loadAppendixFiles(ruleId, wzpubno).catch(err => {
                        console.error('[RegulationEditor] Failed to load appendix files:', err);
                    });
                } else {
                    console.warn('[RegulationEditor] Cannot load appendix - ruleId:', ruleId, 'function:', typeof window.loadAppendixFiles);
                }
            }
        }
    },

    // 조문 편집 영역과 미리보기 영역의 스크롤 동기화
    setupArticleScrollSync() {
        const articleContent = document.getElementById('articleContent');
        const articlePreview = document.getElementById('articlePreview');

        if (!articleContent || !articlePreview) return;

        // 기존 이벤트 리스너 제거 (중복 방지)
        articleContent.removeEventListener('scroll', this.syncArticleScroll);
        articlePreview.removeEventListener('scroll', this.syncPreviewScroll);

        // 편집 영역 스크롤 시 미리보기 동기화
        this.syncArticleScroll = () => {
            if (this.isSyncingScroll) return;
            this.isSyncingScroll = true;

            const scrollPercentage = articleContent.scrollTop /
                (articleContent.scrollHeight - articleContent.clientHeight);

            articlePreview.scrollTop = scrollPercentage *
                (articlePreview.scrollHeight - articlePreview.clientHeight);

            setTimeout(() => {
                this.isSyncingScroll = false;
            }, 50);
        };

        // 미리보기 영역 스크롤 시 편집 영역 동기화
        this.syncPreviewScroll = () => {
            if (this.isSyncingScroll) return;
            this.isSyncingScroll = true;

            const scrollPercentage = articlePreview.scrollTop /
                (articlePreview.scrollHeight - articlePreview.clientHeight);

            articleContent.scrollTop = scrollPercentage *
                (articleContent.scrollHeight - articleContent.clientHeight);

            setTimeout(() => {
                this.isSyncingScroll = false;
            }, 50);
        };

        // 이벤트 리스너 추가
        articleContent.addEventListener('scroll', this.syncArticleScroll);
        articlePreview.addEventListener('scroll', this.syncPreviewScroll);
    },

    // 점 메뉴 토글
    toggleEditMenu() {
        const menu = document.getElementById('editMenu');
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    },

    // 규정 삭제
    async deleteRegulation() {
        if (!this.currentEditingRegulation) return;

        const reg = this.currentEditingRegulation;

        if (!confirm(`정말로 "${reg.title}" 내규를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) {
            return;
        }

        try {
            const response = await fetch(`/api/v1/rule/delete/${reg.wzruleseq || reg.id}`, {
                method: 'DELETE',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                this.showNotification(`"${reg.title}" 규정이 삭제되었습니다.`, 'success');
                this.closeEditModal();
                this.loadRegulationsFromDB(); // 목록 새로고침
            } else {
                const error = await response.json();
                this.showNotification(`삭제 실패: ${error.detail || '알 수 없는 오류'}`, 'error');
            }
        } catch (error) {
            console.error('Error deleting regulation:', error);
            this.showNotification('삭제 중 오류가 발생했습니다.', 'error');
        }
    },

    // edited 폴더에 편집 내용 저장
    async saveToEditedFolder(content) {
        try {
            const regulation = this.currentEditingRegulation || this.currentRevisingRegulation;
            if (!regulation) return;

            const response = await fetch('/api/v1/rule/save-edited', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    rule_id: regulation.wzruleseq || regulation.wz_rule_id || regulation.rule_id || regulation.id,
                    title: regulation.title || regulation.wzname || 'untitled',
                    content_type: 'article',
                    content: content
                })
            });

            if (response.ok) {
                const data = await response.json();
                console.log(`Edited content saved: ${data.filename}`);
                this.showNotification('편집 내용이 자동 저장되었습니다.', 'info');
            }
        } catch (error) {
            console.error('Error saving to edited folder:', error);
            // 자동 저장 실패는 조용히 처리
        }
    },

    // 텍스트 영역 높이 자동 조정
    adjustTextareaHeight(textarea) {
        if (!textarea) return;

        // 기본 최소 높이
        textarea.style.height = 'auto';

        // 스크롤 높이에 맞춰 조정
        const newHeight = Math.max(400, textarea.scrollHeight);
        textarea.style.height = newHeight + 'px';

        // 미리보기 영역도 같은 높이로 설정
        const preview = document.getElementById('articlePreview');
        if (preview) {
            preview.style.height = newHeight + 'px';
        }
    },

    // 조문 미리보기
    async previewArticles() {
        const content = document.getElementById('articleContent').value;
        const preview = document.getElementById('articlePreview');

        if (!content) {
            preview.innerHTML = '<p style="color: #6c757d;">미리보기할 내용이 없습니다.</p>';
            return;
        }

        // edited 폴더에 자동 저장
        await this.saveToEditedFolder(content);

        // 미리보기 업데이트 후 스크롤 동기화 재설정
        setTimeout(() => {
            this.setupArticleScrollSync();
        }, 100);

        // HTML 이스케이프 함수
        const escapeHtml = (text) => {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, m => map[m]);
        };

        // 줄바꿈을 유지하면서 HTML로 변환
        let html = content
            .split('\n')
            .map(line => {
                // 빈 줄은 단락 구분으로 처리
                if (!line.trim()) {
                    return '<br><br>';
                }

                // 제X장 (장 제목)
                if (line.match(/^제\d+장/)) {
                    return `<h3 style="color: #495057; margin-top: 25px; margin-bottom: 15px; text-align: center; font-weight: bold;">${escapeHtml(line)}</h3>`;
                }

                // 제X절 (절 제목)
                if (line.match(/^제\d+절/)) {
                    return `<h4 style="color: #495057; margin-top: 20px; margin-bottom: 10px; font-weight: bold;">${escapeHtml(line)}</h4>`;
                }

                // 제X조 (조문 제목)
                if (line.match(/^제\d+조/)) {
                    return `<h4 style="color: #007bff; margin-top: 20px; margin-bottom: 10px; font-weight: bold;">${escapeHtml(line)}</h4>`;
                }

                // 부칙
                if (line.trim().startsWith('부칙') || line.trim().startsWith('부 칙')) {
                    return `<h4 style="color: #6c757d; margin-top: 30px; margin-bottom: 10px; border-top: 1px solid #dee2e6; padding-top: 15px; font-weight: bold;">${escapeHtml(line)}</h4>`;
                }

                // 항목 번호 (①②③..., 1. 2. 3..., 가. 나. 다...)
                if (line.match(/^[①②③④⑤⑥⑦⑧⑨⑩]/) ||
                    line.match(/^\d+\./) ||
                    line.match(/^[가나다라마바사아자차카타파하]\./)) {
                    return `<p style="margin-left: 20px; margin-top: 8px; margin-bottom: 8px; line-height: 1.6;">${escapeHtml(line)}</p>`;
                }

                // 들여쓰기가 있는 경우 (공백이나 탭으로 시작)
                if (line.match(/^[\s\t]+/)) {
                    return `<p style="margin-left: 40px; margin-top: 5px; margin-bottom: 5px; line-height: 1.6;">${escapeHtml(line.trim())}</p>`;
                }

                // 일반 텍스트
                return `<p style="margin-top: 5px; margin-bottom: 5px; line-height: 1.6;">${escapeHtml(line)}</p>`;
            })
            .join('');

        // 연속된 <br> 태그를 정리
        html = html.replace(/(<br>){3,}/g, '<br><br>');

        // 미리보기 영역에 스타일 추가
        preview.style.cssText = 'padding: 20px; background: white; border-radius: 8px; font-family: "Malgun Gothic", sans-serif; font-size: 14px;';
        preview.innerHTML = html || '<p>내용이 없습니다.</p>';
    },

    // 편집 내용 저장
    async saveEdit() {
        const reg = this.currentEditingRegulation;
        if (!reg) return;

        const title = document.getElementById('editTitle').value.trim();
        const classification = document.getElementById('editClassification').value.trim();
        const department = document.getElementById('editDepartment').value.trim();
        const establishDate = document.getElementById('editEstablishDate').value.trim();  // 제정일
        const revisionDate = document.getElementById('editRevisionDate').value.trim();  // 개정일
        const effectiveDate = document.getElementById('effectiveDate').value.trim();  // 시행일
        const articleContent = document.getElementById('articleContent').value;
        const regulationStatus = document.getElementById('editStatus')?.value.trim() || '현행';  // 현행/연혁 상태

        if (!title || !department) {
            alert('필수 항목을 입력하세요.');
            return;
        }

        // 현재 정렬 상태 저장
        const savedSort = {
            column: this.currentSort.column,
            direction: this.currentSort.direction
        };

        try {
            // 개정 모드인 경우: 새 파일로 저장
            if (reg.isRevision && reg.mergedData) {
                console.log('[RegulationEditor] Saving revision with new file');
                const response = await fetch(`/api/v1/rule-enhanced/save-revision`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        wzruleseq: reg.wzruleseq || reg.id,
                        wzname: title,
                        wzpubno: classification,
                        wzmgrdptnm: department,
                        wzestabdate: establishDate || reg.establishedDate || reg.wzestabdate,
                        wzlastrevdate: revisionDate,
                        wzexecdate: effectiveDate,
                        content_text: articleContent,
                        merged_data: reg.mergedData.merged_data,  // 병합된 JSON 데이터
                        wzNewFlag: regulationStatus
                    })
                });

                if (response.ok) {
                    const result = await response.json();

                    // 신구대비표 및 수정 이력파일 업로드
                    let uploadMessages = [];
                    let hasError = false;

                    if (this.pendingComparisonFile && result.new_rule_seq) {
                        try {
                            await this.uploadComparisonTable(result.new_rule_seq, this.pendingComparisonFile);
                            uploadMessages.push('신구대비표');
                        } catch (compError) {
                            console.error('신구대비표 업로드 실패:', compError);
                            hasError = true;
                        }
                        this.pendingComparisonFile = null;
                    }

                    if (this.pendingHistoryFile && result.new_rule_seq) {
                        try {
                            await this.uploadHistoryFile(result.new_rule_seq, this.pendingHistoryFile);
                            uploadMessages.push('수정 이력파일');
                        } catch (histError) {
                            console.error('수정 이력파일 업로드 실패:', histError);
                            hasError = true;
                        }
                        this.pendingHistoryFile = null;
                    }

                    // 결과 메시지 표시
                    if (uploadMessages.length > 0) {
                        const filesText = uploadMessages.join(', ');
                        if (hasError) {
                            this.showNotification(`개정 규정은 저장되었으나 일부 파일 업로드에 실패했습니다. (성공: ${filesText})`, 'warning');
                        } else {
                            this.showNotification(`개정 규정 및 ${filesText}가 저장되었습니다.`, 'success');
                        }
                    } else {
                        this.showNotification('개정 규정이 저장되었습니다.', 'success');
                    }

                    this.closeEditModal();

                    // 정렬 상태 복원
                    await this.loadRegulationsFromDB();
                    if (savedSort.column) {
                        this.currentSort = savedSort;
                        this.sortBy(savedSort.column);
                    }
                } else {
                    const error = await response.json();
                    this.showNotification(`저장 실패: ${error.detail || '알 수 없는 오류'}`, 'error');
                }
            }
            // 일반 편집 모드: 기존 파일명 유지
            else {
                console.log('[RegulationEditor] Saving edit with existing file');
                const response = await fetch(`/api/v1/rule-enhanced/update-content`, {
                    method: 'PUT',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        wzruleseq: reg.wzruleseq || reg.id,
                        wzname: title,
                        wzpubno: classification,
                        wzmgrdptnm: department,
                        wzestabdate: establishDate || reg.establishedDate || reg.wzestabdate,
                        wzlastrevdate: revisionDate,
                        wzexecdate: effectiveDate,
                        content_text: articleContent,
                        revision_reason: this.lastParsedContent?.revisionReason || '',
                        wzNewFlag: regulationStatus
                    })
                });

                if (response.ok) {
                    this.showNotification('저장되었습니다.', 'success');
                    this.closeEditModal();

                    // 정렬 상태 복원
                    await this.loadRegulationsFromDB();
                    if (savedSort.column) {
                        this.currentSort = savedSort;
                        this.sortBy(savedSort.column);
                    }
                } else {
                    const error = await response.json();
                    this.showNotification(`저장 실패: ${error.detail || '알 수 없는 오류'}`, 'error');
                }
            }
        } catch (error) {
            console.error('Error saving regulation:', error);
            this.showNotification('저장 중 오류가 발생했습니다.', 'error');
        }
    },

    // 기본 편집 HTML 생성
    generateBasicEditHTML(regulation) {
        return `
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <title>편집 - ${regulation.title}</title>
                <style>
                    body { font-family: sans-serif; padding: 20px; }
                    h1 { color: #667eea; }
                </style>
            </head>
            <body>
                <h1>${regulation.title} 편집</h1>
                <p>부서: ${regulation.department}</p>
                <p>버전: ${regulation.version}</p>
                <button onclick="window.close()">닫기</button>
            </body>
            </html>
        `;
    },

    // 열린 창 목록 업데이트
    updateOpenWindowsList() {
        const windowList = document.getElementById('windowList');
        const container = document.getElementById('openWindows');
        
        if (this.openEditWindows.size === 0) {
            container.style.display = 'none';
            return;
        }
        
        container.style.display = 'block';
        windowList.innerHTML = '';
        
        this.openEditWindows.forEach((window, regId) => {
            if (!window.closed) {
                const regulation = this.regulations.find(r => r.id == regId);
                const item = document.createElement('div');
                item.className = 'window-item';
                item.innerHTML = `
                    <span>${regulation.title}</span>
                    <button onclick="RegulationEditor.focusEditWindow(${regId})">이동</button>
                `;
                windowList.appendChild(item);
            }
        });
    },

    // 편집 창 포커스
    focusEditWindow(regId) {
        const window = this.openEditWindows.get(regId);
        if (window && !window.closed) {
            window.focus();
        }
    },

    // 선택 관리
    toggleSelection(regId) {
        const checkbox = document.querySelector(`input[value="${regId}"]`);
        const row = checkbox.closest('tr');
        
        if (this.selectedRegulations.has(regId)) {
            this.selectedRegulations.delete(regId);
            row.classList.remove('selected');
        } else {
            this.selectedRegulations.add(regId);
            row.classList.add('selected');
        }
        
        this.updateSelectionUI();
    },

    toggleSelectAll() {
        const selectAll = document.getElementById('selectAll').checked;
        const checkboxes = document.querySelectorAll('.row-checkbox');
        
        checkboxes.forEach(cb => {
            cb.checked = selectAll;
            const regId = parseInt(cb.value);
            const row = cb.closest('tr');
            
            if (selectAll) {
                this.selectedRegulations.add(regId);
                row.classList.add('selected');
            } else {
                this.selectedRegulations.delete(regId);
                row.classList.remove('selected');
            }
        });
        
        this.updateSelectionUI();
    },

    updateSelectionUI() {
        document.getElementById('selectedCount').textContent = this.selectedRegulations.size;
        
        const hasSelection = this.selectedRegulations.size > 0;
        // deleteBtn이 있는 경우에만 설정
        const deleteBtn = document.getElementById('deleteBtn');
        if (deleteBtn) {
            deleteBtn.disabled = !hasSelection;
        }
    },

    // 규정 복사
    duplicateRegulation(regId) {
        const original = this.regulations.find(r => r.id == regId);
        if (!original) return;
        
        const copy = JSON.parse(JSON.stringify(original));
        copy.id = Date.now();
        copy.title = `${original.title} (복사본)`;
        copy.status = 'draft';
        copy.announceDate = new Date().toISOString().split('T')[0];
        copy.revisionDate = new Date().toISOString().split('T')[0];  // 개정일 업데이트
        
        this.regulations.push(copy);
        this.loadRegulations();
        
        this.showNotification(`"${original.title}" 규정이 복사되었습니다.`, 'success');
        
        // 복사본 편집 창 열기
        setTimeout(() => {
            this.openEditWindow(copy.id);
        }, 300);
    },

    // 규정 개정 - 파일 업로드 모달 열기
    async reviseRegulation(regId) {
        const regulation = this.regulations.find(r => r.id === regId || r.id == regId);
        if (!regulation) {
            alert('내규를 찾을 수 없습니다.');
            return;
        }

        // 현재 개정 중인 규정 저장
        this.currentRevisingRegulation = regulation;

        // 해당 규정을 선택된 상태로 설정
        this.selectedRegulations.clear();
        const actualId = regulation.wzruleseq || regulation.wz_rule_id || regulation.rule_id || regulation.id;
        this.selectedRegulations.add(actualId);
        console.log('[Revise] Selected regulation:', actualId, regulation.rule_nm || regulation.title);

        // 개정 파일 업로드 모달 열기
        const modal = document.getElementById('revisionUploadModal');
        modal.style.display = 'block';
        modal.classList.add('active');

        // 오늘 날짜로 기본값 설정
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('revisionDate').value = today;
    },

    // 개정 파일 업로드 모달 닫기
    closeRevisionUploadModal(shouldClearData = true) {
        const modal = document.getElementById('revisionUploadModal');
        modal.style.display = 'none';
        modal.classList.remove('active');

        // shouldClearData가 true일 때만 데이터 초기화
        if (shouldClearData) {
            this.currentRevisingRegulation = null;
        }

        // 입력 필드 초기화
        const pdfInput = document.getElementById('revisionPdfFile');
        const docxInput = document.getElementById('revisionDocxFile');
        const comparisonInput = document.getElementById('revisionComparisonFile');
        if (pdfInput) pdfInput.value = '';
        if (docxInput) docxInput.value = '';
        if (comparisonInput) comparisonInput.value = '';
        document.getElementById('revisionReason').value = '';
        document.getElementById('revisionDate').value = '';

        // 파일 정보 및 미리보기 초기화
        const pdfInfo = document.getElementById('pdfFileInfo');
        const docxInfo = document.getElementById('docxFileInfo');
        const comparisonInfo = document.getElementById('comparisonFileInfo');
        if (pdfInfo) pdfInfo.innerHTML = '';
        if (docxInfo) docxInfo.innerHTML = '';
        if (comparisonInfo) comparisonInfo.innerHTML = '';
        const preview = document.getElementById('parsingPreview');
        if (preview) preview.style.display = 'none';
        const previewContent = document.getElementById('parsingPreviewContent');
        if (previewContent) previewContent.innerHTML = '';
    },

    // 파싱된 내용으로 편집 창 열기
    proceedWithParsedContent(shouldClearData = false) {
        if (this.lastParsedContent) {
            // currentRevisingRegulation 백업 (모달 닫기 전에)
            const regulation = this.currentRevisingRegulation;

            this.closeRevisionUploadModal(false);  // 데이터 초기화하지 않음
            this.closeComparisonModal();

            // 백업한 regulation을 복원
            this.currentRevisingRegulation = regulation;
            this.openEditWindowWithParsedContent(this.lastParsedContent, true);

            // shouldClearData가 true일 때만 초기화 (병합 후 편집 창 열 때)
            if (shouldClearData) {
                this.lastParsedContent = null;
                this.lastUploadedFiles = null;
                this.currentRevisingRegulation = null;
            }
        } else {
            alert('파싱된 내용을 찾을 수 없습니다.');
        }
    },

    // 비교 모달 표시
    showComparisonModal() {
        if (!this.lastParsedContent) {
            alert('비교할 파싱 결과가 없습니다.');
            return;
        }

        const modal = document.getElementById('comparisonModal');
        const pdfContent = document.getElementById('pdfComparisonContent');
        const docxContent = document.getElementById('docxComparisonContent');

        if (!modal || !pdfContent || !docxContent) {
            console.error('Comparison modal elements not found');
            return;
        }

        // PDF 결과 표시
        if (this.lastParsedContent.pdf_result) {
            const pdfResult = this.lastParsedContent.pdf_result;
            if (pdfResult.error) {
                pdfContent.innerHTML = `<div style="color: red;">오류: ${pdfResult.text}</div>`;
            } else if (pdfResult.json) {
                // JSON 구조화된 데이터 표시
                pdfContent.innerHTML = this.formatStructuredData(pdfResult.json);
            } else {
                // 텍스트만 표시
                pdfContent.textContent = pdfResult.text || '파싱된 내용이 없습니다.';
            }
        } else {
            pdfContent.innerHTML = '<div style="color: #999;">PDF 파싱 결과가 없습니다.</div>';
        }

        // DOCX 결과 표시
        if (this.lastParsedContent.docx_result) {
            const docxResult = this.lastParsedContent.docx_result;
            if (docxResult.error) {
                docxContent.innerHTML = `<div style="color: red;">오류: ${docxResult.text}</div>`;
            } else if (docxResult.json) {
                // JSON 구조화된 데이터 표시
                docxContent.innerHTML = this.formatStructuredData(docxResult.json);
            } else {
                // 텍스트만 표시
                docxContent.textContent = docxResult.text || '파싱된 내용이 없습니다.';
            }
        } else {
            docxContent.innerHTML = '<div style="color: #999;">DOCX 파싱 결과가 없습니다.</div>';
        }

        // 모달 표시
        modal.style.display = 'flex';
        modal.classList.add('active');

        // 스크롤 동기화 설정
        this.setupSynchronizedScrolling();
    },

    // 구조화된 데이터를 HTML로 포맷팅
    formatStructuredData(data) {
        if (!data) return '데이터가 없습니다.';

        let html = '';

        // 문서정보 표시
        if (data.문서정보) {
            html += '<div style="margin-bottom: 20px; padding: 10px; background: #f0f7ff; border-radius: 4px;">';
            html += '<h5 style="color: #667eea; margin-bottom: 10px;">📋 문서정보</h5>';
            for (const [key, value] of Object.entries(data.문서정보)) {
                if (Array.isArray(value)) {
                    html += `<div><strong>${key}:</strong> ${value.join(', ')}</div>`;
                } else {
                    html += `<div><strong>${key}:</strong> ${value || '-'}</div>`;
                }
            }
            html += '</div>';
        }

        // 조문내용 표시
        if (data.조문내용 && Array.isArray(data.조문내용)) {
            html += '<div style="margin-top: 20px;">';
            html += '<h5 style="color: #667eea; margin-bottom: 10px;">📝 조문내용</h5>';
            data.조문내용.forEach(item => {
                const level = item.레벨 || 0;
                const indent = level * 20;
                html += `<div style="margin-left: ${indent}px; margin-bottom: 8px; padding: 5px; border-left: 2px solid #e0e0e0;">`;
                if (item.번호) {
                    html += `<strong style="color: #2c3e50;">${item.번호}</strong> `;
                }
                html += `<span>${item.내용 || ''}</span>`;
                html += '</div>';
            });
            html += '</div>';
        }

        return html || '구조화된 데이터가 없습니다.';
    },

    // 스크롤 동기화 설정
    setupSynchronizedScrolling() {
        const pdfPane = document.getElementById('pdfComparisonContent');
        const docxPane = document.getElementById('docxComparisonContent');

        if (!pdfPane || !docxPane) return;

        let syncing = false;

        // PDF 스크롤 시 DOCX 동기화
        pdfPane.addEventListener('scroll', function() {
            if (!syncing) {
                syncing = true;
                const scrollPercentage = this.scrollTop / (this.scrollHeight - this.clientHeight);
                docxPane.scrollTop = scrollPercentage * (docxPane.scrollHeight - docxPane.clientHeight);
                setTimeout(() => { syncing = false; }, 10);
            }
        });

        // DOCX 스크롤 시 PDF 동기화
        docxPane.addEventListener('scroll', function() {
            if (!syncing) {
                syncing = true;
                const scrollPercentage = this.scrollTop / (this.scrollHeight - this.clientHeight);
                pdfPane.scrollTop = scrollPercentage * (pdfPane.scrollHeight - pdfPane.clientHeight);
                setTimeout(() => { syncing = false; }, 10);
            }
        });
    },

    // 비교 모달 닫기
    closeComparisonModal() {
        const modal = document.getElementById('comparisonModal');
        if (modal) {
            modal.style.display = 'none';
            modal.classList.remove('active');
        }

        // 스크롤 이벤트 리스너 정리 (메모리 누수 방지)
        const pdfPane = document.getElementById('pdfComparisonContent');
        const docxPane = document.getElementById('docxComparisonContent');
        if (pdfPane) {
            pdfPane.replaceWith(pdfPane.cloneNode(true));
        }
        if (docxPane) {
            docxPane.replaceWith(docxPane.cloneNode(true));
        }
    },

    // 문서 병합
    async mergeDocuments() {
        if (!this.lastParsedContent || !this.lastUploadedFiles) {
            alert('병합할 파싱 데이터가 없습니다.');
            return;
        }

        // currentRevisingRegulation이 없으면 lastParsedContent에서 복원
        if (!this.currentRevisingRegulation && this.lastParsedContent.regulation) {
            this.currentRevisingRegulation = this.lastParsedContent.regulation;
        }

        const pdfFile = this.lastUploadedFiles.pdf;
        const docxFile = this.lastUploadedFiles.docx;

        if (!pdfFile || !docxFile) {
            alert('PDF와 DOCX 파일이 모두 필요합니다.');
            return;
        }

        // 병합 버튼 비활성화
        const mergeBtn = event.target;
        const originalText = mergeBtn.textContent;
        mergeBtn.disabled = true;
        mergeBtn.textContent = '병합 중...';

        try {
            // 병합 API 호출
            const response = await fetch('/api/v1/rule/merge-documents', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    pdf_filename: pdfFile.filename,
                    docx_filename: docxFile.filename,
                    pdf_result: this.lastParsedContent.pdf_result,
                    docx_result: this.lastParsedContent.docx_result,
                    rule_id: this.currentRevisingRegulation?.wzruleseq || this.currentRevisingRegulation?.id || 0
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.showNotification(`병합이 완료되었습니다.\n저장 경로: ${data.merged_path}`, 'success');

                // 병합된 결과로 편집 창 열기 옵션 제공
                if (confirm('병합이 완료되었습니다. 편집 창을 여시겠습니까?')) {
                    if (data.merged_content) {
                        this.lastParsedContent.structured_data = data.merged_content;
                    }
                    // 병합 후 편집 창 열 때는 데이터를 초기화
                    this.proceedWithParsedContent(true);
                }
            } else {
                const error = await response.json();
                this.showNotification(`병합 실패: ${error.detail || '알 수 없는 오류'}`, 'error');
            }
        } catch (error) {
            console.error('Error merging documents:', error);
            this.showNotification('문서 병합 중 오류가 발생했습니다.', 'error');
        } finally {
            // 버튼 복구
            mergeBtn.disabled = false;
            mergeBtn.textContent = originalText;
        }
    },

    // 개정 파일 처리 및 저장 (비동기 처리)
    async processRevisionFiles() {
        const pdfFileInput = document.getElementById('revisionPdfFile');
        const docxFileInput = document.getElementById('revisionDocxFile');
        const comparisonFileInput = document.getElementById('revisionComparisonFile');
        const pdfFile = pdfFileInput ? pdfFileInput.files[0] : null;
        const docxFile = docxFileInput ? docxFileInput.files[0] : null;
        const comparisonFile = comparisonFileInput ? comparisonFileInput.files[0] : null;
        const reason = document.getElementById('revisionReason').value.trim();
        const revisionDate = document.getElementById('revisionDate').value.trim();

        // 신구대비표 파일 저장 (나중에 사용)
        this.pendingComparisonFile = comparisonFile;

        // 두 파일 모두 필수
        if (!pdfFile || !docxFile) {
            let missingFiles = [];
            if (!pdfFile) missingFiles.push('PDF');
            if (!docxFile) missingFiles.push('DOCX');
            alert(`${missingFiles.join('와 ')} 파일을 업로드해주세요.\nPDF와 DOCX 파일 모두 필요합니다.`);
            return;
        }

        // 버튼 비활성화 및 로딩 표시
        const processBtn = document.getElementById('processRevisionBtn');
        const originalText = processBtn ? processBtn.textContent : '파일 파싱 및 저장';
        if (processBtn) {
            processBtn.disabled = true;
            processBtn.textContent = '비동기 파싱 시작 중...';
        }

        try {
            // 파싱 결과 초기화
            this.lastParsedContent = {};

            // 파일 정보 저장 (병합 시 필요)
            this.lastUploadedFiles = {
                pdf: {
                    filename: pdfFile.name,
                    size: pdfFile.size
                },
                docx: {
                    filename: docxFile.name,
                    size: docxFile.size
                }
            };

            // PDF 파일 비동기 업로드
            this.showNotification('PDF 파일 파싱을 시작합니다...', 'info');
            await this.uploadFileAsync(pdfFile, 'pdf');

            // DOCX 파일 비동기 업로드
            this.showNotification('DOCX 파일 파싱을 시작합니다...', 'info');
            await this.uploadFileAsync(docxFile, 'docx');

            this.showNotification('두 파일의 비동기 파싱이 시작되었습니다. 진행 상황을 확인해주세요.', 'success');

        } catch (error) {
            console.error('Error starting async processing:', error);
            this.showNotification('비동기 파싱 시작 중 오류가 발생했습니다.', 'error');
        } finally {
            // 버튼 원상태로 복구
            if (processBtn) {
                processBtn.disabled = false;
                processBtn.textContent = originalText;
            }
        }
    },

    // 편집 모달에서 파일 업로드 처리
    async processEditUploadFiles() {
        const pdfFile = document.getElementById('editPdfFile').files[0];
        const docxFile = document.getElementById('editDocxFile').files[0];

        if (!pdfFile || !docxFile) {
            alert('PDF와 DOCX 파일을 모두 업로드해주세요.');
            return;
        }

        try {
            // 파싱 결과 초기화
            this.lastParsedContent = {};
            this.lastUploadedFiles = {
                pdf: { filename: pdfFile.name, size: pdfFile.size },
                docx: { filename: docxFile.name, size: docxFile.size }
            };

            // 편집 모달에서 파싱하는 경우 현재 편집 중인 규정 사용
            if (!this.currentRevisingRegulation && this.currentEditingRegulation) {
                this.currentRevisingRegulation = this.currentEditingRegulation;
                console.log('[Edit Upload] Using current editing regulation:', this.currentEditingRegulation);
            }

            // 비동기 파싱 시작
            this.showNotification('PDF 파일 파싱을 시작합니다...', 'info');
            await this.uploadFileAsync(pdfFile, 'pdf', true);  // 편집 모달 업로드 표시

            this.showNotification('DOCX 파일 파싱을 시작합니다...', 'info');
            await this.uploadFileAsync(docxFile, 'docx', true);  // 편집 모달 업로드 표시

            this.showNotification('파일 파싱이 시작되었습니다. 진행 상황을 확인해주세요.', 'success');

        } catch (error) {
            console.error('파일 업로드 오류:', error);
            this.showNotification('파일 업로드 중 오류가 발생했습니다.', 'error');
        }
    },

    // 파일 선택 시 파일 정보 표시 (이벤트 리스너 설정)
    setupFileChangeListeners() {
        // PDF 파일 변경 리스너
        const pdfInput = document.getElementById('revisionPdfFile');
        if (pdfInput) {
            pdfInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                const infoDiv = document.getElementById('pdfFileInfo');
                if (file && infoDiv) {
                    const sizeKB = (file.size / 1024).toFixed(2);
                    infoDiv.innerHTML = `✓ ${file.name} (${sizeKB} KB)`;
                    infoDiv.style.color = '#28a745';
                } else if (infoDiv) {
                    infoDiv.innerHTML = '';
                }
            });
        }

        // DOCX 파일 변경 리스너
        const docxInput = document.getElementById('revisionDocxFile');
        if (docxInput) {
            docxInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                const infoDiv = document.getElementById('docxFileInfo');
                if (file && infoDiv) {
                    const sizeKB = (file.size / 1024).toFixed(2);
                    infoDiv.innerHTML = `✓ ${file.name} (${sizeKB} KB)`;
                    infoDiv.style.color = '#28a745';
                } else if (infoDiv) {
                    infoDiv.innerHTML = '';
                }
            });
        }
    },

    // 파싱된 내용으로 편집 창 열기
    async openEditWindowWithParsedContent(parsedContent, isRevision = false) {
        console.log('[Edit] Opening edit window with parsed content');
        console.log('[Edit] Parsed content structure:', parsedContent);

        // 현재 개정 중인 규정 정보 사용
        const regulation = this.currentRevisingRegulation;
        if (!regulation) {
            console.error('[Edit] No regulation found');
            return;
        }

        console.log('[Edit] Regulation:', regulation);

        // currentEditingRegulation 설정 - saveEdit()에서 사용됨
        this.currentEditingRegulation = regulation;

        // 모달 표시
        const modal = document.getElementById('editModal');
        modal.style.display = 'flex';  // flex로 변경하여 중앙 정렬
        modal.classList.add('active');

        // 제목 설정 - regulation의 실제 필드명 확인
        const title = regulation.title || regulation.rule_nm || regulation.wz_rule_nm || '';
        document.getElementById('editModalTitle').textContent = `규정 개정 - ${title}`;

        // 기본정보 채우기 (기존 정보 유지) - 실제 필드명 사용
        document.getElementById('editTitle').value = regulation.title || regulation.rule_nm || regulation.wz_rule_nm || '';
        document.getElementById('editClassification').value = regulation.classification || regulation.wz_cate_id || regulation.wzpubno || '';

        // 날짜 필드
        const today = new Date().toISOString().split('T')[0];
        // 개정 파일 업로드 모달에서 설정한 개정일자 사용
        const revisionDate = document.getElementById('revisionDate')?.value || today;

        // editRevisionDate 필드 설정
        const revisionDateField = document.getElementById('editRevisionDate');
        if (revisionDateField) {
            revisionDateField.value = revisionDate;
        }

        // 제정일 필드 설정
        const establishDateField = document.getElementById('editEstablishDate');
        if (establishDateField) {
            const establishDate = regulation.establishedDate || regulation.first_create_date || regulation.wzestabdate || '';
            establishDateField.value = this.formatDateForInput(establishDate);
        }

        // 부서 정보 설정 - 실제 필드명 사용
        const deptSelect = document.getElementById('editDepartment');
        if (deptSelect) {
            const deptName = regulation.department || regulation.wz_dept_nm || regulation.wzmgrdptnm || '';
            // 부서 선택 옵션 로드 및 설정
            this.loadDepartmentsForEdit(deptName);
        }

        // 조문 및 부칙 탭으로 전환
        const articlesTab = document.querySelector('.tab-button[data-tab="articles"]');
        if (articlesTab) {
            articlesTab.click();
        }

        // 파싱된 내용 설정
        let contentToShow = '';

        if (parsedContent) {
            console.log('[Edit] Processing parsed content');

            // 병합된 내용 우선 확인
            if (parsedContent.merged) {
                console.log('[Edit] Found merged content');
                console.log('[Edit] Merged text type:', typeof parsedContent.merged.text);
                console.log('[Edit] Merged text exists:', !!parsedContent.merged.text);

                // 텍스트 직접 할당
                if (parsedContent.merged.text) {
                    contentToShow = parsedContent.merged.text;
                    console.log('[Edit] Using merged text, length:', contentToShow.length);
                }

                // structured_data 할당
                if (parsedContent.merged.structured_data) {
                    parsedContent.structured_data = parsedContent.merged.structured_data;
                    console.log('[Edit] Using merged structured_data');
                }
            }

            // merged에서 못 찾으면 원본 결과에서 다시 시도
            if (!contentToShow) {
                console.log('[Edit] No merged content, trying direct extraction');
                const pdfResult = parsedContent.pdf || parsedContent.pdf_result;
                const docxResult = parsedContent.docx || parsedContent.docx_result;
                const sourceResult = docxResult || pdfResult;

                if (sourceResult) {
                    // JSON 구조에서 조문내용 확인 (우선순위 높음)
                    if (sourceResult.json && sourceResult.json.조문내용) {
                        console.log('[Edit] Converting 조문내용 from source result');
                        const articles = sourceResult.json.조문내용;
                        contentToShow = articles.map(item => {
                            let text = '';
                            if (item.번호) {
                                text += item.번호 + ' ';
                            }
                            if (item.내용) {
                                text += item.내용;
                            }
                            return text;
                        }).join('\n\n');
                        // structured_data도 설정
                        parsedContent.structured_data = sourceResult.json;
                    }
                    // 문자열인 경우
                    else if (typeof sourceResult === 'string') {
                        contentToShow = sourceResult;
                    }
                    // 다른 텍스트 필드 확인
                    else if (sourceResult) {
                        contentToShow = sourceResult.text || sourceResult.content || sourceResult.parsed_text || '';
                    }
                    console.log('[Edit] Extracted from source result, length:', contentToShow.length);
                }
            }

            // structured_data가 있고 텍스트가 없는 경우
            if (parsedContent.structured_data && !contentToShow) {
                console.log('[Edit] No text found, trying to extract from structured_data');
                const structuredData = parsedContent.structured_data;

                // 문서정보가 있으면 추출
                if (structuredData.문서정보) {
                    const docInfo = structuredData.문서정보;

                    // 제목 설정
                    if (docInfo.규정명) {
                        document.getElementById('editTitle').value = docInfo.규정명;
                    }

                    // 부서 정보 업데이트
                    if (docInfo.소관부서 || docInfo.담당부서) {
                        const deptField = document.getElementById('editDepartment');
                        if (deptField) {
                            this.loadDepartmentsForEdit(docInfo.소관부서 || docInfo.담당부서);
                        }
                    }

                    // 제정일 추출 및 설정 (파싱된 문서에서)
                    if (docInfo.제정일 || docInfo.공포일 || docInfo.최초시행일) {
                        const establishDate = docInfo.제정일 || docInfo.공포일 || docInfo.최초시행일;
                        const establishField = document.getElementById('editEstablishDate');
                        if (establishField) {
                            establishField.value = this.formatDateForInput(establishDate);
                            // regulation 객체에도 저장
                            regulation.establishedDate = establishDate;
                            this.currentEditingRegulation.establishedDate = establishDate;
                        }
                        console.log('[Edit] 제정일 설정 from 문서정보:', establishDate);
                    }

                    // 시행일 설정
                    if (docInfo.시행일) {
                        const effectiveField = document.getElementById('editEffectiveDate');
                        if (effectiveField) {
                            effectiveField.value = this.formatDateForInput(docInfo.시행일);
                        }
                    }
                }

                // 조문내용을 텍스트로 변환 (글머리 기호 포함)
                if (structuredData.조문내용 && Array.isArray(structuredData.조문내용)) {
                    console.log('[Edit] Converting structured data to text');
                    contentToShow = structuredData.조문내용.map(section => {
                        let text = '';

                        // 번호(글머리 기호)가 있는 경우 추가
                        if (section.번호) {
                            text += section.번호;
                            // 번호 뒤에 공백 추가 (내용과 구분)
                            if (section.제목 || section.내용) {
                                text += ' ';
                            }
                        }

                        // 제목이 있는 경우
                        if (section.제목) {
                            text += section.제목;
                        }

                        // 내용이 있는 경우
                        if (section.내용) {
                            // 제목이 있으면 줄바꿈 후 내용, 없으면 바로 내용
                            if (section.제목) {
                                text += '\n' + section.내용;
                            } else {
                                text += section.내용;
                            }
                        }

                        return text;
                    }).join('\n\n');  // 각 섹션 간에 빈 줄 추가
                }
            }
            // 내용이 아직 없으면 개별 파싱 결과에서 직접 찾기
            if (!contentToShow) {
                // DOCX 결과에서 찾기
                if (parsedContent.docx_result) {
                    const docx = parsedContent.docx_result;
                    // JSON 조문내용 확인
                    if (docx.json && docx.json.조문내용) {
                        console.log('[Edit] Converting 조문내용 from docx_result');
                        contentToShow = docx.json.조문내용.map(item => {
                            let text = '';
                            if (item.번호) text += item.번호 + ' ';
                            if (item.내용) text += item.내용;
                            return text;
                        }).join('\n\n');
                    } else {
                        contentToShow = docx.text || docx.content || docx.parsed_text || docx.full_text || '';
                    }
                    if (contentToShow) {
                        console.log('[Edit] DOCX 결과에서 텍스트 추출, length:', contentToShow.length);
                    }
                }

                // 아직도 없으면 PDF 결과에서 찾기
                if (!contentToShow && parsedContent.pdf_result) {
                    const pdf = parsedContent.pdf_result;
                    // JSON 조문내용 확인
                    if (pdf.json && pdf.json.조문내용) {
                        console.log('[Edit] Converting 조문내용 from pdf_result');
                        contentToShow = pdf.json.조문내용.map(item => {
                            let text = '';
                            if (item.번호) text += item.번호 + ' ';
                            if (item.내용) text += item.내용;
                            return text;
                        }).join('\n\n');
                    } else {
                        contentToShow = pdf.text || pdf.content || pdf.parsed_text || pdf.full_text || '';
                    }
                    if (contentToShow) {
                        console.log('[Edit] PDF 결과에서 텍스트 추출, length:', contentToShow.length);
                    }
                }

                // 일반 텍스트 필드
                if (!contentToShow && parsedContent.text) {
                    contentToShow = parsedContent.text;
                }

                // parsedContent가 직접 문자열인 경우
                if (!contentToShow && typeof parsedContent === 'string') {
                    contentToShow = parsedContent;
                }
            }

            // 조문 내용 설정
            console.log('[Edit] Setting content to textareas, length:', contentToShow ? contentToShow.length : 0);

            const articleTextarea = document.getElementById('articleContent');
            const articlePreview = document.getElementById('articlePreview');

            if (contentToShow) {
                // 편집 영역에 내용 설정
                if (articleTextarea) {
                    articleTextarea.value = contentToShow;
                    console.log('[Edit] Set article content textarea');
                    // 높이 자동 조정
                    this.adjustTextareaHeight(articleTextarea);
                }

                // 미리보기 업데이트
                if (articlePreview) {
                    // HTML로 변환하여 미리보기 표시
                    this.previewArticles();
                    console.log('[Edit] Updated article preview');
                }

                // 파싱된 내용 플래그 설정
                this.currentEditingRegulation = {
                    ...this.currentEditingRegulation,
                    hasParsedContent: true,
                    parsedContent: contentToShow
                };
            } else {
                // 파싱된 내용이 없는 경우
                console.log('[Edit] No parsed content found');

                // 기존 내용 사용
                const existingContent = regulation.content || regulation.wz_content || '';

                if (articleTextarea) {
                    articleTextarea.value = existingContent;
                    this.adjustTextareaHeight(articleTextarea);
                }

                if (existingContent) {
                    this.previewArticles();
                }

                this.currentEditingRegulation = {
                    ...this.currentEditingRegulation,
                    hasParsedContent: false
                };
            }
        } else {
            // parsedContent 자체가 없는 경우 - 기존 내용 사용
            console.log('[Edit] No parsed content provided, using existing content');
            const existingContent = regulation.content || regulation.wz_content || '';

            const articleTextarea = document.getElementById('articleContent');
            if (articleTextarea) {
                articleTextarea.value = existingContent;
                this.adjustTextareaHeight(articleTextarea);
            }

            if (existingContent) {
                this.previewArticles();
            }
        }

        // 조문 탭으로 전환
        this.switchEditTab('articles');

        // 개정 API 호출 제거 - 파싱된 내용으로 바로 편집창이 열리므로 불필요
    },

    // 사용하지 않는 함수들 제거됨 (openRevisionEditModal, saveRevision, closeRevisionEditModal, addArticle, formatContent)

    // 알림 표시
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type}`;
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px; animation: slideUp 0.3s;';

        const icon = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }[type] || 'ℹ️';

        notification.innerHTML = `
            <span>${icon}</span>
            <span>${message}</span>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.3s';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    },

    // 비동기 파일 업로드 및 파싱 (XMLHttpRequest로 진행률 표시)
    async uploadFileAsync(file, fileType, isFromEditModal = false) {
        const self = this;
        const endpoint = fileType === 'pdf' ? '/api/v1/async/upload-pdf-async' : '/api/v1/async/upload-docx-async';
        const fileTypeName = fileType.toUpperCase();

        // 전체 화면 오버레이 표시
        self.showUploadOverlay(fileType);

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            const formData = new FormData();
            formData.append('file', file);

            // 업로드 진행률 이벤트
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    const percent = Math.round((event.loaded / event.total) * 100);
                    // 진행률 UI 업데이트
                    self.updateUploadProgress(fileType, percent);
                }
            });

            // 완료 이벤트
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const data = JSON.parse(xhr.responseText);
                        console.log('Async upload started:', data);

                        // 완료 표시 후 오버레이 닫기
                        self.showUploadComplete(fileType);

                        // 작업 추적 시작 (편집 모달 여부 포함)
                        self.startTaskTracking(data.task_id, fileType, data.filename, isFromEditModal);

                        resolve(data);
                    } catch (e) {
                        self.hideUploadOverlay();
                        reject(new Error('응답 파싱 오류'));
                    }
                } else {
                    self.hideUploadOverlay();
                    reject(new Error(`파일 업로드 실패: ${xhr.status}`));
                }
            });

            // 에러 이벤트
            xhr.addEventListener('error', () => {
                self.hideUploadOverlay();
                reject(new Error('네트워크 오류'));
            });

            xhr.addEventListener('timeout', () => {
                self.hideUploadOverlay();
                reject(new Error('업로드 시간 초과'));
            });

            // 요청 설정 및 전송
            xhr.open('POST', endpoint);
            xhr.withCredentials = true;
            xhr.timeout = 300000; // 5분 타임아웃
            xhr.send(formData);
        });
    },

    // 전체 화면 업로드 오버레이 표시
    showUploadOverlay(fileType) {
        // 이미 있으면 제거
        this.hideUploadOverlay();

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
                    border-top-color: #667eea;
                    border-radius: 50%;
                    animation: spinLarge 1s linear infinite;
                    margin: 0 auto 24px;
                }
                @keyframes spinLarge {
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
                    background: linear-gradient(90deg, #667eea, #764ba2);
                    border-radius: 10px;
                    transition: width 0.3s ease;
                    width: 0%;
                }
                .upload-percent {
                    font-size: 28px;
                    font-weight: 700;
                    color: #667eea;
                }
            </style>
            <div class="upload-modal">
                <div class="upload-spinner-large"></div>
                <div class="upload-title" id="uploadTitle">${fileType.toUpperCase()} 파일 업로드 중</div>
                <div class="upload-subtitle">잠시만 기다려주세요...</div>
                <div class="upload-progress-wrap">
                    <div class="upload-progress-bar" id="uploadProgressBar"></div>
                </div>
                <div class="upload-percent"><span id="uploadPercent">0</span>%</div>
            </div>
        `;
        document.body.appendChild(overlay);
    },

    // 업로드 진행률 업데이트
    updateUploadProgress(fileType, percent) {
        const progressBar = document.getElementById('uploadProgressBar');
        const percentText = document.getElementById('uploadPercent');
        const title = document.getElementById('uploadTitle');

        if (progressBar) progressBar.style.width = percent + '%';
        if (percentText) percentText.textContent = percent;
        if (title) title.textContent = `${fileType.toUpperCase()} 파일 업로드 중`;
    },

    // 업로드 오버레이 숨기기
    hideUploadOverlay() {
        const overlay = document.getElementById('uploadOverlay');
        if (overlay) {
            overlay.remove();
        }
    },

    // 업로드 완료 표시
    showUploadComplete(fileType) {
        const modal = document.querySelector('.upload-modal');
        if (modal) {
            modal.innerHTML = `
                <div style="font-size: 60px; margin-bottom: 16px;">✅</div>
                <div class="upload-title" style="color: #22c55e;">${fileType.toUpperCase()} 업로드 완료!</div>
                <div class="upload-subtitle">파싱을 시작합니다...</div>
            `;
            setTimeout(() => this.hideUploadOverlay(), 1500);
        }
    },

    // 작업 추적 시작
    startTaskTracking(taskId, fileType, filename, isFromEditModal = false) {
        const taskInfo = {
            type: fileType,
            filename: filename,
            started_at: new Date(),
            interval_id: null,
            isFromEditModal: isFromEditModal
        };

        // 진행률 UI 표시
        this.showTaskProgress(taskId, taskInfo);

        // 폴링 시작
        taskInfo.interval_id = setInterval(() => {
            this.pollTaskStatus(taskId);
        }, this.taskPollingInterval);

        this.activeAsyncTasks.set(taskId, taskInfo);
        console.log(`Started tracking task ${taskId} (${fileType}: ${filename})`);
    },

    // 작업 상태 폴링
    async pollTaskStatus(taskId) {
        try {
            const response = await fetch(`/api/v1/async/task-status/${taskId}`, {
                method: 'GET',
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                const task = data.task;

                console.log(`Task ${taskId} status:`, task.status, `${task.progress}%`);

                // 진행률 업데이트
                this.updateTaskProgress(taskId, task);

                // 완료되었으면 결과 가져오기
                if (task.status === 'completed') {
                    await this.handleTaskCompletion(taskId);
                } else if (task.status === 'failed') {
                    await this.handleTaskFailure(taskId, task.error);
                }
            } else {
                console.error(`Failed to poll task ${taskId}:`, response.status);
            }
        } catch (error) {
            console.error(`Error polling task ${taskId}:`, error);
        }
    },

    // 작업 완료 처리
    async handleTaskCompletion(taskId) {
        try {
            const response = await fetch(`/api/v1/async/task-result/${taskId}`, {
                method: 'GET',
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                const taskInfo = this.activeAsyncTasks.get(taskId);

                console.log(`Task ${taskId} completed:`, data.result);

                // 폴링 중지
                this.stopTaskTracking(taskId);

                // 파싱 결과 처리 - result가 중첩된 경우 처리
                const parsedResult = data.result?.result || data.result;
                console.log('파싱 결과 구조:', {
                    taskId: taskId,
                    type: taskInfo.type,
                    hasResult: !!parsedResult,
                    resultKeys: parsedResult ? Object.keys(parsedResult) : []
                });
                this.handleParsingResult(parsedResult, taskInfo);

                this.showNotification(`${taskInfo.filename} 파싱이 완료되었습니다.`, 'success');
            } else {
                throw new Error(`결과 조회 실패: ${response.status}`);
            }
        } catch (error) {
            console.error(`Error getting task result ${taskId}:`, error);
            this.showNotification('파싱 결과 조회 중 오류가 발생했습니다.', 'error');
        }
    },

    // 작업 실패 처리
    async handleTaskFailure(taskId, error) {
        const taskInfo = this.activeAsyncTasks.get(taskId);

        console.error(`Task ${taskId} failed:`, error);

        // 폴링 중지
        this.stopTaskTracking(taskId);

        this.showNotification(`${taskInfo.filename} 파싱이 실패했습니다: ${error}`, 'error');
    },

    // 파싱 결과 처리
    handleParsingResult(result, taskInfo) {
        // 기존 파싱 로직과 동일하게 처리
        if (taskInfo.type === 'pdf') {
            this.handlePdfParsingResult(result);
        } else if (taskInfo.type === 'docx') {
            this.handleDocxParsingResult(result);
        }

        // 두 파일이 모두 완료되었으면 비교 모달 표시
        this.checkIfBothFilesCompleted();
    },

    // PDF 파싱 결과 처리
    handlePdfParsingResult(result) {
        if (!this.lastParsedContent) {
            this.lastParsedContent = {};
        }

        // 중첩된 result 처리
        const actualResult = result?.result || result;

        this.lastParsedContent.pdf_result = actualResult;
        console.log('PDF parsing completed:', actualResult);
        console.log('PDF result structure:', {
            has_text: !!actualResult?.text,
            has_structured_data: !!actualResult?.structured_data,
            has_content: !!actualResult?.content,
            has_parsed_text: !!actualResult?.parsed_text,
            keys: actualResult ? Object.keys(actualResult) : []
        });
    },

    // DOCX 파싱 결과 처리
    handleDocxParsingResult(result) {
        if (!this.lastParsedContent) {
            this.lastParsedContent = {};
        }

        // 중첩된 result 처리
        const actualResult = result?.result || result;

        this.lastParsedContent.docx_result = actualResult;
        console.log('DOCX parsing completed:', actualResult);
        console.log('DOCX result structure:', {
            has_text: !!actualResult?.text,
            has_structured_data: !!actualResult?.structured_data,
            has_content: !!actualResult?.content,
            has_parsed_text: !!actualResult?.parsed_text,
            keys: actualResult ? Object.keys(actualResult) : []
        });
    },

    // 두 파일 파싱 완료 확인
    checkIfBothFilesCompleted() {
        if (this.lastParsedContent &&
            this.lastParsedContent.pdf_result &&
            this.lastParsedContent.docx_result) {

            // regulation 정보 백업
            this.lastParsedContent.regulation = this.currentRevisingRegulation;

            // 개정 사유 저장
            const revisionReason = document.getElementById('revisionReason');
            if (revisionReason && revisionReason.value) {
                this.lastParsedContent.revisionReason = revisionReason.value;
            }

            // 편집 모달에서 업로드한 경우 바로 내용 업데이트
            const editModal = document.getElementById('editModal');
            if (editModal && editModal.style.display === 'flex') {
                console.log('[Parsing Complete] Updating edit modal with parsed content');
                // 파싱된 내용으로 편집 화면 업데이트
                this.updateEditModalWithParsedContent();
            }
            // 개정 모달에서 업로드한 경우
            else {
                // 자동 병합 및 편집창 열기 (비교 모달 생략)
                setTimeout(() => {
                    this.closeRevisionUploadModal(false);  // 데이터 초기화하지 않음
                    this.autoMergeAndOpenEditor();
                }, 500);
            }
        }
    },

    // 편집 모달에 파싱된 내용 업데이트
    updateEditModalWithParsedContent() {
        console.log('[Update Edit Modal] Starting update with parsed content');

        // 파싱 결과 추출
        const pdfResult = this.lastParsedContent?.pdf_result || this.lastParsedContent?.pdf;
        const docxResult = this.lastParsedContent?.docx_result || this.lastParsedContent?.docx;

        let textContent = '';
        let bulletPoints = [];  // PDF에서 추출한 글머리기호
        let docxContent = [];   // DOCX에서 추출한 내용

        // PDF에서 글머리기호 추출
        if (pdfResult) {
            console.log('[Update Edit Modal] Processing PDF for bullet points');
            if (pdfResult.json && pdfResult.json.조문내용) {
                // 조문의 번호(글머리기호)만 추출
                bulletPoints = pdfResult.json.조문내용.map(item => item.번호 || '').filter(num => num);
                console.log('[Update Edit Modal] Extracted bullet points from PDF:', bulletPoints);
            }
        }

        // DOCX에서 내용 추출
        if (docxResult) {
            console.log('[Update Edit Modal] Processing DOCX for content');
            if (docxResult.json && docxResult.json.조문내용) {
                // DOCX의 조문 내용 추출
                const docxArticles = docxResult.json.조문내용;

                // DOCX 내용에서 글머리기호를 제거 (이미 PDF에서 가져옴)
                docxContent = docxArticles.map(item => {
                    let content = item.내용 || '';
                    // 만약 내용이 글머리기호로 시작하면 제거
                    // 예: "제1조 내용" -> "내용"
                    content = content.replace(/^제\d+조\s*/, '');
                    content = content.replace(/^제\d+항\s*/, '');
                    content = content.replace(/^[①②③④⑤⑥⑦⑧⑨⑩]+\s*/, '');
                    content = content.replace(/^\d+\.\s*/, '');
                    return content.trim();
                }).filter(content => content);

                console.log('[Update Edit Modal] Extracted content from DOCX (글머리기호 제거), articles count:', docxContent.length);
                if (docxContent.length > 0) {
                    console.log('[Update Edit Modal] First DOCX content sample:', docxContent[0].substring(0, 100));
                }
            } else if (typeof docxResult === 'string') {
                docxContent = [docxResult];
            } else if (typeof docxResult === 'object') {
                // 다양한 필드에서 텍스트 찾기
                const text = docxResult.text ||
                            docxResult.content ||
                            docxResult.parsed_text ||
                            docxResult.full_text ||
                            '';
                if (text) {
                    docxContent = [text];
                }
            }

            // 문서정보 업데이트 (DOCX 우선, PDF 보조)
            let docInfo = null;
            if (docxResult && docxResult.json && docxResult.json.문서정보) {
                docInfo = docxResult.json.문서정보;
            } else if (pdfResult && pdfResult.json && pdfResult.json.문서정보) {
                docInfo = pdfResult.json.문서정보;
            }

            if (docInfo) {
                if (docInfo.규정명) {
                    const titleField = document.getElementById('editTitle');
                    if (titleField) titleField.value = docInfo.규정명;
                }
                if (docInfo.소관부서 || docInfo.담당부서) {
                    const deptField = document.getElementById('editDepartment');
                    if (deptField) deptField.value = docInfo.소관부서 || docInfo.담당부서;
                }
                // 제정일 추출 및 설정
                if (docInfo.제정일 || docInfo.공포일 || docInfo.최초시행일) {
                    const establishDate = docInfo.제정일 || docInfo.공포일 || docInfo.최초시행일;
                    const establishField = document.getElementById('editEstablishDate');
                    if (establishField) {
                        establishField.value = this.formatDateForInput(establishDate);
                        // currentEditingRegulation에도 저장
                        if (this.currentEditingRegulation) {
                            this.currentEditingRegulation.establishedDate = establishDate;
                        }
                    }
                    console.log('[Update Edit Modal] 제정일 추출:', establishDate);
                }
            }
        }

        // 병합: PDF의 글머리기호와 DOCX의 내용 결합
        if (bulletPoints.length > 0 && docxContent.length > 0) {
            console.log('[Update Edit Modal] Merging PDF bullet points with DOCX content');
            // 글머리기호와 내용을 1:1로 매칭
            const mergedArticles = [];
            const maxLength = Math.max(bulletPoints.length, docxContent.length);

            for (let i = 0; i < maxLength; i++) {
                let articleText = '';
                if (i < bulletPoints.length && bulletPoints[i]) {
                    articleText += bulletPoints[i] + ' ';
                }
                if (i < docxContent.length && docxContent[i]) {
                    articleText += docxContent[i];
                }
                if (articleText.trim()) {
                    mergedArticles.push(articleText);
                }
            }

            textContent = mergedArticles.join('\n\n');
            console.log('[Update Edit Modal] Merged content created, articles count:', mergedArticles.length);
        }
        // PDF만 있는 경우
        else if (pdfResult) {
            console.log('[Update Edit Modal] Using PDF content only');
            if (pdfResult.json && pdfResult.json.조문내용) {
                const articles = pdfResult.json.조문내용;
                textContent = articles.map(item => {
                    let text = '';
                    if (item.번호) text += item.번호 + ' ';
                    if (item.내용) text += item.내용;
                    return text;
                }).join('\n\n');
            } else {
                textContent = pdfResult.text || pdfResult.content || '';
            }
        }
        // DOCX만 있는 경우
        else if (docxContent.length > 0) {
            console.log('[Update Edit Modal] Using DOCX content only - showing as preview');
            textContent = Array.isArray(docxContent) ? docxContent.join('\n\n') : docxContent;
        }

        // 조문 및 부칙 탭에 내용 설정
        if (textContent) {
            console.log('[Update Edit Modal] Setting content, length:', textContent.length);
            const articleTextarea = document.getElementById('articleContent');
            if (articleTextarea) {
                articleTextarea.value = textContent;
                // 높이 자동 조정
                this.adjustTextareaHeight(articleTextarea);
                // 미리보기 업데이트
                this.previewArticles();
            }

            // 조문 및 부칙 탭으로 전환
            const articlesTab = document.querySelector('.tab-button[data-tab="articles"]');
            if (articlesTab) {
                articlesTab.click();
            }

            this.showNotification('파싱된 내용이 편집창에 로드되었습니다.', 'success');
        } else {
            console.warn('[Update Edit Modal] No text content found in parsing result');
            this.showNotification('파싱된 텍스트를 찾을 수 없습니다.', 'warning');
        }
    },

    // 자동 병합 및 편집창 열기
    async autoMergeAndOpenEditor() {
        console.log('[Auto-merge] Starting auto-merge process');
        console.log('[Auto-merge] Full lastParsedContent:', JSON.stringify(this.lastParsedContent, null, 2));

        try {
            // PDF나 DOCX 파싱 결과가 있는지 확인 - 다양한 필드명 확인
            const pdfResult = this.lastParsedContent?.pdf || this.lastParsedContent?.pdf_result;
            const docxResult = this.lastParsedContent?.docx || this.lastParsedContent?.docx_result;

            console.log('[Auto-merge] PDF Result keys:', pdfResult ? Object.keys(pdfResult) : 'null');
            console.log('[Auto-merge] DOCX Result keys:', docxResult ? Object.keys(docxResult) : 'null');

            if (!pdfResult && !docxResult) {
                console.warn('[Auto-merge] No parsing results found');
                alert('병합할 내용이 없습니다.');
                return;
            }

            // PDF와 DOCX를 별도로 처리
            let textContent = null;
            let structuredData = null;
            let bulletPoints = [];  // PDF에서 추출한 글머리기호
            let docxContent = '';   // DOCX에서 추출한 내용

            // PDF에서 글머리기호 추출
            if (pdfResult) {
                console.log('[Auto-merge] Processing PDF for bullet points');
                if (pdfResult.json && pdfResult.json.조문내용) {
                    // 조문의 번호(글머리기호)만 추출
                    bulletPoints = pdfResult.json.조문내용.map(item => item.번호 || '').filter(num => num);
                    console.log('[Auto-merge] Extracted bullet points from PDF:', bulletPoints);
                }
                structuredData = pdfResult.json;
            }

            // DOCX에서 내용 추출
            if (docxResult) {
                console.log('[Auto-merge] Processing DOCX for content');
                if (docxResult.json && docxResult.json.조문내용) {
                    // DOCX의 조문 내용 추출
                    const docxArticles = docxResult.json.조문내용;

                    // DOCX 내용에서 글머리기호를 제거 (이미 PDF에서 가져옴)
                    docxContent = docxArticles.map(item => {
                        let content = item.내용 || '';
                        // 만약 내용이 글머리기호로 시작하면 제거
                        // 예: "제1조 내용" -> "내용"
                        content = content.replace(/^제\d+조\s*/, '');
                        content = content.replace(/^제\d+항\s*/, '');
                        content = content.replace(/^[①②③④⑤⑥⑦⑧⑨⑩]+\s*/, '');
                        content = content.replace(/^\d+\.\s*/, '');
                        return content.trim();
                    }).filter(content => content);

                    console.log('[Auto-merge] Extracted content from DOCX (글머리기호 제거), articles count:', docxContent.length);
                    if (docxContent.length > 0) {
                        console.log('[Auto-merge] First DOCX content sample:', docxContent[0].substring(0, 100));
                    }
                } else if (typeof docxResult === 'string') {
                    docxContent = [docxResult];
                } else if (typeof docxResult === 'object') {
                    // 다양한 필드에서 텍스트 찾기
                    const text = docxResult.text ||
                                docxResult.content ||
                                docxResult.parsed_text ||
                                docxResult.full_text ||
                                (docxResult.data && docxResult.data.text) ||
                                (docxResult.result && docxResult.result.text) ||
                                '';
                    if (text) {
                        docxContent = [text];
                    }
                }

                // DOCX에 구조화된 데이터가 있으면 우선 사용
                if (docxResult.json) {
                    structuredData = docxResult.json;
                }
            }

            // 병합: PDF의 글머리기호와 DOCX의 내용 결합
            if (bulletPoints.length > 0 && docxContent.length > 0) {
                console.log('[Auto-merge] Merging PDF bullet points with DOCX content');
                // 글머리기호와 내용을 1:1로 매칭
                const mergedArticles = [];
                const maxLength = Math.max(bulletPoints.length, docxContent.length);

                for (let i = 0; i < maxLength; i++) {
                    let articleText = '';
                    if (i < bulletPoints.length && bulletPoints[i]) {
                        articleText += bulletPoints[i] + ' ';
                    }
                    if (i < docxContent.length && docxContent[i]) {
                        articleText += docxContent[i];
                    }
                    if (articleText.trim()) {
                        mergedArticles.push(articleText);
                    }
                }

                textContent = mergedArticles.join('\n\n');
                console.log('[Auto-merge] Merged content created, articles count:', mergedArticles.length);

                // 문서정보도 병합 (DOCX 우선, PDF 보조)
                if (docxResult.json) {
                    structuredData = docxResult.json;
                } else if (pdfResult.json) {
                    structuredData = pdfResult.json;
                }
            }
            // PDF만 있는 경우
            else if (pdfResult) {
                console.log('[Auto-merge] Using PDF content only');
                if (pdfResult.json && pdfResult.json.조문내용) {
                    const articles = pdfResult.json.조문내용;
                    textContent = articles.map(item => {
                        let text = '';
                        if (item.번호) text += item.번호 + ' ';
                        if (item.내용) text += item.내용;
                        return text;
                    }).join('\n\n');
                } else {
                    textContent = pdfResult.text || pdfResult.content || '';
                }
            }
            // DOCX만 있는 경우
            else if (docxContent.length > 0) {
                console.log('[Auto-merge] Using DOCX content only');
                textContent = Array.isArray(docxContent) ? docxContent.join('\n\n') : docxContent;
            }

            console.log('[Auto-merge] Extracted text length:', textContent ? textContent.length : 0);
            if (textContent && textContent.length > 0) {
                console.log('[Auto-merge] Text preview:', textContent.substring(0, 200) + '...');
            }

            // 새로운 merged 객체 생성 (참조가 아닌 복사)
            let mergedContent = {
                text: textContent || '',
                structured_data: structuredData || sourceResult?.structured_data || sourceResult?.json || null,
                metadata: sourceResult?.metadata || sourceResult?.document_info || null
            };

            console.log('[Auto-merge] Created merged content with text length:', mergedContent.text.length);

            // lastParsedContent에 merged 추가
            this.lastParsedContent.merged = mergedContent;

            // 병합된 데이터를 백엔드에 저장
            try {
                console.log('[Auto-merge] Saving merged data to backend');
                const saveResponse = await fetch('/api/v1/rule/save-merged', {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        merged_data: mergedContent,
                        pdf_filename: this.lastUploadedFiles?.pdf?.name || 'unknown.pdf',
                        docx_filename: this.lastUploadedFiles?.docx?.name || 'unknown.docx',
                        rule_id: this.currentRevisingRegulation?.wzruleseq || this.currentRevisingRegulation?.id || 0,
                        timestamp: new Date().toISOString()
                    })
                });

                if (saveResponse.ok) {
                    const saveData = await saveResponse.json();
                    console.log('[Auto-merge] Merged data saved to:', saveData.file_path);
                } else {
                    console.warn('[Auto-merge] Failed to save merged data to backend');
                }
            } catch (error) {
                console.error('[Auto-merge] Error saving merged data:', error);
                // 저장 실패해도 계속 진행
            }

            // 선택된 규정으로 편집창 열기
            if (this.selectedRegulations.size === 1) {
                const regulationId = Array.from(this.selectedRegulations)[0];
                // ID 필드명 다양하게 확인
                const regulation = this.regulations.find(r =>
                    r.wz_rule_id == regulationId ||
                    r.id == regulationId ||
                    r.wzruleseq == regulationId ||
                    r.rule_id == regulationId
                );

                if (regulation) {
                    console.log('[Auto-merge] Found regulation:', {
                        id: regulationId,
                        name: regulation.rule_nm || regulation.title || regulation.wzname,
                        regulation: regulation
                    });

                    // currentRevisingRegulation 설정
                    this.currentRevisingRegulation = regulation;

                    // 편집창 열기
                    this.openEditWindowWithParsedContent(this.lastParsedContent, true);
                } else {
                    console.error('[Auto-merge] Regulation not found for ID:', regulationId);
                    console.log('[Auto-merge] Available regulations:', this.regulations.map(r => ({
                        wz_rule_id: r.wz_rule_id,
                        id: r.id,
                        wzruleseq: r.wzruleseq,
                        name: r.rule_nm || r.title
                    })));
                }
            } else {
                console.log('[Auto-merge] No single regulation selected, count:', this.selectedRegulations.size);
                // 내규가 선택되지 않았다면 알림
                if (this.selectedRegulations.size === 0) {
                    alert('편집할 내규를 선택해주세요.');
                }
            }

        } catch (error) {
            console.error('자동 병합 오류:', error);
            // 오류가 있어도 편집창은 열기
            this.proceedWithParsedContent(false);
        }
    },

    // 작업 추적 중지
    stopTaskTracking(taskId) {
        const taskInfo = this.activeAsyncTasks.get(taskId);
        if (taskInfo && taskInfo.interval_id) {
            clearInterval(taskInfo.interval_id);
        }

        // 진행률 UI 제거
        this.hideTaskProgress(taskId);

        this.activeAsyncTasks.delete(taskId);
        console.log(`Stopped tracking task ${taskId}`);
    },

    // 진행률 UI 표시
    showTaskProgress(taskId, taskInfo) {
        // 진행률 UI 컨테이너 찾기 또는 생성
        let progressContainer = document.getElementById('taskProgressContainer');
        if (!progressContainer) {
            progressContainer = document.createElement('div');
            progressContainer.id = 'taskProgressContainer';
            progressContainer.style.cssText = `
                position: fixed;
                top: 80px;
                right: 20px;
                z-index: 9998;
                max-width: 350px;
            `;
            document.body.appendChild(progressContainer);
        }

        // 개별 작업 진행률 UI 생성
        const progressDiv = document.createElement('div');
        progressDiv.id = `task-${taskId}`;
        progressDiv.className = 'task-progress';
        progressDiv.style.cssText = `
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            animation: slideInFromRight 0.3s;
        `;

        progressDiv.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: bold; font-size: 14px;">${taskInfo.filename}</span>
                <button onclick="RegulationEditor.cancelAsyncTask('${taskId}')"
                        style="background: #ff4444; color: white; border: none; border-radius: 4px; padding: 2px 8px; cursor: pointer;">
                    취소
                </button>
            </div>
            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
                ${taskInfo.type.toUpperCase()} 파일 파싱 중...
            </div>
            <div style="background: #f0f0f0; border-radius: 10px; height: 8px; overflow: hidden;">
                <div id="progress-bar-${taskId}"
                     style="background: #4CAF50; height: 100%; width: 0%; transition: width 0.3s;">
                </div>
            </div>
            <div id="progress-text-${taskId}" style="font-size: 11px; color: #888; margin-top: 4px;">
                0% - 작업 시작 중...
            </div>
        `;

        progressContainer.appendChild(progressDiv);
    },

    // 진행률 UI 업데이트
    updateTaskProgress(taskId, task) {
        const progressBar = document.getElementById(`progress-bar-${taskId}`);
        const progressText = document.getElementById(`progress-text-${taskId}`);

        if (progressBar && progressText) {
            progressBar.style.width = `${task.progress}%`;
            progressText.textContent = `${task.progress}% - ${task.message || '처리 중...'}`;

            // 상태에 따른 색상 변경
            if (task.status === 'completed') {
                progressBar.style.background = '#4CAF50';
            } else if (task.status === 'failed') {
                progressBar.style.background = '#f44336';
            } else if (task.status === 'running') {
                progressBar.style.background = '#2196F3';
            }
        }
    },

    // 진행률 UI 숨기기
    hideTaskProgress(taskId) {
        const progressDiv = document.getElementById(`task-${taskId}`);
        if (progressDiv) {
            progressDiv.style.animation = 'fadeOut 0.3s';
            setTimeout(() => {
                progressDiv.remove();

                // 모든 진행률이 완료되면 컨테이너도 제거
                const container = document.getElementById('taskProgressContainer');
                if (container && container.children.length === 0) {
                    container.remove();
                }
            }, 300);
        }
    },

    // 비동기 작업 취소
    async cancelAsyncTask(taskId) {
        try {
            const response = await fetch(`/api/v1/async/task/${taskId}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            if (response.ok) {
                this.stopTaskTracking(taskId);
                this.showNotification('작업이 취소되었습니다.', 'warning');
            } else {
                throw new Error(`작업 취소 실패: ${response.status}`);
            }
        } catch (error) {
            console.error('Error cancelling task:', error);
            this.showNotification('작업 취소 중 오류가 발생했습니다.', 'error');
        }
    },

    // 이벤트 리스너 설정
    setupEventListeners() {
        // 등록 유형 변경시 파일 업로드 섹션 표시/숨김
        const newType = document.getElementById('newType');
        if (newType) {
            newType.addEventListener('change', (e) => {
                document.getElementById('fileUploadSection').style.display =
                    e.target.value === 'hwpx' ? 'block' : 'none';
            });
        }

        // 엔터키로 검색
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.searchRegulations();
                }
            });
        }

        // 조문 내용 편집 시 높이 자동 조정
        const articleContent = document.getElementById('articleContent');
        if (articleContent) {
            articleContent.addEventListener('input', () => {
                this.adjustTextareaHeight(articleContent);
            });

            // 초기 높이 설정
            this.adjustTextareaHeight(articleContent);
        }
    },

    // 로그아웃
    async logout() {
        if (confirm('로그아웃 하시겠습니까?')) {
            try {
                const response = await fetch('/api/v1/auth/logout', {
                    method: 'POST',
                    credentials: 'include'
                });
                
                if (response.ok) {
                    alert('로그아웃되었습니다.');
                    window.location.href = '/login';
                } else {
                    alert('로그아웃 처리 중 오류가 발생했습니다.');
                }
            } catch (error) {
                console.error('Logout error:', error);
                alert('로그아웃 처리 중 오류가 발생했습니다.');
                // 로그아웃 실패시에도 로그인 페이지로 이동
                window.location.href = '/login';
            }
        }
    },

    /**
     * 신구대비표 파일 업로드
     * @param {number} ruleSeq - wzRuleSeq 값
     * @param {File} file - 업로드할 PDF 파일
     */
    async uploadComparisonTable(ruleSeq, file) {
        if (!file) {
            throw new Error('업로드할 파일이 없습니다');
        }

        if (!file.name.toLowerCase().endsWith('.pdf')) {
            throw new Error('신구대비표는 PDF 파일만 업로드 가능합니다');
        }

        const formData = new FormData();
        formData.append('comparison_file', file);

        const response = await fetch(`/api/v1/rule/upload-comparison-table/${ruleSeq}`, {
            method: 'POST',
            credentials: 'include',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '신구대비표 업로드 실패');
        }

        const result = await response.json();
        console.log('신구대비표 업로드 성공:', result);
        return result;
    },

    // 수정 이력파일 업로드
    async uploadHistoryFile(ruleSeq, file) {
        if (!file) {
            throw new Error('업로드할 파일이 없습니다');
        }

        if (!file.name.toLowerCase().endsWith('.pdf')) {
            throw new Error('수정 이력파일은 PDF 파일만 업로드 가능합니다');
        }

        const formData = new FormData();
        formData.append('history_file', file);

        const response = await fetch(`/api/v1/rule/upload-history-file/${ruleSeq}`, {
            method: 'POST',
            credentials: 'include',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '수정 이력파일 업로드 실패');
        }

        const result = await response.json();
        console.log('수정 이력파일 업로드 성공:', result);
        return result;
    }
};

// 페이지 로드시 초기화
document.addEventListener('DOMContentLoaded', () => {
    RegulationEditor.init();
});
