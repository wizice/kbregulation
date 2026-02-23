/**
 * 규정 관리 모듈
 * 현행 내규목록, 연혁목록 관리
 */

const RegulationManager = {
    // 상태 관리
    regulations: [],
    currentPage: 1,
    pageSize: 20,
    filters: {
        dept: '',
        category: '',
        keyword: ''
    },

    /**
     * 초기화
     */
    async init() {
        await this.loadDepartments();
        await this.loadCategories();
        await this.loadRegulations();
        this.bindEvents();
    },

    /**
     * 이벤트 바인딩
     */
    bindEvents() {
        // 전체 선택 체크박스
        const selectAll = document.getElementById('selectAll');
        if (selectAll) {
            selectAll.addEventListener('change', (e) => {
                const checkboxes = document.querySelectorAll('.regulation-checkbox');
                checkboxes.forEach(cb => cb.checked = e.target.checked);
            });
        }

        // 검색 입력 디바운스
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input',
                CommonUtils.debounce(() => this.search(), 500)
            );
        }

        // 필터 변경
        ['deptFilter', 'categoryFilter'].forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => this.search());
            }
        });
    },

    /**
     * 부서 목록 로드
     */
    async loadDepartments() {
        try {
            const data = await CommonUtils.apiCall('/api/v1/wz_dept/list');
            const select = document.getElementById('deptFilter');
            if (select && data.departments) {
                data.departments.forEach(dept => {
                    const option = document.createElement('option');
                    option.value = dept.dept_code;
                    option.textContent = dept.dept_name;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('부서 목록 로드 실패:', error);
        }
    },

    /**
     * 분류 목록 로드
     */
    async loadCategories() {
        try {
            const data = await CommonUtils.apiCall('/api/v1/classification/list');
            const select = document.getElementById('categoryFilter');
            if (select && data.categories) {
                data.categories.forEach(cat => {
                    const option = document.createElement('option');
                    option.value = cat.cate_code;
                    option.textContent = cat.cate_name;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('분류 목록 로드 실패:', error);
        }
    },

    /**
     * 규정 목록 로드
     */
    async loadRegulations(page = 1) {
        // 페이지 로드 시 서버사이드 렌더링된 데이터가 있는지 확인
        const tbody = document.getElementById('regulationsList');
        if (tbody && tbody.querySelector('tr[data-id]')) {
            // 이미 서버에서 렌더링된 데이터가 있으면 스킵
            return;
        }

        CommonUtils.showLoading(true);

        try {
            const data = await CommonUtils.apiCall('/regulations/api/current');

            if (data.success) {
                this.regulations = data.data || [];
                this.currentPage = page;

                this.renderTable();
                this.updateTotalCount(data.total_count);
            } else {
                throw new Error(data.error || '데이터 로드 실패');
            }

        } catch (error) {
            console.error('규정 목록 로드 실패:', error);
            CommonUtils.showAlert('규정 목록을 불러오는데 실패했습니다.', 'danger');
        } finally {
            CommonUtils.showLoading(false);
        }
    },

    /**
     * 전체 건수 업데이트
     */
    updateTotalCount(count) {
        const totalCountEl = document.getElementById('totalCount');
        if (totalCountEl) {
            totalCountEl.textContent = count;
        }
    },

    /**
     * 테이블 렌더링
     */
    renderTable() {
        const tbody = document.getElementById('regulationsList');
        if (!tbody) return;

        if (this.regulations.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center p-4">
                        검색 결과가 없습니다.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.regulations.map((reg, index) => `
            <tr data-id="${reg.wzruleseq}">
                <td>
                    <input type="checkbox" class="select-item" value="${reg.wzruleseq}">
                </td>
                <td>${index + 1}</td>
                <td>${reg.wzmgrdptnm || '-'}</td>
                <td>${reg.wzlkndname || '-'}</td>
                <td class="text-left">
                    <a href="#" onclick="RegulationManager.view(${reg.wzruleseq}); return false;">
                        ${reg.wzname}
                    </a>
                </td>
                <td>${reg.wzestabdate || '-'}</td>
                <td>${reg.wzlastrevdate || '-'}</td>
                <td>${reg.wzexecdate || '-'}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="RegulationManager.edit(${reg.wzruleseq})">
                        편집
                    </button>
                    <button class="btn btn-sm btn-info" onclick="RegulationManager.download(${reg.wzruleseq})">
                        다운로드
                    </button>
                </td>
            </tr>
        `).join('');
    },

    /**
     * 페이지네이션 렌더링
     */
    renderPagination(totalCount) {
        const totalPages = Math.ceil(totalCount / this.pageSize);
        const pagination = document.getElementById('pagination');
        if (!pagination) return;

        let html = '<ul class="pagination">';

        // 이전 페이지
        if (this.currentPage > 1) {
            html += `
                <li class="page-item">
                    <a class="page-link" href="#" onclick="RegulationManager.loadRegulations(${this.currentPage - 1}); return false;">
                        이전
                    </a>
                </li>
            `;
        }

        // 페이지 번호
        for (let i = Math.max(1, this.currentPage - 2); i <= Math.min(totalPages, this.currentPage + 2); i++) {
            html += `
                <li class="page-item ${i === this.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="RegulationManager.loadRegulations(${i}); return false;">
                        ${i}
                    </a>
                </li>
            `;
        }

        // 다음 페이지
        if (this.currentPage < totalPages) {
            html += `
                <li class="page-item">
                    <a class="page-link" href="#" onclick="RegulationManager.loadRegulations(${this.currentPage + 1}); return false;">
                        다음
                    </a>
                </li>
            `;
        }

        html += '</ul>';
        pagination.innerHTML = html;
    },

    /**
     * 검색
     */
    search() {
        this.filters.dept = document.getElementById('deptFilter')?.value || '';
        this.filters.category = document.getElementById('categoryFilter')?.value || '';
        this.filters.keyword = document.getElementById('searchInput')?.value || '';

        this.loadRegulations(1);
    },

    /**
     * 새 규정 추가
     */
    addNew() {
        window.location.href = '/regulations/new';
    },

    /**
     * 규정 편집
     */
    edit(ruleId) {
        window.location.href = `/regulations/edit/${ruleId}`;
    },

    /**
     * 규정 보기
     */
    view(ruleId) {
        window.location.href = `/regulations/view/${ruleId}`;
    },

    /**
     * 규정 상세 보기
     */
    viewDetail(ruleId) {
        window.location.href = `/regulations/view/${ruleId}`;
    },

    /**
     * 연혁 보기
     */
    viewHistory(ruleId) {
        window.location.href = `/regulations/history/${ruleId}`;
    },

    /**
     * 파일 다운로드
     */
    async download(ruleId) {
        try {
            const response = await fetch(`/api/v1/wz_rule/download/${ruleId}`, {
                method: 'GET',
            });

            if (!response.ok) throw new Error('Download failed');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;

            // 파일명 추출 (헤더에서 가져오거나 기본값 사용)
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = `regulation_${ruleId}.pdf`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                if (filenameMatch) filename = filenameMatch[1];
            }

            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

        } catch (error) {
            console.error('다운로드 실패:', error);
            CommonUtils.showAlert('파일 다운로드에 실패했습니다.', 'danger');
        }
    },

    /**
     * 엑셀 내보내기
     */
    async exportExcel() {
        CommonUtils.showLoading(true);

        try {
            const response = await fetch('/api/v1/wz_rule/export/excel', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.filters)
            });

            if (!response.ok) throw new Error('Export failed');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `regulations_${CommonUtils.formatDate(new Date(), 'YYYYMMDD')}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            CommonUtils.showAlert('엑셀 파일이 다운로드되었습니다.', 'success');

        } catch (error) {
            console.error('엑셀 내보내기 실패:', error);
            CommonUtils.showAlert('엑셀 내보내기에 실패했습니다.', 'danger');
        } finally {
            CommonUtils.showLoading(false);
        }
    }
};

// 전역 객체로 내보내기
window.RegulationManager = RegulationManager;