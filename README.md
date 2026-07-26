# EWY/DRAM Flow Report

매일 자동으로 삼성전자, SK하이닉스 수급 및 EWY ETF 데이터를 수집하여 텔레그램으로 리포트를 발송합니다.

## 📅 발송 스케줄

- **08:00 KST (잠정치 / preliminary)**: 전날 마감 기준 데이터
- **10:00 KST (확정치 / confirmed)**: 당일 장 개시 직전 최종 데이터

## 🚀 GitHub Actions 설정

### 1. 리포지토리 생성
GitHub에서 새 리포지토리를 생성하고 이 폴더의 내용을 푸시합니다.

```bash
cd /Users/kyungseok10/.openclaw/workspace/dram_ewy_report
git init
git add .
git commit -m "Initial commit: EWY/DRAM Flow Report"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ewy-dram-flow.git
git push -u origin main
```

### 2. GitHub Secrets 설정

리포지토리 Settings > Secrets and variables > Actions > New repository secret:

- **TELEGRAM_BOT_TOKEN**: 텔레그램 봇 토큰 (현재 사용 중인 한국 시장 보고서 봇 토큰)
  - 값: `8551100662:AAEaRxJ3x4OACiprPxR-RjmDzmh3kmuBkfI`

- **TELEGRAM_CHAT_ID**: 수신자 Chat ID
  - 값: `8499505036`

### 3. Actions 권한 활성화

리포지토리 Settings > Actions > General:
- **Workflow permissions**: "Read and write permissions" 선택
- **Allow GitHub Actions to create and approve pull requests** 체크

### 4. 수동 테스트

리포지토리 Actions 탭 > "EWY/DRAM Flow Report" 워크플로우 선택 > "Run workflow" 버튼 클릭
- **mode 선택**: preliminary (잠정치) 또는 confirmed (확정치)

## 📊 수집 데이터

### 한국 주식 (네이버 금융)
- 삼성전자 (005930)
- SK하이닉스 (000660)

항목:
- 종가
- 외국인 순매수량
- 기관 순매수량

### 미국 ETF
- EWY (iShares MSCI South Korea ETF)

항목:
- 현재가
- 변동률

## 🛠️ 로컬 테스트

```bash
cd /Users/kyungseok10/.openclaw/workspace/dram_ewy_report
export TELEGRAM_BOT_TOKEN="8551100662:AAEaRxJ3x4OACiprPxR-RjmDzmh3kmuBkfI"
export TELEGRAM_CHAT_ID="8499505036"
python3 main.py --mode preliminary
```

## 📝 파일 구조

```
dram_ewy_report/
├── .github/
│   └── workflows/
│       └── report.yml          # GitHub Actions 워크플로우 (수동 실행 지원)
├── main.py                     # 메인 스크립트
├── requirements.txt            # Python 의존성
├── state.json                  # 실행 상태 (루트 디렉토리, 자동 커밋)
└── README.md                   # 이 파일
```

### 워크플로우 특징
- **자동 실행**: 매일 08:00, 10:00 KST (UTC 23:00, 01:00)
- **수동 실행**: Actions 탭에서 "Run workflow" 버튼으로 즉시 실행 가능
  - mode 선택 가능 (preliminary / confirmed)
- **state.json 자동 커밋**: 실행 히스토리 Git으로 추적

## 🔧 트러블슈팅

### 데이터 수집 실패
- 네이버 금융 페이지 구조 변경 시 `main.py`의 셀렉터 수정 필요
- User-Agent 차단 시 헤더 변경

### 텔레그램 발송 실패
- Secrets 설정 확인
- 봇 토큰 유효성 확인
- Chat ID 정확성 확인

### GitHub Actions 실행 실패
- Workflow permissions 확인
- Python 버전 호환성 확인

## 📌 참고

- 한국 주식 데이터는 전날 마감 기준 (T-1)
- EWY는 실시간 데이터 (미국 시장 개장 시)
- GitHub Actions는 UTC 기준으로 작동 (KST = UTC+9)
