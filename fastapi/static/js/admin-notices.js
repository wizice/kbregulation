// 공지사항 관리 JavaScript

let allNotices = [];
let currentNoticeId = null;
let selectedFile = null;
let removeCurrentAttachment = false;

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', () => {
    loadNotices();
    setupFileUploadEvents();
    setupSearchEvent();
});

// 공지사항 목록 불러오기
async function loadNotices() {
    try {
        const response = await fetch('/api/notices/?is_active=null');  // 모든 공지사항 조회
        if (!response.ok) throw new Error('공지사항 로드 실패');

        allNotices = await response.json();
        renderNotices(allNotices);
    } catch (error) {
        console.error('Error:', error);
        showError('공지사항을 불러오는데 실패했습니다.');
    }
}

// 공지사항 렌더링
function renderNotices(notices) {
    const loadingState = document.getElementById('loadingState');
    const tableElement = document.getElementById('noticesTable');
    const emptyState = document.getElementById('emptyState');
    const tbody = document.getElementById('noticesBody');

    loadingState.style.display = 'none';

    if (notices.length === 0) {
        tableElement.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }

    tableElement.style.display = 'table';
    emptyState.style.display = 'none';

    tbody.innerHTML = notices.map(notice => {
        const attachmentIcon = notice.attachment_name ?
            `<i class="fas fa-paperclip" style="color: #667eea; margin-left: 5px;" title="첨부파일: ${notice.attachment_name}"></i>` : '';

        return `
        <tr>
            <td>${notice.notice_id}</td>
            <td>
                ${notice.title}
                ${attachmentIcon}
            </td>
            <td>${notice.created_by || '-'}</td>
            <td>${formatDate(notice.created_at)}</td>
            <td>${notice.view_count}</td>
            <td>
                ${notice.is_important ? '<span class="badge badge-important">중요</span>' : '-'}
            </td>
            <td>
                ${notice.is_active ? '<span class="badge badge-active">활성</span>' : '<span class="badge badge-inactive">비활성</span>'}
            </td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editNotice(${notice.notice_id})" title="수정">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteNotice(${notice.notice_id}, '${notice.title.replace(/'/g, "\\'")}' )" title="삭제">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
        `;
    }).join('');
}

// 날짜 포맷팅
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}.`;
}

// 검색 이벤트 설정
function setupSearchEvent() {
    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const filtered = allNotices.filter(notice =>
            notice.title.toLowerCase().includes(query) ||
            notice.content.toLowerCase().includes(query)
        );
        renderNotices(filtered);
    });
}

// 파일 업로드 이벤트 설정
function setupFileUploadEvents() {
    const fileUploadArea = document.getElementById('fileUploadArea');
    const fileInput = document.getElementById('fileInput');

    // 드래그 앤 드롭
    fileUploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileUploadArea.classList.add('drag-over');
    });

    fileUploadArea.addEventListener('dragleave', () => {
        fileUploadArea.classList.remove('drag-over');
    });

    fileUploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        fileUploadArea.classList.remove('drag-over');

        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect({ target: fileInput });
        }
    });
}

// 파일 선택 처리
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    // 파일 크기 체크 (10MB)
    if (file.size > 10 * 1024 * 1024) {
        alert('파일 크기는 10MB를 초과할 수 없습니다.');
        event.target.value = '';
        return;
    }

    selectedFile = file;

    const fileInfo = document.getElementById('fileInfo');
    fileInfo.innerHTML = `
        <i class="fas fa-file" style="color: #667eea;"></i>
        <strong>${file.name}</strong> (${formatFileSize(file.size)})
        <button type="button" onclick="clearFile()" style="float: right; background: none; border: none; color: #f56565; cursor: pointer;">
            <i class="fas fa-times"></i>
        </button>
    `;
    fileInfo.classList.add('show');
}

// 파일 크기 포맷팅
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// 파일 선택 취소
function clearFile() {
    selectedFile = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('fileInfo').classList.remove('show');
}

// 새 공지사항 작성 모달 열기
function openCreateModal() {
    currentNoticeId = null;
    removeCurrentAttachment = false;
    document.getElementById('modalTitle').textContent = '새 공지사항';
    document.getElementById('noticeForm').reset();
    document.getElementById('noticeId').value = '';
    document.getElementById('createdBy').value = '관리자';
    document.getElementById('currentAttachment').style.display = 'none';
    clearFile();
    document.getElementById('noticeModal').style.display = 'block';
}

// 공지사항 수정 모달 열기
async function editNotice(noticeId) {
    try {
        const response = await fetch(`/api/notices/${noticeId}`);
        if (!response.ok) throw new Error('공지사항 조회 실패');

        const notice = await response.json();

        currentNoticeId = noticeId;
        removeCurrentAttachment = false;
        document.getElementById('modalTitle').textContent = '공지사항 수정';
        document.getElementById('noticeId').value = noticeId;
        document.getElementById('title').value = notice.title;
        document.getElementById('content').value = notice.content;
        document.getElementById('createdBy').value = notice.created_by || '관리자';
        document.getElementById('isImportant').checked = notice.is_important;

        // 기존 첨부파일 표시
        if (notice.attachment_name) {
            document.getElementById('currentFileName').textContent = notice.attachment_name;
            document.getElementById('currentAttachment').style.display = 'block';
        } else {
            document.getElementById('currentAttachment').style.display = 'none';
        }

        clearFile();
        document.getElementById('noticeModal').style.display = 'block';

    } catch (error) {
        console.error('Error:', error);
        alert('공지사항을 불러오는데 실패했습니다.');
    }
}

// 첨부파일 삭제
function removeAttachment() {
    if (confirm('첨부파일을 삭제하시겠습니까?')) {
        removeCurrentAttachment = true;
        document.getElementById('currentAttachment').style.display = 'none';
    }
}

// 모달 닫기
function closeModal() {
    document.getElementById('noticeModal').style.display = 'none';
    document.getElementById('noticeForm').reset();
    currentNoticeId = null;
    selectedFile = null;
    removeCurrentAttachment = false;
    clearFile();
}

// 공지사항 저장
async function saveNotice(event) {
    event.preventDefault();

    const title = document.getElementById('title').value.trim();
    const content = document.getElementById('content').value.trim();
    const createdBy = document.getElementById('createdBy').value.trim();
    const isImportant = document.getElementById('isImportant').checked;

    if (!title || !content) {
        alert('제목과 내용을 입력해주세요.');
        return;
    }

    try {
        const formData = new FormData();
        formData.append('title', title);
        formData.append('content', content);
        formData.append('is_important', isImportant);
        formData.append('created_by', createdBy);

        // 파일 첨부
        if (selectedFile) {
            formData.append('file', selectedFile);
        }

        let url, method;
        if (currentNoticeId) {
            // 수정
            url = `/api/notices/${currentNoticeId}`;
            method = 'PUT';

            // 첨부파일 삭제 요청
            if (removeCurrentAttachment) {
                formData.append('remove_attachment', 'true');
            }
        } else {
            // 신규 등록
            url = '/api/notices/';
            method = 'POST';
        }

        const response = await fetch(url, {
            method: method,
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '저장 실패');
        }

        alert(currentNoticeId ? '수정되었습니다.' : '등록되었습니다.');
        closeModal();
        loadNotices();

    } catch (error) {
        console.error('Error:', error);
        alert('저장하는데 실패했습니다: ' + error.message);
    }
}

// 공지사항 삭제
async function deleteNotice(noticeId, title) {
    if (!confirm(`"${title}"\n이 공지사항을 삭제하시겠습니까?`)) {
        return;
    }

    // 완전 삭제 확인
    const permanent = confirm('완전히 삭제하시겠습니까?\n(취소 시 비활성화됩니다)');

    try {
        const response = await fetch(`/api/notices/${noticeId}?permanent=${permanent}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('삭제 실패');

        alert('삭제되었습니다.');
        loadNotices();

    } catch (error) {
        console.error('Error:', error);
        alert('삭제하는데 실패했습니다.');
    }
}

// 에러 메시지 표시
function showError(message) {
    const loadingState = document.getElementById('loadingState');
    loadingState.innerHTML = `
        <i class="fas fa-exclamation-triangle" style="color: #f56565;"></i>
        <p>${message}</p>
        <button class="btn btn-primary" onclick="loadNotices()">다시 시도</button>
    `;
}

// 모달 외부 클릭 시 닫기
window.onclick = function(event) {
    const modal = document.getElementById('noticeModal');
    if (event.target === modal) {
        closeModal();
    }
}
