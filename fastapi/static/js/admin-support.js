/**
 * 지원 페이지 관리 JavaScript
 */

const SupportManager = {
    currentPage: null,
    removeAttachmentFlag: false,
    currentTab: 'notice',

    init() {
        console.log('[SupportManager] Initializing...');
        this.currentTab = 'notice';
        this.loadPages();
    },

    switchTab(tabName) {
        this.currentTab = tabName;

        // 탭 버튼 활성화 상태 변경
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // 페이지 로드
        this.loadPages();
    },

    async loadPages() {
        const pageType = this.currentTab;
        const isActive = document.getElementById('statusFilter').value;

        try {
            let url, pages;

            // 공지사항은 별도 API 사용
            if (pageType === 'notice') {
                url = '/api/notices/?';
                if (isActive) url += `is_active=${isActive}`;

                const response = await fetch(url, {
                    credentials: 'include'
                });

                if (!response.ok) {
                    throw new Error(`Failed to load notices: ${response.status}`);
                }

                const notices = await response.json();
                // 공지사항 데이터를 지원 페이지 형식으로 변환
                pages = notices.map(notice => ({
                    page_id: notice.notice_id,
                    page_type: 'notice',
                    title: notice.title,
                    order_no: 0,
                    view_count: notice.view_count,
                    is_active: notice.is_active,
                    attachment_name: notice.attachment_name
                }));
            } else {
                // 지원 페이지 API
                url = '/api/support/pages?';
                if (pageType) url += `page_type=${pageType}&`;
                if (isActive) url += `is_active=${isActive}`;

                const response = await fetch(url, {
                    credentials: 'include'
                });

                if (!response.ok) {
                    throw new Error(`Failed to load pages: ${response.status}`);
                }

                pages = await response.json();
            }

            this.renderPages(pages);

        } catch (error) {
            console.error('[SupportManager] Error loading pages:', error);
            alert('페이지 목록을 불러오는데 실패했습니다.');
        }
    },

    renderPages(pages) {
        const tbody = document.getElementById('pagesList');

        if (pages.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 40px; color: #999;">
                        등록된 페이지가 없습니다.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = pages.map(page => `
            <tr>
                <td>${page.page_id}</td>
                <td>
                    <span class="badge badge-${page.page_type}">
                        ${this.getPageTypeName(page.page_type)}
                    </span>
                </td>
                <td>
                    <span class="clickable" onclick="SupportManager.openEditModal(${page.page_id}, '${page.page_type}')">
                        ${page.title}
                    </span>
                    ${page.attachment_name ? `<br><small style="color: #666;"><i class="fas fa-paperclip"></i> ${page.attachment_name}</small>` : ''}
                </td>
                <td>${page.order_no}</td>
                <td>${page.view_count}</td>
                <td>
                    <span class="badge badge-${page.is_active ? 'active' : 'inactive'}">
                        ${page.is_active ? '활성' : '비활성'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="SupportManager.openEditModal(${page.page_id}, '${page.page_type}')" title="수정">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="SupportManager.deletePage(${page.page_id}, '${page.page_type}')" title="삭제">
                        <i class="fas fa-trash"></i>
                    </button>
                    ${page.attachment_path ? `
                        <button class="btn btn-sm btn-secondary" onclick="SupportManager.downloadAttachment(${page.page_id}, '${page.page_type}')" title="첨부파일">
                            <i class="fas fa-download"></i>
                        </button>
                    ` : ''}
                </td>
            </tr>
        `).join('');
    },

    getPageTypeName(type) {
        const types = {
            'notice': '공지사항',
            'procedure': '제개정절차',
            'usage': '사용방법',
            'faq': 'FAQ'
        };
        return types[type] || type;
    },

    openCreateModal() {
        this.currentPage = null;
        this.removeAttachmentFlag = false;

        document.getElementById('modalTitle').textContent = '새 페이지 추가';
        document.getElementById('pageForm').reset();
        document.getElementById('pageType').value = this.currentTab; // 현재 탭으로 자동 설정
        document.getElementById('isActive').checked = true;
        document.getElementById('isImportant').checked = false;
        document.getElementById('currentAttachment').style.display = 'none';

        document.getElementById('pageModal').classList.add('active');
    },

    async openEditModal(pageId, pageType) {
        try {
            let url, page;

            // 공지사항은 별도 API 사용
            if (pageType === 'notice') {
                url = `/api/notices/${pageId}`;
                const response = await fetch(url, {
                    credentials: 'include'
                });

                if (!response.ok) {
                    throw new Error('Failed to load notice');
                }

                const notice = await response.json();
                page = {
                    page_id: notice.notice_id,
                    page_type: 'notice',
                    title: notice.title,
                    content: notice.content,
                    order_no: 0,
                    is_active: notice.is_active,
                    is_important: notice.is_important,
                    attachment_name: notice.attachment_name
                };
            } else {
                url = `/api/support/pages/${pageId}`;
                const response = await fetch(url, {
                    credentials: 'include'
                });

                if (!response.ok) {
                    throw new Error('Failed to load page');
                }

                page = await response.json();
            }

            this.currentPage = page;
            this.removeAttachmentFlag = false;

            document.getElementById('modalTitle').textContent = '페이지 수정';
            document.getElementById('pageType').value = page.page_type;
            document.getElementById('pageTitle').value = page.title;
            document.getElementById('pageContent').value = page.content;
            document.getElementById('orderNo').value = page.order_no || 0;
            document.getElementById('isActive').checked = page.is_active;
            document.getElementById('isImportant').checked = page.is_important || false;

            // 첨부파일 표시
            if (page.attachment_name) {
                document.getElementById('attachmentName').textContent = page.attachment_name;
                document.getElementById('currentAttachment').style.display = 'block';
            } else {
                document.getElementById('currentAttachment').style.display = 'none';
            }

            document.getElementById('pageModal').classList.add('active');

        } catch (error) {
            console.error('[SupportManager] Error loading page:', error);
            alert('페이지 정보를 불러오는데 실패했습니다.');
        }
    },

    closeModal() {
        document.getElementById('pageModal').classList.remove('active');
        document.getElementById('pageForm').reset();
        this.currentPage = null;
        this.removeAttachmentFlag = false;
    },

    async savePage() {
        const pageType = document.getElementById('pageType').value;
        const title = document.getElementById('pageTitle').value.trim();
        const content = document.getElementById('pageContent').value.trim();
        const orderNo = document.getElementById('orderNo').value;
        const isActive = document.getElementById('isActive').checked;
        const isImportant = document.getElementById('isImportant').checked;
        const attachment = document.getElementById('attachment').files[0];

        if (!pageType || !title || !content) {
            alert('필수 항목을 입력해주세요.');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('title', title);
            formData.append('content', content);
            formData.append('is_active', isActive);
            formData.append('is_important', isImportant);

            if (pageType === 'notice') {
                // 공지사항 API 사용

                if (this.currentPage) {
                    // 수정
                    formData.append('remove_attachment', this.removeAttachmentFlag);
                    if (attachment) {
                        formData.append('attachment', attachment);
                    }

                    const response = await fetch(`/api/notices/${this.currentPage.page_id}`, {
                        method: 'PUT',
                        body: formData,
                        credentials: 'include'
                    });

                    if (!response.ok) {
                        throw new Error('Failed to update notice');
                    }

                    alert('공지사항이 수정되었습니다.');
                } else {
                    // 생성
                    if (attachment) {
                        formData.append('attachment', attachment);
                    }

                    const response = await fetch('/api/notices/', {
                        method: 'POST',
                        body: formData,
                        credentials: 'include'
                    });

                    if (!response.ok) {
                        throw new Error('Failed to create notice');
                    }

                    alert('공지사항이 생성되었습니다.');
                }
            } else {
                // 지원 페이지 API 사용
                formData.append('page_type', pageType);
                formData.append('order_no', orderNo);

                if (this.currentPage) {
                    // 수정
                    formData.append('remove_attachment', this.removeAttachmentFlag);
                    if (attachment) {
                        formData.append('attachment', attachment);
                    }

                    const response = await fetch(`/api/support/pages/${this.currentPage.page_id}`, {
                        method: 'PUT',
                        body: formData,
                        credentials: 'include'
                    });

                    if (!response.ok) {
                        throw new Error('Failed to update page');
                    }

                    alert('페이지가 수정되었습니다.');
                } else {
                    // 생성
                    if (attachment) {
                        formData.append('attachment', attachment);
                    }

                    const response = await fetch('/api/support/pages', {
                        method: 'POST',
                        body: formData,
                        credentials: 'include'
                    });

                    if (!response.ok) {
                        throw new Error('Failed to create page');
                    }

                    alert('페이지가 생성되었습니다.');
                }
            }

            this.closeModal();
            this.loadPages();

        } catch (error) {
            console.error('[SupportManager] Error saving page:', error);
            alert('페이지 저장에 실패했습니다.');
        }
    },

    async deletePage(pageId, pageType) {
        if (!confirm('정말 이 페이지를 삭제하시겠습니까?')) {
            return;
        }

        try {
            let url;
            if (pageType === 'notice') {
                url = `/api/notices/${pageId}`;
            } else {
                url = `/api/support/pages/${pageId}`;
            }

            const response = await fetch(url, {
                method: 'DELETE',
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Failed to delete page');
            }

            alert('페이지가 삭제되었습니다.');
            this.loadPages();

        } catch (error) {
            console.error('[SupportManager] Error deleting page:', error);
            alert('페이지 삭제에 실패했습니다.');
        }
    },

    removeAttachment() {
        if (confirm('첨부파일을 삭제하시겠습니까?')) {
            this.removeAttachmentFlag = true;
            document.getElementById('currentAttachment').style.display = 'none';
            document.getElementById('attachment').value = '';
        }
    },

    downloadAttachment(pageId, pageType) {
        let url;
        if (pageType === 'notice') {
            url = `/api/notices/attachments/${pageId}`;
        } else {
            url = `/api/support/attachments/${pageId}`;
        }
        window.open(url, '_blank');
    }
};
