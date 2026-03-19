// support-tab-manager.js - 지원페이지 관리 탭

const SupportTabManager = {
    pages: [],
    currentPageId: null,
    currentSubTab: 'procedure',
    selectedFile: null,
    initialized: false,

    init() {
        if (!this.initialized) {
            this.initialized = true;
        }
        this.loadPages();
    },

    switchSubTab(subTab) {
        this.currentSubTab = subTab;
        document.querySelectorAll('#supportTab .sup-sub-tab').forEach(btn => btn.classList.remove('active'));
        const activeBtn = document.querySelector(`#supportTab .sup-sub-tab[data-tab="${subTab}"]`);
        if (activeBtn) activeBtn.classList.add('active');
        this.loadPages();
    },

    async loadPages() {
        try {
            const response = await fetch(`/api/support/pages?page_type=${this.currentSubTab}`, { credentials: 'include' });
            if (!response.ok) throw new Error('지원페이지 로드 실패');
            this.pages = await response.json();
            this.renderPages();
        } catch (error) {
            console.error('지원페이지 로드 오류:', error);
            const list = document.getElementById('supPagesList');
            if (list) list.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#dc3545;padding:30px;">지원페이지를 불러오는데 실패했습니다.</td></tr>';
        }
    },

    renderPages() {
        const tbody = document.getElementById('supPagesList');
        if (!tbody) return;

        if (this.pages.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#6c757d;padding:30px;">등록된 페이지가 없습니다.</td></tr>';
            return;
        }

        tbody.innerHTML = this.pages.map(p => {
            const date = p.created_at ? new Date(p.created_at).toLocaleDateString('ko-KR') : '-';
            const attachIcon = p.attachment_name ? ' <span style="color:#60584C;">&#128206;</span>' : '';
            return `<tr>
                <td>${p.page_id || p.id}</td>
                <td>${p.title}${attachIcon}</td>
                <td>${p.sort_order || 0}</td>
                <td>${p.view_count || 0}</td>
                <td>${p.is_active !== false ? '<span class="status-badge status-active">활성</span>' : '<span class="status-badge status-draft">비활성</span>'}</td>
                <td>
                    <button class="action-btn btn-primary" onclick="SupportTabManager.openEditModal(${p.page_id || p.id})">수정</button>
                    <button class="action-btn btn-danger" onclick="SupportTabManager.deletePage(${p.page_id || p.id}, '${(p.title || '').replace(/'/g, "\\'")}')">삭제</button>
                </td>
            </tr>`;
        }).join('');
    },

    openCreateModal() {
        this.currentPageId = null;
        this.selectedFile = null;
        document.getElementById('supModalTitle').textContent = '새 지원페이지';
        document.getElementById('supTitle').value = '';
        document.getElementById('supContent').value = '';
        document.getElementById('supPageType').value = this.currentSubTab;
        document.getElementById('supSortOrder').value = '0';
        document.getElementById('supIsActive').checked = true;
        document.getElementById('supCurrentAttachment').style.display = 'none';
        this.clearFile();
        document.getElementById('supportModal').style.display = 'flex';
    },

    async openEditModal(id) {
        try {
            const response = await fetch(`/api/support/pages/${id}`, { credentials: 'include' });
            if (!response.ok) throw new Error('조회 실패');
            const page = await response.json();

            this.currentPageId = id;
            this.selectedFile = null;
            document.getElementById('supModalTitle').textContent = '지원페이지 수정';
            document.getElementById('supTitle').value = page.title || '';
            document.getElementById('supContent').value = page.content || '';
            document.getElementById('supPageType').value = page.page_type || this.currentSubTab;
            document.getElementById('supSortOrder').value = page.sort_order || 0;
            document.getElementById('supIsActive').checked = page.is_active !== false;

            if (page.attachment_name) {
                document.getElementById('supCurrentFileName').textContent = page.attachment_name;
                document.getElementById('supCurrentAttachment').style.display = 'block';
            } else {
                document.getElementById('supCurrentAttachment').style.display = 'none';
            }

            this.clearFile();
            document.getElementById('supportModal').style.display = 'flex';
        } catch (error) {
            alert('지원페이지를 불러오는데 실패했습니다.');
        }
    },

    closeModal() {
        document.getElementById('supportModal').style.display = 'none';
        this.currentPageId = null;
        this.selectedFile = null;
    },

    async savePage() {
        const title = document.getElementById('supTitle').value.trim();
        const content = document.getElementById('supContent').value.trim();
        const pageType = document.getElementById('supPageType').value;
        const sortOrder = parseInt(document.getElementById('supSortOrder').value) || 0;
        const isActive = document.getElementById('supIsActive').checked;

        if (!title) { alert('제목을 입력해주세요.'); return; }

        const formData = new FormData();
        formData.append('title', title);
        formData.append('content', content);
        formData.append('page_type', pageType);
        formData.append('sort_order', sortOrder);
        formData.append('is_active', isActive);
        if (this.selectedFile) formData.append('file', this.selectedFile);

        const url = this.currentPageId ? `/api/support/pages/${this.currentPageId}` : '/api/support/pages';
        const method = this.currentPageId ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, { method, body: formData, credentials: 'include' });
            if (!response.ok) { const e = await response.json(); throw new Error(e.detail || '저장 실패'); }
            this.closeModal();
            this.loadPages();
            this.showNotification(this.currentPageId ? '수정되었습니다.' : '등록되었습니다.', 'success');
        } catch (error) {
            alert('저장 실패: ' + error.message);
        }
    },

    async deletePage(id, title) {
        if (!confirm(`"${title}"\n이 페이지를 삭제하시겠습니까?`)) return;

        try {
            const response = await fetch(`/api/support/pages/${id}`, { method: 'DELETE', credentials: 'include' });
            if (!response.ok) throw new Error('삭제 실패');
            this.loadPages();
            this.showNotification('삭제되었습니다.', 'success');
        } catch (error) {
            alert('삭제 실패');
        }
    },

    handleFileSelect(input) {
        const file = input.files[0];
        if (!file) return;
        if (file.size > 10 * 1024 * 1024) { alert('파일 크기는 10MB를 초과할 수 없습니다.'); input.value = ''; return; }
        this.selectedFile = file;
        const info = document.getElementById('supFileInfo');
        const sizeStr = file.size < 1024 ? file.size + ' B' : (file.size / 1024).toFixed(1) + ' KB';
        info.innerHTML = `<strong>${file.name}</strong> (${sizeStr}) <button type="button" onclick="SupportTabManager.clearFile()" style="float:right;background:none;border:none;color:#dc3545;cursor:pointer;">X</button>`;
        info.style.display = 'block';
    },

    clearFile() {
        this.selectedFile = null;
        const input = document.getElementById('supFileInput');
        if (input) input.value = '';
        const info = document.getElementById('supFileInfo');
        if (info) info.style.display = 'none';
    },

    showNotification(message, type) {
        if (typeof SearchEngine !== 'undefined' && SearchEngine.showNotification) {
            SearchEngine.showNotification(message, type);
        } else { alert(message); }
    }
};
