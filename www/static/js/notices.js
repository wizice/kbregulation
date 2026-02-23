/**
 * 사용자 화면 공지사항 표시 JavaScript
 */

// 공지사항 데이터
let noticesData = [];
let noticesExpanded = true;

// 페이지 로드 시 공지사항 로드
document.addEventListener('DOMContentLoaded', () => {
    loadNotices();
});

/**
 * 공지사항 목록 로드 (활성화된 공지사항만)
 */
async function loadNotices() {
    try {
        // FastAPI 백엔드에서 활성화된 공지사항만 조회
        const response = await fetch('/api/notices/?is_active=true&limit=10');

        if (!response.ok) {
            console.warn('공지사항 로드 실패:', response.status);
            return;
        }

        noticesData = await response.json();

        // 공지사항이 있으면 표시
        if (noticesData && noticesData.length > 0) {
            renderNotices();
            document.getElementById('noticesSection').style.display = 'block';
        }
    } catch (error) {
        console.error('공지사항 로드 에러:', error);
    }
}

/**
 * 공지사항 목록 렌더링
 */
function renderNotices() {
    const noticesList = document.getElementById('noticesList');

    if (!noticesList) return;

    if (noticesData.length === 0) {
        noticesList.innerHTML = `
            <div class="notices-empty">
                <i class="fas fa-inbox"></i>
                <p>등록된 공지사항이 없습니다</p>
            </div>
        `;
        return;
    }

    // 공지사항 HTML 생성
    noticesList.innerHTML = noticesData.map(notice => {
        // 날짜 포맷 (yyyy.mm.dd.)
        const createdDate = formatDate(notice.created_at);

        // 첨부파일 아이콘
        const attachmentIcon = notice.attachment_name ?
            `<i class="fas fa-paperclip notice-attachment-icon" title="첨부파일: ${notice.attachment_name}"></i>` : '';

        // NEW 배지 (3일 이내 작성된 공지사항)
        const isNew = isWithinDays(notice.created_at, 3);
        const newBadge = isNew ?
            `<span class="notice-new-badge">N</span> ` : '';

        // 중요 공지사항 배지 (제목 앞에 표시)
        const importantBadge = notice.is_important ?
            `<span class="notice-important-badge">
                중요
            </span> ` : '';

        return `
            <div class="notice-item" onclick="showNoticeDetail(${notice.notice_id})">
                <div class="notice-content">
                    <div class="notice-title">
                        ${newBadge}${importantBadge}
                        <span class="notice-title-text">${escapeHtml(notice.title)}</span>
                        ${attachmentIcon}
                    </div>
                    <div class="notice-meta">
                        <span>
                            <i class="fas fa-user"></i>
                            ${escapeHtml(notice.created_by || '관리자')}
                        </span>
                        <span>
                            <i class="fas fa-calendar"></i>
                            ${createdDate}
                        </span>
                        <span>
                            <i class="fas fa-eye"></i>
                            ${notice.view_count}
                        </span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * 공지사항 토글 (확장/축소)
 */
function toggleNotices() {
    noticesExpanded = !noticesExpanded;
    const noticesList = document.getElementById('noticesList');
    const toggleIcon = document.getElementById('noticesToggleIcon');
    const toggleBtn = document.querySelector('.notices-toggle');

    if (noticesExpanded) {
        noticesList.style.display = 'block';
        toggleIcon.className = 'fas fa-chevron-up';
        toggleBtn.classList.remove('collapsed');
    } else {
        noticesList.style.display = 'none';
        toggleIcon.className = 'fas fa-chevron-down';
        toggleBtn.classList.add('collapsed');
    }
}

/**
 * 공지사항 상세 보기
 */
async function showNoticeDetail(noticeId) {
    try {
        // API에서 상세 정보 가져오기 (조회수 자동 증가)
        const response = await fetch(`/api/notices/${noticeId}`);

        if (!response.ok) {
            alert('공지사항을 불러올 수 없습니다.');
            return;
        }

        const notice = await response.json();

        // 모달 생성 및 표시
        showNoticeModal(notice);

    } catch (error) {
        console.error('공지사항 상세 조회 에러:', error);
        alert('공지사항을 불러오는 중 오류가 발생했습니다.');
    }
}

/**
 * 공지사항 모달 표시
 */
function showNoticeModal(notice) {
    // 기존 모달 제거
    const existingModal = document.getElementById('noticeModal');
    if (existingModal) {
        existingModal.remove();
    }

    // 날짜 포맷
    const createdDate = formatDate(notice.created_at);

    // 중요 배지
    const importantBadge = notice.is_important ?
        `<span class="notice-important-badge">
            <i class="fas fa-exclamation-circle"></i>
            중요
        </span>` : '';

    // 첨부파일 섹션
    const attachmentSection = notice.attachment_name ? `
        <div class="notice-modal-attachment">
            <div class="notice-modal-attachment-title">
                <i class="fas fa-paperclip"></i> 첨부파일
            </div>
            <a href="/api/notices/download/${notice.notice_id}"
               class="notice-modal-attachment-link"
               download="${notice.attachment_name}">
                <i class="fas fa-download"></i>
                ${escapeHtml(notice.attachment_name)}
                ${formatFileSize(notice.attachment_size)}
            </a>
        </div>
    ` : '';

    // 모달 HTML
    const modalHTML = `
        <div id="noticeModal" class="notice-modal">
            <div class="notice-modal-content">
                <div class="notice-modal-header">
                    <h2>
                        <i class="fas fa-bullhorn"></i>
                        공지사항
                    </h2>
                    <button class="notice-modal-close" onclick="closeNoticeModal()">
                        &times;
                    </button>
                </div>
                <div class="notice-modal-body">
                    <div class="notice-modal-title">
                        ${importantBadge}
                        ${escapeHtml(notice.title)}
                    </div>
                    <div class="notice-modal-meta">
                        <span>
                            <i class="fas fa-user"></i>
                            ${escapeHtml(notice.created_by || '관리자')}
                        </span>
                        <span>
                            <i class="fas fa-calendar"></i>
                            ${createdDate}
                        </span>
                        <span>
                            <i class="fas fa-eye"></i>
                            조회수 ${notice.view_count}
                        </span>
                    </div>
                    <div class="notice-modal-content-text">
                        ${escapeHtml(notice.content)}
                    </div>
                    ${attachmentSection}
                </div>
            </div>
        </div>
    `;

    // 모달 추가
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // 모달 표시
    const modal = document.getElementById('noticeModal');
    modal.style.display = 'block';

    // 모달 외부 클릭 시 닫기
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeNoticeModal();
        }
    });
}

/**
 * 공지사항 모달 닫기
 */
function closeNoticeModal() {
    const modal = document.getElementById('noticeModal');
    if (modal) {
        modal.style.display = 'none';
        setTimeout(() => modal.remove(), 300);
    }
}

/**
 * 날짜 포맷팅 (yyyy.mm.dd.)
 */
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}.${month}.${day}.`;
}

/**
 * 파일 크기 포맷팅
 */
function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    const size = Math.round(bytes / Math.pow(k, i) * 100) / 100;
    return `(${size} ${sizes[i]})`;
}

/**
 * HTML 이스케이프 (XSS 방지)
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 날짜가 지정된 일수 이내인지 확인
 */
function isWithinDays(dateStr, days) {
    if (!dateStr) return false;
    const date = new Date(dateStr);
    const now = new Date();
    const diffTime = now - date;
    const diffDays = diffTime / (1000 * 60 * 60 * 24);
    return diffDays <= days;
}

// ESC 키로 모달 닫기
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeNoticeModal();
    }
});
