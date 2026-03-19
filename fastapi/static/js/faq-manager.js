// faq-manager.js - FAQ 관리 탭

const FAQManager = {
    faqs: [],
    currentFaqId: null,
    categories: ['일반', '검색', '즐겨찾기', '개정이력', '기타'],
    initialized: false,

    init() {
        if (!this.initialized) {
            this.initialized = true;
        }
        this.loadFAQs();
    },

    async loadFAQs() {
        try {
            const response = await fetch('/api/faqs/?limit=100', { credentials: 'include' });
            if (!response.ok) throw new Error('FAQ 로드 실패');
            this.faqs = await response.json();
            this.renderFAQs();
        } catch (error) {
            console.error('FAQ 로드 오류:', error);
            const list = document.getElementById('faqFaqsList');
            if (list) list.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#dc3545;padding:30px;">FAQ를 불러오는데 실패했습니다.</td></tr>';
        }
    },

    renderFAQs() {
        const tbody = document.getElementById('faqFaqsList');
        if (!tbody) return;

        const query = (document.getElementById('faqSearchInput') || {}).value || '';
        const catFilter = (document.getElementById('faqCategoryFilter') || {}).value || '';

        let filtered = this.faqs;
        if (query) {
            const q = query.toLowerCase();
            filtered = filtered.filter(f => f.question.toLowerCase().includes(q) || (f.answer || '').toLowerCase().includes(q));
        }
        if (catFilter) {
            filtered = filtered.filter(f => f.category === catFilter);
        }

        if (filtered.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#6c757d;padding:30px;">FAQ가 없습니다.</td></tr>';
            return;
        }

        tbody.innerHTML = filtered.map(f => {
            const answer = (f.answer || '').length > 50 ? f.answer.substring(0, 50) + '...' : (f.answer || '-');
            return `<tr>
                <td>${f.faq_id}</td>
                <td><span class="status-badge" style="background:#e9ecef;color:#495057;">${f.category || '일반'}</span></td>
                <td>${f.question}</td>
                <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${answer}</td>
                <td>${f.sort_order || 0}</td>
                <td>${f.is_active ? '<span class="status-badge status-active">활성</span>' : '<span class="status-badge status-draft">비활성</span>'}</td>
                <td>
                    <button class="action-btn btn-primary" onclick="FAQManager.openEditModal(${f.faq_id})">수정</button>
                    <button class="action-btn btn-danger" onclick="FAQManager.deleteFAQ(${f.faq_id}, '${(f.question || '').replace(/'/g, "\\'")}')">삭제</button>
                </td>
            </tr>`;
        }).join('');
    },

    searchFAQs() {
        this.renderFAQs();
    },

    openCreateModal() {
        this.currentFaqId = null;
        document.getElementById('faqModalTitle').textContent = '새 FAQ';
        document.getElementById('faqQuestion').value = '';
        document.getElementById('faqAnswer').value = '';
        document.getElementById('faqCategory').value = '일반';
        document.getElementById('faqSortOrder').value = '0';
        document.getElementById('faqIsActive').checked = true;
        document.getElementById('faqModal').style.display = 'flex';
    },

    async openEditModal(id) {
        try {
            const response = await fetch(`/api/faqs/${id}`, { credentials: 'include' });
            if (!response.ok) throw new Error('FAQ 조회 실패');
            const faq = await response.json();

            this.currentFaqId = id;
            document.getElementById('faqModalTitle').textContent = 'FAQ 수정';
            document.getElementById('faqQuestion').value = faq.question;
            document.getElementById('faqAnswer').value = faq.answer || '';
            document.getElementById('faqCategory').value = faq.category || '일반';
            document.getElementById('faqSortOrder').value = faq.sort_order || 0;
            document.getElementById('faqIsActive').checked = faq.is_active !== false;
            document.getElementById('faqModal').style.display = 'flex';
        } catch (error) {
            alert('FAQ를 불러오는데 실패했습니다.');
        }
    },

    closeModal() {
        document.getElementById('faqModal').style.display = 'none';
        this.currentFaqId = null;
    },

    async saveFAQ() {
        const question = document.getElementById('faqQuestion').value.trim();
        const answer = document.getElementById('faqAnswer').value.trim();
        const category = document.getElementById('faqCategory').value;
        const sortOrder = parseInt(document.getElementById('faqSortOrder').value) || 0;
        const isActive = document.getElementById('faqIsActive').checked;

        if (!question || !answer) { alert('질문과 답변을 입력해주세요.'); return; }

        const body = { question, answer, category, sort_order: sortOrder, is_active: isActive };
        const url = this.currentFaqId ? `/api/faqs/${this.currentFaqId}` : '/api/faqs/';
        const method = this.currentFaqId ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                credentials: 'include'
            });
            if (!response.ok) { const e = await response.json(); throw new Error(e.detail || '저장 실패'); }
            this.closeModal();
            this.loadFAQs();
            this.showNotification(this.currentFaqId ? '수정되었습니다.' : '등록되었습니다.', 'success');
        } catch (error) {
            alert('저장 실패: ' + error.message);
        }
    },

    async deleteFAQ(id, question) {
        if (!confirm(`"${question}"\n이 FAQ를 삭제하시겠습니까?`)) return;
        const permanent = confirm('완전히 삭제하시겠습니까?\n(취소 시 비활성화됩니다)');

        try {
            const response = await fetch(`/api/faqs/${id}?permanent=${permanent}`, { method: 'DELETE', credentials: 'include' });
            if (!response.ok) throw new Error('삭제 실패');
            this.loadFAQs();
            this.showNotification('삭제되었습니다.', 'success');
        } catch (error) {
            alert('삭제 실패');
        }
    },

    showNotification(message, type) {
        if (typeof SearchEngine !== 'undefined' && SearchEngine.showNotification) {
            SearchEngine.showNotification(message, type);
        } else { alert(message); }
    }
};
