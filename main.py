import time
from lbank_monitor import LBankPriceMonitor
from mexc_monitor import MEXCMonitor
from telegram_sender import TelegramSender
import logging
import json
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # 콘솔 출력만 사용
    ]
)

def compare_funding_rates():
    """LBank와 MEXC의 펀딩 레이트 비교"""
    try:
        # LBank 펀딩 레이트 읽기
        with open('lbank_funding.json', 'r', encoding='utf-8') as f:
            lbank_data = json.load(f)
            lbank_rates = {}
            for item in lbank_data.get('funding_rates', []):
                rate = item['funding_rate']
                # 문자열인 경우 % 제거 후 float로 변환
                if isinstance(rate, str):
                    rate = float(rate.replace('%', ''))
                lbank_rates[item['symbol']] = rate
        
        # MEXC 펀딩 레이트 읽기
        with open('mexc_funding.json', 'r', encoding='utf-8') as f:
            mexc_data = json.load(f)
            mexc_rates = {item['symbol']: float(item['funding_rate'])
                         for item in mexc_data.get('funding_rates', [])}
        
        # 공통 심볼 찾기 및 비교
        common_symbols = set(lbank_rates.keys()) & set(mexc_rates.keys())
        comparison_results = []
        
        # 임계값을 0.001 (0.1%)로 수정
        threshold = 0.001
        
        for symbol in common_symbols:
            lbank_rate = lbank_rates[symbol]
            mexc_rate = mexc_rates[symbol]
            difference = lbank_rate - mexc_rate
            
            # 펀딩 레이트 차이가 0.1% 이상인 경우만 포함
            if abs(difference) >= threshold:
                comparison_results.append({
                    'symbol': symbol,
                    'lbank_rate': lbank_rate,
                    'mexc_rate': mexc_rate,
                    'difference': difference,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        
        # 결과 저장
        with open('funding_comparison.json', 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'comparisons': comparison_results
            }, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Compared {len(comparison_results)} funding rates with difference >= 0.1%")
        return comparison_results
        
    except Exception as e:
        logging.error(f"Error comparing funding rates: {e}")
        return None

def main():
    """메인 실행 함수"""
    logging.info("모니터링 시스템 시작")
    
    try:
        while True:
            try:
                # 1. LBank 펀딩 레이트 수집
                logging.info("LBank 펀딩 레이트 수집 시작")
                lbank = LBankPriceMonitor()
                lbank.monitor_loop()
                logging.info("LBank 펀딩 레이트 수집 완료")
                
                # 2. MEXC 펀딩 레이트 수집
                logging.info("MEXC 펀딩 레이트 수집 시작")
                mexc = MEXCMonitor()
                mexc.monitor_funding_rates()
                logging.info("MEXC 펀딩 레이트 수집 완료")
                
                # 3. 펀딩 레이트 비교
                logging.info("펀딩 레이트 비교 시작")
                comparison_results = compare_funding_rates()
                if comparison_results:
                    logging.info("펀딩 레이트 비교 완료")
                    
                    # 4. 결과 전송
                    logging.info("결과 전송 시작")
                    telegram = TelegramSender()
                    telegram.send_comparison_results(comparison_results)
                    logging.info("결과 전송 완료")
                else:
                    logging.error("펀딩 레이트 비교 실패")
                
                # 30분 대기
                logging.info("다음 실행까지 30분 대기...")
                time.sleep(1800)  # 30분 = 1800초
                
            except Exception as e:
                logging.error(f"실행 중 오류 발생: {e}")
                logging.info("15분 후 재시도...")
                time.sleep(900)  # 15분 대기 후 재시도
                
    except KeyboardInterrupt:
        logging.info("모니터링 시스템 종료")
    except Exception as e:
        logging.error(f"시스템 오류: {e}")

if __name__ == "__main__":
    main() 