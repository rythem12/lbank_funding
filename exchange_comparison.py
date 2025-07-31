import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import pandas as pd
from dataclasses import dataclass

@dataclass
class ExchangeData:
    symbol: str
    price: float
    funding_rate: str  # 문자열로 변경 (퍼센트 표시 포함)
    countdown: str     # 펀딩 주기 추가
    timestamp: str

class LBankPriceMonitor:
    def __init__(self):
        self.filename = "lbank_funding.json"  # 변경된 파일명

    def get_funding_data(self) -> Dict:
        """Get LBank funding rates and countdowns"""
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("funding_rates", [])
        except Exception as e:
            print(f"[LBank] Error reading funding data: {e}")
        return []

class MexcPriceMonitor:
    def __init__(self):
        self.filename = "mexc_prices.json"

    def get_funding_data(self) -> Dict:
        """Get MEXC funding rates"""
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("prices", [])
        except Exception as e:
            print(f"[MEXC] Error reading funding data: {e}")
        return []

class ExchangeComparator:
    def __init__(self):
        self.lbank = LBankPriceMonitor()
        self.mexc = MexcPriceMonitor()
        self.comparison_file = "exchange_comparison.csv"

    def collect_data(self) -> Tuple[List[ExchangeData], List[ExchangeData]]:
        """Collect data from both exchanges"""
        lbank_data = []
        mexc_data = []

        # Get LBank data
        lbank_funding = self.lbank.get_funding_data()
        for item in lbank_funding:
            symbol = item.get("symbol", "")
            if symbol.endswith("_usdt"):  # Only consider USDT pairs
                lbank_data.append(ExchangeData(
                    symbol=symbol,
                    price=0.0,  # 가격 정보는 필요 없음
                    funding_rate=item.get("funding_rate", "0%"),
                    countdown=item.get("countdown", "N/A"),
                    timestamp=item.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                ))

        # Get MEXC data
        mexc_funding = self.mexc.get_funding_data()
        for item in mexc_funding:
            symbol = item.get("symbol", "")
            if symbol.endswith("_usdt"):  # Only consider USDT pairs
                # MEXC의 펀딩비를 퍼센트 형태로 변환
                funding_rate = float(item.get("fundingRate", 0)) * 100
                mexc_data.append(ExchangeData(
                    symbol=symbol,
                    price=0.0,  # 가격 정보는 필요 없음
                    funding_rate=f"{funding_rate:.4f}%",
                    countdown="8h",  # MEXC는 8시간 주기
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

        return lbank_data, mexc_data

    def compare_exchanges(self):
        """Compare funding rates and periods between exchanges"""
        lbank_data, mexc_data = self.collect_data()

        # Create DataFrames
        lbank_df = pd.DataFrame([vars(d) for d in lbank_data])
        mexc_df = pd.DataFrame([vars(d) for d in mexc_data])

        # Merge DataFrames on symbol
        comparison_df = pd.merge(
            lbank_df, 
            mexc_df, 
            on='symbol', 
            suffixes=('_lbank', '_mexc'),
            how='outer'  # 양쪽 데이터 모두 포함
        )

        # 펀딩비 비교
        comparison_df['funding_rate_diff'] = comparison_df.apply(
            lambda x: self._calculate_funding_rate_diff(x['funding_rate_lbank'], x['funding_rate_mexc']),
            axis=1
        )

        # 정렬 (펀딩비 차이가 큰 순서대로)
        comparison_df = comparison_df.sort_values('funding_rate_diff', ascending=False)

        # Save to CSV
        comparison_df.to_csv(self.comparison_file, index=False)
        print(f"Comparison data saved to {self.comparison_file}")

        # Print summary
        print("\nExchange Comparison Summary:")
        print(comparison_df[['symbol', 'funding_rate_lbank', 'funding_rate_mexc', 
                           'funding_rate_diff', 'countdown_lbank', 'countdown_mexc']].to_string())

    def _calculate_funding_rate_diff(self, lbank_rate: str, mexc_rate: str) -> float:
        """Calculate the difference between funding rates"""
        try:
            # 퍼센트 기호 제거하고 숫자로 변환
            lbank_value = float(lbank_rate.strip('%+')) if lbank_rate != "N/A" else 0
            mexc_value = float(mexc_rate.strip('%+')) if mexc_rate != "N/A" else 0
            return abs(lbank_value - mexc_value)
        except:
            return 0.0

    def monitor_loop(self):
        """Continuously monitor and compare exchanges"""
        print("Starting exchange comparison monitoring...")
        print("Press Ctrl+C to stop...")
        
        while True:
            try:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{current_time}] Collecting and comparing data...")
                
                self.compare_exchanges()
                time.sleep(60)  # 1분 간격으로 업데이트
                
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(60)

def main():
    comparator = ExchangeComparator()
    comparator.monitor_loop()

if __name__ == "__main__":
    main() 