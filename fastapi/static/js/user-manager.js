/**
 * UserManager - 유저(관리자 계정) 관리 모듈
 */
const UserManager = {
    users: [],
    currentUserId: null,
    initialized: false,

    init() {
        if (!this.initialized) {
            this.initialized = true;
        }
        this.loadUsers();
    },

    async loadUsers() {
        try {
            const resp = await fetch('/api/v1/users/select?is_active=true&order_by=date_created DESC', {
                credentials: 'include'
            });
            if (!resp.ok) throw new Error('유저 목록 로드 실패');
            const data = await resp.json();
            this.users = data.data || [];
            this.renderUsers(this.users);
        } catch (e) {
            console.error('유저 목록 로드 오류:', e);
            document.getElementById('usersList').innerHTML =
                '<tr><td colspan="8" style="text-align:center;color:#999;padding:30px;">유저 목록을 불러올 수 없습니다.</td></tr>';
        }
    },

    roleLabels: {
        admin: '관리자',
        approver2: '2차 결재자',
        approver1: '1차 결재자',
        drafter: '입안자',
        user: '사용자'
    },

    roleColors: {
        admin: '#dc3545',
        approver2: '#fd7e14',
        approver1: '#28a745',
        drafter: '#6f42c1',
        user: '#6c757d'
    },

    getRoleBadge(role) {
        const label = this.roleLabels[role] || role || '사용자';
        const color = this.roleColors[role] || '#6c757d';
        return `<span style="background:${color}15;color:${color};padding:2px 8px;border-radius:10px;font-size:12px;font-weight:500;border:1px solid ${color}33;">${label}</span>`;
    },

    renderUsers(users) {
        const tbody = document.getElementById('usersList');
        if (!tbody) return;

        if (!users || users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#999;padding:30px;">등록된 유저가 없습니다.</td></tr>';
            return;
        }

        tbody.innerHTML = users.map(u => `
            <tr>
                <td>${u.users_id || ''}</td>
                <td>${this.escapeHtml(u.full_name || '')}</td>
                <td>${this.escapeHtml(u.username || '')}</td>
                <td>${this.escapeHtml(u.email || '')}</td>
                <td>${this.escapeHtml(u.departments || '')}</td>
                <td>${this.getRoleBadge(u.role)}</td>
                <td><span style="color:${u.is_active ? '#28a745' : '#dc3545'};font-weight:500;">${u.is_active ? '활성' : '비활성'}</span></td>
                <td>
                    <button class="btn btn-primary btn-sm" onclick="UserManager.openEditModal(${u.users_id})" style="padding:4px 10px;font-size:12px;">수정</button>
                    <button class="btn btn-danger btn-sm" onclick="UserManager.deleteUser(${u.users_id})" style="padding:4px 10px;font-size:12px;">삭제</button>
                </td>
            </tr>
        `).join('');
    },

    openCreateModal() {
        this.currentUserId = null;
        const modal = document.getElementById('userModal');
        document.getElementById('userModalTitle').textContent = '새 유저 추가';
        document.getElementById('userEditId').value = '';
        document.getElementById('userUsername').value = '';
        document.getElementById('userUsername').readOnly = false;
        document.getElementById('userPassword').value = '';
        document.getElementById('userPasswordLabel').innerHTML = '비밀번호 <span class="required">*</span>';
        document.getElementById('userPasswordHint').style.display = 'none';
        document.getElementById('userFullName').value = '';
        document.getElementById('userEmail').value = '';
        document.getElementById('userPhone').value = '';
        document.getElementById('userDepartments').value = '';
        document.getElementById('userRole').value = 'user';
        document.getElementById('userIsActive').checked = true;
        modal.style.display = 'flex';
    },

    openEditModal(id) {
        const user = this.users.find(u => u.users_id === id);
        if (!user) return;

        this.currentUserId = id;
        const modal = document.getElementById('userModal');
        document.getElementById('userModalTitle').textContent = '유저 수정';
        document.getElementById('userEditId').value = id;
        document.getElementById('userUsername').value = user.username || '';
        document.getElementById('userUsername').readOnly = true;
        document.getElementById('userPassword').value = '';
        document.getElementById('userPasswordLabel').innerHTML = '비밀번호';
        document.getElementById('userPasswordHint').style.display = 'block';
        document.getElementById('userFullName').value = user.full_name || '';
        document.getElementById('userEmail').value = user.email || '';
        document.getElementById('userPhone').value = user.phone || '';
        document.getElementById('userDepartments').value = user.departments || '';
        document.getElementById('userRole').value = user.role || 'user';
        document.getElementById('userIsActive').checked = user.is_active !== false;
        modal.style.display = 'flex';
    },

    async saveUser() {
        const editId = document.getElementById('userEditId').value;
        const isEdit = !!editId;

        const username = document.getElementById('userUsername').value.trim();
        const password = document.getElementById('userPassword').value;
        const fullName = document.getElementById('userFullName').value.trim();
        const email = document.getElementById('userEmail').value.trim();
        const phone = document.getElementById('userPhone').value.trim();
        const departments = document.getElementById('userDepartments').value.trim();
        const role = document.getElementById('userRole').value;
        const isActive = document.getElementById('userIsActive').checked;

        if (!username) { alert('아이디를 입력하세요.'); return; }
        if (!isEdit && !password) { alert('비밀번호를 입력하세요.'); return; }
        if (!fullName) { alert('이름을 입력하세요.'); return; }
        if (!email) { alert('이메일을 입력하세요.'); return; }

        try {
            let url, body;

            if (isEdit) {
                url = `/api/v1/users/update?id=${editId}`;
                body = { full_name: fullName, email, phone, departments, role, is_active: isActive };
                if (password) body.password = password;
            } else {
                url = '/api/v1/users/insert';
                body = { username, password, email, full_name: fullName, phone, departments, role, is_active: isActive };
            }

            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(body)
            });

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.detail || '저장 실패');
            }

            this.closeModal();
            this.loadUsers();
            alert(isEdit ? '유저 정보가 수정되었습니다.' : '유저가 추가되었습니다.');
        } catch (e) {
            alert('오류: ' + e.message);
        }
    },

    async deleteUser(id) {
        const user = this.users.find(u => u.users_id === id);
        const name = user ? (user.full_name || user.username) : id;

        if (!confirm(`"${name}" 유저를 삭제하시겠습니까?`)) return;

        try {
            const resp = await fetch(`/api/v1/users/delete?id=${id}`, {
                method: 'POST',
                credentials: 'include'
            });

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.detail || '삭제 실패');
            }

            this.loadUsers();
            alert('유저가 삭제되었습니다.');
        } catch (e) {
            alert('오류: ' + e.message);
        }
    },

    closeModal() {
        const modal = document.getElementById('userModal');
        if (modal) modal.style.display = 'none';
        this.currentUserId = null;
    },

    async searchUsers() {
        const keyword = document.getElementById('userSearchInput')?.value?.trim() || '';
        if (!keyword) {
            this.loadUsers();
            return;
        }

        const filtered = this.users.filter(u =>
            (u.full_name || '').includes(keyword) ||
            (u.username || '').includes(keyword) ||
            (u.departments || '').includes(keyword) ||
            (u.email || '').includes(keyword)
        );
        this.renderUsers(filtered);
    },

    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
