// classification-manager.js - 분류 체계 관리

const ClassificationManager = {
    // 분류 데이터 - 실제 KB신용정보 병원 규정 분류
    chapters: [
        {
            id: '1',
            name: '환자안전보장활동',
            count: 9,
            expanded: false,
            articles: []
        },
        {
            id: '2',
            name: '진료전달체계와 평가',
            count: 36,
            expanded: false,
            articles: []
        },
        {
            id: '3',
            name: '환자진료',
            count: 24,
            expanded: false,
            articles: []
        },
        {
            id: '4',
            name: '의약품관리',
            count: 17,
            expanded: false,
            articles: []
        },
        {
            id: '5',
            name: '수술 및 마취진정관리',
            count: 6,
            expanded: false,
            articles: []
        },
        {
            id: '6',
            name: '환자권리존중 및 보호',
            count: 11,
            expanded: false,
            articles: []
        },
        {
            id: '7',
            name: '질 향상 및 환자안전 활동',
            count: 8,
            expanded: false,
            articles: []
        },
        {
            id: '8',
            name: '감염관리',
            count: 11,
            expanded: false,
            articles: []
        },
        {
            id: '9',
            name: '경영 및 조직운영',
            count: 8,
            expanded: false,
            articles: []
        },
        {
            id: '10',
            name: '인적자원 관리',
            count: 14,
            expanded: false,
            articles: []
        },
        {
            id: '11',
            name: '시설 및 환경관리',
            count: 14,
            expanded: false,
            articles: []
        },
        {
            id: '12',
            name: '의무기록/의료정보 관리',
            count: 12,
            expanded: false,
            articles: []
        },
        {
            id: '13',
            name: '의학교육',
            count: 2,
            expanded: false,
            articles: []
        }
    ],

    // 현재 선택된 조문
    selectedArticle: null,

    // 데이터 로드
    async loadData() {
        await this.loadClassifications();
        this.renderClassificationTable();
        // RegulationEditor가 로드된 경우 분류 필터 업데이트
        if (typeof RegulationEditor !== 'undefined' && RegulationEditor.loadClassificationFilter) {
            RegulationEditor.loadClassificationFilter();
        }
    },

    // wz_cate 테이블에서 분류 로드
    async loadClassifications() {
        try {
            const response = await fetch('/api/v1/classification/list', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (!response.ok) {
                console.error('Failed to load classifications');
                return;
            }

            const data = await response.json();

            if (data.success && data.classifications) {
                // 기존 chapters 배열 업데이트
                this.chapters = data.classifications.map(cls => ({
                    id: cls.id,
                    name: cls.name,
                    count: cls.count,
                    expanded: false,
                    articles: []
                }));
            }
        } catch (error) {
            console.error('Error loading classifications:', error);
        }
    },

    // 분류 테이블 렌더링
    renderClassificationTable() {
        const tbody = document.getElementById('classificationList');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        this.chapters.forEach(chapter => {
            // 장 행
            const chapterRow = document.createElement('tr');
            chapterRow.style.cursor = 'pointer';
            chapterRow.style.background = chapter.expanded ? '#f8f9fa' : '';
            chapterRow.innerHTML = `
                <td>제${chapter.id}장</td>
                <td onclick="ClassificationManager.toggleChapter('${chapter.id}')">
                    <span style="display: inline-block; width: 20px;">${chapter.expanded ? '▼' : '▶'}</span>
                    ${chapter.name}
                </td>
                <td><span class="status-badge status-active">${chapter.count}</span></td>
                <td>
                    <button class="action-btn btn-secondary btn-small" onclick="ClassificationManager.editChapter(event, '${chapter.id}')" style="margin-right: 5px;">
                        편집
                    </button>
                    <button class="action-btn btn-primary btn-small" onclick="ClassificationManager.toggleChapter('${chapter.id}')">
                        ${chapter.expanded ? '접기' : '조문보기'}
                    </button>
                </td>
            `;
            tbody.appendChild(chapterRow);
            
            // 조문 행들 (펼쳐진 경우만)
            if (chapter.expanded && chapter.articles) {
                chapter.articles.forEach(article => {
                    const articleRow = document.createElement('tr');
                    articleRow.style.cursor = 'pointer';
                    articleRow.style.background = this.selectedArticle === article.id ? '#e7f1ff' : '#fafafa';
                    articleRow.innerHTML = `
                        <td style="padding-left: 30px; color: #6c757d;">${article.number || article.id}</td>
                        <td onclick="ClassificationManager.selectArticle('${chapter.id}', ${article.id})" style="color: #6c757d;">
                            <span style="display: inline-block; width: 20px;">└</span>
                            ${article.title}
                            ${this.selectedArticle === article.id ? ' ✓' : ''}
                        </td>
                        <td style="color: #6c757d; font-size: 12px;">${article.department || '-'}</td>
                        <td>
                            <button class="action-btn btn-info btn-small"
                                    onclick="event.stopPropagation(); ClassificationManager.selectArticle('${chapter.id}', ${article.id})">
                                미리보기
                            </button>
                        </td>
                    `;
                    tbody.appendChild(articleRow);
                });
            }
        });
    },

    // 장 토글
    async toggleChapter(chapterId) {
        const chapter = this.chapters.find(c => c.id === chapterId);
        if (chapter) {
            chapter.expanded = !chapter.expanded;

            // 펼쳐질 때 실제 규정 데이터 로드
            if (chapter.expanded && (!chapter.articles || chapter.articles.length === 0)) {
                await this.loadChapterRegulations(chapterId);
            }

            this.renderClassificationTable();

            // 미리보기 영역 업데이트
            if (chapter.expanded) {
                const previewArea = document.getElementById('articlePreviewArea');
                if (previewArea) {
                    previewArea.innerHTML = `
                        <h4>제${chapterId}장 - ${chapter.name}</h4>
                        <p style="color: #6c757d;">조문을 선택하면 내용이 표시됩니다.</p>
                    `;
                }
            }
        }
    },

    // 장의 규정 목록 로드
    async loadChapterRegulations(chapterId) {
        try {
            const response = await fetch(`/api/v1/regulation/by-classification/${chapterId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (!response.ok) {
                console.error('Failed to load regulations');
                return;
            }

            const data = await response.json();

            if (data.success && data.regulations) {
                const chapter = this.chapters.find(c => c.id === chapterId);
                if (chapter) {
                    // 규정 데이터를 articles 형식으로 변환
                    chapter.articles = data.regulations.map(reg => ({
                        id: reg.rule_id,
                        number: reg.publication_no,
                        title: reg.name,
                        department: reg.department,
                        established_date: reg.established_date,
                        revised_date: reg.last_revised_date,
                        content_path: reg.content_path
                    }));
                }
            }
        } catch (error) {
            console.error('Error loading chapter regulations:', error);
        }
    },

    // 장 편집
    async editChapter(event, chapterId) {
        if (event) {
            event.stopPropagation(); // 행 클릭 이벤트 전파 방지
        }

        const chapter = this.chapters.find(c => c.id === chapterId);
        if (!chapter) return;

        // 편집 모달 표시
        this.showClassificationModal('edit', chapter);
    },

    // 조문 선택
    async selectArticle(chapterId, articleId) {
        console.log('selectArticle called with chapterId:', chapterId, 'articleId:', articleId);
        this.selectedArticle = articleId;

        const chapter = this.chapters.find(c => c.id === chapterId);
        if (chapter) {
            console.log('Chapter found:', chapter);
            const article = chapter.articles.find(a => a.id === articleId);
            if (article) {
                console.log('Article found:', article);
                // 실제 조문 내용 로드
                await this.loadArticleContent(articleId);
                this.renderClassificationTable(); // 선택 표시 업데이트
            } else {
                console.error('Article not found with ID:', articleId);
            }
        } else {
            console.error('Chapter not found with ID:', chapterId);
        }
    },

    // 조문 내용 로드
    async loadArticleContent(articleId) {
        console.log('Loading article content for ID:', articleId);
        const previewArea = document.getElementById('articlePreviewArea');
        if (!previewArea) {
            console.error('Preview area not found');
            return;
        }

        // 로딩 표시
        previewArea.innerHTML = '<div style="text-align: center; padding: 40px;"><div class="spinner"></div> 조문 내용을 불러오는 중...</div>';

        try {
            const response = await fetch(`/api/v1/regulation/content/${articleId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            console.log('Response status:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Failed to load article content:', errorText);
                throw new Error(`Failed to load article content: ${response.status}`);
            }

            const data = await response.json();
            console.log('Article content data:', data);

            if (data.success && data.content) {
                this.showArticlePreview(data.rule, data.content);
            } else {
                console.error('No content in response:', data);
                previewArea.innerHTML = `
                    <div style="background: #fff3cd; padding: 20px; border-radius: 8px;">
                        <p style="color: #856404; text-align: center;">
                            조문 내용을 불러올 수 없습니다.<br>
                            <small>${data.error || 'Content not available'}</small>
                        </p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading article content:', error);
            previewArea.innerHTML = `
                <div style="background: #f8d7da; padding: 20px; border-radius: 8px;">
                    <p style="color: #721c24; text-align: center;">
                        조문 내용을 불러오는 중 오류가 발생했습니다.<br>
                        <small>${error.message}</small>
                    </p>
                </div>
            `;
        }
    },

    // 조문 미리보기 표시
    showArticlePreview(ruleInfo, content) {
        console.log('Showing article preview:', ruleInfo, content);
        const previewArea = document.getElementById('articlePreviewArea');
        if (!previewArea) {
            console.error('Preview area not found in showArticlePreview');
            return;
        }

        let htmlContent = '';

        if (content && content.full_text) {
            htmlContent = `
                <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h3 style="color: #60584C; margin-bottom: 20px;">${ruleInfo.name}</h3>
                    <div style="line-height: 1.8; font-size: 14px; margin-bottom: 30px; max-height: 500px; overflow-y: auto;">
                        ${content.full_text}
                    </div>
                    <div style="padding-top: 20px; border-top: 1px solid #e9ecef;">
                        <p style="font-size: 14px; color: #6c757d; margin: 5px 0;">
                            <strong>공포번호:</strong> ${ruleInfo.publication_no || '-'}
                        </p>
                        <p style="font-size: 14px; color: #6c757d; margin: 5px 0;">
                            <strong>소관부서:</strong> ${ruleInfo.department || '-'}
                        </p>
                        <p style="font-size: 14px; color: #6c757d; margin: 5px 0;">
                            <strong>제정일:</strong> ${ruleInfo.established_date || '-'}
                        </p>
                        <p style="font-size: 14px; color: #6c757d; margin: 5px 0;">
                            <strong>최종개정일:</strong> ${ruleInfo.last_revised_date || '-'}
                        </p>
                    </div>
                </div>
            `;
        } else if (content && content.error) {
            htmlContent = `
                <div style="background: #fff3cd; padding: 20px; border-radius: 8px;">
                    <h3 style="color: #856404;">${ruleInfo.name}</h3>
                    <p style="color: #856404;">${content.error}</p>
                    <p style="font-size: 12px; color: #856404; margin-top: 10px;">파일 경로: ${content.path || '-'}</p>
                </div>
            `;
        } else {
            htmlContent = `
                <div style="background: white; padding: 20px; border-radius: 8px;">
                    <h3>${ruleInfo.name}</h3>
                    <p style="color: #6c757d;">조문 내용을 표시할 수 없습니다.</p>
                </div>
            `;
        }

        previewArea.innerHTML = htmlContent;
    },

    // 장 추가
    addChapter() {
        this.showClassificationModal('add');
    },

    // 분류 모달 표시 (추가/편집 통합)
    showClassificationModal(mode, chapter = null) {
        const isEdit = mode === 'edit';
        const title = isEdit ? '분류 편집' : '분류 추가';

        // 모달 HTML 생성
        const modalHtml = `
            <div class="modal active" id="classificationModal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>${title}</h2>
                        <button class="modal-close" onclick="ClassificationManager.closeModal()">✕</button>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" id="classificationMode" value="${mode}">
                        ${isEdit ? `<input type="hidden" id="classificationId" value="${chapter.id}">` : ''}
                        <div class="form-group">
                            <label class="form-label">장 번호 <span class="required">*</span></label>
                            <input type="number" class="form-input" id="classificationNumber"
                                   placeholder="예: 14" min="1" required
                                   value="${isEdit ? chapter.id : ''}"
                                   ${isEdit ? 'disabled' : ''}>
                        </div>
                        <div class="form-group">
                            <label class="form-label">분류명 <span class="required">*</span></label>
                            <input type="text" class="form-input" id="classificationName"
                                   placeholder="분류명을 입력하세요" required
                                   value="${isEdit ? chapter.name : ''}">
                        </div>
                        ${isEdit ? `
                        <div id="deleteWarning" style="display: none; background: #fff3cd; padding: 10px; border-radius: 4px; margin-top: 10px;">
                            <p style="color: #856404; margin: 0; font-size: 14px;">
                                <strong>⚠️ 경고:</strong> 이 분류에 속한 모든 규정도 함께 삭제됩니다. 삭제하시려면 삭제 버튼을 다시 클릭하세요.
                            </p>
                        </div>
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="ClassificationManager.closeModal()">취소</button>
                        ${isEdit ? `<button class="btn btn-danger" onclick="ClassificationManager.deleteClassification('${chapter.id}')">삭제</button>` : ''}
                        <button class="btn btn-primary" onclick="ClassificationManager.saveClassification()">저장</button>
                    </div>
                </div>
            </div>
        `;

        // 기존 모달 제거 후 새 모달 추가
        const existingModal = document.getElementById('classificationModal');
        if (existingModal) existingModal.remove();

        document.body.insertAdjacentHTML('beforeend', modalHtml);
    },

    // 모달 닫기
    closeModal() {
        const modal = document.getElementById('classificationModal');
        if (modal) {
            modal.remove();
        }
    },

    // 분류 저장
    async saveClassification() {
        const mode = document.getElementById('classificationMode').value.trim();
        const name = document.getElementById('classificationName').value.trim();

        if (!name) {
            alert('분류명을 입력해주세요.');
            return;
        }

        if (mode === 'add') {
            // 새 분류 추가
            const chapterNumberInput = document.getElementById('classificationNumber');
            if (!chapterNumberInput || !chapterNumberInput.value) {
                alert('장 번호를 입력해주세요.');
                return;
            }

            const chapterNumber = parseInt(chapterNumberInput.value);
            if (isNaN(chapterNumber) || chapterNumber < 1) {
                alert('올바른 장 번호를 입력해주세요.');
                return;
            }

            try {
                const response = await fetch(`/api/v1/classification/create?chapter_number=${chapterNumber}&name=${encodeURIComponent(name)}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include'
                });

                const data = await response.json();

                if (data.success) {
                    // 로컬 데이터에 추가
                    this.chapters.push({
                        id: chapterNumber.toString(),
                        name: name,
                        count: 0,
                        expanded: false,
                        articles: []
                    });

                    // 장 번호순으로 정렬
                    this.chapters.sort((a, b) => parseInt(a.id) - parseInt(b.id));

                    this.showNotification(data.message);

                    // 데이터 다시 로드하여 실제 카운트 반영
                    await this.loadData();
                    this.closeModal();
                } else {
                    if (data.error === 'duplicate') {
                        alert(data.message);
                    } else {
                        alert(data.message || '분류 추가 실패');
                    }
                }
            } catch (error) {
                console.error('Error creating classification:', error);
                alert('분류 추가 중 오류가 발생했습니다.');
            }
        } else {
            // 기존 분류 수정
            const chapterId = document.getElementById('classificationId').value.trim();

            try {
                const response = await fetch(`/api/v1/classification/update/${chapterId}?new_name=${encodeURIComponent(name)}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include'
                });

                const data = await response.json();

                if (data.success) {
                    const chapter = this.chapters.find(c => c.id === chapterId);
                    if (chapter) {
                        chapter.name = name;
                    }

                    this.showNotification(data.message);
                    this.renderClassificationTable();
                    this.closeModal();

                    // 미리보기 영역 업데이트
                    if (chapter && chapter.expanded) {
                        const previewArea = document.getElementById('articlePreviewArea');
                        if (previewArea && !this.selectedArticle) {
                            previewArea.innerHTML = `
                                <h4>제${chapterId}장 - ${chapter.name}</h4>
                                <p style="color: #6c757d;">조문을 선택하면 내용이 표시됩니다.</p>
                            `;
                        }
                    }
                } else {
                    alert(data.message || '분류 수정 실패');
                }
            } catch (error) {
                console.error('Error updating classification:', error);
                alert('분류 수정 중 오류가 발생했습니다.');
            }
        }

        // 분류 필터 업데이트
        if (typeof RegulationEditor !== 'undefined' && RegulationEditor.loadClassificationFilter) {
            RegulationEditor.loadClassificationFilter();
        }
    },

    // 분류 삭제
    async deleteClassification(chapterId) {
        const deleteWarning = document.getElementById('deleteWarning');

        // 첫 번째 클릭: 경고 메시지 표시
        if (deleteWarning && deleteWarning.style.display === 'none') {
            deleteWarning.style.display = 'block';
            return;
        }

        // 두 번째 클릭: 실제 삭제 실행
        const chapter = this.chapters.find(c => c.id === chapterId);
        if (!chapter) return;

        if (!confirm(`정말로 "제${chapterId}장 - ${chapter.name}"을(를) 삭제하시겠습니까?\n이 분류에 속한 모든 내규도 함께 삭제될 수 있습니다.`)) {
            return;
        }

        try {
            const response = await fetch(`/api/v1/classification/delete/${chapterId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            const data = await response.json();

            if (data.success) {
                // 로컬 데이터에서 제거
                const chapterIndex = this.chapters.findIndex(c => c.id === chapterId);
                if (chapterIndex > -1) {
                    this.chapters.splice(chapterIndex, 1);
                }

                this.renderClassificationTable();
                this.closeModal();

                // 미리보기 영역 초기화
                const previewArea = document.getElementById('articlePreviewArea');
                if (previewArea) {
                    previewArea.innerHTML = '<p style="color: #6c757d; text-align: center;">분류를 선택하면 해당 조문이 표시됩니다.</p>';
                }

                // 분류 필터 업데이트
                if (typeof RegulationEditor !== 'undefined' && RegulationEditor.loadClassificationFilter) {
                    RegulationEditor.loadClassificationFilter();
                }

                this.showNotification(data.message, 'success');
            } else {
                if (data.error === 'has_regulations') {
                    alert(data.message);
                } else {
                    alert(data.message || '분류 삭제 실패');
                }
            }
        } catch (error) {
            console.error('Error deleting classification:', error);
            alert('분류 삭제 중 오류가 발생했습니다.');
        }
    },

    // 전체 분류 목록 가져오기 (select box용)
    getAllClassifications() {
        const classifications = [];
        
        this.chapters.forEach(chapter => {
            // 장 추가
            classifications.push({
                value: chapter.id,
                text: `제${chapter.id}장 - ${chapter.name}`
            });
            
            // 조문 추가
            if (chapter.articles) {
                chapter.articles.forEach(article => {
                    classifications.push({
                        value: article.id,
                        text: `　${article.id} 제${article.number}조 (${article.title})`
                    });
                });
            }
        });
        
        return classifications;
    },

    // 알림 표시
    showNotification(message, type = 'success') {
        if (typeof RegulationEditor !== 'undefined' && RegulationEditor.showNotification) {
            RegulationEditor.showNotification(message, type);
        } else {
            alert(message);
        }
    },

    // Excel 다운로드 (별표 제1호 형식)
    async downloadExcel() {
        try {
            this.showNotification('Excel 생성 중...', 'info');
            const response = await fetch('/api/v1/classification/export/excel', {
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Excel 다운로드 실패');

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const today = new Date().toISOString().slice(2, 10).replace(/-/g, '');
            a.download = `KB신용정보_별표제1호_사규_목차_${today}.xlsx`;
            a.click();
            URL.revokeObjectURL(url);
            this.showNotification('Excel 다운로드 완료', 'success');
        } catch (error) {
            console.error('Excel 다운로드 오류:', error);
            alert('Excel 다운로드에 실패했습니다.');
        }
    },

    // Excel 업로드
    async uploadExcel(input) {
        const file = input.files[0];
        if (!file) return;

        if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
            alert('Excel 파일(.xlsx)만 업로드 가능합니다.');
            input.value = '';
            return;
        }

        if (!confirm(`"${file.name}" 파일을 업로드하시겠습니까?\nExcel의 사규명, 소관부서, 개정일, 제정일이 DB에 반영됩니다.`)) {
            input.value = '';
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            this.showNotification('Excel 업로드 중...', 'info');
            const response = await fetch('/api/v1/classification/import/excel', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || '업로드 실패');
            }

            const result = await response.json();
            let msg = result.message;
            if (result.errors && result.errors.length > 0) {
                msg += `\n\n경고:\n${result.errors.join('\n')}`;
            }
            alert(msg);
            this.showNotification(`${result.updated}개 규정 업데이트 완료`, 'success');

            // 데이터 새로고침
            await this.loadData();
        } catch (error) {
            console.error('Excel 업로드 오류:', error);
            alert('Excel 업로드 실패: ' + error.message);
        }

        input.value = '';
    }
};
