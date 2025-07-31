import requests
import json
import logging
import time
from datetime import datetime
import pandas as pd
import os

class TelegramSender:
    def __init__(self):
        # 직접 환경설정 값 입력
        self.token = "8097747405:AAGg87KUDPXE-I812jzJogDGK_qDRROpOTI"  # 실제 토큰으로 교체 필요
        self.chat_id = "-1002610171617"  # 실제 채팅 ID로 교체 필요
        self.comparison_file = "exchange_comparison.csv"    
        self.last_sent_time = None
        self.logger = logging.getLogger(__name__)

    def send_message(self, message: str):
        """텔레그램 메시지 전송"""
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=data)
            response.raise_for_status()
            self.logger.info("메시지 전송 성공")
        except Exception as e:
            self.logger.error(f"메시지 전송 실패: {e}")

    def format_comparison_message(self, df: pd.DataFrame, top_n: int = 5) -> str:
        """Format comparison data into a readable message"""
        try:
            # 상위 N개 펀딩비 차이만 선택
            top_df = df.head(top_n)
            
            message = "<b>🔔 거래소 펀딩비 비교 결과</b>\n\n"
            message += f"📊 비교 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for _, row in top_df.iterrows():
                symbol = row['symbol']
                lbank_rate = row['funding_rate_lbank']
                mexc_rate = row['funding_rate_mexc']
                diff = row['funding_rate_diff']
                lbank_countdown = row['countdown_lbank']
                mexc_countdown = row['countdown_mexc']
                
                message += f"<b>{symbol}</b>\n"
                message += f"LBank: {lbank_rate} (남은시간: {lbank_countdown})\n"
                message += f"MEXC: {mexc_rate} (주기: {mexc_countdown})\n"
                message += f"차이: {diff:.4f}%\n\n"
            
            return message
        except Exception as e:
            print(f"Error formatting message: {e}")
            return "Error formatting comparison data"

    def send_comparison(self):
        """Send comparison results to Telegram"""
        try:
            # CSV 파일 읽기
            df = pd.read_csv(self.comparison_file)
            
            # 메시지 포맷팅
            message = self.format_comparison_message(df)
            
            # 메시지 전송
            if self.send_message(message):
                print("Comparison results sent to Telegram")
                self.last_sent_time = datetime.now()
            else:
                print("Failed to send comparison results")
                
        except Exception as e:
            print(f"Error in send_comparison: {e}")

    def send_comparison_results(self, comparison_results: list):
        """펀딩 레이트 비교 결과 전송"""
        try:
            # 결과를 메시지로 포맷팅
            message = "<b>펀딩 레이트 비교 결과</b>\n\n"
            
            # 차이가 큰 순서대로 정렬
            sorted_results = sorted(comparison_results, 
                                 key=lambda x: abs(x['difference']), 
                                 reverse=True)
            
            for result in sorted_results[:10]:  # 상위 10개만 표시
                symbol = result['symbol']
                lbank_rate = result['lbank_rate']
                mexc_rate = result['mexc_rate']
                difference = result['difference']
                
                message += (
                    f"<b>{symbol}</b>\n"
                    f"LBank: {lbank_rate:.4f}%\n"
                    f"MEXC: {mexc_rate:.4f}%\n"
                    f"차이: {difference:.4f}%\n\n"
                )
            
            # 메시지 전송
            self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"비교 결과 전송 실패: {e}")

    def monitor_and_send(self, interval_minutes: int = 5):
        """Monitor comparison file and send updates"""
        self.logger.info("텔레그램 전송 시작")
        print("Press Ctrl+C to stop...")
        
        while True:
            try:
                current_time = datetime.now()
                
                # 첫 실행이거나 지정된 간격이 지났을 때만 전송
                if (self.last_sent_time is None or 
                    (current_time - self.last_sent_time).total_seconds() >= interval_minutes * 60):
                    self.send_comparison()
                
                time.sleep(60)  # 1분마다 체크
                
            except KeyboardInterrupt:
                self.logger.info("텔레그램 전송 종료")
                break
            except Exception as e:
                self.logger.error(f"텔레그램 전송 오류: {e}")
                time.sleep(60)

def main():
    sender = TelegramSender()
    sender.monitor_and_send()

if __name__ == "__main__":
    main() 