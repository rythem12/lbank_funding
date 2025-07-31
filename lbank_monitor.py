import requests
import json
import time
from datetime import datetime
from typing import Dict, Optional, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging
import gc
import os
import psutil

class LBankPriceMonitor:
    def __init__(self):
        self.base_url = "https://api.lbank.com"
        self.interval = 10  # 10초 간격
        self.ticker_file = "lbank_tickers.json"
        self.funding_file = "lbank_funding.json"
        self.log_file = "lbank_funding.log"
        self.blacklist_file = "blacklist.json"
        self.driver = None
        self.driver_lock = threading.Lock()
        
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()  # 콘솔 출력만 사용
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_selenium(self):
        """Setup Selenium WebDriver with Cloudflare bypass"""
        try:
            options = Options()
            options.add_argument('--headless')
            
            # Cloudflare 우회를 위한 User-Agent 설정
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Firefox 전용 설정
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference('useAutomationExtension', False)
            
            # 창 크기 설정
            options.add_argument('--window-size=1920,1080')
            
            # 메모리 최적화 설정
            options.set_preference("browser.cache.disk.enable", False)
            options.set_preference("browser.cache.memory.enable", False)
            options.set_preference("browser.cache.offline.enable", False)
            options.set_preference("network.http.use-cache", False)
            
            service = Service(executable_path='/usr/local/bin/geckodriver')
            driver = webdriver.Firefox(service=service, options=options)
            
            # JavaScript 실행으로 자동화 감지 방지
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info(f"Firefox WebDriver successfully initialized for thread {threading.get_ident()}")
            return driver
        except Exception as e:
            self.logger.error(f"Error setting up Firefox WebDriver: {e}")
            raise

    def cleanup_driver(self, driver):
        """Clean up WebDriver resources"""
        try:
            if driver:
                driver.quit()
        except Exception as e:
            self.logger.warning(f"Error cleaning up driver: {e}")

    def read_blacklist(self) -> set:
        """Read blacklist from JSON file"""
        try:
            with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                blacklist = set(data.get('blacklist', []))
                self.logger.info(f"📋 Loaded {len(blacklist)} blacklisted tickers")
                return blacklist
        except FileNotFoundError:
            self.logger.warning(f"Blacklist file {self.blacklist_file} not found, using empty blacklist")
            return set()
        except Exception as e:
            self.logger.error(f"Error reading blacklist: {e}")
            return set()

    def read_tickers_from_file(self) -> Optional[List[Dict]]:
        """Read ticker information from JSON file"""
        try:
            with open(self.ticker_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('tickers', [])
        except Exception as e:
            print(f"Error reading tickers from file: {e}")
            return None

    def get_funding_rate_from_web(self, symbol: str, max_retries: int = 2) -> dict:
        """Get funding rate from LBank website using Selenium and BeautifulSoup with optimized retry logic and memory management"""
        for attempt in range(max_retries):
            driver = None
            soup = None
            html = None
            try:
                driver = self.setup_selenium()
                symbol_converted = symbol.replace('_', '').lower()
                url = f"https://www.lbank.com/futures/{symbol_converted}"
                self.logger.info(f"Fetching funding rate for {symbol} (attempt {attempt + 1}/{max_retries})")
                
                self.logger.info("Loading page...")
                driver.get(url)
                
                # Cloudflare 페이지 확인 및 대기 (시간 단축)
                self.logger.info("Checking for Cloudflare protection...")
                time.sleep(2)  # 3초 → 2초로 단축
                
                # Cloudflare 페이지인지 확인
                title = driver.title
                if "Just a moment" in title or "Checking your browser" in title:
                    self.logger.info("Cloudflare protection detected, waiting for bypass...")
                    # Cloudflare 우회를 위해 대기 (시간 단축)
                    time.sleep(10)  # 15초 → 10초로 단축
                    
                    # 페이지 새로고침
                    driver.refresh()
                    time.sleep(3)  # 5초 → 3초로 단축
                
                # JavaScript 실행 완료까지 대기 (시간 단축)
                self.logger.info("Waiting for JavaScript to complete...")
                time.sleep(6)  # 10초 → 6초로 단축
                
                # 페이지가 완전히 로드되었는지 확인 (시간 단축)
                self.logger.info("Checking if page is fully loaded...")
                time.sleep(2)  # 3초 → 2초로 단축
                
                # HTML 가져오기
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                
                # 디버깅: 페이지 제목 확인
                title = soup.find('title')
                self.logger.info(f"Page title: {title.text if title else 'No title found'}")
                
                # funding rate와 countdown 찾기 (최적화된 검색)
                self.logger.info("Searching for funding rate and countdown in HTML...")
                
                # 1. warning_color span에서 직접 검색 (가장 빠른 방법)
                funding_spans = soup.find_all('span', class_='warning_color')
                self.logger.info(f"Found {len(funding_spans)} spans with warning_color class")
                
                for span in funding_spans:
                    if '%' in span.text:
                        funding_rate = span.text.strip()
                        self.logger.info(f"Found funding rate: {funding_rate}")
                        
                        # countdown 찾기
                        countdown = "Not found"
                        next_span = span.find_next('span')
                        if next_span and ':' in next_span.text:
                            countdown = next_span.text.strip()
                        
                        return {
                            "symbol": symbol,
                            "funding_rate": float(funding_rate.replace('%', '')),
                            "countdown": countdown,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                
                # 2. funding-rate div에서 검색 (백업 방법)
                funding_divs = soup.find_all('div', class_='funding-rate')
                self.logger.info(f"Found {len(funding_divs)} divs with funding-rate class")
                
                for div in funding_divs:
                    funding_rate_span = div.find('span', class_='warning_color')
                    if funding_rate_span and '%' in funding_rate_span.text:
                        funding_rate = funding_rate_span.text.strip()
                        self.logger.info(f"Found funding rate: {funding_rate}")
                        
                        countdown_span = div.find('span', class_='countdown')
                        if countdown_span:
                            countdown = countdown_span.text.strip()
                        else:
                            next_span = funding_rate_span.find_next('span')
                            countdown = next_span.text.strip() if next_span else "Not found"
                        
                        result = {
                            "symbol": symbol,
                            "funding_rate": float(funding_rate.replace('%', '')),
                            "countdown": countdown,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        return result
                
                # 3. 모든 span에서 %가 포함된 텍스트 찾기 (최후의 방법)
                all_spans = soup.find_all('span')
                for span in all_spans:
                    if span.text and '%' in span.text and any(char.isdigit() for char in span.text):
                        text = span.text.strip()
                        # 펀딩 레이트 패턴 확인 (예: +0.0019%, -0.0019%)
                        if ('+' in text or '-' in text) and '%' in text:
                            try:
                                funding_rate = text
                                self.logger.info(f"Found funding rate with alternative method: {funding_rate}")
                                
                                # countdown 찾기
                                countdown = "Not found"
                                next_span = span.find_next('span')
                                if next_span and ':' in next_span.text:
                                    countdown = next_span.text.strip()
                                
                                result = {
                                    "symbol": symbol,
                                    "funding_rate": float(funding_rate.replace('%', '').replace('+', '')),
                                    "countdown": countdown,
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                                
                                return result
                            except ValueError:
                                continue
                
                self.logger.warning(f"Could not find funding rate in HTML (attempt {attempt + 1}/{max_retries})")
                
                # 재시도 전 대기 (시간 단축)
                if attempt < max_retries - 1:
                    self.logger.info(f"Waiting 3 seconds before retry...")
                    time.sleep(3)
                
            except Exception as e:
                self.logger.error(f"Error getting funding rate from web for {symbol} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    self.logger.info(f"Waiting 3 seconds before retry...")
                    time.sleep(3)
                
            finally:
                # 메모리 정리
                if soup:
                    del soup
                if html:
                    del html
                self.cleanup_driver(driver)
        
        self.logger.error(f"Failed to get funding rate for {symbol} after {max_retries} attempts")
        return None

    def update_funding_rates(self):
        """Update funding rates for all tickers from JSON file"""
        try:
            print("\nReading tickers from file...")
            tickers = self.read_tickers_from_file()
            if not tickers:
                print("No tickers found in file")
                return

            print("\nUpdating funding rates...")
            funding_rates = []
            total_tickers = len(tickers)
            
            for idx, ticker in enumerate(tickers, 1):
                symbol = ticker.get('symbol')
                if symbol:
                    print(f"\nProcessing {idx}/{total_tickers}: {symbol}")
                    funding_data = self.get_funding_rate_from_web(symbol)
                    if funding_data:
                        funding_rates.append(funding_data)
                    time.sleep(1)  # 웹 크롤링 간격 조절
            
            data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "funding_rates": funding_rates
            }
            
            with open(self.funding_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"\nSaved {len(funding_rates)} funding rates to {self.funding_file}")
            if funding_rates:
                print("Sample funding rate data:")
                print(json.dumps(funding_rates[0], indent=2, ensure_ascii=False))
            
        except Exception as e:
            print(f"Error updating funding rates: {e}")

    def get_currency_pairs(self) -> Optional[List[str]]:
        """Get all available currency pairs"""
        try:
            endpoint = "/v2/currencyPairs.do"
            url = self.base_url + endpoint
            print(f"\nFetching currency pairs from {url}")
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if isinstance(data, dict) and 'data' in data:
                # USDT 페어만 필터링하고 레버리지 페어 제외
                excluded = ['3l', '3s', '5l', '5s']
                usdt_pairs = [
                    pair for pair in data['data'] 
                    if pair.endswith('_usdt') and not any(x in pair.lower() for x in excluded)
                ]
                print(f"Found {len(usdt_pairs)} USDT pairs (excluding leverage pairs)")
                return usdt_pairs
                
            else:
                print(f"[LBank] Unexpected currency pairs response format: {data}")
                return None
                
        except Exception as e:
            print(f"[LBank] Error getting currency pairs: {e}")
            return None

    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get ticker information for a specific symbol"""
        try:
            endpoint = "/v2/ticker/24hr.do"
            url = self.base_url + endpoint
            params = {"symbol": symbol}
            print(f"Fetching ticker for {symbol}")
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if isinstance(data, dict) and 'data' in data:
                ticker_data = data['data'][0]
                print(f"Got ticker for {symbol}: latest price = {ticker_data.get('ticker', {}).get('latest', 'N/A')}")
                return ticker_data
            else:
                print(f"[LBank] Unexpected ticker response for {symbol}: {data}")
                return None
                
        except Exception as e:
            print(f"[LBank] Error getting ticker for {symbol}: {e}")
            return None

    def get_all_tickers(self) -> Optional[List[Dict]]:
        """Get all ticker information from LBank"""
        try:
            # 1. 먼저 모든 USDT 페어 가져오기
            usdt_pairs = self.get_currency_pairs()
            if not usdt_pairs:
                return None

            # 2. 각 페어의 티커 정보 가져오기
            tickers = []
            total_pairs = len(usdt_pairs)
            
            print(f"\nFetching ticker information for {total_pairs} pairs...")
            for idx, symbol in enumerate(usdt_pairs, 1):
                print(f"Fetching {idx}/{total_pairs}: {symbol}")
                ticker = self.get_ticker(symbol)
                if ticker:
                    tickers.append(ticker)
                time.sleep(1)  # API 호출 간격을 1초로 늘림

            return tickers
                
        except Exception as e:
            print(f"[LBank] Error getting all tickers: {e}")
            return None

    def save_tickers(self, tickers: List[Dict]):
        """Save ticker information to JSON file"""
        try:
            data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tickers": tickers
            }
            
            with open(self.ticker_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"\nSaved {len(tickers)} tickers to {self.ticker_file}")
            print("Sample ticker data:")
            if tickers:
                print(json.dumps(tickers[0], indent=2, ensure_ascii=False))
            
        except Exception as e:
            print(f"Error saving tickers: {e}")

    def save_funding_rates(self, funding_rates: list):
        """Save funding rates directly to a single file"""
        try:
            data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "funding_rates": funding_rates
            }
            
            with open(self.funding_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"💾 Saved {len(funding_rates)} funding rates to {self.funding_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving funding rates: {e}")

    def log_memory_usage(self, stage: str = ""):
        """Log current memory usage"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024  # MB로 변환
            
            self.logger.info(f"💾 Memory usage {stage}: {memory_mb:.1f} MB")
            return memory_mb
        except Exception as e:
            self.logger.warning(f"Could not get memory usage: {e}")
            return 0

    def process_ticker_batch(self, tickers: list, batch_num: int) -> list:
        """Process a batch of tickers in parallel for maximum speed with memory management"""
        start_time = datetime.now()
        self.logger.info(f"Starting batch {batch_num} with {len(tickers)} tickers at {start_time}")
        
        # 메모리 사용량 로그
        self.log_memory_usage(f"before batch {batch_num}")
        
        funding_rates = []
        success_count = 0
        
        # 병렬 처리로 속도 향상 (워커 수를 10으로 증가)
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 각 티커에 대해 병렬로 펀딩 레이트 가져오기
            future_to_ticker = {
                executor.submit(self.get_funding_rate_from_web, ticker.get('symbol'), 2): ticker 
                for ticker in tickers if ticker.get('symbol')
            }
            
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                symbol = ticker.get('symbol')
                
                try:
                    funding_data = future.result()
                    if funding_data:
                        funding_rates.append(funding_data)
                        success_count += 1
                        self.logger.info(f"✓ Success: {symbol} = {funding_data['funding_rate']}")
                    else:
                        self.logger.warning(f"✗ Failed: {symbol}")
                        
                except Exception as e:
                    self.logger.error(f"Error processing ticker {symbol}: {e}")
                
                # 주기적으로 가비지 컬렉션 실행 (메모리 관리)
                if len(funding_rates) % 10 == 0 and len(funding_rates) > 0:
                    gc.collect()
                    self.log_memory_usage(f"after {len(funding_rates)} tickers in batch {batch_num}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        success_rate = (success_count / len(tickers)) * 100 if tickers else 0
        
        self.logger.info(f"Completed batch {batch_num} in {duration:.2f} seconds")
        self.logger.info(f"Success rate: {success_count}/{len(tickers)} ({success_rate:.1f}%)")
        
        # 메모리 정리
        gc.collect()
        self.log_memory_usage(f"after batch {batch_num}")
        
        return funding_rates

    def monitor_loop(self):
        """Monitor funding rates continuously with optimized performance and memory management"""
        self.logger.info("Starting LBank funding rate monitoring")
        
        try:
            # 티커 읽기
            tickers = self.read_tickers_from_file()
            if not tickers:
                self.logger.error("No tickers found")
                return
            
            # 블랙리스트 읽기 및 적용
            blacklist = self.read_blacklist()
            filtered_tickers = [ticker for ticker in tickers if ticker.get('symbol') not in blacklist]
            
            self.logger.info(f"📊 Original tickers: {len(tickers)}")
            self.logger.info(f"🚫 Blacklisted tickers: {len(blacklist)}")
            self.logger.info(f"✅ Filtered tickers: {len(filtered_tickers)}")
            
            if not filtered_tickers:
                self.logger.error("No tickers remaining after blacklist filtering")
                return
            
            batch_size = 80  # 배치 크기를 80으로 대폭 증가 (속도 대폭 향상)
            total_batches = (len(filtered_tickers) + batch_size - 1) // batch_size
            
            self.logger.info(f"Processing {len(filtered_tickers)} tickers in {total_batches} batches")
            
            all_funding_rates = []
            
            # 티커를 배치로 나누어 처리
            for i in range(0, len(filtered_tickers), batch_size):
                batch = filtered_tickers[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                self.logger.info(f"Starting batch {batch_num}/{total_batches}")
                
                # 배치 처리
                funding_rates = self.process_ticker_batch(batch, batch_num)
                all_funding_rates.extend(funding_rates)
                
                # 배치 간 대기 (시간 단축)
                if i + batch_size < len(filtered_tickers):
                    self.logger.info("Waiting 3 seconds before next batch...")
                    time.sleep(3)
                
                # 메모리 정리
                gc.collect()
            
            # 모든 배치 처리 완료 후 한 번에 저장
            if all_funding_rates:
                self.save_funding_rates(all_funding_rates)
                total_success_rate = (len(all_funding_rates) / len(filtered_tickers)) * 100
                self.logger.info(f"📊 Overall success rate: {len(all_funding_rates)}/{len(filtered_tickers)} ({total_success_rate:.1f}%)")
                self.logger.info("🎉 LBank funding rate collection completed")
            else:
                self.logger.error("❌ No funding rates were fetched")
                
        except Exception as e:
            self.logger.error(f"Error in monitoring loop: {e}")
            
        finally:
            # 최종 메모리 정리
            gc.collect()
            self.logger.info("🏁 LBank monitoring process completed")

def main():
    monitor = LBankPriceMonitor()
    monitor.monitor_loop()

if __name__ == "__main__":
    main() 