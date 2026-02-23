/**
 * KB신용정보 내규 시스템 - 워터마크 모듈
 * @module kbregulation_watermark
 */

import { AppState } from './kbregulation_common.js';

// ============================================
// 워터마크 설정
// ============================================

export const WatermarkConfig = {
    enabled: true,
    opacity: 0.08,
    fontSize: 14,
    rotation: -30,
    spacing: { x: 60, y: 40 }
};

// ============================================
// 워터마크 함수
// ============================================

/**
 * 사용자 정보로 워터마크 텍스트 생성
 */
export function createWatermarkText(userInfo) {
    const name = userInfo.name || '사용자';
    const empNo = userInfo.empNo || userInfo.employeeNumber || '';
    const dept = userInfo.dept || userInfo.department || '';
    const timestamp = new Date().toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });

    let text = name;
    if (empNo) text += ` (${empNo})`;
    if (dept) text += `\n${dept}`;
    text += `\n${timestamp}`;

    return text;
}

/**
 * 워터마크 HTML 요소 생성
 */
export function createWatermarkElement(text, repeatCount = 100) {
    // 기존 워터마크 제거
    const existingWatermark = document.querySelector('.watermark-overlay');
    if (existingWatermark) {
        existingWatermark.remove();
    }

    // 워터마크 오버레이 생성
    const overlay = document.createElement('div');
    overlay.className = 'watermark-overlay';
    overlay.style.opacity = WatermarkConfig.opacity;

    // 워터마크 패턴 생성
    const pattern = document.createElement('div');
    pattern.className = 'watermark-pattern';
    pattern.style.transform = `rotate(${WatermarkConfig.rotation}deg)`;

    // 워터마크 아이템 반복 생성
    for (let i = 0; i < repeatCount; i++) {
        const item = document.createElement('div');
        item.className = 'watermark-item';
        item.style.fontSize = `${WatermarkConfig.fontSize}px`;
        item.style.padding = `${WatermarkConfig.spacing.y}px ${WatermarkConfig.spacing.x}px`;
        item.innerHTML = text.replace(/\n/g, '<br>');
        pattern.appendChild(item);
    }

    overlay.appendChild(pattern);
    return overlay;
}

/**
 * 특정 컨테이너에 워터마크 적용
 */
export function applyWatermark(container, userInfo) {
    if (!WatermarkConfig.enabled) return;

    const containerEl = typeof container === 'string'
        ? document.querySelector(container)
        : container;

    if (!containerEl) {
        console.warn('워터마크 컨테이너를 찾을 수 없습니다:', container);
        return;
    }

    // 컨테이너에 워터마크 클래스 추가
    containerEl.classList.add('watermark-container');

    // 기존 내용을 워터마크 컨텐츠로 감싸기
    if (!containerEl.querySelector('.watermark-content')) {
        const content = document.createElement('div');
        content.className = 'watermark-content';
        while (containerEl.firstChild) {
            content.appendChild(containerEl.firstChild);
        }
        containerEl.appendChild(content);
    }

    // 워터마크 텍스트 생성
    const watermarkText = createWatermarkText(userInfo);

    // 워터마크 요소 생성 및 추가
    const watermarkEl = createWatermarkElement(watermarkText);
    containerEl.insertBefore(watermarkEl, containerEl.firstChild);
}

/**
 * 워터마크 제거
 */
export function removeWatermark(container) {
    const containerEl = typeof container === 'string'
        ? document.querySelector(container)
        : container;

    if (!containerEl) return;

    const overlay = containerEl.querySelector('.watermark-overlay');
    if (overlay) {
        overlay.remove();
    }
    containerEl.classList.remove('watermark-container');
}

/**
 * 워터마크 활성화/비활성화 토글
 */
export function toggleWatermark(enabled) {
    WatermarkConfig.enabled = enabled;
    const containers = document.querySelectorAll('.watermark-container');
    containers.forEach(container => {
        if (enabled) {
            container.classList.remove('watermark-disabled');
        } else {
            container.classList.add('watermark-disabled');
        }
    });
}

/**
 * 워터마크 설정 업데이트
 */
export function updateWatermarkConfig(config) {
    Object.assign(WatermarkConfig, config);
}

/**
 * 사용자 정보 설정
 */
export function setUserInfo(userInfo) {
    AppState.currentUserInfo = userInfo;
    console.log('사용자 정보 설정됨:', userInfo.name);
}

/**
 * 규정 본문에 워터마크 자동 적용
 */
export function applyWatermarkToContent() {
    if (!AppState.currentUserInfo) {
        console.log('사용자 정보가 없어 워터마크를 적용하지 않습니다.');
        return;
    }

    const contentBody = document.getElementById('contentBody');
    if (contentBody && contentBody.style.display !== 'none') {
        applyWatermark(contentBody, AppState.currentUserInfo);
    }
}

// ============================================
// 전역 노출
// ============================================
if (typeof window !== 'undefined') {
    window.WatermarkConfig = WatermarkConfig;
    window.createWatermarkText = createWatermarkText;
    window.createWatermarkElement = createWatermarkElement;
    window.applyWatermark = applyWatermark;
    window.removeWatermark = removeWatermark;
    window.toggleWatermark = toggleWatermark;
    window.updateWatermarkConfig = updateWatermarkConfig;
    window.setUserInfo = setUserInfo;
    window.applyWatermarkToContent = applyWatermarkToContent;
}
