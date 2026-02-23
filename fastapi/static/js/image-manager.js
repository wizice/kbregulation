/**
 * 이미지 관리 모듈
 * 규정 편집 시 조문별 이미지 업로드/삭제/조회 기능 제공
 */

const ImageManager = {
    currentRuleId: null,
    currentArticleSeq: null,        // seq 사용 (고유 식별자)
    currentArticleNumber: null,     // 표시용 번호
    images: {},  // 조문별 이미지 매핑 (seq를 키로 사용) { "10": [{...}], "21": [{...}] }

    /**
     * 초기화
     */
    async init(ruleId) {
        console.log('[ImageManager] Initializing for rule:', ruleId);
        this.currentRuleId = ruleId;
        this.currentArticleSeq = null;
        this.currentArticleNumber = null;
        this.images = {};  // 이미지 목록 초기화

        // 이벤트 리스너 설정
        this.setupEventListeners();

        // 조문 목록 및 이미지 목록 로드 (한 번의 API 호출)
        await this.loadImagesAndArticles();
    },

    /**
     * 이벤트 리스너 설정
     */
    setupEventListeners() {
        // 조문 선택 이벤트
        const articleSelector = document.getElementById('imageArticleSelector');
        if (articleSelector) {
            articleSelector.addEventListener('change', (e) => {
                this.onArticleSelected(e.target.value);
            });
        }

        // 파일 선택 이벤트
        const fileInput = document.getElementById('imageFileInput');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.onFilesSelected(e.target.files);
            });
        }

        // 드래그 앤 드롭 이벤트
        this.setupDragDrop();
    },

    /**
     * 조문 목록 및 이미지 목록 로드 (한 번의 API 호출)
     */
    async loadImagesAndArticles() {
        try {
            const response = await fetch(`/api/v1/rule-enhanced/images/${this.currentRuleId}`, {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('데이터 조회 실패');
            }

            const data = await response.json();

            if (data.success) {
                // 조문 목록 채우기
                if (data.articles) {
                    this.populateArticleSelector(data.articles);
                } else {
                    console.warn('[ImageManager] No articles found');
                }

                // 이미지 목록 저장
                if (data.images_by_article) {
                    this.images = data.images_by_article;
                    console.log('[ImageManager] Loaded images:', this.images);

                    // 현재 선택된 조문의 이미지 표시
                    if (this.currentArticleNumber) {
                        this.renderImageList(this.currentArticleNumber);
                    }
                }
            }
        } catch (error) {
            console.error('[ImageManager] Error loading data:', error);
            alert('조문 및 이미지 데이터 조회 중 오류가 발생했습니다.');
        }
    },

    /**
     * 조문 선택 드롭다운 채우기
     */
    populateArticleSelector(articles) {
        const selector = document.getElementById('imageArticleSelector');
        if (!selector) return;

        // 기존 옵션 제거 (첫 번째 "선택하세요" 제외)
        selector.innerHTML = '<option value="">조문을 선택하세요...</option>';

        // 조문 옵션 추가 (seq를 value로 사용!)
        articles.forEach(article => {
            if (article.번호 && article.seq) {
                const option = document.createElement('option');
                option.value = article.seq;  // seq를 value로!
                option.dataset.articleNumber = article.번호;  // 번호는 data attribute에 저장
                option.textContent = `${article.번호} - ${article.내용 ? article.내용.substring(0, 50) : ''}${article.내용 && article.내용.length > 50 ? '...' : ''}`;
                selector.appendChild(option);
            }
        });

        console.log('[ImageManager] Article selector populated with', articles.length, 'articles');
    },

    /**
     * 조문 선택 시 처리
     */
    onArticleSelected(articleSeq) {
        console.log('[ImageManager] Article seq selected:', articleSeq);
        this.currentArticleSeq = articleSeq;

        // 선택된 조문의 번호 가져오기
        const selector = document.getElementById('imageArticleSelector');
        const selectedOption = selector.options[selector.selectedIndex];
        this.currentArticleNumber = selectedOption ? selectedOption.dataset.articleNumber : null;

        console.log('[ImageManager] Article number:', this.currentArticleNumber);

        const uploadArea = document.getElementById('imageUploadArea');
        const noArticleMessage = document.getElementById('noArticleMessage');
        const imagesList = document.getElementById('imagesList');

        if (articleSeq) {
            uploadArea.style.display = 'block';
            noArticleMessage.style.display = 'none';
            this.renderImageList(articleSeq);
        } else {
            uploadArea.style.display = 'none';
            noArticleMessage.style.display = 'block';
            // 조문 미선택 시 이미지 목록 초기화
            if (imagesList) {
                imagesList.innerHTML = '';
            }
        }
    },

    /**
     * 파일 선택 시 처리
     */
    async onFilesSelected(files) {
        if (!this.currentArticleSeq) {
            alert('먼저 조문을 선택하세요.');
            return;
        }

        for (const file of files) {
            await this.uploadImage(this.currentArticleSeq, file);
        }
    },

    /**
     * 이미지 업로드
     */
    async uploadImage(articleSeq, file) {
        try {
            // 파일 타입 검증
            if (!file.type.startsWith('image/')) {
                alert(`${file.name}은(는) 이미지 파일이 아닙니다.`);
                return;
            }

            // 파일 크기 검증 (10MB)
            if (file.size > 10 * 1024 * 1024) {
                alert(`${file.name} 파일 크기가 10MB를 초과합니다.`);
                return;
            }

            console.log('[ImageManager] Uploading image:', file.name, 'to article seq:', articleSeq);

            const formData = new FormData();
            formData.append('wzruleseq', this.currentRuleId);
            formData.append('article_seq', articleSeq);  // seq 전달!
            formData.append('image', file);

            const response = await fetch('/api/v1/rule-enhanced/upload-image', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '이미지 업로드 실패');
            }

            const data = await response.json();
            console.log('[ImageManager] Image uploaded successfully:', data);

            alert(`✅ "${file.name}" 이미지가 업로드되었습니다.`);

            // 이미지 목록 다시 로드
            await this.loadImagesAndArticles();

        } catch (error) {
            console.error('[ImageManager] Error uploading image:', error);
            alert(`이미지 업로드 중 오류가 발생했습니다: ${error.message}`);
        }
    },

    /**
     * 이미지 삭제
     */
    async deleteImage(articleSeq, fileName) {
        if (!confirm(`"${fileName}" 이미지를 삭제하시겠습니까?`)) {
            return;
        }

        try {
            console.log('[ImageManager] Deleting image:', fileName, 'from article seq:', articleSeq);

            const response = await fetch('/api/v1/rule-enhanced/delete-image', {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    wzruleseq: this.currentRuleId,
                    article_seq: parseInt(articleSeq),  // seq 전달!
                    image_file_name: fileName
                }),
                credentials: 'include'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '이미지 삭제 실패');
            }

            console.log('[ImageManager] Image deleted successfully');
            alert('✅ 이미지가 삭제되었습니다.');

            // 이미지 목록 다시 로드
            await this.loadImagesAndArticles();

        } catch (error) {
            console.error('[ImageManager] Error deleting image:', error);
            alert(`이미지 삭제 중 오류가 발생했습니다: ${error.message}`);
        }
    },

    /**
     * 이미지 목록 렌더링
     */
    renderImageList(articleSeq) {
        const imagesList = document.getElementById('imagesList');
        if (!imagesList) return;

        const articleImages = this.images[articleSeq] || [];

        if (articleImages.length === 0) {
            imagesList.innerHTML = `
                <div style="grid-column: 1 / -1; padding: 40px; text-align: center; color: #6c757d;">
                    <p>등록된 이미지가 없습니다.</p>
                    <p style="font-size: 13px; margin-top: 10px;">위의 업로드 영역을 사용하여 이미지를 추가하세요.</p>
                </div>
            `;
            return;
        }

        // 이미지 카드 생성 (seq 사용!)
        imagesList.innerHTML = articleImages.map((img, index) => `
            <div style="border: 1px solid #dee2e6; border-radius: 8px; overflow: hidden; background: white;">
                <img id="img-${articleSeq}-${index}"
                     src="${img.file_path}?t=${Date.now()}"
                     alt="${img.title || img.file_name}"
                     onload="ImageManager.initImageSize('${articleSeq}', ${index})"
                     style="width: 100%; height: 150px; object-fit: contain; background: #f8f9fa; transition: height 0.2s;">
                <div style="padding: 10px;">
                    <p style="font-size: 13px; font-weight: 600; margin-bottom: 5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${img.file_name}">
                        ${img.title || img.file_name}
                    </p>
                    <p style="font-size: 11px; color: #6c757d; margin-bottom: 8px;">
                        순서: ${img.seq}
                    </p>

                    <!-- 현재 크기 표시 -->
                    <p id="current-size-${articleSeq}-${index}" style="font-size: 10px; color: #28a745; margin-bottom: 8px; font-weight: 600;">
                        📏 현재 크기: 로딩 중...
                    </p>

                    <!-- 크기 조절 슬라이더 -->
                    <div style="margin-bottom: 10px;">
                        <label style="font-size: 11px; color: #6c757d; display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                            <span>📐 새 크기 (너비)</span>
                            <span id="size-label-${articleSeq}-${index}" style="font-weight: 600; color: #667eea;">800px</span>
                        </label>
                        <input type="range"
                               id="size-slider-${articleSeq}-${index}"
                               class="image-size-slider"
                               min="200"
                               max="2000"
                               value="800"
                               step="50"
                               oninput="ImageManager.updateSizeLabel('${articleSeq}', ${index}, this.value)"
                               style="width: 100%; height: 6px; background: linear-gradient(to right, #667eea 0%, #667eea 33%, #dee2e6 33%, #dee2e6 100%); border-radius: 3px; outline: none; -webkit-appearance: none; cursor: pointer;">
                        <p style="font-size: 10px; color: #6c757d; margin-top: 4px;">
                            💡 슬라이더로 원하는 크기 선택 후 "크기 저장" 버튼 클릭
                        </p>
                    </div>

                    <!-- 버튼 그룹 -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 6px;">
                        <button onclick="ImageManager.viewFullSize('${img.file_path}', '${img.file_name}')"
                                style="padding: 6px; border: 1px solid #667eea; background: white; color: #667eea; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 600; transition: all 0.2s;">
                            🔍 원본보기
                        </button>
                        <button onclick="ImageManager.saveResizedImage('${articleSeq}', ${index}, '${img.file_name}')"
                                style="padding: 6px; border: 1px solid #28a745; background: white; color: #28a745; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 600; transition: all 0.2s;">
                            💾 크기 저장
                        </button>
                    </div>

                    <button onclick="ImageManager.deleteImage('${articleSeq}', '${img.file_name}')"
                            style="width: 100%; padding: 6px; border: 1px solid #dc3545; background: white; color: #dc3545; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.2s;">
                        🗑️ 삭제
                    </button>
                </div>
            </div>
        `).join('');
    },

    /**
     * 이미지 로드 시 실제 크기 초기화
     */
    initImageSize(articleSeq, index) {
        const img = document.getElementById(`img-${articleSeq}-${index}`);
        const currentSizeLabel = document.getElementById(`current-size-${articleSeq}-${index}`);
        const slider = document.getElementById(`size-slider-${articleSeq}-${index}`);
        const sizeLabel = document.getElementById(`size-label-${articleSeq}-${index}`);

        if (img && img.naturalWidth) {
            const actualWidth = img.naturalWidth;
            const actualHeight = img.naturalHeight;

            // 현재 크기 표시
            if (currentSizeLabel) {
                currentSizeLabel.textContent = `📏 현재 크기: ${actualWidth} x ${actualHeight}px`;
            }

            // 슬라이더 초기값을 실제 너비로 설정
            if (slider && sizeLabel) {
                slider.value = actualWidth;
                sizeLabel.textContent = `${actualWidth}px`;

                // 슬라이더 progress bar 업데이트
                const min = parseInt(slider.min);
                const max = parseInt(slider.max);
                const percentage = ((actualWidth - min) / (max - min)) * 100;
                slider.style.background = `linear-gradient(to right, #667eea 0%, #667eea ${percentage}%, #dee2e6 ${percentage}%, #dee2e6 100%)`;
            }
        }
    },

    /**
     * 슬라이더 레이블 업데이트
     */
    updateSizeLabel(articleSeq, index, size) {
        const label = document.getElementById(`size-label-${articleSeq}-${index}`);
        const slider = document.getElementById(`size-slider-${articleSeq}-${index}`);

        if (label) {
            label.textContent = `${size}px`;
        }

        // 슬라이더 progress bar 업데이트
        if (slider) {
            const min = parseInt(slider.min);
            const max = parseInt(slider.max);
            const percentage = ((size - min) / (max - min)) * 100;
            slider.style.background = `linear-gradient(to right, #667eea 0%, #667eea ${percentage}%, #dee2e6 ${percentage}%, #dee2e6 100%)`;
        }
    },

    /**
     * 이미지 크기 저장 (실제 파일 리사이즈)
     */
    async saveResizedImage(articleSeq, index, fileName) {
        const slider = document.getElementById(`size-slider-${articleSeq}-${index}`);
        if (!slider) {
            alert('크기 조정 슬라이더를 찾을 수 없습니다.');
            return;
        }

        const targetWidth = parseInt(slider.value);

        // 확인 메시지
        if (!confirm(`이미지를 ${targetWidth}px 너비로 리사이즈하시겠습니까?\n\n⚠️ 원본은 .backup 폴더에 백업됩니다.\n비율은 자동으로 유지됩니다.`)) {
            return;
        }

        try {
            const response = await fetch('/api/v1/rule-enhanced/resize-image', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    wzruleseq: this.currentRuleId,
                    article_seq: articleSeq,
                    image_file_name: fileName,
                    width: targetWidth
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                alert(`✅ 이미지 크기가 성공적으로 조정되었습니다!\n\n` +
                      `원본: ${result.image.original_size.width} x ${result.image.original_size.height}\n` +
                      `조정: ${result.image.new_size.width} x ${result.image.new_size.height}\n\n` +
                      `저장된 경로: ${result.image.saved_paths}개 위치`);

                // 이미지 목록 새로고침
                await this.loadImagesAndArticles();
                this.renderImageList(articleSeq);
            } else {
                throw new Error(result.detail || result.message || '이미지 크기 조정 실패');
            }
        } catch (error) {
            console.error('Image resize error:', error);
            alert(`❌ 이미지 크기 조정 중 오류가 발생했습니다.\n\n${error.message}`);
        }
    },

    /**
     * 원본 크기로 이미지 보기 (새 창)
     */
    viewFullSize(imagePath, fileName) {
        // 모달 생성
        const modal = document.createElement('div');
        modal.id = 'fullSizeImageModal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            cursor: zoom-out;
        `;

        modal.innerHTML = `
            <div style="position: relative; max-width: 95%; max-height: 95%; display: flex; flex-direction: column;">
                <div style="background: white; padding: 10px 20px; border-radius: 8px 8px 0 0; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 600; color: #333;">${fileName}</span>
                    <button onclick="document.getElementById('fullSizeImageModal').remove()"
                            style="background: #dc3545; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer; font-weight: 600;">
                        ✕ 닫기
                    </button>
                </div>
                <img src="${imagePath}"
                     style="max-width: 100%; max-height: calc(95vh - 60px); object-fit: contain; background: white; border-radius: 0 0 8px 8px;"
                     onclick="event.stopPropagation();">
            </div>
        `;

        // 모달 클릭 시 닫기
        modal.addEventListener('click', () => {
            modal.remove();
        });

        document.body.appendChild(modal);
    },

    /**
     * 드래그 앤 드롭 설정
     */
    setupDragDrop() {
        const dropZone = document.getElementById('imageDropZone');
        if (!dropZone) return;

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.style.borderColor = '#667eea';
            dropZone.style.background = '#e7f1ff';
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.style.borderColor = '#dee2e6';
            dropZone.style.background = '#f8f9fa';
        });

        dropZone.addEventListener('drop', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.style.borderColor = '#dee2e6';
            dropZone.style.background = '#f8f9fa';

            if (!this.currentArticleSeq) {
                alert('먼저 조문을 선택하세요.');
                return;
            }

            const files = e.dataTransfer.files;
            for (const file of files) {
                if (file.type.startsWith('image/')) {
                    await this.uploadImage(this.currentArticleSeq, file);
                }
            }
        });
    }
};

// 전역으로 노출
window.ImageManager = ImageManager;
