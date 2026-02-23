/**
 * 유사어 관리 JavaScript
 *
 * 기능:
 * - 유사어 목록 조회
 * - 유사어 등록/수정/삭제
 * - JSON 내보내기
 * - 검색 및 필터링
 */

const SynonymManager = {
    // 상태
    synonyms: [],
    currentSynonyms: [], // 현재 편집 중인 유사어 목록
    editingId: null,

    // 초기화
    async init() {
        await this.loadStats();
        await this.loadSynonyms();
        this.setupEventListeners();
    },

    // 이벤트 리스너 설정
    setupEventListeners() {
        // 검색 입력
        document.getElementById('searchInput').addEventListener('input',
            this.debounce(() => this.loadSynonyms(), 300)
        );

        // 필터 변경
        document.getElementById('activeFilter').addEventListener('change',
            () => this.loadSynonyms()
        );

        // 유사어 입력 Enter 키
        document.getElementById('newSynonymInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.addSynonymTag();
            }
        });
    },

    // 디바운스 헬퍼
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // 통계 로드
    async loadStats() {
        try {
            const response = await fetch('/api/synonyms/stats');
            if (!response.ok) throw new Error('통계 조회 실패');

            const stats = await response.json();

            document.getElementById('statTotal').textContent = stats.total_groups || 0;
            document.getElementById('statActive').textContent = stats.active_groups || 0;
            document.getElementById('statInactive').textContent = stats.inactive_groups || 0;
            document.getElementById('statSynonyms').textContent = stats.total_synonyms || 0;
        } catch (error) {
            console.error('통계 로드 실패:', error);
        }
    },

    // 유사어 목록 로드
    async loadSynonyms() {
        const loadingState = document.getElementById('loadingState');
        const table = document.getElementById('synonymsTable');
        const emptyState = document.getElementById('emptyState');
        const tbody = document.getElementById('synonymsBody');

        loadingState.style.display = 'block';
        table.style.display = 'none';
        emptyState.style.display = 'none';

        try {
            const search = document.getElementById('searchInput').value;
            const activeFilter = document.getElementById('activeFilter').value;

            let url = '/api/synonyms/?limit=500';
            if (search) url += `&search=${encodeURIComponent(search)}`;
            if (activeFilter) url += `&is_active=${activeFilter}`;

            const response = await fetch(url);
            if (!response.ok) throw new Error('목록 조회 실패');

            this.synonyms = await response.json();

            loadingState.style.display = 'none';

            if (this.synonyms.length === 0) {
                emptyState.style.display = 'block';
                return;
            }

            table.style.display = 'table';
            tbody.innerHTML = this.synonyms.map(s => this.renderRow(s)).join('');

        } catch (error) {
            console.error('목록 로드 실패:', error);
            loadingState.innerHTML = `<p style="color: #f56565;">로드 실패: ${error.message}</p>`;
        }
    },

    // 테이블 행 렌더링
    renderRow(synonym) {
        const statusBadge = synonym.is_active
            ? '<span class="badge badge-active">활성</span>'
            : '<span class="badge badge-inactive">비활성</span>';

        const synonymTags = this.renderSynonymTags(synonym.synonyms);

        return `
            <tr>
                <td>${synonym.synonym_id}</td>
                <td><strong>${this.escapeHtml(synonym.group_name)}</strong></td>
                <td>${synonymTags}</td>
                <td><span class="badge badge-priority">${synonym.priority}</span></td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="SynonymManager.openEditModal(${synonym.synonym_id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="SynonymManager.deleteSynonym(${synonym.synonym_id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    },

    // 유사어 태그 렌더링
    renderSynonymTags(synonyms) {
        const maxShow = 5;
        const shown = synonyms.slice(0, maxShow);
        const remaining = synonyms.length - maxShow;

        let html = '<div class="synonym-tags">';
        html += shown.map(s => `<span class="synonym-tag">${this.escapeHtml(s)}</span>`).join('');

        if (remaining > 0) {
            html += `<span class="synonym-tag more" title="${synonyms.slice(maxShow).join(', ')}">+${remaining}개</span>`;
        }

        html += '</div>';
        return html;
    },

    // HTML 이스케이프
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // 등록 모달 열기
    openCreateModal() {
        this.editingId = null;
        this.currentSynonyms = [];

        document.getElementById('modalTitle').textContent = '새 유사어 그룹';
        document.getElementById('synonymForm').reset();
        document.getElementById('synonymId').value = '';
        document.getElementById('isActive').checked = true;
        document.getElementById('priority').value = '0';

        this.renderCurrentSynonyms();
        document.getElementById('synonymModal').classList.add('active');
    },

    // 수정 모달 열기
    async openEditModal(id) {
        try {
            const response = await fetch(`/api/synonyms/${id}`);
            if (!response.ok) throw new Error('조회 실패');

            const synonym = await response.json();

            this.editingId = id;
            this.currentSynonyms = [...synonym.synonyms];

            document.getElementById('modalTitle').textContent = '유사어 수정';
            document.getElementById('synonymId').value = id;
            document.getElementById('groupName').value = synonym.group_name;
            document.getElementById('description').value = synonym.description || '';
            document.getElementById('priority').value = synonym.priority;
            document.getElementById('isActive').checked = synonym.is_active;

            this.renderCurrentSynonyms();
            document.getElementById('synonymModal').classList.add('active');

        } catch (error) {
            this.showToast('유사어 조회 실패', 'error');
        }
    },

    // 모달 닫기
    closeModal() {
        document.getElementById('synonymModal').classList.remove('active');
        this.currentSynonyms = [];
        this.editingId = null;
    },

    // 유사어 태그 추가
    addSynonymTag() {
        const input = document.getElementById('newSynonymInput');
        const value = input.value.trim();

        if (!value) return;

        // 쉼표로 분리하여 여러 개 추가
        const newSynonyms = value.split(',')
            .map(s => s.trim())
            .filter(s => s && !this.currentSynonyms.includes(s));

        this.currentSynonyms.push(...newSynonyms);
        this.renderCurrentSynonyms();
        input.value = '';
        input.focus();
    },

    // 유사어 태그 제거
    removeSynonymTag(index) {
        this.currentSynonyms.splice(index, 1);
        this.renderCurrentSynonyms();
    },

    // 현재 유사어 태그 렌더링
    renderCurrentSynonyms() {
        const container = document.getElementById('synonymsTags');
        container.innerHTML = this.currentSynonyms.map((s, i) => `
            <span class="synonym-input-tag">
                ${this.escapeHtml(s)}
                <span class="remove-tag" onclick="SynonymManager.removeSynonymTag(${i})">&times;</span>
            </span>
        `).join('');
    },

    // 저장
    async saveSynonym(event) {
        event.preventDefault();

        if (this.currentSynonyms.length === 0) {
            this.showToast('유사어를 최소 1개 이상 입력해주세요', 'error');
            return;
        }

        const data = {
            group_name: document.getElementById('groupName').value.trim(),
            synonyms: this.currentSynonyms,
            description: document.getElementById('description').value.trim() || null,
            priority: parseInt(document.getElementById('priority').value) || 0,
            is_active: document.getElementById('isActive').checked
        };

        try {
            let url = '/api/synonyms/';
            let method = 'POST';

            if (this.editingId) {
                url = `/api/synonyms/${this.editingId}`;
                method = 'PUT';
            }

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '저장 실패');
            }

            this.showToast(this.editingId ? '유사어가 수정되었습니다' : '유사어가 등록되었습니다', 'success');
            this.closeModal();
            await this.loadSynonyms();
            await this.loadStats();

        } catch (error) {
            this.showToast(error.message, 'error');
        }
    },

    // 삭제
    async deleteSynonym(id) {
        if (!confirm('이 유사어 그룹을 삭제하시겠습니까?')) return;

        try {
            const response = await fetch(`/api/synonyms/${id}?permanent=true`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error('삭제 실패');

            this.showToast('유사어가 삭제되었습니다', 'success');
            await this.loadSynonyms();
            await this.loadStats();

        } catch (error) {
            this.showToast('삭제 실패: ' + error.message, 'error');
        }
    },

    // 내보내기 모달 열기
    openExportModal() {
        document.getElementById('exportModal').classList.add('active');
        this.loadExportPreview();
    },

    // 내보내기 모달 닫기
    closeExportModal() {
        document.getElementById('exportModal').classList.remove('active');
    },

    // 내보내기 미리보기 로드
    async loadExportPreview() {
        const format = document.getElementById('exportFormat').value;
        const preview = document.getElementById('exportPreview');
        const esConfig = document.getElementById('esConfigExample');

        try {
            const response = await fetch(`/api/synonyms/export/json?format=${format}`);
            if (!response.ok) throw new Error('내보내기 실패');

            const data = await response.json();

            // 미리보기
            const esConfigGroup = document.getElementById('esConfigGroup');
            if (format === 'elasticsearch') {
                preview.textContent = JSON.stringify(data.synonyms, null, 2);
                esConfigGroup.style.display = 'block';
                esConfig.textContent = JSON.stringify(data.config_example, null, 2);
            } else {
                preview.textContent = JSON.stringify(data.synonyms, null, 2);
                esConfigGroup.style.display = 'none';
            }

            // 저장용 데이터
            this.exportData = data.synonyms;

        } catch (error) {
            preview.textContent = '로드 실패: ' + error.message;
        }
    },

    // 클립보드 복사
    async copyToClipboard() {
        try {
            const text = document.getElementById('exportPreview').textContent;
            await navigator.clipboard.writeText(text);
            this.showToast('클립보드에 복사되었습니다', 'success');
        } catch (error) {
            this.showToast('복사 실패', 'error');
        }
    },

    // JSON 다운로드
    downloadJson() {
        const format = document.getElementById('exportFormat').value;
        const content = document.getElementById('exportPreview').textContent;
        const blob = new Blob([content], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `synonyms_${format}_${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.showToast('파일이 다운로드되었습니다', 'success');
    },

    // 서버에 저장
    async saveToServer() {
        const format = document.getElementById('exportFormat').value;

        try {
            const response = await fetch(`/api/synonyms/export/json?format=${format}&save_to_server=true`);
            if (!response.ok) throw new Error('저장 실패');

            const data = await response.json();

            if (data.saved_file) {
                this.showToast(`서버에 저장되었습니다: ${data.saved_file}`, 'success');
            } else {
                this.showToast('서버에 저장되었습니다', 'success');
            }
        } catch (error) {
            this.showToast('서버 저장 실패: ' + error.message, 'error');
        }
    },

    // 토스트 메시지
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
};

// 전역 함수 (HTML onclick에서 호출)
function openCreateModal() { SynonymManager.openCreateModal(); }
function closeModal() { SynonymManager.closeModal(); }
function saveSynonym(event) { SynonymManager.saveSynonym(event); }
function addSynonymTag() { SynonymManager.addSynonymTag(); }
function openExportModal() { SynonymManager.openExportModal(); }
function closeExportModal() { SynonymManager.closeExportModal(); }
function loadExportPreview() { SynonymManager.loadExportPreview(); }
function copyToClipboard() { SynonymManager.copyToClipboard(); }
function downloadJson() { SynonymManager.downloadJson(); }
function saveToServer() { SynonymManager.saveToServer(); }

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    SynonymManager.init();
});
