/**
 * KB신용정보 내규 시스템 - 사이드바 모듈
 * @module kbregulation_sidebar
 */

import { AppState, highlightText } from './kbregulation_common.js';

// ============================================
// 사이드바 상태
// ============================================

let departmentTreeData = null;
let currentDepartmentSearch = '';

// ============================================
// 사이드바 토글
// ============================================

/**
 * 사이드바 토글
 */
export function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.querySelector('.overlay');

    if (sidebar) {
        sidebar.classList.toggle('active');
    }
    if (overlay) {
        overlay.classList.toggle('active');
    }
}

/**
 * 사이드바 닫기
 */
export function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.querySelector('.overlay');

    if (sidebar) {
        sidebar.classList.remove('active');
    }
    if (overlay) {
        overlay.classList.remove('active');
    }
}

// ============================================
// 트리 메뉴 생성
// ============================================

/**
 * 트리 메뉴 생성
 */
export function generateTreeMenu() {
    const treeMenu = document.getElementById('treeMenu');
    if (!treeMenu) return;

    // 기존 내용 초기화
    treeMenu.innerHTML = '';

    Object.entries(AppState.hospitalRegulations).forEach(([chapter, chapterData]) => {
        const treeItem = document.createElement('div');
        treeItem.className = 'tree-item';

        const treeHeader = document.createElement('div');
        treeHeader.className = 'tree-header';
        treeHeader.innerHTML = `
            <span>${chapter}. ${chapterData.title}</span>
            <i class="fas fa-chevron-right tree-icon"></i>
        `;
        treeHeader.onclick = () => toggleTreeItem(treeHeader, chapter);

        const treeChildren = document.createElement('div');
        treeChildren.className = 'tree-children';

        if (chapterData.regulations) {
            chapterData.regulations.forEach(regulation => {
                const childNode = document.createElement('div');
                childNode.className = 'tree-child';
                if (regulation.appendix && regulation.appendix.length > 0) {
                    childNode.classList.add('has-appendix');
                }
                childNode.textContent = `${regulation.code}. ${regulation.name}`;
                childNode.onclick = async (event) => {
                    event.stopPropagation();
                    await selectRegulation(regulation, chapter, childNode);
                };

                treeChildren.appendChild(childNode);

                // 부록이 있는 경우 서브 레벨 추가
                if (regulation.appendix && regulation.appendix.length > 0) {
                    const subChildren = document.createElement('div');
                    subChildren.className = 'tree-sub-children';

                    // 안전한 부록 처리
                    let safeAppendixArray = [];

                    if (Array.isArray(regulation.appendix)) {
                        safeAppendixArray = regulation.appendix;
                    } else if (typeof regulation.appendix === 'string') {
                        safeAppendixArray = [regulation.appendix];
                    } else if (typeof regulation.appendix === 'object' && regulation.appendix !== null) {
                        try {
                            safeAppendixArray = Object.values(regulation.appendix).filter(item => item != null);
                        } catch (error) {
                            console.error(`부록 변환 실패 - ${regulation.code}:`, error);
                            safeAppendixArray = [];
                        }
                    }

                    // 부록 아이템 생성
                    safeAppendixArray.forEach((appendixItem, index) => {
                        // 유효성 검사
                        if (!appendixItem || typeof appendixItem !== 'string') {
                            console.warn(`유효하지 않은 부록 아이템 - ${regulation.code}[${index}]:`, appendixItem);
                            return;
                        }

                        const subChild = document.createElement('div');
                        subChild.className = 'tree-sub-child';

                        // 텍스트에서 중복된 번호 제거
                        const cleanAppendixItem = appendixItem.replace(/^\d+\.\s*/, '');
                        subChild.textContent = `부록 ${index + 1}. ${cleanAppendixItem}`;

                        // 부록 클릭 시 PDF 열기
                        subChild.onclick = (event) => {
                            event.stopPropagation();
                            if (typeof window.openAppendixPdf === 'function') {
                                window.openAppendixPdf(regulation.code, index, cleanAppendixItem);
                            }
                        };

                        subChildren.appendChild(subChild);
                    });

                    // has-appendix 클래스가 있으면 DOM 구조를 위해 항상 추가
                    treeChildren.appendChild(subChildren);
                }
            });
        }

        treeItem.appendChild(treeHeader);
        treeItem.appendChild(treeChildren);
        treeMenu.appendChild(treeItem);
    });
}

/**
 * 트리 아이템 토글
 */
export function toggleTreeItem(header, chapter) {
    const children = header.nextElementSibling;
    const isOpen = children.classList.contains('open');
    const treeMenu = document.getElementById('treeMenu');
    const icon = header.querySelector('i.tree-icon');

    if (!isOpen) {
        // 클릭한 아이템 열기
        children.classList.add('open');
        header.classList.add('active');
        if (icon) {
            icon.classList.remove('fa-chevron-right');
            icon.classList.add('fa-chevron-down');
        }

        // 클릭한 장으로 스크롤 이동
        setTimeout(() => {
            if (treeMenu && header) {
                const treeItem = header.parentElement;
                const targetScrollPosition = treeItem.offsetTop;

                treeMenu.scrollTo({
                    top: targetScrollPosition - 20,
                    behavior: 'smooth'
                });
            }
        }, 100);
    } else {
        // 클릭한 아이템 닫기
        children.classList.remove('open');
        header.classList.remove('active');
        if (icon) {
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-right');
        }
    }
}

// ============================================
// 규정 선택
// ============================================

/**
 * 규정 선택
 */
export async function selectRegulation(regulation, chapter, element) {
    // 모바일에서는 sidebar 자동으로 닫기
    const isMobile = window.innerWidth <= 768;
    if (isMobile) {
        closeSidebar();
    }

    // 현재 요소가 이미 active인지 확인
    const isCurrentlyActive = element.classList.contains('active');

    // 부록 관련 요소들
    const hasAppendix = regulation.appendix && regulation.appendix.length > 0;
    const subChildren = hasAppendix ? element.nextElementSibling : null;
    const isCurrentlyOpen = subChildren && subChildren.classList.contains('open');

    // Case 1: 부록이 있고, 이미 선택된 내규를 다시 클릭한 경우 (토글)
    if (hasAppendix && isCurrentlyActive && subChildren) {
        if (isCurrentlyOpen) {
            // 부록 닫기
            subChildren.classList.remove('open');
            subChildren.style.display = 'none';
            element.classList.remove('expanded');
        } else {
            // 부록 열기
            subChildren.classList.add('open');
            subChildren.style.display = 'block';
            element.classList.add('expanded');
        }
        return; // 상세보기는 다시 호출하지 않음
    }

    // Case 2: 새로운 내규 선택 또는 부록이 없는 내규

    // 모든 기존 선택 해제
    document.querySelectorAll('.tree-child.active').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });

    // 현재 선택 표시
    element.classList.add('active');

    // 부록이 있는 경우 처리
    if (hasAppendix && subChildren) {
        // 다른 모든 부록들 닫기
        document.querySelectorAll('.tree-sub-children').forEach(sub => {
            if (sub !== subChildren) {
                sub.classList.remove('open');
                sub.style.display = 'none';
            }
        });
        document.querySelectorAll('.has-appendix').forEach(hasApp => {
            if (hasApp !== element) {
                hasApp.classList.remove('expanded');
            }
        });

        // 현재 부록 열기
        subChildren.classList.add('open');
        subChildren.style.display = 'block';
        element.classList.add('expanded');
    }

    // 규정 상세 표시
    if (typeof window.showRegulationDetail === 'function') {
        await window.showRegulationDetail(regulation, chapter);
    }
}

/**
 * 사이드바 활성 상태 업데이트
 */
export function updateSidebarActiveState(regulation, chapter) {
    // 모든 활성 상태 제거
    document.querySelectorAll('.tree-child.active').forEach(child => {
        child.classList.remove('active');
    });
    document.querySelectorAll('.tree-sub-child.active').forEach(subChild => {
        subChild.classList.remove('active');
    });

    // 해당 챕터 펼치기
    const treeItems = document.querySelectorAll('.tree-item');
    treeItems.forEach(item => {
        const header = item.querySelector('.tree-header');
        const title = header?.querySelector('.tree-title')?.textContent || '';

        if (title.startsWith(`${chapter}.`)) {
            const children = item.querySelector('.tree-children');
            if (children) {
                children.style.display = 'block';
            }

            // 아이콘 업데이트
            const arrow = header.querySelector('.tree-arrow i');
            const icon = header.querySelector('.tree-icon i');
            if (arrow) {
                arrow.classList.remove('fa-chevron-right');
                arrow.classList.add('fa-chevron-down');
            }
            if (icon) {
                icon.classList.remove('fa-folder');
                icon.classList.add('fa-folder-open');
            }

            // 해당 규정 활성화
            const regChildren = item.querySelectorAll('.tree-child');
            regChildren.forEach(child => {
                const childTitle = child.querySelector('.tree-child-title')?.textContent || '';
                if (childTitle.startsWith(`${regulation.code}.`)) {
                    child.classList.add('active');
                    child.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            });
        }
    });
}

// ============================================
// 사이드 탭 전환
// ============================================

/**
 * 사이드 탭 전환
 */
export function switchSideTab(tabType, clickedTab) {
    // 탭 활성화 상태 업데이트
    document.querySelectorAll('.side-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.type === tabType);
    });

    // 컨텐츠 전환
    if (tabType === 'side_category') {
        showCategoryTree();
    } else if (tabType === 'side_dep') {
        showDepartmentTree();
    }
}

/**
 * 분류 트리 표시
 */
export function showCategoryTree() {
    const treeMenu = document.getElementById('treeMenu');
    if (treeMenu) {
        treeMenu.style.display = 'block';
    }

    const deptTree = document.getElementById('departmentTree');
    if (deptTree) {
        deptTree.style.display = 'none';
    }

    generateTreeMenu();
}

/**
 * 부서 트리 표시
 */
export function showDepartmentTree() {
    const treeMenu = document.getElementById('treeMenu');
    if (treeMenu) {
        treeMenu.style.display = 'none';
    }

    let deptTree = document.getElementById('departmentTree');
    if (!deptTree) {
        deptTree = document.createElement('div');
        deptTree.id = 'departmentTree';
        deptTree.className = 'tree-menu';
        treeMenu.parentNode.insertBefore(deptTree, treeMenu.nextSibling);
    }

    deptTree.style.display = 'block';
    renderDepartmentTree();
}

/**
 * 부서 트리 렌더링
 */
export function renderDepartmentTree(filteredDepartments = null) {
    const container = document.getElementById('departmentTree');
    if (!container) return;

    // 부서 데이터 구축
    if (!departmentTreeData) {
        departmentTreeData = buildDepartmentTreeData();
    }

    const departments = filteredDepartments || departmentTreeData;

    let html = `
        <div class="department-search">
            <input type="text" id="deptSearchInput" placeholder="부서명 검색..."
                   onkeyup="filterDepartmentTree(this.value)">
            <button onclick="clearDepartmentSearch()"><i class="fas fa-times"></i></button>
        </div>
        <div class="department-tree-content">
    `;

    Object.entries(departments).forEach(([deptName, regulations]) => {
        html += `
            <div class="tree-item">
                <div class="tree-header" onclick="toggleDepartmentItem(this)">
                    <span class="tree-icon"><i class="fas fa-building"></i></span>
                    <span class="tree-title">${deptName}</span>
                    <span class="tree-count">${regulations.length}</span>
                    <span class="tree-arrow"><i class="fas fa-chevron-right"></i></span>
                </div>
                <div class="tree-children" style="display: none;">
                    ${regulations.map(reg => `
                        <div class="tree-child"
                             onclick="selectDepartmentRegulation(hospitalRegulations['${reg.chapter}'].regulations.find(r => r.code === '${reg.code}'), '${reg.chapter}', this)">
                            <span class="tree-child-icon"><i class="fas fa-file-alt"></i></span>
                            <span class="tree-child-title">${reg.code}. ${reg.name}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;
}

/**
 * 부서 트리 데이터 구축
 */
export function buildDepartmentTreeData() {
    const deptData = {};

    Object.entries(AppState.hospitalRegulations).forEach(([chapter, chapterData]) => {
        if (chapterData.regulations) {
            chapterData.regulations.forEach(reg => {
                const dept = reg.detail?.documentInfo?.소관부서 ||
                            reg.detailData?.문서정보?.소관부서 ||
                            '미지정';

                // 부서명 분리 (쉼표로 구분된 경우)
                const depts = dept.split(/[,，]/).map(d => d.trim()).filter(d => d);

                depts.forEach(deptName => {
                    if (!deptData[deptName]) {
                        deptData[deptName] = [];
                    }
                    deptData[deptName].push({
                        code: reg.code,
                        name: reg.name,
                        chapter: chapter
                    });
                });
            });
        }
    });

    // 정렬
    return Object.fromEntries(
        Object.entries(deptData).sort((a, b) => a[0].localeCompare(b[0], 'ko'))
    );
}

/**
 * 부서 트리 필터링
 */
export function filterDepartmentTree(searchTerm) {
    currentDepartmentSearch = searchTerm.toLowerCase();

    if (!searchTerm) {
        renderDepartmentTree();
        return;
    }

    const filtered = {};
    Object.entries(departmentTreeData).forEach(([deptName, regulations]) => {
        if (deptName.toLowerCase().includes(currentDepartmentSearch)) {
            filtered[deptName] = regulations;
        }
    });

    renderDepartmentTree(filtered);
}

/**
 * 부서 검색 초기화
 */
export function clearDepartmentSearch() {
    const input = document.getElementById('deptSearchInput');
    if (input) {
        input.value = '';
    }
    currentDepartmentSearch = '';
    renderDepartmentTree();
}

/**
 * 부서 아이템 토글
 */
export function toggleDepartmentItem(header) {
    const treeItem = header.parentElement;
    const children = treeItem.querySelector('.tree-children');
    const arrow = header.querySelector('.tree-arrow i');
    const icon = header.querySelector('.tree-icon i');

    if (children) {
        const isExpanded = children.style.display !== 'none';
        children.style.display = isExpanded ? 'none' : 'block';

        if (arrow) {
            arrow.classList.toggle('fa-chevron-right', isExpanded);
            arrow.classList.toggle('fa-chevron-down', !isExpanded);
        }
        if (icon) {
            icon.classList.toggle('fa-building', isExpanded);
            icon.classList.toggle('fa-building-user', !isExpanded);
        }
    }
}

/**
 * 부서 규정 선택
 */
export function selectDepartmentRegulation(regulation, chapter, element) {
    selectRegulation(regulation, chapter, element);
}

// ============================================
// 전역 노출
// ============================================
if (typeof window !== 'undefined') {
    window.toggleSidebar = toggleSidebar;
    window.closeSidebar = closeSidebar;
    window.generateTreeMenu = generateTreeMenu;
    window.toggleTreeItem = toggleTreeItem;
    window.selectRegulation = selectRegulation;
    window.updateSidebarActiveState = updateSidebarActiveState;
    window.switchSideTab = switchSideTab;
    window.showCategoryTree = showCategoryTree;
    window.showDepartmentTree = showDepartmentTree;
    window.renderDepartmentTree = renderDepartmentTree;
    window.buildDepartmentTreeData = buildDepartmentTreeData;
    window.filterDepartmentTree = filterDepartmentTree;
    window.clearDepartmentSearch = clearDepartmentSearch;
    window.toggleDepartmentItem = toggleDepartmentItem;
    window.selectDepartmentRegulation = selectDepartmentRegulation;
}
