# JSON 편집 기능 수동 테스트 가이드

## 구현 완료 내역

### 1. 프론트엔드 수정 (`/static/js/rule-editor.js`)

#### 1.1 `convertJsonToEditableText()` 수정 (line ~1188)
- **필수 기능 구현:**
  - ✅ `═══ 조문 구분선 ═══` 구분자 추가 (빈 줄 문제 해결)
  - ✅ `###` 주석 마커 (충돌 방지)
  - ✅ 안내 메시지 추가

```javascript
convertJsonToEditableText(jsonContent) {
    const SEPARATOR = '═══ 조문 구분선 ═══';
    let text = '### ⚠️ 조문의 내용만 수정하세요 (개수와 순서 유지 필수)\n\n';

    if (jsonContent && jsonContent.조문내용) {
        jsonContent.조문내용.forEach((article) => {
            if (article.번호) {
                text += `### ${article.번호}\n${article.내용}\n${SEPARATOR}\n\n`;
            } else {
                text += `${article.내용}\n${SEPARATOR}\n\n`;
            }
        });
    }
    return text.trim();
}
```

#### 1.2 `convertTextToJson()` 신규 추가 (line ~1204)
- **필수 기능 구현:**
  - ✅ 개행 정규화 (`\r\n` → `\n`)
  - ✅ 주석 제거 (`###` 라인 제거)
  - ✅ 구분선 기반 파싱
  - ✅ 조문 개수 검증
  - ✅ 구조 100% 보존 (seq, 레벨, 관련이미지 등 모두 유지)

```javascript
convertTextToJson(editedText, originalJson) {
    const updatedJson = JSON.parse(JSON.stringify(originalJson));

    // 개행 정규화 (필수)
    const normalized = editedText.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

    // 주석 제거 (### 형식만)
    const cleaned = normalized.replace(/^###[^\n]*\n/gm, '').trim();

    // 구분선으로 분리 (필수 - 빈 줄 문제 해결)
    const SEPARATOR = '═══ 조문 구분선 ═══';
    const contents = cleaned.split(SEPARATOR)
        .map(c => c.trim())
        .filter(c => c.length > 0);

    // 개수 검증
    const originalCount = updatedJson.조문내용.length;
    if (contents.length !== originalCount) {
        alert(`조문 개수 불일치!\n원본: ${originalCount}개\n현재: ${contents.length}개`);
        return null;
    }

    // 내용만 순서대로 교체 (구조 100% 보존)
    contents.forEach((content, index) => {
        if (updatedJson.조문내용[index]) {
            updatedJson.조문내용[index].내용 = content;
        }
    });

    return updatedJson;
}
```

#### 1.3 `saveContent()` 수정 (line ~1107)
- **변경 사항:**
  - ✅ 새 API 엔드포인트 호출: `PUT /api/v1/rule/update-json/{rule_id}`
  - ✅ `convertTextToJson()` 호출
  - ✅ 검증 실패 시 저장 중단
  - ✅ 메모리 동기화 (`this.existingJsonContent` 업데이트)

```javascript
async saveContent() {
    try {
        const editedText = document.getElementById('contentEditor').value;

        if (!this.existingJsonContent) {
            this.showNotification('기존 JSON이 없습니다', 'error');
            return;
        }

        const updatedJson = this.convertTextToJson(editedText, this.existingJsonContent);
        if (!updatedJson) return; // 검증 실패

        const response = await fetch(`/api/v1/rule/update-json/${this.currentRule.wzruleseq}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ json_data: updatedJson })
        });

        if (!response.ok) {
            throw new Error('내용 저장에 실패했습니다.');
        }

        const result = await response.json();
        if (result.success) {
            this.existingJsonContent = updatedJson; // 메모리 동기화
            this.showNotification('✅ 저장 완료', 'success');
            setTimeout(() => {
                this.closeModal();
                this.loadRegulations();
            }, 1500);
        }
    } catch (error) {
        console.error('[RuleEditor] Save content error:', error);
        this.showNotification(`❌ 저장 실패: ${error.message}`, 'error');
    }
}
```

### 2. 백엔드 수정 (`/api/service_rule_editor.py`)

#### 2.1 `PUT /update-json/{rule_id}` 신규 추가 (line ~2923)
- **필수 기능 구현:**
  - ✅ 기존 JSON 파일 덮어쓰기
  - ✅ 백업 파일 자동 생성 (`.backup`)
  - ✅ `ensure_ascii=False` 인코딩 (한글 보존)
  - ✅ `content_text` 동기화
  - ✅ 인증 필수 (`get_current_user`)

```python
@router.put("/update-json/{rule_id}")
async def update_existing_json(
    rule_id: int,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """기존 JSON 파일 덮어쓰기 (필수 기능만)"""
    try:
        data = await request.json()
        updated_json = data.get('json_data')

        if not updated_json:
            raise HTTPException(status_code=400, detail="JSON 데이터 없음")

        # DB 연결
        db_config = {...}
        db_manager = DatabaseConnectionManager(**db_config)

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # JSON 파일 경로 조회
                cur.execute("SELECT wzFileJson FROM wz_rule WHERE wzruleseq = %s", (rule_id,))
                row = cur.fetchone()

                if not row or not row[0]:
                    raise HTTPException(status_code=404, detail="JSON 경로 없음")

                json_path = row[0]

                if not os.path.exists(json_path):
                    raise HTTPException(status_code=404, detail="파일 없음")

                # 백업 (필수)
                backup_path = json_path + '.backup'
                shutil.copy2(json_path, backup_path)

                # 덮어쓰기 (필수: ensure_ascii=False)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(updated_json, f, ensure_ascii=False, indent=2)

                # content_text 동기화
                text_content = ""
                for article in updated_json.get('조문내용', []):
                    if article.get('번호'):
                        text_content += f"{article['번호']} {article['내용']}\n\n"

                cur.execute("""
                    UPDATE wz_rule
                    SET content_text = %s, wzModifiedBy = %s
                    WHERE wzruleseq = %s
                """, (text_content.strip(), user.get('username'), rule_id))

                conn.commit()

                return {
                    "success": True,
                    "message": "JSON 업데이트 완료",
                    "articles_count": len(updated_json.get('조문내용', []))
                }
    except Exception as e:
        logger.error(f"Error updating JSON: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

## 테스트 시나리오

### 시나리오 1: 기본 텍스트 편집
1. http://localhost:8800 접속
2. 관리자 로그인 (admin / admin123!@#)
3. 규정 목록에서 아무 규정이나 선택
4. "편집" 버튼 클릭
5. "내용편집" 탭 클릭
6. **확인사항:**
   - ✅ `### ⚠️ 조문의 내용만 수정하세요` 안내 문구 표시
   - ✅ 조문마다 `### 제1조`, `### 제2조` 형식의 주석
   - ✅ 조문 사이에 `═══ 조문 구분선 ═══` 표시
7. 첫 번째 조문의 내용 일부 수정 (예: "[테스트]" 추가)
8. "저장" 버튼 클릭
9. **확인사항:**
   - ✅ "✅ 저장 완료" 알림 표시
   - ✅ 모달 자동 닫힘
   - ✅ 목록 새로고침

### 시나리오 2: 구조 보존 확인
1. 규정 편집 모달 다시 열기
2. "내용편집" 탭에서 JSON 내용 확인
3. **확인사항:**
   - ✅ 수정한 내용이 반영됨
   - ✅ 조문 개수 동일
   - ✅ 조문 순서 유지
4. 브라우저 개발자도구 → Network 탭 열기
5. 수정 후 저장 클릭
6. `update-json` API 응답 확인
7. **확인사항:**
   - ✅ `"success": true`
   - ✅ `"articles_count"`: 원래 개수와 동일

### 시나리오 3: 검증 기능 테스트
1. 규정 편집 → 내용편집 탭
2. **테스트 A: 조문 삭제 시도**
   - 첫 번째 조문을 통째로 삭제 (구분선 포함)
   - 저장 클릭
   - **기대 결과:** "조문 개수 불일치!" 알림 표시

3. **테스트 B: 조문 추가 시도**
   - 마지막에 새로운 조문 추가
   - 저장 클릭
   - **기대 결과:** "조문 개수 불일치!" 알림 표시

4. **테스트 C: 빈 줄 포함 내용 수정**
   - 조문 내용에 빈 줄 여러 개 추가
   - 저장 클릭
   - **기대 결과:** 정상 저장 (빈 줄도 내용의 일부로 보존)

### 시나리오 4: 특수 문자 처리
1. 규정 편집 → 내용편집
2. 조문 내용에 다음 추가:
   ```
   특수문자 테스트: # @ $ % ^ & * < > / \ " '
   한글: 가나다라마바사
   이모지: 😀 ✅ ❌
   ```
3. 저장 클릭
4. **확인사항:**
   - ✅ 모든 특수문자 정상 저장
   - ✅ 한글 정상 저장
   - ✅ 이모지 정상 저장 (ensure_ascii=False 덕분)

### 시나리오 5: 백업 파일 확인
1. 터미널에서 다음 명령 실행:
```bash
# wz_rule 테이블에서 JSON 파일 경로 조회
PGPASSWORD='<비밀번호>' psql -h localhost -p 35432 -U severance -d severance \
  -c "SELECT wzruleseq, wzfilejson FROM wz_rule WHERE wzfilejson IS NOT NULL LIMIT 1;"
```

2. 조회된 경로로 백업 파일 확인:
```bash
ls -lh /path/to/json/file.json*
# 기대 결과:
# file.json        (원본)
# file.json.backup (백업)
```

3. **확인사항:**
   - ✅ `.backup` 파일 존재
   - ✅ 백업 파일 크기 > 0

## 필수 기능 체크리스트

### Phase 1 (현재 구현 완료)
- ✅ **빈 줄 구분자**: `═══ 조문 구분선 ═══` 사용
- ✅ **주석 충돌 방지**: `###` 주석 마커 사용
- ✅ **개행 정규화**: `\r\n` → `\n` 변환
- ✅ **백엔드 인코딩**: `ensure_ascii=False`
- ✅ **구조 보존**: seq, 레벨, 관련이미지 등 모든 필드 유지
- ✅ **조문 개수 검증**: 원본과 편집본 개수 비교
- ✅ **백업 생성**: 자동 `.backup` 파일 생성

### Phase 2 (선택 사항 - 추후 구현 가능)
- ⏸️ 동시 편집 감지 (optimistic locking)
- ⏸️ 백업 파일 관리 (주기적 정리)
- ⏸️ 조문 추가/삭제 지원
- ⏸️ Undo/Redo 기능
- ⏸️ 대용량 문서 최적화

## 문제 발생 시 확인사항

### 1. 저장이 안 될 때
- 브라우저 콘솔 확인: F12 → Console
- 네트워크 탭 확인: F12 → Network → update-json 요청
- 서버 로그 확인: `/home/wizice/regulation/fastapi/logs/app.log`

### 2. 한글이 깨질 때
- `ensure_ascii=False` 설정 확인 (service_rule_editor.py:2965)
- 파일 인코딩 확인: `file -bi /path/to/json/file.json`

### 3. 조문 개수 불일치 알림이 뜰 때
- 구분선(`═══ 조문 구분선 ═══`)을 실수로 삭제하지 않았는지 확인
- 주석 라인(`###`)을 삭제하지 않았는지 확인

## 서버 재시작
```bash
# 서버는 --reload 모드이므로 자동으로 변경사항 반영
# 만약 재시작이 필요하면:
ps aux | grep uvicorn
kill -9 <PID>
cd /home/wizice/regulation/fastapi
uvicorn app:app --host 0.0.0.0 --port 8800 --reload
```

## 구현 요약

**목표:** 기존 JSON 파일에서 조문 내용만 텍스트로 편집하고, 구조(seq, 레벨 등)는 100% 보존

**방식:**
1. JSON → 텍스트: 구분선과 주석으로 조문 구분
2. 텍스트 → JSON: 구분선으로 파싱, 인덱스 기반 내용 교체
3. 저장: 기존 파일 덮어쓰기 (백업 생성)

**핵심 원칙:**
- 새 파일 생성 ❌
- 기존 파일 덮어쓰기 ✅
- 구조 보존 ✅
- 내용만 교체 ✅
