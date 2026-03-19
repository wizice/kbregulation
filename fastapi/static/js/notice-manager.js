// notice-manager.js - 공지사항 관리 탭

const NoticeManager = {
    notices: [],
    currentNoticeId: null,
    selectedFile: null,
    initialized: false,

    init() {
        if (!this.initialized) {
            this.setupEvents();
            this.initialized = true;
        }
        this.loadNotices();
    },

    setupEvents() {
        const area = document.getElementById('ntcFileUploadArea');
        if (!area) return;
        area.addEventListener('dragover', (e) => { e.preventDefault(); area.classList.add('drag-over'); });
        area.addEventListener('dragleave', () => area.classList.remove('drag-over'));
        area.addEventListener('drop', (e) => {
            e.preventDefault();
            area.classList.remove('drag-over');
            if (e.dataTransfer.files.length > 0) {
                const input = document.getElementById('ntcFileInput');
                input.files = e.dataTransfer.files;
                this.handleFileSelect(input);
            }
        });
    },

    async loadNotices() {
        try {
            const response = await fetch('/api/notices/', { credentials: 'include' });
            if (!response.ok) throw new Error('공지사항 로드 실패');
            this.notices = await response.json();
            this.renderNotices();
        } catch (error) {
            console.error('공지사항 로드 오류:', error);
            const list = document.getElementById('ntcNoticesList');
            if (list) list.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#dc3545;padding:30px;">공지사항을 불러오는데 실패했습니다.</td></tr>';
        }
    },

    renderNotices() {
        const tbody = document.getElementById('ntcNoticesList');
        if (!tbody) return;

        const query = (document.getElementById('ntcSearchInput') || {}).value || '';
        const filtered = query
            ? this.notices.filter(n => n.title.toLowerCase().includes(query.toLowerCase()) || (n.content || '').toLowerCase().includes(query.toLowerCase()))
            : this.notices;

        if (filtered.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#6c757d;padding:30px;">공지사항이 없습니다.</td></tr>';
            return;
        }

        tbody.innerHTML = filtered.map(n => {
            const attachIcon = n.attachment_name ? ' <span title="첨부: ' + n.attachment_name + '" style="color:#60584C;">&#128206;</span>' : '';
            const date = n.created_at ? new Date(n.created_at).toLocaleDateString('ko-KR') : '-';
            return `<tr>
                <td>${n.notice_id}</td>
                <td>${n.title}${attachIcon}</td>
                <td>${n.created_by || '-'}</td>
                <td>${date}</td>
                <td>${n.view_count || 0}</td>
                <td>${n.is_important ? '<span class="status-badge status-review">중요</span>' : '-'}</td>
                <td>${n.is_active ? '<span class="status-badge status-active">활성</span>' : '<span class="status-badge status-draft">비활성</span>'}</td>
                <td>
                    <button class="action-btn btn-primary" onclick="NoticeManager.openEditModal(${n.notice_id})">수정</button>
                    <button class="action-btn btn-danger" onclick="NoticeManager.deleteNotice(${n.notice_id}, '${(n.title || '').replace(/'/g, "\\'")}')">삭제</button>
                </td>
            </tr>`;
        }).join('');
    },

    searchNotices() {
        this.renderNotices();
    },

    openCreateModal() {
        this.currentNoticeId = null;
        this.selectedFile = null;
        const modal = document.getElementById('noticeModal');
        document.getElementById('ntcModalTitle').textContent = '새 공지사항';
        document.getElementById('ntcTitle').value = '';
        document.getElementById('ntcContent').value = '';
        document.getElementById('ntcCreatedBy').value = window.__currentUser?.full_name || '관리자';
        document.getElementById('ntcIsImportant').checked = false;
        document.getElementById('ntcCurrentAttachment').style.display = 'none';
        this.clearFile();
        modal.style.display = 'flex';
    },

    async openEditModal(id) {
        try {
            const response = await fetch(`/api/notices/${id}`, { credentials: 'include' });
            if (!response.ok) throw new Error('조회 실패');
            const notice = await response.json();

            this.currentNoticeId = id;
            this.selectedFile = null;
            document.getElementById('ntcModalTitle').textContent = '공지사항 수정';
            document.getElementById('ntcTitle').value = notice.title;
            document.getElementById('ntcContent').value = notice.content || '';
            document.getElementById('ntcCreatedBy').value = notice.created_by || '관리자';
            document.getElementById('ntcIsImportant').checked = notice.is_important;

            if (notice.attachment_name) {
                document.getElementById('ntcCurrentFileName').textContent = notice.attachment_name;
                document.getElementById('ntcCurrentAttachment').style.display = 'block';
            } else {
                document.getElementById('ntcCurrentAttachment').style.display = 'none';
            }

            this.clearFile();
            document.getElementById('noticeModal').style.display = 'flex';
        } catch (error) {
            alert('공지사항을 불러오는데 실패했습니다.');
        }
    },

    closeModal() {
        document.getElementById('noticeModal').style.display = 'none';
        this.currentNoticeId = null;
        this.selectedFile = null;
    },

    async saveNotice() {
        const title = document.getElementById('ntcTitle').value.trim();
        const content = document.getElementById('ntcContent').value.trim();
        const createdBy = document.getElementById('ntcCreatedBy').value.trim();
        const isImportant = document.getElementById('ntcIsImportant').checked;

        if (!title || !content) { alert('제목과 내용을 입력해주세요.'); return; }

        const formData = new FormData();
        formData.append('title', title);
        formData.append('content', content);
        formData.append('is_important', isImportant);
        formData.append('created_by', createdBy);
        if (this.selectedFile) formData.append('file', this.selectedFile);

        const url = this.currentNoticeId ? `/api/notices/${this.currentNoticeId}` : '/api/notices/';
        const method = this.currentNoticeId ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, { method, body: formData, credentials: 'include' });
            if (!response.ok) { const e = await response.json(); throw new Error(e.detail || '저장 실패'); }
            this.closeModal();
            this.loadNotices();
            this.showNotification(this.currentNoticeId ? '수정되었습니다.' : '등록되었습니다.', 'success');
        } catch (error) {
            alert('저장 실패: ' + error.message);
        }
    },

    async deleteNotice(id, title) {
        if (!confirm(`"${title}"\n이 공지사항을 삭제하시겠습니까?`)) return;
        const permanent = confirm('완전히 삭제하시겠습니까?\n(취소 시 비활성화됩니다)');

        try {
            const response = await fetch(`/api/notices/${id}?permanent=${permanent}`, { method: 'DELETE', credentials: 'include' });
            if (!response.ok) throw new Error('삭제 실패');
            this.loadNotices();
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
        const info = document.getElementById('ntcFileInfo');
        const sizeStr = file.size < 1024 ? file.size + ' B' : (file.size / 1024).toFixed(1) + ' KB';
        info.innerHTML = `<strong>${file.name}</strong> (${sizeStr}) <button type="button" onclick="NoticeManager.clearFile()" style="float:right;background:none;border:none;color:#dc3545;cursor:pointer;">X</button>`;
        info.style.display = 'block';
    },

    clearFile() {
        this.selectedFile = null;
        const input = document.getElementById('ntcFileInput');
        if (input) input.value = '';
        const info = document.getElementById('ntcFileInfo');
        if (info) info.style.display = 'none';
    },

    showNotification(message, type) {
        if (typeof SearchEngine !== 'undefined' && SearchEngine.showNotification) {
            SearchEngine.showNotification(message, type);
        } else { alert(message); }
    }
};
