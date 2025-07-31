# LBank Funding Monitor

LBank 거래소의 펀딩 레이트를 모니터링하고 분석하는 Python 프로젝트입니다.

## 기능

- LBank 거래소의 펀딩 레이트 실시간 수집
- MEXC 거래소와의 펀딩 레이트 비교
- 블랙리스트를 통한 특정 티커 제외 기능
- Telegram을 통한 알림 기능
- 펀딩 레이트 데이터 분석 및 시각화

## 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 설정
- `blacklist.json` 파일에서 제외할 티커들을 설정
- Telegram 봇 토큰 설정 (선택사항)

### 3. 실행
```bash
python main.py
```

## 파일 구조

- `main.py`: 메인 실행 파일
- `lbank_monitor.py`: LBank 펀딩 레이트 모니터링
- `mexc_monitor.py`: MEXC 펀딩 레이트 모니터링
- `exchange_comparison.py`: 거래소 간 펀딩 레이트 비교
- `telegram_sender.py`: Telegram 알림 기능
- `manage_blacklist.py`: 블랙리스트 관리
- `test_funding.py`: 테스트 파일
- `blacklist.json`: 제외할 티커 목록
- `requirements.txt`: Python 의존성 목록

## 데이터 파일

- `lbank_funding.json`: LBank 펀딩 레이트 데이터
- `mexc_funding.json`: MEXC 펀딩 레이트 데이터
- `funding_comparison.json`: 거래소 간 비교 데이터
- `lbank_tickers.json`: LBank 티커 목록
- `mexc_prices.json`: MEXC 가격 데이터

## 라이선스

이 프로젝트는 개인적인 용도로 개발되었습니다.

## 연락처

- 이메일: nom456@naver.com
- GitHub: https://github.com/rythem12/lbank_funding.git 