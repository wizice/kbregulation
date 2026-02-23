# Severance Zip 사용 가이드

## 📦 압축하기 (소스 서버에서)

### Step 1: www 디렉토리로 이동
```bash
cd ~/regulation/www
```

### Step 2: 압축 스크립트 실행
```bash
./create_severance_zip.sh
```

### Step 3: 압축 결과 확인
```bash
ls -lh severance_zip.tar.gz
```

압축 파일이 생성되었습니다! (약 425개 파일, 2025-09-24 이후 수정된 파일만)

---

## 📤 압축 파일 전송 (소스 → 대상 서버)

### 방법 1: SCP 사용
```bash
# 현재 위치: ~/regulation/www
scp severance_zip.tar.gz 사용자@대상서버:/home/wizice/regulation/
```

### 방법 2: SFTP 사용
```bash
sftp 사용자@대상서버
put severance_zip.tar.gz /home/wizice/regulation/
exit
```

### 방법 3: USB/다운로드
- `~/regulation/www/severance_zip.tar.gz` 파일을 USB나 다운로드로 복사
- 대상 서버의 `~/regulation/` 폴더에 업로드

---

## 📂 압축 풀기 (대상 서버에서)

### Step 1: regulation 디렉토리로 이동
```bash
cd ~/regulation
```

### Step 2: 압축 파일 확인
```bash
ls -lh severance_zip.tar.gz
```

### Step 3: 압축 해제 스크립트 실행
```bash
./extract_severance_zip.sh
```

또는 압축 파일 경로를 직접 지정:
```bash
./extract_severance_zip.sh ~/regulation/severance_zip.tar.gz
```

### Step 4: 대화형 안내에 따라 진행

**질문 1: 백업 여부**
```
기존 파일을 백업하시겠습니까? (y/n, 기본값: y):
```
- `y` 입력 또는 Enter: 기존 파일을 백업 (권장)
- `n` 입력: 백업하지 않음

**질문 2: 압축 해제 확인**
```
압축을 해제하시겠습니까? (y/n):
```
- `y` 입력: 압축 해제 진행
- `n` 입력: 취소

### Step 5: 완료!
```
======================================
압축 해제 완료!
======================================
처리된 파일: 425 개
백업 위치: /home/wizice/regulation/backup_20251002_123456
```

---

## 🔄 전체 프로세스 요약

```
소스 서버                          대상 서버
---------                          ---------
1. cd ~/regulation/www
2. ./create_severance_zip.sh
3. severance_zip.tar.gz 생성

4. ---- 파일 전송 (scp/sftp) ---->
                                   5. cd ~/regulation
                                   6. ./extract_severance_zip.sh
                                   7. 백업 여부 선택 (y/n)
                                   8. 압축 해제 확인 (y)
                                   9. 완료!
```

---

## ⚠️ 주의사항

1. **백업 권장**: 처음 실행 시 반드시 백업(`y`) 선택하세요
2. **폴더 구조**:
   - `templates/*` → `~/regulation/templates/`로 자동 배치
   - 나머지 파일 → `~/regulation/www/`로 자동 배치
3. **디스크 공간**: 압축 해제 전 충분한 디스크 공간 확인
4. **백업 보관**: 생성된 백업 폴더는 자동 삭제되지 않습니다
5. **Windows에서 압축 해제 시**: Windows 기본 압축 프로그램은 한글 파일명을 지원하지 않습니다
   - **7-Zip** 사용 권장 (무료): https://www.7-zip.org/
   - **반디집** 사용 권장 (무료): https://www.bandisoft.com/bandizip/
   - Linux 서버에서 직접 압축 해제 스크립트 사용 권장

---

## 🆘 문제 해결

### Windows에서 "보관 파일이 잘못되었습니다" 오류 (0x80960016)
**원인**: Windows 기본 압축 프로그램이 UTF-8 한글 파일명을 지원하지 않음

**해결 방법**:
1. **7-Zip 설치** (권장):
   - https://www.7-zip.org/ 다운로드 및 설치
   - tar.gz 파일 우클릭 → "7-Zip" → "압축 풀기"

2. **반디집 설치**:
   - https://www.bandisoft.com/bandizip/ 다운로드 및 설치
   - tar.gz 파일 우클릭 → "반디집으로 압축 풀기"

3. **Linux 서버에서 직접 압축 해제** (가장 안전):
   ```bash
   # 메일로 받은 파일을 서버에 업로드 후
   cd ~/regulation
   ./extract_severance_zip.sh severance_zip.tar.gz
   ```

### 압축 파일을 찾을 수 없다는 오류
```bash
# 압축 파일 위치 확인
find ~/regulation -name "severance_zip.tar.gz"

# 경로를 직접 지정하여 실행
./extract_severance_zip.sh /찾은/경로/severance_zip.tar.gz
```

### 권한 오류
```bash
# 스크립트 실행 권한 부여
chmod +x ~/regulation/www/create_severance_zip.sh
chmod +x ~/regulation/extract_severance_zip.sh
```

### 백업 폴더 삭제
```bash
# 오래된 백업 확인
ls -ld ~/regulation/backup_*

# 불필요한 백업 삭제
rm -rf ~/regulation/backup_20251002_123456
```
