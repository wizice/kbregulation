// service-manager.js - 서비스 페이지 관리

const ServiceManager = {
    // 서비스 상태 데이터
    serviceStatus: [
        { id: 1, title: '인사관리규정', status: 'published', views: 1234 },
        { id: 2, title: '재무관리규정', status: 'unpublished', views: 0 },
        { id: 3, title: '정보보안규정', status: 'published', views: 567 },
        { id: 4, title: '휴가관리규정', status: 'scheduled', views: 0 },
        { id: 5, title: '연명의료결정 규정', status: 'published', views: 892 }
    ],

    // 통계 데이터
    statsData: {
        daily: [120, 145, 189, 210, 198, 235, 267],
        weekly: [890, 1203, 1456, 1678],
        monthly: [4567, 5234, 5890, 6234]
    },

    // 상태 로드
    loadStatus() {
        this.renderServiceStatus();
        this.renderStats();
        this.loadRegulationOptions();
    },

    // 서비스 상태 렌더링
    renderServiceStatus() {
        const tbody = document.getElementById('serviceStatusList');
        if (!tbody) return;

        tbody.innerHTML = '';

        this.serviceStatus.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item.title}</td>
                <td>${this.getStatusBadge(item.status)}</td>
                <td>${item.views.toLocaleString()}</td>
                <td>
                    <button class="action-btn btn-secondary" onclick="ServiceManager.preview(${item.id})">미리보기</button>
                    ${item.status === 'published' 
                        ? `<button class="action-btn btn-warning" onclick="ServiceManager.unpublish(${item.id})">게시중단</button>`
                        : `<button class="action-btn btn-success" onclick="ServiceManager.publish(${item.id})">게시</button>`
                    }
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

    // 통계 렌더링 - 수정된 부분
    renderStats() {
        const chartDiv = document.getElementById('statsChart');
        if (!chartDiv) return;

        // 차트 스타일 개선
        chartDiv.innerHTML = `
            <div style="background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h5 style="margin-bottom: 20px; color: #495057; font-weight: 600;">일일 조회수 추이</h5>
                <div style="position: relative; height: 250px;">
                    <!-- Y축 레이블 -->
                    <div style="position: absolute; left: -40px; top: 0; height: 100%; display: flex; flex-direction: column-reverse; justify-content: space-between; font-size: 11px; color: #6c757d;">
                        <span>0</span>
                        <span>100</span>
                        <span>200</span>
                        <span>300</span>
                    </div>
                    
                    <!-- 차트 영역 -->
                    <div style="height: 100%; display: flex; align-items: flex-end; gap: 15px; border-bottom: 2px solid #dee2e6; padding: 0 10px;">
                        ${this.statsData.daily.map((value, index) => {
                            const height = (value / 300) * 100;
                            const days = ['월', '화', '수', '목', '금', '토', '일'];
                            return `
                                <div style="flex: 1; display: flex; flex-direction: column; align-items: center;">
                                    <span style="font-size: 12px; color: #495057; margin-bottom: 5px; font-weight: 600;">${value}</span>
                                    <div style="width: 100%; background: linear-gradient(to top, #667eea, #764ba2); 
                                                height: ${height}%; border-radius: 4px 4px 0 0;
                                                box-shadow: 0 -2px 8px rgba(102, 126, 234, 0.3);
                                                transition: all 0.3s ease;
                                                cursor: pointer;"
                                         onmouseover="this.style.transform='scale(1.05)'"
                                         onmouseout="this.style.transform='scale(1)'">
                                    </div>
                                    <span style="margin-top: 10px; font-size: 12px; color: #6c757d;">${days[index]}</span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                    
                    <!-- 그리드 라인 -->
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 100%; pointer-events: none;">
                        <div style="border-top: 1px dashed #e9ecef; position: absolute; top: 0; left: 0; right: 0;"></div>
                        <div style="border-top: 1px dashed #e9ecef; position: absolute; top: 25%; left: 0; right: 0;"></div>
                        <div style="border-top: 1px dashed #e9ecef; position: absolute; top: 50%; left: 0; right: 0;"></div>
                        <div style="border-top: 1px dashed #e9ecef; position: absolute; top: 75%; left: 0; right: 0;"></div>
                    </div>
                </div>
                
                <!-- 범례 -->
                <div style="margin-top: 20px; display: flex; justify-content: center; gap: 30px; font-size: 13px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 12px; height: 12px; background: #667eea; border-radius: 2px;"></div>
                        <span style="color: #6c757d;">이번 주</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 12px; height: 12px; background: #e9ecef; border-radius: 2px;"></div>
                        <span style="color: #6c757d;">지난 주</span>
                    </div>
                </div>
            </div>
        `;
    },

    // 규정 옵션 로드
    loadRegulationOptions() {
        const select = document.getElementById('qrRegulationSelect');
        if (!select) return;

        const regulations = this.serviceStatus.filter(item => item.status === 'published');
        
        select.innerHTML = '<option value="">규정 선택...</option>';
        regulations.forEach(reg => {
            const option = document.createElement('option');
            option.value = reg.id;
            option.textContent = reg.title;
            select.appendChild(option);
        });
    },

    // 미리보기
    preview(regulationId) {
        const regulation = this.serviceStatus.find(r => r.id === regulationId);
        if (!regulation) return;

        // 새 창에서 미리보기
        const previewWindow = window.open('', 'preview', 'width=1024,height=768');
        previewWindow.document.write(`
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>${regulation.title} - 미리보기</title>
                <style>
                    body {
                        font-family: 'Noto Sans KR', sans-serif;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 40px 20px;
                        line-height: 1.8;
                    }
                    h1 {
                        color: #333;
                        border-bottom: 3px solid #667eea;
                        padding-bottom: 10px;
                    }
                    .meta-info {
                        background: #f8f9fa;
                        padding: 15px;
                        border-radius: 8px;
                        margin: 20px 0;
                    }
                    .meta-info p {
                        margin: 5px 0;
                        color: #6c757d;
                    }
                    .content {
                        margin-top: 30px;
                    }
                    .article {
                        margin: 20px 0;
                        padding: 15px;
                        background: #fff;
                        border-left: 3px solid #667eea;
                    }
                    .footer {
                        margin-top: 50px;
                        padding-top: 20px;
                        border-top: 1px solid #dee2e6;
                        color: #6c757d;
                        font-size: 14px;
                    }
                </style>
            </head>
            <body>
                <h1>${regulation.title}</h1>
                <div class="meta-info">
                    <p><strong>상태:</strong> ${regulation.status === 'published' ? '시행중' : '미게시'}</p>
                    <p><strong>조회수:</strong> ${regulation.views.toLocaleString()}회</p>
                    <p><strong>최종 수정일:</strong> ${new Date().toLocaleDateString('ko-KR')}</p>
                </div>
                <div class="content">
                    <div class="article">
                        <h3>제1조 (목적)</h3>
                        <p>이 규정은 예시 내용입니다. 실제 내용은 데이터베이스에서 불러옵니다.</p>
                    </div>
                    <div class="article">
                        <h3>제2조 (적용범위)</h3>
                        <p>이 규정의 적용범위는 전 직원을 대상으로 합니다.</p>
                    </div>
                </div>
                <div class="footer">
                    <p>이 문서는 미리보기용입니다. 실제 서비스 페이지와 다를 수 있습니다.</p>
                    <button onclick="window.close()" style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer;">
                        닫기
                    </button>
                </div>
            </body>
            </html>
        `);
    },

    // 게시
    async publish(regulationId) {
        const regulation = this.serviceStatus.find(r => r.id === regulationId);
        if (!regulation) return;

        if (!confirm(`"${regulation.title}"을(를) 게시하시겠습니까?`)) return;

        try {
            // API 호출 시뮬레이션
            // const response = await fetch(`/api/service/publish/${regulationId}`, {
            //     method: 'POST'
            // });

            regulation.status = 'published';
            this.renderServiceStatus();
            this.showNotification(`"${regulation.title}"이(가) 게시되었습니다.`, 'success');
        } catch (error) {
            console.error('게시 오류:', error);
            this.showNotification('게시 중 오류가 발생했습니다.', 'error');
        }
    },

    // 게시 중단
    async unpublish(regulationId) {
        const regulation = this.serviceStatus.find(r => r.id === regulationId);
        if (!regulation) return;

        if (!confirm(`"${regulation.title}"의 게시를 중단하시겠습니까?`)) return;

        try {
            // API 호출 시뮬레이션
            // const response = await fetch(`/api/service/unpublish/${regulationId}`, {
            //     method: 'POST'
            // });

            regulation.status = 'unpublished';
            regulation.views = 0;
            this.renderServiceStatus();
            this.showNotification(`"${regulation.title}"의 게시가 중단되었습니다.`, 'warning');
        } catch (error) {
            console.error('게시 중단 오류:', error);
            this.showNotification('게시 중단 중 오류가 발생했습니다.', 'error');
        }
    },

    // QR코드 생성
    generateQR() {
        const select = document.getElementById('qrRegulationSelect');
        if (!select || !select.value) {
            alert('QR코드를 생성할 내규를 선택해주세요.');
            return;
        }

        const regulation = this.serviceStatus.find(r => r.id == select.value);
        if (!regulation) return;

        // QR코드 생성 (실제로는 QR 라이브러리 사용)
        const qrWindow = window.open('', 'qr', 'width=400,height=450');
        qrWindow.document.write(`
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <title>QR코드 - ${regulation.title}</title>
                <style>
                    body {
                        font-family: sans-serif;
                        text-align: center;
                        padding: 20px;
                    }
                    .qr-container {
                        background: white;
                        padding: 20px;
                        border-radius: 12px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        display: inline-block;
                    }
                    .qr-code {
                        width: 200px;
                        height: 200px;
                        margin: 20px auto;
                        background: #f0f0f0;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border: 2px solid #333;
                    }
                    .qr-info {
                        margin-top: 20px;
                        padding: 15px;
                        background: #f8f9fa;
                        border-radius: 8px;
                    }
                    button {
                        margin-top: 20px;
                        padding: 10px 20px;
                        background: #667eea;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        cursor: pointer;
                    }
                </style>
            </head>
            <body>
                <div class="qr-container">
                    <h2>${regulation.title}</h2>
                    <div class="qr-code">
                        <span style="font-size: 48px;">📱</span>
                    </div>
                    <div class="qr-info">
                        <p><strong>URL:</strong> https://regulations.company.com/${regulation.id}</p>
                        <p style="font-size: 12px; color: #6c757d;">
                            실제 구현시 QR 라이브러리를 사용하여 생성됩니다.
                        </p>
                    </div>
                    <button onclick="window.print()">인쇄</button>
                    <button onclick="window.close()">닫기</button>
                </div>
            </body>
            </html>
        `);
    },

    // 알림 표시
    showNotification(message, type) {
        if (typeof RegulationEditor !== 'undefined' && RegulationEditor.showNotification) {
            RegulationEditor.showNotification(message, type);
        } else {
            alert(message);
        }
    }
};
