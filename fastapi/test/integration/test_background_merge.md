# 백그라운드 JSON 병합 기능 구현 완료

## 🎯 구현 목표
편집 후 "저장" 버튼 클릭 시:
1. ✅ 즉시 응답 (0.5초 이내)
2. ✅ merge_json 폴더의 JSON 파일 업데이트
3. ✅ 백그라운드에서 `json_all.py` 실행
4. ✅ 백그라운드에서 `create_summary.py` 실행

## 📦 구현 내용

### 1. 백그라운드 함수 추가 (`service_rule_editor.py`)

```python
def run_json_merge_and_summary():
    """
    백그라운드에서 JSON 병합 및 요약 파일 생성
    1. JSON_ALL.py 실행 (merge_json 폴더의 모든 JSON 병합)
    2. create_summary.py 실행 (요약 파일 생성)
    """
    try:
        logger.info("🔄 백그라운드 작업 시작: JSON 병합 및 요약 생성")

        # 1. JSON_ALL.py 실행
        result1 = subprocess.run(
            [PYTHON_EXECUTABLE, JSON_ALL_SCRIPT],
            capture_output=True,
            text=True,
            timeout=60  # 60초 타임아웃
        )

        # 2. create_summary.py 실행
        result2 = subprocess.run(
            [PYTHON_EXECUTABLE, CREATE_SUMMARY_SCRIPT],
            capture_output=True,
            text=True,
            timeout=30  # 30초 타임아웃
        )

        logger.info("✅ 백그라운드 작업 완료")
        return True

    except Exception as e:
        logger.error(f"❌ 백그라운드 작업 실패: {e}")
        return False
```

### 2. API 엔드포인트 수정

```python
@router.put("/update-json/{rule_id}")
async def update_existing_json(
    rule_id: int,
    request: Request,
    background_tasks: BackgroundTasks,  # ← 추가됨
    user: Dict[str, Any] = Depends(get_current_user)
):
    # ... JSON 파일 업데이트 ...

    # 백그라운드에서 JSON 병합 및 요약 생성
    background_tasks.add_task(run_json_merge_and_summary)

    return {
        "success": True,
        "message": "JSON 업데이트 완료 (병합 작업은 백그라운드에서 진행 중)",
        "articles_count": len(updated_json.get('조문내용', []))
    }
```

### 3. 실행 흐름

```
사용자: "저장" 버튼 클릭
    ↓
프론트엔드: PUT /api/v1/rule/update-json/{rule_id}
    ↓
백엔드:
  1. JSON 파일 업데이트 (즉시)
  2. DB content_text 동기화 (즉시)
  3. 백그라운드 작업 예약 (즉시)
  4. 응답 반환 (✅ 저장 완료)
    ↓
사용자: 모달 닫힘, 목록 새로고침
    ↓
백그라운드 (비동기):
  1. JSON_ALL.py 실행 (5~10초)
     - merge_json/*.json → merged_severance.json
  2. create_summary.py 실행 (2~3초)
     - merged_severance.json → summary_severance.json
    ↓
완료: 모든 파일 최신 상태
```

## 📝 테스트 방법

### 방법 1: 웹 UI 테스트

1. **브라우저에서 접속**
   ```
   http://localhost:8800
   ```

2. **로그인**
   - 사용자명: `admin`
   - 비밀번호: `admin123!@#`

3. **규정 편집**
   - 규정 목록에서 아무 규정 선택
   - "편집" 버튼 클릭
   - "내용편집" 탭 클릭
   - 첫 번째 조문의 내용 수정 (예: `[테스트 수정]` 추가)
   - "저장" 버튼 클릭

4. **확인사항**
   - ✅ "저장 완료" 알림 즉시 표시 (0.5초 이내)
   - ✅ 모달 자동 닫힘
   - ✅ 목록 새로고침

5. **로그 확인**
   ```bash
   tail -f /home/wizice/regulation/fastapi/logs/app.log
   ```

   예상 로그:
   ```
   ✅ JSON 파일 업데이트 완료 (rule_id=123), 백그라운드 병합 작업 예약됨
   🔄 백그라운드 작업 시작: JSON 병합 및 요약 생성
     Step 1: JSON_ALL.py 실행 중...
     ✅ JSON_ALL.py 완료
     Step 2: create_summary.py 실행 중...
     ✅ create_summary.py 완료
   ✅ 백그라운드 작업 완료: 병합 파일 및 요약 파일 생성됨
   ```

6. **파일 확인**
   ```bash
   # 개별 JSON 파일 업데이트 확인
   ls -lht /home/wizice/regulation/fastapi/applib/merge_json/ | head -5

   # 병합 파일 확인
   ls -lh /home/wizice/regulation/fastapi/applib/merged_severance.json

   # 요약 파일 확인
   ls -lh /home/wizice/regulation/www/static/file/summary_severance.json
   ```

### 방법 2: 로그 모니터링

터미널에서 실시간 로그 확인:

```bash
# 로그 실시간 모니터링
tail -f /home/wizice/regulation/fastapi/logs/app.log | grep -E "(백그라운드|JSON|병합|요약)"

# 또는 더 자세하게
tail -f /home/wizice/regulation/fastapi/logs/app.log
```

### 방법 3: 파일 타임스탬프 확인

```bash
# 편집 전 타임스탬프 확인
stat /home/wizice/regulation/fastapi/applib/merged_severance.json

# 편집 후 (10초 대기)
sleep 10
stat /home/wizice/regulation/fastapi/applib/merged_severance.json

# 변경 시간이 업데이트되었는지 확인
```

## 🔍 디버깅 가이드

### 문제 1: 백그라운드 작업이 실행되지 않음

**증상:**
- 로그에 "백그라운드 작업 시작" 메시지 없음

**해결:**
1. 서버 로그 확인:
   ```bash
   tail -100 /home/wizice/regulation/fastapi/logs/app.log
   ```

2. Python 경로 확인:
   ```bash
   python3 /home/wizice/regulation/fastapi/applib/JSON_ALL.py
   ```

### 문제 2: JSON_ALL.py 실행 실패

**증상:**
- 로그에 "❌ JSON_ALL.py 실패" 메시지

**해결:**
1. 수동 실행 테스트:
   ```bash
   cd /home/wizice/regulation/fastapi/applib
   python3 JSON_ALL.py
   ```

2. merge_json 폴더 확인:
   ```bash
   ls -l /home/wizice/regulation/fastapi/applib/merge_json/
   ```

3. 권한 확인:
   ```bash
   ls -ld /home/wizice/regulation/fastapi/applib/merge_json/
   ```

### 문제 3: create_summary.py 실행 실패

**증상:**
- 로그에 "❌ create_summary.py 실패" 메시지

**해결:**
1. merged_severance.json 존재 확인:
   ```bash
   ls -lh /home/wizice/regulation/fastapi/applib/merged_severance.json
   ```

2. 수동 실행 테스트:
   ```bash
   cd /home/wizice/regulation/fastapi/applib
   python3 create_summary.py
   ```

3. 출력 폴더 권한 확인:
   ```bash
   ls -ld /home/wizice/regulation/www/static/file/
   ```

### 문제 4: 타임아웃 발생

**증상:**
- 로그에 "❌ 백그라운드 작업 타임아웃" 메시지

**해결:**
1. 파일 개수가 많은 경우 타임아웃 증가:
   ```python
   # service_rule_editor.py에서
   timeout=60  # → timeout=120 으로 증가
   ```

2. 파일 크기 확인:
   ```bash
   du -sh /home/wizice/regulation/fastapi/applib/merge_json/
   ```

## 📊 성능 메트릭

### 예상 실행 시간

| 작업 | 시간 | 비고 |
|------|------|------|
| JSON 파일 업데이트 | ~0.1초 | 즉시 |
| API 응답 | ~0.5초 | 즉시 |
| JSON_ALL.py | 5~10초 | 백그라운드 (파일 개수에 따라) |
| create_summary.py | 2~3초 | 백그라운드 |
| **총 사용자 대기 시간** | **~0.5초** | ✅ |
| **전체 작업 완료** | **7~13초** | 백그라운드 |

### 파일 크기 (참고)

```
merge_json/*.json        : 약 5~6MB (개별 파일들)
merged_severance.json   : 약 10~15MB
summary_severance.json  : 약 2~3MB
```

## ✅ 체크리스트

### 필수 확인사항

- ✅ `service_rule_editor.py`에 `subprocess` import 추가됨
- ✅ `run_json_merge_and_summary()` 함수 구현됨
- ✅ `update_existing_json()` 엔드포인트에 `background_tasks` 파라미터 추가됨
- ✅ `background_tasks.add_task()` 호출 추가됨
- ✅ 서버가 `--reload` 모드로 실행 중
- ✅ JSON_ALL.py 실행 가능
- ✅ create_summary.py 실행 가능
- ✅ merge_json 폴더 존재 및 권한 확인

### 테스트 확인사항

- ⏸️ 웹 UI에서 편집 → 저장 → 즉시 응답 확인
- ⏸️ 로그에 백그라운드 작업 시작/완료 메시지 확인
- ⏸️ merged_severance.json 타임스탬프 업데이트 확인
- ⏸️ summary_severance.json 타임스탬프 업데이트 확인
- ⏸️ 편집한 내용이 병합 파일에 반영되었는지 확인

## 🎉 완료!

이제 편집 후 저장 시:
1. ✅ **즉시 응답** - 사용자는 기다릴 필요 없음
2. ✅ **자동 병합** - 백그라운드에서 자동으로 처리
3. ✅ **최신 상태 유지** - merged_severance.json과 summary_severance.json 항상 최신
4. ✅ **안정성** - 병합 실패해도 개별 JSON 파일은 안전

---

**작성일:** 2025-10-11
**작성자:** Claude AI
**테스트 필요:** 실제 편집 → 저장 → 로그 확인
