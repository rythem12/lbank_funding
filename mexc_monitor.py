import requests
import json
import time
from datetime import datetime
from typing import Dict, Optional, List
import logging

class MEXCMonitor:
    def __init__(self):
        self.base_url = "https://contract.mexc.com"
        self.funding_file = "mexc_funding.json"
        self.logger = logging.getLogger(__name__)

    def get_funding_rates(self) -> Optional[List[Dict]]:
        """Get MEXC futures funding rates"""
        try:
            endpoint = "/api/v1/contract/ticker"
            url = self.base_url + endpoint
            self.logger.info(f"Fetching funding rates from {url}")
            
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("success"):
                funding_rates = []
                for ticker in data["data"]:
                    if "fundingRate" in ticker:
                        # 심볼 변환: 대문자 -> 소문자, _USDT -> _usdt
                        symbol = ticker["symbol"].lower().replace('_usdt', '_usdt')
                        funding_rate = float(ticker["fundingRate"]) * 100  # 퍼센트로 변환
                        funding_rates.append({
                            "symbol": symbol,
                            "funding_rate": funding_rate,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                self.logger.info(f"Successfully fetched {len(funding_rates)} funding rates")
                return funding_rates
            else:
                self.logger.error(f"API response failed: {data.get('message')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching funding rates: {e}")
            return None

    def save_funding_rates(self, funding_rates: List[Dict]):
        """Save funding rates to JSON file"""
        try:
            data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "funding_rates": funding_rates
            }
            
            with open(self.funding_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(funding_rates)} funding rates to {self.funding_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving funding rates: {e}")

    def monitor_funding_rates(self):
        """Monitor funding rates"""
        self.logger.info("Starting MEXC funding rate monitoring")
        
        try:
            funding_rates = self.get_funding_rates()
            if funding_rates:
                self.save_funding_rates(funding_rates)
                self.logger.info("MEXC funding rate collection completed")
            else:
                self.logger.error("No funding rates were fetched")
                
        except Exception as e:
            self.logger.error(f"Error in monitoring loop: {e}")
            
        finally:
            self.logger.info("MEXC monitoring process completed")

def main():
    monitor = MEXCMonitor()
    monitor.monitor_funding_rates()

if __name__ == "__main__":
    main() 