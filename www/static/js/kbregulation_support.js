/**
 * KB신용정보 내규 시스템 - 도움말/지원 모듈
 * @module kbregulation_support
 */

import { AppState, showToast } from './kbregulation_common.js';

// ============================================
// 지원 페이지 상태
// ============================================

// 공지사항
let currentNoticesData = [];
let filteredNoticesData = [];
let currentNoticesPage = 1;
let noticesPerPage = 10;

// 제개정 절차
let currentProceduresData = [];
let filteredProceduresData = [];
let currentProceduresPage = 1;
let proceduresPerPage = 10;

// 사용방법
let currentUsageData = [];
let filteredUsageData = [];
let currentUsagePage = 1;
let usagePerPage = 10;

// FAQ
let currentFAQData = [];
let filteredFAQData = [];
let currentFAQPage = 1;
let faqPerPage = 10;

// ============================================
// 도움말 메인 페이지
// ============================================

/**
 * 도움말 메인 페이지 표시
 */
export function displaySupportContent() {
    const contentBody = document.getElementById('contentBody');
    if (!contentBody) return;

    const html = `
        <div class="support-page">
            <div class="support-header">
                <h2><i class="fas fa-question-circle"></i> 도움말</h2>
            </div>
            <div class="support-tabs">
                <button class="support-tab active" data-tab="notices" onclick="switchSupportTab('notices', this)">
                    <i class="fas fa-bullhorn"></i> 공지사항
                </button>
                <button class="support-tab" data-tab="procedures" onclick="switchSupportTab('procedures', this)">
                    <i class="fas fa-clipboard-list"></i> 내규 제·개정 절차
                </button>
                <button class="support-tab" data-tab="usage" onclick="switchSupportTab('usage', this)">
                    <i class="fas fa-book"></i> 사용방법
                </button>
                <button class="support-tab" data-tab="faq" onclick="switchSupportTab('faq', this)">
                    <i class="fas fa-comments"></i> FAQ
                </button>
            </div>
            <div class="support-content" id="supportContentArea">
                <!-- 탭 컨텐츠가 여기에 로드됨 -->
            </div>
        </div>
    `;

    contentBody.innerHTML = html;

    // 기본 탭 로드
    loadNoticesTab();
}

/**
 * 지원 탭 전환
 */
export function switchSupportTab(tabName, clickedTab) {
    // 모든 탭 비활성화
    document.querySelectorAll('.support-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // 클릭한 탭 활성화
    if (clickedTab) {
        clickedTab.classList.add('active');
    }

    // 탭별 콘텐츠 로드
    switch (tabName) {
        case 'notices':
            loadNoticesTab();
            break;
        case 'procedures':
            loadProceduresTab();
            break;
        case 'usage':
            loadUsageTab();
            break;
        case 'faq':
            loadFAQTab();
            break;
    }
}

// ============================================
// 공지사항 탭
// ============================================

/**
 * 공지사항 탭 로드
 */
async function loadNoticesTab() {
    const contentArea = document.getElementById('supportContentArea');

    contentArea.innerHTML = `
        <div class="loading-spinner">
            <i class="fas fa-spinner fa-spin"></i> 공지사항을 불러오는 중...
        </div>
    `;

    try {
        const response = await fetch('/api/notices/?is_active=true');
        const data = await response.json();

        if (data) {
            currentNoticesData = Array.isArray(data) ? data : (data.data || []);
            filteredNoticesData = [...currentNoticesData];
            currentNoticesPage = 1;
            renderNoticesContent();
        } else {
            contentArea.innerHTML = '<div class="error-message">공지사항을 불러오는데 실패했습니다.</div>';
        }
    } catch (error) {
        console.error('공지사항 로드 오류:', error);
        contentArea.innerHTML = '<div class="error-message">공지사항을 불러오는데 실패했습니다.</div>';
    }
}

/**
 * 공지사항 콘텐츠 렌더링
 */
function renderNoticesContent() {
    const contentArea = document.getElementById('supportContentArea');

    const totalPages = Math.ceil(filteredNoticesData.length / noticesPerPage);
    const startIdx = (currentNoticesPage - 1) * noticesPerPage;
    const pageData = filteredNoticesData.slice(startIdx, startIdx + noticesPerPage);

    let html = `
        <div class="support-list-header">
            <div class="support-search">
                <input type="text" id="noticesSearchInput" placeholder="공지사항 검색..."
                       onkeyup="filterNotices(this.value)">
                <i class="fas fa-search"></i>
            </div>
            <div class="support-count">총 ${filteredNoticesData.length}건</div>
        </div>
        <div class="support-list">
    `;

    if (pageData.length === 0) {
        html += `
            <div class="support-empty">
                <i class="fas fa-inbox"></i>
                <p>등록된 공지사항이 없습니다.</p>
            </div>
        `;
    } else {
        pageData.forEach(notice => {
            const isImportant = notice.is_important || notice.isImportant;
            html += `
                <div class="support-item ${isImportant ? 'important' : ''}" onclick="openNoticeDetail(${notice.id})">
                    <div class="support-item-header">
                        ${isImportant ? '<span class="badge important">중요</span>' : ''}
                        <span class="support-item-title">${notice.title}</span>
                    </div>
                    <div class="support-item-meta">
                        <span><i class="fas fa-calendar"></i> ${formatSupportDate(notice.created_at)}</span>
                        <span><i class="fas fa-eye"></i> ${notice.view_count || 0}</span>
                    </div>
                </div>
            `;
        });
    }

    html += '</div>';
    html += renderPagination(currentNoticesPage, totalPages, 'changeNoticesPage');

    contentArea.innerHTML = html;
}

/**
 * 공지사항 필터링
 */
export function filterNotices(searchTerm) {
    const searchLower = searchTerm.toLowerCase();

    if (!searchTerm || searchTerm.trim() === '') {
        filteredNoticesData = [...currentNoticesData];
    } else {
        filteredNoticesData = currentNoticesData.filter(notice =>
            notice.title.toLowerCase().includes(searchLower) ||
            (notice.content && notice.content.toLowerCase().includes(searchLower))
        );
    }

    currentNoticesPage = 1;
    renderNoticesContent();
}

/**
 * 공지사항 페이지 변경
 */
export function changeNoticesPage(page) {
    currentNoticesPage = page;
    renderNoticesContent();
}

/**
 * 공지사항 상세 열기
 */
export async function openNoticeDetail(id) {
    try {
        const response = await fetch(`/api/notices/${id}`);
        const data = await response.json();

        if (data) {
            showNoticeModal(data);
        } else {
            showToast('공지사항을 불러오는데 실패했습니다.', 'error');
        }
    } catch (error) {
        console.error('공지사항 상세 오류:', error);
        showToast('공지사항을 불러오는데 실패했습니다.', 'error');
    }
}

/**
 * 공지사항 모달 표시
 */
function showNoticeModal(notice) {
    let modal = document.getElementById('noticeModal');

    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'noticeModal';
        modal.className = 'support-modal';
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <div class="support-modal-content">
            <div class="support-modal-header">
                <h3>${notice.title}</h3>
                <button class="close-btn" onclick="closeNoticeModal()">&times;</button>
            </div>
            <div class="support-modal-meta">
                <span><i class="fas fa-calendar"></i> ${formatSupportDate(notice.created_at)}</span>
                <span><i class="fas fa-eye"></i> ${notice.view_count || 0}</span>
            </div>
            <div class="support-modal-body">
                ${notice.content || '내용이 없습니다.'}
            </div>
        </div>
    `;

    modal.classList.add('active');
}

/**
 * 공지사항 모달 닫기
 */
export function closeNoticeModal() {
    const modal = document.getElementById('noticeModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// ============================================
// 제·개정 절차 탭
// ============================================

/**
 * 제·개정 절차 탭 로드
 */
async function loadProceduresTab() {
    const contentArea = document.getElementById('supportContentArea');

    contentArea.innerHTML = `
        <div class="loading-spinner">
            <i class="fas fa-spinner fa-spin"></i> 제·개정 절차를 불러오는 중...
        </div>
    `;

    try {
        const response = await fetch('/api/support/pages/public?page_type=procedure');
        const data = await response.json();

        if (data) {
            const pages = Array.isArray(data) ? data : (data.data || []);
            currentProceduresData = pages.map(page => ({
                id: page.page_id,
                title: page.title,
                content: page.content,
                created_at: page.created_at,
                attachment_path: page.attachment_name ? `/api/support/attachments/${page.page_id}` : null,
                attachment_name: page.attachment_name
            }));
            filteredProceduresData = [...currentProceduresData];
            currentProceduresPage = 1;
            renderProceduresContent();
        } else {
            contentArea.innerHTML = '<div class="error-message">제·개정 절차를 불러오는데 실패했습니다.</div>';
        }
    } catch (error) {
        console.error('제·개정 절차 로드 오류:', error);
        contentArea.innerHTML = '<div class="error-message">제·개정 절차를 불러오는데 실패했습니다.</div>';
    }
}

/**
 * 제·개정 절차 콘텐츠 렌더링
 */
function renderProceduresContent() {
    const contentArea = document.getElementById('supportContentArea');

    const totalPages = Math.ceil(filteredProceduresData.length / proceduresPerPage);
    const startIdx = (currentProceduresPage - 1) * proceduresPerPage;
    const pageData = filteredProceduresData.slice(startIdx, startIdx + proceduresPerPage);

    let html = `
        <div class="support-list-header">
            <div class="support-search">
                <input type="text" id="proceduresSearchInput" placeholder="절차 검색..."
                       onkeyup="filterProcedures(this.value)">
                <i class="fas fa-search"></i>
            </div>
            <div class="support-count">총 ${filteredProceduresData.length}건</div>
        </div>
        <div class="support-list procedures-list">
    `;

    if (pageData.length === 0) {
        html += `
            <div class="support-empty">
                <i class="fas fa-clipboard-list"></i>
                <p>등록된 절차가 없습니다.</p>
            </div>
        `;
    } else {
        pageData.forEach((procedure, index) => {
            html += `
                <div class="procedure-item">
                    <div class="procedure-step">${startIdx + index + 1}</div>
                    <div class="procedure-content">
                        <div class="procedure-title">${procedure.title}</div>
                        <div class="procedure-desc">${procedure.description || ''}</div>
                    </div>
                </div>
            `;
        });
    }

    html += '</div>';
    html += renderPagination(currentProceduresPage, totalPages, 'changeProceduresPage');

    contentArea.innerHTML = html;
}

/**
 * 제·개정 절차 필터링
 */
export function filterProcedures(searchTerm) {
    const searchLower = searchTerm.toLowerCase();

    if (!searchTerm || searchTerm.trim() === '') {
        filteredProceduresData = [...currentProceduresData];
    } else {
        filteredProceduresData = currentProceduresData.filter(proc =>
            proc.title.toLowerCase().includes(searchLower) ||
            (proc.description && proc.description.toLowerCase().includes(searchLower))
        );
    }

    currentProceduresPage = 1;
    renderProceduresContent();
}

/**
 * 제·개정 절차 페이지 변경
 */
export function changeProceduresPage(page) {
    currentProceduresPage = page;
    renderProceduresContent();
}

// ============================================
// 사용방법 탭
// ============================================

/**
 * 사용방법 탭 로드
 */
async function loadUsageTab() {
    const contentArea = document.getElementById('supportContentArea');

    contentArea.innerHTML = `
        <div class="loading-spinner">
            <i class="fas fa-spinner fa-spin"></i> 사용방법을 불러오는 중...
        </div>
    `;

    try {
        const response = await fetch('/api/support/pages/public?page_type=usage');
        const data = await response.json();

        if (data) {
            const pages = Array.isArray(data) ? data : (data.data || []);
            currentUsageData = pages.map(page => ({
                id: page.page_id,
                title: page.title,
                content: page.content,
                created_at: page.created_at,
                attachment_path: page.attachment_name ? `/api/support/attachments/${page.page_id}` : null,
                attachment_name: page.attachment_name
            }));
            filteredUsageData = [...currentUsageData];
            currentUsagePage = 1;
            renderUsageContent();
        } else {
            contentArea.innerHTML = '<div class="error-message">사용방법을 불러오는데 실패했습니다.</div>';
        }
    } catch (error) {
        console.error('사용방법 로드 오류:', error);
        contentArea.innerHTML = '<div class="error-message">사용방법을 불러오는데 실패했습니다.</div>';
    }
}

/**
 * 사용방법 콘텐츠 렌더링
 */
function renderUsageContent() {
    const contentArea = document.getElementById('supportContentArea');

    const totalPages = Math.ceil(filteredUsageData.length / usagePerPage);
    const startIdx = (currentUsagePage - 1) * usagePerPage;
    const pageData = filteredUsageData.slice(startIdx, startIdx + usagePerPage);

    let html = `
        <div class="support-list-header">
            <div class="support-search">
                <input type="text" id="usageSearchInput" placeholder="사용방법 검색..."
                       onkeyup="filterUsage(this.value)">
                <i class="fas fa-search"></i>
            </div>
            <div class="support-count">총 ${filteredUsageData.length}건</div>
        </div>
        <div class="support-list usage-list">
    `;

    if (pageData.length === 0) {
        html += `
            <div class="support-empty">
                <i class="fas fa-book"></i>
                <p>등록된 사용방법이 없습니다.</p>
            </div>
        `;
    } else {
        pageData.forEach(usage => {
            html += `
                <div class="usage-item" onclick="toggleUsageDetail(this)">
                    <div class="usage-header">
                        <span class="usage-title">${usage.title}</span>
                        <i class="fas fa-chevron-down"></i>
                    </div>
                    <div class="usage-content" style="display: none;">
                        ${usage.content || '내용이 없습니다.'}
                    </div>
                </div>
            `;
        });
    }

    html += '</div>';
    html += renderPagination(currentUsagePage, totalPages, 'changeUsagePage');

    contentArea.innerHTML = html;
}

/**
 * 사용방법 필터링
 */
export function filterUsage(searchTerm) {
    const searchLower = searchTerm.toLowerCase();

    if (!searchTerm || searchTerm.trim() === '') {
        filteredUsageData = [...currentUsageData];
    } else {
        filteredUsageData = currentUsageData.filter(usage =>
            usage.title.toLowerCase().includes(searchLower) ||
            (usage.content && usage.content.toLowerCase().includes(searchLower))
        );
    }

    currentUsagePage = 1;
    renderUsageContent();
}

/**
 * 사용방법 페이지 변경
 */
export function changeUsagePage(page) {
    currentUsagePage = page;
    renderUsageContent();
}

/**
 * 사용방법 상세 토글
 */
export function toggleUsageDetail(element) {
    const content = element.querySelector('.usage-content');
    const icon = element.querySelector('.fa-chevron-down, .fa-chevron-up');

    if (content.style.display === 'none') {
        content.style.display = 'block';
        icon.className = 'fas fa-chevron-up';
    } else {
        content.style.display = 'none';
        icon.className = 'fas fa-chevron-down';
    }
}

// ============================================
// FAQ 탭
// ============================================

/**
 * FAQ 탭 로드
 */
async function loadFAQTab() {
    const contentArea = document.getElementById('supportContentArea');

    contentArea.innerHTML = `
        <div class="loading-spinner">
            <i class="fas fa-spinner fa-spin"></i> FAQ를 불러오는 중...
        </div>
    `;

    try {
        const response = await fetch('/api/support/pages/public?page_type=faq');
        const data = await response.json();

        if (data) {
            const pages = Array.isArray(data) ? data : (data.data || []);
            currentFAQData = pages.map(page => ({
                id: page.page_id,
                question: page.title,
                answer: page.content,
                created_at: page.created_at,
                attachment_path: page.attachment_name ? `/api/support/attachments/${page.page_id}` : null,
                attachment_name: page.attachment_name
            }));
            filteredFAQData = [...currentFAQData];
            currentFAQPage = 1;
            renderFAQContent();
        } else {
            contentArea.innerHTML = '<div class="error-message">FAQ를 불러오는데 실패했습니다.</div>';
        }
    } catch (error) {
        console.error('FAQ 로드 오류:', error);
        contentArea.innerHTML = '<div class="error-message">FAQ를 불러오는데 실패했습니다.</div>';
    }
}

/**
 * FAQ 콘텐츠 렌더링
 */
function renderFAQContent() {
    const contentArea = document.getElementById('supportContentArea');

    const totalPages = Math.ceil(filteredFAQData.length / faqPerPage);
    const startIdx = (currentFAQPage - 1) * faqPerPage;
    const pageData = filteredFAQData.slice(startIdx, startIdx + faqPerPage);

    let html = `
        <div class="support-list-header">
            <div class="support-search">
                <input type="text" id="faqSearchInput" placeholder="FAQ 검색..."
                       onkeyup="filterFAQ(this.value)">
                <i class="fas fa-search"></i>
            </div>
            <div class="support-count">총 ${filteredFAQData.length}건</div>
        </div>
        <div class="support-list faq-list">
    `;

    if (pageData.length === 0) {
        html += `
            <div class="support-empty">
                <i class="fas fa-comments"></i>
                <p>등록된 FAQ가 없습니다.</p>
            </div>
        `;
    } else {
        pageData.forEach(faq => {
            html += `
                <div class="faq-item" onclick="toggleFAQDetail(this)">
                    <div class="faq-question">
                        <span class="faq-q">Q</span>
                        <span class="faq-title">${faq.question}</span>
                        <i class="fas fa-chevron-down"></i>
                    </div>
                    <div class="faq-answer" style="display: none;">
                        <span class="faq-a">A</span>
                        <div class="faq-content">${faq.answer || '답변이 없습니다.'}</div>
                    </div>
                </div>
            `;
        });
    }

    html += '</div>';
    html += renderPagination(currentFAQPage, totalPages, 'changeFAQPage');

    contentArea.innerHTML = html;
}

/**
 * FAQ 필터링
 */
export function filterFAQ(searchTerm) {
    const searchLower = searchTerm.toLowerCase();

    if (!searchTerm || searchTerm.trim() === '') {
        filteredFAQData = [...currentFAQData];
    } else {
        filteredFAQData = currentFAQData.filter(faq =>
            faq.question.toLowerCase().includes(searchLower) ||
            (faq.answer && faq.answer.toLowerCase().includes(searchLower))
        );
    }

    currentFAQPage = 1;
    renderFAQContent();
}

/**
 * FAQ 페이지 변경
 */
export function changeFAQPage(page) {
    currentFAQPage = page;
    renderFAQContent();
}

/**
 * FAQ 상세 토글
 */
export function toggleFAQDetail(element) {
    const answer = element.querySelector('.faq-answer');
    const icon = element.querySelector('.fa-chevron-down, .fa-chevron-up');

    if (answer.style.display === 'none') {
        answer.style.display = 'flex';
        icon.className = 'fas fa-chevron-up';
    } else {
        answer.style.display = 'none';
        icon.className = 'fas fa-chevron-down';
    }
}

// ============================================
// 공통 유틸리티
// ============================================

/**
 * 페이지네이션 렌더링
 */
function renderPagination(currentPage, totalPages, changeFunction) {
    if (totalPages <= 1) return '';

    let html = '<div class="support-pagination">';

    // 이전 버튼
    if (currentPage > 1) {
        html += `<button onclick="${changeFunction}(${currentPage - 1})"><i class="fas fa-chevron-left"></i></button>`;
    }

    // 페이지 번호
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);

    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="${i === currentPage ? 'active' : ''}" onclick="${changeFunction}(${i})">${i}</button>`;
    }

    // 다음 버튼
    if (currentPage < totalPages) {
        html += `<button onclick="${changeFunction}(${currentPage + 1})"><i class="fas fa-chevron-right"></i></button>`;
    }

    html += '</div>';
    return html;
}

/**
 * 날짜 포맷팅
 */
function formatSupportDate(dateString) {
    if (!dateString) return '-';

    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

// ============================================
// 전역 노출
// ============================================
if (typeof window !== 'undefined') {
    window.displaySupportContent = displaySupportContent;
    window.switchSupportTab = switchSupportTab;
    window.filterNotices = filterNotices;
    window.changeNoticesPage = changeNoticesPage;
    window.openNoticeDetail = openNoticeDetail;
    window.closeNoticeModal = closeNoticeModal;
    window.filterProcedures = filterProcedures;
    window.changeProceduresPage = changeProceduresPage;
    window.filterUsage = filterUsage;
    window.changeUsagePage = changeUsagePage;
    window.toggleUsageDetail = toggleUsageDetail;
    window.filterFAQ = filterFAQ;
    window.changeFAQPage = changeFAQPage;
    window.toggleFAQDetail = toggleFAQDetail;
}
