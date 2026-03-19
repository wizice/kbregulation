// service-manager.js - 서비스 페이지 관리

const ServiceManager = {
    // 서비스 상태 데이터 (실 API에서 로드)
    serviceStatus: [],

    // 통계 데이터
    statsData: {
        noticeCount: 0,
        faqCount: 0,
        supportCount: 0,
        totalRegulations: 0
    },

    // 상태 로드
    async loadStatus() {
        await Promise.all([
            this.loadRegulations(),
            this.loadStatsFromAPI()
        ]);
        this.renderServiceStatus();
        this.renderStats();
    },

    // 규정 목록 로드
    async loadRegulations() {
        try {
            const response = await fetch('/api/v1/regulations/current', {
                credentials: 'include'
            });
            if (!response.ok) throw new Error('규정 목록 로드 실패');
            const data = await response.json();
            const regulations = data.regulations || data || [];
            this.serviceStatus = regulations.map(r => ({
                id: r.wzruleseq || r.id,
                title: r.wzrulename || r.name || r.title,
                status: (r.wzstatus === '현행' || r.status === 'active') ? 'published' : 'unpublished',
                views: r.view_count || 0,
                pubno: r.wzpubno || ''
            }));
            this.statsData.totalRegulations = this.serviceStatus.length;
        } catch (error) {
            console.error('규정 목록 로드 오류:', error);
            this.serviceStatus = [];
        }
    },

    // 실제 통계 데이터 로드
    async loadStatsFromAPI() {
        try {
            const [noticeRes, faqRes, supportRes] = await Promise.all([
                fetch('/api/notices/', { credentials: 'include' }).catch(() => null),
                fetch('/api/faqs/', { credentials: 'include' }).catch(() => null),
                fetch('/api/support/pages/public', { credentials: 'include' }).catch(() => null)
            ]);

            if (noticeRes && noticeRes.ok) {
                const notices = await noticeRes.json();
                this.statsData.noticeCount = Array.isArray(notices) ? notices.length : 0;
            }
            if (faqRes && faqRes.ok) {
                const faqs = await faqRes.json();
                this.statsData.faqCount = Array.isArray(faqs) ? faqs.length : 0;
            }
            if (supportRes && supportRes.ok) {
                const pages = await supportRes.json();
                this.statsData.supportCount = Array.isArray(pages) ? pages.length : 0;
            }
        } catch (error) {
            console.error('통계 로드 오류:', error);
        }
    },

    // 서비스 상태 렌더링
    renderServiceStatus() {
        const tbody = document.getElementById('serviceStatusList');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (this.serviceStatus.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#6c757d;padding:30px;">등록된 규정이 없습니다.</td></tr>';
            return;
        }

        this.serviceStatus.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item.pubno ? `[${item.pubno}] ` : ''}${item.title}</td>
                <td>${this.getStatusBadge(item.status)}</td>
                <td>${item.views.toLocaleString()}</td>
                <td>
                    <button class="action-btn btn-secondary" onclick="ServiceManager.preview(${item.id})">미리보기</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    },

    // 상태 배지 생성
    getStatusBadge(status) {
        const statusMap = {
            'published': { text: '게시중', class: 'status-active' },
            'unpublished': { text: '미게시', class: 'status-draft' },
            'scheduled': { text: '예약', class: 'status-review' }
        };

        const statusInfo = statusMap[status] || { text: status, class: 'status-draft' };
        return `<span class="status-badge ${statusInfo.class}">${statusInfo.text}</span>`;
    },

    // 통계 렌더링
    renderStats() {
        const chartDiv = document.getElementById('statsChart');
        if (!chartDiv) return;

        chartDiv.innerHTML = `
            <div style="background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h5 style="margin-bottom: 20px; color: #495057; font-weight: 600;">서비스 현황 요약</h5>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                    <div style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                        <div style="font-size: 28px; font-weight: bold; color: #60584C;">${this.statsData.totalRegulations}</div>
                        <div style="font-size: 13px; color: #6c757d; margin-top: 5px;">등록 규정</div>
                    </div>
                    <div style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                        <div style="font-size: 28px; font-weight: bold; color: #28a745;">${this.statsData.noticeCount}</div>
                        <div style="font-size: 13px; color: #6c757d; margin-top: 5px;">활성 공지사항</div>
                    </div>
                    <div style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                        <div style="font-size: 28px; font-weight: bold; color: #17a2b8;">${this.statsData.faqCount}</div>
                        <div style="font-size: 13px; color: #6c757d; margin-top: 5px;">활성 FAQ</div>
                    </div>
                    <div style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                        <div style="font-size: 28px; font-weight: bold; color: #ffc107;">${this.statsData.supportCount}</div>
                        <div style="font-size: 13px; color: #6c757d; margin-top: 5px;">지원 페이지</div>
                    </div>
                </div>
            </div>
        `;
    },

    // 미리보기
    preview(regulationId) {
        // 공개 사이트에서 해당 규정 페이지를 연다
        window.open(`/kbregulation_page.html?seq=${regulationId}`, '_blank');
    },

    // 알림 표시
    showNotification(message, type) {
        if (typeof SearchEngine !== 'undefined' && SearchEngine.showNotification) {
            SearchEngine.showNotification(message, type);
        } else {
            alert(message);
        }
    }
};
