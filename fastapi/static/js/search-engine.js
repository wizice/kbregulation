// search-engine.js - PostgreSQL FTS 검색 엔진 관리

const SearchEngine = {
    // 색인 상태 데이터
    indexStatus: {
        totalDocs: 0,
        indexedDocs: 0,
        pendingDocs: 0,
        errorDocs: 0,
        lastIndexed: null,
        indexPercentage: 0
    },

    // 검색 통계
    searchStats: {
        departmentStats: [],
        recentIndexed: []
    },

    // 부서 목록
    departments: [],

    // 초기화
    async init() {
        await this.loadStatus();
        await this.loadDepartments();
        await this.loadStats();
    },

    // 상태 로드
    async loadStatus() {
        try {
            const response = await fetch('/api/v1/search/status', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Failed to load index status');
            }

            const data = await response.json();
            if (data.success) {
                this.indexStatus = {
                    totalDocs: data.stats.total_documents,
                    indexedDocs: data.stats.indexed_documents,
                    pendingDocs: data.stats.pending_documents,
                    errorDocs: data.stats.error_documents,
                    lastIndexed: data.stats.last_indexed_at,
                    indexPercentage: data.stats.index_percentage
                };
                this.renderIndexStatus();
            }
        } catch (error) {
            console.error('Error loading index status:', error);
        }
    },

    // 통계 로드
    async loadStats() {
        try {
            const response = await fetch('/api/v1/search/stats', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Failed to load search stats');
            }

            const data = await response.json();
            if (data.success) {
                this.searchStats = {
                    departmentStats: data.department_stats || [],
                    recentIndexed: data.recent_indexed || []
                };
                this.renderSearchStats();
            }
        } catch (error) {
            console.error('Error loading search stats:', error);
        }
    },

    // 부서 목록 로드
    async loadDepartments() {
        try {
            const response = await fetch('/api/v1/dept/list', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Failed to load departments');
            }

            const data = await response.json();
            if (data.success) {
                this.departments = data.departments;
                this.renderDepartmentSelect();
            }
        } catch (error) {
            console.error('Error loading departments:', error);
        }
    },

    // 부서 선택 드롭다운 렌더링
    renderDepartmentSelect() {
        const selectElement = document.getElementById('searchDepartment');
        if (!selectElement) return;

        selectElement.innerHTML = '<option value="">전체 부서</option>';

        this.departments.forEach(dept => {
            const option = document.createElement('option');
            option.value = dept.name;  // API expects department name, not code
            option.textContent = dept.name;
            selectElement.appendChild(option);
        });
    },

    // 색인 상태 렌더링
    renderIndexStatus() {
        const statusDiv = document.getElementById('indexStatus');
        if (!statusDiv) return;

        const lastIndexedStr = this.indexStatus.lastIndexed
            ? new Date(this.indexStatus.lastIndexed).toLocaleString('ko-KR')
            : '없음';

        statusDiv.innerHTML = `
            <div>
                <span>전체 문서:</span>
                <strong>${this.indexStatus.totalDocs}개</strong>
            </div>
            <div>
                <span>색인된 문서:</span>
                <strong style="color: #28a745;">${this.indexStatus.indexedDocs}개</strong>
            </div>
            <div>
                <span>대기중:</span>
                <strong style="color: #ffc107;">${this.indexStatus.pendingDocs}개</strong>
            </div>
            <div>
                <span>오류:</span>
                <strong style="color: #dc3545;">${this.indexStatus.errorDocs}개</strong>
            </div>
            <div>
                <span>마지막 색인:</span>
                <strong>${lastIndexedStr}</strong>
            </div>
        `;

        // 진행률 바 업데이트
        const progressBar = document.getElementById('indexProgress');
        if (progressBar) {
            progressBar.style.width = `${this.indexStatus.indexPercentage}%`;
            progressBar.style.background = this.getProgressColor(this.indexStatus.indexPercentage);
        }

        // 진행률 텍스트 업데이트
        const progressText = document.querySelector('.progress-text');
        if (progressText) {
            progressText.textContent = `${this.indexStatus.indexPercentage}% 완료`;
        }
    },

    // 검색 통계 렌더링
    renderSearchStats() {
        // 부서별 통계
        const deptStatsDiv = document.getElementById('departmentStats');
        if (deptStatsDiv && this.searchStats.departmentStats.length > 0) {
            deptStatsDiv.innerHTML = `
                <h4>부서별 색인 문서</h4>
                <div style="max-height: 200px; overflow-y: auto;">
                    ${this.searchStats.departmentStats.map(dept => `
                        <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #e9ecef;">
                            <span>${dept.department}</span>
                            <strong>${dept.count}개</strong>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        // 최근 색인 문서
        const recentDiv = document.getElementById('recentIndexed');
        if (recentDiv && this.searchStats.recentIndexed.length > 0) {
            recentDiv.innerHTML = `
                <h4>최근 색인된 문서</h4>
                <div style="max-height: 200px; overflow-y: auto;">
                    ${this.searchStats.recentIndexed.map(doc => {
                        const date = new Date(doc.indexed_at).toLocaleString('ko-KR');
                        return `
                            <div style="padding: 8px 0; border-bottom: 1px solid #e9ecef;">
                                <div style="font-weight: 500;">${doc.title}</div>
                                <div style="font-size: 12px; color: #6c757d;">${date}</div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }
    },

    // 전체 재색인
    async reindexAll() {
        if (!confirm('전체 재색인을 시작하시겠습니까? 시간이 걸릴 수 있습니다.')) {
            return;
        }

        const button = event.target;
        button.disabled = true;
        button.textContent = '재색인 중...';

        try {
            const response = await fetch('/api/v1/search/reindex-all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Failed to reindex');
            }

            const data = await response.json();

            if (data.success) {
                this.showNotification(
                    `재색인 완료: ${data.indexed}개 성공, ${data.errors}개 실패 (전체 ${data.total}개)`,
                    data.errors > 0 ? 'warning' : 'success'
                );

                // 에러 상세 표시
                if (data.error_details && data.error_details.length > 0) {
                    console.error('재색인 오류 상세:', data.error_details);
                }

                // 상태 새로고침
                await this.loadStatus();
                await this.loadStats();
            } else {
                throw new Error(data.message || '재색인 실패');
            }
        } catch (error) {
            console.error('재색인 오류:', error);
            this.showNotification('재색인 중 오류가 발생했습니다.', 'error');
        } finally {
            button.disabled = false;
            button.textContent = '전체 재색인';
        }
    },

    // 검색 테스트
    async testSearch() {
        const query = document.getElementById('testSearchInput').value.trim();
        const department = document.getElementById('searchDepartment').value.trim();
        const classification = document.getElementById('searchClassification').value.trim();

        if (!query || query.length < 2) {
            alert('검색어를 2자 이상 입력하세요');
            return;
        }

        const resultsDiv = document.getElementById('searchTestResults');
        resultsDiv.innerHTML = '<div class="spinner"></div> 검색 중...';

        try {
            // URL 파라미터 구성
            const params = new URLSearchParams({
                q: query,
                limit: 20,
                offset: 0
            });

            if (department) {
                params.append('department', department);
            }

            if (classification) {
                params.append('classification', classification);
            }

            const response = await fetch(`/api/v1/search/query?${params}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Search failed');
            }

            const data = await response.json();

            if (data.success) {
                resultsDiv.innerHTML = data.results.length > 0
                    ? this.renderSearchResults(data.results, data.total)
                    : '<p style="text-align: center; color: #6c757d;">검색 결과가 없습니다.</p>';
            } else {
                throw new Error(data.message || '검색 실패');
            }

        } catch (error) {
            console.error('검색 오류:', error);
            resultsDiv.innerHTML = `<p style="color: #dc3545;">검색 중 오류가 발생했습니다: ${error.message}</p>`;
        }
    },

    // 검색 결과 렌더링
    renderSearchResults(results, total) {
        let html = `
            <div style="margin-bottom: 15px; font-weight: 500;">
                검색 결과: ${total}개 (${results.length}개 표시)
            </div>
        `;

        html += results.map(result => {
            const establishedDate = result.established_date || '-';
            const effectiveDate = result.effective_date || '-';
            const snippet = result.snippet ?
                result.snippet.replace(/(.{100})..+/, '$1...') : '';

            return `
                <div style="padding: 15px; background: #f8f9fa; border-radius: 4px; margin-bottom: 10px; border-left: 3px solid #007bff;">
                    <div style="margin-bottom: 8px;">
                        <strong style="font-size: 16px; color: #007bff;">
                            ${result.title}
                        </strong>
                        ${result.relevance > 1 ?
                            '<span style="margin-left: 10px; font-size: 12px; color: #28a745;">⭐ 높은 관련성</span>' :
                            ''}
                    </div>

                    ${snippet ? `
                        <p style="font-size: 13px; color: #495057; margin: 10px 0; line-height: 1.5;">
                            ${snippet}
                        </p>
                    ` : ''}

                    <div style="font-size: 12px; color: #6c757d; margin-top: 10px;">
                        <span>${result.department || '-'}</span>
                        <span style="margin: 0 10px;">|</span>
                        <span>분류: ${result.classification || '-'}</span>
                        <span style="margin: 0 10px;">|</span>
                        <span>공포일: ${establishedDate}</span>
                        <span style="margin: 0 10px;">|</span>
                        <span>시행일: ${effectiveDate}</span>
                    </div>

                    <div style="margin-top: 10px;">
                        <button
                            class="btn-small"
                            onclick="SearchEngine.viewRegulation(${result.rule_id})"
                            style="font-size: 12px; padding: 4px 12px;">
                            상세보기
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        return html;
    },

    // 규정 상세 보기
    async viewRegulation(ruleId) {
        try {
            // 규정 내용 가져오기
            const response = await fetch(`/api/v1/regulation/content/${ruleId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Failed to load regulation content');
            }

            const data = await response.json();

            // API 응답에서 실제 데이터 추출
            const ruleInfo = data.rule || {};
            const contentData = data.content || {};

            // 새 창에서 규정 내용 표시
            const viewWindow = window.open('', `view_regulation_${ruleId}`,
                'width=1200,height=800,menubar=no,toolbar=no,location=no,status=yes,resizable=yes,scrollbars=yes');

            // HTML 생성
            const html = `
                <!DOCTYPE html>
                <html lang="ko">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>${ruleInfo.name || '규정 상세보기'}</title>
                    <style>
                        body {
                            font-family: 'Malgun Gothic', sans-serif;
                            margin: 0;
                            padding: 20px;
                            background: #f5f5f5;
                        }
                        .container {
                            max-width: 1000px;
                            margin: 0 auto;
                            background: white;
                            padding: 30px;
                            border-radius: 8px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        }
                        .header {
                            border-bottom: 2px solid #007bff;
                            padding-bottom: 20px;
                            margin-bottom: 30px;
                        }
                        h1 {
                            color: #333;
                            margin: 0 0 10px 0;
                        }
                        .meta-info {
                            display: grid;
                            grid-template-columns: repeat(2, 1fr);
                            gap: 10px;
                            margin-top: 20px;
                            padding: 15px;
                            background: #f8f9fa;
                            border-radius: 4px;
                        }
                        .meta-item {
                            display: flex;
                        }
                        .meta-label {
                            font-weight: bold;
                            color: #666;
                            min-width: 100px;
                        }
                        .content-section {
                            margin-top: 30px;
                        }
                        .content-section h2 {
                            color: #007bff;
                            border-bottom: 1px solid #dee2e6;
                            padding-bottom: 10px;
                        }
                        .article {
                            margin: 20px 0;
                            padding: 15px;
                            background: #f8f9fa;
                            border-left: 3px solid #007bff;
                        }
                        .article-title {
                            font-weight: bold;
                            color: #333;
                            margin-bottom: 10px;
                        }
                        .article-content {
                            color: #666;
                            line-height: 1.6;
                        }
                        .close-btn {
                            position: fixed;
                            top: 20px;
                            right: 20px;
                            padding: 10px 20px;
                            background: #6c757d;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            cursor: pointer;
                        }
                        .close-btn:hover {
                            background: #5a6268;
                        }
                        pre {
                            white-space: pre-wrap;
                            word-wrap: break-word;
                            font-family: inherit;
                        }
                    </style>
                </head>
                <body>
                    <button class="close-btn" onclick="window.close()">✕ 닫기</button>
                    <div class="container">
                        <div class="header">
                            <h1>${ruleInfo.name || '제목 없음'}</h1>
                            <div class="meta-info">
                                <div class="meta-item">
                                    <span class="meta-label">분류번호:</span>
                                    <span>${ruleInfo.publication_no || '-'}</span>
                                </div>
                                <div class="meta-item">
                                    <span class="meta-label">소관부서:</span>
                                    <span>${ruleInfo.department || '-'}</span>
                                </div>
                                <div class="meta-item">
                                    <span class="meta-label">공포일자:</span>
                                    <span>${ruleInfo.established_date || '-'}</span>
                                </div>
                                <div class="meta-item">
                                    <span class="meta-label">최종개정일:</span>
                                    <span>${ruleInfo.last_revised_date || '-'}</span>
                                </div>
                            </div>
                        </div>

                        <div class="content-section">
                            ${this.formatRegulationContent(contentData)}
                        </div>
                    </div>
                </body>
                </html>
            `;

            viewWindow.document.write(html);
            viewWindow.document.close();

        } catch (error) {
            console.error('Error loading regulation:', error);
            alert('내규를 불러오는 중 오류가 발생했습니다.');
        }
    },

    // 규정 내용 포맷팅
    formatRegulationContent(contentData) {
        // contentData가 없는 경우
        if (!contentData) {
            return '<div class="article">내용이 없습니다.</div>';
        }

        // full_text가 있는 경우 (우선순위 1)
        if (contentData.full_text) {
            // full_text는 이미 HTML 형식이므로 그대로 반환
            return `<div style="line-height: 1.8; font-size: 14px;">${contentData.full_text}</div>`;
        }

        // full_text가 없는 경우 대체 내용 표시
        let html = '<div class="article">';

        // document_info와 articles는 표시하지 않음
        // 다른 필드가 있다면 표시
        for (const [key, value] of Object.entries(contentData)) {
            if (key !== 'document_info' && key !== 'articles' && value) {
                if (typeof value === 'string') {
                    html += `<div>${value}</div>`;
                }
            }
        }

        if (html === '<div class="article">') {
            html += '규정 내용을 불러올 수 없습니다.';
        }

        html += '</div>';
        return html;
    },

    // 진행률에 따른 색상
    getProgressColor(percentage) {
        if (percentage >= 80) return '#28a745';
        if (percentage >= 50) return '#ffc107';
        return '#dc3545';
    },

    // 알림 표시
    showNotification(message, type) {
        // 알림 컨테이너가 없으면 생성
        let container = document.getElementById('notificationContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notificationContainer';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
            `;
            document.body.appendChild(container);
        }

        // 알림 엘리먼트 생성
        const notification = document.createElement('div');
        notification.style.cssText = `
            padding: 15px 20px;
            margin-bottom: 10px;
            border-radius: 4px;
            color: white;
            font-size: 14px;
            min-width: 300px;
            animation: slideIn 0.3s ease-out;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        `;

        // 타입별 색상
        switch(type) {
            case 'success':
                notification.style.background = '#28a745';
                break;
            case 'warning':
                notification.style.background = '#ffc107';
                notification.style.color = '#212529';
                break;
            case 'error':
                notification.style.background = '#dc3545';
                break;
            default:
                notification.style.background = '#17a2b8';
        }

        notification.textContent = message;
        container.appendChild(notification);

        // 5초 후 자동 제거
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                container.removeChild(notification);
            }, 300);
        }, 5000);
    }
};

// CSS 애니메이션 추가
(function() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }

    .spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid #f3f3f3;
        border-top: 3px solid #007bff;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .btn-small {
        background: #007bff;
        color: white;
        border: none;
        border-radius: 3px;
        cursor: pointer;
        transition: background 0.2s;
    }

    .btn-small:hover {
        background: #0056b3;
    }
`;
    document.head.appendChild(style);
})();