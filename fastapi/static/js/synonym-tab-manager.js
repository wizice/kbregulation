// synonym-tab-manager.js - 동의어사전 관리 탭

const SynonymTabManager = {
    synonyms: [],
    stats: { total: 0, active: 0, inactive: 0, totalSynonyms: 0 },
    currentSynonymId: null,
    synTags: [],
    initialized: false,

    init() {
        if (!this.initialized) {
            this.initialized = true;
        }
        this.loadStats();
        this.loadSynonyms();
    },

    async loadStats() {
        try {
            const response = await fetch('/api/synonyms/stats', { credentials: 'include' });
            if (!response.ok) throw new Error('통계 로드 실패');
            const data = await response.json();
            this.stats = {
                total: data.total_groups || 0,
                active: data.active_groups || 0,
                inactive: data.inactive_groups || 0,
                totalSynonyms: data.total_synonyms || 0
            };
            this.renderStats();
        } catch (error) {
            console.error('동의어 통계 로드 오류:', error);
        }
    },

    renderStats() {
        const container = document.getElementById('synStatsCards');
        if (!container) return;
        container.innerHTML = `
            <div style="flex:1;text-align:center;padding:15px;background:#f8f9fa;border-radius:8px;">
                <div style="font-size:24px;font-weight:bold;color:#60584C;">${this.stats.total}</div>
                <div style="font-size:12px;color:#6c757d;margin-top:4px;">전체 그룹</div>
            </div>
            <div style="flex:1;text-align:center;padding:15px;background:#f8f9fa;border-radius:8px;">
                <div style="font-size:24px;font-weight:bold;color:#28a745;">${this.stats.active}</div>
                <div style="font-size:12px;color:#6c757d;margin-top:4px;">활성 그룹</div>
            </div>
            <div style="flex:1;text-align:center;padding:15px;background:#f8f9fa;border-radius:8px;">
                <div style="font-size:24px;font-weight:bold;color:#dc3545;">${this.stats.inactive}</div>
                <div style="font-size:12px;color:#6c757d;margin-top:4px;">비활성 그룹</div>
            </div>
            <div style="flex:1;text-align:center;padding:15px;background:#f8f9fa;border-radius:8px;">
                <div style="font-size:24px;font-weight:bold;color:#17a2b8;">${this.stats.totalSynonyms}</div>
                <div style="font-size:12px;color:#6c757d;margin-top:4px;">전체 동의어</div>
            </div>
        `;
    },

    async loadSynonyms() {
        try {
            const search = (document.getElementById('synSearchInput') || {}).value || '';
            const activeFilter = (document.getElementById('synActiveFilter') || {}).value || '';
            let url = '/api/synonyms/?limit=500';
            if (search) url += `&search=${encodeURIComponent(search)}`;
            if (activeFilter !== '') url += `&is_active=${activeFilter}`;

            const response = await fetch(url, { credentials: 'include' });
            if (!response.ok) throw new Error('동의어 로드 실패');
            const data = await response.json();
            this.synonyms = Array.isArray(data) ? data : (data.synonyms || data.items || []);
            this.renderSynonyms();
        } catch (error) {
            console.error('동의어 로드 오류:', error);
            const list = document.getElementById('synSynonymsList');
            if (list) list.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#dc3545;padding:30px;">동의어를 불러오는데 실패했습니다.</td></tr>';
        }
    },

    renderSynonyms() {
        const tbody = document.getElementById('synSynonymsList');
        if (!tbody) return;

        if (this.synonyms.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#6c757d;padding:30px;">동의어 그룹이 없습니다.</td></tr>';
            return;
        }

        tbody.innerHTML = this.synonyms.map(s => {
            const words = s.synonyms || s.words || [];
            const displayWords = words.slice(0, 5);
            const moreCount = words.length - 5;
            const tags = displayWords.map(w => `<span style="display:inline-block;background:#e9ecef;padding:2px 8px;border-radius:12px;font-size:12px;margin:2px;">${w}</span>`).join('');
            const more = moreCount > 0 ? `<span style="color:#60584C;font-size:12px;margin-left:4px;">+${moreCount}</span>` : '';

            return `<tr>
                <td>${s.synonym_id || s.id}</td>
                <td>${s.group_name || s.name || '-'}</td>
                <td style="max-width:300px;">${tags}${more}</td>
                <td>${s.is_active !== false ? '<span class="status-badge status-active">활성</span>' : '<span class="status-badge status-draft">비활성</span>'}</td>
                <td>
                    <button class="action-btn btn-primary" onclick="SynonymTabManager.openEditModal(${s.synonym_id || s.id})">수정</button>
                    <button class="action-btn btn-danger" onclick="SynonymTabManager.deleteSynonym(${s.synonym_id || s.id}, '${(s.group_name || s.name || '').replace(/'/g, "\\'")}')">삭제</button>
                </td>
            </tr>`;
        }).join('');
    },

    searchSynonyms() {
        this.loadSynonyms();
    },

    openCreateModal() {
        this.currentSynonymId = null;
        this.synTags = [];
        document.getElementById('synModalTitle').textContent = '새 동의어 그룹';
        document.getElementById('synGroupName').value = '';
        document.getElementById('synTagInput').value = '';
        document.getElementById('synIsActive').checked = true;
        this.renderTags();
        document.getElementById('synSynonymModal').style.display = 'flex';
    },

    async openEditModal(id) {
        try {
            const response = await fetch(`/api/synonyms/${id}`, { credentials: 'include' });
            if (!response.ok) throw new Error('조회 실패');
            const synonym = await response.json();

            this.currentSynonymId = id;
            this.synTags = [...(synonym.synonyms || synonym.words || [])];
            document.getElementById('synModalTitle').textContent = '동의어 그룹 수정';
            document.getElementById('synGroupName').value = synonym.group_name || synonym.name || '';
            document.getElementById('synTagInput').value = '';
            document.getElementById('synIsActive').checked = synonym.is_active !== false;
            this.renderTags();
            document.getElementById('synSynonymModal').style.display = 'flex';
        } catch (error) {
            alert('동의어를 불러오는데 실패했습니다.');
        }
    },

    closeModal() {
        document.getElementById('synSynonymModal').style.display = 'none';
        this.currentSynonymId = null;
        this.synTags = [];
    },

    addSynonymTag() {
        const input = document.getElementById('synTagInput');
        const val = input.value.trim();
        if (!val) return;

        // 쉼표 구분 지원
        const words = val.split(',').map(w => w.trim()).filter(w => w && !this.synTags.includes(w));
        this.synTags.push(...words);
        input.value = '';
        this.renderTags();
    },

    removeSynonymTag(idx) {
        this.synTags.splice(idx, 1);
        this.renderTags();
    },

    renderTags() {
        const container = document.getElementById('synTagsContainer');
        if (!container) return;
        container.innerHTML = this.synTags.map((tag, i) =>
            `<span style="display:inline-flex;align-items:center;background:#FFBC00;color:white;padding:4px 10px;border-radius:16px;font-size:13px;margin:3px;">
                ${tag}
                <button type="button" onclick="SynonymTabManager.removeSynonymTag(${i})" style="background:none;border:none;color:white;margin-left:6px;cursor:pointer;font-size:14px;line-height:1;">×</button>
            </span>`
        ).join('');
    },

    async saveSynonym() {
        const mainWord = document.getElementById('synGroupName').value.trim();
        const isActive = document.getElementById('synIsActive').checked;

        if (!mainWord) { alert('그룹명을 입력해주세요.'); return; }
        if (this.synTags.length === 0) { alert('동의어를 1개 이상 추가해주세요.'); return; }

        const body = { group_name: mainWord, synonyms: this.synTags, is_active: isActive };
        const url = this.currentSynonymId ? `/api/synonyms/${this.currentSynonymId}` : '/api/synonyms/';
        const method = this.currentSynonymId ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                credentials: 'include'
            });
            if (!response.ok) { const e = await response.json(); throw new Error(e.detail || '저장 실패'); }
            this.closeModal();
            this.loadStats();
            this.loadSynonyms();
            this.showNotification(this.currentSynonymId ? '수정되었습니다.' : '등록되었습니다.', 'success');
        } catch (error) {
            alert('저장 실패: ' + error.message);
        }
    },

    async deleteSynonym(id, mainWord) {
        if (!confirm(`"${mainWord}"\n이 동의어 그룹을 삭제하시겠습니까?`)) return;
        const permanent = confirm('완전히 삭제하시겠습니까?\n(취소 시 비활성화됩니다)');

        try {
            const response = await fetch(`/api/synonyms/${id}?permanent=${permanent}`, { method: 'DELETE', credentials: 'include' });
            if (!response.ok) throw new Error('삭제 실패');
            this.loadStats();
            this.loadSynonyms();
            this.showNotification('삭제되었습니다.', 'success');
        } catch (error) {
            alert('삭제 실패');
        }
    },

    // 내보내기 모달
    openExportModal() {
        document.getElementById('synExportModal').style.display = 'flex';
        this.loadExportPreview('elasticsearch');
    },

    closeExportModal() {
        document.getElementById('synExportModal').style.display = 'none';
    },

    async loadExportPreview(format) {
        try {
            const response = await fetch(`/api/synonyms/export/json?format=${format}`, { credentials: 'include' });
            if (!response.ok) throw new Error('내보내기 실패');
            const data = await response.json();
            document.getElementById('synExportPreview').textContent = JSON.stringify(data, null, 2);
            document.getElementById('synExportFormat').value = format;
        } catch (error) {
            document.getElementById('synExportPreview').textContent = '내보내기 데이터를 불러올 수 없습니다.';
        }
    },

    async downloadJson() {
        const content = document.getElementById('synExportPreview').textContent;
        const blob = new Blob([content], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `synonyms_${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
    },

    copyToClipboard() {
        const content = document.getElementById('synExportPreview').textContent;
        navigator.clipboard.writeText(content).then(() => {
            this.showNotification('클립보드에 복사되었습니다.', 'success');
        }).catch(() => {
            // fallback
            const ta = document.createElement('textarea');
            ta.value = content;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            this.showNotification('클립보드에 복사되었습니다.', 'success');
        });
    },

    async saveToServer() {
        try {
            const format = document.getElementById('synExportFormat').value;
            const response = await fetch(`/api/synonyms/export/save?format=${format}`, {
                method: 'POST',
                credentials: 'include'
            });
            if (!response.ok) throw new Error('저장 실패');
            this.showNotification('서버에 저장되었습니다.', 'success');
        } catch (error) {
            alert('서버 저장 실패: ' + error.message);
        }
    },

    showNotification(message, type) {
        if (typeof SearchEngine !== 'undefined' && SearchEngine.showNotification) {
            SearchEngine.showNotification(message, type);
        } else { alert(message); }
    }
};
