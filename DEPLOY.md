# 🚀 배포 가이드

## 1단계: GitHub 리포지토리 생성

1. https://github.com/new 접속
2. Repository name: `ewy-dram-flow` (또는 원하는 이름)
3. Description: `EWY/DRAM 수급 자동 리포트 (삼성전자, SK하이닉스, EWY ETF)`
4. Public 또는 Private 선택
5. **"Add a README file" 체크 해제** (이미 README.md 있음)
6. Create repository 클릭

## 2단계: 코드 푸시

```bash
cd /Users/kyungseok10/.openclaw/workspace/dram_ewy_report

# Git 초기화 (아직 안 했다면)
git init
git add .
git commit -m "Initial commit: EWY/DRAM Flow Report"

# 리모트 추가 (YOUR_USERNAME을 실제 GitHub 유저명으로 변경)
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ewy-dram-flow.git
git push -u origin main
```

## 3단계: GitHub Secrets 설정

1. 리포지토리 페이지에서 **Settings** 탭 클릭
2. 왼쪽 메뉴에서 **Secrets and variables** > **Actions** 클릭
3. **New repository secret** 버튼 클릭

### Secret 1: TELEGRAM_BOT_TOKEN
- Name: `TELEGRAM_BOT_TOKEN`
- Value: `8551100662:AAEaRxJ3x4OACiprPxR-RjmDzmh3kmuBkfI`
- **Add secret** 클릭

### Secret 2: TELEGRAM_CHAT_ID
- Name: `TELEGRAM_CHAT_ID`
- Value: `8499505036`
- **Add secret** 클릭

## 4단계: Actions 권한 설정

1. 리포지토리 **Settings** 탭
2. 왼쪽 메뉴 **Actions** > **General**
3. **Workflow permissions** 섹션에서:
   - ✅ **Read and write permissions** 선택
   - ✅ **Allow GitHub Actions to create and approve pull requests** 체크
4. **Save** 클릭

## 5단계: 첫 테스트 실행

1. 리포지토리 **Actions** 탭 클릭
2. 왼쪽에서 **"EWY/DRAM Flow Report"** 워크플로우 선택
3. 오른쪽 위 **"Run workflow"** 버튼 클릭
4. **Use workflow from**: `main` (기본값)
5. **mode**: `preliminary` 또는 `confirmed` 선택
6. **Run workflow** 버튼 클릭

## 6단계: 실행 결과 확인

- Actions 탭에서 실행 중인 워크플로우 클릭
- 각 스텝 로그 확인
- 텔레그램으로 리포트 수신 확인

## ✅ 완료!

이제 매일 자동으로:
- **08:00 KST (잠정치)**: 전날 마감 데이터
- **10:00 KST (확정치)**: 당일 장 개시 전 최종 데이터

가 텔레그램으로 발송됩니다!

## 🐛 트러블슈팅

### "Permission denied" 에러
- Step 4의 Actions 권한 설정 확인

### 텔레그램 메시지 안 옴
- Secrets 값 정확히 입력했는지 확인
- 봇 토큰 유효성 확인

### 데이터 수집 실패
- 주말/공휴일에는 시장 데이터 없음 (정상)
- 평일 장중에 재실행하여 HTML 구조 확인

### Cron 스케줄 안 맞음
- GitHub Actions는 UTC 기준
- KST = UTC + 9시간
- 08:00 KST = 전날 23:00 UTC
- 10:00 KST = 당일 01:00 UTC
